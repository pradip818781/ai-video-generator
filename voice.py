"""
Step 3: Scenes -> voiceover audio

Reads the narration line of each scene in output/scenes.json and turns it
into speech with Edge TTS (Microsoft's free online voices).
Saves output/audio/scene_N.mp3 and prints how long each clip is.

Usage:
    .venv/bin/python voice.py

Needs internet (the speech is made on Microsoft's servers).
List all voices with:  .venv/bin/edge-tts --list-voices
"""

import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SCENES_FILE = Path("output/scenes.json")
AUDIO_DIR = Path("output/audio")

VOICE = "en-US-AriaNeural"  # a warm storytelling voice
RATE = "-10%"               # 10% slower than normal = calmer narration


async def make_clip(text: str, path: Path) -> None:
    """Turn one line of text into an MP3 file."""
    # Communicate = one request to the TTS service with our text + voice
    communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE)
    await communicate.save(str(path))  # download the audio to a file


def audio_length(path: Path) -> float:
    """Return the clip length in seconds, using ffprobe (comes with FFmpeg)."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",  # only ask for the duration
            "-of", "csv=p=0",                    # print just the number
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def generate_voiceover() -> None:
    # 1. Read the scenes made in step 1
    scenes = json.loads(SCENES_FILE.read_text())["scenes"]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # 2. One audio clip per scene
    total = 0.0
    for scene in scenes:
        number = scene["scene_number"]
        path = AUDIO_DIR / f"scene_{number}.mp3"

        await make_clip(scene["narration"], path)

        seconds = audio_length(path)
        total += seconds
        print(f"Scene {number}: {path} ({seconds:.1f}s) - {scene['narration']}")

    # The video in step 4 will be roughly this long
    print(f"\nTotal narration: {total:.1f}s")


if __name__ == "__main__":
    # edge_tts is "async" (it waits on the network), so we start it with
    # asyncio.run() - the standard way to run async code from a script.
    asyncio.run(generate_voiceover())
