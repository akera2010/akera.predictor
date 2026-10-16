import json
import socket

from akeraten.discovery import DISCOVERY_PORT, Beacon, beacon, is_private


def test_is_private():
    assert is_private("192.168.1.20") and is_private("10.0.0.5") and is_private("172.20.1.1")
    assert not is_private("8.8.8.8") and not is_private("172.40.0.1") and not is_private("bad")


def test_beacon_payload():
    b = beacon(port=8123, ips=["192.168.1.20"])
    assert b["app"] == "AKERATEN" and b["port"] == 8123
    assert b["urls"] == ["http://192.168.1.20:8123/"]


def test_beacon_thread_sends_udp():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("", 0))
    rx.settimeout(3)
    port = rx.getsockname()[1]
    b = Beacon(interval=0.2, port=port, targets=["127.0.0.1"]).start()
    try:
        data, _ = rx.recvfrom(4096)
        assert json.loads(data)["app"] == "AKERATEN"
    finally:
        b.stop()
        rx.close()
    assert DISCOVERY_PORT == 47800


def test_connect_endpoint():
    from fastapi.testclient import TestClient

    from akeraten.main import app

    with TestClient(app) as client:
        r = client.get("/api/connect")
        assert r.status_code == 200
    body = r.json()
    assert body["app"] == "AKERATEN" and body["discovery_udp_port"] == 47800
