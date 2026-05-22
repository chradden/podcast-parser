# CLAUDE.md – Briefing für künftige Claude-Code-Sessions

Dieses Repo ist eine schlanke CLI zum **Herunterladen + Transkribieren + Zusammenfassen** von Audio- und Video-Quellen, gezielt fürs Zusammenspiel mit Claude Code gebaut. Es gibt **bewusst keine UI**: Claude orchestriert die CLI, liest die erzeugten `.txt`-Dateien und liefert die Zusammenfassung direkt im Chat.

## Mentales Modell

```
RSS-Feed     ──┐
Video-URL    ──┼── podcast.py ──> .txt + .json auf der Platte ──> Claude liest + fasst zusammen
Audio-Datei  ──┘
```

Die drei Eingangsquellen, die Claude antreffen wird:

1. **Podcast (RSS)** – Standardfall. `pipeline`-Subcommand.
2. **Video-URL hinter Login** (eigene Plattform, Vimeo, kleine Anbieter, YouTube) – `video`-Subcommand. Nutzt die Chrome-Cookies des Users.
3. **Lokale Audio-Datei** (z. B. eine MasterClass-Audio-Capture-Aufnahme) – `transcribe`-Subcommand.

## CLI-Schnellreferenz

| Bedarf | Befehl |
|---|---|
| Episoden eines RSS-Feeds zeigen | `python podcast.py list <feed> --no-sizes` |
| Eine Folge in einem Schritt verarbeiten | `python podcast.py pipeline <feed> --episode latest --lang de` |
| Letzte N Folgen | `--episode latest:N` |
| Bestimmte Folgen | `--episode 0,2,5` oder `--episode 3-8` |
| Alle Folgen | `--episode all` |
| Video-URL transkribieren | `python podcast.py video <url> --lang de` |
| Lokales Audio transkribieren | `python podcast.py transcribe ./file.mp3 --lang de` |
| Lokales Backend (offline) | zusätzlich `--engine local` |

Default-Engine ist **Groq** (`whisper-large-v3`). Braucht `GROQ_API_KEY` im Environment.
Default-Out-Verzeichnisse: `./podcasts/` für Feeds, `./videos/` für Video-URLs.

## Typische Claude-Workflows

### „Fasse die neueste Folge von <Podcast-Name> zusammen"

1. RSS-Feed finden (über WebSearch / podcastindex.org / die Podcast-Website). Spreaker-Pattern: `https://www.spreaker.com/show/<id>/episodes/feed`.
2. `python podcast.py pipeline <feed> --episode latest --lang <code>`
3. Resultierende `.txt`-Datei mit `Read` einlesen, im Chat zusammenfassen.

### „Fasse die letzten N Folgen zusammen"

Selektor `latest:N`, dann nacheinander alle erzeugten `.txt`-Dateien lesen und zusammenfassen. Bei vielen Folgen vorher mit User klären: einzelne Zusammenfassungen oder eine Meta-Zusammenfassung?

### „Transkribiere mir dieses Online-Video"

`python podcast.py video <url> --lang <code>`. Bei `auto`-Methode probiert die CLI zuerst yt-dlp (mit Chrome-Cookies), fällt bei „Unsupported URL" automatisch auf Playwright zurück.

## Harte Grenzen (nicht versuchen zu umgehen)

- **Widevine-DRM** (MasterClass, LinkedIn Learning, Udemy meistens, Coursera teilweise): Stream lässt sich nicht extrahieren. CLI bricht mit `DRMDetectedError` ab. **Workaround = manuelle System-Audio-Capture** durch den User; siehe README. Ergebnis ist eine `.wav`, die dann via `transcribe` läuft.
- **Spotify-Exklusivinhalte**: kein offener RSS, kein Workaround. Sag dem User klar, dass das nicht geht. Die meisten Podcasts auf Spotify haben aber einen öffentlichen RSS-Feed parallel.

## Architektur (für Code-Änderungen)

```
feeds.py        # parse_feed(), Episode-Dataclass, select_episodes() mit Selektor-Syntax
download.py     # download_episode() / download_episodes(), atomares .part-Rename
video.py        # fetch_audio(): yt-dlp primär, Playwright Fallback, DRMDetectedError
transcribe.py   # transcribe(): Backends 'local' (faster-whisper) und 'groq', write_outputs()
podcast.py      # argparse-CLI mit lazy imports, damit --help auch pre-install läuft
```

Die heavy imports (feedparser, faster_whisper, playwright) sind in `podcast.py` jeweils im Handler lazy – nicht beim Modul-Load.

## Setup-Annahmen

Setup ist Aufgabe des Users; nicht von Claude orchestriert. Voraussetzung für volle Funktion:

- `pip install -r requirements.txt`
- `ffmpeg` im PATH
- `playwright install chromium` (nur falls Video-Fallback gebraucht wird)
- `GROQ_API_KEY` exportiert
- Chrome lokal mit den nötigen Logins (nur für `video`-Subcommand)

Wenn ein Lauf an einer dieser Vorbedingungen scheitert, ist die Fehlermeldung der CLI in der Regel präzise – einfach an den User zurückgeben.

## Was Claude bei einer typischen Anfrage tun sollte

1. **Quelle identifizieren** (Podcast-Name → RSS-Suche; YouTube-Link → direkt `video`; lokale Datei → `transcribe`).
2. **Selektor festlegen** (latest / latest:N / Bereich / alle). Bei Unsicherheit kurz nachfragen.
3. **Sprache des Inhalts** als `--lang` setzen, nicht die Sprache der Zusammenfassung.
4. **Pipeline laufen lassen**, dann die erzeugten `.txt`-Dateien lesen.
5. **Im Chat zusammenfassen** in der Sprache, die der User wünscht (Default: Sprache der User-Nachricht).

Keine Zusatzdateien (`summary.md`, `notes/…`) erzeugen, außer der User fragt explizit danach. Die Zusammenfassung gehört in den Chat.
