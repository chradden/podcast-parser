#!/usr/bin/env python3
"""Podcast/Video CLI: list / download / transcribe / pipeline / video.

Designed to be driven from Claude Code (or any shell): structured output,
file artifacts next to audio files, no UI.

Examples:
  python podcast.py list https://feeds.example.com/feed.xml
  python podcast.py download <feed> --episode latest:3 --out ./podcasts
  python podcast.py transcribe ./podcasts/foo.mp3 --lang de
  python podcast.py pipeline <feed> --episode latest --lang de
  python podcast.py video https://kurs.example.com/lesson/42 --lang de
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _print_episodes_table(episodes, stream=sys.stdout):
    for ep in episodes:
        size = f"{ep.size_mb:>6.1f} MB" if ep.size_mb is not None else "      ? MB"
        stream.write(f"[{ep.index:>3}] {size}  {ep.title}\n")


def _resolve_txt_out(arg_value: str | None) -> Path | None:
    """Return a Path for the TXT library root, or None if not configured.

    Resolution order: --txt-out flag, then PODCAST_PARSER_TXT_OUT env var.
    """
    raw = arg_value or os.environ.get("PODCAST_PARSER_TXT_OUT")
    if not raw:
        return None
    return Path(raw).expanduser()


def cmd_list(args: argparse.Namespace) -> int:
    from feeds import parse_feed
    feed = parse_feed(args.feed_url, fetch_sizes=not args.no_sizes)
    if args.json:
        json.dump(
            {"title": feed.title, "episodes": [e.to_dict() for e in feed.episodes]},
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"# {feed.title}", file=sys.stderr)
        _print_episodes_table(feed.episodes)
        print(f"\n{len(feed.episodes)} episode(s).", file=sys.stderr)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from feeds import parse_feed, select_episodes
    from download import download_episodes
    feed = parse_feed(args.feed_url, fetch_sizes=False)
    selected = select_episodes(feed.episodes, args.episode)
    if not selected:
        print(f"No episodes matched selector: {args.episode!r}", file=sys.stderr)
        return 2
    paths = download_episodes(selected, args.out, progress=not args.quiet)
    if args.json:
        json.dump([str(p) for p in paths], sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for p in paths:
            print(p)
    return 0


def cmd_transcribe(args: argparse.Namespace) -> int:
    from transcribe import transcribe as run_transcribe, write_outputs
    audio = Path(args.audio_file)
    if not audio.exists():
        print(f"Audio file not found: {audio}", file=sys.stderr)
        return 2
    result = run_transcribe(
        audio,
        engine=args.engine,
        model=args.model,
        language=None if args.lang == "auto" else args.lang,
    )
    txt_out_base = _resolve_txt_out(args.txt_out)
    # Standalone file → use the audio file's parent directory name as the
    # library subfolder (keeps the user's --out organisation intact).
    txt_path_override = (
        txt_out_base / audio.parent.name / (audio.stem + ".txt")
        if txt_out_base else None
    )
    txt_path, json_path = write_outputs(result, audio, txt_path=txt_path_override)
    if args.json:
        json.dump(
            {"text_path": str(txt_path), "json_path": str(json_path), **result.to_dict()},
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"Transcript: {txt_path}")
        print(f"Segments:   {json_path}")
        print(f"Language:   {result.language}   Duration: {result.duration}s   Engine: {result.engine}/{result.model}")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    from feeds import parse_feed, select_episodes, sanitize_for_filename
    from download import download_episode
    from transcribe import transcribe as run_transcribe, write_outputs
    feed = parse_feed(args.feed_url, fetch_sizes=False)
    selected = select_episodes(feed.episodes, args.episode)
    if not selected:
        print(f"No episodes matched selector: {args.episode!r}", file=sys.stderr)
        return 2

    txt_out_base = _resolve_txt_out(args.txt_out)
    txt_subdir = (
        txt_out_base / sanitize_for_filename(feed.title) if txt_out_base else None
    )
    if txt_subdir:
        print(f"# {feed.title}  (txt → {txt_subdir})", file=sys.stderr)

    results = []
    failures = 0
    for ep in selected:
        print(f"→ {ep.title}", file=sys.stderr)
        try:
            audio = download_episode(ep, args.out, progress=not args.quiet)
            result = run_transcribe(
                audio,
                engine=args.engine,
                model=args.model,
                language=None if args.lang == "auto" else args.lang,
            )
            txt_path_override = (
                txt_subdir / (audio.stem + ".txt") if txt_subdir else None
            )
            txt_path, json_path = write_outputs(result, audio, txt_path=txt_path_override)
            results.append({
                "title": ep.title,
                "audio": str(audio),
                "transcript": str(txt_path),
                "segments_json": str(json_path),
                "language": result.language,
                "duration": result.duration,
                "engine": result.engine,
                "model": result.model,
            })
            print(f"  → {txt_path}", file=sys.stderr)
        except Exception as e:
            failures += 1
            results.append({"title": ep.title, "error": str(e)})
            print(f"  ✗ failed: {e}", file=sys.stderr)
            continue

    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for r in results:
            if "transcript" in r:
                print(r["transcript"])
    return 0 if failures == 0 else 4


def cmd_video(args: argparse.Namespace) -> int:
    from video import fetch_audio, DRMDetectedError, FetchError
    from transcribe import transcribe as run_transcribe, write_outputs

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        audio = fetch_audio(
            args.url,
            out_dir,
            method=args.method,
            cookies_from_browser=args.cookies_from_browser,
            chrome_profile=args.chrome_profile,
        )
    except DRMDetectedError as e:
        print(f"DRM detected: {e}", file=sys.stderr)
        return 3
    except FetchError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 2

    print(f"→ audio: {audio}", file=sys.stderr)
    result = run_transcribe(
        audio,
        engine=args.engine,
        model=args.model,
        language=None if args.lang == "auto" else args.lang,
    )
    txt_out_base = _resolve_txt_out(args.txt_out)
    txt_path_override = (
        txt_out_base / audio.parent.name / (audio.stem + ".txt")
        if txt_out_base else None
    )
    txt_path, json_path = write_outputs(result, audio, txt_path=txt_path_override)

    if args.json:
        json.dump(
            {
                "source_url": args.url,
                "audio": str(audio),
                "text_path": str(txt_path),
                "json_path": str(json_path),
                **result.to_dict(),
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"Transcript: {txt_path}")
        print(f"Segments:   {json_path}")
        print(f"Language:   {result.language}   Duration: {result.duration}s   Engine: {result.engine}/{result.model}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="podcast", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List episodes in an RSS feed")
    p_list.add_argument("feed_url")
    p_list.add_argument("--no-sizes", action="store_true", help="Skip HEAD requests for size")
    p_list.add_argument("--json", action="store_true", help="Output JSON")
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="Download one or more episodes")
    p_dl.add_argument("feed_url")
    p_dl.add_argument("--episode", required=True,
                      help="Selector: 'all', 'latest', 'latest:N', index, range '2-5', or list '1,4,7'")
    p_dl.add_argument("--out", default="./podcasts", help="Output directory")
    p_dl.add_argument("--quiet", action="store_true")
    p_dl.add_argument("--json", action="store_true")
    p_dl.set_defaults(func=cmd_download)

    txt_out_help = (
        "Redirect transcript .txt files to a library directory "
        "(default: $PODCAST_PARSER_TXT_OUT). Audio and JSON stay in --out."
    )

    p_tr = sub.add_parser("transcribe", help="Transcribe a local audio file")
    p_tr.add_argument("audio_file")
    p_tr.add_argument("--engine", choices=["local", "groq"], default="groq")
    p_tr.add_argument("--model", default=None,
                      help="local: tiny|base|small|medium|large-v3 (default base). groq: whisper-large-v3")
    p_tr.add_argument("--lang", default="auto", help="Language code (e.g. de, en) or 'auto'")
    p_tr.add_argument("--txt-out", default=None, help=txt_out_help)
    p_tr.add_argument("--json", action="store_true")
    p_tr.set_defaults(func=cmd_transcribe)

    p_pipe = sub.add_parser("pipeline", help="Download + transcribe in one shot")
    p_pipe.add_argument("feed_url")
    p_pipe.add_argument("--episode", required=True,
                        help="Selector (see 'download --episode')")
    p_pipe.add_argument("--out", default="./podcasts")
    p_pipe.add_argument("--engine", choices=["local", "groq"], default="groq")
    p_pipe.add_argument("--model", default=None)
    p_pipe.add_argument("--lang", default="auto")
    p_pipe.add_argument("--txt-out", default=None, help=txt_out_help)
    p_pipe.add_argument("--quiet", action="store_true")
    p_pipe.add_argument("--json", action="store_true")
    p_pipe.set_defaults(func=cmd_pipeline)

    p_vid = sub.add_parser("video", help="Fetch audio from a video URL (using your Chrome session) and transcribe it")
    p_vid.add_argument("url")
    p_vid.add_argument("--method", choices=["auto", "yt-dlp", "playwright"], default="auto",
                       help="auto = try yt-dlp, fall back to Playwright (default)")
    p_vid.add_argument("--cookies-from-browser", default="chrome",
                       help="Browser to read cookies from for yt-dlp (default: chrome)")
    p_vid.add_argument("--chrome-profile", default=None,
                       help="Path to Chrome user-data-dir for Playwright (defaults to your OS-standard path)")
    p_vid.add_argument("--out", default="./videos")
    p_vid.add_argument("--engine", choices=["local", "groq"], default="groq")
    p_vid.add_argument("--model", default=None)
    p_vid.add_argument("--lang", default="auto")
    p_vid.add_argument("--txt-out", default=None, help=txt_out_help)
    p_vid.add_argument("--json", action="store_true")
    p_vid.set_defaults(func=cmd_video)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
