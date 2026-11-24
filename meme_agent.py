import os
import io
import math
import json
import time
import wave
import base64
import random
import socket
import struct
import shutil
import asyncio
import pathlib
import textwrap
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920

# ==============================================================================
# CREATIVE DIRECTION & VISUAL TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.24,      # 0.0 to 0.50: cinematic edge depth
    "color_tint_strength": 0.11,    # 0.0 to 0.25: restrained tint preserving illustration colors
    "ambient_glow_strength": 0.16,  # 0.0 to 0.35: directional warm/cool atmospheric light
    "particle_opacity": 0.34,       # 0.0 to 0.70: subtle depth-layered atmosphere particles
    "max_zoom_delta": 0.10,         # Keeps character framing safe from over-cropping
    "transition_sec": 0.26,         # Duration of mood-driven transitions between acts
    "enable_blur_transition": True  # Lightweight downsampled blur-dissolve for sleepy/chill acts
}

MOOD_PALETTES = {
    "rock_hype": {
        "tint": (245, 105, 75),
        "glow": (255, 188, 82),
        "card_bg": (28, 16, 20),
        "card_fg": (255, 246, 238),
        "accent": (255, 122, 72),
        "particles": "sparks",
        "transition": "flash_impact",
        "scene_env": "indoor",
        "hashtags": ["#rockvibes", "#musicreels", "#maincharacterenergy", "#2danimation", "#relatable"],
        "prompt_light": "warm coral-red and golden amber spotlight glow, rich deep shadows, energetic concert-at-home lighting"
    },
    "dance_party": {
        "tint": (195, 92, 235),
        "glow": (110, 232, 255),
        "card_bg": (24, 15, 38),
        "card_fg": (248, 242, 255),
        "accent": (228, 118, 255),
        "particles": "confetti",
        "transition": "light_sweep",
        "scene_env": "indoor",
        "hashtags": ["#dancebreak", "#goodvibesonly", "#musicreels", "#animatedstory", "#sololife"],
        "prompt_light": "rich violet and magenta ambient glow with subtle cyan rim light, playful upbeat living-room energy"
    },
    "joy_celebrate": {
        "tint": (255, 208, 96),
        "glow": (255, 242, 175),
        "card_bg": (32, 25, 16),
        "card_fg": (255, 251, 238),
        "accent": (255, 212, 78),
        "particles": "confetti",
        "transition": "light_sweep",
        "scene_env": "indoor",
        "hashtags": ["#smallwins", "#goodmood", "#wholesomereels", "#2danimation", "#dailyjoy"],
        "prompt_light": "sunshine gold and warm cream daylight streaming into the room, crisp joyful highlights"
    },
    "sunrise_fresh": {
        "tint": (255, 178, 138),
        "glow": (255, 226, 172),
        "card_bg": (30, 22, 28),
        "card_fg": (255, 247, 242),
        "accent": (255, 186, 132),
        "particles": "dust",
        "transition": "light_sweep",
        "scene_env": "outdoor",
        "hashtags": ["#sunrisevibes", "#morningroutine", "#freshstart", "#animatedstory", "#peacefulmind"],
        "prompt_light": "soft peach, muted rose, and warm golden sunrise horizon gradient, crisp fresh morning air"
    },
    "sunset_golden": {
        "tint": (242, 132, 74),
        "glow": (255, 192, 108),
        "card_bg": (32, 19, 25),
        "card_fg": (255, 245, 236),
        "accent": (255, 156, 84),
        "particles": "dust",
        "transition": "light_sweep",
        "scene_env": "outdoor",
        "hashtags": ["#sunsetlovers", "#goldenhourglow", "#sunsetdrive", "#2danimation", "#chillvibes"],
        "prompt_light": "cinematic golden-hour amber, burnt orange sky, and muted twilight purple shadows"
    },
    "hike_nature": {
        "tint": (118, 192, 148),
        "glow": (232, 248, 204),
        "card_bg": (18, 32, 25),
        "card_fg": (242, 252, 245),
        "accent": (124, 222, 156),
        "particles": "dust",
        "transition": "dissolve",
        "scene_env": "outdoor",
        "hashtags": ["#hikingadventures", "#naturelover", "#getoutside", "#solohike", "#2danimation"],
        "prompt_light": "fresh forest greens, crisp sky blue, and dappled warm sunlight through trees"
    },
    "chill_vibe": {
        "tint": (114, 178, 188),
        "glow": (255, 220, 172),
        "card_bg": (19, 30, 35),
        "card_fg": (242, 250, 252),
        "accent": (132, 214, 218),
        "particles": "dust",
        "transition": "blur_dissolve",
        "scene_env": "indoor",
        "hashtags": ["#chillvibes", "#cozyvibes", "#introvertlife", "#webcomic", "#slowliving"],
        "prompt_light": "muted teal afternoon atmosphere balanced with gentle warm cream lamp light, relaxed calm mood"
    },
    "sleepy_dream": {
        "tint": (96, 112, 198),
        "glow": (172, 184, 255),
        "card_bg": (16, 20, 38),
        "card_fg": (236, 241, 255),
        "accent": (154, 168, 255),
        "particles": "dust",
        "transition": "blur_dissolve",
        "scene_env": "indoor",
        "hashtags": ["#latenightthoughts", "#sleepyvibes", "#3amthoughts", "#cozynight", "#2danimation"],
        "prompt_light": "deep indigo night tones, soft lavender moonlight, and calm drowsy blue shadows"
    },
    "work_stress": {
        "tint": (126, 146, 172),
        "glow": (180, 212, 240),
        "card_bg": (22, 28, 37),
        "card_fg": (240, 246, 252),
        "accent": (164, 202, 242),
        "particles": "none",
        "transition": "dissolve",
        "scene_env": "indoor",
        "hashtags": ["#workhumor", "#corporatememes", "#wfhlife", "#relatablehumor", "#webcomic"],
        "prompt_light": "muted slate blue and restrained neutral tones with cool laptop screen glow, deadpan atmosphere"
    },
    "panic_crimson": {
        "tint": (232, 78, 88),
        "glow": (255, 132, 98),
        "card_bg": (48, 16, 22),
        "card_fg": (255, 244, 244),
        "accent": (255, 96, 102),
        "particles": "sparks",
        "transition": "flash_impact",
        "scene_env": "indoor",
        "hashtags": ["#overthinking", "#panicmode", "#funnyreels", "#relatable", "#2danimation"],
        "prompt_light": "crimson and coral-red dramatic warm rim highlights, expressive comedic shock lighting"
    }
}

