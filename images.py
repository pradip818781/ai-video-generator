"""
Step 2: Scenes -> images

Reads output/scenes.json (made by scenes.py) and creates one image per
scene with SDXL Turbo, running on the Mac's GPU (Apple "MPS").

Each image prompt is built from four parts, in this order:
    style keywords  +  character  +  setting  +  scene action

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
MODEL_ID = "stabilityai/sdxl-turbo"  # downloaded once (~6 GB), then cached

# Same seed for every scene = same "starting noise" each time, which helps
# the character look similar across images. Change it to get a new look.
SEED = 42

# SDXL Turbo is trained to make good images in very few steps (1-4).
STEPS = 4
WIDTH, HEIGHT = 512, 512  # Turbo's native size; bigger is slower/worse

# Style name (picked by the LLM or the user) -> keywords the image model
# responds well to. Short on purpose: the model only reads ~77 tokens.
STYLE_PROMPTS = {
    "photorealistic": "professional photo, photorealistic, natural lighting, sharp focus",
    "cinematic": "cinematic film still, dramatic lighting, shallow depth of field",
    "storybook": "children's storybook illustration, soft watercolor, warm colors",
    "3d_animation": "3D animated movie still, cute, soft lighting, vibrant colors",
    "anime": "anime style illustration, clean line art, vibrant colors",
}

MAX_TOKENS = 77  # SDXL's text encoders ignore anything after this


def load_pipeline():
    """Download (first time only) and load the image model onto the GPU."""
    # "mps" = Apple Silicon GPU. Fall back to CPU if it isn't available.
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Loading {MODEL_ID} on {device}...")

    pipe = AutoPipelineForText2Image.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,  # half precision = half the memory
        variant="fp16",             # download the smaller fp16 weights
    )
    return pipe.to(device)


def build_prompt(story: dict, scene: dict) -> str:
    """Combine the four parts. Most important first, since the end may be cut.

    Style, character and setting are the SAME for every scene - that's what
    keeps the video consistent. Only the scene action changes.
    """
    return (f"{STYLE_PROMPTS[story['style']]}, {story['character']}, "
            f"in {story['setting']}, {scene['image_prompt']}")


def generate_images():
    # 1. Read the storyboard made in step 1
    story = json.loads(SCENES_FILE.read_text())
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Load the model once and reuse it for every scene
    pipe = load_pipeline()
    print(f"Style: {story['style']} | Character: {story['character']} "
          f"| Setting: {story['setting']}")

    # 3. One image per scene
    for scene in story["scenes"]:
        number = scene["scene_number"]
        start = time.time()
        prompt = build_prompt(story, scene)

        # Warn if the prompt is too long (the end of it would be ignored)
        tokens = len(pipe.tokenizer(prompt).input_ids)
        if tokens > MAX_TOKENS:
            print(f"  Warning: scene {number} prompt is {tokens} tokens; "
                  f"words after ~{MAX_TOKENS} are ignored")

        # A new generator with the SAME seed for each scene
        generator = torch.Generator("cpu").manual_seed(SEED)

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
        print(f"Scene {number}: saved {path} ({time.time() - start:.1f}s, {tokens} tokens)")

    # 4. Free the model's memory (matters in the web app, where the next
    #    run loads the LLM again in the same process)
    del pipe
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


if __name__ == "__main__":
    generate_images()
