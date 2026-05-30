"""External factor generation for simulation.

Improvements over the previous version:
- Full retail holiday calendar (not just Christmas/New Year)
- Per-category demand multipliers (grocery != apparel != electronics)
- Weather severity varies by season and region, not a constant
- Price elasticity coefficient per category
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Category demand multiplier profiles
# ---------------------------------------------------------------------------
CATEGORY_HOLIDAY_LIFT: Dict[str, float] = {
    "grocery":     1.30,
    "bakery":      1.50,
    "beverages":   1.25,
    "apparel":     1.10,
    "electronics": 1.40,
    "toys":        2.00,
    "default":     1.20,
}

CATEGORY_WEEKEND_LIFT: Dict[str, float] = {
    "grocery":     1.10,
    "bakery":      1.20,
    "beverages":   1.15,
    "apparel":     1.05,
    "electronics": 1.03,
    "toys":        1.08,
    "default":     1.05,
}

CATEGORY_BLACK_FRIDAY_LIFT: Dict[str, float] = {
    "grocery":     1.05,
    "apparel":     2.50,
    "electronics": 3.00,
    "toys":        2.80,
    "beverages":   1.10,
    "default":     1.80,
}

# Price elasticity: demand change per 1% price change (negative = normal good)
CATEGORY_PRICE_ELASTICITY: Dict[str, float] = {
    "grocery":     -0.5,
    "bakery":      -0.6,
    "beverages":   -0.8,
    "apparel":     -2.0,
    "electronics": -1.5,
    "toys":        -1.8,
    "default":     -1.0,
}

# Fixed holidays: (month, day) -> (name, is_major)
HOLIDAY_CALENDAR: Dict[tuple, tuple] = {
    (1,  1):  ("New Year's Day",    True),
    (2, 14):  ("Valentine's Day",   False),
    (3, 17):  ("St. Patrick's Day", False),
    (5,  1):  ("May Day",           False),
    (7,  4):  ("Independence Day",  True),
    (10, 31): ("Halloween",         False),
    (11, 11): ("Veterans Day",      False),
    (12, 24): ("Christmas Eve",     False),
    (12, 25): ("Christmas Day",     True),
    (12, 26): ("Boxing Day",        False),
    (12, 31): ("New Year's Eve",    False),
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> Optional[datetime]:
    """Return the nth occurrence of weekday (0=Mon..6=Sun) in month/year."""
    count = 0
    day = datetime(year, month, 1)
    while day.month == month:
        if day.weekday() == weekday:
            count += 1
            if count == n:
                return day
        day += timedelta(days=1)
    return None


def _easter(year: int) -> datetime:
    """Easter Sunday via the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(114 + h + l - 7 * m, 31)
    return datetime(year, month, day + 1)


def _build_floating_holidays(year: int) -> Dict[tuple, tuple]:
    result: Dict[tuple, tuple] = {}
    # Thanksgiving — 4th Thursday of November
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    if thanksgiving:
        result[(thanksgiving.month, thanksgiving.day)] = ("Thanksgiving", True)
        bf = thanksgiving + timedelta(days=1)
        result[(bf.month, bf.day)] = ("Black Friday", True)
    # Mother's Day — 2nd Sunday of May
    mothers = _nth_weekday(year, 5, 6, 2)
    if mothers:
        result[(mothers.month, mothers.day)] = ("Mother's Day", False)
    # Father's Day — 3rd Sunday of June
    fathers = _nth_weekday(year, 6, 6, 3)
    if fathers:
        result[(fathers.month, fathers.day)] = ("Father's Day", False)
    easter = _easter(year)
    result[(easter.month, easter.day)] = ("Easter Sunday", False)
    return result


def _seasonal_weather_severity(date: datetime, region: str = "CA") -> float:
    """0.0 = clear, 1.0 = severe. Varies by month and region."""
    month = date.month
    profiles: Dict[str, List[float]] = {
        # Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
        "CA": [0.15,0.12,0.08,0.05,0.05,0.05,0.08,0.08,0.06,0.08,0.12,0.18],
        "TX": [0.20,0.18,0.12,0.08,0.12,0.25,0.30,0.30,0.20,0.10,0.15,0.22],
        "WI": [0.45,0.42,0.30,0.15,0.08,0.05,0.05,0.05,0.10,0.20,0.35,0.50],
        "MN": [0.55,0.50,0.35,0.18,0.08,0.05,0.05,0.05,0.10,0.22,0.40,0.58],
    }
    return profiles.get(region.upper(), profiles["CA"])[month - 1]


