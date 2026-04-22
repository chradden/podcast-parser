# Podcast Parser & Transkriptor

CLI-Tool zum Herunterladen und Transkribieren von Podcast-Folgen aus RSS-Feeds.
Speziell dafür gebaut, **aus einer Claude-Code-Session** angesteuert zu werden:
strukturierte Ein-/Ausgaben, Transkripte als `.txt` auf der Platte, Claude
erledigt Zusammenfassungen direkt im Chat.

## Architektur

```
feeds.py        # RSS-Feed parsen, Episoden-Liste + Selektoren
download.py     # chunked Download mit safen Dateinamen
transcribe.py   # Whisper-Wrapper, Backends: local (faster-whisper) | groq
podcast.py      # CLI (list / download / transcribe / pipeline)
```

Zusätzlich im Repo: `podcast_parser_transkriptor.ipynb` – die alte Colab-/GPU-Variante,
bleibt als Option für Batch-Jobs mit Google-Hardware.

## Installation

```bash
pip install -r requirements.txt
# für den lokalen Backend wird zusätzlich ffmpeg im System benötigt:
#   macOS:   brew install ffmpeg
#   Ubuntu:  sudo apt install ffmpeg
```

Optional für das Groq-Backend:

```bash
export GROQ_API_KEY=...
```

## CLI-Nutzung

### Episoden auflisten

```bash
python podcast.py list https://www.energiezone.org/feed/mp3
python podcast.py list <feed> --json          # maschinenlesbar
python podcast.py list <feed> --no-sizes      # schneller, ohne HEAD-Requests
```

### Episoden herunterladen

```bash
python podcast.py download <feed> --episode latest        # neueste Folge
python podcast.py download <feed> --episode latest:5      # 5 neueste
python podcast.py download <feed> --episode 3             # Index 3
python podcast.py download <feed> --episode 2-7           # Bereich
python podcast.py download <feed> --episode 1,4,9         # Liste
python podcast.py download <feed> --episode all --out ./podcasts
```

Selektoren funktionieren in `download` und `pipeline` identisch.

### Audio transkribieren

```bash
# Lokal via faster-whisper (Default-Modell: base)
python podcast.py transcribe ./podcasts/folge.mp3 --lang de

# Anderes Modell
python podcast.py transcribe folge.mp3 --model small --lang de

# Via Groq (schnell, braucht GROQ_API_KEY)
python podcast.py transcribe folge.mp3 --engine groq --lang de
```

Nebenprodukt: `folge.txt` (reiner Transkripttext) und `folge.json`
(Segmente mit Timestamps) landen neben der Audio-Datei.

### Alles-in-einem: Pipeline

```bash
# Letzte 3 Folgen herunterladen und direkt transkribieren
python podcast.py pipeline <feed> --episode latest:3 --engine groq --lang de
```

## Nutzung aus Claude Code

Der eigentliche Workflow sieht so aus:

1. Du sagst: _„Fasse mir die neueste Folge von https://…/feed.xml zusammen."_
2. Claude ruft `python podcast.py pipeline <feed> --episode latest --engine groq --lang de`.
3. Das Transkript landet als `.txt` im `./podcasts`-Ordner.
4. Claude liest die Datei und fasst sie dir direkt im Chat zusammen – in Länge,
   Sprache und Stil deiner Wahl, mit Rückfragen.

Für mehrere Folgen („alle Folgen von Podcast X") läuft die Pipeline über den
entsprechenden Selektor (`--episode all` bzw. `latest:N`), und Claude liest am
Ende alle `.txt`-Dateien nacheinander.

## Backend-Wahl

| Backend | Geschwindigkeit | Kosten | Benötigt | Wofür |
|---|---|---|---|---|
| `local` (faster-whisper) | CPU: ~Echtzeit mit `base` | 0 | ffmpeg | einzelne Folgen, offline |
| `groq` (Whisper-large-v3) | ~10–30s pro Stunde Audio | Free-Tier, sonst pay | `GROQ_API_KEY` | Bulk-Transkription |

Daumenregel: Eine Folge zwischendurch → `local`. Ganze Podcasts → `groq`.

## Whisper-Modelle (local)

| Modell | Größe | RAM | Relative Geschwindigkeit | Genauigkeit |
|---|---|---|---|---|
| `tiny`     |   39 MB |  1 GB | sehr schnell | okay |
| `base`     |   74 MB |  1 GB | schnell      | gut |
| `small`    |  244 MB |  2 GB | mittel       | besser |
| `medium`   |  769 MB |  5 GB | langsam      | sehr gut |
| `large-v3` | 1550 MB | 10 GB | sehr langsam | beste |

`faster-whisper` ist durch CT2-Quantisierung (`int8`) im Vergleich zu
`openai-whisper` ca. 3–5× schneller bei gleicher Qualität.

## Alter Streamlit-UI

Die frühere `app.py` (Streamlit-basiert) wurde zugunsten des CLI entfernt –
in einer Claude-Code-Session bringt eine UI nichts. Wer sie weiterhin haben
möchte, findet sie in der Git-Historie.

## Lizenz

MIT.
