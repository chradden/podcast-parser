import streamlit as st
import os
import requests
import feedparser
from urllib.parse import urlparse, unquote

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
