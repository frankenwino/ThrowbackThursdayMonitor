"""
Integration tests for browser automation with real website.

Tests the complete workflow of browser automation, consent handling,
and content extraction using the actual Borås Bio website.
"""

import pytest
import asyncio
from pathlib import Path

from src.models import BrowserConfig
from src.browser_automation.browser_engine import BrowserAutomationEngine
from src.browser_automation.consent_handler import CookieConsentHandler
from src.browser_automation.content_extractor import ContentExtractor


class TestBrowserIntegration:
    """Integration tests for browser automation components."""
    
    @pytest.fixture
    def test_url(self):
        """Provide test URL for integration tests."""
        return "https://www.boras.se/upplevaochgora/kulturochnoje/borasbiorodakvarn/throwbackthursday.4.706b03641584ebf5394d6c1a.html"
    
    @pytest.fixture
    def browser_config(self):
        """Provide browser configuration for testing."""
        return BrowserConfig(
            headless=True,
            timeout_page_load=30000,
            timeout_element_wait=10000
        )
    
    @pytest.mark.asyncio
    async def test_browser_initialization_and_cleanup(self, browser_config):
        """Test browser can be initialized and cleaned up properly."""
        engine = BrowserAutomationEngine(browser_config)
        
        # Test initialization
        browser = await engine.initialize_browser()
        assert browser is not None
        assert engine.is_initialized
        
        # Test context creation
        context = await engine.create_context()
        assert context is not None
        assert engine.context is not None
        
        # Test cleanup
        await engine.cleanup()
        assert not engine.is_initialized
        assert engine.browser is None
        assert engine.context is None
    
    @pytest.mark.asyncio
    async def test_consent_handler_detection(self, test_url, browser_config):
        """Test consent handler can detect and handle cookie dialogs."""
        async with BrowserAutomationEngine(browser_config) as engine:
            page = await engine.navigate_to_page(test_url)
            
            consent_handler = CookieConsentHandler(timeout=10000)
            
            # Test consent detection
            dialog_detected = await consent_handler.detect_consent_dialog(page)
            
            # The website should have a consent dialog
            assert dialog_detected, "Expected to detect consent dialog on Borås website"
            
            # Test consent handling
            result = await consent_handler.handle_consent(page)
            
            # Should successfully handle consent or at least detect the dialog
            assert result.dialog_detected, "Should detect consent dialog"
            # The success depends on whether the button click worked
            print(f"Consent handling success: {result.success}")
            print(f"Method used: {result.method_used}")
            print(f"Error message: {result.error_message}")
    
    @pytest.mark.asyncio
    async def test_content_extraction_after_consent(self, test_url, browser_config):
        """Test content extraction works after handling consent."""
        async with BrowserAutomationEngine(browser_config) as engine:
            page = await engine.navigate_to_page(test_url)
            
            # Handle consent first
            consent_handler = CookieConsentHandler()
            consent_result = await consent_handler.handle_consent(page)
            
            # Extract content
            extractor = ContentExtractor()
            await extractor.wait_for_content_load(page)
            
            movie_data = await extractor.extract_movie_data(page)
            
            # Validate extracted data
            assert movie_data is not None
            assert movie_data.source_url == test_url
            assert movie_data.extracted_at is not None
            
            # At least some data should be extracted
            extracted_fields = [
                movie_data.title,
                movie_data.screening_datetime,
                movie_data.location,
                movie_data.booking_url
            ]
            
            non_empty_fields = [field for field in extracted_fields if field]
            assert len(non_empty_fields) > 0, "Should extract at least one field"
            
            # Log what was extracted for debugging
            print(f"Extracted title: {movie_data.title}")
            print(f"Extracted datetime: {movie_data.screening_datetime}")
            print(f"Extracted location: {movie_data.location}")
            print(f"Extracted booking URL: {movie_data.booking_url}")
    
    @pytest.mark.asyncio
    async def test_full_scraping_workflow(self, test_url, browser_config):
        """Test the complete scraping workflow from start to finish."""
        async with BrowserAutomationEngine(browser_config) as engine:
            # Navigate to page
            page = await engine.navigate_to_page(test_url)
            assert page.url == test_url
            
            # Handle consent
            consent_handler = CookieConsentHandler()
            consent_result = await consent_handler.handle_consent(page)
            
            # Wait for content to load
            extractor = ContentExtractor()
            await extractor.wait_for_content_load(page)
            
            # Extract movie data
            movie_data = await extractor.extract_movie_data(page)
            
            # Validate results
            validation_result = await extractor.validate_extracted_data(movie_data)
            
            # The workflow should complete without errors
            assert movie_data is not None
            assert validation_result is not None
            
            # Print results for manual verification
            print(f"Consent handling: {consent_result.success}")
            print(f"Data validation: {validation_result['is_valid']}")
            print(f"Missing fields: {validation_result['missing_fields']}")
            print(f"Warnings: {validation_result['warnings']}")
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_url(self, browser_config):
        """Test error handling with invalid URL."""
        async with BrowserAutomationEngine(browser_config) as engine:
            with pytest.raises(RuntimeError):
                await engine.navigate_to_page("https://invalid-url-that-does-not-exist.com")
    
    @pytest.mark.asyncio 
    async def test_context_manager_cleanup_on_error(self, browser_config):
        """Test that context manager properly cleans up even when errors occur."""
        try:
            async with BrowserAutomationEngine(browser_config) as engine:
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected error
        
        # Engine should still be cleaned up
        assert not engine.is_initialized