# USAGE – Schritt für Schritt für Vergessliche

Du hast die App. Du willst eine Podcast-Folge zusammengefasst kriegen. Dieser
Zettel erklärt von „PowerShell auf, Loslegen" bis „wo liegt das Ergebnis"
ohne dass du etwas im Kopf behalten musst.

---

## 1. Einmalig einrichten (musst du nur EINMAL machen)

### a) Groq-API-Key besorgen

1. Geh auf https://console.groq.com/keys (kostenlos, E-Mail reicht).
2. Klick „Create API Key", kopier den Schlüssel (beginnt mit `gsk_`).
3. **Empfehlung wenn du regelmäßig Podcasts batcht**: zusätzlich auf
   https://console.groq.com/settings/billing eine Kreditkarte hinterlegen
   → Developer-Tier (~$0.04/Audio-Stunde, viel höhere Limits, keine 429-Fehler).

### b) Key dauerhaft setzen (Windows)

In PowerShell:

```powershell
setx GROQ_API_KEY "gsk_HIER_DEIN_KEY"
```

Danach **PowerShell schließen und neu öffnen**, sonst kennt sie die Variable
noch nicht. Test:

```powershell
echo $env:GROQ_API_KEY
```

Wenn dein Key erscheint: fertig. Wenn leer: PowerShell war noch nicht neu.

### c) Bei Groq Developer-Tier: Limit hochschrauben

Optional, nur wenn du upgegradet hast. Dann profitiert das Tool davon,
indem es Dateien bis 99 MB ohne Recompress hochlädt:

```powershell
setx GROQ_MAX_UPLOAD_MB "99"
```

### d) Transkripte in deinen Obsidian-Vault umleiten

Wenn du willst, dass die `.txt`-Dateien automatisch in einem zentralen
Wissensordner (z. B. deinem Obsidian-Vault) landen statt neben den MP3s,
setz die Env-Var einmalig:

```powershell
setx PODCAST_PARSER_TXT_OUT "C:\Users\Christian\3_Wissensressourcen\Obsidian_Vault\podcast-parser"
```

PowerShell schließen + neu öffnen.

Danach legt das Tool für jeden Podcast automatisch einen Unterordner an,
der den Namen aus dem RSS-Feed übernimmt. Z. B.:

```
C:\Users\Christian\3_Wissensressourcen\Obsidian_Vault\podcast-parser\
├── Money_Talks\
│   ├── Folge_42_Geld_und_Inflation.txt
│   └── Folge_43_Krypto_Update.txt
└── Silicon_Valley_Girl\
    ├── LinkedIn_founder_…_Reid_Hoffman.txt
    └── AI_Instead_of_a_Degree_…_$1B_Company.txt
```

MP3 und JSON bleiben weiterhin im `--out`-Ordner (also dort, wo du
Download und Roh-Segmente erwartest).

Für einen einzelnen Lauf kannst du das Ziel auch ad-hoc setzen oder
überschreiben:

```powershell
python podcast.py pipeline <FEED> --episode latest --lang en `
    --out .\podcasts\svg `
    --txt-out "C:\Users\Christian\3_Wissensressourcen\Obsidian_Vault\podcast-parser"
```

---

## 2. Eine Folge zusammenfassen lassen (jedes Mal)

### Schritt 1: PowerShell auf, in den Projektordner

```powershell
cd C:\Users\Christian\podcast-parser
```

### Schritt 2: Den passenden Befehl absetzen

Je nach Quelle:

#### Fall A – Podcast (du kennst den RSS-Feed)

```powershell
python podcast.py pipeline <FEED_URL> --episode latest --lang en --out .\podcasts\<ordner>
```

Beispiel:

```powershell
python podcast.py pipeline https://www.spreaker.com/show/6644934/episodes/feed --episode latest --lang en --out .\podcasts\svg
```

Selektor anpassen je nach Bedarf:

| willst du… | `--episode` |
|---|---|
| die neueste Folge | `latest` |
| die letzten 10 Folgen | `latest:10` |
| Folgen 3 bis 8 (Index) | `3-8` |
| Folgen 0, 2 und 5 | `0,2,5` |
| alle Folgen (Vorsicht!) | `all` |

