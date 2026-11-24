#!/usr/bin/env python3
"""
Autonomous Viral Instagram Reels Engine (Zero-Cost Architecture)
- 4-Source Live Trend & Relatable Comedy Research (Google Trends + Reddit Hot JSON + History)
- Two-Step Gemini Showrunner (Research Analyst -> 5-Mode Retention Scriptwriter)
- Multi-Model Image Generation (Gemini Image / Imagen + 3D-Shaded Procedural Fallback)
- Instagram Safe-Zone Renderer:
    * Episodic Corner Badge (EP. XX)
    * 2-Line Top Hook Banner with Gold Keyword Highlight
    * Left-vs-Right Split Labels & Equation Overlays
    * Karaoke Active-Word Highlight Subtitle Pill
    * Procedural Foley SFX (Whoosh/Pop/Bass) + Ambient Synth Loop
- GitHub Pages Hosting + Meta Graph API Reels Auto-Publisher
"""

import os
import re
import sys
import json
import math
import time
import wave
import struct
import random
import shutil
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# ==============================================================================
# 1. CONFIGURATION & ENVIRONMENT
# ==============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
GITHUB_PAGES_BASE_URL = os.environ.get("GITHUB_PAGES_BASE_URL", "").strip().rstrip("/")
USE_TRIAL_REELS = os.environ.get("TRIAL_REELS", "false").strip().lower() == "true"

WIDTH = 1080
HEIGHT = 1920
FPS = 24
DURATION_SEC = 10
TOTAL_FRAMES = FPS * DURATION_SEC  # 240 frames (4 beats x 2.5s)
SAMPLE_RATE = 44100

ROOT_DIR = Path(__file__).resolve().parent
DOCS_DIR = ROOT_DIR / "docs"
MEDIA_DIR = DOCS_DIR / "reels"
WORK_DIR = ROOT_DIR / "build_tmp"
HISTORY_FILE = ROOT_DIR / "history.json"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)

HOOK_ARCHETYPES = [
    "EQUATION_HOOK",
    "LEFT_VS_RIGHT",
    "DEFINITION_FRAME",
    "ANTICIPATION_COLD_OPEN",
    "MIRROR_QUESTION",
]


# ==============================================================================
# 2. FONT & SAFE-ZONE UTILITIES
# ==============================================================================
def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for w in words[1:]:
        test = f"{current} {w}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def load_history() -> Dict[str, Any]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"episode_count": 0, "reels": []}


def save_history(history: Dict[str, Any]) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


# ==============================================================================
# 3. 4-SOURCE AUTONOMOUS LIVE RESEARCH ENGINE
# ==============================================================================
def fetch_url_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TrendResearchBot/2.0; +https://github.com)",
            "Accept": "application/json, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def gather_google_trends() -> List[str]:
    url = "https://trends.google.com/trending/rss?geo=US"
    topics = []
    try:
        xml_data = fetch_url_text(url)
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item")[:10]:
            title_el = item.find("title")
            traffic_el = item.find("{https://trends.google.com/trending/rss}approx_traffic")
            if title_el is not None and title_el.text:
                traffic = f" ({traffic_el.text})" if (traffic_el is not None and traffic_el.text) else ""
                topics.append(f"{title_el.text.strip()}{traffic}")
    except Exception as exc:
        print(f"[Research] Google Trends fallback ({exc})")
    return topics


def gather_reddit_comedy_threads() -> List[Dict[str, str]]:
    subreddits = ["me_irl", "Showerthoughts", "memes"]
    findings = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=6"
        try:
            raw = fetch_url_text(url)
            payload = json.loads(raw)
            children = payload.get("data", {}).get("children", [])
            for child in children:
                data = child.get("data", {})
                if data.get("stickied") or data.get("over_18"):
                    continue
                title = (data.get("title") or "").strip()
                score = data.get("score", 0)
                if title and len(title) > 10:
                    findings.append({
                        "subreddit": f"r/{sub}",
                        "title": title[:160],
                        "upvotes": str(score),
                    })
        except Exception as exc:
            print(f"[Research] r/{sub} skipped ({exc})")
    return findings[:12]


