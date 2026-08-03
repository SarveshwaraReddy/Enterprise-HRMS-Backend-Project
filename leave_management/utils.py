import datetime


def calculate_leave_days(start_date: datetime.date, end_date: datetime.date, exclude_weekends: bool = True) -> int:
    """
    Calculates total leave days between start_date and end_date (inclusive).
    If exclude_weekends is True, excludes Saturdays (weekday 5) and Sundays (weekday 6).
    """
    if start_date > end_date:
        return 0

    total_days = 0
    current_date = start_date
    while current_date <= end_date:
        if not exclude_weekends or current_date.weekday() < 5:
            total_days += 1
        current_date += datetime.timedelta(days=1)

    return total_days
