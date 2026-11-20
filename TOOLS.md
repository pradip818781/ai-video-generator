# Tools Used in This Project

Every tool in the project, explained twice:
- **Technical:** what it really is.
- **In plain words:** an everyday explanation.

This file is updated as each step adds new tools.

---

## Foundation (used everywhere)

### Python 3.13
- **Technical:** an interpreted programming language. All the scripts here (`scenes.py`, `images.py`) are written in it.
- **In plain words:** the language we write our instructions in, like English for computers.

### Virtual environment (`.venv`)
- **Technical:** an isolated Python setup made with `python3 -m venv .venv`. Packages are installed in `.venv/` instead of system-wide.
- **In plain words:** a private toolbox for this project. Whatever we put in it doesn't mess up other projects on your Mac.

### pip + `requirements.txt`
- **Technical:** `pip` is Python's package installer. `requirements.txt` lists the packages and minimum versions; `pip install -r requirements.txt` installs them all.
- **In plain words:** `pip` is the app store for Python. `requirements.txt` is the shopping list, so anyone can rebuild the same toolbox in one command.

---

## Step 1: Story → scenes (`scenes.py`)

### Ollama
- **Technical:** a local server that runs LLMs on your machine and exposes an HTTP API at `http://localhost:11434`. We call its `/api/chat` endpoint.
- **In plain words:** a program that keeps an AI "brain" running on your own Mac. Our script sends it questions like a website would, but nothing leaves your computer and it's free.

### llama3.1:8b
- **Technical:** Meta's Llama 3.1 large language model with 8 billion parameters, quantized to 4-bit (Q4_K_M), about 4.9 GB.
- **In plain words:** the AI writer itself. "8b" is its size; bigger models are smarter but need more memory. "Quantized" means compressed so it fits on a laptop.

### Structured outputs (Ollama's `format` option)
- **Technical:** passing a JSON Schema in the request makes Ollama constrain token generation so the reply always matches that schema.
- **In plain words:** instead of asking the AI to "please reply neatly", we hand it a form with fixed boxes, and it can only write inside the boxes.

### requests
- **Technical:** a Python HTTP client library. `requests.post(url, json=...)` sends the prompt to Ollama and receives the reply.
- **In plain words:** the postman. It carries our message to Ollama and brings the answer back.

### pydantic
- **Technical:** a data validation library. We define `Scene`/`Story` classes with typed fields and rules (e.g. 3–4 scenes, no empty strings); `model_validate_json()` parses and checks the reply.
- **In plain words:** a strict checker at the door. If the AI forgot a box or wrote 7 scenes, it gets rejected and we ask again.

### JSON
- **Technical:** JavaScript Object Notation, a text format for structured data (keys, values, lists). Saved as `output/scenes.json`.
- **In plain words:** a neat, labelled list that both humans and programs can read, like a well-organised form.

---

## Step 2: Scenes → images (`images.py`)

### PyTorch (`torch`)
- **Technical:** a deep-learning framework that runs neural network math (tensors) on the CPU or GPU.
- **In plain words:** the engine that does the huge number of calculations an AI image model needs.

### MPS (Metal Performance Shaders)
- **Technical:** Apple's GPU backend for PyTorch on Apple Silicon (M1/M2/M3). We select it with `device = "mps"`.
- **In plain words:** the part of your M1 chip that's built for graphics. Using it makes images much faster than the regular processor.

### diffusers (Hugging Face)
- **Technical:** a library that packages diffusion models into ready-made "pipelines". `AutoPipelineForText2Image` loads the model and turns a prompt into an image.
- **In plain words:** a ready-made kit that plugs the image AI together so we can just say "draw this".

### transformers + accelerate (Hugging Face)
- **Technical:** `transformers` provides the CLIP text encoders that convert prompts into embeddings; `accelerate` handles efficient model loading and device placement.
- **In plain words:** helpers. One translates our words into numbers the image AI understands; the other loads the big model quickly.

### SDXL Turbo
- **Technical:** Stability AI's distilled Stable Diffusion XL model, trained (via Adversarial Diffusion Distillation) to make 512×512 images in 1–4 denoising steps, with `guidance_scale=0`. We use fp16 weights (~7 GB). Non-commercial licence.
- **In plain words:** the AI artist. It starts from random "TV static" and cleans it up into a picture matching the prompt. "Turbo" means it does this in just a few passes instead of 30–50.