def run_autonomous_research(client: Any, text_model: str, history: Dict[str, Any]) -> Dict[str, Any]:
    print("[Research] Gathering live Google Trends & Reddit hot topics...")
    google_trends = gather_google_trends()
    reddit_posts = gather_reddit_comedy_threads()

    past_hooks = [r.get("hook_line_1", "") + " " + r.get("hook_line_2", "") for r in history.get("reels", [])[-12:]]
    last_archetype = history.get("reels", [{}])[-1].get("archetype", "") if history.get("reels") else ""
    candidate_archetypes = [a for a in HOOK_ARCHETYPES if a != last_archetype]
    chosen_archetype = random.choice(candidate_archetypes)

    research_prompt = f"""
You are a viral short-form content strategist analyzing live cultural data to engineer a 10-second animated comedy Reel that achieves >120% average watch duration.

LIVE GOOGLE TRENDS TODAY:
{json.dumps(google_trends, indent=2)}

LIVE REDDIT RELATABLE COMEDY & SHOWERTHOUGHTS TODAY:
{json.dumps(reddit_posts, indent=2)}

RECENTLY USED HOOKS (DO NOT REPEAT):
{json.dumps(past_hooks, indent=2)}

ASSIGNED VIRAL RETENTION ARCHETYPE: {chosen_archetype}
Archetype definitions:
- EQUATION_HOOK: Top hook presents an incomplete equation ("TALENT + NO AUDIENCE:" or "PAYDAY + 2 HOURS:") and the final scene reveals the brutal 2-word truth ("A HOBBY." or "$4.12 LEFT.").
- LEFT_VS_RIGHT: Side-by-side comparison of two mindsets ("99% OF PEOPLE" vs "THAT ONE FRIEND" or "2020 YOU" vs "2026 YOU") facing the exact same everyday situation.
- DEFINITION_FRAME: Framed as a universal law ("THE DEFINITION OF" + "'BROKE CONFIDENCE':") illustrated by an escalating 4-beat visual skit.
- ANTICIPATION_COLD_OPEN: Beat 1 starts AT THE CLIMAX of a disaster ("HOW I ENDED UP HERE IN 6 SECONDS:"), Beat 2 rewinds, Beat 3-4 show the absurd chain reaction.
- MIRROR_QUESTION: Opens with a direct ego-trap question ("WHICH TYPE ARE YOU?" or "WHY DO WE ALL DO THIS?") that forces viewers to watch all 4 beats and tag a friend.

TASK:
1. Synthesize ONE hyper-relatable, unorthodox comedic premise inspired by today's live trends or everyday human psychology (money, work, friends, late-night overthinking, gym, AI, dating, or groceries).
2. Design a psychological curiosity gap so viewers CANNOT swipe away in the first 1.5 seconds.
3. Include a subtle comment-bait detail or debatable question so viewers flood the comments.

Return STRICT JSON only:
{{
  "chosen_archetype": "{chosen_archetype}",
  "trend_inspiration": "short note on what live trend or insight inspired this",
  "core_relatable_truth": "one-sentence psychological insight",
  "curiosity_gap": "why the viewer must watch until second 10",
  "comment_bait_detail": "subtle visual or verbal detail people will argue/comment about"
}}
"""
    try:
        resp = client.models.generate_content(
            model=text_model,
            contents=research_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.9,
            ),
        )
        brief = json.loads(resp.text)
        brief["chosen_archetype"] = chosen_archetype
        print(f"[Research] Archetype={chosen_archetype} | Premise={brief.get('core_relatable_truth', '')[:80]}")
        return brief
    except Exception as exc:
        print(f"[Research] Analyst fallback ({exc})")
        return {
            "chosen_archetype": chosen_archetype,
            "trend_inspiration": "Universal everyday relatable psychology",
            "core_relatable_truth": "Everyone says they are 'just browsing' online until a $149 checkout happens at 2 AM.",
            "curiosity_gap": "Starts at the empty bank notification and rewinds to show the 3 micro-excuses.",
            "comment_bait_detail": "The cart has 1 useful item and 4 completely useless gadgets.",
        }


