"""
Cookie Consent Handler for browser automation.

Detects and automatically handles cookie consent dialogs using common patterns
and provides comprehensive logging for debugging consent handling issues.
"""

import asyncio
import logging
from typing import Optional, List
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ConsentResult


logger = logging.getLogger(__name__)


class CookieConsentHandler:
    """
    Detects and automatically handles cookie consent dialogs.
    
    Uses a prioritized list of CSS selectors for common consent management
    platforms and provides fallback strategies for unknown dialog types.
    """
    
    # Prioritized list of consent button selectors
    CONSENT_SELECTORS = [
        # CookieBot
        '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
        
        # OneTrust
        '#onetrust-accept-btn-handler',
        
        # Cookieyes
        '.cky-btn-accept',
        
        # Swedish-specific patterns
        'button:has-text("Godkänn alla kakor")',
        'button:has-text("Acceptera alla kakor")',
        'button:has-text("Godkänn alla")',
        
        # Generic accept patterns
        'button:has-text("Accept all")',
        'button:has-text("Acceptera alla")',
        'button:has-text("Accept")',
        'button:has-text("Acceptera")',
        
        # Attribute-based fallbacks
        '[data-testid*="accept"]',
        '[id*="accept"]',
        '[class*="accept"]',
        '[data-cy*="accept"]',
        
        # Common button classes
        '.cookie-accept',
        '.consent-accept',
        '.accept-all',
        '.btn-accept'
    ]
    
    # Dialog detection selectors
    DIALOG_SELECTORS = [
        '[role="dialog"]',
        'dialog',  # HTML5 dialog element
        '.cookie-banner',
        '.consent-banner',
        '.cookie-notice',
        '#cookie-consent',
        '.gdpr-banner',
        '[class*="cookie"]',
        '[class*="consent"]',
        '[id*="cookie"]',
        '[id*="consent"]'
    ]
    
    def __init__(self, timeout: int = 10000, screenshot_on_failure: bool = True):
        self.timeout = timeout
        self.screenshot_on_failure = screenshot_on_failure
        
    async def detect_consent_dialog(self, page: Page) -> bool:
        """
        Checks for presence of consent dialogs.
        
        Args:
            page: Playwright page instance
            
        Returns:
            bool: True if consent dialog is detected
        """
        try:
            logger.debug("Detecting consent dialog...")
            
            for selector in self.DIALOG_SELECTORS:
                try:
                    element = await page.wait_for_selector(
                        selector, 
                        timeout=2000,  # Short timeout for each selector
                        state='visible'
                    )
                    if element:
                        logger.info(f"Consent dialog detected with selector: {selector}")
                        return True
                except PlaywrightTimeoutError:
                    continue
                    
            logger.debug("No consent dialog detected")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting consent dialog: {e}")
            return False
    
    async def handle_consent(self, page: Page) -> ConsentResult:
        """
        Attempts to accept cookies using known selectors.
        
        Args:
            page: Playwright page instance
            
        Returns:
            ConsentResult: Result of consent handling attempt
        """
        result = ConsentResult(success=False)
        
        try:
            logger.info("Attempting to handle cookie consent...")
            
            # First detect if dialog exists
            result.dialog_detected = await self.detect_consent_dialog(page)
            
            if not result.dialog_detected:
                logger.info("No consent dialog detected, proceeding...")
                result.success = True
                result.method_used = "no_dialog_detected"
                return result
            
            # Try each consent selector
            for i, selector in enumerate(self.CONSENT_SELECTORS):
                try:
                    logger.debug(f"Trying consent selector {i+1}/{len(self.CONSENT_SELECTORS)}: {selector}")
                    
                    # Wait for the button to be visible and clickable
                    button = await page.wait_for_selector(
                        selector,
                        timeout=2000,  # Short timeout per selector
                        state='visible'
                    )
                    
                    if button:
                        # Check if button is enabled
                        is_enabled = await button.is_enabled()
                        if not is_enabled:
                            logger.debug(f"Button found but disabled: {selector}")
                            continue
                        
                        # Click the consent button
                        await button.click()
                        logger.info(f"Successfully clicked consent button: {selector}")
                        
                        # Wait for dialog to disappear
                        await self.wait_for_consent_completion(page)
                        
                        result.success = True
                        result.method_used = selector
                        return result
                        
                except PlaywrightTimeoutError:
                    logger.debug(f"Selector not found: {selector}")
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If we get here, no consent button was found
            logger.warning("No clickable consent button found")
            result.error_message = "No clickable consent button found"
            
            # Take screenshot for debugging if enabled
            if self.screenshot_on_failure:
                result.screenshot_path = await self._take_debug_screenshot(page)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling consent: {e}")
            result.error_message = str(e)
            
            if self.screenshot_on_failure:
                result.screenshot_path = await self._take_debug_screenshot(page)
            
            return result
    
    async def wait_for_consent_completion(self, page: Page) -> None:
        """
        Waits for dialog dismissal after consent button click.
        
        Args:
            page: Playwright page instance
        """
        try:
            logger.debug("Waiting for consent dialog to disappear...")
            
            # Wait for any of the dialog selectors to become hidden
            for selector in self.DIALOG_SELECTORS:
                try:
                    await page.wait_for_selector(
                        selector,
                        timeout=3000,
                        state='hidden'
                    )
                    logger.debug(f"Dialog disappeared: {selector}")
                    break
                except PlaywrightTimeoutError:
                    continue
            
            # Additional wait for page to stabilize
            await page.wait_for_timeout(1000)
            logger.info("Consent handling completed")
            
        except Exception as e:
            logger.warning(f"Error waiting for consent completion: {e}")
    
    async def _take_debug_screenshot(self, page: Page) -> Optional[str]:
        """
        Takes a screenshot for debugging consent handling failures.
        
        Args:
            page: Playwright page instance
            
        Returns:
            Optional[str]: Path to screenshot file if successful
        """
        try:
            screenshot_dir = Path("debug_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            timestamp = asyncio.get_event_loop().time()
            screenshot_path = screenshot_dir / f"consent_failure_{timestamp}.png"
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Debug screenshot saved: {screenshot_path}")
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to take debug screenshot: {e}")
            return None