`--lang en` ist die **Sprache des Podcasts**, nicht die Sprache deiner
gewünschten Zusammenfassung. Häufige Codes: `en`, `de`, `fr`, `es`, `it`.

#### Fall B – Online-Video hinter Login (YouTube, Vimeo, eigene Kursplattform)

```powershell
python podcast.py video <URL> --lang en
```

Nutzt automatisch deine Chrome-Cookies. Outputs landen in `.\videos\`.

#### Fall C – Du hast eine lokale Audio-/Videodatei

```powershell
python podcast.py transcribe ".\pfad\zur\datei.mp3" --lang en
```

Transkript landet neben der Datei.

### Schritt 3: Ergebnisse einsammeln

Für jede verarbeitete Folge bekommst du drei Dateien:

```
podcasts\<ordner>\Foo_Bar_Episode_Title.mp3    ← Originalaudio (bleibt liegen)
podcasts\<ordner>\Foo_Bar_Episode_Title.json   ← Segmente mit Zeitstempeln
podcasts\<ordner>\Foo_Bar_Episode_Title.txt    ← Transkript (Volltext)
```

**Wenn du `PODCAST_PARSER_TXT_OUT` gesetzt hast** (siehe Setup 1d), wandert
die `.txt` stattdessen in deinen Vault:

```
<VAULT>\<Podcast_Name>\Foo_Bar_Episode_Title.txt
```

Die **`.txt`** ist die, die du Claude in den Chat ziehst oder reinkopierst.

### Schritt 4: Claude zusammenfassen lassen

Mach im Claude-Chat einen neuen Talk auf, gib z. B.:

> Hier ist das Transkript von <Folgentitel>. Bitte fasse die Hauptthesen in
> 6 Bullet Points zusammen, danach 3 konkrete Quotes mit Zeitangabe.
> [Inhalt der .txt-Datei einfügen oder Datei anhängen]

---

## 3. Wenn etwas schief geht

| Fehler | Was zu tun |
|---|---|
| `GROQ_API_KEY not set` | `$env:GROQ_API_KEY = "gsk_..."` für die aktuelle Session, oder `setx GROQ_API_KEY "..."` und PowerShell neu starten |
| `429 Too Many Requests` | Du bist im Groq-Free-Tier-Limit. Entweder warten (ca. 1 Std) oder Karte bei Groq hinterlegen (Developer-Tier) |
| `413 Payload Too Large` | Sollte nicht mehr passieren — Tool recompresst automatisch. Falls doch: melden |
| `DRM detected` | Plattform schützt das Video (MasterClass, Coursera). Workaround: System-Audio-Capture (siehe README) |
| `ffmpeg failed` | `ffmpeg` ist nicht im PATH. `ffmpeg -version` prüfen, ggf. installieren |
| `Unsupported URL` (Video) | yt-dlp kennt die Plattform nicht. Tool fällt automatisch auf Playwright zurück |
| Folge bricht mitten in Batch ab | Pipeline läuft mit der nächsten Folge weiter; fehlgeschlagene siehst du am Ende mit `✗ failed: …` |

---

## 4. Häufige Quellen für RSS-Feeds

- **Spreaker**: `https://www.spreaker.com/show/<SHOW_ID>/episodes/feed`
- **Apple Podcasts**: ID raussuchen, dann z. B. `https://podcasts.apple.com/.../id<ID>` →
  Original-Feed über die Podcast-Webseite des Anbieters oder
  https://podcastindex.org suchen.
- **Spotify-Exclusive-Podcasts**: kein Feed, geht nicht. Die meisten Podcasts
  auf Spotify haben aber parallel einen öffentlichen RSS-Feed beim
  Original-Anbieter.

---

## 5. Schnellreferenz (Spickzettel)

```powershell
# Folgen eines Feeds auflisten:
python podcast.py list <FEED> --no-sizes

# Neueste Folge transkribieren:
python podcast.py pipeline <FEED> --episode latest --lang en --out .\podcasts\<ordner>

# Die letzten 10 Folgen:
python podcast.py pipeline <FEED> --episode latest:10 --lang en --out .\podcasts\<ordner>

# Video-URL:
python podcast.py video <URL> --lang en

# Lokale Datei:
python podcast.py transcribe ".\datei.mp3" --lang en

# Offline (kein Groq nötig, langsamer):
…  --engine local
```
