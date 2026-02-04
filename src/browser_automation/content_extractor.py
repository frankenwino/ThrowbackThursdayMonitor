"""
Content Extractor for browser automation.

Extracts movie information from JavaScript-rendered pages using robust
waiting strategies and fallback selectors for reliable data extraction.
"""

import asyncio
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import MovieData, ExtractionConfig


logger = logging.getLogger(__name__)


class ContentExtractor:
    """
    Extracts movie information from JavaScript-rendered pages.
    
    Uses Playwright's robust element waiting mechanisms and implements
    fallback selectors for reliable data extraction across different
    page layouts and content management systems.
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        
    async def wait_for_content_load(self, page: Page) -> None:
        """
        Waits for dynamic content to fully render.
        
        Args:
            page: Playwright page instance
        """
        try:
            logger.debug("Waiting for content to load...")
            
            # Wait for network to be idle (no requests for 500ms)
            await page.wait_for_load_state('networkidle', timeout=self.config.extraction_timeout)
            
            # Additional wait for JavaScript to complete
            await page.wait_for_timeout(2000)
            
            logger.debug("Content loading completed")
            
        except Exception as e:
            logger.warning(f"Content loading wait failed: {e}")
    
    async def extract_movie_data(self, page: Page) -> MovieData:
        """
        Extracts all required movie information from the page.
        
        Args:
            page: Playwright page instance
            
        Returns:
            MovieData: Extracted movie information
        """
        logger.info("Starting movie data extraction...")
        
        movie_data = MovieData(
            extracted_at=datetime.now(),
            source_url=page.url
        )
        
        # Extract each field with error handling
        movie_data.title = await self._extract_movie_title(page)
        movie_data.screening_datetime = await self._extract_screening_datetime(page)
        movie_data.location = await self._extract_location(page)
        movie_data.booking_url = await self._extract_booking_url(page)
        movie_data.movie_url = page.url
        
        logger.info(f"Movie data extraction completed: {movie_data.title}")
        return movie_data
    
    async def _extract_movie_title(self, page: Page) -> Optional[str]:
        """Extract movie title using multiple selector strategies."""
        logger.debug("Extracting movie title...")
        
        for selector in self.config.title_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    text = await element.text_content()
                    if text:
                        title = self._clean_movie_title(text.strip())
                        if title:
                            logger.info(f"Movie title extracted: {title}")
                            return title
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Error with title selector {selector}: {e}")
                continue
        
        logger.warning("Could not extract movie title")
        return None
    
    def _clean_movie_title(self, raw_title: str) -> Optional[str]:
        """
        Clean and extract movie title from raw text.
        
        Handles various title formats like:
        - "Throwback Thursday: Title (Year)"
        - "Title" in quotes
        - Plain title text
        """
        if not raw_title:
            return None
        
        # First try to find title in quotes (original format)
        quote_match = re.search(r'"(.*?)"', raw_title)
        if quote_match:
            return quote_match.group(1)
        
        # New format: "Throwback Thursday: Title (Year)"
        throwback_match = re.search(r'Throwback Thursday:\s*(.+?)\s*\(\d{4}\)', raw_title)
        if throwback_match:
            return throwback_match.group(1).strip()
        
        # Fallback: if it contains "Throwback Thursday:" but no year
        if 'Throwback Thursday:' in raw_title:
            parts = raw_title.split('Throwback Thursday:', 1)
            if len(parts) > 1:
                title = parts[1].strip()
                # Remove year in parentheses if present
                title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
                return title.strip()
        
        # Return cleaned raw title as fallback
        return raw_title.strip()
    
    async def _extract_screening_datetime(self, page: Page) -> Optional[str]:
        """Extract screening date and time."""
        logger.debug("Extracting screening datetime...")
        
        # Try to find time element with datetime attribute first
        try:
            time_element = await page.wait_for_selector('time[datetime]', timeout=3000)
            if time_element:
                datetime_attr = await time_element.get_attribute('datetime')
                if datetime_attr:
                    # Parse and format the datetime
                    try:
                        dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        logger.info(f"Screening datetime extracted: {formatted_time}")
                        return formatted_time
                    except ValueError as e:
                        logger.debug(f"Error parsing datetime: {e}")
        except PlaywrightTimeoutError:
            pass
        
        # Try to find "Tid:" followed by text
        try:
            # Look for "Tid:" text and get the next text content
            tid_elements = await page.query_selector_all('text="Tid:"')
            for tid_element in tid_elements:
                # Get parent element and look for time info
                parent = await tid_element.evaluate('el => el.parentElement')
                if parent:
                    parent_text = await page.evaluate('el => el.textContent', parent)
                    if parent_text:
                        # Extract datetime from the parent text
                        datetime_text = self._extract_datetime_from_text(parent_text)
                        if datetime_text:
                            logger.info(f"Screening datetime extracted from Tid: {datetime_text}")
                            return datetime_text
        except Exception as e:
            logger.debug(f"Error extracting from Tid: {e}")
        
        # Try to find text that looks like "2026-02-26 19.00"
        try:
            page_content = await page.content()
            datetime_text = self._extract_datetime_from_text(page_content)
            if datetime_text:
                logger.info(f"Screening datetime extracted from page content: {datetime_text}")
                return datetime_text
        except Exception as e:
            logger.debug(f"Error extracting from page content: {e}")
        
        logger.warning("Could not extract screening datetime")
        return None
    
    def _extract_datetime_from_text(self, text: str) -> Optional[str]:
        """Extract datetime from text using regex patterns."""
        if not text:
            return None
        
        # Pattern for "2026-02-26 19.00" format (what we saw in the page)
        iso_time_pattern = r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2})\.(\d{2})'
        match = re.search(iso_time_pattern, text)
        if match:
            date_part, hour, minute = match.groups()
            return f"{date_part} {hour.zfill(2)}:{minute}"
        
        # Pattern for "26 februari 19.00" or similar
        swedish_pattern = r'(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+(\d{1,2})\.(\d{2})'
        match = re.search(swedish_pattern, text.lower())
        if match:
            day, month_name, hour, minute = match.groups()
            
            # Convert Swedish month names to numbers
            month_map = {
                'januari': '01', 'februari': '02', 'mars': '03', 'april': '04',
                'maj': '05', 'juni': '06', 'juli': '07', 'augusti': '08',
                'september': '09', 'oktober': '10', 'november': '11', 'december': '12'
            }
            
            month = month_map.get(month_name, '01')
            year = datetime.now().year  # Assume current year
            
            return f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute}"
        
        return None
    
    async def _extract_location(self, page: Page) -> Optional[str]:
        """Extract screening location."""
        logger.debug("Extracting location...")
        
        # Try to find "Plats:" followed by text
        try:
            # Look for text containing "Plats:" and extract what follows
            page_content = await page.content()
            plats_match = re.search(r'Plats:\s*([^<\n]+)', page_content)
            if plats_match:
                location = plats_match.group(1).strip()
                if location:
                    logger.info(f"Location extracted from Plats: {location}")
                    return location
        except Exception as e:
            logger.debug(f"Error extracting from Plats: {e}")
        
        # Fallback to default location for this venue
        default_location = "Borås Bio Röda Kvarn"
        logger.info(f"Using default location: {default_location}")
        return default_location
    
    def _clean_location_text(self, text: str) -> Optional[str]:
        """Clean location text by removing labels and extra whitespace."""
        if not text:
            return None
        
        # Remove common labels
        text = re.sub(r'^(Plats:|Location:|Venue:)\s*', '', text, flags=re.IGNORECASE)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text if text else None
    
    async def _extract_booking_url(self, page: Page) -> Optional[str]:
        """Extract booking URL."""
        logger.debug("Extracting booking URL...")
        
        for selector in self.config.booking_url_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element:
                    href = await element.get_attribute('href')
                    if href:
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            base_url = f"{page.url.split('/')[0]}//{page.url.split('/')[2]}"
                            href = base_url + href
                        elif not href.startswith('http'):
                            base_url = '/'.join(page.url.split('/')[:-1])
                            href = base_url + '/' + href
                        
                        logger.info(f"Booking URL extracted: {href}")
                        return href
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Error with booking URL selector {selector}: {e}")
                continue
        
        logger.warning("Could not extract booking URL")
        return None
    
    async def validate_extracted_data(self, data: MovieData) -> Dict[str, Any]:
        """
        Validates extracted data and returns validation results.
        
        Args:
            data: MovieData instance to validate
            
        Returns:
            Dict containing validation results
        """
        validation_result = {
            'is_valid': True,
            'missing_fields': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['title', 'screening_datetime', 'location', 'booking_url']
        for field in required_fields:
            if not getattr(data, field):
                validation_result['missing_fields'].append(field)
                validation_result['is_valid'] = False
        
        # Check data quality
        if data.title and len(data.title) < 2:
            validation_result['warnings'].append('Title seems too short')
        
        if data.booking_url and not data.booking_url.startswith('http'):
            validation_result['warnings'].append('Booking URL may be malformed')
        
        logger.info(f"Data validation completed: {validation_result}")
        return validation_result
    
    async def take_extraction_screenshot(self, page: Page, reason: str = "extraction_debug") -> Optional[str]:
        """
        Takes a screenshot for debugging extraction failures.
        
        Args:
            page: Playwright page instance
            reason: Reason for taking screenshot
            
        Returns:
            Optional[str]: Path to screenshot file if successful
        """
        try:
            screenshot_dir = Path("debug_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            timestamp = int(asyncio.get_event_loop().time())
            screenshot_path = screenshot_dir / f"{reason}_{timestamp}.png"
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Extraction screenshot saved: {screenshot_path}")
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to take extraction screenshot: {e}")
            return None