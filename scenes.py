"""
Step 1: Story prompt -> scenes (JSON)

Sends a story idea to a local LLM (Ollama) and gets back:
  - character: what the main character looks like (designed for THIS story)
  - style:     the visual style that fits the story (photo, storybook, ...)
  - narrator:  which voice should read it (female / male)
  - scenes:    3-4 scenes, each with description, narration, image_prompt

Usage:
    .venv/bin/python scenes.py "A teenage boy presenting the weather forecast on TV"
    .venv/bin/python scenes.py --style storybook "A robot learns to paint"
"""

import argparse
import json
from pathlib import Path
from typing import Literal

import requests
from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
OUTPUT_FILE = Path("output/scenes.json")
MAX_ATTEMPTS = 3  # small models sometimes return bad JSON, so we retry

# The visual styles we support. The LLM must pick one of these names, and
# images.py turns the name into proven image-model keywords.
Style = Literal["photorealistic", "cinematic", "storybook", "3d_animation", "anime"]
STYLES = list(Style.__args__)  # ["photorealistic", "cinematic", ...]


# ---------------------------------------------------------------------------
# Data shape (Pydantic checks the LLM's output matches this)
# ---------------------------------------------------------------------------
class Scene(BaseModel):
    scene_number: int = Field(ge=1)
    description: str = Field(min_length=1)   # what happens in the scene
    narration: str = Field(min_length=1)     # the line the voiceover will say
    image_prompt: str = Field(min_length=1)  # setting + action for the image model


class Story(BaseModel):
    # One character design, reused in every image so they look the same
    character: str = Field(min_length=10, max_length=200)
    # One main location, reused in every image so the place stays the same
    setting: str = Field(min_length=5, max_length=150)
    style: Style                                 # must be one of STYLES
    narrator: Literal["female", "male"]          # voice for the narration
    scenes: list[Scene] = Field(min_length=3, max_length=4)


# ---------------------------------------------------------------------------
# Instructions for the LLM
# ---------------------------------------------------------------------------
SYSTEM_MESSAGE = """You are a storyboard writer for short videos.
Turn the user's story into a JSON storyboard with these fields:

character: a SHORT visual description of the main character (max 20 words):
  age, gender, hair, and ONE outfit visible from the waist up, using at
  most two colors. It MUST match the story exactly (a "teenage boy" story
  gets a teenage boy). Format examples only - never copy them, invent
  details that fit THIS story:
  "a 70-year-old woman with a grey bun, green cardigan and cream blouse"
  "a 9-year-old girl with two black braids and an orange hoodie"

setting: the main location of THIS story, max 12 words, used for every
  scene so the place stays consistent. Format examples only:
  "a small wooden fishing boat on a calm lake at sunrise"
  "a busy night market street with paper lanterns"

style: the visual style that best fits the story. One of:
  photorealistic (real-world, news, ads, documentary),
  cinematic (dramatic, movie-like),
  storybook (children's stories, fairy tales),
  3d_animation (fun, family, Pixar-like),
  anime (Japanese animation look)

narrator: "male" or "female" - the voice that fits the story best
  (usually the main character's gender if they are speaking).

scenes: 3 or 4 scenes. For each scene write:
  - description: one or two sentences about what happens
  - narration: one sentence for the voiceover, under 25 words. If the
    character is speaking (e.g. presenting news), write it in first person.
  - image_prompt: under 20 words describing ONLY the action, camera angle
    and lighting of this moment. Do NOT describe the character's looks or
    the main setting (both are added automatically). Refer to the character
    by a short noun such as "the boy" or "the woman", matching their gender.
    Only mention a place if this scene happens somewhere else.

Number scenes starting at 1. Reply with JSON only."""


# ---------------------------------------------------------------------------
# Talking to Ollama
# ---------------------------------------------------------------------------
def ask_ollama(story_prompt: str) -> str:
    """Send the prompt to Ollama and return the raw text reply."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": story_prompt},
        ],
        # Passing a JSON schema here makes Ollama force the reply into
        # that exact shape ("structured outputs").
        "format": Story.model_json_schema(),
        "stream": False,  # get one complete reply instead of chunks
        "options": {"temperature": 0.7},
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()  # error out on HTTP 4xx/5xx
    return response.json()["message"]["content"]


def generate_scenes(story_prompt: str, style: str | None = None) -> Story:
    """Ask the LLM for a storyboard, validate it, retry if it's invalid.

    style: force a visual style (one of STYLES), or None to let the LLM pick.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = ask_ollama(story_prompt)
        try:
            # Parse + validate in one step. Raises ValidationError if wrong.
            story = Story.model_validate_json(raw)
            break
        except ValidationError as error:
            print(f"Attempt {attempt}: invalid output, retrying...\n{error}")
    else:
        # The loop finished without "break" = every attempt failed
        raise RuntimeError(f"No valid scenes after {MAX_ATTEMPTS} attempts")

    # The user's choice wins over the LLM's choice
    if style:
        story.style = style

    # Clean up: number the scenes 1..N
    for number, scene in enumerate(story.scenes, start=1):
        scene.scene_number = number

    return story


def unload_model() -> None:
    """Tell Ollama to free the LLM's memory right now (same as `ollama stop`).

    keep_alive=0 means "don't keep this model loaded after this request".
    We do this before loading the image model, so both don't fill 16 GB RAM.
    """
    requests.post(
        "http://localhost:11434/api/generate",
        json={"model": MODEL, "keep_alive": 0},
        timeout=60,
    )


def save_scenes(story: Story) -> None:
    """Write the storyboard to output/scenes.json for the next steps."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(story.model_dump(), indent=2))


# ---------------------------------------------------------------------------
# Run from the command line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # argparse reads the command-line words: an optional --style and the story
    parser = argparse.ArgumentParser(description="Story prompt -> scenes")
    parser.add_argument("story", nargs="*", help="your story idea")
    parser.add_argument("--style", choices=STYLES, help="force a visual style")
    args = parser.parse_args()

    prompt = " ".join(args.story) or (
        "A girl finds a lost baby fox in the forest during a storm "
        "and helps it find its way home."
    )

    print(f"Generating scenes for: {prompt}\n")
    story = generate_scenes(prompt, style=args.style)
    save_scenes(story)  # writes output/scenes.json

    print(json.dumps(story.model_dump(), indent=2))
    print(f"\nSaved to {OUTPUT_FILE}")
