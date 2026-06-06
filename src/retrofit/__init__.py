"""industrial-retrofit — give a legacy machine a modern data voice.

Public API:

    from retrofit import LegacyMachine, RetrofitBridge, decode

    machine = LegacyMachine(seed=1)
    bridge = RetrofitBridge(client=machine)
    for record in bridge.stream(ticks=600, machine=machine):
        print(record)
"""
from .anomaly import EwmaTrend, RollingZScore
from .bridge import RetrofitBridge, decode
from .machine_sim import LegacyMachine
from .oee import OeeAccumulator, oee

__all__ = [
    "LegacyMachine", "RetrofitBridge", "decode",
    "RollingZScore", "EwmaTrend", "OeeAccumulator", "oee",
]
__version__ = "0.1.0"
