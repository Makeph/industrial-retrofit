"""Real Modbus-TCP, in pure standard library -- no pymodbus, just sockets.

This is what turns the retrofit from a demo into a tool: it speaks the actual
Modbus-TCP wire protocol (MBAP header + PDU, function code 3), so the same
`read_holding_registers(address, count)` the bridge already calls now goes over a
real socket. Point `ModbusTcpClient` at a real PLC or gateway and nothing else
changes; the bundled `ModbusServer` is a software device that speaks the same
protocol for development and CI.
"""
from __future__ import annotations

import socket
import socketserver
import struct
import threading

READ_HOLDING_REGISTERS = 3


class ModbusError(Exception):
    pass


def _recv_exact(conn: socket.socket, n: int):
    buf = b""
    while len(buf) < n:
        try:
            chunk = conn.recv(n - len(buf))
        except socket.timeout:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


class ModbusTcpClient:
    """Minimal Modbus-TCP master. Same interface as a pymodbus client and the
    simulator, so it drops straight into `RetrofitBridge(client=...)`."""

    def __init__(self, host: str, port: int = 502, unit: int = 1, timeout: float = 3.0) -> None:
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._tid = 0

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        if self._sock is None:
            self.connect()
        self._tid = (self._tid + 1) & 0xFFFF
        pdu = struct.pack(">BHH", READ_HOLDING_REGISTERS, address, count)
        self._sock.sendall(struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unit) + pdu)

        head = _recv_exact(self._sock, 7)
        if head is None:
            raise ModbusError("no response from %s:%d" % (self.host, self.port))
        tid, proto, length, _unit = struct.unpack(">HHHB", head)
        body = _recv_exact(self._sock, length - 1)
        if body is None or len(body) < 2:
            raise ModbusError("truncated response")
        fc = body[0]
        if fc & 0x80:
            raise ModbusError("Modbus exception code %d" % body[1])
        byte_count = body[1]
        data = body[2:2 + byte_count]
        return [struct.unpack(">H", data[i:i + 2])[0] for i in range(0, len(data), 2)]


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        conn = self.request
        conn.settimeout(self.server.read_timeout)
        while True:
            head = _recv_exact(conn, 7)
            if head is None:
                return
            tid, proto, length, unit = struct.unpack(">HHHB", head)
            pdu = _recv_exact(conn, length - 1)
            if pdu is None:
                return
            fc = pdu[0]
            if fc == READ_HOLDING_REGISTERS and len(pdu) >= 5:
                addr, count = struct.unpack(">HH", pdu[1:5])
                try:
                    regs = self.server.source.read_holding_registers(addr, count)
                    data = b"".join(struct.pack(">H", r & 0xFFFF) for r in regs)
                    resp = struct.pack(">BB", READ_HOLDING_REGISTERS, len(data)) + data
                except Exception:
                    resp = struct.pack(">BB", READ_HOLDING_REGISTERS | 0x80, 2)  # illegal data address
            else:
                resp = struct.pack(">BB", fc | 0x80, 1)  # illegal function
            conn.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)


class ModbusServer:
    """A software Modbus-TCP device. `source` is anything exposing
    `read_holding_registers(address, count)` -- e.g. a `LiveDevice` wrapping the
    machine simulator. Speaks the real protocol, so a real client (ours, pymodbus,
    or a SCADA tool) can poll it."""

    def __init__(self, source, host: str = "127.0.0.1", port: int = 502,
                 read_timeout: float = 30.0) -> None:
        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._srv = _Server((host, port), _Handler)
        self._srv.source = source
        self._srv.read_timeout = read_timeout

    @property
    def port(self) -> int:
        return self._srv.server_address[1]

    def serve_forever(self) -> None:
        self._srv.serve_forever()

    def start(self) -> "ModbusServer":
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
