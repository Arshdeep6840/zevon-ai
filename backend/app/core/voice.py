"""Local voice: faster-whisper (speech-to-text) and Piper (text-to-speech). Both optional and lazy-loaded."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading

_whisper = None
_lock = threading.Lock()


def stt_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def tts_available(cfg) -> bool:
    return bool(cfg.piper_model) and os.path.exists(cfg.piper_model) and importlib.util.find_spec("piper") is not None


def transcribe(audio: bytes, cfg) -> str:
    global _whisper
    from faster_whisper import WhisperModel
    with _lock:
        if _whisper is None:
            _whisper = WhisperModel(cfg.whisper_model, compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio)
        path = f.name
    try:
        segments, _ = _whisper.transcribe(path, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(path)


def synthesize(text: str, cfg) -> bytes:
    """Run the Piper CLI (stable across versions): text on stdin -> WAV file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    try:
        subprocess.run([sys.executable, "-m", "piper", "--model", cfg.piper_model, "--output_file", out],
                       input=text[:1500].encode(), check=True, capture_output=True, timeout=60)
        with open(out, "rb") as fh:
            return fh.read()
    finally:
        os.unlink(out)
