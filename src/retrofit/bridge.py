"""The retrofit bridge: raw legacy registers -> clean, contextualised telemetry.

This is the layer that gives an old machine a modern voice. It:

1. reads the holding registers from *any* client exposing
   ``read_holding_registers(address, count)`` (the simulator, or a real
   ``pymodbus`` ``ModbusTcpClient`` — same method signature);
2. decodes them into SI units with names and a timestamp;
3. runs online anomaly detection (predictive maintenance);
4. accumulates a live OEE figure.

Each poll yields one JSON-serialisable record ready to publish to MQTT / a
time-series DB / a dashboard.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator, Protocol

from . import machine_sim as rm
from .anomaly import EwmaTrend, RollingZScore
from .oee import OeeAccumulator

STATUS_NAMES = {rm.IDLE: "idle", rm.RUNNING: "running", rm.FAULT: "fault"}


class RegisterClient(Protocol):
    def read_holding_registers(self, address: int, count: int) -> list[int]: ...


def decode(regs: list[int]) -> dict:
    """Turn 8 raw 16-bit registers into a typed, unit-bearing reading."""
    cycles = regs[rm.CYCLE_COUNT_LO] | (regs[rm.CYCLE_COUNT_HI] << 16)
    return {
        "status": STATUS_NAMES.get(regs[rm.STATUS], "unknown"),
        "spindle_rpm": regs[rm.SPINDLE_RPM],
        "temperature_c": regs[rm.TEMP_C_X10] / 10.0,
        "vibration_mm_s": regs[rm.VIBRATION_X100] / 100.0,
        "cycle_count": cycles,
        "good_parts": regs[rm.GOOD_PARTS],
        "reject_parts": regs[rm.REJECT_PARTS],
    }


@dataclass
class RetrofitBridge:
    client: RegisterClient
    ideal_cycle_s: float = 2.0
    vib_alarm: float = 2.5
    _spike: RollingZScore = field(default=None, repr=False)
    _trend: EwmaTrend = field(default=None, repr=False)
    _oee: OeeAccumulator = field(default=None, repr=False)

    def __post_init__(self):
        self._spike = RollingZScore(window=30, k=4.0)
        self._trend = EwmaTrend(alpha=0.05, alarm=self.vib_alarm)
        self._oee = OeeAccumulator(ideal_cycle_s=self.ideal_cycle_s)

    def poll(self, dt_s: float = 1.0, now: float | None = None) -> dict:
        regs = self.client.read_holding_registers(0, rm.N_REGISTERS)
        r = decode(regs)
        spike, z = self._spike.update(r["vibration_mm_s"])
        wear_alarm, vib_ewma = self._trend.update(r["vibration_mm_s"])
        self._oee.tick(running=(r["status"] == "running"),
                       total_count=r["good_parts"] + r["reject_parts"],
                       good_count=r["good_parts"], dt_s=dt_s)
        r.update({
            "ts": now if now is not None else time.time(),
            "vib_zscore": round(z, 2),
            "vib_ewma": round(vib_ewma, 3),
            "anomaly": bool(spike),
            "maintenance_alarm": bool(wear_alarm),
            **self._oee.snapshot(),
        })
        return r

    def stream(self, ticks: int, dt_s: float = 1.0,
               machine: "rm.LegacyMachine | None" = None) -> Iterator[dict]:
        """Convenience driver for the simulator: step + poll ``ticks`` times."""
        t0 = 0.0
        for _ in range(ticks):
            if machine is not None:
                machine.step(dt_s)
            yield self.poll(dt_s=dt_s, now=t0)
            t0 += dt_s
