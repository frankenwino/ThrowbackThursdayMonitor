"""
Browser-based web scraper that replaces the aiohttp-based checker.

Maintains full compatibility with the existing WebChecker interface while
using Playwright for browser automation to handle cookie consent dialogs
and JavaScript-rendered content.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json
import aiofiles

from models import BrowserConfig, MovieData, ScrapingResult
from browser_automation import BrowserAutomationEngine, CookieConsentHandler, ContentExtractor
from discord_notifier import DiscordNotifier
from discord_webhook import DiscordEmbed


logger = logging.getLogger(__name__)


class BrowserWebChecker:
    """
    Browser-based web scraper that maintains compatibility with existing WebChecker.
    
    Replaces aiohttp with Playwright browser automation to handle modern web
    interactions while preserving the exact same interface and database format.
    """
    
    def __init__(self, url: str, db_file_path: Path, headless: bool = True):
        self.url = url
        self.db_file_path = db_file_path
        self.notifier = DiscordNotifier()
        
        # Browser automation components
        self.browser_config = BrowserConfig(headless=headless)
        self.browser_engine = BrowserAutomationEngine(self.browser_config)
        self.consent_handler = CookieConsentHandler()
        self.content_extractor = ContentExtractor()
        
    async def go(self) -> None:
        """
        Main method to check for updates, extract movie information, and update the database.
        
        Maintains exact compatibility with the original WebChecker.go() method.
        """
        try:
            logger.info(f"Starting browser-based scraping of {self.url}")
            
            # Initialize browser automation
            await self.browser_engine.initialize_browser()
            await self.browser_engine.create_context()
            
            # Navigate to the main page
            page = await self.browser_engine.navigate_to_page(self.url)
            
            # Handle cookie consent
            consent_result = await self.consent_handler.handle_consent(page)
            logger.info(f"Consent handling: {consent_result.success}")
            
            # Wait for content to load
            await self.content_extractor.wait_for_content_load(page)
            
            # Extract site last changed date (for compatibility)
            site_last_changed_date = await self._get_site_last_changed_date(page)
            db_last_changed_date = await self.get_db_last_changed_date()
            
            # Check if we need to update (same logic as original)
            if db_last_changed_date is None or (site_last_changed_date and site_last_changed_date > db_last_changed_date):
                logger.info("Site has changed, extracting movie information...")
                
                # Get movie URL from the main page
                movie_url = await self._get_movie_url(page)
                
                if movie_url:
                    # Navigate to the movie detail page
                    movie_page = await self.browser_engine.navigate_to_page(movie_url)
                    
                    # Handle consent on movie page if needed
                    await self.consent_handler.handle_consent(movie_page)
                    await self.content_extractor.wait_for_content_load(movie_page)
                    
                    # Extract movie data
                    movie_data = await self.content_extractor.extract_movie_data(movie_page)
                    
                    # Convert to legacy format for compatibility
                    legacy_data = self._convert_to_legacy_format(movie_data)
                    
                    # Print extracted data (same as original)
                    if legacy_data.get('title'):
                        print(f"Movie title: {legacy_data['title']}")
                    if legacy_data.get('screening_datetime'):
                        print(f"Screening time: {legacy_data['screening_datetime']}")
                    if legacy_data.get('location'):
                        print(f"Location: {legacy_data['location']}")
                    if legacy_data.get('booking_url'):
                        print(f"Booking URL: {legacy_data['booking_url']}")
                    
                    # Update database (same format as original)
                    json_data = await self.open_db_file()
                    json_data['last_changed_date'] = site_last_changed_date
                    json_data['latest_movie_data'] = legacy_data
                    await self.write_db_file(json_data)
                    
                    # Send Discord notification (same as original)
                    if all(legacy_data.get(field) for field in ['title', 'screening_datetime', 'location', 'booking_url']):
                        embed = self.generate_embed(
                            legacy_data['title'],
                            legacy_data['screening_datetime'],
                            legacy_data['location'],
                            legacy_data['movie_url'],
                            legacy_data['booking_url']
                        )
                        self.notifier.send_embed(embed)
                    else:
                        logger.warning("Incomplete movie data, skipping notification")
                else:
                    logger.warning("Could not find movie URL on main page")
            else:
                print("Site has not changed")
                
        except Exception as e:
            error_msg = f"An error occurred in {Path(__file__).parts[-3]}/{Path(__file__).parts[-2]}/{Path(__file__).name}:\n**{type(e).__name__}**: {e}"
            logger.error(error_msg)
            self.notifier.send_message(error_msg)
        finally:
            # Always cleanup browser resources
            await self.browser_engine.cleanup()
    
    async def _get_site_last_changed_date(self, page) -> Optional[str]:
        """Extract the last changed date from the page (compatibility method)."""
        try:
            # Look for the same element as original scraper
            element = await page.wait_for_selector('.sv-font-uppdaterad-info-ny time[datetime]', timeout=5000)
            if element:
                datetime_attr = await element.get_attribute('datetime')
                return datetime_attr
        except Exception as e:
            logger.debug(f"Could not extract last changed date: {e}")
        
        # Fallback: use current timestamp
        return datetime.now().isoformat()
    
    async def _get_movie_url(self, page) -> Optional[str]:
        """Extract movie URL from the main page (compatibility method)."""
        try:
            # Look for the same element as original scraper
            element = await page.wait_for_selector('.sv-channel-item a[href]', timeout=5000)
            if element:
                href = await element.get_attribute('href')
                if href:
                    # Convert relative URL to absolute
                    if href.startswith('/'):
                        base_url = f"{page.url.split('/')[0]}//{page.url.split('/')[2]}"
                        return base_url + href
                    elif not href.startswith('http'):
                        base_url = '/'.join(page.url.split('/')[:-1])
                        return base_url + '/' + href
                    return href
        except Exception as e:
            logger.debug(f"Could not extract movie URL: {e}")
        
        return None
    
    def _convert_to_legacy_format(self, movie_data: MovieData) -> Dict[str, Any]:
        """Convert MovieData to legacy format for database compatibility."""
        return {
            'title': movie_data.title,
            'screening_datetime': movie_data.screening_datetime,
            'location': movie_data.location,
            'booking_url': movie_data.booking_url,
            'movie_url': movie_data.movie_url or movie_data.source_url
        }
    
    # Legacy compatibility methods (exact same as original WebChecker)
    
    async def get_db_last_changed_date(self) -> Optional[str]:
        """Retrieves the last changed date from the JSON database file."""
        json_data = await self.open_db_file()
        return json_data.get('last_changed_date')
    
    async def open_db_file(self) -> Dict[str, Any]:
        """Opens and reads the JSON database file."""
        try:
            async with aiofiles.open(self.db_file_path, 'r') as file:
                content = await file.read()
                return json.loads(content)
        except FileNotFoundError:
            return {}
    
    async def write_db_file(self, data: Dict[str, Any]) -> None:
        """Writes data to the JSON database file."""
        json_data = json.dumps(data, indent=2)
        async with aiofiles.open(self.db_file_path, 'w') as f:
            await f.write(json_data)
    
    def generate_embed(self, movie_title: str, screening_datetime: str, screening_location: str, movie_url: str, booking_url: str) -> DiscordEmbed:
        """Generate Discord embed (exact same as original)."""
        return DiscordEmbed(
            title=f"New Screening: {movie_title}",
            description=(
                f"**When:** {screening_datetime}\n"
                f"**Where:** {screening_location}\n"
                f"**Details:** [View More]({movie_url})\n"
                f"**Book here:** [Click to Book]({booking_url})"
            ),
            color=0x00FF00  # Optional: Set an embed color (hex code)
        )


# Backward compatibility alias
WebChecker = BrowserWebChecker