# Throwback Thursday Movie Monitor

A Python script that monitors Borås Bio Röda Kvarn's Throwback Thursday movie screenings webpage for updates. When new screenings are posted, it extracts the movie information and can send notifications.

## Features

- Monitors webpage for changes
- Extracts movie details:
  - Title
  - Screening date and time
  - Location
  - Booking URL
- Stores data in JSON format
- Avoids duplicate notifications

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ThrowbackThursdayMonitor.git
cd ThrowbackThursdayMonitor

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Create a virtual environment:
```bash
python -m venv venv
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
The script stores state in db.json:


```
{
    "last_changed": "2024-03-14",
    "movies": [
        {
            "title": "Movie Title",
            "screening_time": "2024-03-14T19:00:00",
            "location": "Borås Bio Röda Kvarn",
            "booking_url": "https://bio.se/booking"
        }
    ]
}
```
