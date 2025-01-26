from pathlib import Path
import re
import aiofiles
import aiohttp
import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser
import json
from datetime import datetime
from typing import Optional, Dict, Any
from discord_notifier import DiscordNotifier

class WebChecker:
    """
    A class to check and monitor updates on a specific webpage and extract movie information.
    Attributes:
        url (str): The URL of the webpage to monitor.
        db_file_path (str): The file path to the JSON database file.
    Methods:
        download_html(url: str) -> str:
            Downloads the HTML content of the given URL.
        html_to_soup(html: str) -> BeautifulSoup:
            Converts HTML content to a BeautifulSoup object.
        get_element_by_class(class_name: str, soup: BeautifulSoup) -> Optional[Tag]:
            Finds the first element with the specified class name in the BeautifulSoup object.
        get_site_last_changed_date(soup: BeautifulSoup) -> Optional[str]:
            Extracts the last changed date of the site from the BeautifulSoup object.
        get_db_last_changed_date() -> Optional[str]:
            Retrieves the last changed date from the JSON database file.
        datestring_to_datetime(datestring: str) -> datetime:
            Converts a date string to a datetime object.
        open_db_file() -> Dict[str, Any]:
            Opens and reads the JSON database file.
        write_db_file(data: Dict[str, Any]) -> None:
            Writes data to the JSON database file.
        get_movie_url(soup: BeautifulSoup) -> Optional[str]:
            Extracts the movie URL from the BeautifulSoup object.
        get_movie_title(soup: BeautifulSoup) -> Optional[str]:
            Extracts the movie title from the BeautifulSoup object.
        get_booking_url(soup: BeautifulSoup) -> Optional[str]:
            Extracts the booking URL from the BeautifulSoup object.
        get_screening_datetime(soup: BeautifulSoup) -> Optional[datetime]:
            Extracts the screening datetime from the BeautifulSoup object.
        get_screening_location(soup: BeautifulSoup) -> Optional[str]:
            Extracts the screening location from the BeautifulSoup object.
        go() -> None:
            Main method to check for updates, extract movie information, and update the database.
    """
    def __init__(self, url: str, db_file_path: Path):
        self.url: str = url
        self.db_file_path: str = db_file_path
        self.notifier = DiscordNotifier()

    # def download_html(self, url: str) -> str:
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     return response.text
    
    async def download_html(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    def html_to_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, 'lxml')

    def get_element_by_class(self, class_name: str, soup: BeautifulSoup) -> Optional[Tag]:
        return soup.find(class_=class_name)

    def get_site_last_changed_date(self, soup: BeautifulSoup) -> Optional[str]:
        last_changed_element = self.get_element_by_class('sv-font-uppdaterad-info-ny', soup)
        if last_changed_element:
            time_element = last_changed_element.find('time')
            if time_element and 'datetime' in time_element.attrs:
                return time_element['datetime']
        return None

    async def get_db_last_changed_date(self) -> Optional[str]:
        json_data = await self.open_db_file()
        return json_data.get('last_changed_date')

    def datestring_to_datetime(self, datestring: str) -> datetime:
        return parser.parse(datestring)

    async def open_db_file(self) -> Dict[str, Any]:
        try:
            async with aiofiles.open(self.db_file_path, 'r') as file:
                content = await file.read()
                return json.loads(content)
        except FileNotFoundError:
            return {}

    async def write_db_file(self, data: Dict[str, Any]) -> None:
        json_data = json.dumps(data)
        async with aiofiles.open(self.db_file_path, 'w') as f:
            await f.write(json_data)

    def get_movie_url(self, soup: BeautifulSoup) -> Optional[str]:
        movie_element = self.get_element_by_class('sv-channel-item', soup)
        if movie_element:
            link_element = movie_element.find('a', href=True)
            if link_element:
                return requests.compat.urljoin(self.url, link_element['href'])
        return None

    def get_movie_title(self, soup: BeautifulSoup) -> Optional[str]:
        movie_title_element = self.get_element_by_class('sidrubrik', soup)
        if movie_title_element:
            movie_title_text = movie_title_element.get_text(strip=True)
            match = re.search(r'"(.*?)"', movie_title_text)
            if match:
                return match.group(1)
        return None

    def get_booking_url(self, soup: BeautifulSoup) -> Optional[str]:
        booking_element = soup.find('strong', string='Köp biljett')
        if booking_element:
            anchor = booking_element.find_parent('a')
            if anchor and 'href' in anchor.attrs:
                return anchor['href']
        return None

    def get_screening_datetime(self, soup: BeautifulSoup) -> Optional[datetime]:
        time_element = soup.find('strong', string='Tid:')
        if time_element:
            time_tag = time_element.find_next_sibling('time')
            if time_tag and 'datetime' in time_tag.attrs:
                dt = datetime.fromisoformat(time_tag['datetime'])
                return dt.strftime('%Y-%m-%d %H:%M')
        return None
    
    def get_screening_location(self, soup: BeautifulSoup) -> Optional[str]:
        location_element = soup.find('strong', string=lambda t: t and 'Plats:' in t)
        if location_element:
            location_text = location_element.next_sibling
            if location_text:
                return location_text.strip()
        return None

    async def go(self) -> None:
        html = await self.download_html(self.url)
        soup = self.html_to_soup(html)
        site_last_changed_date = self.get_site_last_changed_date(soup)
        db_last_changed_date = await self.get_db_last_changed_date()

        if db_last_changed_date is None or site_last_changed_date > db_last_changed_date:
            movie_url = self.get_movie_url(soup)
            movie_html = await self.download_html(movie_url)
            movie_soup = self.html_to_soup(movie_html)

            movie_title = self.get_movie_title(movie_soup)
            if movie_title:
                print(f"Movie title: {movie_title}")

            screening_datetime = self.get_screening_datetime(movie_soup)
            if screening_datetime:
                print(f"Screening time: {screening_datetime}")

            screening_location = self.get_screening_location(movie_soup)
            if screening_location:
                print(f"Location: {screening_location}")

            booking_url = self.get_booking_url(movie_soup)
            if booking_url:
                print(f"Booking URL: {booking_url}")

            latest_movie_data = {
                'title': movie_title,
                'screening_datetime': screening_datetime,
                'location': screening_location,
                'booking_url': booking_url,
                'movie_url': movie_url
            }

            json_data = await self.open_db_file()
            json_data['last_changed_date'] = site_last_changed_date
            json_data['latest_movie_data'] = latest_movie_data
            await self.write_db_file(json_data)
            message = f"New Movie: {movie_title}\nWhen: {screening_datetime}\nWhere: {screening_location}\nDetails: <{movie_url}>\nBook here: <{booking_url}>"
            self.notifier.send_message(message)
        else:
            print("Site has not changed")
