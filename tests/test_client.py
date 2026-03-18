import socket
import threading

import pytest

from murmur.client import send_command, DaemonNotRunningError, DaemonTimeoutError


@pytest.fixture
def echo_server(tmp_path):
    """A simple echo server that responds to commands."""
    sock_path = str(tmp_path / "test.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    def serve():
        conn, _ = server.accept()
        data = conn.recv(4096).decode().strip()
        conn.sendall(f"OK {data}\n".encode())
        conn.close()
        server.close()

    t = threading.Thread(target=serve)
    t.start()
    yield sock_path
    t.join(timeout=2)


def test_send_command_success(echo_server):
    """Client sends command and receives response."""
    resp = send_command(echo_server, "status", timeout=2.0)
    assert resp == "OK status"


def test_daemon_not_running(tmp_path):
    """Client raises DaemonNotRunningError when socket doesn't exist."""
    with pytest.raises(DaemonNotRunningError):
        send_command(str(tmp_path / "nonexistent.sock"), "status", timeout=1.0)


def test_timeout(tmp_path):
    """Client raises DaemonTimeoutError when daemon doesn't respond."""
    sock_path = str(tmp_path / "slow.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    def serve():
        conn, _ = server.accept()
        import time
        time.sleep(5)
        conn.close()
        server.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    with pytest.raises(DaemonTimeoutError):
        send_command(sock_path, "status", timeout=1.0)
