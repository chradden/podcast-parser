import streamlit as st
import os
import requests
import feedparser
from urllib.parse import urlparse, unquote
import whisper
import tempfile
import shutil

# Page config
st.set_page_config(
    page_title="Podcast Parser & Transkriptor",
    page_icon="🎙️",
    layout="wide"
)

# Sidebar for navigation
st.sidebar.title("🎙️ Podcast Tools")
page = st.sidebar.selectbox(
    "Wählen Sie eine Funktion:",
    ["📥 Podcast Downloader", "📝 Audio Transkriptor"]
)

# Initialize session state for transcription
if "whisper_model" not in st.session_state:
    st.session_state.whisper_model = None
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False

if page == "📥 Podcast Downloader":
    st.title("Podcast Downloader für RSS-Feeds")

    feed_url = st.text_input("RSS-Feed-URL eingeben", "https://www.energiezone.org/feed/mp3")
    download_dir = st.text_input("Zielordner (wird angelegt, falls nicht vorhanden)", "Energiezone_Podcast")

    def title_to_filename(title, ext):
        invalid_chars = ['?', '*', ':', '<', '>', '|', '"', '\\', '/', '\n', '\r']
        filename = title
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        filename = filename.strip().replace(' ', '_')
        filename = filename[:120]  # Länge beschränken
        return f"{filename}{ext}"

    if "episode_data" not in st.session_state:
        st.session_state.episode_data = []
    if "checked" not in st.session_state:
        st.session_state.checked = []
    if "feed_loaded" not in st.session_state:
        st.session_state.feed_loaded = False

    if st.button("Feed laden & Folgen anzeigen"):
        with st.spinner("Lade Feed und analysiere Folgen ..."):
            feed = feedparser.parse(feed_url)
        episode_data = []
        checked = []
        for entry in feed.entries:
            if "enclosures" in entry and entry.enclosures:
                mp3_url = entry.enclosures[0].href
                title = entry.title
                try:
                    head = requests.head(mp3_url, allow_redirects=True, timeout=10)
                    size = int(head.headers.get("Content-Length", 0))
                    size_mb = round(size / (1024 * 1024), 2)
                except:
                    size_mb = "?"
                url_path = urlparse(mp3_url).path
                ext = os.path.splitext(url_path)[1]
                filename = title_to_filename(title, ext)
                episode_data.append({
                    "title": title,
                    "mp3_url": mp3_url,
                    "size_mb": size_mb,
                    "filename": filename,
                    "ext": ext,
                })
                checked.append(not os.path.exists(os.path.join(download_dir, filename)))
        st.session_state.episode_data = episode_data
        st.session_state.checked = checked
        st.session_state.feed_loaded = True

    if st.session_state.feed_loaded and st.session_state.episode_data:
        st.subheader("Folgen auswählen")

        # Buttons für alle auswählen / abwählen
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Alle auswählen"):
                st.session_state.checked = [True] * len(st.session_state.episode_data)
        with col2:
            if st.button("Alle abwählen"):
                st.session_state.checked = [False] * len(st.session_state.episode_data)

        # Checkboxen pro Folge
        for i, episode in enumerate(st.session_state.episode_data):
            label = f"{episode['title']} ({episode['size_mb']} MB)"
            st.session_state.checked[i] = st.checkbox(label, value=st.session_state.checked[i], key=f"ep_{i}")

        if st.button("Ausgewählte Folgen herunterladen"):
            os.makedirs(download_dir, exist_ok=True)
            selected = [ep for ep, checked in zip(st.session_state.episode_data, st.session_state.checked) if checked]
            if not selected:
                st.warning("Keine Folge ausgewählt.")
            else:
                progress = st.progress(0, text="Starte Download ...")
                num = len(selected)
                for idx, episode in enumerate(selected):
                    filename = os.path.join(download_dir, title_to_filename(episode['title'], episode['ext']))
                    if os.path.exists(filename):
                        st.write(f"**{filename}** existiert schon, überspringe.")
                    else:
                        st.write(f"Lade herunter: {episode['title']}")
                        try:
                            with requests.get(episode['mp3_url'], stream=True, timeout=30) as r:
                                r.raise_for_status()
                                with open(filename, "wb") as f:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            st.success(f"Gespeichert: {filename} ({episode['size_mb']} MB)")
                        except Exception as e:
                            st.error(f"Fehler beim Download von {filename}: {e}")
                    progress.progress((idx + 1) / num, text=f"{idx+1} von {num} Folgen geladen")
                st.info("Alle ausgewählten Folgen wurden verarbeitet.")