# Full-Spectrum Solo Story Themes (Hype, Dance, Hike, Sunrise, Sunset, Chill, Sleepy, Everyday Chaos)
STORY_THEMES = [
    "The Solo Kitchen Dance Break (putting headphones on while cooking and accidentally throwing a full concert in your socks)",
    "The Air-Guitar Rock Anthem Moment (when that one guitar solo hits in the car or bedroom and you forget all responsibilities)",
    "The 6:15 AM Sunrise Trail Hike (waking up early for a solo mountain hike, questioning your life halfway up, then seeing the view)",
    "The Golden-Hour Sunset Highway Drive (windows down, favorite playlist on, zero destination, pure main-character peace)",
    "The Friday Night Plan Dodge & Chill (thinking you have to go out, getting the 'let's reschedule' text, and celebrating in sweatpants)",
    "The 2:47 AM Sleepy Brain Spiral (trying to fall asleep in a cozy bed while your brain replays an awkward 4-second moment from 2017)",
    "The Payday Direct-Deposit Victory (seeing your balance jump at midnight after surviving all week on $14.82 and creativity)",
    "The 4:58 PM Weekend Freedom Sprint (closing 47 work tabs like disarming a bomb and instantly switching into weekend mode)",
    "The Rainy Sunday Afternoon Nap Saga (lying down for a 'quick 20-minute power nap' at 2:00 PM and waking up in another dimension)",
    "The Solo Coffee Shop & Park Walk (treating yourself to an iced coffee and a sunny park bench with zero rush)",
    "The Sibling No-Purpose Call Story (answering a dramatic call thinking it's urgent, only for them to ask what you ate)",
    "The Target One-Item Expedition (walking in for $4 toothpaste and walking out $94 later feeling weirdly accomplished)"
]

STORY_SETTINGS = [
    "scenic mountain hiking trail overlook at sunrise with pine trees and golden horizon clouds",
    "open coastal or desert highway at golden sunset seen from a parked car overlook",
    "sunny city park pathway lined with green trees and warm morning light",
    "cozy modern living room with warm floor lamp, speakers, and hardwood floor for dancing",
    "bright sunlit apartment kitchen counter with coffee mug and morning sunbeams",
    "cozy dark apartment bedroom with bedside lamp glow, soft pillows, and starry/rainy window",
    "driver's seat of a car at sunset with golden orange sky through the windshield",
    "minimalist home desk with glowing laptop screen transitioning into warm evening light"
]

SPECIFIC_ANCHORS = [
    "6:15 AM", "2:47 AM", "$14.82", "47 Chrome tabs", "4 hrs 11 mins",
    "100% volume", "3-mile summit", "golden hour", "4:58 PM", "1% battery",
    "$94.18 receipt", "2017 memory", "zero alarms", "7:02 AM", "20-min nap"
]

STORY_ARCS = [
    "Effort -> Pure Reward (starts tired or doubtful, ends with an unforgettable view or win)",
    "Sudden Hype Explosion (calm routine instantly turns into rock/dance celebration)",
    "False Alarm Relief (starts in comedic panic, resolves into pure chill bliss)",
    "Main-Character Golden Hour (quiet solo moment that feels like a movie ending)",
    "Deadpan Plot Twist (unexpected interruption turns into the best part of the day)"
]


def load_active_pages():
    cfg_path = pathlib.Path("pages.json")
    if cfg_path.exists():
        pages = json.loads(cfg_path.read_text(encoding="utf-8"))
        active = [p for p in pages if p.get("enabled")]
        if active:
            return active
    return [{
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "layout_mode": "v5_solo_story",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Full-spectrum relatable 3-act solo micro-stories: rock/dance hype moments, sunrise & sunset drives, outdoor hikes, pure chill, sleepy 3 AM thoughts, and everyday solo adventures (100% solo character, ZERO couples)",
        "art_style": "Clean vector-neat 2D webcomic storytelling illustration starring ONE solo minimalist white-headed character wearing a muted-olive baseball cap and dark charcoal hoodie, crisp uniform black ink outlines, rich expressive marker shading, detailed indoor or outdoor scenery, leave clean top and bottom space for story captions, strictly NO text or speech bubbles inside the drawing"
    }]


