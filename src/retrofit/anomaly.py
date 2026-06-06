"""Lightweight online anomaly detection for streaming machine telemetry.

Pure stdlib (no numpy) so it runs on an edge gateway next to the PLC.

* :class:`RollingZScore` flags transient spikes (e.g. a fault ringing the bearing).
* :class:`EwmaTrend` tracks slow drift (progressive wear) and fires once a smoothed
  value crosses an absolute alarm threshold — the basis of predictive maintenance.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import sqrt


@dataclass
class RollingZScore:
    """Flag a sample whose z-score over the last ``window`` points exceeds ``k``."""

    window: int = 30
    k: float = 4.0
    _buf: deque = field(default=None, repr=False)

    def __post_init__(self):
        self._buf = deque(maxlen=self.window)

    def update(self, x: float) -> tuple[bool, float]:
        buf = self._buf
        if len(buf) < max(5, self.window // 3):
            buf.append(x)
            return False, 0.0
        mean = sum(buf) / len(buf)
        var = sum((v - mean) ** 2 for v in buf) / len(buf)
        std = sqrt(var) or 1e-9
        z = (x - mean) / std
        buf.append(x)
        return abs(z) >= self.k, z


@dataclass
class EwmaTrend:
    """Exponentially-weighted mean; alarms when the smoothed value passes ``alarm``."""

    alpha: float = 0.05
    alarm: float = 2.5
    value: float = None

    def update(self, x: float) -> tuple[bool, float]:
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        return self.value >= self.alarm, self.value
