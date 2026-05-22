"""Audio transcription with pluggable backends.

Backends:
  - "local": faster-whisper (CTranslate2 Whisper, runs on CPU/GPU locally).
  - "groq":  Groq-hosted Whisper-large-v3 via HTTP API (needs GROQ_API_KEY).

Both backends return the same TranscriptionResult shape so the CLI can
treat them interchangeably.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    duration: float | None
    segments: list[Segment]
    engine: str
    model: str

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# faster-whisper (local)
# ---------------------------------------------------------------------------

_LOCAL_MODEL_CACHE: dict[tuple[str, str, str], object] = {}


def _load_local_model(model: str, device: str, compute_type: str):
    key = (model, device, compute_type)
    if key not in _LOCAL_MODEL_CACHE:
        from faster_whisper import WhisperModel  # lazy import

        _LOCAL_MODEL_CACHE[key] = WhisperModel(
            model, device=device, compute_type=compute_type
        )
    return _LOCAL_MODEL_CACHE[key]


def _transcribe_local(
    audio_path: str | os.PathLike,
    model: str = "base",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "int8",
) -> TranscriptionResult:
    wm = _load_local_model(model, device, compute_type)
    segments_iter, info = wm.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
    )
    segments: list[Segment] = []
    parts: list[str] = []
    for seg in segments_iter:
        segments.append(Segment(start=seg.start, end=seg.end, text=seg.text))
        parts.append(seg.text)
    return TranscriptionResult(
        text="".join(parts).strip(),
        language=getattr(info, "language", None),
        duration=getattr(info, "duration", None),
        segments=segments,
        engine="local",
        model=model,
    )


# ---------------------------------------------------------------------------
# Groq (hosted Whisper)
# ---------------------------------------------------------------------------

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_DEFAULT_MODEL = "whisper-large-v3"


def _transcribe_groq(
    audio_path: str | os.PathLike,
    model: str = GROQ_DEFAULT_MODEL,
    language: str | None = None,
    api_key: str | None = None,
) -> TranscriptionResult:
    import requests  # lazy import

    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Export it or pass --api-key."
        )

    data = {
        "model": model,
        "response_format": "verbose_json",
    }
    if language:
        data["language"] = language

    with open(audio_path, "rb") as f:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            data=data,
            files={"file": (Path(audio_path).name, f)},
            timeout=600,
        )
    resp.raise_for_status()
    payload = resp.json()

    segments = [
        Segment(start=s.get("start", 0.0), end=s.get("end", 0.0), text=s.get("text", ""))
        for s in payload.get("segments", [])
    ]
    return TranscriptionResult(
        text=payload.get("text", "").strip(),
        language=payload.get("language"),
        duration=payload.get("duration"),
        segments=segments,
        engine="groq",
        model=model,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def transcribe(
    audio_path: str | os.PathLike,
    engine: str = "local",
    model: str | None = None,
    language: str | None = None,
    **kwargs,
) -> TranscriptionResult:
    if engine == "local":
        return _transcribe_local(
            audio_path,
            model=model or "base",
            language=language,
            device=kwargs.get("device", "auto"),
            compute_type=kwargs.get("compute_type", "int8"),
        )
    if engine == "groq":
        return _transcribe_groq(
            audio_path,
            model=model or GROQ_DEFAULT_MODEL,
            language=language,
            api_key=kwargs.get("api_key"),
        )
    raise ValueError(f"Unknown engine: {engine!r} (use 'local' or 'groq')")


def write_outputs(result: TranscriptionResult, audio_path: str | os.PathLike) -> tuple[Path, Path]:
    """Write <stem>.txt and <stem>.json next to the audio file. Returns both paths."""
    stem = Path(audio_path).with_suffix("")
    txt_path = stem.with_suffix(".txt")
    json_path = stem.with_suffix(".json")
    txt_path.write_text(result.text, encoding="utf-8")
    json_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return txt_path, json_path
