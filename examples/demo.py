"""Minimal end-to-end demo: legacy machine -> retrofit bridge -> telemetry + KPIs.

    python examples/demo.py
"""
from retrofit import LegacyMachine, RetrofitBridge

machine = LegacyMachine(seed=1)
bridge = RetrofitBridge(client=machine, ideal_cycle_s=2.0)

anomalies = 0
last = None
for rec in bridge.stream(ticks=600, machine=machine):
    last = rec
    anomalies += rec["anomaly"]

print(f"final OEE        : {last['oee'] * 100:.1f}%")
print(f"availability     : {last['availability'] * 100:.1f}%")
print(f"quality          : {last['quality'] * 100:.1f}%")
print(f"vibration (ewma) : {last['vib_ewma']:.2f} mm/s")
print(f"spike anomalies  : {anomalies}")
print(f"maintenance alarm: {last['maintenance_alarm']}")
