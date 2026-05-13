# Podcast & Video Parser/Transkriptor

CLI-Tool zum Herunterladen und Transkribieren von Podcast-Folgen (RSS) und
Online-Videokursen hinter einem Login. Speziell dafür gebaut, **aus einer
Claude-Code-Session** angesteuert zu werden: strukturierte Ein-/Ausgaben,
Transkripte als `.txt` auf der Platte, Claude fasst im Chat zusammen.

## Architektur

```
feeds.py        # RSS-Feed parsen, Episoden-Liste + Selektoren
download.py     # chunked Download mit safen Dateinamen
video.py        # URL → Audio via yt-dlp (primär) oder Playwright (Fallback)
transcribe.py   # Whisper-Wrapper, Backends: local (faster-whisper) | groq
podcast.py      # CLI (list / download / transcribe / pipeline / video)
```

Zusätzlich im Repo: `podcast_parser_transkriptor.ipynb` – die alte Colab-/GPU-Variante,
bleibt als Option für Batch-Jobs mit Google-Hardware.

## Installation

```bash
pip install -r requirements.txt
# ffmpeg im System (für Audio-Decoding):
#   macOS:   brew install ffmpeg
#   Ubuntu:  sudo apt install ffmpeg

# Nur für den Playwright-Fallback bei Videos:
playwright install chromium
```

Groq-Backend ist Default; setze:

```bash
export GROQ_API_KEY=...
```

Wer offline arbeiten will: `--engine local` (nutzt faster-whisper, kein Key nötig).

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
# Default: Groq (schnell, braucht GROQ_API_KEY)
python podcast.py transcribe ./podcasts/folge.mp3 --lang de

# Lokal via faster-whisper
python podcast.py transcribe folge.mp3 --engine local --model base --lang de
```

Nebenprodukt: `folge.txt` (reiner Transkripttext) und `folge.json`
(Segmente mit Timestamps) landen neben der Audio-Datei.

### Alles-in-einem: Pipeline

```bash
# Letzte 3 Folgen herunterladen und direkt transkribieren
python podcast.py pipeline <feed> --episode latest:3 --lang de
```

### Videokurse transkribieren (mit Login)

```bash
python podcast.py video https://kurs.example.com/lesson/42 --lang de
```

Wie das funktioniert:

1. **yt-dlp liest deine Chrome-Cookies** (`--cookies-from-browser chrome`).
   Du musst in Chrome bereits eingeloggt sein – yt-dlp übernimmt die Session.
2. Wenn yt-dlp die Site nicht kennt, fällt die CLI **automatisch auf
   Playwright** zurück: ein echter Chromium öffnet sich mit deinem
   Chrome-Profil, navigiert zur URL, lauscht auf den Medien-Stream und reicht
   ihn an ffmpeg.
3. Das extrahierte Audio wandert direkt durch Whisper.

Wichtige Flags:

```bash
--method auto|yt-dlp|playwright   # erzwingen, falls nötig
--chrome-profile <path>           # eigener Chrome-Profilpfad
--cookies-from-browser firefox    # Cookies aus Firefox statt Chrome
--out ./videos                    # Zielordner
```

Default-Pfade für `--chrome-profile`:

| OS | Pfad |
|---|---|
| macOS | `~/Library/Application Support/Google/Chrome` |
| Linux | `~/.config/google-chrome` |
| Windows | `~/AppData/Local/Google/Chrome/User Data` |

Wenn der gleichzeitig laufende Chrome das Profil blockiert: einmal kurz
schließen, oder ein zweites Profil anlegen.

## DRM-geschützte Plattformen (MasterClass, LinkedIn Learning, Udemy …)

**Diese Plattformen verschlüsseln den Stream mit Widevine**. Weder yt-dlp noch
Playwright können das Audio rausziehen – der Stream wird erst im Browser-CDM
entschlüsselt und ist außerhalb davon nicht greifbar. Das ist Designziel von
DRM, nicht ein Bug, den wir umgehen.

`python podcast.py video <drm-url>` bricht in dem Fall mit einer klaren
DRM-Meldung ab.

**Workaround: System-Audio aufnehmen, während du den Kurs anschaust.** Du
spielst das Video normal in Chrome, capturest den Lautsprecher-Output in eine
`.wav` und reichst sie an die CLI weiter:

```bash
python podcast.py transcribe ./aufnahme.wav --lang de
```

Audio-Routing pro OS:

**macOS**
1. [BlackHole 2ch](https://existential.audio/blackhole/) installieren.
2. In *Audio-MIDI-Setup* ein „Multi-Output"-Gerät anlegen (BlackHole +
   Kopfhörer/Lautsprecher), als System-Output wählen.
3. In QuickTime *Neue Audioaufnahme* → BlackHole als Eingang → aufnehmen.
4. Export als `.wav` oder `.m4a`, dann `python podcast.py transcribe …`

**Linux (PulseAudio/PipeWire)**
```bash
# Sink-Monitor finden:
pactl list short sources | grep monitor
# Aufnehmen (eine MasterClass-Folge etwa 90 min lang):
parec -d <sink>.monitor --file-format=wav aufnahme.wav
```
Im Parallel-Tab den Kurs in Chrome abspielen.

**Windows**
1. „Stereo Mix" in den Sound-Einstellungen aktivieren – oder
   [VB-Audio Cable](https://vb-audio.com/Cable/) installieren.
2. In Audacity das virtuelle Gerät als Eingang wählen → aufnehmen → als `.wav`
   exportieren.

Nachteile dieses Wegs: Aufnahme läuft in Echtzeit (60-Min-Kurs = 60 Min
Wartezeit), und alle Systemklänge in der Zeit landen mit auf der Spur. Dafür
ist die Qualität in der Regel sehr gut.

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
| `groq` (Default, Whisper-large-v3) | ~10–30s pro Stunde Audio | Free-Tier, sonst pay | `GROQ_API_KEY` | Standardfall, Bulk |
| `local` (faster-whisper) | CPU: ~Echtzeit mit `base` | 0 | ffmpeg | offline, kein Key gewünscht |

Mit `--engine local` schaltest du explizit aufs lokale Backend.

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
