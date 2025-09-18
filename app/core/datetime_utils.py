from datetime import datetime, timedelta
from typing import Tuple, Optional
import re

def parse_date_flexible(date_string: str) -> Optional[datetime]:
    """Tries to parse a date string from various common formats."""
    # Simple way to handle '1st', '2nd', '3rd', 'th'
    date_string = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_string)

    formats_to_try = [
        '%Y-%m-%d',        # "2025-09-12"
        '%d %B %Y',        # "12 September 2025"
        '%B %d %Y',        # "September 12 2025"
    ]
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            pass
    return None

def parse_time_range(time_range_str: Optional[str]) -> Tuple[datetime, datetime]:
    """
    Parses a natural language or date string into a start and end datetime object.
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if not time_range_str:
        return now - timedelta(days=30), now

    time_range_str_lower = time_range_str.lower()

    # --- UPGRADED: Try to parse a specific date string first ---
    specific_date = parse_date_flexible(time_range_str.split('T')[0])
    if specific_date:
        start_date = specific_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = specific_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_date, end_date
    # --- END UPGRADE ---

    if "today" in time_range_str_lower:
        start_date = today_start
        end_date = now
    elif "yesterday" in time_range_str_lower:
        start_date = today_start - timedelta(days=1)
        end_date = today_start - timedelta(microseconds=1)
    elif "this week" in time_range_str_lower:
        start_date = today_start - timedelta(days=now.weekday())
        end_date = now
    elif "last week" in time_range_str_lower:
        end_of_last_week = today_start - timedelta(days=now.weekday() + 1)
        start_date = end_of_last_week - timedelta(days=6)
        end_date = end_of_last_week.replace(hour=23, minute=59, second=59)
    elif "this month" in time_range_str_lower:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif "last month" in time_range_str_lower:
        last_month_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        start_date = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = last_month_end
    # --- NEW: If no relative keyword is found, and it wasn't a specific date, return a zero-duration range
    else:
        # Check if the string looks like it could be a date but failed parsing
        # This is a simple heuristic; can be improved if needed
        if re.search(r'\d', time_range_str_lower) and ("year" not in time_range_str_lower):
            return now, now  # Return zero-duration range to yield 0 expenses

        # Default fallback to the last 30 days if no other condition is met
        start_date = now - timedelta(days=30)
        end_date = now

    return start_date, end_date
