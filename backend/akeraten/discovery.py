"""LAN discovery: lets the Android app find the backend running on the user's PC.

While the server runs, a background thread broadcasts a small JSON beacon over UDP
every couple of seconds:

    {"app": "AKERATEN", "version": "0.1", "port": 8000, "urls": ["http://192.168.1.20:8000/"]}

The app listens on the same UDP port and switches its backend URL to the first beacon
whose /api/health answers. Disable with AKERATEN_DISCOVERY=false.
"""
from __future__ import annotations

import json
import logging
import socket
import threading

from .config import env, env_bool

log = logging.getLogger("akeraten.discovery")

DISCOVERY_PORT = 47800
BEACON_APP = "AKERATEN"


def lan_ips() -> list[str]:
    """Best-effort list of this machine's private IPv4 addresses (no packets are sent)."""
    ips: list[str] = []
    try:  # the default-route interface; connect() on UDP only picks the route
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.append(info[4][0])
    except OSError:
        pass
    seen: list[str] = []
    for ip in ips:
        if ip not in seen and not ip.startswith("127.") and is_private(ip):
            seen.append(ip)
    return seen


def is_private(ip: str) -> bool:
    try:
        a, b = (int(x) for x in ip.split(".")[:2])
    except ValueError:
        return False
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def server_port() -> int:
    try:
        return int(env("AKERATEN_PORT", "8000"))
    except ValueError:
        return 8000


def beacon(port: int | None = None, ips: list[str] | None = None) -> dict:
    port = port or server_port()
    ips = lan_ips() if ips is None else ips
    return {
        "app": BEACON_APP,
        "version": "0.1",
        "port": port,
        "urls": [f"http://{ip}:{port}/" for ip in ips],
    }


class Beacon:
    """Daemon thread that broadcasts the beacon until stop() is called."""

    def __init__(self, interval: float = 2.0, port: int = DISCOVERY_PORT, targets: list[str] | None = None):
        self.interval = interval
        self.port = port
        self.targets = targets  # None = broadcast on every LAN interface
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Beacon":
        if not env_bool("AKERATEN_DISCOVERY", True):
            log.info("LAN discovery disabled (AKERATEN_DISCOVERY=false)")
            return self
        self._thread = threading.Thread(target=self._run, name="akeraten-beacon", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        logged = False
        while not self._stop.is_set():
            info = beacon()
            payload = json.dumps(info).encode()
            targets = self.targets or (
                {"255.255.255.255"} | {ip.rsplit(".", 1)[0] + ".255" for ip in lan_ips()})
            for target in targets:
                try:
                    sock.sendto(payload, (target, self.port))
                except OSError:
                    pass  # no network yet / interface down: keep looping
            if not logged and info["urls"]:
                log.info("LAN discovery beacon on UDP %s -> %s", self.port, ", ".join(info["urls"]))
                logged = True
            self._stop.wait(self.interval)
        sock.close()
