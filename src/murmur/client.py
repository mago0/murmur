import socket
import subprocess
import sys

from murmur.config import get_config


class DaemonNotRunningError(Exception):
    pass


class DaemonTimeoutError(Exception):
    pass


def send_command(socket_path: str, command: str, timeout: float = 30.0) -> str:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect(socket_path)
    except (FileNotFoundError, ConnectionRefusedError):
        raise DaemonNotRunningError(f"Cannot connect to {socket_path}")

    try:
        sock.sendall((command + "\n").encode())
        data = sock.recv(65536).decode().strip()
        return data
    except socket.timeout:
        raise DaemonTimeoutError(f"Timed out after {timeout}s waiting for response")
    finally:
        sock.close()


def _notify(title: str, body: str, timeout_ms: int = 3000):
    try:
        subprocess.run(
            ["notify-send", title, body, "-t", str(timeout_ms)],
            check=False, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass


def main():
    cfg = get_config()
    args = sys.argv[1:]

    if not args:
        print("Usage: murmur-client <command> [args...]", file=sys.stderr)
        sys.exit(1)

    command = " ".join(args)

    try:
        response = send_command(cfg.socket_path, command)
        print(response)
    except DaemonNotRunningError:
        _notify("Murmur", "Daemon not running")
        sys.exit(1)
    except DaemonTimeoutError:
        _notify("Murmur", "Timed out")
        sys.exit(1)
