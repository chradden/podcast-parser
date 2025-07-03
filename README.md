# Podcast Parser & Transkriptor - RSS Feed Downloader & Audio Transkription

Ein benutzerfreundlicher Podcast-Downloader mit integrierter Audio-Transkription, der es ermöglicht, Podcast-Folgen aus RSS-Feeds herunterzuladen und automatisch zu transkribieren.

**🚀 Neue Google Colab Version verfügbar!** - Nutzen Sie die Google Hardware für deutlich schnellere Transkription.

## 🎯 Features

### 📥 Podcast Downloader
- **Einfache Bedienung**: Web-basierte Benutzeroberfläche mit Streamlit
- **RSS-Feed-Parsing**: Automatische Erkennung und Analyse von Podcast-Feeds
- **Selektiver Download**: Einzelne oder alle Folgen auswählen
- **Dateigrößen-Anzeige**: Zeigt die Größe jeder Folge vor dem Download an
- **Intelligente Dateinamen**: Automatische Bereinigung von ungültigen Zeichen
- **Fortschrittsanzeige**: Echtzeit-Feedback während des Downloads
- **Duplikat-Erkennung**: Überspringt bereits vorhandene Dateien

### 📝 Audio Transkriptor
- **🎵 Multi-Format Support**: MP3, WAV, M4A, FLAC, OGG
- **🌍 Mehrsprachige Transkription**: Deutsch, Englisch, automatische Erkennung
- **🤖 OpenAI Whisper Integration**: Lokale Verarbeitung mit verschiedenen Modell-Größen
- **📊 Intelligente Modell-Auswahl**: Von tiny (schnell) bis large (genau)
- **💾 Direkte Integration**: Transkribiert heruntergeladene Podcast-Folgen
- **📁 Datei-Upload**: Unterstützt auch externe Audio-Dateien
- **📝 Export-Funktion**: Speichern als Textdatei

## 🚀 Verfügbare Versionen

### 🖥️ **Lokale Streamlit-App** (`app.py`)
- Vollständige Desktop-Anwendung
- Benötigt lokale Python-Installation
- Ideal für regelmäßige Nutzung

### ☁️ **Google Colab Notebook** (`podcast_parser_transkriptor.ipynb`) ⭐ **Empfohlen**
- **GPU-Beschleunigung**: Nutzt Google's T4/TPU Hardware
- **Keine lokale Installation**: Läuft komplett in der Cloud
- **Schnellere Transkription**: 3-5x schneller als lokale CPU
- **Interaktive Widgets**: Benutzerfreundliche Oberfläche
- **Batch-Verarbeitung**: Automatische Transkription mehrerer Dateien
- **ZIP-Export**: Einfacher Download aller Transkriptionen

> **💡 Google Hardware Vorteile:**
> - **T4 GPU**: 3-5x schnellere Whisper-Verarbeitung
> - **TPU**: Noch schnellere Verarbeitung für große Modelle
> - **Hohe RAM-Verfügbarkeit**: Bis zu 25GB RAM für große Modelle
> - **Stabile Internetverbindung**: Optimiert für Downloads

## 📋 Voraussetzungen

### Für lokale Installation:
- Python 3.8 oder höher
- Mindestens 4GB RAM (für base Modell)
- Für größere Whisper-Modelle wird mehr RAM benötigt:
  - **Tiny**: 1GB RAM
  - **Base**: 1GB RAM  
  - **Small**: 2GB RAM
  - **Medium**: 5GB RAM
  - **Large**: 10GB RAM
- Internetverbindung für RSS-Feed-Zugriff und Downloads

### Für Google Colab:
- Google-Konto (kostenlos)
- Internetverbindung
- **Keine lokale Installation erforderlich!**

## 🚀 Installation & Verwendung

### ☁️ **Google Colab Version (Empfohlen)**

