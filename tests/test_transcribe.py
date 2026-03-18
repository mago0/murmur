from unittest.mock import MagicMock, patch
from dictation.transcribe import Transcriber


class FakeSegment:
    def __init__(self, text):
        self.text = text


@patch("dictation.transcribe.WhisperModel")
def test_transcribe_joins_segments(mock_model_cls):
    """Transcriber joins segment texts with spaces."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        iter([FakeSegment(" Hello "), FakeSegment(" world ")]),
        MagicMock(),
    )
    mock_model_cls.return_value = mock_model

    t = Transcriber(model="base.en", device="cpu", compute_type="int8")
    result = t.transcribe("/fake/audio.wav")
    assert result == "Hello world"


@patch("dictation.transcribe.WhisperModel")
def test_transcribe_empty_audio(mock_model_cls):
    """Transcriber returns empty string for silence."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([]), MagicMock())
    mock_model_cls.return_value = mock_model

    t = Transcriber(model="base.en", device="cpu", compute_type="int8")
    result = t.transcribe("/fake/audio.wav")
    assert result == ""


@patch("dictation.transcribe.WhisperModel")
def test_model_loaded_once(mock_model_cls):
    """Model is loaded at construction, not per-transcription."""
    mock_model_cls.return_value.transcribe.return_value = (iter([]), MagicMock())

    t = Transcriber(model="base.en", device="cpu", compute_type="int8")
    mock_model_cls.assert_called_once_with("base.en", device="cpu", compute_type="int8")
    t.transcribe("/fake/a.wav")
    t.transcribe("/fake/b.wav")
    # Constructor called once, transcribe called twice
    assert mock_model_cls.call_count == 1
    assert mock_model_cls.return_value.transcribe.call_count == 2
