from retrofit import machine_sim as rm
from retrofit.bridge import RetrofitBridge, decode
from retrofit.machine_sim import LegacyMachine


def test_decode_round_trips_registers():
    regs = [0] * rm.N_REGISTERS
    regs[rm.STATUS] = rm.RUNNING
    regs[rm.SPINDLE_RPM] = 5999
    regs[rm.TEMP_C_X10] = 615           # 61.5 C
    regs[rm.VIBRATION_X100] = 247       # 2.47 mm/s
    regs[rm.CYCLE_COUNT_LO] = 0x0001
    regs[rm.CYCLE_COUNT_HI] = 0x0001    # -> 65537
    regs[rm.GOOD_PARTS] = 90
    regs[rm.REJECT_PARTS] = 10
    r = decode(regs)
    assert r["status"] == "running"
    assert r["temperature_c"] == 61.5
    assert r["vibration_mm_s"] == 2.47
    assert r["cycle_count"] == 65537


def test_bridge_record_is_complete_and_serialisable():
    import json
    machine = LegacyMachine(seed=7)
    bridge = RetrofitBridge(client=machine)
    rec = None
    for rec in bridge.stream(ticks=50, machine=machine):
        pass
    for key in ("status", "spindle_rpm", "temperature_c", "vibration_mm_s",
                "anomaly", "maintenance_alarm", "oee", "availability"):
        assert key in rec
    json.dumps(rec)                      # must be JSON-serialisable
    assert 0.0 <= rec["oee"] <= 1.0


def test_wear_eventually_triggers_maintenance_alarm():
    machine = LegacyMachine(seed=3)
    bridge = RetrofitBridge(client=machine, vib_alarm=2.5)
    alarmed = any(rec["maintenance_alarm"]
                  for rec in bridge.stream(ticks=2000, machine=machine))
    assert alarmed, "bearing wear should eventually cross the maintenance threshold"