elif page == "📝 Audio Transkriptor":
    st.title("Audio Transkriptor")
    st.markdown("Transkribieren Sie heruntergeladene Podcast-Folgen oder andere Audio-Dateien mit OpenAI's Whisper-Modell.")

    # Whisper Model Selection
    st.subheader("🎯 Whisper-Modell auswählen")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        model_size = st.selectbox(
            "Modell-Größe:",
            ["tiny", "base", "small", "medium", "large"],
            help="Tiny = schnell, Large = genau"
        )
    
    with col2:
        if st.button("Modell laden", type="primary"):
            if not st.session_state.model_loaded or st.session_state.whisper_model is None:
                with st.spinner(f"Lade Whisper {model_size} Modell..."):
                    try:
                        st.session_state.whisper_model = whisper.load_model(model_size)
                        st.session_state.model_loaded = True
                        st.success(f"✅ {model_size} Modell erfolgreich geladen!")
                    except Exception as e:
                        st.error(f"❌ Fehler beim Laden des Modells: {e}")
            else:
                st.info("Modell bereits geladen!")

    # Model Info
    model_info = {
        "tiny": {"size": "39 MB", "ram": "1GB", "speed": "Sehr schnell", "accuracy": "Gut"},
        "base": {"size": "74 MB", "ram": "1GB", "speed": "Schnell", "accuracy": "Besser"},
        "small": {"size": "244 MB", "ram": "2GB", "speed": "Mittel", "accuracy": "Noch besser"},
        "medium": {"size": "769 MB", "ram": "5GB", "speed": "Langsam", "accuracy": "Sehr gut"},
        "large": {"size": "1550 MB", "ram": "10GB", "speed": "Sehr langsam", "accuracy": "Beste"}
    }
    
    if model_size in model_info:
        info = model_info[model_size]
        st.info(f"📊 **{model_size.upper()} Modell**: {info['size']} | {info['ram']} RAM | {info['speed']} | {info['accuracy']}")

    # File Selection
    st.subheader("🎵 Audio-Datei auswählen")
    
    # Option 1: Upload file
    uploaded_file = st.file_uploader(
        "Audio-Datei hochladen",
        type=['mp3', 'wav', 'm4a', 'flac', 'ogg'],
        help="Unterstützte Formate: MP3, WAV, M4A, FLAC, OGG"
    )
    
    # Option 2: Select from download directory
    download_dir = st.text_input("Podcast-Ordner (für heruntergeladene Dateien)", "Energiezone_Podcast")
    
    if os.path.exists(download_dir):
        audio_files = [f for f in os.listdir(download_dir) 
                      if f.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg'))]
        
        if audio_files:
            st.write("**Oder wählen Sie eine heruntergeladene Datei:**")
            selected_file = st.selectbox("Verfügbare Audio-Dateien:", [""] + audio_files)
            
            if selected_file:
                selected_file_path = os.path.join(download_dir, selected_file)
        else:
            selected_file_path = None
    else:
        selected_file_path = None

    # Language Selection
    st.subheader("🌍 Sprache auswählen")
    language = st.selectbox(
        "Sprache:",
        ["auto", "de", "en"],
        format_func=lambda x: {"auto": "Automatische Erkennung", "de": "Deutsch", "en": "Englisch"}[x]
    )

    # Transcription Process
    if st.button("🎯 Transkribieren", disabled=not st.session_state.model_loaded):
        audio_file_path = None
        
        # Determine which file to use
        if uploaded_file is not None:
            # Save uploaded file to temp location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                shutil.copyfileobj(uploaded_file, tmp_file)
                audio_file_path = tmp_file.name
        elif selected_file_path and os.path.exists(selected_file_path):
            audio_file_path = selected_file_path
        else:
            st.error("❌ Bitte wählen Sie eine Audio-Datei aus!")
            st.stop()

        if audio_file_path and st.session_state.whisper_model:
            with st.spinner("🎵 Transkribiere Audio..."):
                try:
                    # Perform transcription
                    result = st.session_state.whisper_model.transcribe(
                        audio_file_path,
                        language=language if language != "auto" else None,
                        task="transcribe"
                    )
                    
                    # Display results
                    st.subheader("📝 Transkription")
                    
                    # Show transcription text
                    transcription_text = result["text"]
                    st.text_area("Transkription:", transcription_text, height=300)
                    
                    # Download button
                    original_filename = os.path.splitext(os.path.basename(audio_file_path))[0]
                    st.download_button(
                        label="💾 Als Textdatei speichern",
                        data=transcription_text,
                        file_name=f"{original_filename}.txt",
                        mime="text/plain"
                    )
                    
                                # Show additional info
            if "segments" in result:
                st.subheader("📊 Transkriptions-Details")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Segmente", len(result["segments"]))
                with col2:
                    duration = result["segments"][-1]["end"] if result["segments"] else 0
                    st.metric("Dauer", f"{duration:.1f}s")
                with col3:
                    st.metric("Sprache", result.get("language", "Unbekannt"))
                
                # Zeige Dateiname-Info
                st.info(f"💾 Transkription wird als: **{original_filename}.txt** gespeichert")
                    
                    # Clean up temp file if it was uploaded
                    if uploaded_file is not None and os.path.exists(audio_file_path):
                        os.unlink(audio_file_path)
                        
                except Exception as e:
                    st.error(f"❌ Fehler bei der Transkription: {e}")
                    # Clean up temp file on error
                    if uploaded_file is not None and os.path.exists(audio_file_path):
                        os.unlink(audio_file_path)

    # Tips Section
    with st.expander("💡 Tipps für bessere Transkription"):
        st.markdown("""
        **Für beste Ergebnisse:**
        - 🎵 Verwenden Sie hochwertige Audio-Dateien
        - 🔇 Reduzieren Sie Hintergrundgeräusche
        - 🎯 Wählen Sie das richtige Modell:
          - **Tiny/Base**: Für schnelle Transkription
          - **Medium/Large**: Für hohe Genauigkeit
        - 🌍 Wählen Sie die korrekte Sprache
        - 💾 Stellen Sie sicher, dass genügend RAM verfügbar ist
        """)

    # Troubleshooting
    with st.expander("🔧 Fehlerbehebung"):
        st.markdown("""
        **Häufige Probleme:**
        
        **Modell kann nicht geladen werden:**
        - Überprüfen Sie Ihre Internetverbindung (erster Download)
        - Stellen Sie sicher, dass genügend RAM verfügbar ist
        - Versuchen Sie ein kleineres Modell
        
        **Audio-Datei kann nicht verarbeitet werden:**
        - Überprüfen Sie, ob die Datei beschädigt ist
        - Stellen Sie sicher, dass das Format unterstützt wird
        - Versuchen Sie eine andere Audio-Datei
        
        **Langsame Performance:**
        - Verwenden Sie ein kleineres Whisper-Modell
        - Schließen Sie andere Programme
        - Stellen Sie sicher, dass genügend RAM verfügbar ist
        """)
