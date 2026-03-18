#!/bin/bash
# dictate-toggle.sh - Toggle voice dictation recording
# Press once to start recording, press again to stop and transcribe.
# Result is copied to clipboard.

set -euo pipefail

# Defaults (same as Python config.py - keep in sync)
DICTATION_TMPDIR="${DICTATION_TMPDIR:-/tmp}"
DICTATION_AUDIO_SOURCE="${DICTATION_AUDIO_SOURCE:-alsa_input.usb-HP__Inc_HyperX_Cloud_II_Core_Wireless-00.mono-fallback}"
DICTATION_SOCKET="${DICTATION_SOCKET:-/run/user/$(id -u)/dictation.sock}"

PIDFILE="$DICTATION_TMPDIR/dictation.pid"
AUDIOFILE="$DICTATION_TMPDIR/dictation-capture.wav"

notify() {
    notify-send "Dictation" "$1" -t "${2:-2000}" 2>/dev/null || true
}

# Check for stale PID file
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ! kill -0 "$PID" 2>/dev/null; then
        # Process is dead - stale PID file
        rm -f "$PIDFILE"
    fi
fi

if [ -f "$PIDFILE" ]; then
    # --- STOP RECORDING ---
    PID=$(cat "$PIDFILE")
    rm -f "$PIDFILE"

    # SIGINT lets pw-record finalize the WAV header
    kill -INT "$PID" 2>/dev/null || true
    # wait only works for child processes; poll since this is a different invocation
    while kill -0 "$PID" 2>/dev/null; do sleep 0.05; done

    # Validate audio file
    if [ ! -f "$AUDIOFILE" ] || [ "$(stat -c%s "$AUDIOFILE" 2>/dev/null || echo 0)" -lt 1024 ]; then
        notify "Nothing captured"
        rm -f "$AUDIOFILE"
        exit 0
    fi

    notify "Transcribing..." 1500

    # Send to daemon
    dictation-client transcribe "$AUDIOFILE"

else
    # --- START RECORDING ---
    notify "Recording..." 1500

    pw-record \
        --target="$DICTATION_AUDIO_SOURCE" \
        --format=s16 \
        --rate=16000 \
        --channels=1 \
        "$AUDIOFILE" &
    PW_PID=$!

    # Verify pw-record started successfully
    sleep 0.2
    if ! kill -0 "$PW_PID" 2>/dev/null; then
        notify "Mic not available"
        rm -f "$AUDIOFILE"
        exit 1
    fi

    echo "$PW_PID" > "$PIDFILE"
fi