@dataclass
class ExternalFactors:
    date: datetime
    is_holiday: bool
    holiday_name: Optional[str]
    is_weekend: bool
    weather_severity: float
    demand_multiplier: float                            # aggregate baseline
    category_multipliers: Dict[str, float] = field(default_factory=dict)
    price_elasticity: Dict[str, float] = field(default_factory=dict)
    is_black_friday: bool = False
    is_major_holiday: bool = False

    def get_demand_multiplier(self, category: str = "default") -> float:
        """Return the demand multiplier for a specific product category."""
        return self.category_multipliers.get(
            category,
            self.category_multipliers.get("default", self.demand_multiplier)
        )

    def get_price_elasticity(self, category: str = "default") -> float:
        return self.price_elasticity.get(
            category,
            self.price_elasticity.get("default", -1.0)
        )

    def apply_price_change(
        self, base_demand: float, price_pct_change: float, category: str = "default"
    ) -> float:
        """Scale base_demand by a price change using category elasticity.

        price_pct_change: positive = price increase, negative = discount.
        Example: price_pct_change=10 with elasticity=-1.5 -> 15% demand drop.
        """
        elasticity = self.get_price_elasticity(category)
        multiplier = 1.0 + (elasticity * price_pct_change / 100.0)
        return base_demand * max(0.0, multiplier)


class ExternalFactorsGenerator:
    def __init__(self, seed: int = 42, region: str = "CA"):
        self.seed = seed
        self.region = region
        self._floating_cache: Dict[int, Dict[tuple, tuple]] = {}

    def _floating_for_year(self, year: int) -> Dict[tuple, tuple]:
        if year not in self._floating_cache:
            self._floating_cache[year] = _build_floating_holidays(year)
        return self._floating_cache[year]

    def generate(self, day: datetime) -> ExternalFactors:
        is_weekend = day.weekday() >= 5

        fixed = HOLIDAY_CALENDAR.get((day.month, day.day))
        floating = self._floating_for_year(day.year).get((day.month, day.day))
        holiday_entry = fixed or floating

        is_holiday = holiday_entry is not None
        holiday_name = holiday_entry[0] if holiday_entry else None
        is_major = holiday_entry[1] if holiday_entry else False
        is_bf = (holiday_name == "Black Friday")

        weather = _seasonal_weather_severity(day, region=self.region)

        cat_multipliers: Dict[str, float] = {}
        for cat in list(CATEGORY_HOLIDAY_LIFT.keys()):
            mult = 1.0
            if is_weekend:
                mult *= CATEGORY_WEEKEND_LIFT.get(cat, 1.05)
            if is_bf:
                mult *= CATEGORY_BLACK_FRIDAY_LIFT.get(cat, 1.80)
            elif is_holiday:
                mult *= CATEGORY_HOLIDAY_LIFT.get(cat, 1.20)
            # Weather dampens foot traffic; essentials less affected
            if cat in ("grocery", "bakery", "beverages"):
                mult *= (1.0 - weather * 0.10)
            else:
                mult *= (1.0 - weather * 0.25)
            cat_multipliers[cat] = round(mult, 4)

        baseline = round(sum(cat_multipliers.values()) / len(cat_multipliers), 4)

        return ExternalFactors(
            date=day,
            is_holiday=is_holiday,
            holiday_name=holiday_name,
            is_weekend=is_weekend,
            weather_severity=weather,
            demand_multiplier=baseline,
            category_multipliers=cat_multipliers,
            price_elasticity=dict(CATEGORY_PRICE_ELASTICITY),
            is_black_friday=is_bf,
            is_major_holiday=is_major,
        )

    def generate_range(self, start: datetime, days: int) -> List[ExternalFactors]:
        return [self.generate(start + timedelta(days=i)) for i in range(days)]