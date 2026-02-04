"""
Browser Automation Package

Provides browser automation capabilities using Playwright for handling
JavaScript-rendered content, cookie consent dialogs, and content extraction.
"""

from .browser_engine import BrowserAutomationEngine
from .consent_handler import CookieConsentHandler
from .content_extractor import ContentExtractor

__all__ = ['BrowserAutomationEngine', 'CookieConsentHandler', 'ContentExtractor']
