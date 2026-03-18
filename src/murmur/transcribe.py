from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model: str, device: str, compute_type: str):
        self._model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str) -> str:
        segments, info = self._model.transcribe(
            audio_path,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 1000,
                "speech_pad_ms": 300,
            },
        )
        parts = []
        for seg in segments:
            parts.append(seg.text.strip())
        text = " ".join(parts)
        return text.strip()