def fetch_live_trends():
    trends = []
    try:
        req = urllib.request.Request(
            "https://trends.google.com/trending/rss?geo=US",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item/title")[:10]:
                if item.text:
                    trends.append(item.text.strip())
    except Exception as e:
        print(f"Google Trends RSS skipped: {e}")

    if not trends:
        trends = [
            "Golden hour sunset drives with the windows down",
            "Weekend morning trail hikes and iced coffee",
            "Friday 4:58 PM logging off for the weekend"
        ]
    return "\n".join(f"- {t}" for t in trends)


def load_history(slug, limit=25):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            return items[-limit:]
        except Exception:
            return []
    return []


def save_history(slug, entry):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            items = []
    items.append(entry)
    hist_path.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


def sample_unique_story_seed(recent_history):
    used_combos = {h.get("combo_key", "") for h in recent_history}
    for _ in range(30):
        theme = random.choice(STORY_THEMES)
        setting = random.choice(STORY_SETTINGS)
        anchor = random.choice(SPECIFIC_ANCHORS)
        arc = random.choice(STORY_ARCS)
        combo_key = f"{theme[:24]}|{setting[:22]}|{anchor}|{arc[:18]}"
        if combo_key not in used_combos:
            return {
                "combo_key": combo_key,
                "theme": theme,
                "setting": setting,
                "anchor": anchor,
                "arc": arc
            }
    return {
        "combo_key": f"story_{int(time.time())}",
        "theme": random.choice(STORY_THEMES),
        "setting": random.choice(STORY_SETTINGS),
        "anchor": random.choice(SPECIFIC_ANCHORS),
        "arc": random.choice(STORY_ARCS)
    }


def build_mood_aware_caption(raw_caption, scenes):
    """Ensures every reel ships with 6-8 clean, non-duplicate, mood-matched trending hashtags."""
    base_text = (raw_caption or "").strip()
    lines = base_text.splitlines()
    text_body = []
    existing_tags = []

    for line in lines:
        words = line.split()
        if words and all(w.startswith("#") for w in words):
            existing_tags.extend(w.lower() for w in words)
        else:
            clean_words = []
            for w in words:
                if w.startswith("#"):
                    existing_tags.append(w.lower())
                else:
                    clean_words.append(w)
            if clean_words:
                text_body.append(" ".join(clean_words))

    mood_tags = []
    for sc in scenes[:3]:
        mood = sc.get("scene_mood", "chill_vibe")
        for tag in MOOD_PALETTES.get(mood, MOOD_PALETTES["chill_vibe"]).get("hashtags", []):
            if tag.lower() not in mood_tags:
                mood_tags.append(tag.lower())

    brand_tags = ["#wearechillclub", "#animatedreels", "#solodiary"]
    merged = []
    for tag in existing_tags + mood_tags + brand_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Just another day in the solo chapter."
    return f"{body_str}\n\n{' '.join(merged)}"


def ask_gemini_script(prompt):
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview"]
    last_err = "Unknown error"

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.92,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json"
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(req_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(raw_text, strict=False)
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 3:
                        print(f"Generated Full-Spectrum Story script with {model}")
                        return parsed
                    last_err = f"{model} returned incomplete JSON keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}"
                    print(last_err)
            except json.JSONDecodeError as e:
                last_err = f"{model} JSONDecodeError: {e}"
                print(last_err)
                time.sleep(1)
                continue
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:350]
                last_err = f"{model} HTTP {e.code}: {body}"
                print(last_err)
                if e.code in (400, 404):
                    break
                if e.code in (429, 500, 503):
                    time.sleep(3 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} Network/Timeout: {e}"
                print(last_err)
                time.sleep(2)
                continue
    raise RuntimeError(f"All Gemini models failed to produce valid JSON. Last error: {last_err}")


def _render_illustrated_scene_fallback(scene_mood, act_idx, out_png_path):
    """Rich 2D webcomic indoor OR outdoor fallback matching all 10 moods & preserving exact character identity."""
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["chill_vibe"])
    is_outdoor = palette.get("scene_env") == "outdoor"

    env_colors = {
        "rock_hype": {"bg": (54, 22, 28), "ground": (34, 14, 18), "win": (95, 36, 42), "sun": (255, 195, 85)},
        "dance_party": {"bg": (46, 22, 66), "ground": (28, 14, 42), "win": (85, 42, 125), "sun": (125, 235, 255)},
        "joy_celebrate": {"bg": (72, 58, 34), "ground": (48, 38, 22), "win": (135, 185, 230), "sun": (255, 225, 110)},
        "sunrise_fresh": {"bg": (235, 155, 125), "ground": (52, 68, 56), "win": (255, 210, 155), "sun": (255, 238, 180)},
        "sunset_golden": {"bg": (215, 110, 68), "ground": (44, 34, 42), "win": (255, 175, 95), "sun": (255, 215, 130)},
        "hike_nature": {"bg": (118, 182, 225), "ground": (56, 98, 64), "win": (165, 215, 245), "sun": (255, 240, 175)},
        "chill_vibe": {"bg": (34, 54, 62), "ground": (24, 38, 44), "win": (68, 112, 128), "sun": (255, 215, 155)},
        "sleepy_dream": {"bg": (22, 28, 52), "ground": (15, 19, 36), "win": (36, 48, 88), "sun": (175, 190, 255)},
        "work_stress": {"bg": (34, 42, 54), "ground": (24, 30, 40), "win": (52, 64, 82), "sun": (175, 210, 245)},
        "panic_crimson": {"bg": (64, 20, 28), "ground": (42, 14, 18), "win": (90, 32, 40), "sun": (255, 120, 105)}
    }
    ec = env_colors.get(scene_mood, env_colors["chill_vibe"])
    img = Image.new("RGB", (W, H), color=ec["bg"])
    draw = ImageDraw.Draw(img)

    if is_outdoor:
        draw.ellipse([W // 2 - 190, 560, W // 2 + 190, 940], fill=ec["sun"])
        draw.polygon([(0, 1180), (280, 790), (620, 1180)], fill=(42, 62, 54), outline=(16, 20, 24))
        draw.polygon([(380, 1180), (790, 740), (W, 1180)], fill=(34, 52, 46), outline=(16, 20, 24))
        draw.rectangle([0, 1160, W, H], fill=ec["ground"])
        draw.line([(0, 1160), (W, 1160)], fill=(14, 16, 20), width=8)
        for tx, ty in [(140, 1060), (920, 1040)]:
            draw.polygon([(tx, ty - 170), (tx - 65, ty + 40), (tx + 65, ty + 40)], fill=(28, 58, 42), outline=(14, 16, 20))
            draw.rectangle([tx - 12, ty + 40, tx + 12, ty + 100], fill=(48, 34, 24))
    else:
        draw.rectangle([0, 1180, W, H], fill=ec["ground"])
        draw.line([(0, 1180), (W, 1180)], fill=(14, 14, 18), width=8)
        wx0, wy0, wx1, wy1 = 110, 440, 430, 860
        draw.rounded_rectangle([wx0, wy0, wx1, wy1], radius=16, fill=ec["win"], outline=(16, 18, 24), width=10)
        draw.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=(16, 18, 24), width=8)
        draw.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=(16, 18, 24), width=8)
        draw.rectangle([720, 990, 950, 1185], fill=(48, 36, 30), outline=(14, 14, 18), width=8)
        draw.rectangle([827, 870, 843, 990], fill=(30, 30, 36), outline=(14, 14, 18), width=5)
        draw.polygon([(775, 875), (895, 875), (870, 795), (800, 795)], fill=ec["sun"], outline=(14, 14, 18), width=7)

    cx = 540 + (act_idx - 1) * 20
    cy = 930
    is_hype = scene_mood in ("rock_hype", "dance_party", "joy_celebrate")

    draw.rounded_rectangle([cx - 96, cy + 75, cx + 96, cy + 360], radius=46, fill=(44, 48, 60), outline=(14, 14, 18), width=10)
    if is_hype:
        draw.line([(cx - 90, cy + 125), (cx - 175, cy + 15)], fill=(44, 48, 60), width=26)
        draw.line([(cx + 90, cy + 125), (cx + 175, cy + 15)], fill=(44, 48, 60), width=26)
    draw.ellipse([cx - 110, cy - 140, cx + 110, cy + 80], fill=(252, 252, 255), outline=(14, 14, 18), width=11)
    draw.pieslice([cx - 112, cy - 160, cx + 112, cy - 25], start=180, end=360, fill=(92, 112, 78), outline=(14, 14, 18), width=9)
    draw.rounded_rectangle([cx - 8, cy - 102, cx + 150, cy - 78], radius=10, fill=(92, 112, 78), outline=(14, 14, 18), width=7)

    if scene_mood == "sleepy_dream":
        draw.line([(cx - 52, cy - 26), (cx - 22, cy - 26)], fill=(14, 14, 18), width=7)
        draw.line([(cx + 22, cy - 26), (cx + 52, cy - 26)], fill=(14, 14, 18), width=7)
        draw.ellipse([cx - 12, cy + 12, cx + 12, cy + 32], outline=(14, 14, 18), width=6)
    elif is_hype or scene_mood in ("sunrise_fresh", "sunset_golden", "hike_nature", "chill_vibe"):
        draw.arc([cx - 50, cy - 42, cx - 20, cy - 14], start=180, end=360, fill=(14, 14, 18), width=7)
        draw.arc([cx + 20, cy - 42, cx + 50, cy - 14], start=180, end=360, fill=(14, 14, 18), width=7)
        draw.arc([cx - 32, cy - 2, cx + 32, cy + 36], start=10, end=170, fill=(14, 14, 18), width=7)
    else:
        draw.ellipse([cx - 50, cy - 42, cx - 22, cy - 14], fill=(14, 14, 18))
        draw.ellipse([cx + 22, cy - 42, cx + 50, cy - 14], fill=(14, 14, 18))
        draw.line([(cx - 24, cy + 22), (cx + 24, cy + 22)], fill=(14, 14, 18), width=7)

    img.save(out_png_path, format="PNG")


