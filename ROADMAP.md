# Roadmap

AI Video Generator turns a one-line story into a narrated, illustrated short video. The current release runs entirely on a single Apple Silicon Mac. This roadmap covers where it goes next.

## Shipped (v1)

- **Story to scenes:** an LLM (Llama 3.1 8B via Ollama) turns a prompt into 3–4 scenes as validated JSON.
- **Consistent images:** one image per scene with SDXL Turbo, using a fixed character, art style and seed.
- **Voiceover:** neural text-to-speech for each narration line.
- **Assembly:** slow-zoom (Ken Burns) motion, narration and crossfades combined into one MP4 with FFmpeg.
- **Web UI:** a Streamlit app with a prompt box, live progress, a video player, download and a storyboard view.
- **Cost model:** about 1 minute per video locally; about $0.01–0.03 per video on cloud APIs (see README).

## Shipped (v1.1)

- **Story-aware visuals:** the LLM designs the character, setting, style and narrator voice for each story (no more one fixed character); style dropdown in the UI.

## Next (v1.x)

- [ ] **Face consistency:** generate one character reference image, then use IP-Adapter so every scene shows the same face

- [ ] **Vertical output:** 1080×1920 for YouTube Shorts, Instagram Reels and TikTok
- [ ] **Subtitles:** burned-in captions generated from the narration
- [ ] **Background music:** with automatic ducking under the voice
- [ ] **Style and voice presets:** pick an art style and narrator in the UI
- [ ] **Longer stories:** configurable scene count
- [ ] **Commercial image model:** swap SDXL Turbo for a commercially licensed model

## Later (v2)

- [ ] **Cloud deployment:** hosted APIs (LLM, images, TTS) behind the same pipeline, for multi-user use
- [ ] **Job queue:** per-user output folders and background jobs
- [ ] **Batch mode:** generate many videos from a list of prompts (e.g. a month of Shorts)

## Product directions

The same pipeline adapts to:

- **Faceless YouTube Shorts:** a daily content generator for channels
- **Product ads:** short ad videos from a single product photo
- **Children's storybooks:** illustrated, narrated stories
- **Explainers:** a blog post or article turned into a narrated video
