# Throwback Thursday Movie Monitor

A Python script that monitors Borås Bio Röda Kvarn's Throwback Thursday movie screenings webpage for updates. When new screenings are posted, it extracts the movie information and sends a notification to a Discord channel.

**Now with browser automation** to handle modern websites with cookie consent dialogs and JavaScript-rendered content.

## Features

- **Browser Automation**: Uses Playwright to handle cookie consent dialogs and JavaScript content
- **Automatic Consent Handling**: Automatically clicks "Godkänn alla kakor" (Accept all cookies)
- **Robust Data Extraction**: Extracts movie details even from dynamically loaded content:
  - Title
  - Screening date and time
  - Location
  - Booking URL
- **Smart Monitoring**: Only processes updates when content actually changes
- **Discord Notifications**: Sends rich embed notifications via Discord webhooks
- **Error Handling**: Comprehensive error handling with detailed logging
- **Resource Management**: Proper browser cleanup and memory management

## Installation

1. Clone the repository:

```bash
git clone https://github.com/frankenwino/ThrowbackThursdayMonitor.git
cd ThrowbackThursdayMonitor
```

2. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:

```bash
playwright install chromium
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and add your Discord webhook URL:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

For more information on how to create a Discord webhook, refer to the [Discord Webhooks Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

## Usage

Run the scraper:

```bash
cd src
python main.py
```

The scraper will:
1. Launch a headless browser
2. Navigate to the Throwback Thursday page
3. Handle cookie consent automatically
4. Extract movie information
5. Send Discord notification if new content is found
6. Store data in `db.json` for change detection

## Development

Run tests:

```bash
pytest tests/
```

Run with visible browser (for debugging):

```bash
# Edit .env file and set:
HEADLESS_BROWSER=false
```

## How It Works

### Browser Automation
The scraper uses Playwright to:
- Launch a Chromium browser instance
- Handle cookie consent dialogs automatically
- Wait for JavaScript content to load
- Extract data from the rendered page

### Data Storage
The script stores state in `db.json`:

```json
{
    "last_changed_date": "2025-02-04T10:30:00+01:00",
    "latest_movie_data": {
        "title": "Dirty Harry",
        "screening_datetime": "2026-02-26 19:00",
        "location": "Borås Bio Röda Kvarn",
        "booking_url": "https://bio.se/biografer/boras-bio-roda-kvarn/film/ST00018036/dirty-harry-otextad/",
        "movie_url": "https://www.boras.se/upplevaochgora/evenemangkulturochnoje/throwbackthursdaydirtyharry1971.5.7169943b19afcd7b7e5f350.html"
    }
}
```

### Discord Notifications
When new movies are detected, the script sends rich Discord embeds with:
- Movie title and screening information
- Direct links to booking and movie details
- Formatted date/time and location

## Troubleshooting

### Browser Issues
If you encounter browser-related errors:
1. Ensure Playwright browsers are installed: `playwright install chromium`
2. Try running in non-headless mode for debugging
3. Check system requirements for Playwright

### Discord Notifications Not Working
1. Verify your webhook URL is correct in `.env`
2. Test the webhook URL manually
3. Check Discord server permissions

### No Movie Data Extracted
1. The website structure may have changed
2. Check logs for specific extraction errors
3. Run in non-headless mode to see what's happening

## Architecture

The scraper consists of several components:

- **BrowserAutomationEngine**: Manages Playwright browser lifecycle
- **CookieConsentHandler**: Detects and handles consent dialogs
- **ContentExtractor**: Extracts movie data from rendered pages
- **BrowserWebChecker**: Main orchestrator maintaining compatibility with original interface

## Requirements

- Python 3.8+
- Playwright (automatically installs Chromium)
- Discord webhook URL
- Internet connection

## License

This project is open source and available under the MIT License.