def generate_scene_illustration(visual_prompt, art_style, scene_mood, act_idx, out_png_path):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["chill_vibe"])
    lighting_note = palette["prompt_light"]
    full_prompt = (
        f"{art_style}. Act {act_idx + 1} Story Scene: {visual_prompt}. Lighting & Mood: {lighting_note}. "
        "Character must strictly keep a minimalist white round head, muted-olive baseball cap, dark charcoal hoodie, "
        "and crisp black outlines. Vertical 9:16 portrait composition, keep the character centered in the middle frame "
        "with clean unobstructed space in the top 20% and bottom 28% for story captions, strictly NO text, NO letters, NO speech bubbles."
    )

    for imagen_model in ["imagen-3.0-generate-002", "imagen-4.0-generate-001", "imagen-4.0-fast-generate-001"]:
        try:
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){imagen_model}:predict?key={GEMINI_API_KEY}"
            payload = {
                "instances": [{"prompt": full_prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                res = json.loads(resp.read().decode())
                b64 = res["predictions"][0]["bytesBase64Encoded"]
                img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                img.save(out_png_path, format="PNG")
                print(f"Generated Story artwork via {imagen_model} (Act {act_idx + 1}, {scene_mood})")
                return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:200]
            print(f"{imagen_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{imagen_model} skipped ({e})")

    for img_model in ["gemini-2.5-flash-image", "gemini-3.1-flash-image-preview", "gemini-3.8-flash-image"]:
        try:
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){img_model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                res = json.loads(resp.read().decode())
                for part in res["candidates"][0]["content"]["parts"]:
                    if "inlineData" in part:
                        b64 = part["inlineData"]["data"]
                        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                        img.save(out_png_path, format="PNG")
                        print(f"Generated Story artwork via {img_model} (Act {act_idx + 1}, {scene_mood})")
                        return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:200]
            print(f"{img_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    print(f"Using illustrated scene fallback for Act {act_idx + 1} ({scene_mood})")
    _render_illustrated_scene_fallback(scene_mood, act_idx, out_png_path)


async def _stream_lyria_wav(music_prompt, bpm, out_wav, duration_sec):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})
    target_bytes = int(48000 * 2 * 2 * (duration_sec + 1.5))
    pcm_buffer = bytearray()

    async with client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(prompts=[types.WeightedPrompt(text=music_prompt, weight=1.0)])
        await session.set_music_generation_config(config=types.LiveMusicGenerationConfig(bpm=int(bpm), temperature=1.05))
        await session.play()

        deadline = time.time() + 28
        async for message in session.receive():
            if message.server_content and message.server_content.audio_chunks:
                for chunk in message.server_content.audio_chunks:
                    if chunk.data:
                        pcm_buffer.extend(chunk.data)
            if len(pcm_buffer) >= target_bytes or time.time() >= deadline:
                break
        await session.stop()

    if len(pcm_buffer) < int(48000 * 2 * 2 * 4):
        raise RuntimeError("Insufficient Lyria bytes")

    raw_wav = pathlib.Path(str(out_wav) + ".raw.wav")
    with wave.open(str(raw_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(pcm_buffer)

    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(raw_wav),
        "-t", f"{duration_sec:.3f}",
        "-af", f"volume=0.88,afade=t=in:st=0:d=0.35,afade=t=out:st={max(0.5, duration_sec - 0.9):.3f}:d=0.9",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria storytelling score ({bpm} BPM)")


def build_story_audio_with_sfx(music_prompt, bpm, sfx_style, act_starts, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating synth bed...")
        sr = 48000
        total_samples = int(sr * duration_sec)
        chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
        bar_len = int(sr * 2.5)
        with wave.open(str(bed_wav), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            frames = bytearray()
            for i in range(total_samples):
                t = i / sr
                chord = chords[(i // bar_len) % len(chords)]
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.09
                s = int(max(-0.9, min(0.9, val)) * 32767)
                frames.extend(struct.pack("<hh", s, s))
            wf.writeframes(frames)

    sfx_wav = final_wav.parent / "micro_sfx.wav"
    sr = 48000
    total_samples = int(sr * duration_sec)
    t_act2 = act_starts[1]
    t_act3 = act_starts[2]

    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sr
            sig = 0.0
            if t_act2 <= t <= t_act2 + 0.22:
                dt = t - t_act2
                env = math.exp(-dt * 18.0)
                sig += math.sin(2 * math.pi * 880.0 * dt) * env * 0.25
            if t_act3 <= t <= t_act3 + 0.55:
                dt = t - t_act3
                env = math.exp(-dt * 7.5)
                if sfx_style == "heartbeat_drop":
                    freq = 68.0 - 20.0 * dt
                elif sfx_style == "alert_ding":
                    freq = 1046.5
                else:
                    freq = 420.0 * math.exp(-dt * 4.5)
                sig += math.sin(2 * math.pi * freq * dt) * env * 0.38
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            frames.extend(struct.pack("<hh", s, s))
        wf.writeframes(frames)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# CINEMATIC GRADING, EASING, TRANSITIONS & DEPTH PARTICLE ENGINE
# ==============================================================================
def _ease_out_cubic(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 3)


def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def build_vignette_mask(strength=0.24):
    small_w, small_h = 270, 480
    vig = Image.new("L", (small_w, small_h), 0)
    px = vig.load()
    cx, cy = small_w / 2.0, small_h * 0.50
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_d
            val = int(max(0.0, min(255.0, (d ** 2.3) * 255.0 * strength)))
            px[x, y] = val
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def build_ambient_glow_mask(strength=0.16):
    """Precomputed upper-corner soft radial light falloff for natural cinematic depth."""
    small_w, small_h = 270, 480
    mask = Image.new("L", (small_w, small_h), 0)
    px = mask.load()
    lx, ly = small_w * 0.72, small_h * 0.24
    max_d = math.hypot(small_w, small_h) * 0.78
    for y in range(small_h):
        for x in range(small_w):
            d = min(1.0, math.hypot(x - lx, y - ly) / max_d)
            val = int(max(0.0, min(255.0, pow(1.0 - d, 2.0) * 255.0 * strength)))
            px[x, y] = val
    return mask.resize((W, H), Image.Resampling.BILINEAR)


def generate_particle_seeds(count=30):
    rng = random.Random(42)
    palette_colors = [(255, 215, 90), (235, 120, 255), (120, 235, 255), (135, 235, 165)]
    return [
        {
            "x": rng.uniform(0.03, 0.97),
            "y": rng.uniform(0.04, 0.96),
            "depth": rng.uniform(0.45, 1.0),
            "speed": rng.uniform(0.65, 1.35),
            "size": rng.randint(2, 5),
            "phase": rng.uniform(0, math.pi * 2),
            "col": rng.choice(palette_colors)
        }
        for _ in range(count)
    ]


def apply_atmosphere_grade(frame, scene_mood, t, vignette_mask, glow_mask, particle_seeds):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["chill_vibe"])

    # 1. Restrained mood tint + subtle directional ambient light glow
    tint_strength = VISUAL_TUNING["color_tint_strength"]
    if scene_mood in ("panic_crimson", "rock_hype", "dance_party"):
        tint_strength += 0.025 * math.sin(t * 11.0)
    tint_layer = Image.new("RGB", (W, H), palette["tint"])
    graded = Image.blend(frame, tint_layer, max(0.0, min(0.24, tint_strength)))

    if VISUAL_TUNING["ambient_glow_strength"] > 0:
        glow_layer = Image.new("RGB", (W, H), palette["glow"])
        graded = Image.composite(glow_layer, graded, glow_mask)

    graded = ImageEnhance.Contrast(graded).enhance(1.05)
    graded = ImageEnhance.Color(graded).enhance(1.04)

    # 2. Cinematic radial vignette
    dark_layer = Image.new("RGB", (W, H), (10, 12, 18))
    graded = Image.composite(dark_layer, graded, vignette_mask)

    # 3. Depth-layered organic particles (only when appropriate for the mood)
    p_type = palette.get("particles", "none")
    if p_type != "none" and VISUAL_TUNING["particle_opacity"] > 0:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        base_alpha = 255 * VISUAL_TUNING["particle_opacity"]
        glow_col = palette["glow"]

        for p in particle_seeds:
            depth = p["depth"]
            spd = p["speed"] * (0.6 + 0.5 * depth)
            twinkle = 0.72 + 0.28 * math.sin(t * 3.2 + p["phase"])
            p_alpha = int(base_alpha * (0.4 + 0.6 * depth) * twinkle)

            if p_type == "dust":
                px = int(((p["x"] + math.sin(t * 1.2 + p["phase"]) * 0.022 * depth) % 1.0) * W)
                py = int(((p["y"] - t * 0.035 * spd) % 1.0) * H)
                r = max(2, int(p["size"] * (0.7 + 0.5 * depth)))
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.58)))
            elif p_type == "sparks":
                px = int(((p["x"] + math.sin(t * 5.2 + p["phase"]) * 0.038 * depth) % 1.0) * W)
                py = int(((p["y"] - t * 0.24 * spd) % 1.0) * H)
                r = max(2, int((p["size"] + 1) * (0.7 + 0.5 * depth)))
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.76)))
            elif p_type == "confetti":
                px = int(((p["x"] + math.sin(t * 2.2 + p["phase"]) * 0.035 * depth) % 1.0) * W)
                py = int(((p["y"] + t * 0.14 * spd) % 1.0) * H)
                r = max(3, int((p["size"] + 2) * (0.7 + 0.5 * depth)))
                c = p["col"]
                odraw.rounded_rectangle([px - r, py - r // 2, px + r, py + r // 2], radius=2, fill=(c[0], c[1], c[2], int(p_alpha * 0.78)))

        graded = Image.alpha_composite(graded.convert("RGBA"), overlay).convert("RGB")

    return graded


def apply_scene_transition(prev_frame, curr_frame, mood, tr_p):
    """Story-driven transition styles matched to the incoming scene mood."""
    palette = MOOD_PALETTES.get(mood, MOOD_PALETTES["chill_vibe"])
    style = palette.get("transition", "dissolve")
    eased = _ease_out_cubic(tr_p)

    if style == "flash_impact":
        # Crisp warm flash beat for rock hype or panic spike
        blended = Image.blend(prev_frame, curr_frame, min(1.0, eased * 1.35))
        flash_alpha = (1.0 - tr_p) * 0.30
        flash_img = Image.new("RGB", (W, H), palette["glow"])
        return Image.blend(blended, flash_img, flash_alpha)

    if style == "light_sweep":
        # Smooth cross-dissolve paired with a soft golden/cyan light bloom
        blended = Image.blend(prev_frame, curr_frame, eased)
        sweep_alpha = math.sin(tr_p * math.pi) * 0.18
        sweep_img = Image.new("RGB", (W, H), palette["glow"])
        return Image.blend(blended, sweep_img, sweep_alpha)

    if style == "blur_dissolve" and VISUAL_TUNING.get("enable_blur_transition", True):
        # Fast downsampled Gaussian blur cross-dissolve for sleepy/chill acts
        blur_amount = math.sin(tr_p * math.pi) * 4.5
        blended = Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))
        if blur_amount > 0.3:
            tiny = blended.resize((W // 4, H // 4), Image.Resampling.BILINEAR)
            tiny = tiny.filter(ImageFilter.GaussianBlur(radius=blur_amount))
            return tiny.resize((W, H), Image.Resampling.BILINEAR)
        return blended

    return Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))


