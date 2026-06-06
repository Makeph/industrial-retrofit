"""CLI: drive the simulator through the bridge and print live telemetry.

    python -m retrofit run --ticks 60 --json
    python -m retrofit run --ticks 600            # human-readable + final OEE
"""
from __future__ import annotations

import argparse
import json

from .bridge import RetrofitBridge
from .machine_sim import LegacyMachine


def run(args: argparse.Namespace) -> int:
    machine = LegacyMachine(seed=args.seed)
    bridge = RetrofitBridge(client=machine, ideal_cycle_s=args.ideal_cycle)
    last = None
    for rec in bridge.stream(ticks=args.ticks, machine=machine):
        last = rec
        if args.json:
            print(json.dumps(rec))
        else:
            flag = " !ANOMALY" if rec["anomaly"] else ""
            flag += " !MAINT" if rec["maintenance_alarm"] else ""
            print(f"t={rec['ts']:6.0f}s  {rec['status']:>7}  "
                  f"rpm={rec['spindle_rpm']:5d}  T={rec['temperature_c']:5.1f}C  "
                  f"vib={rec['vibration_mm_s']:4.2f}mm/s  OEE={rec['oee']*100:5.1f}%{flag}")
    if last and not args.json:
        print("\n-- shift summary --------------------------------")
        print(f"availability {last['availability']*100:5.1f}%   "
              f"performance {last['performance']*100:5.1f}%   "
              f"quality {last['quality']*100:5.1f}%")
        print(f"OEE          {last['oee']*100:5.1f}%   "
              f"parts {last['good_parts']} good / {last['reject_parts']} reject")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="retrofit", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the simulated retrofit bridge")
    r.add_argument("--ticks", type=int, default=120)
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--ideal-cycle", type=float, default=2.0, dest="ideal_cycle")
    r.add_argument("--json", action="store_true", help="emit JSON lines")
    r.set_defaults(func=run)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
