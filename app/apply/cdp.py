"""Smallest CDP client over a WebSocket, stdlib only: measuring (app/docs/apply/vscode-browser/measure.py) and
the in-window fill trial (apply/window.py).
Talks to js-debug's CDP proxy (`extension.js-debug.requestCDPProxy` -> {host, port, path}) or to a
target's own `webSocketDebuggerUrl`. Events reach handlers on the reader thread: a handler may
send (fire and forget) but never wait on a reply there."""
import base64
import json
import os
import socket
import struct
import threading
import time


class Closed(Exception):
    pass


class ScriptError(RuntimeError):
    """The page's script threw: a real answer, never retried (a plain RuntimeError may be a page
    mid-navigation, worth another look)."""


class CDP:
    def __init__(self, host: str, port: int, path: str, timeout: float = 10):
        self.sock = socket.create_connection((host, port), timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1)
            if not chunk:
                raise Closed("handshake closed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise Closed(head.decode(errors="replace")[:200])
        self.sock.settimeout(None)
        self.lock, self.wlock = threading.Lock(), threading.Lock()
        self.n, self.waiting, self.replies = 0, {}, {}
        self.handlers: dict[str, list] = {}
        self.events: list[dict] = []
        self.keep_events = True
        self.closed = False
        threading.Thread(target=self._read, daemon=True).start()

    def _frame(self, op: int, data: bytes) -> None:
        head = bytes([0x80 | op])
        n = len(data)
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        with self.wlock:
            self.sock.sendall(head + mask + body)

    def _exact(self, n: int) -> bytes:
        out = b""
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise Closed("socket closed")
            out += chunk
        return out

    def _read(self) -> None:
        buf = b""
        try:
            while True:
                b0, b1 = self._exact(2)
                op, n = b0 & 0x0F, b1 & 0x7F
                if n == 126:
                    n = struct.unpack(">H", self._exact(2))[0]
                elif n == 127:
                    n = struct.unpack(">Q", self._exact(8))[0]
                mask = self._exact(4) if b1 & 0x80 else None
                data = self._exact(n)
                if mask:
                    data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
                if op == 0x9:
                    self._frame(0xA, data)
                    continue
                if op == 0x8:
                    raise Closed("close frame")
                if op in (0x1, 0x2, 0x0):
                    buf += data
                    if not b0 & 0x80:
                        continue
                    self._dispatch(json.loads(buf))
                    buf = b""
        except (Closed, OSError, ValueError):
            pass
        finally:
            self.closed = True
            with self.lock:
                for ev in self.waiting.values():
                    ev.set()

    def _dispatch(self, msg: dict) -> None:
        if "id" in msg and "method" not in msg:
            with self.lock:
                ev = self.waiting.pop(msg["id"], None)
                self.replies[msg["id"]] = msg
            if ev:
                ev.set()
            return
        if self.keep_events:
            self.events.append({"t": round(time.time(), 3), **msg})
        for fn in self.handlers.get(msg.get("method"), []) + self.handlers.get("*", []):
            try:
                fn(msg.get("params", {}), msg)
            except Exception as e:  # a handler bug must not kill the reader
                self.events.append({"handlerError": repr(e), "method": msg.get("method")})

    def post(self, method: str, params: dict | None = None) -> int:
        """Send without waiting -> id."""
        with self.lock:
            self.n += 1
            i = self.n
        self._frame(0x1, json.dumps({"id": i, "method": method, "params": params or {}}).encode())
        return i

    def send(self, method: str, params: dict | None = None, timeout: float = 15, session: str | None = None) -> dict:
        """-> result; raises RuntimeError w/ the CDP error, TimeoutError when no reply. session = a
        flat child session (Target.attachToTarget flatten true) on the same socket."""
        ev = threading.Event()
        with self.lock:
            self.n += 1
            i = self.n
            self.waiting[i] = ev
        msg = {"id": i, "method": method, "params": params or {}} | ({"sessionId": session} if session else {})
        self._frame(0x1, json.dumps(msg).encode())
        if not ev.wait(timeout):
            with self.lock:
                self.waiting.pop(i, None)
            raise TimeoutError(f"{method}: no reply in {timeout} s")
        with self.lock:
            msg = self.replies.pop(i, None)
        if msg is None:
            raise Closed(f"{method}: connection closed")
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error'].get('message')}")
        return msg.get("result", {})

    def on(self, method: str, fn) -> None:
        self.handlers.setdefault(method, []).append(fn)

    def evaluate(self, expr: str, timeout: float = 15, **extra):
        r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True, **extra}, timeout)
        if "exceptionDetails" in r:
            raise ScriptError(r["exceptionDetails"].get("exception", {}).get("description") or r["exceptionDetails"].get("text"))
        return r.get("result", {}).get("value")

    def close(self) -> None:
        try:
            self._frame(0x8, b"")
            self.sock.close()
        except OSError:
            pass