# ==============================================================================
# 4. GEMINI MODEL DISCOVERY & SHOWRUNNER SCRIPTWRITER
# ==============================================================================
def discover_models(client: Any) -> Tuple[str, List[str], List[str]]:
    text_candidates = []
    gemini_img_candidates = []
    imagen_candidates = []

    try:
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            lower = name.lower()
            if "imagen" in lower:
                imagen_candidates.append(name)
            elif "image" in lower:
                gemini_img_candidates.append(name)
            elif "flash" in lower and "tts" not in lower and "audio" not in lower and "lite" not in lower:
                text_candidates.append(name)
    except Exception as exc:
        print(f"[Models] List warning: {exc}")

    # Prefer fast modern Gemini Flash models
    preferred_text = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.0-flash"]
    chosen_text = next((p for p in preferred_text if p in text_candidates), None)
    if not chosen_text:
        chosen_text = text_candidates[0] if text_candidates else "gemini-2.5-flash"

    print(f"[Models] Text={chosen_text} | GeminiImage={gemini_img_candidates} | Imagen={imagen_candidates}")
    return chosen_text, gemini_img_candidates, imagen_candidates


def generate_viral_script(
    client: Any,
    text_model: str,
    research_brief: Dict[str, Any],
    episode_num: int,
) -> Dict[str, Any]:
    archetype = research_brief.get("chosen_archetype", "DEFINITION_FRAME")

    prompt = f"""
You are the showrunner of a viral 3D/2D stylized character comedy Instagram Reels page (inspired by @nobodytoldme_0, @neuronvisuals, @canwebuildthis, and @yearlikeaghost).
This is Episode #{episode_num}.

RESEARCH BRIEF:
{json.dumps(research_brief, indent=2)}

WRITE A 4-BEAT (10-SECOND) COMEDY REEL SCRIPT.
Rules for maximum retention (>130% watch time):
1. Top Hook Banner (visible throughout):
   - hook_line_1: 2-4 words in ALL CAPS (white text), e.g., "THE DEFINITION OF" or "TALENT + NO AUDIENCE:" or "99% OF PEOPLE"
   - hook_line_2_gold: 2-4 words in ALL CAPS (gold highlight), e.g., "'BROKE CONFIDENCE':" or "VS. THAT ONE FRIEND"
2. If archetype is LEFT_VS_RIGHT, provide left_label (e.g., "NORMAL YOU") and right_label (e.g., "2 AM YOU"). Otherwise leave them empty strings.
3. Exactly 4 beats (Beat 1 = 0.0-2.5s, Beat 2 = 2.5-5.0s, Beat 3 = 5.0-7.5s, Beat 4 = 7.5-10.0s).
4. Each beat's spoken caption MUST be 4 to 7 punchy, conversational words (easy to read in 2.5s with karaoke word highlighting).
5. Beat 4 MUST end with an ironic twist or seamless loop back into Beat 1.
6. Provide a rich, clean 3D stylized CGI visual prompt for each beat featuring our signature recurring characters:
   - "Stu": expressive stylized 3D character with oversized round glasses, yellow hoodie, big worried/excited eyes.
   - "Pip": sleek minimalist 3D sidekick character in a dark cap with deadpan eyebrows.
   - Visual prompts must specify: "Stylized 3D Pixar-meets-Blender character illustration, dramatic studio rim lighting, clean minimalist background, expressive face, NO text or words inside the image."
7. Write an engaging Instagram caption with a comment-trigger question + 5 targeted hashtags.

Return STRICT JSON only:
{{
  "archetype": "{archetype}",
  "hook_line_1": "THE DEFINITION OF",
  "hook_line_2_gold": "'2 AM CONFIDENCE':",
  "left_label": "",
  "right_label": "",
  "instagram_caption": "Be honest, which beat is literally you? 👇😂 #relatable #comedyreels #3danimation #funnyreels #memes",
  "beats": [
    {{
      "beat_number": 1,
      "caption": "Me saying I will sleep early",
      "sfx": "whoosh",
      "mood": "confident",
      "visual_prompt": "Stylized 3D character Stu with oversized round glasses and yellow hoodie confidently tucking into bed at 10 PM with a peaceful smile, cozy dark bedroom with warm lamp rim light, Blender 3D render style, no text"
    }},
    {{
      "beat_number": 2,
      "caption": "My brain remembering one awkward text",
      "sfx": "pop",
      "mood": "shocked",
      "visual_prompt": "Stylized 3D character Stu with oversized round glasses sitting bolt upright in bed with wide shocked eyes staring at a glowing phone screen in the dark, dramatic blue rim light, Blender 3D render style, no text"
    }},
    {{
      "beat_number": 3,
      "caption": "Now researching medieval castle defense tactics",
      "sfx": "rise",
      "mood": "manic",
      "visual_prompt": "Stylized 3D character Stu with oversized round glasses surrounded by floating glowing holographic browser tabs at 3 AM with messy hair and wide manic eyes, dramatic cyan and amber lighting, Blender 3D render style, no text"
    }},
    {{
      "beat_number": 4,
      "caption": "Alarm rings in exactly four minutes",
      "sfx": "bass_drop",
      "mood": "defeated",
      "visual_prompt": "Stylized 3D character Stu with oversized round glasses face-down on his desk next to an alarm clock glowing 06:56 AM in bright red, exhausted comedic pose, Blender 3D render style, no text"
    }}
  ]
}}
"""
    resp = client.models.generate_content(
        model=text_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.85,
        ),
    )
    script_data = json.loads(resp.text)
    if len(script_data.get("beats", [])) < 4:
        raise ValueError("Gemini returned fewer than 4 beats")
    script_data["beats"] = script_data["beats"][:4]
    return script_data


