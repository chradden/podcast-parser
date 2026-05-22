"""RSS feed parsing for podcasts."""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Iterable
from urllib.parse import urlparse

import feedparser
import requests


INVALID_FILENAME_CHARS = ['?', '*', ':', '<', '>', '|', '"', '\\', '/', '\n', '\r']


@dataclass
class Episode:
    index: int
    title: str
    audio_url: str
    filename: str
    ext: str
    size_bytes: int | None
    published: str | None

    @property
    def size_mb(self) -> float | None:
        if self.size_bytes is None:
            return None
        return round(self.size_bytes / (1024 * 1024), 2)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["size_mb"] = self.size_mb
        return d


@dataclass
class Feed:
    title: str
    episodes: list[Episode]


def sanitize_for_filename(name: str, max_len: int = 120) -> str:
    """Strip filesystem-hostile characters so a title is safe as a file/folder name."""
    for ch in INVALID_FILENAME_CHARS:
        name = name.replace(ch, "_")
    return name.strip().replace(" ", "_")[:max_len] or "untitled"


def title_to_filename(title: str, ext: str, max_len: int = 120) -> str:
    return f"{sanitize_for_filename(title, max_len)}{ext}"


def _extract_audio_url(entry) -> str | None:
    if getattr(entry, "enclosures", None):
        for enc in entry.enclosures:
            href = getattr(enc, "href", None) or enc.get("href") if isinstance(enc, dict) else None
            if href:
                return href
    return None


def _head_size(url: str, timeout: float = 10.0) -> int | None:
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        length = r.headers.get("Content-Length")
        return int(length) if length else None
    except Exception:
        return None


def parse_feed(feed_url: str, fetch_sizes: bool = True) -> Feed:
    """Parse a podcast RSS feed. Returns Feed(title, episodes).

    Set fetch_sizes=False to skip HEAD requests (faster, but size unknown).
    """
    parsed = feedparser.parse(feed_url)
    channel_title = (getattr(parsed.feed, "title", None) or "podcast").strip()
    episodes: list[Episode] = []
    for idx, entry in enumerate(parsed.entries):
        audio_url = _extract_audio_url(entry)
        if not audio_url:
            continue
        title = getattr(entry, "title", f"episode_{idx}")
        ext = os.path.splitext(urlparse(audio_url).path)[1] or ".mp3"
        size = _head_size(audio_url) if fetch_sizes else None
        episodes.append(
            Episode(
                index=idx,
                title=title,
                audio_url=audio_url,
                filename=title_to_filename(title, ext),
                ext=ext,
                size_bytes=size,
                published=getattr(entry, "published", None),
            )
        )
    return Feed(title=channel_title, episodes=episodes)


def select_episodes(episodes: list[Episode], selector: str) -> list[Episode]:
    """Pick episodes by selector string.

    Syntax:
      "all"         -> every episode
      "3"           -> single index
      "1,4,7"       -> list of indices
      "2-5"         -> inclusive range
      "latest"      -> first entry in feed (most recent)
      "latest:N"    -> first N entries
    """
    if selector == "all":
        return list(episodes)
    if selector == "latest":
        return episodes[:1]
    if selector.startswith("latest:"):
        n = int(selector.split(":", 1)[1])
        return episodes[:n]
    picked: list[Episode] = []
    for part in selector.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            picked.extend(ep for ep in episodes if int(a) <= ep.index <= int(b))
        else:
            idx = int(part)
            picked.extend(ep for ep in episodes if ep.index == idx)
    return picked
