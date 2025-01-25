import pytest
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bs4 import BeautifulSoup
from unittest.mock import patch, mock_open
from src.checker import WebChecker


@pytest.fixture
def web_checker():
    return WebChecker(url="http://example.com", db_file_path="db.json")

def test_download_html(web_checker):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html></html>"
        html = web_checker.download_html("http://example.com")
        assert html == "<html></html>"

def test_html_to_soup(web_checker):
    html = "<html><body></body></html>"
    soup = web_checker.html_to_soup(html)
    assert isinstance(soup, BeautifulSoup)

def test_get_element_by_class(web_checker):
    html = '<div class="test-class">Content</div>'
    soup = web_checker.html_to_soup(html)
    element = web_checker.get_element_by_class("test-class", soup)
    assert element.get_text() == "Content"

def test_get_site_last_changed_date(web_checker):
    html = '<div class="sv-font-uppdaterad-info-ny"><time datetime="2023-01-01T00:00:00Z"></time></div>'
    soup = web_checker.html_to_soup(html)
    last_changed_date = web_checker.get_site_last_changed_date(soup)
    assert last_changed_date == "2023-01-01T00:00:00Z"

def test_get_db_last_changed_date(web_checker):
    with patch("builtins.open", mock_open(read_data='{"last_changed_date": "2023-01-01T00:00:00Z"}')):
        last_changed_date = web_checker.get_db_last_changed_date()
        assert last_changed_date == "2023-01-01T00:00:00Z"

def test_datestring_to_datetime(web_checker):
    datestring = "2023-01-01T00:00:00Z"
    dt = web_checker.datestring_to_datetime(datestring)
    assert dt.isoformat() == "2023-01-01T00:00:00+00:00"

def test_get_movie_url(web_checker):
    html = '<div class="sv-channel-item"><a href="/movie"></a></div>'
    soup = web_checker.html_to_soup(html)
    movie_url = web_checker.get_movie_url(soup)
    assert movie_url == "http://example.com/movie"

def test_get_movie_title(web_checker):
    html = '<div class="sidrubrik">"Movie Title"</div>'
    soup = web_checker.html_to_soup(html)
    movie_title = web_checker.get_movie_title(soup)
    assert movie_title == "Movie Title"

def test_get_booking_url(web_checker):
    html = '<a href="http://example.com/booking" rel="external"><strong>Köp biljett</strong><img alt="" src="/sitevision/util/images/externallinknewwindow.png" style="max-width:11px;max-height:10px" class="sv-linkicon"><span class="env-assistive-text"> Länk till annan webbplats, öppnas i nytt fönster.</span></a>'
    soup = web_checker.html_to_soup(html)
    booking_url = web_checker.get_booking_url(soup)
    assert booking_url == "http://example.com/booking"

def test_get_screening_datetime(web_checker):
    html = '<strong>Tid:</strong><time datetime="2023-01-01T00:00:00"></time>'
    soup = web_checker.html_to_soup(html)
    screening_datetime = web_checker.get_screening_datetime(soup)
    assert screening_datetime.isoformat() == "2023-01-01T00:00:00"

def test_get_screening_location(web_checker):
    html = '<p class="sv-font-ny-brodtext"><strong>Tid:</strong> <time datetime="2025-02-20T19:00:00+01:00">2025-02-20 19.00</time><br><strong>Plats: </strong>Location</p>'
    soup = web_checker.html_to_soup(html)
    screening_location = web_checker.get_screening_location(soup)
    assert screening_location == "Location"

def test_open_db_file_not_found(web_checker):
    with patch("builtins.open", side_effect=FileNotFoundError):
        data = web_checker.open_db_file()
        assert data == {}

def test_write_db_file(web_checker):
    json_data = {"key": "value"}
    with patch("builtins.open", mock_open()) as mock_file:
        web_checker.write_db_file(json_data)
        mock_file.assert_called_once_with('db.json', 'w')
        mock_file().write.assert_called_once_with('{"key": "value"}')
