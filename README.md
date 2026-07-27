# industrial-retrofit

**Donner une voix data moderne à une machine ancienne.**
Registres Modbus bruts → télémétrie propre → détection d'anomalie (maintenance prédictive) → **OEE en temps réel**.

![cover](assets/cover.png)

Une machine industrielle de 1995 ne parle que des registres 16 bits : pas d'unités, pas
de contexte, aucune remontée réseau. Ce projet est la **couche de rétrofit** qui transforme
ce flux brut en télémétrie exploitable — sans toucher à l'automate, sans remplacer la machine.

> **C'est un vrai outil Modbus.** Le bridge parle le **protocole Modbus-TCP réel**
> (trame MBAP + fonction 3) via [`modbus.py`](src/retrofit/modbus.py) — pur stdlib,
> sans `pymodbus`. Pointez `--host` sur n'importe quel équipement Modbus-TCP (PLC,
> passerelle, SCADA) et rien d'autre ne change. Le repo embarque aussi un **device
> logiciel** (`retrofit serve`) qui parle le même protocole, pour développer et tester
> sans automate sous la main — comme on développe tout outillage Modbus. Les valeurs
> des registres du device sont synthétiques ; le protocole et l'outil, eux, sont réels
> (test d'intégration bout-en-bout sur une vraie socket).

```
  ┌────────────┐   Modbus      ┌──────────────────┐   JSON       ┌────────────┐
  │  Machine    │  registres    │  RetrofitBridge   │  télémétrie  │  MQTT /     │
  │  legacy     │ ────────────▶ │  décode · unités  │ ───────────▶ │  TSDB /     │
  │  (PLC)      │  0,1,2,3...    │  anomalie · OEE   │              │  dashboard  │
  └────────────┘               └──────────────────┘              └────────────┘
```

## Ce que ça fait

- **Décodage** — 8 registres 16 bits → dict typé en unités SI (°C, mm/s, rpm), horodaté,
  prêt à publier sur MQTT / InfluxDB / un dashboard.
- **Maintenance prédictive** — détection d'anomalie en ligne, pur stdlib (tourne sur une
  passerelle edge) : z-score glissant pour les pics, EWMA pour la dérive lente d'usure de
  roulement → **alarme avant la panne**.
- **OEE temps réel** — Disponibilité × Performance × Qualité, accumulé sur le poste.
- **Vrai Modbus-TCP, zéro dépendance** — client *et* serveur Modbus-TCP en pur
  stdlib (`modbus.py`). Le bridge lit n'importe quel client
  `read_holding_registers(address, count)` : notre client réseau, un
  `pymodbus.ModbusTcpClient`, ou le device logiciel fourni. Le décodage ne change pas.

## Démarrage rapide

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

En Python :

```python
from retrofit import LegacyMachine, RetrofitBridge

machine = LegacyMachine(seed=1)
bridge  = RetrofitBridge(client=machine, ideal_cycle_s=2.0)

for rec in bridge.stream(ticks=600, machine=machine):
    if rec["maintenance_alarm"]:
        print("⚠ usure roulement — planifier maintenance", rec["vib_ewma"], "mm/s")
```

### Brancher un vrai automate

```python
from retrofit import ModbusTcpClient, RetrofitBridge

client = ModbusTcpClient("192.168.0.10", port=502)   # notre client stdlib (pymodbus marche aussi)
bridge = RetrofitBridge(client=client)
while True:
    print(bridge.poll())
```

## Architecture

| Module | Rôle |
|--------|------|
| `modbus.py` | **Vrai Modbus-TCP** en pur stdlib : `ModbusTcpClient` (master) + `ModbusServer` (device logiciel) |
| `machine_sim.py` | `LegacyMachine` (modèle de machine) + `LiveDevice` (source servie en Modbus) |
| `bridge.py` | Le rétrofit : lecture → décodage → anomalie → OEE → record JSON |
| `anomaly.py` | `RollingZScore` (pics) + `EwmaTrend` (dérive d'usure), pur stdlib |
| `oee.py` | Disponibilité / Performance / Qualité / OEE + accumulateur poste |
| `cli.py` | `retrofit run` (bridge) · `retrofit serve` (device) |

## Tests

```bash
pytest -q          # 13 passed — dont l'aller-retour Modbus client↔serveur sur socket réelle
```

## Stack

Python 3.9+ · **client & serveur Modbus-TCP en pur stdlib** (pas de dépendance ;
`pymodbus` supporté mais non requis) · `pytest` · assets visuels via Pillow/numpy/imageio.

---
MIT · un rétrofit industriel réel, honnête et testable — vrai protocole, device logiciel fourni.
