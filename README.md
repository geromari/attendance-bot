# Employee Attendance Bot

A Telegram bot for tracking employee check-ins/check-outs with location verification, work schedule management, and competitive leaderboards.

## Features

### Core Functionality
- **Check-in/Check-out**: Location-based attendance tracking with 5-hour daily limit
- **Auto Checkout**: Automatic checkout when time limit or schedule ends
- **Nicknames**: Unique employee identifiers for confusion-free tracking
- **Weekly Schedules**: Admin-managed work schedules per employee

### Extension Buttons

#### My Profile
- Weekly working hours summary
- Days worked per week
- Specific work days displayed

#### Honor Board
- Competitive leaderboard
- Total hours worked per employee
- Ranking system

#### Location Verification
- Real-time location check on check-in
- Distance-based validation
- Rejects check-ins from unauthorized locations

## Tech Stack

- **Language**: Python 3.11+
- **Bot Framework**: python-telegram-bot 20.x
- **Database**: SQLite (development) / PostgreSQL (production)
- **Scheduler**: APScheduler
- **Geolocation**: geopy for distance calculations

## Project Structure

```
attendance-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Bot entry point
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # Registration & start
│   │   ├── checkin.py       # Check-in/out logic
│   │   ├── profile.py       # My Profile button
│   │   ├── leaderboard.py   # Honor Board
│   │   └── admin.py         # Admin commands
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py        # Button layouts
│   ├── services/
│   │   ├── __init__.py
│   │   ├── attendance.py    # Attendance logic
│   │   ├── location.py      # Location validation
│   │   ├── schedule.py      # Schedule management
│   │   └── auto_checkout.py # Auto checkout scheduler
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── attendance.py
│   │   └── schedule.py
│   ├── config.py            # Configuration
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── database/
│   ├── __init__.py
│   ├── db.py                # Database connection
│   └── migrations/
│       └── 001_initial.sql
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
├── DEPLOYMENT.md
└── README.md
```

## Setup

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure
6. Run: `python bot/main.py`

## Environment Variables

- `BOT_TOKEN`: Telegram bot token
- `ADMIN_IDS`: Comma-separated admin user IDs
- `WORK_LOCATION_LAT`: Work location latitude
- `WORK_LOCATION_LNG`: Work location longitude
- `MAX_DISTANCE_METERS`: Maximum allowed distance (default: 100)
- `DAILY_HOUR_LIMIT`: Daily work hour limit (default: 5)
- `DATABASE_URL`: Database connection string
