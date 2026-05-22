"""Fetch audio from password-protected video URLs.

Two strategies, both leveraging an already-logged-in Chrome session:

  1. yt-dlp with --cookies-from-browser chrome (primary).
     Handles most platforms (own sites, Vimeo, Teachable, Thinkific,
     Kajabi when not DRM-protected, YouTube-unlisted, …).

  2. Playwright with the user's Chrome profile (fallback).
     Opens a real browser session, intercepts the media manifest, then
     pipes it through ffmpeg. Useful for sites yt-dlp doesn't recognise.

Both refuse DRM-protected streams (Widevine etc.) with a clear error
pointing to the README's audio-capture workflow.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal


class DRMDetectedError(RuntimeError):
    """Raised when the source uses DRM and cannot be transcribed."""


class FetchError(RuntimeError):
    """Generic fetch failure."""


# ---------------------------------------------------------------------------
# yt-dlp backend
# ---------------------------------------------------------------------------

DRM_MARKERS = ("widevine", "playready", "fairplay", "license_url", "cenc:pssh")


def _looks_drm(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in DRM_MARKERS)


def _fetch_with_ytdlp(
    url: str,
    out_dir: Path,
    cookies_from_browser: str,
) -> Path:
    if shutil.which("yt-dlp") is None:
        raise FetchError("yt-dlp not installed. Run: pip install yt-dlp")
    if shutil.which("ffmpeg") is None:
        raise FetchError("ffmpeg not installed (needed for audio extraction).")

    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "%(title).120s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--cookies-from-browser", cookies_from_browser,
        "-x", "--audio-format", "mp3",
        "--restrict-filenames",
        "-o", template,
        "--print", "after_move:filepath",
        "--no-warnings",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    combined = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode != 0:
        if _looks_drm(combined) or "DRM" in combined or "drm" in combined:
            raise DRMDetectedError(
                "yt-dlp reports DRM-protected content. See README → "
                "'DRM-geschützte Plattformen' for the audio-capture workflow."
            )
        raise FetchError(f"yt-dlp failed:\n{combined.strip()}")

    # Last non-empty line of stdout is the produced filepath (from --print)
    paths = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not paths:
        # Fallback: newest audio file in out_dir
        candidates = sorted(
            (p for p in out_dir.iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".opus", ".webm"}),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FetchError("yt-dlp succeeded but no audio file was produced.")
        return candidates[0]
    return Path(paths[-1])


# ---------------------------------------------------------------------------
# Playwright backend
# ---------------------------------------------------------------------------

DEFAULT_CHROME_PROFILES = {
    "darwin": "~/Library/Application Support/Google/Chrome",
    "linux": "~/.config/google-chrome",
    "win32": "~/AppData/Local/Google/Chrome/User Data",
}


def _default_chrome_profile() -> str | None:
    key = sys.platform if sys.platform in DEFAULT_CHROME_PROFILES else (
        "darwin" if sys.platform == "darwin" else "linux" if sys.platform.startswith("linux") else None
    )
    return DEFAULT_CHROME_PROFILES.get(key) if key else None


MEDIA_URL_RE = re.compile(r"\.(m3u8|mpd|mp4|m4a|webm)(\?|$)", re.IGNORECASE)


def _fetch_with_playwright(
    url: str,
    out_dir: Path,
    chrome_profile: str | None,
    wait_seconds: int = 25,
) -> Path:
    try:
        from playwright.sync_api import sync_playwright  # lazy import
    except ImportError as e:
        raise FetchError("playwright not installed. Run: pip install playwright && playwright install chromium") from e
    if shutil.which("ffmpeg") is None:
        raise FetchError("ffmpeg not installed (needed for audio extraction).")

    profile = chrome_profile or _default_chrome_profile()
    if profile is None:
        raise FetchError("Could not determine default Chrome profile path; pass --chrome-profile.")
    profile_path = Path(os.path.expanduser(profile))

    media_urls: list[str] = []
    drm_hits: list[str] = []

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=False,  # DRM/Widevine detection often requires non-headless
            channel="chrome",
        )
        page = ctx.new_page()

        def on_request(req):
            u = req.url
            if MEDIA_URL_RE.search(u):
                media_urls.append(u)
            if _looks_drm(u):
                drm_hits.append(u)

        def on_response(resp):
            ct = resp.headers.get("content-type", "")
            if "dash+xml" in ct or "mpegurl" in ct:
                media_urls.append(resp.url)
                try:
                    body = resp.text()
                    if _looks_drm(body):
                        drm_hits.append(resp.url)
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_seconds * 1000)
        ctx.close()

    if drm_hits:
        raise DRMDetectedError(
            "Playwright detected DRM markers in the stream. See README → "
            "'DRM-geschützte Plattformen' for the audio-capture workflow.\n"
            f"  hit: {drm_hits[0]}"
        )
    if not media_urls:
        raise FetchError(
            "No media stream observed. Try increasing --wait, or the page may "
            "require an explicit click to start playback."
        )

    # Pick the first manifest (HLS .m3u8 / DASH .mpd) if any, else first MP4.
    manifests = [u for u in media_urls if u.lower().split("?")[0].endswith((".m3u8", ".mpd"))]
    stream_url = manifests[0] if manifests else media_urls[0]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "video_capture.m4a"
    cmd = [
        "ffmpeg", "-y",
        "-i", stream_url,
        "-vn", "-acodec", "aac", "-b:a", "128k",
        str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FetchError(f"ffmpeg failed:\n{proc.stderr.strip()}")
    return out_path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

Method = Literal["auto", "yt-dlp", "playwright"]


def fetch_audio(
    url: str,
    out_dir: str | os.PathLike,
    *,
    method: Method = "auto",
    cookies_from_browser: str = "chrome",
    chrome_profile: str | None = None,
) -> Path:
    """Resolve a video URL to a local audio file. Raises DRMDetectedError if blocked."""
    out_path = Path(out_dir)

    if method == "yt-dlp":
        return _fetch_with_ytdlp(url, out_path, cookies_from_browser)
    if method == "playwright":
        return _fetch_with_playwright(url, out_path, chrome_profile)

    # auto: try yt-dlp first, fall back to Playwright on FetchError (but NOT on DRM)
    try:
        return _fetch_with_ytdlp(url, out_path, cookies_from_browser)
    except DRMDetectedError:
        raise
    except FetchError as e:
        print(f"yt-dlp could not handle this URL ({e}); falling back to Playwright …", file=sys.stderr)
        return _fetch_with_playwright(url, out_path, chrome_profile)