1. **Notebook öffnen**
   - Öffnen Sie [Google Colab](https://colab.research.google.com/)
   - Laden Sie `podcast_parser_transkriptor.ipynb` hoch oder kopieren Sie den Inhalt

2. **GPU aktivieren**
   - Gehen Sie zu `Runtime` → `Change runtime type`
   - Wählen Sie `GPU` als Hardware accelerator

3. **Zellen ausführen**
   - Führen Sie alle Zellen der Reihe nach aus
   - Folgen Sie den interaktiven Anweisungen

4. **Podcasts herunterladen & transkribieren**
   - Geben Sie RSS-Feed-URL ein
   - Wählen Sie Folgen aus und laden Sie herunter
   - Laden Sie Whisper-Modell und transkribieren Sie

**Vorteile der Colab-Version:**
- ⚡ **3-5x schneller** durch GPU-Beschleunigung
- 🆓 **Kostenlos** (mit Google-Konto)
- 🔧 **Keine Installation** erforderlich
- 📱 **Überall verfügbar** (Browser-basiert)
- 💾 **Hohe RAM-Verfügbarkeit** für große Modelle

### 🖥️ **Lokale Streamlit-App**

1. **Repository klonen oder herunterladen**
   ```bash
   git clone <repository-url>
   cd podcast-parser
   ```

2. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **Anwendung starten**
   ```bash
   streamlit run app.py
   ```

4. **Im Browser öffnen**
   - Die Anwendung öffnet sich automatisch in Ihrem Standard-Browser
   - Standard-URL: `http://localhost:8501`

## 💻 Verwendung

### 📥 Podcast Downloader verwenden

1. **RSS-Feed eingeben**
   - RSS-Feed-URL eingeben (Standard: Energiezone Podcast)
   - Zielordner angeben (wird automatisch erstellt)

2. **Folgen herunterladen**
   - "Feed laden & Folgen anzeigen" klicken
   - Gewünschte Folgen auswählen
   - "Ausgewählte Folgen herunterladen" starten

### 📝 Audio Transkriptor verwenden

1. **Whisper-Modell laden**
   - Modell-Größe auswählen (tiny = schnell, large = genau)
   - "Modell laden" klicken
   - Warten bis das Modell geladen ist

2. **Audio-Datei auswählen**
   - **Option A**: Datei hochladen
   - **Option B**: Heruntergeladene Podcast-Folge auswählen

3. **Transkribieren**
   - Sprache auswählen (Deutsch, Englisch, Auto)
   - "Transkribieren" klicken
   - Ergebnis anzeigen und als Text speichern

### 🔄 **Batch-Transkription (nur Colab)**
- Automatische Transkription aller Audio-Dateien in einem Ordner
- ZIP-Export aller Transkriptionen
- Intelligente Überspringung bereits transkribierter Dateien

## 🔧 Konfiguration

### RSS-Feed-URL
Geben Sie die URL des RSS-Feeds ein. Beispiele:
- `https://www.energiezone.org/feed/mp3`
- `https://feeds.simplecast.com/your-podcast-feed`

### Zielordner
- Wird automatisch erstellt, falls nicht vorhanden
- Standard: `Energiezone_Podcast` (lokal) / `./podcasts` (Colab)
- Verwenden Sie relative oder absolute Pfade

### Whisper-Modelle

| Modell | Größe   | RAM  | Geschwindigkeit | Genauigkeit | Empfehlung |
| ------ | ------- | ---- | --------------- | ----------- | ---------- |
| tiny   | 39 MB   | 1GB  | Sehr schnell    | Gut         | Schnelle Tests |
| base   | 74 MB   | 1GB  | Schnell         | Besser      | Standard |
| small  | 244 MB  | 2GB  | Mittel          | Noch besser | Gute Balance |
| medium | 769 MB  | 5GB  | Langsam         | Sehr gut    | Hohe Qualität |
| large  | 1550 MB | 10GB | Sehr langsam    | Beste       | Beste Qualität |

> **⚡ Performance-Vergleich (Google Colab vs. Lokal):**
> - **Tiny Modell**: 2-3x schneller
> - **Base Modell**: 3-4x schneller  
> - **Small Modell**: 3-5x schneller
> - **Medium Modell**: 4-6x schneller
> - **Large Modell**: 5-8x schneller

## 📁 Projektstruktur

```
podcast-parser/
├── app.py                                    # Lokale Streamlit-App
├── podcast_parser_transkriptor.ipynb         # Google Colab Notebook ⭐
├── requirements.txt                          # Python-Abhängigkeiten
└── README.md                                # Diese Dokumentation
```

## 📦 Abhängigkeiten

- **streamlit**: Web-Framework für die Benutzeroberfläche
- **feedparser**: RSS/Atom-Feed-Parsing
- **requests**: HTTP-Requests für Downloads
- **openai-whisper**: Audio-Transkription mit Whisper-Modellen
- **ipywidgets**: Interaktive Widgets für Colab (automatisch installiert)

## 🛠️ Technische Details

### Dateinamen-Generierung
- Automatische Bereinigung ungültiger Zeichen
- Maximale Länge: 120 Zeichen
- Leerzeichen werden durch Unterstriche ersetzt

### Download-Features
- Chunk-basierte Downloads für große Dateien
- Timeout-Schutz (30 Sekunden)
- Automatische Weiterleitung bei HTTP-Redirects
- Fehlerbehandlung mit detaillierten Meldungen

### Transkriptions-Features
- Lokale Whisper-Modell-Verarbeitung
- Unterstützung für verschiedene Audio-Formate
- Automatische Spracherkennung
- Segment-basierte Transkription
- Temporäre Datei-Verwaltung für Uploads

### Google Colab Optimierungen
- **GPU-Beschleunigung**: Automatische Nutzung von T4/TPU
- **Hohe RAM-Verfügbarkeit**: Bis zu 25GB für große Modelle
- **Interaktive Widgets**: Benutzerfreundliche Oberfläche
- **Batch-Verarbeitung**: Effiziente Massentranskription
- **ZIP-Export**: Einfacher Download aller Ergebnisse

## 💡 Tipps für bessere Transkription

1. **Audioqualität**: Verwenden Sie möglichst hochwertige Audio-Dateien
2. **Hintergrundgeräusche**: Reduzieren Sie Hintergrundgeräusche
3. **Modellauswahl**: 
   - Für schnelle Transkription: tiny oder base
   - Für hohe Genauigkeit: medium oder large
4. **Sprache**: Wählen Sie die korrekte Sprache für bessere Ergebnisse
5. **RAM**: Stellen Sie sicher, dass genügend RAM verfügbar ist
6. **Google Colab**: Nutzen Sie GPU-Beschleunigung für beste Performance

## 🐛 Bekannte Probleme & Fehlerbehebung

### Download-Probleme
- Sehr große Dateien können längere Download-Zeiten benötigen
- Einige RSS-Feeds haben möglicherweise unterschiedliche Strukturen

### Transkriptions-Probleme
- **Modell kann nicht geladen werden**:
  - Überprüfen Sie Ihre Internetverbindung (erster Download)
  - Stellen Sie sicher, dass genügend RAM verfügbar ist
  - Versuchen Sie ein kleineres Modell

- **Audio-Datei kann nicht verarbeitet werden**:
  - Überprüfen Sie, ob die Datei beschädigt ist
  - Stellen Sie sicher, dass das Format unterstützt wird
  - Versuchen Sie eine andere Audio-Datei

- **Langsame Performance**:
  - **Lokal**: Verwenden Sie ein kleineres Whisper-Modell
  - **Colab**: Aktivieren Sie GPU-Beschleunigung
  - Schließen Sie andere Programme
  - Stellen Sie sicher, dass genügend RAM verfügbar ist

### Google Colab spezifisch
- **GPU nicht verfügbar**: Warten Sie oder verwenden Sie CPU
- **RAM-Limit erreicht**: Verwenden Sie ein kleineres Modell
- **Session-Timeout**: Speichern Sie Ergebnisse regelmäßig

## 🤝 Beitragen

Verbesserungsvorschläge und Bug-Reports sind willkommen! 

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz.

## 🙏 Danksagungen

- [Streamlit](https://streamlit.io/) für das Web-Framework
- [feedparser](https://feedparser.readthedocs.io/) für RSS-Parsing
- [Requests](https://requests.readthedocs.io/) für HTTP-Funktionalität
- [OpenAI Whisper](https://github.com/openai/whisper) für Audio-Transkription
- [LocalTranscript](https://github.com/chradden/LocalTranscript) für Inspiration
- [Google Colab](https://colab.research.google.com/) für GPU-Beschleunigung

---

**Hinweis**: Stellen Sie sicher, dass Sie die Rechte haben, Podcast-Inhalte herunterzuladen und zu transkribieren. Respektieren Sie die Urheberrechte der Podcast-Ersteller.

**💡 Empfehlung**: Für beste Performance und Benutzerfreundlichkeit verwenden Sie die **Google Colab Version** mit GPU-Beschleunigung! 