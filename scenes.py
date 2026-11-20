"""
Step 1: Story prompt -> scenes (JSON)

Sends a story idea to a local LLM (Ollama) and gets back 3-4 scenes.
Each scene has: scene_number, description, narration, image_prompt.

Usage:
    .venv/bin/python scenes.py "A robot learns to paint in a quiet village"
"""

import json
import sys
from pathlib import Path

import requests
from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
OUTPUT_FILE = Path("output/scenes.json")
MAX_ATTEMPTS = 3  # small models sometimes return bad JSON, so we retry

# One fixed character description. We add it to EVERY image prompt ourselves
# (in code), so the character looks the same in every image we generate later.
# Keep it short (image models only read ~77 tokens) and avoid competing
# colours: "yellow coat + green boots" made the model paint a green coat.
CHARACTER = (
    "Mira, a 10-year-old girl with curly red hair, freckles, "
    "yellow raincoat and yellow rain boots"
)


# ---------------------------------------------------------------------------
# Data shape (Pydantic checks the LLM's output matches this)
# ---------------------------------------------------------------------------
class Scene(BaseModel):
    scene_number: int = Field(ge=1)
    description: str = Field(min_length=1)   # what happens in the scene
    narration: str = Field(min_length=1)     # the line the voiceover will say
    image_prompt: str = Field(min_length=1)  # prompt for the image model


class Story(BaseModel):
    # min/max length = we want 3 or 4 scenes, nothing else
    scenes: list[Scene] = Field(min_length=3, max_length=4)


# ---------------------------------------------------------------------------
# Talking to Ollama
# ---------------------------------------------------------------------------
def ask_ollama(story_prompt: str) -> str:
    """Send the prompt to Ollama and return the raw text reply."""
    system_message = (
        "You are a storyboard writer for short videos. "
        "Split the user's story into 3 or 4 scenes. For each scene write:\n"
        "- description: one or two sentences about what happens\n"
        "- narration: one short sentence for a voiceover (under 25 words)\n"
        "- image_prompt: a visual description of the scene for an image "
        "generator (setting, action, lighting, style). Refer to the main "
        "character only as 'the girl' - do NOT describe her looks.\n"
        "Number scenes starting at 1. Reply with JSON only."
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_message},
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


def generate_scenes(story_prompt: str) -> Story:
    """Ask the LLM for scenes, validate them, retry if they're invalid."""
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

    # Clean up: renumber scenes 1..N and add the fixed character to each
    # image prompt so every image shows the same person.
    for number, scene in enumerate(story.scenes, start=1):
        scene.scene_number = number
        scene.image_prompt = f"{CHARACTER}. {scene.image_prompt}"

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
    """Write the scenes to output/scenes.json for the next steps."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(story.model_dump(), indent=2))


# ---------------------------------------------------------------------------
# Run from the command line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Use the prompt from the command line, or a default test prompt
    prompt = " ".join(sys.argv[1:]) or (
        "A girl finds a lost baby fox in the forest during a storm "
        "and helps it find its way home."
    )

    print(f"Generating scenes for: {prompt}\n")
    story = generate_scenes(prompt)

    save_scenes(story)  # writes output/scenes.json

    print(json.dumps(story.model_dump(), indent=2))
    print(f"\nSaved to {OUTPUT_FILE}")
