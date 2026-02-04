"""
Browser Automation Engine using Playwright.

Manages browser lifecycle, context creation, and provides core automation
capabilities with proper resource management and error handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import BrowserConfig


logger = logging.getLogger(__name__)


class BrowserAutomationEngine:
    """
    Manages Playwright browser lifecycle and provides core automation capabilities.
    
    Handles browser initialization, context creation, navigation, and proper
    resource cleanup with comprehensive error handling and logging.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._is_initialized = False
        
    async def initialize_browser(self) -> Browser:
        """
        Creates and configures browser instance.
        
        Returns:
            Browser: Configured Playwright browser instance
            
        Raises:
            RuntimeError: If browser initialization fails
        """
        try:
            logger.info("Initializing Playwright browser...")
            
            self.playwright = await async_playwright().start()
            
            # Launch browser with configuration
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            self._is_initialized = True
            logger.info(f"Browser initialized successfully (headless={self.config.headless})")
            
            return self.browser
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            await self.cleanup()
            raise RuntimeError(f"Browser initialization failed: {e}")
    
    async def create_context(self) -> BrowserContext:
        """
        Creates isolated browser context with appropriate settings.
        
        Returns:
            BrowserContext: Configured browser context
            
        Raises:
            RuntimeError: If context creation fails or browser not initialized
        """
        if not self._is_initialized or not self.browser:
            raise RuntimeError("Browser must be initialized before creating context")
            
        try:
            logger.debug("Creating browser context...")
            
            # Context configuration
            context_options = {
                'viewport': {
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                'user_agent': self.config.user_agent,
                'java_script_enabled': self.config.enable_javascript,
                'ignore_https_errors': True,
            }
            
            # Remove None values
            context_options = {k: v for k, v in context_options.items() if v is not None}
            
            self.context = await self.browser.new_context(**context_options)
            
            # Configure resource blocking for performance
            if self.config.block_images or self.config.block_fonts:
                await self._setup_resource_blocking()
            
            logger.debug("Browser context created successfully")
            return self.context
            
        except Exception as e:
            logger.error(f"Failed to create browser context: {e}")
            raise RuntimeError(f"Context creation failed: {e}")
    
    async def navigate_to_page(self, url: str) -> Page:
        """
        Navigates to target URL with proper error handling.
        
        Args:
            url: Target URL to navigate to
            
        Returns:
            Page: Playwright page instance
            
        Raises:
            RuntimeError: If navigation fails or context not created
        """
        if not self.context:
            raise RuntimeError("Browser context must be created before navigation")
            
        try:
            logger.info(f"Navigating to: {url}")
            
            page = await self.context.new_page()
            
            # Set timeouts
            page.set_default_timeout(self.config.timeout_element_wait)
            page.set_default_navigation_timeout(self.config.timeout_page_load)
            
            # Navigate to URL
            response = await page.goto(url, wait_until='domcontentloaded')
            
            if not response or response.status >= 400:
                raise RuntimeError(f"Navigation failed with status: {response.status if response else 'No response'}")
            
            logger.info(f"Successfully navigated to: {url}")
            return page
            
        except Exception as e:
            logger.error(f"Navigation to {url} failed: {e}")
            raise RuntimeError(f"Navigation failed: {e}")
    
    async def _setup_resource_blocking(self):
        """Set up resource blocking for improved performance."""
        if not self.context:
            return
            
        async def route_handler(route, request):
            resource_type = request.resource_type
            
            # Block images and fonts if configured
            if (self.config.block_images and resource_type == 'image') or \
               (self.config.block_fonts and resource_type == 'font'):
                await route.abort()
            else:
                await route.continue_()
        
        await self.context.route('**/*', route_handler)
        logger.debug("Resource blocking configured")
    
    async def cleanup(self) -> None:
        """
        Properly closes browser resources.
        
        Ensures all browser processes are terminated and resources
        are freed to prevent memory leaks and zombie processes.
        """
        logger.info("Cleaning up browser resources...")
        
        try:
            if self.context:
                await self.context.close()
                self.context = None
                logger.debug("Browser context closed")
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                logger.debug("Browser closed")
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                logger.debug("Playwright stopped")
                
            self._is_initialized = False
            logger.info("Browser cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
            # Force cleanup even if errors occur
            self.context = None
            self.browser = None
            self.playwright = None
            self._is_initialized = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_browser()
        await self.create_context()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    @property
    def is_initialized(self) -> bool:
        """Check if browser is properly initialized."""
        return self._is_initialized and self.browser is not None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get basic performance metrics.
        
        Returns:
            Dict containing performance information
        """
        return {
            'browser_initialized': self._is_initialized,
            'context_active': self.context is not None,
            'config': {
                'headless': self.config.headless,
                'viewport': f"{self.config.viewport_width}x{self.config.viewport_height}",
                'timeouts': {
                    'page_load': self.config.timeout_page_load,
                    'element_wait': self.config.timeout_element_wait
                }
            }
        }