"""Chunked download of podcast episodes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

from feeds import Episode


def download_episode(
    episode: Episode,
    out_dir: str | os.PathLike,
    chunk_size: int = 8192,
    timeout: float = 30.0,
    skip_existing: bool = True,
    progress: bool = False,
) -> Path:
    """Download a single episode to out_dir. Returns the final file path."""
    out_path = Path(out_dir) / episode.filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if skip_existing and out_path.exists():
        return out_path

    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    with requests.get(episode.audio_url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0)) or (episode.size_bytes or 0)
        downloaded = 0
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress and total:
                    pct = downloaded / total * 100
                    sys.stderr.write(f"\r  {episode.filename}: {pct:5.1f}%")
                    sys.stderr.flush()
        if progress:
            sys.stderr.write("\n")
    tmp_path.replace(out_path)
    return out_path


def download_episodes(
    episodes: list[Episode],
    out_dir: str | os.PathLike,
    progress: bool = False,
) -> list[Path]:
    paths: list[Path] = []
    for ep in episodes:
        paths.append(download_episode(ep, out_dir, progress=progress))
    return paths
