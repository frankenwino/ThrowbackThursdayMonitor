"""
Browser-based web scraper for the Throwback Thursday page.

All data (title, date/time, booking URL, movie detail URL) is extracted
directly from the main listing page — no second navigation required.

Maintains full compatibility with the existing WebChecker interface and
db.json database format.
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
    Browser-based scraper for the Throwback Thursday page.

    Navigates to the main page once, handles the cookie consent dialog,
    then extracts all movie data (title, datetime, booking URL, detail URL)
    directly from the listing — no sub-page navigation needed.
    """

    def __init__(self, url: str, db_file_path: Path, headless: bool = True):
        self.url = url
        self.db_file_path = db_file_path
        self.notifier = DiscordNotifier()

        self.browser_config = BrowserConfig(headless=headless)
        self.browser_engine = BrowserAutomationEngine(self.browser_config)
        self.consent_handler = CookieConsentHandler()
        self.content_extractor = ContentExtractor()

    async def go(self) -> None:
        """
        Main entry point: check for updates, extract movie data, notify on change.

        Flow:
          1. Open the main Throwback Thursday page
          2. Accept the cookie consent dialog
          3. Extract the "Senast ändrad" date and compare with stored value
          4. If changed (or first run): extract movie data and send Discord notification
          5. Always clean up the browser
        """
        try:
            logger.info(f"Starting scrape of {self.url}")

            await self.browser_engine.initialize_browser()
            await self.browser_engine.create_context()

            page = await self.browser_engine.navigate_to_page(self.url)

            # Handle cookie consent
            consent_result = await self.consent_handler.handle_consent(page)
            logger.info(f"Consent handling: success={consent_result.success}, "
                        f"method={consent_result.method_used!r}")

            # Wait for the listing to be present
            await self.content_extractor.wait_for_content_load(page)

            # Compare "last changed" dates
            site_last_changed = await self.content_extractor.extract_last_changed_date(page)
            db_last_changed = await self.get_db_last_changed_date()

            logger.info(f"Site last changed: {site_last_changed}")
            logger.info(f"DB last changed:   {db_last_changed}")

            if db_last_changed is None or (
                site_last_changed and site_last_changed > db_last_changed[:19]
            ):
                logger.info("Change detected — extracting movie data...")

                # Extract everything from the main page (no sub-page needed)
                movie_data = await self.content_extractor.extract_movie_data(page)
                legacy = self._to_legacy_format(movie_data)

                # Log what we found
                for field in ('title', 'screening_datetime', 'location', 'booking_url'):
                    if legacy.get(field):
                        print(f"{field.replace('_', ' ').title()}: {legacy[field]}")

                # Persist to db.json
                db = await self.open_db_file()
                db['last_changed_date'] = site_last_changed
                db['latest_movie_data'] = legacy
                await self.write_db_file(db)

                # Send Discord notification if we have all required fields
                required = ('title', 'screening_datetime', 'location', 'booking_url')
                if all(legacy.get(f) for f in required):
                    embed = self.generate_embed(
                        legacy['title'],
                        legacy['screening_datetime'],
                        legacy['location'],
                        legacy.get('movie_url', self.url),
                        legacy['booking_url'],
                    )
                    self.notifier.send_embed(embed)
                    logger.info("Discord notification sent")
                else:
                    missing = [f for f in required if not legacy.get(f)]
                    logger.warning(f"Incomplete data — skipping notification. Missing: {missing}")
            else:
                print("Site has not changed")

        except Exception as e:
            error_msg = (
                f"An error occurred in "
                f"{Path(__file__).parts[-2]}/{Path(__file__).name}:\n"
                f"**{type(e).__name__}**: {e}"
            )
            logger.error(error_msg)
            self.notifier.send_message(error_msg)

        finally:
            await self.browser_engine.cleanup()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _to_legacy_format(self, movie_data: MovieData) -> Dict[str, Any]:
        """Convert MovieData to the flat dict format stored in db.json."""
        return {
            'title': movie_data.title,
            'screening_datetime': movie_data.screening_datetime,
            'location': movie_data.location,
            'booking_url': movie_data.booking_url,
            'movie_url': movie_data.movie_url or self.url,
        }

    # ------------------------------------------------------------------
    # DB helpers (unchanged interface)
    # ------------------------------------------------------------------

    async def get_db_last_changed_date(self) -> Optional[str]:
        """Return the last_changed_date stored in db.json, or None."""
        db = await self.open_db_file()
        return db.get('last_changed_date')

    async def open_db_file(self) -> Dict[str, Any]:
        """Read db.json; return empty dict if file doesn't exist yet."""
        try:
            async with aiofiles.open(self.db_file_path, 'r') as f:
                return json.loads(await f.read())
        except FileNotFoundError:
            return {}

    async def write_db_file(self, data: Dict[str, Any]) -> None:
        """Write data to db.json."""
        async with aiofiles.open(self.db_file_path, 'w') as f:
            await f.write(json.dumps(data, indent=2))

    def generate_embed(
        self,
        movie_title: str,
        screening_datetime: str,
        screening_location: str,
        movie_url: str,
        booking_url: str,
    ) -> DiscordEmbed:
        """Generate a Discord embed for the new screening."""
        return DiscordEmbed(
            title=f"New Screening: {movie_title}",
            description=(
                f"**When:** {screening_datetime}\n"
                f"**Where:** {screening_location}\n"
                f"**Details:** [View More]({movie_url})\n"
                f"**Book here:** [Click to Book]({booking_url})"
            ),
            color=0x00FF00,
        )


# Backward compatibility alias
WebChecker = BrowserWebChecker
