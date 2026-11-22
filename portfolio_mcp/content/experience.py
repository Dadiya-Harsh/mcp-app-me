"""Experience years. Same rule as the portfolio's src/utils/experience.ts."""

from datetime import UTC, date, datetime


def experience_years(career_start: str, today: date | None = None) -> float:
    """Years since `career_start` ("YYYY-MM"), one decimal, rounded down.

    months = (nowYear - startYear) * 12 + (nowMonth - startMonth)
    years  = floor(months / 12 * 10) / 10

    Nov 2026 from 2025-01 is 22 months, so 1.8. Jan 2027 is 24 months, so 2.0.
    """
    year_text, month_text = career_start.split("-")
    start_year, start_month = int(year_text), int(month_text)
    now = today or datetime.now(UTC).date()
    months = (now.year - start_year) * 12 + (now.month - start_month)
    if months < 0:
        return 0.0
    # Whole numbers only, so nothing like 0.7 * 10 = 6.999... can round the wrong way
    return (months * 10 // 12) / 10


def format_experience_years(years: float) -> str:
    """Always one decimal: 1.8, 2.0."""
    return f"{years:.1f}"
