"""
Core data models for the browser automation scraper.

These models maintain compatibility with the existing scraper while adding
new structures needed for browser automation and consent handling.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class MovieData:
    """
    Movie information extracted from the webpage.
    
    Maintains compatibility with existing scraper format while adding
    metadata for browser automation tracking.
    """
    title: Optional[str] = None
    screening_datetime: Optional[str] = None  # Keep existing field name for compatibility
    location: Optional[str] = None
    booking_url: Optional[str] = None
    movie_url: Optional[str] = None
    extracted_at: Optional[datetime] = None
    source_url: Optional[str] = None


@dataclass
class ConsentResult:
    """
    Result of cookie consent dialog handling.
    
    Tracks the success/failure of consent handling and provides
    debugging information for troubleshooting.
    """
    success: bool
    method_used: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    dialog_detected: bool = False
    timeout_occurred: bool = False


@dataclass
class ScrapingResult:
    """
    Complete result of a scraping operation.
    
    Aggregates all information from browser automation, consent handling,
    and content extraction for comprehensive logging and debugging.
    """
    success: bool
    movie_data: Optional[MovieData] = None
    consent_result: Optional[ConsentResult] = None
    extraction_errors: List[str] = None
    performance_metrics: Dict[str, float] = None
    browser_errors: List[str] = None
    
    def __post_init__(self):
        if self.extraction_errors is None:
            self.extraction_errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.browser_errors is None:
            self.browser_errors = []


@dataclass
class BrowserConfig:
    """
    Configuration for browser automation engine.
    
    Centralizes browser settings and provides defaults for
    headless operation and resource management.
    """
    headless: bool = True
    timeout_page_load: int = 30000  # milliseconds
    timeout_element_wait: int = 10000  # milliseconds
    user_agent: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    block_images: bool = True  # For performance
    block_fonts: bool = True   # For performance
    enable_javascript: bool = True
    
    
@dataclass
class ExtractionConfig:
    """
    Configuration for content extraction.
    
    Defines selectors and extraction strategies for different
    page elements and fallback behavior.
    """
    # CSS selectors for movie information
    title_selectors: List[str] = None
    datetime_selectors: List[str] = None
    location_selectors: List[str] = None
    booking_url_selectors: List[str] = None
    
    # Extraction timeouts and retries
    max_extraction_retries: int = 3
    extraction_timeout: int = 5000  # milliseconds
    screenshot_on_failure: bool = True
    
    def __post_init__(self):
        if self.title_selectors is None:
            self.title_selectors = [
                'h1',  # Main heading
                '.sidrubrik',
                '[class*="title"]',
                '[class*="heading"]'
            ]
        if self.datetime_selectors is None:
            self.datetime_selectors = [
                'time[datetime]',
                'strong:has-text("Tid:") + *',  # Text after "Tid:"
                '[class*="time"]',
                '[class*="date"]'
            ]
        if self.location_selectors is None:
            self.location_selectors = [
                'strong:has-text("Plats:") + *',  # Text after "Plats:"
                '[class*="location"]',
                '[class*="venue"]'
            ]
        if self.booking_url_selectors is None:
            self.booking_url_selectors = [
                'a:contains("Köp biljett")',
                'a:contains("Book")',
                '[class*="booking"]',
                '[href*="bio.se"]'
            ]