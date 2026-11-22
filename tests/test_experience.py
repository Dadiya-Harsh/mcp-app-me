"""Experience years: same rule as the portfolio's experience.ts."""

from datetime import date

import pytest

from portfolio_mcp.content.experience import experience_years, format_experience_years


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 22), 1.8),  # 22 months
        (date(2027, 1, 1), 2.0),  # 24 months
        (date(2025, 1, 31), 0.0),
        (date(2025, 6, 1), 0.4),  # 5 months, 4.16 -> 0.4 (rounded down)
        (date(2026, 1, 1), 1.0),
        (date(2024, 12, 1), 0.0),  # before the start: never negative
    ],
)
def test_experience_years(today: date, expected: float) -> None:
    assert experience_years("2025-01", today) == expected


def test_one_decimal_text() -> None:
    assert (
        format_experience_years(experience_years("2025-01", date(2027, 1, 1))) == "2.0"
    )
    assert (
        format_experience_years(experience_years("2025-01", date(2026, 11, 1))) == "1.8"
    )


def test_uses_today_when_not_given() -> None:
    assert experience_years("2025-01") >= 1.8
