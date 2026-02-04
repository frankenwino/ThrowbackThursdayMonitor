"""
Tests for browser automation components.

Includes unit tests and property-based tests for browser engine,
consent handling, and content extraction functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st

from src.models import BrowserConfig, ConsentResult, MovieData, ScrapingResult
from src.browser_automation.browser_engine import BrowserAutomationEngine


class TestBrowserAutomationEngine:
    """Test cases for BrowserAutomationEngine."""
    
    @pytest.fixture
    def browser_config(self):
        """Provide test browser configuration."""
        return BrowserConfig(
            headless=True,
            timeout_page_load=10000,
            timeout_element_wait=5000
        )
    
    @pytest.fixture
    def browser_engine(self, browser_config):
        """Provide browser engine instance."""
        return BrowserAutomationEngine(browser_config)
    
    def test_browser_engine_initialization(self, browser_engine):
        """Test browser engine creates with proper configuration."""
        assert browser_engine.config.headless is True
        assert browser_engine.config.timeout_page_load == 10000
        assert not browser_engine.is_initialized
        assert browser_engine.browser is None
        assert browser_engine.context is None
    
    def test_browser_config_defaults(self):
        """Test browser configuration has sensible defaults."""
        config = BrowserConfig()
        assert config.headless is True
        assert config.timeout_page_load == 30000
        assert config.timeout_element_wait == 10000
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.block_images is True
        assert config.enable_javascript is True
    
    @pytest.mark.asyncio
    async def test_cleanup_without_initialization(self, browser_engine):
        """Test cleanup works even without initialization."""
        # Should not raise any exceptions
        await browser_engine.cleanup()
        assert not browser_engine.is_initialized
    
    def test_performance_metrics_structure(self, browser_engine):
        """Test performance metrics return expected structure."""
        metrics = browser_engine.get_performance_metrics()
        
        assert 'browser_initialized' in metrics
        assert 'context_active' in metrics
        assert 'config' in metrics
        assert 'headless' in metrics['config']
        assert 'viewport' in metrics['config']
        assert 'timeouts' in metrics['config']


class TestDataModels:
    """Test cases for data models."""
    
    def test_movie_data_initialization(self):
        """Test MovieData model initialization."""
        movie = MovieData(
            title="Test Movie",
            screening_datetime="2026-02-26 19:00",
            location="Test Cinema",
            booking_url="https://example.com/book",
            movie_url="https://example.com/movie"
        )
        
        assert movie.title == "Test Movie"
        assert movie.screening_datetime == "2026-02-26 19:00"
        assert movie.location == "Test Cinema"
        assert movie.booking_url == "https://example.com/book"
        assert movie.movie_url == "https://example.com/movie"
    
    def test_consent_result_initialization(self):
        """Test ConsentResult model initialization."""
        result = ConsentResult(
            success=True,
            method_used="button_click",
            dialog_detected=True
        )
        
        assert result.success is True
        assert result.method_used == "button_click"
        assert result.dialog_detected is True
        assert result.timeout_occurred is False
        assert result.error_message is None
    
    def test_scraping_result_post_init(self):
        """Test ScrapingResult post-initialization."""
        result = ScrapingResult(success=True)
        
        assert result.success is True
        assert result.extraction_errors == []
        assert result.performance_metrics == {}
        assert result.browser_errors == []
    
    @given(
        success=st.booleans(),
        method_used=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        dialog_detected=st.booleans()
    )
    def test_consent_result_property_based(self, success, method_used, dialog_detected):
        """Property-based test for ConsentResult model."""
        result = ConsentResult(
            success=success,
            method_used=method_used,
            dialog_detected=dialog_detected
        )
        
        assert result.success == success
        assert result.method_used == method_used
        assert result.dialog_detected == dialog_detected
        assert isinstance(result.timeout_occurred, bool)


# Property-based test strategies for generating test data
@st.composite
def movie_data_strategy(draw):
    """Generate MovieData instances for property-based testing."""
    return MovieData(
        title=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        screening_datetime=draw(st.one_of(st.none(), st.text(min_size=10, max_size=30))),
        location=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        booking_url=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        movie_url=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200)))
    )


@st.composite
def browser_config_strategy(draw):
    """Generate BrowserConfig instances for property-based testing."""
    return BrowserConfig(
        headless=draw(st.booleans()),
        timeout_page_load=draw(st.integers(min_value=1000, max_value=60000)),
        timeout_element_wait=draw(st.integers(min_value=1000, max_value=30000)),
        viewport_width=draw(st.integers(min_value=800, max_value=2560)),
        viewport_height=draw(st.integers(min_value=600, max_value=1440)),
        block_images=draw(st.booleans()),
        enable_javascript=draw(st.booleans())
    )


class TestPropertyBasedModels:
    """Property-based tests for data models."""
    
    @given(movie_data=movie_data_strategy())
    def test_movie_data_properties(self, movie_data):
        """Property-based test for MovieData consistency."""
        # All fields should maintain their assigned values
        assert hasattr(movie_data, 'title')
        assert hasattr(movie_data, 'screening_datetime')
        assert hasattr(movie_data, 'location')
        assert hasattr(movie_data, 'booking_url')
        assert hasattr(movie_data, 'movie_url')
        
        # Optional fields can be None
        if movie_data.title is not None:
            assert isinstance(movie_data.title, str)
        if movie_data.screening_datetime is not None:
            assert isinstance(movie_data.screening_datetime, str)
    
    @given(config=browser_config_strategy())
    def test_browser_config_properties(self, config):
        """Property-based test for BrowserConfig validation."""
        # Timeouts should be positive
        assert config.timeout_page_load > 0
        assert config.timeout_element_wait > 0
        
        # Viewport dimensions should be reasonable
        assert config.viewport_width >= 800
        assert config.viewport_height >= 600
        
        # Boolean flags should be boolean
        assert isinstance(config.headless, bool)
        assert isinstance(config.block_images, bool)
        assert isinstance(config.enable_javascript, bool)