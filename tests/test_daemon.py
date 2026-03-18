import os
import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from dictation.daemon import DictationDaemon


@pytest.fixture
def sock_path(tmp_path):
    return str(tmp_path / "test.sock")


@pytest.fixture
def log_path(tmp_path):
    return str(tmp_path / "history.log")


@pytest.fixture
def daemon(sock_path, log_path):
    """Create a daemon with a mocked transcriber."""
    with patch("dictation.daemon.Transcriber") as mock_cls:
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "hello world"
        mock_cls.return_value = mock_transcriber
        d = DictationDaemon(
            model="base.en",
            device="cpu",
            compute_type="int8",
            socket_path=sock_path,
            log_path=log_path,
        )
        yield d
        d.shutdown()


def send_command(sock_path: str, cmd: str, timeout: float = 5.0) -> str:
    """Helper to send a command and read response."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(sock_path)
    sock.sendall((cmd + "\n").encode())
    resp = sock.recv(4096).decode().strip()
    sock.close()
    return resp


def test_status_ready(daemon, sock_path):
    """Daemon responds 'ready' to status command."""
    t = threading.Thread(target=daemon.serve_one)
    t.start()
    resp = send_command(sock_path, "status")
    t.join(timeout=2)
    assert resp == "ready"


@patch("dictation.daemon.subprocess.run")
def test_transcribe_command(mock_run, daemon, sock_path, log_path, tmp_path):
    """Daemon transcribes audio and returns OK response."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"\x00" * 2000)

    t = threading.Thread(target=daemon.serve_one)
    t.start()
    resp = send_command(sock_path, f"transcribe {audio}")
    t.join(timeout=5)

    assert resp.startswith("OK ")
    assert "hello world" in resp
    # Verify log was written
    assert os.path.exists(log_path)
    with open(log_path) as f:
        line = f.readline()
    assert "hello world" in line


@patch("dictation.daemon.subprocess.run")
def test_transcribe_copies_to_clipboard(mock_run, daemon, sock_path, tmp_path):
    """Daemon calls wl-copy with the transcribed text."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"\x00" * 2000)

    t = threading.Thread(target=daemon.serve_one)
    t.start()
    send_command(sock_path, f"transcribe {audio}")
    t.join(timeout=5)

    # Find the wl-copy call among subprocess.run calls
    wl_copy_calls = [
        c for c in mock_run.call_args_list if c[0][0] == ["wl-copy"]
    ]
    assert len(wl_copy_calls) == 1
    assert wl_copy_calls[0][1]["input"] == b"hello world"


@patch("dictation.daemon.subprocess.run")
def test_transcribe_empty_returns_empty(mock_run, daemon, sock_path, tmp_path):
    """Daemon returns EMPTY when transcription produces no text."""
    # Override the mock transcriber to return empty
    daemon._transcriber.transcribe.return_value = ""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"\x00" * 2000)

    t = threading.Thread(target=daemon.serve_one)
    t.start()
    resp = send_command(sock_path, f"transcribe {audio}")
    t.join(timeout=5)
    assert resp == "EMPTY"


def test_unknown_command(daemon, sock_path):
    """Daemon responds with error for unknown commands."""
    t = threading.Thread(target=daemon.serve_one)
    t.start()
    resp = send_command(sock_path, "bogus")
    t.join(timeout=2)
    assert resp.startswith("ERR")


def test_shutdown_command(daemon, sock_path):
    """Daemon handles shutdown command gracefully."""
    t = threading.Thread(target=daemon.serve_one)
    t.start()
    resp = send_command(sock_path, "shutdown")
    t.join(timeout=2)
    assert resp == "OK"
    assert not os.path.exists(sock_path)
