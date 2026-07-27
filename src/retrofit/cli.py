"""CLI: run the retrofit bridge over real Modbus-TCP, or expose a software device.

    python -m retrofit run --ticks 600          # loopback: bundled device + bridge
    python -m retrofit run --host 192.168.0.10   # poll a real PLC / gateway
    python -m retrofit serve --port 5020         # expose the software device on TCP
"""
from __future__ import annotations

import argparse
import json

from .bridge import RetrofitBridge
from .machine_sim import LegacyMachine, LiveDevice
from .modbus import ModbusServer, ModbusTcpClient


def run(args: argparse.Namespace) -> int:
    # No --host: stand up the bundled software device on a loopback port, so the
    # demo still exercises the real Modbus-TCP protocol end to end. With --host,
    # poll a real device instead and change nothing else.
    server = None
    if args.host is None:
        server = ModbusServer(LiveDevice(LegacyMachine(seed=args.seed)),
                              host="127.0.0.1", port=0).start()
        host, port = "127.0.0.1", server.port
    else:
        host, port = args.host, args.port

    client = ModbusTcpClient(host, port, unit=args.unit)
    bridge = RetrofitBridge(client=client, ideal_cycle_s=args.ideal_cycle)
    if not args.json:
        print(f"# polling Modbus-TCP device at {host}:{port} (unit {args.unit})")

    last = None
    t0 = 0.0
    try:
        for _ in range(args.ticks):
            rec = bridge.poll(dt_s=1.0, now=t0)
            t0 += 1.0
            last = rec
            if args.json:
                print(json.dumps(rec))
            else:
                flag = " !ANOMALY" if rec["anomaly"] else ""
                flag += " !MAINT" if rec["maintenance_alarm"] else ""
                print(f"t={rec['ts']:6.0f}s  {rec['status']:>7}  "
                      f"rpm={rec['spindle_rpm']:5d}  T={rec['temperature_c']:5.1f}C  "
                      f"vib={rec['vibration_mm_s']:4.2f}mm/s  OEE={rec['oee'] * 100:5.1f}%{flag}")
    finally:
        client.close()
        if server is not None:
            server.stop()

    if last and not args.json:
        print("\n-- shift summary --------------------------------")
        print(f"availability {last['availability'] * 100:5.1f}%   "
              f"performance {last['performance'] * 100:5.1f}%   "
              f"quality {last['quality'] * 100:5.1f}%")
        print(f"OEE          {last['oee'] * 100:5.1f}%   "
              f"parts {last['good_parts']} good / {last['reject_parts']} reject")
    return 0


def serve(args: argparse.Namespace) -> int:
    device = LiveDevice(LegacyMachine(seed=args.seed))
    srv = ModbusServer(device, host=args.host, port=args.port)
    print(f"retrofit: software Modbus-TCP device on {args.host}:{args.port} (unit 1) — Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="retrofit", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the retrofit bridge over Modbus-TCP")
    r.add_argument("--host", default=None, help="Modbus device host (default: bundled loopback device)")
    r.add_argument("--port", type=int, default=502, help="Modbus TCP port (default 502)")
    r.add_argument("--unit", type=int, default=1, help="Modbus unit / slave id")
    r.add_argument("--ticks", type=int, default=120)
    r.add_argument("--seed", type=int, default=42, help="seed for the bundled device")
    r.add_argument("--ideal-cycle", type=float, default=2.0, dest="ideal_cycle")
    r.add_argument("--json", action="store_true", help="emit JSON lines")
    r.set_defaults(func=run)

    s = sub.add_parser("serve", help="expose the bundled software device over Modbus-TCP")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=5020)
    s.add_argument("--seed", type=int, default=42)
    s.set_defaults(func=serve)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
