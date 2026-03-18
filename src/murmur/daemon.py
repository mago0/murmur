import logging
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from murmur.config import get_config
from murmur.transcribe import Transcriber

logger = logging.getLogger("murmur")


class MurmurDaemon:
    def __init__(
        self,
        model: str,
        device: str,
        compute_type: str,
        socket_path: str,
        log_path: str,
    ):
        self._socket_path = socket_path
        self._log_path = log_path
        self._running = False
        self._busy = False
        self._server: socket.socket | None = None

        # Create log directory
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)

        # Remove stale socket
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        # Load model
        logger.info("Loading model %s on %s (%s)...", model, device, compute_type)
        self._transcriber = Transcriber(model, device, compute_type)
        logger.info("Model loaded")

        # Bind socket
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(socket_path)
        self._server.listen(2)
        self._server.settimeout(1.0)

    def serve_one(self):
        """Accept and handle a single connection. Used for testing."""
        conn, _ = self._server.accept()
        self._handle(conn)

    def run(self):
        """Main loop - accept connections until shutdown."""
        self._running = True
        logger.info("Listening on %s", self._socket_path)
        while self._running:
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle(conn)

    def _handle(self, conn: socket.socket):
        try:
            data = conn.recv(4096).decode().strip()
            if not data:
                conn.close()
                return

            parts = data.split(maxsplit=1)
            cmd = parts[0]

            if cmd == "status":
                state = "busy" if self._busy else "ready"
                conn.sendall(f"{state}\n".encode())

            elif cmd == "transcribe" and len(parts) == 2:
                audio_path = parts[1]
                self._busy = True
                try:
                    text = self._transcriber.transcribe(audio_path)
                    if text:
                        self._copy_to_clipboard(text)
                        self._log(text)
                        self._notify(text)
                        self._cleanup_audio(audio_path)
                        conn.sendall(f"OK {text}\n".encode())
                    else:
                        self._notify_empty()
                        conn.sendall(b"EMPTY\n")
                except Exception as e:
                    logger.error("Transcription failed: %s", e)
                    conn.sendall(f"ERR transcription failed: {e}\n".encode())
                finally:
                    self._busy = False

            elif cmd == "shutdown":
                conn.sendall(b"OK\n")
                conn.close()
                self.shutdown()
                return

            else:
                conn.sendall(f"ERR unknown command: {data}\n".encode())
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _copy_to_clipboard(self, text: str):
        try:
            subprocess.run(
                ["wl-copy"], input=text.encode(), check=True, timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Failed to copy to clipboard")

    def _log(self, text: str):
        timestamp = datetime.now().isoformat(timespec="seconds")
        line = f"{timestamp} | {text}\n"
        try:
            with open(self._log_path, "a") as f:
                f.write(line)
        except OSError:
            logger.warning("Failed to write to log %s", self._log_path)

    def _notify(self, text: str):
        display = text[:200] + "..." if len(text) > 200 else text
        try:
            subprocess.run(
                ["notify-send", "Murmur", display, "-t", "4000"],
                check=False, timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    def _notify_empty(self):
        try:
            subprocess.run(
                ["notify-send", "Murmur", "Nothing transcribed", "-t", "2000"],
                check=False, timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    def _cleanup_audio(self, path: str):
        try:
            os.unlink(path)
        except OSError:
            pass

    def shutdown(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass
        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except OSError:
                pass


def _ensure_cuda_ld_path():
    """Re-exec with LD_LIBRARY_PATH pointing to NVIDIA pip package libs.

    Setting LD_LIBRARY_PATH in Python is too late - the dynamic linker
    has already resolved shared libraries by the time Python runs. So we
    detect the needed paths, set the env var, and os.execv ourselves.
    The _MURMUR_CUDA_READY sentinel prevents infinite re-exec loops.
    """
    if os.environ.get("_MURMUR_CUDA_READY"):
        return

    import site
    site_packages = site.getsitepackages()
    if not site_packages:
        return
    nvidia_base = Path(site_packages[0]) / "nvidia"
    if not nvidia_base.is_dir():
        return
    lib_dirs = [str(p) for p in nvidia_base.glob("*/lib") if p.is_dir()]
    if not lib_dirs:
        return

    existing = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([existing] if existing else []))
    os.environ["_MURMUR_CUDA_READY"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    _ensure_cuda_ld_path()
    cfg = get_config()

    daemon = MurmurDaemon(
        model=cfg.model,
        device=cfg.device,
        compute_type=cfg.compute_type,
        socket_path=cfg.socket_path,
        log_path=cfg.log_path,
    )

    def _signal_handler(signum, frame):
        logger.info("Received signal %s, shutting down", signum)
        daemon.shutdown()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    daemon.run()
