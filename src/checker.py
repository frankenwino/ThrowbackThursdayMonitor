import re
import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser
import json
from datetime import datetime
from typing import Optional, Dict, Any

class WebChecker:
    def __init__(self, url: str = "https://www.boras.se/upplevaochgora/kulturochnoje/borasbiorodakvarn/throwbackthursday.4.706b03641584ebf5394d6c1a.html", db_file_path: str = "db.json"):
        self.url: str = url
        self.db_file_path: str = db_file_path

    def download_html(self, url: str) -> str:
        response = requests.get(url)
        response.raise_for_status()
        return response.text

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

    def get_db_last_changed_date(self) -> Optional[str]:
        json_data = self.open_db_file()
        return json_data.get('last_changed_date')

    def datestring_to_datetime(self, datestring: str) -> datetime:
        return parser.parse(datestring)

    def open_db_file(self) -> Dict[str, Any]:
        try:
            with open(self.db_file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def write_db_file(self, data: Dict[str, Any]) -> None:
        json_data = json.dumps(data)
        with open(self.db_file_path, 'w') as f:
            f.write(json_data)

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
                return datetime.fromisoformat(time_tag['datetime'])
        return None
    
    def get_screening_location(self, soup: BeautifulSoup) -> Optional[str]:
        location_element = soup.find('strong', string=lambda t: t and 'Plats:' in t)
        if location_element:
            location_text = location_element.next_sibling
            if location_text:
                return location_text.strip()
        return None

    def go(self) -> None:
        html = self.download_html(self.url)
        soup = self.html_to_soup(html)
        site_last_changed_date = self.get_site_last_changed_date(soup)
        db_last_changed_date = self.get_db_last_changed_date()

        if db_last_changed_date is None or site_last_changed_date > db_last_changed_date:
            movie_url = self.get_movie_url(soup)
            movie_html = self.download_html(movie_url)
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
                'screening_datetime': screening_datetime.isoformat() if screening_datetime else None,
                'location': screening_location,
                'booking_url': booking_url,
                'movie_url': movie_url
            }

            json_data = self.open_db_file()
            json_data['last_changed_date'] = site_last_changed_date
            json_data['latest_movie_data'] = latest_movie_data
            self.write_db_file(json_data)
        else:
            print("Site has not changed")