# ==============================================================================
# 5. MULTI-MODEL IMAGE GENERATOR + 3D PROCEDURAL FALLBACK
# ==============================================================================
def render_procedural_3d_scene(beat: Dict[str, Any], out_path: Path, seed: int) -> None:
    """Guaranteed high-contrast stylized 3D-shaded fallback if API image quotas fail."""
    rng = random.Random(seed + beat.get("beat_number", 1) * 97)
    w, h = 1080, 1080
    img = Image.new("RGB", (w, h), (16, 20, 32))
    draw = ImageDraw.Draw(img)

    mood = beat.get("mood", "confident").lower()
    palettes = {
        "confident": ((22, 34, 58), (255, 209, 102), (56, 189, 248)),
        "shocked": ((40, 18, 54), (244, 63, 94), (168, 85, 247)),
        "manic": ((15, 42, 46), (52, 211, 153), (251, 191, 36)),
        "defeated": ((38, 22, 26), (248, 113, 113), (148, 163, 184)),
    }
    bg_base, accent_1, accent_2 = palettes.get(mood, palettes["confident"])

    # Radial studio backdrop glow
    for r in range(520, 20, -16):
        ratio = 1.0 - (r / 520.0)
        c = tuple(
            min(255, int(bg_base[i] + (accent_2[i] - bg_base[i]) * (ratio ** 2.2) * 0.45))
            for i in range(3)
        )
        draw.ellipse((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r), fill=c)

    # Studio floor reflection plane
    draw.rectangle((0, 760, w, h), fill=(10, 13, 22))
    draw.line((0, 760, w, 760), fill=accent_2, width=4)

    # Stylized 3D Character (Stu in yellow hoodie + big round glasses)
    cx, cy = w // 2 + rng.randint(-25, 25), 540
    # Hoodie body
    draw.rounded_rectangle((cx - 170, cy + 120, cx + 170, cy + 360), radius=70, fill=accent_1, outline=(255, 255, 255), width=5)
    # Head sphere with 3D rim highlight
    draw.ellipse((cx - 145, cy - 165, cx + 145, cy + 125), fill=(255, 218, 185), outline=accent_1, width=6)
    draw.arc((cx - 135, cy - 155, cx + 135, cy + 115), start=200, end=340, fill=(255, 255, 255), width=6)

    # Oversized round glasses
    eye_offset = 66
    glass_r = 56
    for side in (-1, 1):
        gx = cx + side * eye_offset
        gy = cy - 25
        draw.ellipse((gx - glass_r, gy - glass_r, gx + glass_r, gy + glass_r), fill=(245, 248, 255), outline=(25, 28, 38), width=10)
        pupil_r = 24 if mood in ("shocked", "manic") else 18
        px = gx + rng.randint(-8, 8)
        py = gy + rng.randint(-6, 6)
        draw.ellipse((px - pupil_r, py - pupil_r, px + pupil_r, py + pupil_r), fill=(18, 22, 32))
        draw.ellipse((px - 8, py - 10, px - 1, py - 3), fill=(255, 255, 255))
    # Bridge of glasses
    draw.line((cx - 12, cy - 25, cx + 12, cy - 25), fill=(25, 28, 38), width=10)

    # Expressive mouth by mood
    if mood == "confident":
        draw.arc((cx - 45, cy + 35, cx + 45, cy + 80), start=10, end=170, fill=(30, 30, 40), width=8)
    elif mood in ("shocked", "manic"):
        draw.ellipse((cx - 28, cy + 42, cx + 28, cy + 92), fill=(30, 30, 40))
    else:
        draw.arc((cx - 45, cy + 55, cx + 45, cy + 95), start=190, end=350, fill=(30, 30, 40), width=8)

    img = img.filter(ImageFilter.SMOOTH_MORE)
    img.save(out_path, "PNG")


