"""
Step 4: Images + audio -> one MP4 video

For each scene: take its image, add a slow zoom ("Ken Burns" effect) and its
narration. Then join all scene clips with smooth crossfade transitions.

Usage:
    .venv/bin/python assemble.py

Uses FFmpeg directly (no extra Python packages). Output: output/video.mp4
"""

import json
import subprocess
from pathlib import Path

from voice import audio_length  # reuse the ffprobe helper from step 3

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SCENES_FILE = Path("output/scenes.json")
IMAGES_DIR = Path("output/images")
AUDIO_DIR = Path("output/audio")
CLIPS_DIR = Path("output/clips")  # one temporary video per scene
VIDEO_FILE = Path("output/video.mp4")

SIZE = 1024        # final video is 1024x1024 (our images are square)
FPS = 30           # frames per second
ZOOM = 0.15        # zoom in by 15% over each scene
LEAD = 0.5         # seconds of silence before the narration starts
TAIL = 0.7         # seconds of silence after it ends
FADE = 0.5         # length of the crossfade between scenes


def run(command: list[str]) -> None:
    """Run an FFmpeg command and stop with its error message if it fails."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])  # last part = the real error


def make_scene_clip(image: Path, audio: Path, out: Path) -> float:
    """Image + narration -> one short video clip. Returns its length."""
    duration = LEAD + audio_length(audio) + TAIL
    frames = round(duration * FPS)

    # Video filter, step by step:
    #  scale=4x  -> upscale first so the zoom is smooth, not jittery
    #  zoompan   -> zoom from 1.0 to 1.15, centred, one output frame per tick
    #               ("on" = current frame number)
    #  format    -> yuv420p, the colour format every player understands
    video_filter = (
        f"scale={SIZE * 4}:-1,"
        f"zoompan=z='1+{ZOOM}*on/{frames}'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={SIZE}x{SIZE}:fps={FPS},"
        f"format=yuv420p"
    )
    # Audio filter: wait LEAD seconds, then pad silence until the clip ends
    audio_filter = f"adelay={int(LEAD * 1000)}:all=1,apad"

    run([
        "ffmpeg", "-y",                       # -y = overwrite old files
        "-i", str(image),
        "-i", str(audio),
        "-filter_complex",
        f"[0:v]{video_filter}[v];[1:a]{audio_filter}[a]",
        "-map", "[v]", "-map", "[a]",          # use our filtered streams
        "-t", f"{duration:.3f}",               # cut at exactly this length
        "-c:v", "libx264", "-c:a", "aac", "-ar", "44100",
        str(out),
    ])
    return duration


def join_clips(clips: list[Path], durations: list[float]) -> None:
    """Join scene clips with crossfades (video: xfade, audio: acrossfade)."""
    inputs = []
    for clip in clips:
        inputs += ["-i", str(clip)]

    # Build a chain: clip0 + clip1 -> v1, v1 + clip2 -> v2, and so on.
    # "offset" = when the fade starts in the joined video so far. Each fade
    # overlaps two clips by FADE seconds, so we subtract FADE per join.
    parts = []
    video_label, audio_label = "[0:v]", "[0:a]"
    elapsed = durations[0]
    for i in range(1, len(clips)):
        offset = elapsed - FADE
        parts.append(
            f"{video_label}[{i}:v]xfade=transition=fade"
            f":duration={FADE}:offset={offset:.3f}[v{i}]"
        )
        parts.append(f"{audio_label}[{i}:a]acrossfade=d={FADE}[a{i}]")
        video_label, audio_label = f"[v{i}]", f"[a{i}]"
        elapsed = offset + durations[i]

    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(parts),
        "-map", video_label, "-map", audio_label,
        "-c:v", "libx264", "-crf", "20",       # crf: lower = better quality
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",            # lets browsers start playing sooner
        str(VIDEO_FILE),
    ])


def assemble() -> None:
    scenes = json.loads(SCENES_FILE.read_text())["scenes"]
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. One clip per scene
    clips, durations = [], []
    for scene in scenes:
        n = scene["scene_number"]
        clip = CLIPS_DIR / f"scene_{n}.mp4"
        seconds = make_scene_clip(
            IMAGES_DIR / f"scene_{n}.png", AUDIO_DIR / f"scene_{n}.mp3", clip
        )
        clips.append(clip)
        durations.append(seconds)
        print(f"Scene {n}: {clip} ({seconds:.1f}s)")

    # 2. Join them with crossfades
    join_clips(clips, durations)
    print(f"\nDone: {VIDEO_FILE} ({audio_length(VIDEO_FILE):.1f}s)")


if __name__ == "__main__":
    assemble()
