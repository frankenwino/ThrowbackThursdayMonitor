# Throwback Thursday Movie Monitor

A Python script that monitors Borås Bio Röda Kvarn's Throwback Thursday movie screenings webpage for updates. When new screenings are posted, it extracts the movie information and sends a notification to a Discord channel.

## Features

- Monitors webpage for changes
- Extracts movie details:
  - Title
  - Screening date and time
  - Location
  - Booking URL
- Stores data in JSON format
- Sends notifications via Discord webhooks
- Avoids duplicate notifications

## Installation

1. Clone the repository:

```bash
git clone https://github.com/frankenwino/ThrowbackThursdayMonitor.git
cd ThrowbackThursdayMonitor
```

2. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```python
from src.checker import WebChecker

checker = WebChecker()
checker.go()
```

## Development

```bash
pytest tests/
```

## Configuration

1. Create a .env file in the project root directory
2. Add your Discord webhook URL:

```
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

For more information on how to create a Discord webhook, refer to the [Discord Webhooks Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

### Discord Notifications

The script uses Discord webhooks to send notifications when new movies are detected. To enable notifications:

1. Create a Discord webhook in your server settings
2. Copy the webhook URL
3. Add it to your .env file as shown above
4. The script will automatically send notifications when updates are found

The script stores state in db.json:

```
{
    "last_changed_date": "2024-12-10T11:47:00+01:00",
    "latest_movie_data": {
        "title": "The Hills Have Pies",
        "screening_datetime": "2025-02-20T19:00:00+01:00",
        "location": "Cinema",
        "booking_url": "https://example.se",
        "movie_url": "https://www.example.se/movie.html"
    }
}
```
