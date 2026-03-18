import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    model: str
    device: str
    compute_type: str
    audio_source: str
    socket_path: str
    log_path: str
    tmpdir: str


def get_config() -> Config:
    uid = os.getuid()
    home = Path.home()
    return Config(
        model=os.environ.get("DICTATION_MODEL", "small.en"),
        device=os.environ.get("DICTATION_DEVICE", "cuda"),
        compute_type=os.environ.get("DICTATION_COMPUTE_TYPE", "float16"),
        audio_source=os.environ.get(
            "DICTATION_AUDIO_SOURCE",
            "alsa_input.usb-HP__Inc_HyperX_Cloud_II_Core_Wireless-00.mono-fallback",
        ),
        socket_path=os.environ.get(
            "DICTATION_SOCKET",
            f"/run/user/{uid}/dictation.sock",
        ),
        log_path=os.environ.get(
            "DICTATION_LOG",
            str(home / ".local" / "share" / "dictation" / "history.log"),
        ),
        tmpdir=os.environ.get("DICTATION_TMPDIR", "/tmp"),
    )
