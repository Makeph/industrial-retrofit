"""OEE (Overall Equipment Effectiveness) — the headline KPI of any retrofit.

    OEE = Availability x Performance x Quality

Giving an old machine a live OEE number is usually the whole business case for
instrumenting it. Functions are pure and unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass


def availability(run_time_s: float, planned_time_s: float) -> float:
    if planned_time_s <= 0:
        return 0.0
    return min(1.0, run_time_s / planned_time_s)


def performance(total_count: int, ideal_cycle_s: float, run_time_s: float) -> float:
    if run_time_s <= 0:
        return 0.0
    return min(1.0, (ideal_cycle_s * total_count) / run_time_s)


def quality(good_count: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return good_count / total_count


def oee(run_time_s: float, planned_time_s: float, total_count: int,
        good_count: int, ideal_cycle_s: float) -> float:
    a = availability(run_time_s, planned_time_s)
    p = performance(total_count, ideal_cycle_s, run_time_s)
    q = quality(good_count, total_count)
    return a * p * q


@dataclass
class OeeAccumulator:
    """Roll up live counters into a running OEE figure for a single shift."""

    ideal_cycle_s: float = 2.0
    planned_time_s: float = 0.0
    run_time_s: float = 0.0
    total_count: int = 0
    good_count: int = 0

    def tick(self, *, running: bool, total_count: int, good_count: int, dt_s: float = 1.0):
        self.planned_time_s += dt_s
        if running:
            self.run_time_s += dt_s
        self.total_count = total_count
        self.good_count = good_count

    def snapshot(self) -> dict:
        return {
            "availability": round(availability(self.run_time_s, self.planned_time_s), 4),
            "performance": round(performance(self.total_count, self.ideal_cycle_s, self.run_time_s), 4),
            "quality": round(quality(self.good_count, self.total_count), 4),
            "oee": round(oee(self.run_time_s, self.planned_time_s, self.total_count,
                             self.good_count, self.ideal_cycle_s), 4),
        }
