"""External factor generation for simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class ExternalFactors:
    date: datetime
    is_holiday: bool
    holiday_name: str | None
    is_weekend: bool
    weather_severity: float
    demand_multiplier: float


class ExternalFactorsGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def generate(self, day: datetime) -> ExternalFactors:
        is_weekend = day.weekday() >= 5
        is_holiday = day.strftime("%m-%d") in {"12-25", "01-01"}
        holiday_name = "Christmas Day" if day.strftime("%m-%d") == "12-25" else ("New Year's Day" if day.strftime("%m-%d") == "01-01" else None)
        weather_severity = 0.2 if not is_weekend else 0.25
        demand_multiplier = 1.2 if is_holiday else 1.0
        if is_weekend:
            demand_multiplier += 0.05
        return ExternalFactors(day, is_holiday, holiday_name, is_weekend, weather_severity, demand_multiplier)

    def generate_range(self, start: datetime, days: int) -> List[ExternalFactors]:
        return [self.generate(start + timedelta(days=i)) for i in range(days)]
