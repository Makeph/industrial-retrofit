"""End-to-end tests over a real Modbus-TCP socket: the bundled software device
served by ModbusServer, polled by ModbusTcpClient and driven through the bridge.
No mocks -- actual MBAP frames on a loopback socket.
"""
from retrofit.bridge import RetrofitBridge
from retrofit.machine_sim import LegacyMachine, LiveDevice
from retrofit.modbus import ModbusError, ModbusServer, ModbusTcpClient


def test_client_server_roundtrip():
    with ModbusServer(LiveDevice(LegacyMachine(seed=1)), port=0) as srv:
        with ModbusTcpClient("127.0.0.1", srv.port) as client:
            regs = client.read_holding_registers(0, 8)
    assert len(regs) == 8
    assert all(0 <= r <= 0xFFFF for r in regs)


def test_partial_window():
    with ModbusServer(LiveDevice(LegacyMachine(seed=2)), port=0) as srv:
        with ModbusTcpClient("127.0.0.1", srv.port) as client:
            two = client.read_holding_registers(1, 2)  # rpm + temp only
    assert len(two) == 2


def test_out_of_range_raises_modbus_exception():
    with ModbusServer(LiveDevice(LegacyMachine(seed=1)), port=0) as srv:
        client = ModbusTcpClient("127.0.0.1", srv.port)
        client.connect()
        raised = False
        try:
            client.read_holding_registers(0, 99)  # window past the register map
        except ModbusError:
            raised = True
        finally:
            client.close()
    assert raised


def test_bridge_over_real_socket():
    with ModbusServer(LiveDevice(LegacyMachine(seed=3)), port=0) as srv:
        client = ModbusTcpClient("127.0.0.1", srv.port)
        bridge = RetrofitBridge(client=client)
        records = [bridge.poll(dt_s=1.0, now=float(i)) for i in range(40)]
        client.close()
    assert len(records) == 40
    last = records[-1]
    assert last["status"] in ("idle", "running", "fault")
    assert 0.0 <= last["oee"] <= 1.0
    assert last["cycle_count"] >= 0
