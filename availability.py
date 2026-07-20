#!/usr/bin/env python3
"""
Availability Module (availability.py)
Reads availability.json and generates human-readable available time slots
for the AI agent to propose when booking Zoom meetings.
"""
import os
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

AVAILABILITY_PATH = os.path.join(os.path.dirname(__file__), "availability.json")

# Default config if availability.json doesn't exist
DEFAULT_CONFIG = {
    "timezone": "Asia/Dhaka",
    "unavailable_dates": [],
    "default_available_hours": {
        "start": "09:00",
        "end": "18:00",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    },
}


def _load_config() -> dict:
    """Loads the availability config from availability.json."""
    if not os.path.exists(AVAILABILITY_PATH):
        logging.warning(f"⚠️ {AVAILABILITY_PATH} not found, using defaults.")
        return DEFAULT_CONFIG
    try:
        with open(AVAILABILITY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"❌ Failed to load availability config: {e}")
        return DEFAULT_CONFIG


def get_available_slots(days_ahead: int = 5) -> str:
    """Returns a human-readable string of available time slots for the next N days.
    
    This string is injected into the prompt so Alex knows when to propose meetings.
    
    Args:
        days_ahead: How many days ahead to check (default 5)
    
    Returns:
        A formatted string like:
        "Available meeting times:
        - Thursday July 10: 9:00 AM - 6:00 PM
        - Friday July 11: 9:00 AM - 6:00 PM
        - Monday July 14: 9:00 AM - 2:00 PM (unavailable 2:00-6:00 PM)"
    """
    config = _load_config()
    available_days = config.get("default_available_hours", {}).get("days", [])
    start_time = config.get("default_available_hours", {}).get("start", "09:00")
    end_time = config.get("default_available_hours", {}).get("end", "18:00")
    unavailable_dates = config.get("unavailable_dates", [])

    today = datetime.now()
    slots = []

    for day_offset in range(1, days_ahead + 1):
        check_date = today + timedelta(days=day_offset)
        day_name = check_date.strftime("%A")
        date_str = check_date.strftime("%Y-%m-%d")
        display_date = check_date.strftime("%A %B %d")

        # Skip if not an available day of the week
        if day_name not in available_days:
            continue

        # Check if this date has any unavailability
        unavail_match = None
        full_day_blocked = False
        for entry in unavailable_dates:
            if entry.get("date") == date_str:
                if "start" not in entry and "end" not in entry:
                    # Full day blocked
                    full_day_blocked = True
                else:
                    unavail_match = entry
                break

        if full_day_blocked:
            continue

        # Format the time display
        start_display = _format_time(start_time)
        end_display = _format_time(end_time)

        if unavail_match:
            unavail_start = unavail_match.get("start", "")
            unavail_end = unavail_match.get("end", "")
            reason = unavail_match.get("reason", "busy")
            slot_str = f"- {display_date}: {start_display} - {end_display} (NOT available {_format_time(unavail_start)} - {_format_time(unavail_end)}, {reason})"
        else:
            slot_str = f"- {display_date}: {start_display} - {end_display}"

        slots.append(slot_str)

    if not slots:
        return "Available meeting times: No slots available in the next few days. Ask the customer for their preferred time and tell them you'll confirm via email/text."

    header = "Available meeting times (use these when proposing Zoom meetings — suggest specific times, e.g., '10 AM tomorrow' or '2 PM on Thursday'):\n"
    return header + "\n".join(slots)


def _format_time(time_str: str) -> str:
    """Converts '09:00' to '9:00 AM', '14:30' to '2:30 PM', etc."""
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = parts[1] if len(parts) > 1 else "00"
        if hour == 0:
            return f"12:{minute} AM"
        elif hour < 12:
            return f"{hour}:{minute} AM"
        elif hour == 12:
            return f"12:{minute} PM"
        else:
            return f"{hour - 12}:{minute} PM"
    except (ValueError, IndexError):
        return time_str
