"""Audio transcription with pluggable backends.

Backends:
  - "local": faster-whisper (CTranslate2 Whisper, runs on CPU/GPU locally).
  - "groq":  Groq-hosted Whisper-large-v3 via HTTP API (needs GROQ_API_KEY).

Both backends return the same TranscriptionResult shape so the CLI can
treat them interchangeably.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
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

# Groq's hard upload limit for whisper-large-v3 is 25 MB on the free tier
# (100 MB on dev). Stay safely under the free-tier ceiling.
GROQ_MAX_UPLOAD_BYTES = 24 * 1024 * 1024
GROQ_CHUNK_SECONDS = 600  # 10 min chunks when we must split


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError("ffmpeg failed: " + " | ".join(tail))


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip())


def _recompress_for_groq(src: Path, dst: Path) -> None:
    """Transcode to 16 kHz mono FLAC – Whisper resamples to 16 kHz internally,
    so this is loss-free for the model and shrinks most podcasts 3–5×."""
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", str(src),
        "-ar", "16000", "-ac", "1", "-map", "0:a",
        "-c:a", "flac",
        str(dst),
    ])


def _split_for_groq(src: Path, out_dir: Path, chunk_seconds: int) -> list[tuple[Path, float]]:
    """Split src into <=chunk_seconds FLAC pieces. Returns [(path, start_offset), ...]."""
    duration = _ffprobe_duration(src)
    n = max(1, math.ceil(duration / chunk_seconds))
    pieces: list[tuple[Path, float]] = []
    for i in range(n):
        start = i * chunk_seconds
        piece = out_dir / f"chunk_{i:03d}.flac"
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(chunk_seconds),
            "-i", str(src),
            "-ar", "16000", "-ac", "1", "-map", "0:a",
            "-c:a", "flac",
            str(piece),
        ])
        pieces.append((piece, float(start)))
    return pieces


def _post_groq(audio_path: Path, model: str, language: str | None, key: str) -> dict:
    import requests  # lazy import

    data = {"model": model, "response_format": "verbose_json"}
    if language:
        data["language"] = language
    with open(audio_path, "rb") as f:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={"Authorization": f"Bearer {key}"},
            data=data,
            files={"file": (audio_path.name, f)},
            timeout=600,
        )
    resp.raise_for_status()
    return resp.json()


def _transcribe_groq(
    audio_path: str | os.PathLike,
    model: str = GROQ_DEFAULT_MODEL,
    language: str | None = None,
    api_key: str | None = None,
) -> TranscriptionResult:
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Export it or pass --api-key."
        )

    src = Path(audio_path)
    size = src.stat().st_size

    with tempfile.TemporaryDirectory(prefix="groq_audio_") as td:
        td_path = Path(td)

        if size <= GROQ_MAX_UPLOAD_BYTES:
            uploads: list[tuple[Path, float]] = [(src, 0.0)]
        else:
            if not _ffmpeg_available():
                raise RuntimeError(
                    f"Audio is {size / 1e6:.1f} MB, above Groq's {GROQ_MAX_UPLOAD_BYTES / 1e6:.0f} MB "
                    f"upload limit. ffmpeg/ffprobe needed for recompress/split but not found in PATH."
                )
            print(f"  (audio {size / 1e6:.1f} MB > Groq limit, recompressing…)", file=sys.stderr)
            recompressed = td_path / "recompressed.flac"
            _recompress_for_groq(src, recompressed)
            if recompressed.stat().st_size <= GROQ_MAX_UPLOAD_BYTES:
                uploads = [(recompressed, 0.0)]
            else:
                print(
                    f"  (still {recompressed.stat().st_size / 1e6:.1f} MB after recompress, "
                    f"splitting into {GROQ_CHUNK_SECONDS // 60}-min chunks…)",
                    file=sys.stderr,
                )
                uploads = _split_for_groq(recompressed, td_path, GROQ_CHUNK_SECONDS)

        all_segments: list[Segment] = []
        text_parts: list[str] = []
        total_duration: float = 0.0
        detected_language: str | None = None

        for i, (chunk_path, offset) in enumerate(uploads):
            if len(uploads) > 1:
                print(f"  · chunk {i + 1}/{len(uploads)}", file=sys.stderr)
            payload = _post_groq(chunk_path, model, language, key)
            for s in payload.get("segments", []):
                all_segments.append(Segment(
                    start=float(s.get("start", 0.0)) + offset,
                    end=float(s.get("end", 0.0)) + offset,
                    text=s.get("text", ""),
                ))
            chunk_text = (payload.get("text") or "").strip()
            if chunk_text:
                text_parts.append(chunk_text)
            chunk_dur = payload.get("duration")
            if chunk_dur:
                total_duration = max(total_duration, offset + float(chunk_dur))
            if detected_language is None and payload.get("language"):
                detected_language = payload["language"]

        return TranscriptionResult(
            text=" ".join(text_parts).strip(),
            language=detected_language,
            duration=total_duration or None,
            segments=all_segments,
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
