# industrial-retrofit

**Give a legacy machine a modern data voice.**
Raw Modbus registers → clean telemetry → anomaly detection (predictive maintenance) → **live OEE**.

![cover](assets/cover.png)

A 1995 industrial machine only speaks 16-bit registers: no units, no context, nothing
that leaves the shop floor. This project is the **retrofit layer** that turns that raw
stream into telemetry you can act on — without touching the PLC program, without
replacing the machine.

> **This is a real Modbus tool.** The bridge speaks the **actual Modbus-TCP protocol**
> (MBAP header + function 3) via [`modbus.py`](src/retrofit/modbus.py) — pure stdlib,
> no `pymodbus`. Point `--host` at any Modbus-TCP endpoint (PLC, gateway, SCADA) and
> nothing else changes. The repo also ships a **software device** (`retrofit serve`)
> that speaks the same protocol, so you can build and test without a PLC on your desk —
> the way Modbus tooling is normally developed. The device's register *values* are
> synthetic; the protocol and the tool are real (there is an end-to-end integration
> test over a real socket).

```
  ┌─────────────┐   Modbus     ┌───────────────────┐   JSON       ┌─────────────┐
  │   legacy    │  registers   │  RetrofitBridge   │  telemetry   │   MQTT /    │
  │   machine   │ ───────────▶ │  decode · units   │ ───────────▶ │   TSDB /    │
  │   (PLC)     │  0,1,2,3...  │  anomaly · OEE    │              │  dashboard  │
  └─────────────┘              └───────────────────┘              └─────────────┘
```

## What it does

- **Decoding** — 8 raw 16-bit registers → a typed dict in SI units (°C, mm/s, rpm),
  timestamped and ready to publish to MQTT / InfluxDB / a dashboard.
- **Predictive maintenance** — online anomaly detection, pure stdlib (it runs on an edge
  gateway): a rolling z-score for spikes, an EWMA for the slow drift of bearing wear →
  **an alarm before the breakdown**.
- **Live OEE** — Availability × Performance × Quality, accumulated over the shift.
- **Real Modbus-TCP, zero dependencies** — both a Modbus-TCP client *and* server in pure
  stdlib (`modbus.py`). The bridge reads from anything exposing
  `read_holding_registers(address, count)`: our network client, a
  `pymodbus.ModbusTcpClient`, or the bundled software device. The decoding path is
  identical either way.

## Quick start

```bash
pip install -e .
python -m retrofit run --ticks 400 --seed 5     # bundled device, over real Modbus-TCP
```

```
# polling Modbus-TCP device at 127.0.0.1:53017 (unit 1)
t=   222s    fault  rpm= 1819  T= 56.8C  vib=2.45mm/s  OEE= 69.1% !ANOMALY
...
-- shift summary --------------------------------
availability  70.2%   performance 100.0%   quality  96.4%
OEE           67.8%   parts 271 good / 10 reject
```

Split the device and the bridge across two processes, or poll a real PLC:

```bash
python -m retrofit serve --port 5020                  # expose the software device
python -m retrofit run --host 127.0.0.1 --port 5020   # (another shell) the bridge polls it
python -m retrofit run --host 192.168.0.10            # …or a real PLC / gateway
```

From Python:

```python
from retrofit import LegacyMachine, RetrofitBridge

machine = LegacyMachine(seed=1)
bridge  = RetrofitBridge(client=machine, ideal_cycle_s=2.0)

for rec in bridge.stream(ticks=600, machine=machine):
    if rec["maintenance_alarm"]:
        print("⚠ bearing wear — schedule maintenance", rec["vib_ewma"], "mm/s")
```

### Wiring it to a real PLC

```python
from retrofit import ModbusTcpClient, RetrofitBridge

client = ModbusTcpClient("192.168.0.10", port=502)   # our stdlib client (pymodbus works too)
bridge = RetrofitBridge(client=client)
while True:
    print(bridge.poll())
```

## Architecture

| Module | Role |
|--------|------|
| `modbus.py` | **Real Modbus-TCP** in pure stdlib: `ModbusTcpClient` (master) + `ModbusServer` (software device) |
| `machine_sim.py` | `LegacyMachine` (the machine model) + `LiveDevice` (the source served over Modbus) |
| `bridge.py` | The retrofit itself: read → decode → anomaly → OEE → JSON record |
| `anomaly.py` | `RollingZScore` (spikes) + `EwmaTrend` (wear drift), pure stdlib |
| `oee.py` | Availability / Performance / Quality / OEE + a shift accumulator |
| `cli.py` | `retrofit run` (bridge) · `retrofit serve` (device) |

## Tests

```bash
pytest -q          # 13 passed — including a client↔server Modbus round-trip over a real socket
```

## Stack

Python 3.9+ · **Modbus-TCP client & server in pure stdlib** (no dependency; `pymodbus`
is supported but not required) · `pytest` · cover art via Pillow/numpy/imageio.

---
MIT · a real industrial retrofit, honest and testable — real protocol, software device included.

---

<!-- hiddengrid-stack -->

## Part of the HiddenGrid edge stack

Eight small repos, one chain: **control → transport → hub → supervision**. Each one
stands alone and runs offline; together they are a working local-first stack with no
cloud account anywhere in it.

| | Repo | What it does |
|---|---|---|
| Control  | [greenhouse](https://github.com/Makeph/greenhouse) | ESP32/MicroPython greenhouse controller — light, aeration, heat and pulse irrigation. Safety lives in firmware. |
| Control  | [coopilot](https://github.com/Makeph/coopilot) | ESP32/MicroPython coop controller — pop-hole door with anti-pinch, overcurrent and timeout interlocks. |
| Transport  | [gorilla-tsc](https://github.com/Makeph/gorilla-tsc) | Lossless Gorilla time-series compression — the codec the edge→hub link stores with. |
| Hub  | [plexus](https://github.com/Makeph/plexus) | MQTT ingest → compressed store → drift & stuck-sensor detection → one dashboard. Stdlib only. |
| Product  | [serra](https://github.com/Makeph/serra) | Multi-site supervision for greenhouses & aquaponics, built on plexus. |
| Industry → | **industrial-retrofit** | Real Modbus-TCP off a legacy PLC → clean telemetry, anomalies, live OEE. |
| Industry  | [line-twin](https://github.com/Makeph/line-twin) | Measured cycle times → the bottleneck → the ROI of fixing it. |
| Industry  | [kiln-retrofit](https://github.com/Makeph/kiln-retrofit) | Type-K thermocouple → PID ramp/soak → heatwork & pyrometric cones. |

You are here: **industrial-retrofit**.
