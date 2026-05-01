"""
Content Extractor for the Throwback Thursday page.

All data (title, date/time, booking URL, movie detail URL) lives in the
listing on the main page — no second navigation needed.

Page structure (from live inspection):
  <ul>
    <li>
      <time>28 maj 19.00</time>          ← screening date/time (text, no datetime attr)
      <a href="/...">Throwback Thursday: "Stand by Me" ...</a>  ← title + movie URL
      ...
      <a href="https://bio.se/...">Köp biljett ...</a>          ← booking URL
    </li>
    ...  (may be multiple upcoming screenings)
  </ul>

The "Senast ändrad" (last changed) date is in:
  <strong>Senast ändrad:</strong> <time>19 december, 2025</time>
  — text content only, no datetime attribute.
"""

import logging
import re
from typing import Optional
from datetime import datetime

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import MovieData, ExtractionConfig


logger = logging.getLogger(__name__)

# Swedish month name → zero-padded month number
SWEDISH_MONTHS = {
    'januari': '01', 'februari': '02', 'mars': '03', 'april': '04',
    'maj': '05', 'juni': '06', 'juli': '07', 'augusti': '08',
    'september': '09', 'oktober': '10', 'november': '11', 'december': '12',
}


class ContentExtractor:
    """
    Extracts movie information directly from the Throwback Thursday listing page.

    All required data is present on the main page inside a <ul> listing.
    Each <li> represents one upcoming screening and contains:
      - A <time> element with the date/time as text (e.g. "28 maj 19.00")
      - A link to the movie detail page (title is the link text)
      - A "Köp biljett" link pointing to bio.se (booking URL)

    The first <li> is used (next upcoming screening).
    """

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def wait_for_content_load(self, page: Page) -> None:
        """Wait for the page listing to be present in the DOM."""
        try:
            # The listing is server-rendered so domcontentloaded is enough,
            # but we wait for the first <li> in the main content area to be safe.
            await page.wait_for_selector('main li', timeout=10000)
            logger.debug("Content loaded — listing <li> elements found")
        except PlaywrightTimeoutError:
            logger.warning("Timed out waiting for listing <li>; proceeding anyway")

    async def extract_movie_data(self, page: Page) -> MovieData:
        """
        Extract all movie data from the first listing item on the main page.

        Returns a MovieData instance. Fields that cannot be extracted are None.
        """
        logger.info("Extracting movie data from main page listing...")

        movie_data = MovieData(
            extracted_at=datetime.now(),
            source_url=page.url,
        )

        # Find all <li> elements in the main content listing
        # The listing sits inside the main content area; we target the
        # first <li> that contains a <time> element (the screening entry).
        listing_items = await page.query_selector_all('main li')

        target_li = None
        for li in listing_items:
            time_el = await li.query_selector('time')
            if time_el:
                target_li = li
                break

        if not target_li:
            logger.error("No listing <li> with a <time> element found on page")
            return movie_data

        # --- Title & movie detail URL ---
        movie_data.title, movie_data.movie_url = await self._extract_title_and_url(
            target_li, page
        )

        # --- Screening date/time ---
        movie_data.screening_datetime = await self._extract_screening_datetime(target_li)

        # --- Booking URL ---
        movie_data.booking_url = await self._extract_booking_url(target_li)

        # --- Location (hardcoded — always the same venue) ---
        movie_data.location = "Borås Bio Röda Kvarn"

        logger.info(
            f"Extraction complete — title={movie_data.title!r}, "
            f"datetime={movie_data.screening_datetime!r}, "
            f"booking={movie_data.booking_url!r}"
        )
        return movie_data

    async def extract_last_changed_date(self, page: Page) -> Optional[str]:
        """
        Extract the 'Senast ändrad' (last changed) date from the page footer.

        The element is:
          <strong>Senast ändrad:</strong> <time>19 december, 2025</time>

        Returns an ISO-format date string (YYYY-MM-DD) or None.
        """
        try:
            # Find the <time> element that immediately follows "Senast ändrad:"
            time_el = await page.query_selector('strong:has-text("Senast ändrad") + time, '
                                                 'strong:has-text("Senast ändrad:") ~ time')
            if not time_el:
                # Broader fallback: find any <time> in the page footer area
                time_el = await page.query_selector('.sv-font-uppdaterad-info-ny time')

            if time_el:
                # Try datetime attribute first (may not be present)
                dt_attr = await time_el.get_attribute('datetime')
                if dt_attr:
                    return dt_attr

                # Fall back to text content: "19 december, 2025"
                text = await time_el.text_content()
                if text:
                    parsed = self._parse_swedish_date(text.strip())
                    if parsed:
                        return parsed

        except Exception as e:
            logger.debug(f"Could not extract last changed date: {e}")

        # Final fallback: use current timestamp so we always have a value
        return datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _extract_title_and_url(self, li, page: Page):
        """
        Extract the movie title and detail URL from the first non-booking link in the <li>.

        The title link text looks like:
          'Throwback Thursday: "Stand by Me" 40-årsjubileum (1986)'
        """
        title = None
        movie_url = None

        try:
            # All <a> elements in the <li>
            links = await li.query_selector_all('a[href]')
            for link in links:
                href = await link.get_attribute('href')
                text = await link.text_content()

                if not href or not text:
                    continue

                # Skip the booking link (points to bio.se or contains "Köp")
                if 'bio.se' in href or 'köp' in text.lower() or 'biljett' in text.lower():
                    continue

                # Skip venue/location links
                if 'borasbiorodakvarn' in href and 'throwback' not in href:
                    continue

                raw_title = text.strip()
                title = self._clean_title(raw_title)

                # Build absolute URL
                if href.startswith('/'):
                    base = f"{page.url.split('/')[0]}//{page.url.split('/')[2]}"
                    movie_url = base + href
                elif href.startswith('http'):
                    movie_url = href
                else:
                    movie_url = '/'.join(page.url.split('/')[:-1]) + '/' + href

                logger.debug(f"Title link found: {title!r} → {movie_url}")
                break

        except Exception as e:
            logger.warning(f"Error extracting title/URL: {e}")

        return title, movie_url

    async def _extract_screening_datetime(self, li) -> Optional[str]:
        """
        Extract screening date/time from the <time> element inside the <li>.

        The text content is like "28 maj 19.00" — no datetime attribute.
        Returns a normalised string like "2026-05-28 19:00".
        """
        try:
            time_el = await li.query_selector('time')
            if time_el:
                # Try datetime attribute first
                dt_attr = await time_el.get_attribute('datetime')
                if dt_attr:
                    try:
                        dt = datetime.fromisoformat(dt_attr.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        pass

                # Parse text content: "28 maj 19.00"
                text = await time_el.text_content()
                if text:
                    parsed = self._parse_swedish_datetime(text.strip())
                    if parsed:
                        return parsed

        except Exception as e:
            logger.warning(f"Error extracting screening datetime: {e}")

        return None

    async def _extract_booking_url(self, li) -> Optional[str]:
        """
        Extract the booking URL — the link to bio.se or the "Köp biljett" link.
        """
        try:
            links = await li.query_selector_all('a[href]')
            for link in links:
                href = await link.get_attribute('href')
                text = (await link.text_content() or '').lower()

                if not href:
                    continue

                if 'bio.se' in href or 'köp' in text or 'biljett' in text:
                    logger.debug(f"Booking URL found: {href}")
                    return href

        except Exception as e:
            logger.warning(f"Error extracting booking URL: {e}")

        return None

    def _clean_title(self, raw: str) -> Optional[str]:
        """
        Clean the raw link text into a plain movie title.

        Handles formats like:
          'Throwback Thursday: "Stand by Me" 40-årsjubileum (1986)'
          'Throwback Thursday: Dirty Harry (1971)'
          '"Dirty Harry"'
        """
        if not raw:
            return None

        # Strip leading/trailing whitespace and normalise internal spaces
        text = re.sub(r'\s+', ' ', raw).strip()

        # Remove "Throwback Thursday: " prefix
        text = re.sub(r'^Throwback Thursday:\s*', '', text, flags=re.IGNORECASE).strip()

        # Remove anniversary/jubileum suffixes like "40-årsjubileum"
        text = re.sub(r'\s+\d+-årsjubileum', '', text, flags=re.IGNORECASE).strip()

        # Extract year in parentheses if present, then remove it from title
        year_match = re.search(r'\((\d{4})\)', text)
        year = year_match.group(1) if year_match else None
        text = re.sub(r'\s*\(\d{4}\)\s*', '', text).strip()

        # Strip surrounding quotes from title
        text = text.strip('"').strip("'").strip()

        if year and text:
            return f"{text} ({year})"
        return text or None

    def _parse_swedish_datetime(self, text: str) -> Optional[str]:
        """
        Parse a Swedish date/time string like "28 maj 19.00" into "YYYY-MM-DD HH:MM".

        Assumes the current or next year when no year is present.
        """
        # Pattern: "28 maj 19.00" or "28 maj kl. 19.00" or "28 maj kl 19.00"
        pattern = r'(\d{1,2})\s+([a-zåäö]+)(?:\s+kl\.?\s*)?(\d{1,2})[.:](\d{2})'
        match = re.search(pattern, text.lower())
        if not match:
            return None

        day, month_name, hour, minute = match.groups()
        month = SWEDISH_MONTHS.get(month_name)
        if not month:
            return None

        # Pick the year: if the date has already passed this year, use next year
        now = datetime.now()
        year = now.year
        try:
            candidate = datetime(year, int(month), int(day))
            if candidate < now:
                year += 1
        except ValueError:
            pass

        return f"{year}-{month}-{day.zfill(2)} {hour.zfill(2)}:{minute}"

    def _parse_swedish_date(self, text: str) -> Optional[str]:
        """
        Parse a Swedish date string like "19 december, 2025" into "2025-12-19".
        """
        pattern = r'(\d{1,2})\s+([a-zåäö]+),?\s+(\d{4})'
        match = re.search(pattern, text.lower())
        if not match:
            return None

        day, month_name, year = match.groups()
        month = SWEDISH_MONTHS.get(month_name)
        if not month:
            return None

        return f"{year}-{month}-{day.zfill(2)}"
