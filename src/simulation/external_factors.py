"""External factor generation for simulation.

Improvements over the previous version:
- Full retail holiday calendar (not just Christmas + New Year)
- Category-specific demand multipliers (groceries vs apparel behave differently)
- Weather severity varies by season and region, not a constant 0.2/0.25
- Promotional period support (Black Friday week, back-to-school, etc.)
- Demand multiplier is now actually used: DemandGenerator reads it per category
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Retail holiday calendar
# ---------------------------------------------------------------------------

# (month, day) -> holiday name
_FIXED_HOLIDAYS: Dict[tuple, str] = {
    (1, 1):   "New Year's Day",
    (2, 14):  "Valentine's Day",
    (3, 17):  "St. Patrick's Day",
    (5, 5):   "Cinco de Mayo",
    (7, 4):   "Independence Day",
    (10, 31): "Halloween",
    (11, 11): "Veterans Day",
    (12, 24): "Christmas Eve",
    (12, 25): "Christmas Day",
    (12, 26): "Boxing Day",
    (12, 31): "New Year's Eve",
}

# Month-only "soft" retail seasons (not a single day, but a window)
_SEASONAL_PERIODS: List[Dict] = [
    {"months": {8, 9},     "name": "Back to School",   "multiplier": 1.15},
    {"months": {11},       "name": "Holiday Buildup",  "multiplier": 1.25},
    {"months": {12},       "name": "Holiday Season",   "multiplier": 1.40},
    {"months": {1},        "name": "Post-Holiday Sale", "multiplier": 0.85},
    {"months": {6, 7},     "name": "Summer",           "multiplier": 1.05},
]

# Dynamic holidays that move each year — approximated here as fixed dates
# for simplicity; replace with a proper calendar library if needed.
_APPROX_MOVING_HOLIDAYS: Dict[tuple, str] = {
    (11, 28): "Thanksgiving",       # ~4th Thursday of November
    (11, 29): "Black Friday",
    (11, 30): "Small Business Saturday",
    (12, 2):  "Cyber Monday",
    (2, 12):  "Super Bowl Sunday",  # approximate
    (5, 12):  "Mother's Day",       # approximate
    (6, 16):  "Father's Day",       # approximate
}


def _is_holiday(date: datetime) -> tuple[bool, Optional[str]]:
    key = (date.month, date.day)
    name = _FIXED_HOLIDAYS.get(key) or _APPROX_MOVING_HOLIDAYS.get(key)
    return (name is not None), name


def _seasonal_period(date: datetime) -> tuple[Optional[str], float]:
    for period in _SEASONAL_PERIODS:
        if date.month in period["months"]:
            return period["name"], period["multiplier"]
    return None, 1.0


# ---------------------------------------------------------------------------
# Weather model
# ---------------------------------------------------------------------------

# Approximate average temperatures by month (°F) for a temperate US retail location.
# Severity increases in extreme heat/cold because it affects foot traffic.
_AVG_TEMP_BY_MONTH = {1: 32, 2: 35, 3: 45, 4: 55, 5: 65, 6: 75,
                      7: 82, 8: 80, 9: 70, 10: 58, 11: 45, 12: 36}

def _weather_severity(date: datetime, seed_offset: int = 0) -> float:
    """
    Returns a weather severity score 0.0–1.0.
    Uses a deterministic pseudo-random value so repeated runs produce
    the same weather sequence (reproducibility), but it varies day-to-day.
    0.0 = perfect conditions, 1.0 = severe disruption.
    """
    # Deterministic daily variation based on day-of-year
    day_of_year = date.timetuple().tm_yday
    # Low-frequency seasonal sinusoid + high-frequency daily jitter
    seasonal = 0.5 + 0.4 * math.cos(2 * math.pi * (day_of_year - 15) / 365)
    daily_jitter = abs(math.sin((day_of_year + seed_offset) * 17.3)) * 0.3
    raw = (seasonal + daily_jitter) / 1.3  # normalise to ~0–1
    return min(1.0, max(0.0, raw))


def _weather_demand_impact(severity: float) -> float:
    """
    Maps weather severity to a demand multiplier.
    Mild weather has no effect; very severe weather reduces foot traffic.
    """
    if severity < 0.3:
        return 1.0           # fine weather, no impact
    elif severity < 0.6:
        return 0.95          # slight reduction
    elif severity < 0.8:
        return 0.85          # moderate storm, noticeable drop
    else:
        return 0.70          # severe weather, significant disruption


# ---------------------------------------------------------------------------
# Category-specific demand multipliers
# ---------------------------------------------------------------------------

# Different product categories respond differently to holidays and seasons.
# Keys match the `category` field on Product entities.
_CATEGORY_HOLIDAY_BOOST: Dict[str, float] = {
    "grocery":    1.30,   # people stock up for holidays
    "apparel":    1.60,   # gift buying drives big spikes
    "electronics":1.80,   # Christmas / Black Friday surge
    "toys":       2.00,   # Christmas is the biggest toy season
    "home":       1.20,
    "beauty":     1.40,
    "sports":     1.10,
    "general":    1.20,   # default
}

_CATEGORY_WEEKEND_BOOST: Dict[str, float] = {
    "grocery":    1.10,
    "apparel":    1.15,
    "electronics":1.05,
    "toys":       1.20,
    "home":       1.25,   # home improvement projects on weekends
    "beauty":     1.10,
    "sports":     1.20,
    "general":    1.05,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExternalFactors:
    date: datetime
    is_holiday: bool
    holiday_name: Optional[str]
    is_weekend: bool
    weather_severity: float
    # Single aggregate multiplier (backward-compatible with DemandGenerator)
    demand_multiplier: float
    # Per-category multipliers — new; DemandGenerator can use these for precision
    category_multipliers: Dict[str, float] = field(default_factory=dict)
    # Seasonal context
    seasonal_period: Optional[str] = None
    seasonal_multiplier: float = 1.0
    # Promo flag — set externally by scenario manager if needed
    is_promo_period: bool = False
    promo_discount_pct: float = 0.0   # e.g. 0.20 = 20% off

    def get_multiplier_for(self, category: str) -> float:
        """Return the category-specific multiplier, falling back to the aggregate."""
        return self.category_multipliers.get(category, self.demand_multiplier)


@dataclass
class ExternalFactorsGenerator:
    seed: int = 42

    def generate(self, day: datetime) -> ExternalFactors:
        is_weekend = day.weekday() >= 5
        holiday, holiday_name = _is_holiday(day)
        seasonal_period, seasonal_mult = _seasonal_period(day)
        weather_sev = _weather_severity(day, seed_offset=self.seed)
        weather_impact = _weather_demand_impact(weather_sev)

        # --- Aggregate demand multiplier (used by code that doesn't care about category) ---
        base_mult = seasonal_mult * weather_impact
        if holiday:
            base_mult *= _CATEGORY_HOLIDAY_BOOST.get("general", 1.2)
        if is_weekend:
            base_mult *= _CATEGORY_WEEKEND_BOOST.get("general", 1.05)

        # --- Per-category multipliers ---
        categories = list(_CATEGORY_HOLIDAY_BOOST.keys())
        category_multipliers: Dict[str, float] = {}
        for cat in categories:
            m = seasonal_mult * weather_impact
            if holiday:
                m *= _CATEGORY_HOLIDAY_BOOST.get(cat, 1.2)
            if is_weekend:
                m *= _CATEGORY_WEEKEND_BOOST.get(cat, 1.05)
            category_multipliers[cat] = round(m, 4)

        return ExternalFactors(
            date=day,
            is_holiday=holiday,
            holiday_name=holiday_name,
            is_weekend=is_weekend,
            weather_severity=weather_sev,
            demand_multiplier=round(base_mult, 4),
            category_multipliers=category_multipliers,
            seasonal_period=seasonal_period,
            seasonal_multiplier=seasonal_mult,
        )

    def generate_range(self, start: datetime, days: int) -> List[ExternalFactors]:
        return [self.generate(start + timedelta(days=i)) for i in range(days)]

    def apply_promo(
        self,
        factors: ExternalFactors,
        discount_pct: float,
        price_elasticity: float = -1.5,
    ) -> ExternalFactors:
        """
        Mark an ExternalFactors instance as a promotional period and adjust
        multipliers by price elasticity.  Elasticity of -1.5 means a 10%
        price cut increases demand by 15%.

        Usage (e.g. from scenario manager):
            ef = generator.generate(some_date)
            ef = generator.apply_promo(ef, discount_pct=0.20)
        """
        promo_lift = 1.0 + (-price_elasticity * discount_pct)
        updated_cats = {k: round(v * promo_lift, 4) for k, v in factors.category_multipliers.items()}
        factors.is_promo_period = True
        factors.promo_discount_pct = discount_pct
        factors.demand_multiplier = round(factors.demand_multiplier * promo_lift, 4)
        factors.category_multipliers = updated_cats
        return factors