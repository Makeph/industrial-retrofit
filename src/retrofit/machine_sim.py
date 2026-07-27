"""Simulate a legacy CNC-style machine exposing a Modbus-like holding-register map.

The point of a *retrofit* is that the old machine speaks only raw 16-bit registers —
no units, no context, no network telemetry. This simulator reproduces exactly that
surface so the bridge layer (``retrofit.bridge``) can be tested offline, then pointed
at a real PLC (e.g. via ``pymodbus``) by swapping the client. The register map and
decode logic stay identical.

Register map (holding registers, 16-bit unsigned):

    0  STATUS            0=idle 1=running 2=fault
    1  SPINDLE_RPM       rpm
    2  TEMP_C_X10        spindle temperature, °C ×10
    3  VIBRATION_X100    bearing vibration, mm/s ×100
    4  CYCLE_COUNT_LO    32-bit cycle counter, low word
    5  CYCLE_COUNT_HI    32-bit cycle counter, high word
    6  GOOD_PARTS        good parts produced
    7  REJECT_PARTS      rejected parts
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field

# Register addresses (the only contract the legacy PLC gives you).
STATUS = 0
SPINDLE_RPM = 1
TEMP_C_X10 = 2
VIBRATION_X100 = 3
CYCLE_COUNT_LO = 4
CYCLE_COUNT_HI = 5
GOOD_PARTS = 6
REJECT_PARTS = 7
N_REGISTERS = 8

IDLE, RUNNING, FAULT = 0, 1, 2
U16 = 0xFFFF


@dataclass
class LegacyMachine:
    """Stateful simulator. Call :meth:`step` once per polling tick.

    A slow upward drift is injected into vibration to mimic progressive bearing
    wear — that is what the anomaly detector is meant to catch *before* failure.
    """

    seed: int = 42
    ideal_cycle_s: float = 2.0          # nominal seconds per part
    _t: int = 0
    _status: int = IDLE
    _rpm: float = 0.0
    _temp: float = 22.0
    _vib: float = 0.6                   # mm/s, healthy baseline
    _wear: float = 0.0                  # accumulated bearing wear
    _cycles: int = 0
    _good: int = 0
    _reject: int = 0
    _fault_left: int = 0
    _rng: random.Random = field(default=None, repr=False)

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    def step(self, dt_s: float = 1.0) -> None:
        r = self._rng
        self._t += 1

        # state machine: idle -> running, rare faults, recover to idle
        if self._fault_left > 0:
            self._fault_left -= 1
            self._status = FAULT
            self._rpm += (0 - self._rpm) * 0.4
            if self._fault_left == 0:
                self._status = IDLE
        elif self._status == IDLE:
            if r.random() < 0.30:
                self._status = RUNNING
        elif self._status == RUNNING:
            if r.random() < 0.015:                 # trip a fault
                self._fault_left = r.randint(3, 7)
            elif r.random() < 0.05:
                self._status = IDLE

        target_rpm = 6000.0 if self._status == RUNNING else 0.0
        self._rpm += (target_rpm - self._rpm) * 0.5 + r.gauss(0, 25)
        self._rpm = max(0.0, self._rpm)

        # temperature tracks load with thermal inertia
        target_temp = 22.0 + (self._rpm / 6000.0) * 40.0
        self._temp += (target_temp - self._temp) * 0.08 + r.gauss(0, 0.15)

        # vibration: baseline + load term + slow bearing wear + noise
        self._wear += (0.0009 if self._status == RUNNING else 0.0)
        load_term = (self._rpm / 6000.0) * 0.5
        self._vib = 0.6 + load_term + self._wear + abs(r.gauss(0, 0.05))
        if self._status == FAULT:
            self._vib += 1.5                       # fault rings the bearing

        # production counters
        if self._status == RUNNING:
            self._cycles += 1
            if r.random() < 0.97:
                self._good += 1
            else:
                self._reject += 1

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Mimic ``pymodbus`` client API: return ``count`` raw 16-bit registers."""
        regs = [0] * N_REGISTERS
        regs[STATUS] = self._status
        regs[SPINDLE_RPM] = int(self._rpm) & U16
        regs[TEMP_C_X10] = int(round(self._temp * 10)) & U16
        regs[VIBRATION_X100] = int(round(self._vib * 100)) & U16
        regs[CYCLE_COUNT_LO] = self._cycles & U16
        regs[CYCLE_COUNT_HI] = (self._cycles >> 16) & U16
        regs[GOOD_PARTS] = self._good & U16
        regs[REJECT_PARTS] = self._reject & U16
        if address < 0 or address + count > N_REGISTERS:
            raise IndexError(f"register window {address}..{address + count} out of range")
        return regs[address:address + count]


class LiveDevice:
    """Wraps a :class:`LegacyMachine` as a live Modbus source: each register read
    advances the simulation one tick. This is what a `ModbusServer` serves, turning
    the offline simulator into a real network device a Modbus client can poll.
    Thread-safe, since a threaded server may read from several connections.
    """

    def __init__(self, machine: "LegacyMachine", dt_s: float = 1.0) -> None:
        self._machine = machine
        self._dt = dt_s
        self._lock = threading.Lock()

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        with self._lock:
            self._machine.step(self._dt)
            return self._machine.read_holding_registers(address, count)