### Seed
- **Technical:** the number that initialises the random noise. The same seed with the same prompt and settings gives the same image.
- **In plain words:** the starting scribble. Using the same scribble for every scene helps Mira look similar in each picture.

### fp16 (half precision)
- **Technical:** 16-bit floating-point numbers instead of 32-bit, which halves memory use and download size with little quality loss.
- **In plain words:** storing numbers with slightly fewer decimal places, so the model takes half the space and still works almost as well.

### Prompt token limit (CLIP, 77 tokens)
- **Technical:** SDXL's CLIP text encoders read at most 77 tokens; anything after that is silently cut off. That's why `STYLE` goes at the front of the prompt and `CHARACTER` is kept short.
- **In plain words:** the artist only reads the first ~60 words of your note. Put the most important instructions first.

### Colour bleeding
- **Technical:** the model links colour words to the wrong objects in the prompt (e.g. "yellow raincoat, green boots" produced a green raincoat).
- **In plain words:** the artist mixes up which colour goes where. Fewer competing colours means fewer mix-ups.

### Hugging Face Hub (model cache)
- **Technical:** an online model repository. Models are downloaded once to `~/.cache/huggingface/hub` and reused afterwards.
- **In plain words:** the library where AI models live. We borrow a copy once and keep it on your Mac.

---

### Story-aware prompt building (v1.1)
- **Technical:** the LLM's JSON includes `character`, `setting`, `style` (an enum of 5 presets) and `narrator`. `images.py` maps the style name to tested keywords (`STYLE_PROMPTS`) and builds each prompt as style + character + setting + scene action. The constant parts are identical across scenes; only the action changes.
- **In plain words:** the AI first fills in a "casting sheet" (who, where, what look, which voice), then every picture is ordered with the same casting sheet stapled on top, so the person and place don't change.

### Example copying (few-shot leakage)
- **Technical:** small LLMs tend to copy the examples in their instructions word for word. Mitigations: give 2+ deliberately different examples, label them "format only, never copy", and test with unrelated inputs.
- **In plain words:** if you show a student one sample answer, they may hand it back unchanged. Show several different ones and say "just follow the format".

---

## Step 3: Narration → voice (`voice.py`)

### Edge TTS (`edge-tts`)
- **Technical:** a Python library that calls the text-to-speech service behind Microsoft Edge's "Read aloud". You send text, a voice name (`en-US-AriaNeural`) and a speaking rate (`-10%`), and get an MP3 back (24 kHz, mono). It needs internet and isn't an official paid API.
- **In plain words:** a free professional narrator on the internet. You hand over a line, and it sends back a recording of it being read aloud.

### Neural voice
- **Technical:** a TTS voice produced by a neural network trained on recordings of a real speaker, so intonation and pauses sound natural.
- **In plain words:** the difference between a robot reading word by word and a person telling a story.

### async / asyncio
- **Technical:** Python's way of running code that waits on the network without blocking. `edge_tts` functions are `async`, so we `await` them inside an `async def` and start everything with `asyncio.run()`.
- **In plain words:** like ordering food and doing other things while you wait, instead of standing at the counter. The script just has to "start the kitchen" with `asyncio.run()`.

### ffprobe (part of FFmpeg)
- **Technical:** a command-line tool that reads media metadata. We run it with `subprocess` to get each clip's duration in seconds.
- **In plain words:** a tool that tells you facts about a media file, like how long a song is, without playing it.

### Decibels (dB) / volumedetect
- **Technical:** loudness on a log scale; 0 dB is the maximum. FFmpeg's `volumedetect` filter reports mean volume. About -20 dB is normal speech, and -90 dB means silence.
- **In plain words:** a loudness meter. We used it to check the clips actually contain sound.

---

## Step 4: Images + audio → video (`assemble.py`)

### FFmpeg
- **Technical:** the standard command-line toolkit for decoding, filtering and encoding audio and video. We run it from Python with `subprocess.run([...])`. MoviePy is a Python wrapper that uses FFmpeg underneath; calling FFmpeg directly needs no extra package.
- **In plain words:** a video-editing studio with no screen. You describe the edit in one command, and it produces the file.

