"""
Step 2: Scenes -> images

Reads output/scenes.json (made by scenes.py) and creates one image per
scene with SDXL Turbo, running on the Mac's GPU (Apple "MPS").

Usage:
    .venv/bin/python images.py

Tip: stop Ollama's model first to free memory:  ollama stop llama3.1:8b
"""

import json
import time
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SCENES_FILE = Path("output/scenes.json")
IMAGES_DIR = Path("output/images")
MODEL_ID = "stabilityai/sdxl-turbo"  # downloaded once (~7 GB), then cached

# Same seed for every scene = same "starting noise" each time, which helps
# the character look similar across images. Change it to get a new look.
SEED = 42

# SDXL Turbo is trained to make good images in very few steps (1-4).
# More steps = slightly better detail but slower.
STEPS = 4
WIDTH, HEIGHT = 512, 512  # Turbo's native size; bigger is slower

# One fixed art style added to the FRONT of every prompt. Without it the
# model picked a different style per scene (cartoon vs. photo).
# It goes first because the model reads only the first ~77 tokens.
STYLE = "children's storybook illustration, soft watercolor, warm colors"


def load_pipeline():
    """Download (first time only) and load the image model onto the GPU."""
    # "mps" = Apple Silicon GPU. Fall back to CPU if it isn't available.
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Loading {MODEL_ID} on {device} (first run downloads ~7 GB)...")

    pipe = AutoPipelineForText2Image.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,  # half precision = half the memory
        variant="fp16",             # download the smaller fp16 weights
    )
    return pipe.to(device)


def generate_images():
    # 1. Read the scenes made in step 1
    scenes = json.loads(SCENES_FILE.read_text())["scenes"]
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Load the model once and reuse it for every scene
    pipe = load_pipeline()

    # 3. One image per scene
    for scene in scenes:
        number = scene["scene_number"]
        start = time.time()

        # A new generator with the SAME seed for each scene
        generator = torch.Generator("cpu").manual_seed(SEED)

        prompt = f"{STYLE}, {scene['image_prompt']}"

        image = pipe(
            prompt=prompt,
            num_inference_steps=STEPS,
            guidance_scale=0.0,  # Turbo is trained to work without guidance
            width=WIDTH,
            height=HEIGHT,
            generator=generator,
        ).images[0]

        path = IMAGES_DIR / f"scene_{number}.png"
        image.save(path)
        print(f"Scene {number}: saved {path} ({time.time() - start:.1f}s)")

    # 4. Free the model's memory (matters in the web app, where the next
    #    run loads the LLM again in the same process)
    del pipe
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


if __name__ == "__main__":
    generate_images()
