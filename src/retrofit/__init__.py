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
from .machine_sim import LegacyMachine, LiveDevice
from .modbus import ModbusError, ModbusServer, ModbusTcpClient
from .oee import OeeAccumulator, oee

__all__ = [
    "LegacyMachine", "LiveDevice", "RetrofitBridge", "decode",
    "ModbusTcpClient", "ModbusServer", "ModbusError",
    "RollingZScore", "EwmaTrend", "OeeAccumulator", "oee",
]
__version__ = "0.1.0"
