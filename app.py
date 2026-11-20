"""
Step 5: Web UI

A Streamlit page: type a story -> watch the 4 steps run -> play the video.

Usage:
    .venv/bin/streamlit run app.py
Then open http://localhost:8501 in your browser.
"""

import asyncio
import json
import os
import time

# Use the image model already downloaded to this Mac; never re-download.
# Must be set BEFORE importing images.py (which imports diffusers).
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import requests
import streamlit as st

import assemble
import images
import scenes
import voice

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Video Generator", page_icon="🎬")
st.title("🎬 AI Video Generator")
st.caption(
    "Story → scenes (Llama 3.1) → images (SDXL Turbo) → voice (Edge TTS) "
    "→ video (FFmpeg). Runs locally on an M1 Mac."
)


def ollama_running() -> bool:
    """Check that the Ollama server answers before we start."""
    try:
        requests.get("http://localhost:11434/api/tags", timeout=3)
        return True
    except requests.ConnectionError:
        return False


# ---------------------------------------------------------------------------
# The form: a text box and a button
# ---------------------------------------------------------------------------
story_prompt = st.text_area(
    "Your story idea",
    placeholder="A girl finds a lost baby fox in the forest during a storm...",
    height=100,
)
# "Auto" lets the LLM choose the style that fits the story
style_choice = st.selectbox(
    "Visual style",
    ["Auto"] + scenes.STYLES,
    format_func=lambda s: s.replace("_", " ").capitalize(),
)
generate = st.button("Generate video", type="primary")

# ---------------------------------------------------------------------------
# Run the pipeline when the button is clicked
# ---------------------------------------------------------------------------
# Streamlit re-runs this whole file top to bottom on every click.
# The code below only runs on the click where `generate` is True.
if generate:
    if not story_prompt.strip():
        st.warning("Please type a story idea first.")
        st.stop()  # end this run here
    if not ollama_running():
        st.error("Ollama isn't running. Start the Ollama app and try again.")
        st.stop()

    progress = st.progress(0, text="Starting...")
    start = time.time()
    timings = {}

    # st.status shows a box with live messages that can be expanded later
    with st.status("Making your video...", expanded=True) as status:
        # Step 1: story -> scenes (LLM)
        progress.progress(5, text="1/4 Writing scenes with Llama 3.1...")
        t = time.time()
        forced_style = None if style_choice == "Auto" else style_choice
        story = scenes.generate_scenes(story_prompt, style=forced_style)
        scenes.save_scenes(story)
        scenes.unload_model()  # free RAM before loading the image model
        timings["Scenes"] = time.time() - t
        st.write(f"✅ Wrote {len(story.scenes)} scenes ({timings['Scenes']:.0f}s)")
        st.write(f"🎨 Style: {story.style} · 🧑 Character: {story.character} "
                 f"· 📍 Setting: {story.setting} · 🎙️ Voice: {story.narrator}")

        # Step 2: scenes -> images (SDXL Turbo)
        progress.progress(30, text="2/4 Painting images with SDXL Turbo...")
        t = time.time()
        images.generate_images()
        timings["Images"] = time.time() - t
        st.write(f"✅ Painted {len(story.scenes)} images ({timings['Images']:.0f}s)")

        # Step 3: narration -> voice (Edge TTS)
        progress.progress(70, text="3/4 Recording the voiceover...")
        t = time.time()
        asyncio.run(voice.generate_voiceover())
        timings["Voice"] = time.time() - t
        st.write(f"✅ Recorded narration ({timings['Voice']:.0f}s)")

        # Step 4: images + audio -> video (FFmpeg)
        progress.progress(85, text="4/4 Editing the video with FFmpeg...")
        t = time.time()
        assemble.assemble()
        timings["Video"] = time.time() - t
        st.write(f"✅ Edited the video ({timings['Video']:.0f}s)")

        total = time.time() - start
        progress.progress(100, text=f"Done in {total:.0f} seconds!")
        status.update(label=f"Video ready in {total:.0f}s", state="complete",
                      expanded=False)

    # Remember that a video exists, so it stays on the page after re-runs
    st.session_state["has_video"] = True

# ---------------------------------------------------------------------------
# Show the result: the video, a download button, and the storyboard
# ---------------------------------------------------------------------------
if st.session_state.get("has_video") and assemble.VIDEO_FILE.exists():
    video_bytes = assemble.VIDEO_FILE.read_bytes()
    st.video(video_bytes)
    st.download_button("Download MP4", video_bytes, file_name="story.mp4",
                       mime="video/mp4")

    # Storyboard gallery: one card per scene (image + narration + prompt)
    st.subheader("Storyboard")
    story_data = json.loads(scenes.OUTPUT_FILE.read_text())
    st.caption(f"Style: {story_data['style']} · Character: {story_data['character']} "
               f"· Setting: {story_data['setting']}")
    columns = st.columns(2)
    for i, scene in enumerate(story_data["scenes"]):
        n = scene["scene_number"]
        with columns[i % 2]:  # alternate between the 2 columns
            st.image(str(images.IMAGES_DIR / f"scene_{n}.png"))
            st.markdown(f"**Scene {n}.** *{scene['narration']}*")
            with st.expander("Image prompt"):
                # Show the full prompt the image model actually received
                st.write(images.build_prompt(story_data, scene))