def generate_beat_artwork(
    client: Any,
    gemini_img_models: List[str],
    imagen_models: List[str],
    beat: Dict[str, Any],
    out_path: Path,
    seed: int,
) -> str:
    prompt = beat.get("visual_prompt", "Stylized 3D character comedy scene, dramatic lighting, no text")

    # 1. Try Gemini native image generation models
    for model_name in gemini_img_models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            for cand in getattr(resp, "candidates", []) or []:
                for part in getattr(cand.content, "parts", []) or []:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        out_path.write_bytes(inline.data)
                        return model_name
        except Exception as exc:
            print(f"[Art] {model_name} skipped: {exc}")

    # 2. Try Imagen models
    for model_name in imagen_models:
        try:
            resp = client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    output_mime_type="image/png",
                ),
            )
            generated = getattr(resp, "generated_images", []) or []
            if generated and getattr(generated[0], "image", None):
                generated[0].image.save(str(out_path))
                return model_name
        except Exception as exc:
            print(f"[Art] {model_name} skipped: {exc}")

    # 3. Guaranteed procedural 3D fallback
    render_procedural_3d_scene(beat, out_path, seed)
    return "procedural_3d_fallback"


# ==============================================================================
# 6. PROCEDURAL FOLEY SFX & AMBIENT SYNTH AUDIO ENGINE
# ==============================================================================
def synthesize_reel_audio(beats: List[Dict[str, Any]], wav_path: Path, seed: int) -> None:
    """Generates a 10-second 44.1kHz stereo WAV with warm lo-fi synth chords + transition SFX."""
    rng = random.Random(seed)
    total_samples = SAMPLE_RATE * DURATION_SEC
    beat_samples = total_samples // 4

    # Minor/lo-fi chord root frequencies (Hz) for emotional retention
    chord_sets = [
        [220.0, 261.63, 329.63, 392.0],   # Am7
        [174.61, 220.0, 261.63, 329.63],  # Fmaj7
        [196.0, 246.94, 293.66, 349.23],  # G6
        [164.81, 196.0, 246.94, 293.66],  # Em7
    ]

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        frames_bytes = bytearray()
        for i in range(total_samples):
            t = i / SAMPLE_RATE
            beat_idx = min(3, i // beat_samples)
            local_t = (i % beat_samples) / SAMPLE_RATE
            sfx_type = beats[beat_idx].get("sfx", "pop")

            # Warm ambient pad
            freqs = chord_sets[beat_idx]
            pad = 0.0
            for idx_f, f in enumerate(freqs):
                detune = 1.0 + (0.002 if idx_f % 2 == 0 else -0.002)
                pad += math.sin(2.0 * math.pi * f * detune * t) * 0.055
            # Gentle LFO pulse
            lfo = 0.75 + 0.25 * math.sin(2.0 * math.pi * 1.6 * t)
            pad *= lfo

            # Transition SFX in the first 0.28s of each beat
            sfx = 0.0
            if local_t < 0.28:
                env = math.exp(-local_t * 14.0)
                if sfx_type == "whoosh":
                    noise = rng.uniform(-1.0, 1.0)
                    sweep = math.sin(2.0 * math.pi * (180.0 + 900.0 * local_t) * local_t)
                    sfx = (noise * 0.22 + sweep * 0.18) * env
                elif sfx_type == "bass_drop":
                    freq = 130.0 * math.exp(-local_t * 6.5) + 42.0
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.42 * env
                elif sfx_type == "rise":
                    freq = 260.0 + 1100.0 * local_t
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.24 * env
                else:  # crisp pop
                    freq = 520.0 + 420.0 * math.exp(-local_t * 25.0)
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.28 * env

            sample_val = max(-0.95, min(0.95, pad + sfx))
            pcm = int(sample_val * 32767)
            frames_bytes += struct.pack("<hh", pcm, pcm)

        wf.writeframes(bytes(frames_bytes))


# ==============================================================================
# 7. INSTAGRAM SAFE-ZONE COMPOSITOR (24 FPS x 10s = 240 FRAMES)
# ==============================================================================
def render_frames(
    script_data: Dict[str, Any],
    art_paths: List[Path],
    episode_num: int,
    frames_dir: Path,
) -> Path:
    frames_dir.mkdir(parents=True, exist_ok=True)
    beats = script_data["beats"]
    hook_l1 = (script_data.get("hook_line_1") or "THE DEFINITION OF").upper()
    hook_l2 = (script_data.get("hook_line_2_gold") or "'RELATABLE CHAOS':").upper()
    left_label = (script_data.get("left_label") or "").upper()
    right_label = (script_data.get("right_label") or "").upper()

    font_badge = load_font(34, bold=True)
    font_hook = load_font(56, bold=True)
    font_split = load_font(34, bold=True)
    font_sub = load_font(48, bold=True)
    font_wm = load_font(28, bold=False)

    loaded_arts = [Image.open(p).convert("RGB") for p in art_paths]
    frames_per_beat = TOTAL_FRAMES // 4
    cover_frame_path = frames_dir / "cover_frame.jpg"

    for f_idx in range(TOTAL_FRAMES):
        beat_idx = min(3, f_idx // frames_per_beat)
        local_f = f_idx % frames_per_beat
        progress = local_f / float(frames_per_beat)
        beat = beats[beat_idx]

        # Base dark cinema canvas (prevents Instagram UI clashes)
        canvas = Image.new("RGB", (WIDTH, HEIGHT), (10, 12, 18))
        draw = ImageDraw.Draw(canvas)

        # Subtle Ken Burns zoom + micro camera punch on beat cut
        zoom = 1.0 + 0.08 * progress + (0.04 * max(0.0, 1.0 - local_f / 6.0))
        base_art = loaded_arts[beat_idx]
        stage_size = 940
        scaled = int(stage_size * zoom)
        art_resized = base_art.resize((scaled, scaled), Image.Resampling.LANCZOS)
        crop_off = (scaled - stage_size) // 2
        art_cropped = art_resized.crop((crop_off, crop_off, crop_off + stage_size, crop_off + stage_size))

        # Rounded stage mask positioned in central Instagram safe zone (y = 390..1330)
        stage_x = (WIDTH - stage_size) // 2
        stage_y = 395
        mask = Image.new("L", (stage_size, stage_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, stage_size, stage_size), radius=44, fill=255)
        canvas.paste(art_cropped, (stage_x, stage_y), mask)

        # Crisp glowing stage border
        draw.rounded_rectangle(
            (stage_x - 3, stage_y - 3, stage_x + stage_size + 3, stage_y + stage_size + 3),
            radius=46,
            outline=(255, 212, 59) if beat_idx == 3 else (70, 82, 110),
            width=4,
        )

        # Episodic Grid Badge (Top-Left Safe Zone, y=135)
        badge_text = f"EP. {episode_num:02d}"
        b_box = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw = (b_box[2] - b_box[0]) + 34
        draw.rounded_rectangle((70, 130, 70 + bw, 186), radius=14, fill=(225, 29, 72))
        draw.text((87, 140), badge_text, font=font_badge, fill=(255, 255, 255))

        # 2-Line Permanent Top Hook Banner (y=215..355, white line 1 + gold line 2)
        l1_lines = wrap_text(draw, hook_l1, font_hook, WIDTH - 120)[:1]
        l2_lines = wrap_text(draw, hook_l2, font_hook, WIDTH - 120)[:1]
        if l1_lines:
            bb1 = draw.textbbox((0, 0), l1_lines[0], font=font_hook)
            w1 = bb1[2] - bb1[0]
            draw.text(((WIDTH - w1) // 2, 215), l1_lines[0], font=font_hook, fill=(255, 255, 255))
        if l2_lines:
            bb2 = draw.textbbox((0, 0), l2_lines[0], font=font_hook)
            w2 = bb2[2] - bb2[0]
            draw.text(((WIDTH - w2) // 2, 285), l2_lines[0], font=font_hook, fill=(255, 212, 59))

        # Optional Left vs. Right Comparison Pills (inside stage top)
        if left_label and right_label:
            draw.rounded_rectangle((stage_x + 28, stage_y + 24, stage_x + 430, stage_y + 84), radius=16, fill=(220, 38, 38))
            draw.text((stage_x + 48, stage_y + 36), left_label[:18], font=font_split, fill=(255, 255, 255))
            draw.rounded_rectangle((stage_x + stage_size - 430, stage_y + 24, stage_x + stage_size - 28, stage_y + 84), radius=16, fill=(22, 163, 74))
            draw.text((stage_x + stage_size - 410, stage_y + 36), right_label[:18], font=font_split, fill=(255, 255, 255))

        # Karaoke Active-Word Highlight Pill (y=1375, safely above IG caption & right icons)
        words = beat.get("caption", "").split()
        if words:
            active_word_idx = min(len(words) - 1, int(progress * len(words)))
            word_widths = []
            space_w = draw.textbbox((0, 0), " ", font=font_sub)[2]
            for w_str in words:
                wb = draw.textbbox((0, 0), w_str, font=font_sub)
                word_widths.append(wb[2] - wb[0])
            total_w = sum(word_widths) + space_w * (len(words) - 1)
            # Scale down dynamically if line is wide
            pill_w = min(WIDTH - 110, total_w + 68)
            pill_x = (WIDTH - pill_w) // 2
            pill_y = 1375
            draw.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + 88), radius=24, fill=(24, 27, 38), outline=(55, 65, 81), width=2)

            cur_x = (WIDTH - total_w) // 2
            for w_i, w_str in enumerate(words):
                color = (255, 179, 71) if w_i == active_word_idx else (248, 250, 252)
                draw.text((cur_x, pill_y + 18), w_str, font=font_sub, fill=color)
                cur_x += word_widths[w_i] + space_w

        # Subtle Progress Bar at y=1485
        overall_prog = (f_idx + 1) / float(TOTAL_FRAMES)
        draw.rounded_rectangle((140, 1488, WIDTH - 140, 1498), radius=5, fill=(38, 43, 58))
        draw.rounded_rectangle((140, 1488, 140 + int((WIDTH - 280) * overall_prog), 1498), radius=5, fill=(255, 212, 59))

        frame_file = frames_dir / f"frame_{f_idx:04d}.png"
        canvas.save(frame_file, "PNG")
        if f_idx == 12:
            canvas.save(cover_frame_path, "JPEG", quality=92)

    return cover_frame_path


# ==============================================================================
# 8. FFMPEG ENCODING & META GRAPH API REELS PUBLISHER
# ==============================================================================
def encode_mp4(frames_dir: Path, wav_path: Path, out_mp4: Path) -> None:
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "frame_%04d.png"),
        "-i", str(wav_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


def graph_api_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/v21.0/{endpoint}"
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def graph_api_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    url = f"https://graph.facebook.com/v21.0/{endpoint}?{qs}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def publish_to_instagram(video_url: str, cover_url: str, caption: str) -> Optional[str]:
    if not (IG_USER_ID and IG_ACCESS_TOKEN and GITHUB_PAGES_BASE_URL):
        print("[Publish] Missing IG_USER_ID, IG_ACCESS_TOKEN, or GITHUB_PAGES_BASE_URL; skipping IG upload.")
        return None

    container_payload: Dict[str, Any] = {
        "media_type": "REELS",
        "video_url": video_url,
        "cover_url": cover_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": IG_ACCESS_TOKEN,
    }
    if USE_TRIAL_REELS:
        container_payload["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})

    print(f"[Publish] Creating IG Reel container for {video_url}...")
    created = graph_api_post(f"{IG_USER_ID}/media", container_payload)
    creation_id = created.get("id")
    if not creation_id:
        raise RuntimeError(f"Failed to create IG container: {created}")

    # Poll until FINISHED
    for attempt in range(24):
        time.sleep(5)
        status_resp = graph_api_get(
            creation_id,
            {"fields": "status_code,status", "access_token": IG_ACCESS_TOKEN},
        )
        code = status_resp.get("status_code")
        print(f"[Publish] Poll {attempt + 1}: status_code={code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"IG media processing failed: {status_resp}")
    else:
        raise TimeoutError("Timed out waiting for IG media container to finish processing.")

    published = graph_api_post(
        f"{IG_USER_ID}/media_publish",
        {"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN},
    )
    media_id = published.get("id")
    print(f"[Publish] Published Reel successfully! Media ID: {media_id}")
    return media_id


# ==============================================================================
# 9. MAIN PIPELINE ENTRYPOINT
# ==============================================================================
def main() -> None:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    if genai is None:
        raise RuntimeError("google-genai package is not installed. Run: pip install google-genai pillow")

    client = genai.Client(api_key=GEMINI_API_KEY)
    history = load_history()
    episode_num = int(history.get("episode_count", 0)) + 1
    seed = int(datetime.now(timezone.utc).timestamp())

    # 1. Discover active models
    text_model, gemini_img_models, imagen_models = discover_models(client)

    # 2. Run 4-Source Autonomous Live Research
    research_brief = run_autonomous_research(client, text_model, history)

    # 3. Generate High-Retention 4-Beat Script
    script_data = generate_viral_script(client, text_model, research_brief, episode_num)
    print(f"[Script] Hook: {script_data.get('hook_line_1')} / {script_data.get('hook_line_2_gold')}")

    # 4. Generate 4 Beat Artworks (with automatic 3D fallback)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    art_paths = []
    used_generators = []
    for idx, beat in enumerate(script_data["beats"]):
        art_file = WORK_DIR / f"beat_{idx + 1}.png"
        gen_used = generate_beat_artwork(client, gemini_img_models, imagen_models, beat, art_file, seed)
        art_paths.append(art_file)
        used_generators.append(gen_used)
        print(f"[Art] Beat {idx + 1} rendered via {gen_used}")

    # 5. Synthesize Foley SFX + Ambient Audio
    wav_path = WORK_DIR / "audio.wav"
    synthesize_reel_audio(script_data["beats"], wav_path, seed)

    # 6. Render 240 Safe-Zone Frames + Cover Thumbnail
    frames_dir = WORK_DIR / "frames"
    cover_local = render_frames(script_data, art_paths, episode_num, frames_dir)

    # 7. Encode Final MP4 & Save to docs/reels/ for GitHub Pages
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    mp4_filename = f"ep{episode_num:03d}_{stamp}.mp4"
    jpg_filename = f"ep{episode_num:03d}_{stamp}.jpg"
    final_mp4 = MEDIA_DIR / mp4_filename
    final_jpg = MEDIA_DIR / jpg_filename

    encode_mp4(frames_dir, wav_path, final_mp4)
    shutil.copy2(cover_local, final_jpg)
    print(f"[Render] Saved {final_mp4} ({final_mp4.stat().st_size // 1024} KB)")

    # 8. Publish to Instagram Reels (if GitHub Pages URL & IG tokens are configured)
    ig_media_id = None
    if GITHUB_PAGES_BASE_URL:
        video_public_url = f"{GITHUB_PAGES_BASE_URL}/reels/{mp4_filename}"
        cover_public_url = f"{GITHUB_PAGES_BASE_URL}/reels/{jpg_filename}"
        ig_media_id = publish_to_instagram(
            video_public_url,
            cover_public_url,
            script_data.get("instagram_caption", ""),
        )

    # 9. Update Episodic History
    history["episode_count"] = episode_num
    history.setdefault("reels", []).append({
        "episode": episode_num,
        "timestamp_utc": stamp,
        "archetype": script_data.get("archetype"),
        "hook_line_1": script_data.get("hook_line_1"),
        "hook_line_2_gold": script_data.get("hook_line_2_gold"),
        "trend_inspiration": research_brief.get("trend_inspiration"),
        "generators": used_generators,
        "mp4": mp4_filename,
        "ig_media_id": ig_media_id,
    })
    save_history(history)
    print(f"[Done] Episode #{episode_num} complete!")


if __name__ == "__main__":
    main()
