"""Quick debug script to see what's on the Throwback Thursday page."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.boras.se/upplevaochgora/kulturochnoje/borasbiorodakvarn/throwbackthursday.4.706b03641584ebf5394d6c1a.html"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Get page title
        title = await page.title()
        print(f"\nPage Title: {title}")
        
        # Get all text content
        content = await page.content()
        print(f"\nPage has {len(content)} characters of HTML")
        
        # Try to find movie-related content
        text = await page.inner_text('body')
        print(f"\nPage body text ({len(text)} chars):")
        print("="*80)
        print(text[:2000])  # First 2000 chars
        print("="*80)
        
        # Look for specific elements
        links = await page.locator('a').all()
        print(f"\nFound {len(links)} links")
        
        for link in links[:10]:
            href = await link.get_attribute('href')
            text = await link.inner_text()
            if text.strip():
                print(f"  - {text.strip()[:50]} -> {href}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