### Filter graph (`-filter_complex`)
- **Technical:** a chain of FFmpeg filters connected by labelled streams, e.g. `[0:v]scale,zoompan[v];[1:a]adelay,apad[a]`. `[0:v]` means "video from input 0"; `[v]` is a name we give the result; `-map` picks which results go into the file.
- **In plain words:** an assembly line written as text. Each station changes the picture or sound and passes it to the next, and the labels are the conveyor belts.

### zoompan (Ken Burns effect)
- **Technical:** generates frames from an image while changing zoom and position each frame. We use `z='1+0.15*on/frames'` (`on` = frame number) for a steady 15% zoom, centred. We upscale 4× first, because zoompan rounds positions to whole pixels and wobbles on small images.
- **In plain words:** a slow camera push into a still photo, like a documentary, which makes a still image feel alive.

### xfade / acrossfade
- **Technical:** `xfade` blends two video streams over `duration` seconds starting at `offset`; `acrossfade` does the same for audio. Each join overlaps clips by the fade length, so `offset = time so far − FADE`.
- **In plain words:** one scene gently dissolves into the next instead of jumping, and the sound blends the same way.

### adelay / apad
- **Technical:** `adelay=500:all=1` adds 0.5 s of silence at the start; `apad` adds silence at the end so the audio is as long as the clip (cut with `-t`).
- **In plain words:** a short breath before and after each line, so the narrator doesn't start talking right as the picture appears.

### H.264 + AAC in MP4 (`libx264`, `aac`, `yuv420p`, `crf`, `faststart`)
- **Technical:** H.264 is the most widely supported video codec; AAC is its usual audio partner; MP4 is the container holding both. `yuv420p` is the colour format all players accept. `-crf 20` sets quality (lower is better, 18–23 is typical). `+faststart` moves the index to the front so browsers can play before the download finishes.
- **In plain words:** the "plays everywhere" settings: phones, browsers, YouTube and WhatsApp.

---

## Step 5: Web UI (`app.py`)

### Streamlit
- **Technical:** a Python framework that turns a script into a web app. Widgets like `st.text_area`, `st.button`, `st.progress`, `st.status`, `st.video` and `st.columns` become HTML automatically. On every click, the whole script **re-runs top to bottom**; `st.session_state` keeps values between re-runs. Start it with `streamlit run app.py`, then open `http://localhost:8501`.
- **In plain words:** write a normal Python script, and Streamlit turns it into a web page with no HTML or JavaScript. Every button press replays the script, and `session_state` is its short-term memory.

### Model unloading (`keep_alive: 0`, `torch.mps.empty_cache()`)
- **Technical:** sending Ollama a request with `keep_alive: 0` frees the LLM from RAM immediately. After images, `del pipe` and `torch.mps.empty_cache()` release the GPU memory, so the next run can load the LLM again.
- **In plain words:** taking one big tool off the workbench before putting the next one down. 16 GB isn't room for both at once.

### Offline mode (`HF_HUB_OFFLINE=1`)
- **Technical:** an environment variable that tells Hugging Face libraries to use only the local cache and never contact the internet.
- **In plain words:** "use what's already on my Mac, don't go online". It's faster and never re-downloads 6 GB.

### AppTest (Streamlit testing)
- **Technical:** `streamlit.testing.v1.AppTest` runs an app headless. A script can type into widgets, click buttons and inspect output, with no browser needed.
- **In plain words:** a robot that uses your web page and reports what happened, which is how the app was tested here.

---

## Step 6: Cost note (`README.md`)

### Tokens and per-token pricing
- **Technical:** LLM APIs bill per million input and output tokens (a token is about ¾ of an English word). Ollama reports `prompt_eval_count` and `eval_count` per request, which is how we measured about 80–300 in and about 450 out per story.
- **In plain words:** the AI charges by the word, both for what you send and what it writes. We counted our words to estimate the bill.

### Unit economics (cost per video)
- **Technical:** add up the cost of each step for one output (LLM tokens + images + TTS characters + compute), then multiply by volume. Here it's about $0.01–0.03 per video on cloud APIs, versus about $0.0001 in electricity locally.
- **In plain words:** "how much does one video cost us to make?" It's the number you need before quoting a client a price.

### Model licences
- **Technical:** open model weights come with licences. SDXL Turbo is non-commercial; SD 1.5 and SDXL-Lightning allow commercial use under their terms.
- **In plain words:** "free to download" doesn't always mean "free to sell with". Check before a paid project.