def compute_camera_box(motion, mood, local_p, scene_t, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    # Sleepy & chill moods breathe slower; hype moods feel crisper
    breath_rate = 1.6 if mood in ("sleepy_dream", "chill_vibe") else 2.4
    idle_breath = math.sin(t * breath_rate) * 0.0035

    if motion == "zoom_out":
        eased = _ease_out_quart(local_p)
        zoom = (1.0 + max_z) - (max_z * eased) + idle_breath
    elif motion == "punch_zoom":
        # Snappy 0.28s punch-in with smooth hold settle
        if local_p < 0.10:
            zoom = 1.0 + (max_z * 1.15) * _ease_out_quart(local_p / 0.10)
        else:
            zoom = (1.0 + max_z * 1.15) - (max_z * 0.28 * _ease_in_out_sine((local_p - 0.10) / 0.90))
    elif motion == "deadpan_freeze":
        zoom = 1.025 + (idle_breath * 0.25)
    else:
        eased = _ease_in_out_sine(local_p)
        zoom = 1.0 + (max_z * eased) + idle_breath

    zoom = max(1.015, zoom)
    crop_w = int(W / zoom)
    crop_h = int(H / zoom)
    max_dx = W - crop_w
    max_dy = H - crop_h

    if motion == "pan_right":
        eased_pan = _ease_in_out_sine(local_p)
        x0 = int(max_dx * eased_pan)
        y0 = max_dy // 2
    elif motion == "shake_impact":
        if scene_t <= 0.38:
            decay = math.exp(-scene_t * 8.5)
            shake_x = int(math.sin(scene_t * 54.0) * min(16, max_dx // 2) * decay)
            shake_y = int(math.cos(scene_t * 46.0) * min(16, max_dy // 2) * decay)
        else:
            shake_x, shake_y = 0, 0
        x0 = max(0, min(max_dx, (max_dx // 2) + shake_x))
        y0 = max(0, min(max_dy, (max_dy // 2) + shake_y))
    else:
        # Subtle organic camera drift so static zooms feel alive
        drift_x = int(math.sin(t * 0.9) * min(6, max_dx // 3))
        drift_y = int(math.cos(t * 0.7) * min(5, max_dy // 3))
        x0 = max(0, min(max_dx, (max_dx // 2) + drift_x))
        y0 = max(0, min(max_dy, (max_dy // 2) + drift_y))

    return (x0, y0, x0 + crop_w, y0 + crop_h)


def _load_font(size):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_story_overlays(frame, chapter_tag, story_caption, emotion_cue, scene_mood, act_idx, scene_t, act_dur, t, handle):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["chill_vibe"])
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    acc = palette["accent"]

    # 1. Top Chapter / Timestamp Pill with subtle glass border
    if chapter_tag:
        ent = _ease_out_quart(min(1.0, t / 0.30))
        tag_font = _load_font(33)
        tag_str = f"ACT {act_idx + 1}/3  ·  {chapter_tag.strip().upper()}"
        bbox = odraw.textbbox((0, 0), tag_str, font=tag_font)
        tw = (bbox[2] - bbox[0]) + 60
        th = 62
        bx0 = (W - tw) // 2
        by0 = 185 + int((1.0 - ent) * -16)
        alpha = int(244 * ent)
        odraw.rounded_rectangle([bx0 + 3, by0 + 5, bx0 + tw + 3, by0 + th + 5], radius=31, fill=(6, 8, 12, int(alpha * 0.45)))
        odraw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + th], radius=31, fill=(16, 19, 27, alpha), outline=(acc[0], acc[1], acc[2], int(alpha * 0.9)), width=3)
        odraw.text((W // 2, by0 + th // 2), tag_str, font=tag_font, fill=(acc[0], acc[1], acc[2], 255), anchor="mm")

    # 2. Expressive Emotion Cue Tag above Character (smooth entrance + gentle fade out)
    if emotion_cue and scene_t <= 1.75:
        pop_p = min(1.0, scene_t / 0.14)
        fade_out = 1.0 if scene_t < 1.35 else max(0.0, 1.0 - (scene_t - 1.35) / 0.40)
        cue_scale = 1.16 - (0.16 * _ease_out_quart(pop_p))
        cue_alpha = int(255 * min(1.0, scene_t / 0.08) * fade_out)
        cue_font = _load_font(int(52 * cue_scale))
        odraw.text(
            (W // 2, 326),
            emotion_cue.strip().upper(),
            font=cue_font,
            fill=(acc[0], acc[1], acc[2], cue_alpha),
            anchor="mm",
            stroke_width=8,
            stroke_fill=(12, 12, 16, cue_alpha)
        )

    # 3. Lower-Third Story Narration Subtitle Card with Entrance & Exit Easing
    if story_caption:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.22))
        time_left = max(0.0, act_dur - scene_t)
        cap_out = 1.0 if (act_idx == 2 or time_left > 0.18) else max(0.0, time_left / 0.18)
        vis = cap_in * cap_out
        cap_alpha = int(248 * vis)
        slide_y = int((1.0 - cap_in) * 14)
        cap_font = _load_font(40)
        wrapped = textwrap.fill(story_caption.strip(), width=34)
        lines = wrapped.split("\n")
        box_h = 50 + len(lines) * 52
        x0, y0 = 66, 1335 + slide_y
        x1, y1 = W - 66, y0 + box_h

        c_bg = palette["card_bg"]
        c_fg = palette["card_fg"]
        odraw.rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 10], radius=26, fill=(6, 8, 12, int(cap_alpha * 0.55)))
        odraw.rounded_rectangle([x0, y0, x1, y1], radius=26, fill=(c_bg[0], c_bg[1], c_bg[2], cap_alpha), outline=(acc[0], acc[1], acc[2], int(cap_alpha * 0.85)), width=3)
        odraw.rounded_rectangle([x0 + 14, y0 + 20, x0 + 22, y1 - 20], radius=4, fill=(acc[0], acc[1], acc[2], cap_alpha))
        odraw.multiline_text((W // 2 + 8, (y0 + y1) // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=11)

    # 4. Clean Handle Watermark
    handle_font = _load_font(28)
    odraw.text((W // 2, 1625), handle, font=handle_font, fill=(255, 255, 255, 222), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 210))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_story_reel(page_cfg, script_data, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:3]
    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        mood = sc.get("scene_mood") or "chill_vibe"
        if mood not in MOOD_PALETTES:
            mood = "chill_vibe"
        sc["scene_mood"] = mood

        generate_scene_illustration(
            sc["visual_prompt"],
            page_cfg["art_style"],
            mood,
            idx,
            art_path
        )
        scene_imgs.append(Image.open(art_path).convert("RGB"))

    act_durations = [3.5, 4.0, 3.5]
    act_starts = [0.0, 3.5, 7.5]
    total_dur = sum(act_durations)

    final_wav = tmp_dir / "final_story.wav"
    build_story_audio_with_sfx(
        script_data.get("music_prompt", "upbeat indie guitar and warm lo-fi storytelling beat instrumental"),
        script_data.get("music_bpm", 108),
        script_data.get("sfx_style", "alert_ding"),
        act_starts,
        total_dur,
        final_wav
    )

    total_frames = int(total_dur * FPS)
    chapter_tag = script_data.get("chapter_tag", "SOLO DIARY")
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
    particle_seeds = generate_particle_seeds(30)
    prev_rendered_frame = None

    for f_idx in range(total_frames):
        t = f_idx / FPS
        if t < act_starts[1]:
            s_idx = 0
        elif t < act_starts[2]:
            s_idx = 1
        else:
            s_idx = 2

        sc = scenes[s_idx]
        act_dur = act_durations[s_idx]
        scene_t = t - act_starts[s_idx]
        local_p = min(1.0, max(0.0, scene_t / act_dur))
        base_img = scene_imgs[s_idx]
        motion = sc.get("camera_motion", "zoom_in")
        mood = sc["scene_mood"]

        crop_box = compute_camera_box(motion, mood, local_p, scene_t, t)
        frame = base_img.crop(crop_box).resize((W, H), Image.Resampling.BILINEAR)
        frame = apply_atmosphere_grade(frame, mood, t, vignette_mask, glow_mask, particle_seeds)

        trans_dur = VISUAL_TUNING["transition_sec"]
        if s_idx > 0 and scene_t < trans_dur and prev_rendered_frame is not None:
            tr_p = scene_t / trans_dur
            frame = apply_scene_transition(prev_rendered_frame, frame, mood, tr_p)
        else:
            prev_rendered_frame = frame.copy()

        # Polished Top Progress Bar with glowing tip
        draw = ImageDraw.Draw(frame)
        prog = min(1.0, (f_idx + 1) / max(1, total_frames))
        bar_col = MOOD_PALETTES[mood]["accent"]
        glow_tip = MOOD_PALETTES[mood]["glow"]
        bar_x = int(W * prog)
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=bar_col)
        if bar_x > 8:
            draw.rectangle([max(0, bar_x - 18), 0, bar_x, 8], fill=glow_tip)

        frame = draw_story_overlays(
            frame=frame,
            chapter_tag=chapter_tag,
            story_caption=sc.get("story_caption", ""),
            emotion_cue=sc.get("emotion_cue", ""),
            scene_mood=mood,
            act_idx=s_idx,
            scene_t=scene_t,
            act_dur=act_dur,
            t=t,
            handle=page_cfg["handle"]
        )

        frame.save(tmp_dir / f"frame_{f_idx:04d}.png", format="PNG")

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(tmp_dir / "frame_%04d.png"),
        "-i", str(final_wav),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_mp4)
    ], check=True)
    shutil.rmtree(tmp_dir)
    print(f"Rendered Full-Spectrum Storytelling Reel: {out_mp4}")


def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish Story Reel {rel_path}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push"], check=True)

    owner, repo = REPO_NAME.split("/", 1)
    pages_url = f"https://{owner.lower()}.github.io/{repo}/{rel_path}"

    for attempt in range(1, 15):
        time.sleep(5)
        try:
            req = urllib.request.Request(pages_url, headers={"User-Agent": "facebookexternalhit/1.1"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and ("video/" in ctype or "octet-stream" in ctype):
                    print(f"Verified live GitHub Pages MP4 ({ctype}): {pages_url}")
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages deploy ({attempt}/15): {e}")

    raise RuntimeError(f"GitHub Pages did not serve MP4 in time: {pages_url}")


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meta API {e.code} on {url}: {err_body}") from e


def publish_to_instagram(ig_id, token, video_url, caption):
    if not token or not ig_id:
        return
    host = "graph.facebook.com"
    base = "https://" + host + "/" + GRAPH_VERSION + "/" + ig_id

    container = post_request(base + "/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token
    })
    creation_id = container["id"]
    print(f"Created IG Reel container: {creation_id}")

    for attempt in range(1, 20):
        time.sleep(5)
        status_url = "https://" + host + "/" + GRAPH_VERSION + "/" + creation_id + "?fields=status_code,status&access_token=" + token
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel status ({attempt}/20): {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram Reel failed: {status_data}")

    published = post_request(base + "/media_publish", {
        "creation_id": creation_id,
        "access_token": token
    })
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {published['id']}")


def publish_to_facebook_reels(fb_page_id, token, video_url, description):
    if not token or not fb_page_id:
        return
    host = "graph.facebook.com"
    base = "https://" + host + "/" + GRAPH_VERSION + "/" + fb_page_id + "/video_reels"

    start = post_request(base, {
        "upload_phase": "start",
        "access_token": token
    })
    video_id = start["video_id"]

    rupload_url = "[https://rupload.facebook.com/video-upload/](https://rupload.facebook.com/video-upload/)" + GRAPH_VERSION + "/" + video_id
    req = urllib.request.Request(
        rupload_url,
        method="POST",
        headers={
            "Authorization": f"OAuth {token}",
            "file_url": video_url
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("Uploaded MP4 to Facebook Reels:", resp.read().decode())

    finish = post_request(base, {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": description,
        "access_token": token
    })
    print(f"LIVE ON FACEBOOK REELS ({fb_page_id})! Response: {finish}")


if __name__ == "__main__":
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    hour = now_est.hour

    if 5 <= hour < 12:
        time_slot_vibe = "MORNING STORY (9 AM): Sunrise hikes, fresh morning coffee, waking up, or starting the day with energy."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON STORY (2 PM): Kitchen dance breaks, afternoon chill walks, payday wins, or workday plot twists."
    else:
        time_slot_vibe = "EVENING/NIGHT STORY (9 PM+): Golden-hour sunset drives, bedroom rock concerts, sleepy vibes, or late-night thoughts."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('story_hook', '')}" for h in recent_history if h.get("story_hook")) or "None yet"
        seed = sample_unique_story_seed(recent_history)

        prompt = (
            f"You are a versatile webcomic storyteller and visual director for {page['handle']}.\n"
            f"CHANNEL PERSONALITY: {page['domain']}\n"
            f"CHARACTER & ART STYLE: {page['art_style']}\n\n"
            "### MANDATORY STORY SEED (WRITE A CONNECTED 3-ACT MICRO-STORY AROUND THIS)\n"
            f"- Story Premise: {seed['theme']}\n"
            f"- Consistent Setting Across All 3 Acts: {seed['setting']}\n"
            f"- Specific Anchor Detail: {seed['anchor']}\n"
            f"- Story Arc Direction: {seed['arc']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only weave in if natural): \n{trends}\n"
            f"- Previously Told Stories (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### STORYTELLING RULES\n"
            "1. Write a cohesive, relatable 3-act narrative (Beginning -> Turn/Complication -> Resolution) in first-person ('I' / 'my'). It does NOT have to be cozy—lean fully into the seed's energy whether it's rock/dance hype, sunrise/sunset adventure, mountain hiking, pure chill, sleepy tiredness, or joyful celebration!\n"
            "2. Keep the EXACT SAME setting and the same solo character (white round head, muted-olive baseball cap, dark charcoal hoodie) across all 3 scenes for visual continuity. STRICTLY SOLO (no romantic partners).\n"
            "3. 'story_caption' in each scene must be natural, expressive storytelling (14-20 words per act) that flows seamlessly from Act 1 to Act 2 to Act 3.\n"
            "4. 'emotion_cue' is a punchy 1-2 word reaction above the character ('LET'S GO!', 'SO CLOSE.', 'PURE MAGIC.', 'SLEEPY.', 'VIBE.').\n"
            "5. Match 'music_prompt' and 'music_bpm' to the story's true energy (e.g., 128 BPM upbeat rock/dance groove for hype stories, 92 BPM acoustic/lo-fi for sunset/sleepy stories).\n"
            "6. In 'ig_caption', write a relatable 1-sentence hook followed by 4-5 trending niche hashtags matching the exact mood and activity of this story.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "chapter_tag": "SUNSET · 6:45 PM",\n'
            '  "music_prompt": "Uplifting indie rock guitar and drums feel-good driving beat instrumental",\n'
            '  "music_bpm": 122,\n'
            '  "sfx_style": "alert_ding",\n'
            '  "scenes": [\n'
            '    {"story_caption": "Act 1 setup line establishing the scene and expectation (14-20 words)", "emotion_cue": "READY.", "visual_prompt": "Act 1 illustration in the consistent setting showing the character starting out, NO text in drawing", "camera_motion": "zoom_in", "scene_mood": "hike_nature"},\n'
            '    {"story_caption": "Act 2 turn/complication line where effort, a song drop, or a twist happens (14-20 words)", "emotion_cue": "WAIT...", "visual_prompt": "Act 2 illustration in the SAME setting showing the turning point and character action, NO text in drawing", "camera_motion": "punch_zoom", "scene_mood": "rock_hype"},\n'
            '    {"story_caption": "Act 3 satisfying payoff ending the story on a memorable note (14-20 words)", "emotion_cue": "PURE MAGIC.", "visual_prompt": "Act 3 illustration in the SAME setting showing the final joyful, hype, or chill payoff, NO text in drawing", "camera_motion": "zoom_out", "scene_mood": "sunset_golden"}\n'
            "  ],\n"
            '  "ig_caption": "Short relatable story caption + 5 mood-matched hashtags",\n'
            '  "pinned_comment": "Engaging question asking followers about their favorite vibe or similar moment"\n'
            "}\n"
            "Allowed values for scene_mood: 'rock_hype', 'dance_party', 'joy_celebrate', 'sunrise_fresh', 'sunset_golden', 'hike_nature', 'chill_vibe', 'sleepy_dream', 'work_stress', or 'panic_crimson'.\n"
            "Allowed values for camera_motion: 'zoom_in', 'zoom_out', 'pan_right', 'punch_zoom', 'deadpan_freeze', or 'shake_impact'.\n"
            "Allowed values for sfx_style: 'heartbeat_drop', 'alert_ding', or 'record_scratch'."
        )

        script_data = ask_gemini_script(prompt)
        final_caption = build_mood_aware_caption(script_data.get("ig_caption", ""), script_data["scenes"])

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"

        render_story_reel(page, script_data, rel_mp4)
        act1_line = script_data["scenes"][0].get("story_caption", "")
        full_story_text = "\n".join(f"Act {i+1}: {s.get('story_caption', '')}" for i, s in enumerate(script_data["scenes"][:3]))
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"{script_data.get('chapter_tag', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "story_hook": act1_line,
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
