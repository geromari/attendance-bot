# Attendance Bot - Quick Start Guide

## Setup Instructions

### 1. Install Dependencies

```bash
cd /home/patrickb/attendance-bot
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Edit the `.env` file with your settings:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_id_here
WORK_LOCATION_LAT=41.338938      # Your work location latitude
WORK_LOCATION_LNG=69.337057     # Your work location longitude
MAX_DISTANCE_METERS=100        # Max distance from work location
DAILY_HOUR_LIMIT=5             # Daily work hour limit
DATABASE_URL=sqlite+aiosqlite:///./attendance.db
```

**To get your Telegram User ID:**
1. Start a chat with @userinfobot on Telegram
2. Send any message
3. It will reply with your Telegram ID

**To set your work location:**
1. Open Google Maps
2. Click on your work location
3. Copy the latitude and longitude coordinates

### 3. Run the Bot

```bash
python bot/main.py
```

## Bot Commands

### For Employees

- `/start` - Register with the bot or show main menu

### Main Menu Buttons

1. **✅ Check In** - Check in for work (requires location sharing)
2. **🚪 Check Out** - Check out from work
3. **👤 My Profile** - View your weekly statistics
4. **🏆 Honor Board** - View leaderboard of all employees

### For Admins

Admin panel includes:
- **➕ Add Employee Schedule** - Set work schedules for employees
- **📋 View All Schedules** - View all employee schedules
- **👥 View All Employees** - View registered employees

## How It Works

### Registration
1. Employee sends `/start`
2. Bot asks for assigned nickname
3. Employee enters unique nickname
4. Registration complete

### Check-In Process
1. Employee taps "Check In"
2. Bot requests location
3. Employee shares location
4. Bot validates distance from work location
5. If within allowed distance → Check-in successful
6. If too far → Check-in rejected

### Auto Checkout
- Automatic checkout when:
  - Daily hour limit reached (default: 5 hours)
  - Work schedule end time reached
- Bot checks every 5 minutes
- User receives notification on auto checkout

### Location Verification
- Default max distance: 100 meters
- Configurable via MAX_DISTANCE_METERS
- Uses geodesic distance calculation

## Admin Features

### Setting Employee Schedules
1. Admin taps "Admin Panel" → "Add Employee Schedule"
2. Enter employee nickname
3. Select day of week
4. Enter start time (HH:MM format)
5. Enter end time (HH:MM format)
6. Schedule saved

### Viewing Statistics
- View all employees and their schedules
- Monitor who's checked in
- Track weekly hours via Honor Board

## Database

The bot uses SQLite by default (stored in `attendance.db`).

For production, you can use PostgreSQL:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/attendance_db
```

## Troubleshooting

### Bot not responding
- Check if BOT_TOKEN is correct
- Ensure bot is running
- Check logs for errors

### Location verification fails
- Ensure WORK_LOCATION_LAT and WORK_LOCATION_LNG are set correctly
- Check if MAX_DISTANCE_METERS is appropriate
- Make sure user is sharing GPS location, not manually selected location

### Registration issues
- Nicknames must be unique
- Case-sensitive
- No special characters

## Support

For issues or questions, contact the bot administrator.
