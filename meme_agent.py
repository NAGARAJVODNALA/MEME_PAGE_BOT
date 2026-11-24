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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops, ImageOps

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920

# ==============================================================================
# CREATIVE DIRECTOR & HUMAN-PACING TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.22,      # Subtle cinematic depth without darkening faces
    "color_tint_strength": 0.12,    # Natural mood color wash
    "ambient_glow_strength": 0.15,  # Warm/cool environmental rim light
    "particle_opacity": 0.32,       # Gentle atmospheric depth
    "max_zoom_delta": 0.08,         # Gentle breathing camera movement (never disorienting)
    "transition_sec": 0.24,         # Crisp, clean transition window
    "enable_blur_transition": True,
    "min_beat_sec": 3.4,            # Minimum time per illustration so viewer absorbs art + text
    "max_beat_sec": 5.2,            # Prevents dragging while giving plenty of reading time
    "words_per_sec": 2.6            # Comfortable human reading speed
}

# ==============================================================================
# 1. HUMANIZED 4-CHARACTER ROSTER WITH MOOD-BASED FULL-BODY WARDROBES
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Charismatic Instigator (confident smirk, effortless charm, talks everyone into spontaneous plans)",
        "face_and_hair": "Phil (expressive 2D animated young man, stylized white round-head character with expressive eyebrows, confident smirk, short dark-brown hair peeking under a muted-olive baseball cap)",
        "fallback": {"cap": (92, 112, 78), "hair": (58, 44, 36), "beard": False, "glasses": False}
    },
    "Alan": {
        "archetype": "The Lovable Wildcard (deadpan sincerity, philosophical at 2 AM, unexpectedly loyal & weird)",
        "face_and_hair": "Alan (expressive 2D animated young man, stylized white round-head character with fluffy brown beard, messy wavy brown hair, wide earnest deadpan eyes)",
        "fallback": {"cap": None, "hair": (78, 54, 38), "beard": True, "glasses": False}
    },
    "Stu": {
        "archetype": "The Relatable Overthinker (checks bank balance twice, over-prepares for everything, deeply relatable)",
        "face_and_hair": "Stu (expressive 2D animated young man, stylized white round-head character with neat side-parted brown hair, thick black-rimmed glasses, expressive nervous-yet-kind eyes)",
        "fallback": {"cap": None, "hair": (64, 48, 38), "beard": False, "glasses": True}
    },
    "Doug": {
        "archetype": "The Grounded Best Friend (calm voice of reason, effortlessly cool, always shows up at the right moment)",
        "face_and_hair": "Doug (expressive 2D animated young man, stylized white round-head character with clean cropped hair, relaxed half-lidded chill smile, warm approachable expression)",
        "fallback": {"cap": None, "hair": (52, 42, 36), "beard": False, "glasses": False}
    }
}

WARDROBE_MOODS = {
    "casual_hangout": {
        "label": "Everyday Street & Apartment Casual",
        "outfits": {
            "Phil": "wearing an open charcoal zip-up hoodie over a white crew-neck t-shirt, slim dark-wash jeans, and clean white sneakers",
            "Alan": "wearing a faded vintage graphic t-shirt, brown crossbody satchel strap, relaxed beige cargo shorts, and retro sneakers",
            "Stu": "wearing a neat navy knit cardigan over a light-blue button-down shirt, khaki chinos, and brown leather loafers",
            "Doug": "wearing an unbuttoned red-and-black plaid flannel shirt over a heather-gray tee, dark jeans, and casual boots"
        },
        "fallback_colors": {
            "Phil": ((46, 50, 62), (42, 54, 76)),
            "Alan": ((132, 92, 64), (168, 152, 126)),
            "Stu": ((48, 68, 102), (176, 162, 136)),
            "Doug": ((142, 58, 58), (44, 48, 58))
        }
    },
    "sharp_night_out": {
        "label": "Celebration & Sharp Suits / Night Out",
        "outfits": {
            "Phil": "wearing a tailored charcoal blazer over a crisp black t-shirt, tailored trousers, and dress shoes (no cap for formal look, sunglasses in pocket)",
            "Alan": "wearing a slightly rumpled tan linen suit jacket over an open-collar patterned shirt, matching suit pants, and sneakers",
            "Stu": "wearing a sharp fitted navy suit with a neatly knotted tie, white dress shirt, dress pants, and polished oxford shoes",
            "Doug": "wearing a sleek black bomber jacket over a crisp white button-up shirt, dark tailored pants, and Chelsea boots"
        },
        "fallback_colors": {
            "Phil": ((42, 44, 52), (36, 38, 46)),
            "Alan": ((166, 146, 118), (156, 136, 108)),
            "Stu": ((34, 48, 78), (30, 42, 68)),
            "Doug": ((28, 30, 36), (32, 34, 40))
        }
    },
    "cozy_late_night": {
        "label": "Late-Night Cozy Loungewear & Hoodies",
        "outfits": {
            "Phil": "wearing a relaxed olive crewneck sweatshirt, gray joggers, and cozy socks",
            "Alan": "wearing an oversized tie-dye sleep t-shirt, plaid flannel pajama pants, and fuzzy slides",
            "Stu": "wearing a neat heather-gray pullover hoodie, navy sweatpants, and house slippers",
            "Doug": "wearing a soft terracotta waffle-knit long-sleeve shirt, black athletic shorts, and slides"
        },
        "fallback_colors": {
            "Phil": ((86, 104, 74), (112, 116, 124)),
            "Alan": ((124, 96, 148), (138, 64, 64)),
            "Stu": ((118, 124, 134), (42, 54, 78)),
            "Doug": ((168, 92, 68), (38, 40, 46))
        }
    },
    "road_trip_outdoor": {
        "label": "Road Trip, Trail & Golden Hour Adventure",
        "outfits": {
            "Phil": "wearing a lightweight denim jacket over a striped tee, olive utility shorts, and trail sneakers",
            "Alan": "wearing a bright retro windbreaker jacket, athletic shorts, high crew socks, and running shoes",
            "Stu": "wearing a breathable quarter-zip fleece pullover, hiking pants, and sturdy trail shoes",
            "Doug": "wearing a sleeveless quilted vest over a long-sleeve Henley shirt, relaxed jeans, and boots"
        },
        "fallback_colors": {
            "Phil": ((74, 104, 138), (94, 108, 82)),
            "Alan": ((214, 136, 64), (54, 64, 82)),
            "Stu": ((66, 112, 118), (128, 118, 102)),
            "Doug": ((78, 88, 74), (48, 56, 74))
        }
    }
}

CAST_MODES = {
    "solo_pov": {
        "desc": "1 main character in an immersive 'literally me' personal moment",
        "lineups": [["Stu"], ["Alan"], ["Phil"], ["Doug"]]
    },
    "classic_duo": {
        "desc": "2 contrasting best friends bouncing off each other",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Alan", "Stu"],
            ["Phil", "Alan"],
            ["Stu", "Doug"]
        ]
    },
    "trio_hangout": {
        "desc": "3 friends caught in an everyday adventure or group-chat decision",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_crew_4": {
        "desc": "All 4 friends (Phil, Alan, Stu, and Doug) together for a celebration, trip, or big moment",
        "lineups": [["Phil", "Alan", "Stu", "Doug"]]
    }
}

# ==============================================================================
# 2. RELATABLE HUMAN MOMENTS & STORY-MOTIVATED ART STYLES
# ==============================================================================
ART_STYLES = {
    "warm_webcomic": {
        "prompt": "Warm, expressive 2D webcomic character illustration with clean ink outlines, soft painterly indoor/outdoor lighting, rich lived-in background details, cozy human atmosphere",
        "overlay_fx": "none",
        "hashtags": ["#webcomic", "#2danimation", "#relatable"]
    },
    "cinematic_lofi": {
        "prompt": "Atmospheric lo-fi 2D animated film style, warm golden lamp light or twilight sky, detailed lived-in room or car interior, expressive character body language",
        "overlay_fx": "none",
        "hashtags": ["#lofivibes", "#indieanimation", "#nightvibes"]
    },
    "manga_reaction": {
        "prompt": "Expressive anime-inspired 2D comedy illustration, crisp linework, dynamic comedic reaction faces, vibrant color palette",
        "overlay_fx": "speed_lines",
        "hashtags": ["#animememes", "#2danimation", "#funnyreels"]
    },
    "retro_90s_toon": {
        "prompt": "Warm 1990s/2000s Saturday-morning animated sitcom 2D illustration style, nostalgic color palette, expressive full-body poses",
        "overlay_fx": "vhs",
        "hashtags": ["#nostalgia", "#cartoonstyle", "#throwbackvibes"]
    },
    "comic_pop": {
        "prompt": "Crisp modern graphic novel 2D illustration, bold clean linework, rich colors, expressive full-body acting and clear silhouettes",
        "overlay_fx": "none",
        "hashtags": ["#comicart", "#storytelling", "#relatablereels"]
    },
    "sketchbook_warm": {
        "prompt": "Charming hand-drawn ink and watercolor wash 2D animation style on warm cream paper, expressive natural gestures",
        "overlay_fx": "paper_grain",
        "hashtags": ["#handdrawnanimation", "#sketchbook", "#sliceoflife"]
    }
}

HUMAN_RELATABLE_MOMENTS = [
    "Sitting in your parked car for 12 minutes in complete silence after getting home just to decompress",
    "Checking your banking app with one eye half-closed before tapping your card for coffee",
    "The group chat taking 47 messages to pick a restaurant and ending up at the exact same place as always",
    "Saying 'I'm going to bed early tonight' at 10:30 PM and suddenly deep-diving into random life thoughts at 2:15 AM",
    "Walking into the store for one single item and walking out holding four snacks and zero of the thing you came for",
    "That unbeatable golden-hour drive with the windows down when your favorite song comes on at the exact right second",
    "Dressing up sharp with the crew for a regular Friday dinner like you're walking a red carpet",
    "Hearing a 4:58 PM Friday work notification when your brain already clocked out at 3:15 PM",
    "Celebrating a tiny everyday win (like finding front-row parking or finishing a tough week) like a championship trophy",
    "Waking up on Saturday morning in full panic thinking you slept through work, then realizing it's the weekend",
    "Your friend saying 'trust me, I know a shortcut' while your phone battery hits 4%",
    "Morning-after mystery piecing together last night's funny receipts while the calm friend brings everyone iced coffee"
]

SUBTLE_POP_FLAVORS = [
    "None — pure authentic everyday human moment (focus 100% on relatable emotion and friendship)",
    "None — pure authentic everyday human moment (focus 100% on relatable emotion and friendship)",
    "None — pure authentic everyday human moment (focus 100% on relatable emotion and friendship)",
    "None — pure authentic everyday human moment (focus 100% on relatable emotion and friendship)",
    "None — pure authentic everyday human moment (focus 100% on relatable emotion and friendship)",
    "Subtle The Office style deadpan glance toward the viewer during an awkward moment",
    "Subtle Hangover-style morning-after detective energy piecing together a funny night out",
    "Subtle Interstellar dramatic slow-motion seriousness over a completely trivial everyday task"
]

# ==============================================================================
# 3. COLOR GRADES, CAMERA MOVES & TRANSITIONS
# ==============================================================================
COLOR_GRADES = {
    "golden_hour": {
        "tint": (245, 152, 82), "glow": (255, 206, 118), "contrast": 1.05, "sat": 1.10,
        "card_bg": (26, 18, 20), "card_fg": (255, 248, 240), "accent": (255, 174, 92)
    },
    "warm_lamp_night": {
        "tint": (225, 148, 86), "glow": (255, 198, 124), "contrast": 1.06, "sat": 1.08,
        "card_bg": (24, 18, 22), "card_fg": (255, 246, 236), "accent": (255, 184, 102)
    },
    "neon_cyber": {
        "tint": (165, 84, 235), "glow": (95, 232, 255), "contrast": 1.10, "sat": 1.20,
        "card_bg": (16, 14, 34), "card_fg": (244, 248, 255), "accent": (110, 236, 255)
    },
    "crimson_panic": {
        "tint": (228, 72, 82), "glow": (255, 132, 98), "contrast": 1.08, "sat": 1.14,
        "card_bg": (44, 14, 18), "card_fg": (255, 244, 244), "accent": (255, 98, 104)
    },
    "cold_cyan_night": {
        "tint": (84, 142, 208), "glow": (145, 214, 255), "contrast": 1.06, "sat": 1.02,
        "card_bg": (14, 22, 38), "card_fg": (238, 246, 255), "accent": (132, 212, 255)
    },
    "vintage_vhs": {
        "tint": (212, 174, 136), "glow": (255, 214, 166), "contrast": 0.97, "sat": 0.88,
        "card_bg": (30, 24, 22), "card_fg": (252, 245, 234), "accent": (255, 192, 118)
    },
    "comic_vibrant": {
        "tint": (248, 194, 78), "glow": (118, 208, 255), "contrast": 1.10, "sat": 1.18,
        "card_bg": (20, 20, 32), "card_fg": (255, 252, 242), "accent": (255, 214, 72)
    },
    "pastel_soft": {
        "tint": (238, 194, 212), "glow": (255, 232, 210), "contrast": 0.99, "sat": 0.96,
        "card_bg": (30, 24, 34), "card_fg": (255, 248, 252), "accent": (255, 192, 214)
    },
    "desaturated_gloom": {
        "tint": (118, 128, 142), "glow": (175, 188, 205), "contrast": 1.04, "sat": 0.52,
        "card_bg": (20, 22, 28), "card_fg": (236, 240, 246), "accent": (168, 186, 212)
    },
    "warm_sunrise": {
        "tint": (252, 178, 134), "glow": (255, 228, 168), "contrast": 1.04, "sat": 1.08,
        "card_bg": (30, 22, 26), "card_fg": (255, 248, 242), "accent": (255, 188, 128)
    },
    "forest_fresh": {
        "tint": (108, 192, 142), "glow": (222, 248, 196), "contrast": 1.05, "sat": 1.10,
        "card_bg": (16, 30, 24), "card_fg": (242, 252, 245), "accent": (122, 226, 154)
    }
}

ALL_TRANSITIONS = [
    "hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right",
    "blur_dissolve", "light_sweep", "freeze_record_scratch"
]

ALL_CAMERA_MOVES = [
    "dolly_push_in", "pull_back_reveal", "snap_zoom_face",
    "locked_deadpan", "crane_tilt_up", "pan_follow_left",
    "pan_follow_right", "gentle_float"
]

ALL_CAPTION_STYLES = [
    "modern_card", "karaoke_pop", "comic_callout", "cinematic_minimal"
]

ALL_ENV_EFFECTS = [
    "none", "rain", "snow", "sparks", "confetti", "dust", "screen_glow"
]

ALL_SFX_CUES = [
    "whoosh", "record_scratch", "vine_boom_sub", "pop_ding", "riser_hit"
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
        "layout_mode": "v7_human_immersive",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Relatable 2D animated slice-of-life & friendship storytelling starring Phil, Alan, Stu, and Doug — real-feeling characters in lived-in settings, everyday POV moments, road trips, late-night talks, and small wins that make viewers say 'that is literally me'",
        "art_style": "Expressive 2D animated character storytelling with consistent faces, full-body mood-matched outfits, and warm lived-in environments"
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
            for item in root.findall(".//item/title")[:8]:
                if item.text:
                    trends.append(item.text.strip())
    except Exception as e:
        print(f"Google Trends RSS skipped: {e}")

    if not trends:
        trends = [
            "Sitting in the parked car after work to decompress",
            "Group chat plans taking 50 messages",
            "Golden hour sunset drive with favorite music"
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


def sample_creative_director_seed(recent_history):
    """Selects a fresh, human-relatable combination of cast, wardrobe mood, art style, and everyday moment."""
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_styles = [h.get("art_style_key", "") for h in recent_history[-3:]]
    recent_casts = [h.get("cast_mode", "") for h in recent_history[-2:]]
    recent_moods = [h.get("wardrobe_mood", "") for h in recent_history[-2:]]
    recent_scenarios = [h.get("scenario_tag", "") for h in recent_history[-6:]]

    for _ in range(45):
        cast_mode = random.choice(list(CAST_MODES.keys()))
        if cast_mode in recent_casts and random.random() < 0.70:
            continue
        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        art_style_key = random.choice(list(ART_STYLES.keys()))
        if art_style_key in recent_styles and random.random() < 0.75:
            continue
        wardrobe_mood = random.choice(list(WARDROBE_MOODS.keys()))
        if wardrobe_mood in recent_moods and random.random() < 0.65:
            continue
        scenario = random.choice(HUMAN_RELATABLE_MOMENTS)
        if scenario[:28] in recent_scenarios and random.random() < 0.85:
            continue
        pop_flavor = random.choice(SUBTLE_POP_FLAVORS)
        caption_style = random.choice(ALL_CAPTION_STYLES)
        combo_key = f"{cast_mode}|{'+'.join(characters)}|{wardrobe_mood}|{art_style_key}|{scenario[:24]}"
        if combo_key not in used_keys:
            return {
                "combo_key": combo_key,
                "cast_mode": cast_mode,
                "characters": characters,
                "wardrobe_mood": wardrobe_mood,
                "art_style_key": art_style_key,
                "scenario": scenario,
                "pop_flavor": pop_flavor,
                "caption_style": caption_style
            }

    cast_mode = random.choice(list(CAST_MODES.keys()))
    return {
        "combo_key": f"hr_{int(time.time())}",
        "cast_mode": cast_mode,
        "characters": random.choice(CAST_MODES[cast_mode]["lineups"]),
        "wardrobe_mood": random.choice(list(WARDROBE_MOODS.keys())),
        "art_style_key": random.choice(list(ART_STYLES.keys())),
        "scenario": random.choice(HUMAN_RELATABLE_MOMENTS),
        "pop_flavor": random.choice(SUBTLE_POP_FLAVORS),
        "caption_style": random.choice(ALL_CAPTION_STYLES)
    }


def compute_beat_durations(scenes):
    """Calculates natural human reading & visual absorption time per scene (never rushed)."""
    durations = []
    for idx, sc in enumerate(scenes):
        words = len((sc.get("story_caption") or "").split())
        read_sec = words / VISUAL_TUNING["words_per_sec"]
        cushion = 1.65 if idx == len(scenes) - 1 else 1.45
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], read_sec + cushion)), 2)
        durations.append(dur)
    return durations


def validate_and_fix_plan(script_data, seed):
    """Pre-render Quality Control Gate: enforces 4 visual beats, readable short captions, and locked wardrobe consistency."""
    if not isinstance(script_data, dict):
        return _build_local_fallback_script(seed)

    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return _build_local_fallback_script(seed)

    scenes = scenes[:4]
    used_cams = set()
    used_trans = set()

    if seed.get("wardrobe_mood") not in WARDROBE_MOODS:
        seed["wardrobe_mood"] = "casual_hangout"

    setting_lock = (script_data.get("setting_continuity") or "Cozy lived-in apartment living room with warm evening lighting").strip()
    script_data["setting_continuity"] = setting_lock

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "warm_lamp_night" if idx in (0, 3) else "comic_vibrant"
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]
        if sc.get("art_style_key") not in ART_STYLES:
            sc["art_style_key"] = seed["art_style_key"]
        if sc.get("env_effect") not in ALL_ENV_EFFECTS:
            sc["env_effect"] = "none"
        if sc.get("sfx_cue") not in ALL_SFX_CUES:
            sc["sfx_cue"] = "pop_ding" if idx in (0, 2) else "vine_boom_sub"

        cam = sc.get("camera_move")
        if cam not in ALL_CAMERA_MOVES or cam in used_cams:
            avail_cams = [c for c in ALL_CAMERA_MOVES if c not in used_cams]
            cam = random.choice(avail_cams) if avail_cams else "gentle_float"
        sc["camera_move"] = cam
        used_cams.add(cam)

        tr = sc.get("transition_in")
        if tr not in ALL_TRANSITIONS or tr in used_trans:
            avail_tr = [t for t in ALL_TRANSITIONS if t not in used_trans]
            tr = random.choice(avail_tr) if avail_tr else "hard_cut"
        sc["transition_in"] = tr
        used_trans.add(tr)

        cap = (sc.get("story_caption") or "").strip()
        words = cap.split()
        if len(words) > 14:
            sc["story_caption"] = " ".join(words[:13]) + "..."
        elif not cap:
            sc["story_caption"] = f"When {', '.join(seed['characters'])} realize what just happened."

    if script_data.get("caption_style") not in ALL_CAPTION_STYLES:
        script_data["caption_style"] = seed["caption_style"]

    script_data["scenes"] = scenes
    return script_data


def build_smart_hashtags(raw_caption, script_data, seed):
    base_text = (raw_caption or "").strip()
    text_body = []
    existing_tags = []

    for line in base_text.splitlines():
        clean_words = []
        for w in line.split():
            if w.startswith("#"):
                existing_tags.append(w.lower())
            else:
                clean_words.append(w)
        if clean_words:
            text_body.append(" ".join(clean_words))

    dynamic_tags = []
    style_key = script_data.get("scenes", [{}])[0].get("art_style_key", seed["art_style_key"])
    dynamic_tags.extend(ART_STYLES.get(style_key, ART_STYLES["warm_webcomic"]).get("hashtags", []))

    chars = seed.get("characters", [])
    if len(chars) >= 3:
        dynamic_tags.extend(["#friendgroup", "#theboys", "#relatablemoments"])
    elif len(chars) == 2:
        dynamic_tags.extend(["#bestfriends", "#duolife"])
    else:
        dynamic_tags.extend(["#literallyme", "#povlife"])

    dynamic_tags.extend(["#wearechillclub", "#sliceoflife", "#animatedreels"])

    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Tell me you have done this at least once."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    chars = seed["characters"]
    char_str = " and ".join(chars) if len(chars) <= 2 else ", ".join(chars[:-1]) + f", and {chars[-1]}"
    style_key = seed["art_style_key"]

    return {
        "chapter_tag": "POV · 11:48 PM",
        "caption_style": seed["caption_style"],
        "setting_continuity": "Warm dimly lit living room at night with a glowing lamp, couch, and coffee table",
        "music_prompt": "Warm lo-fi indie guitar and soft Rhodes chords with relaxed chill beat instrumental",
        "music_bpm": 96,
        "scenes": [
            {
                "story_caption": "POV: You tell yourself you are going to sleep early tonight.",
                "emotion_cue": "10:30 PM",
                "visual_prompt": f"Full-body view of {char_str} sitting comfortably on the couch winding down with a warm mug, relaxed smile, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_lamp_night",
                "end_grade": "warm_lamp_night",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "dust",
                "sfx_cue": "pop_ding"
            },
            {
                "story_caption": "One quick check of your phone turns into a whole life debate.",
                "emotion_cue": "1:15 AM",
                "visual_prompt": f"Full-body view of {char_str} leaning forward animatedly discussing a phone screen together in warm lamp light, expressive hand gestures, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_lamp_night",
                "end_grade": "cold_cyan_night",
                "camera_move": "pan_follow_right",
                "transition_in": "blur_dissolve",
                "env_effect": "screen_glow",
                "sfx_cue": "whoosh"
            },
            {
                "story_caption": "Suddenly it is 2:40 AM and nobody remembers what started it.",
                "emotion_cue": "2:40 AM",
                "visual_prompt": f"Full-body reaction of {char_str} looking wide-eyed at the wall clock in shock while still wide awake, comedic posture, NO text",
                "art_style_key": style_key,
                "start_grade": "cold_cyan_night",
                "end_grade": "crimson_panic",
                "camera_move": "snap_zoom_face",
                "transition_in": "whip_pan_left",
                "env_effect": "none",
                "sfx_cue": "record_scratch"
            },
            {
                "story_caption": "We immediately agree to fix our sleep schedule starting tomorrow.",
                "emotion_cue": "TOMORROW FOR SURE.",
                "visual_prompt": f"Full-body ending pose of {char_str} giving a calm deadpan thumbs-up while slumping back into the couch cushions, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_lamp_night",
                "end_grade": "golden_hour",
                "camera_move": "pull_back_reveal",
                "transition_in": "light_sweep",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": "Every single night starts with 'I am going to bed at 11' and ends like this.",
        "pinned_comment": "Be honest: what time did you actually fall asleep last night?"
    }


def ask_gemini_script(prompt, seed):
    models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite"
    ]
    last_err = "Unknown error"

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.90,
                    "maxOutputTokens": 2600,
                    "responseMimeType": "application/json"
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(req_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(raw_text, strict=False)
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 4:
                        print(f"Generated Human-Immersive script with {model}")
                        return validate_and_fix_plan(parsed, seed)
                    last_err = f"{model} returned incomplete JSON"
                    print(last_err)
            except json.JSONDecodeError as e:
                last_err = f"{model} JSONDecodeError: {e}"
                print(last_err)
                time.sleep(1)
                continue
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
                last_err = f"{model} HTTP {e.code}: {body}"
                print(last_err)
                if e.code in (400, 404, 429):
                    break
                if e.code in (500, 503):
                    time.sleep(4 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} Network/Timeout: {e}"
                print(last_err)
                time.sleep(2)
                continue

    print(f"All Gemini text endpoints busy ({last_err}); using local human-immersive script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. CONSISTENT CHARACTER & FULL-OUTFIT ILLUSTRATION ENGINE (4 BEATS)
# ==============================================================================
def _render_multi_character_fallback(characters, wardrobe_mood, start_grade, beat_idx, out_png_path):
    """Full-body fallback renderer with consistent faces + mood-matched shirts/jackets/pants/shorts/shoes."""
    g = COLOR_GRADES.get(start_grade, COLOR_GRADES["warm_lamp_night"])
    mood_cfg = WARDROBE_MOODS.get(wardrobe_mood, WARDROBE_MOODS["casual_hangout"])
    bg = tuple(max(22, min(220, int(c * 0.42))) for c in g["tint"])
    floor = tuple(max(16, int(c * 0.62)) for c in bg)
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    draw.ellipse([W // 2 - 260, 400, W // 2 + 260, 920], fill=g["glow"])
    draw.rectangle([0, 1240, W, H], fill=floor)
    draw.line([(0, 1240), (W, 1240)], fill=(14, 14, 18), width=7)

    count = max(1, min(4, len(characters)))
    spacing = min(235, (W - 170) // count)
    start_x = (W // 2) - ((count - 1) * spacing) // 2
    scale = 1.0 if count <= 2 else (0.86 if count == 3 else 0.76)

    for idx, name in enumerate(characters[:4]):
        ident = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])["fallback"]
        top_col, bottom_col = mood_cfg["fallback_colors"].get(name, ((60, 70, 90), (40, 44, 54)))
        cx = start_x + idx * spacing
        cy = 830 + (idx % 2) * 14
        r_head = int(84 * scale)
        body_w = int(76 * scale)
        torso_h = int(195 * scale)
        leg_h = int(165 * scale)

        leg_top = cy + r_head + torso_h - 14
        leg_w = int(28 * scale)
        leg_gap = int(22 * scale)
        for side in (-1, 1):
            lx0 = cx + side * leg_gap - leg_w // 2
            lx1 = lx0 + leg_w
            draw.rounded_rectangle([lx0, leg_top, lx1, leg_top + leg_h], radius=12, fill=bottom_col, outline=(12, 12, 16), width=6)
            draw.rounded_rectangle([lx0 - 6, leg_top + leg_h - 14, lx1 + 12, leg_top + leg_h + 14], radius=10, fill=(242, 244, 248), outline=(12, 12, 16), width=5)

        draw.rounded_rectangle(
            [cx - body_w, cy + r_head - 10, cx + body_w, cy + r_head + torso_h],
            radius=int(32 * scale),
            fill=top_col,
            outline=(12, 12, 16),
            width=max(6, int(8 * scale))
        )
        draw.polygon(
            [(cx - int(22 * scale), cy + r_head - 8), (cx + int(22 * scale), cy + r_head - 8), (cx, cy + r_head + int(52 * scale))],
            fill=(242, 244, 248)
        )

        arm_y = cy + r_head + int(26 * scale)
        if beat_idx in (1, 2):
            draw.line([(cx - body_w + 6, arm_y), (cx - body_w - int(48 * scale), arm_y - int(42 * scale))], fill=top_col, width=max(14, int(20 * scale)))
            draw.line([(cx + body_w - 6, arm_y), (cx + body_w + int(48 * scale), arm_y - int(42 * scale))], fill=top_col, width=max(14, int(20 * scale)))
        else:
            draw.line([(cx - body_w + 6, arm_y), (cx - body_w - int(24 * scale), arm_y + int(95 * scale))], fill=top_col, width=max(14, int(20 * scale)))
            draw.line([(cx + body_w - 6, arm_y), (cx + body_w + int(24 * scale), arm_y + int(95 * scale))], fill=top_col, width=max(14, int(20 * scale)))

        draw.ellipse(
            [cx - r_head, cy - r_head, cx + r_head, cy + r_head],
            fill=(252, 252, 255),
            outline=(12, 12, 16),
            width=max(6, int(9 * scale))
        )

        if ident["cap"] and wardrobe_mood != "sharp_night_out":
            draw.pieslice([cx - r_head - 2, cy - r_head - 12, cx + r_head + 2, cy - 8], start=180, end=360, fill=ident["cap"], outline=(12, 12, 16), width=6)
            draw.rounded_rectangle([cx - 6, cy - int(r_head * 0.54), cx + int(r_head * 1.28), cy - int(r_head * 0.34)], radius=8, fill=ident["cap"], outline=(12, 12, 16), width=5)
        else:
            draw.arc([cx - int(r_head * 0.78), cy - r_head - 4, cx + int(r_head * 0.78), cy - int(r_head * 0.2)], start=195, end=345, fill=ident["hair"], width=max(8, int(12 * scale)))

        if ident["beard"]:
            draw.pieslice([cx - int(r_head * 0.84), cy - 2, cx + int(r_head * 0.84), cy + r_head + 4], start=0, end=180, fill=(84, 58, 40), outline=(12, 12, 16), width=5)

        eye_dx = int(30 * scale)
        eye_y = cy - int(14 * scale)
        eye_r = max(6, int((11 if beat_idx == 2 else 9) * scale))
        draw.ellipse([cx - eye_dx - eye_r, eye_y - eye_r, cx - eye_dx + eye_r, eye_y + eye_r], fill=(12, 12, 16))
        draw.ellipse([cx + eye_dx - eye_r, eye_y - eye_r, cx + eye_dx + eye_r, eye_y + eye_r], fill=(12, 12, 16))

        if ident["glasses"]:
            gr = int(21 * scale)
            draw.rectangle([cx - eye_dx - gr, eye_y - gr, cx - eye_dx + gr, eye_y + gr], outline=(12, 12, 16), width=max(4, int(5 * scale)))
            draw.rectangle([cx + eye_dx - gr, eye_y - gr, cx + eye_dx + gr, eye_y + gr], outline=(12, 12, 16), width=max(4, int(5 * scale)))
            draw.line([(cx - eye_dx + gr, eye_y), (cx + eye_dx - gr, eye_y)], fill=(12, 12, 16), width=max(4, int(5 * scale)))

        my = cy + int(26 * scale)
        if beat_idx in (0, 3):
            draw.arc([cx - int(20 * scale), my - 8, cx + int(20 * scale), my + 14], start=10, end=170, fill=(12, 12, 16), width=5)
        elif beat_idx == 2:
            draw.ellipse([cx - int(13 * scale), my - 8, cx + int(13 * scale), my + 16], outline=(12, 12, 16), width=5)
        else:
            draw.line([(cx - int(20 * scale), my + 4), (cx + int(20 * scale), my + 4)], fill=(12, 12, 16), width=5)

    img.save(out_png_path, format="PNG")


def generate_scene_illustration(scene_data, characters, wardrobe_mood, setting_continuity, beat_idx, total_beats, out_png_path):
    style_key = scene_data.get("art_style_key", "warm_webcomic")
    style_desc = ART_STYLES.get(style_key, ART_STYLES["warm_webcomic"])["prompt"]
    mood_cfg = WARDROBE_MOODS.get(wardrobe_mood, WARDROBE_MOODS["casual_hangout"])

    cast_bible = []
    for c in characters:
        if c in CAST_IDENTITY:
            face = CAST_IDENTITY[c]["face_and_hair"]
            outfit = mood_cfg["outfits"].get(c, "")
            cast_bible.append(f"{face}, {outfit}")
    cast_desc = "; ".join(cast_bible)
    grade_name = scene_data.get("start_grade", "warm_lamp_night")

    full_prompt = (
        f"{style_desc}. "
        f"LOCKED CHARACTER & FULL-BODY WARDROBE BIBLE (MUST STAY 100% IDENTICAL ACROSS ALL {total_beats} SCENES): {cast_desc}. "
        f"LOCKED SETTING CONTINUITY: {setting_continuity}. "
        f"Beat {beat_idx + 1} of {total_beats} Action & Emotion: {scene_data['visual_prompt']}. "
        f"Lighting & Color Mood: {grade_name.replace('_', ' ')}. "
        "Show full-body or three-quarter human framing so their shirts, jackets, suits, pants, or shorts and expressive posture feel like real people. "
        "Keep characters centered between 22% and 70% vertical height so top and bottom caption zones stay clean and uncluttered. "
        "Strictly NO text, NO words, NO letters, NO speech bubbles inside the artwork."
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
                print(f"Generated Beat {beat_idx + 1}/{total_beats} artwork via {imagen_model} ({wardrobe_mood}, cast={characters})")
                return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:180]
            print(f"{imagen_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{imagen_model} skipped ({e})")

    for img_model in ["gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"]:
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
                        print(f"Generated Beat {beat_idx + 1}/{total_beats} artwork via {img_model} ({wardrobe_mood}, cast={characters})")
                        return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:180]
            print(f"{img_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    print(f"Using humanized full-body vector fallback for Beat {beat_idx + 1}/{total_beats} (cast={characters})")
    _render_multi_character_fallback(characters, wardrobe_mood, grade_name, beat_idx, out_png_path)


# ==============================================================================
# 5. LYRIA MUSIC + SUBTLE AUDIO-REACTIVE SFX SYNTHESIZER (N-BEAT SUPPORT)
# ==============================================================================
async def _stream_lyria_wav(music_prompt, bpm, out_wav, duration_sec):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})
    target_bytes = int(48000 * 2 * 2 * (duration_sec + 1.5))
    pcm_buffer = bytearray()

    async with client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(prompts=[types.WeightedPrompt(text=music_prompt, weight=1.0)])
        await session.set_music_generation_config(config=types.LiveMusicGenerationConfig(bpm=int(bpm), temperature=1.0))
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
        "-af", f"volume=0.84,afade=t=in:st=0:d=0.35,afade=t=out:st={max(0.5, duration_sec - 0.9):.3f}:d=0.9",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.28) * math.pi)
        return math.sin(2 * math.pi * (180 + 480 * dt) * dt) * env * 0.22
    if cue == "record_scratch":
        env = math.exp(-dt * 6.5)
        freq = 640.0 * math.exp(-dt * 5.5) + 90.0 * math.sin(dt * 90.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.34
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.8)
        freq = 76.0 * math.exp(-dt * 1.8)
        return math.sin(2 * math.pi * freq * dt) * env * 0.44
    if cue == "riser_hit":
        if dt < 0.35:
            return math.sin(2 * math.pi * (220 + 1200 * dt) * dt) * (dt / 0.35) * 0.24
        env = math.exp(-(dt - 0.35) * 8.0)
        return math.sin(2 * math.pi * 65.0 * dt) * env * 0.40
    env = math.exp(-dt * 16.0)
    return math.sin(2 * math.pi * 987.77 * dt) * env * 0.22


def build_director_audio(music_prompt, bpm, scenes, beat_starts, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating warm lo-fi synth bed...")
        sr = 48000
        total_samples = int(sr * duration_sec)
        chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
        bar_len = int(sr * 2.4)
        with wave.open(str(bed_wav), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            frames = bytearray()
            for i in range(total_samples):
                t = i / sr
                chord = chords[(i // bar_len) % len(chords)]
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.08
                s = int(max(-0.9, min(0.9, val)) * 32767)
                frames.extend(struct.pack("<hh", s, s))
            wf.writeframes(frames)

    sfx_wav = final_wav.parent / "director_sfx.wav"
    sr = 48000
    total_samples = int(sr * duration_sec)
    cues = [
        (beat_starts[i] + (0.12 if i == 0 else 0.0), scenes[i].get("sfx_cue", "pop_ding"))
        for i in range(len(scenes))
    ]

    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sr
            sig = 0.0
            for start_t, cue_name in cues:
                if start_t <= t <= start_t + 0.58:
                    sig += _synth_cue_sample(cue_name, t - start_t)
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            frames.extend(struct.pack("<hh", s, s))
        wf.writeframes(frames)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# 6. EASING, COLOR GRADING, GENTLE CAMERA & HIGH-VISIBILITY CAPTIONS
# ==============================================================================
def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _lerp_color(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def build_vignette_mask(strength=0.22):
    small_w, small_h = 270, 480
    vig = Image.new("L", (small_w, small_h), 0)
    px = vig.load()
    cx, cy = small_w / 2.0, small_h * 0.48
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_d
            px[x, y] = int(max(0.0, min(255.0, (d ** 2.4) * 255.0 * strength)))
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def build_ambient_glow_mask(strength=0.15):
    small_w, small_h = 270, 480
    mask = Image.new("L", (small_w, small_h), 0)
    px = mask.load()
    lx, ly = small_w * 0.72, small_h * 0.25
    max_d = math.hypot(small_w, small_h) * 0.80
    for y in range(small_h):
        for x in range(small_w):
            d = min(1.0, math.hypot(x - lx, y - ly) / max_d)
            px[x, y] = int(max(0.0, min(255.0, pow(1.0 - d, 2.0) * 255.0 * strength)))
    return mask.resize((W, H), Image.Resampling.BILINEAR)


def generate_particle_seeds(count=28):
    rng = random.Random(42)
    colors = [(255, 215, 110), (145, 218, 255), (165, 235, 180), (255, 195, 145)]
    return [
        {
            "x": rng.uniform(0.04, 0.96),
            "y": rng.uniform(0.05, 0.95),
            "depth": rng.uniform(0.45, 1.0),
            "speed": rng.uniform(0.55, 1.15),
            "size": rng.randint(2, 4),
            "phase": rng.uniform(0, math.pi * 2),
            "col": rng.choice(colors)
        }
        for _ in range(count)
    ]


def apply_progressive_grade_and_fx(frame, sc, local_p, t, vignette_mask, glow_mask, particle_seeds):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_lamp_night"), COLOR_GRADES["warm_lamp_night"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_lamp_night"), g1)
    prog = _ease_in_out_sine(local_p)

    tint_col = _lerp_color(g1["tint"], g2["tint"], prog)
    glow_col = _lerp_color(g1["glow"], g2["glow"], prog)
    contrast = g1["contrast"] + (g2["contrast"] - g1["contrast"]) * prog
    sat = g1["sat"] + (g2["sat"] - g1["sat"]) * prog

    tint_layer = Image.new("RGB", (W, H), tint_col)
    graded = Image.blend(frame, tint_layer, VISUAL_TUNING["color_tint_strength"])

    if VISUAL_TUNING["ambient_glow_strength"] > 0:
        glow_layer = Image.new("RGB", (W, H), glow_col)
        graded = Image.composite(glow_layer, graded, glow_mask)

    graded = ImageEnhance.Contrast(graded).enhance(contrast)
    graded = ImageEnhance.Color(graded).enhance(sat)

    dark_layer = Image.new("RGB", (W, H), (10, 12, 18))
    graded = Image.composite(dark_layer, graded, vignette_mask)

    style_fx = ART_STYLES.get(sc.get("art_style_key", "warm_webcomic"), {}).get("overlay_fx", "none")
    env_fx = sc.get("env_effect", "none")

    if style_fx != "none" or env_fx != "none":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if style_fx == "speed_lines":
            for i in range(24):
                ang = (i / 24.0) * math.pi * 2 + (t * 0.35)
                r0 = 460 + int(math.sin(t * 14.0 + i) * 28)
                r1 = 1080
                x0, y0 = int(W // 2 + math.cos(ang) * r0), int(H // 2 + math.sin(ang) * r0)
                x1, y1 = int(W // 2 + math.cos(ang) * r1), int(H // 2 + math.sin(ang) * r1)
                odraw.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 52), width=3)
        elif style_fx == "vhs":
            offset_y = int((t * 36) % 18)
            for y in range(offset_y, H, 18):
                odraw.line([(0, y), (W, y)], fill=(255, 255, 255, 18), width=2)

        base_alpha = 255 * VISUAL_TUNING["particle_opacity"]
        if env_fx == "screen_glow":
            pulse = int(32 + 18 * math.sin(t * 4.5))
            odraw.ellipse([W // 2 - 250, 720, W // 2 + 250, 1240], fill=(135, 215, 255, pulse))
        elif env_fx in ("rain", "snow", "sparks", "confetti", "dust"):
            for p in particle_seeds:
                depth = p["depth"]
                spd = p["speed"] * (0.6 + 0.5 * depth)
                p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
                if env_fx == "rain":
                    px = int(((p["x"] - t * 0.07 * spd) % 1.0) * W)
                    py = int(((p["y"] + t * 0.52 * spd) % 1.0) * H)
                    odraw.line([(px, py), (px - 6, py + 26)], fill=(195, 225, 255, int(p_alpha * 0.72)), width=2)
                elif env_fx == "snow":
                    px = int(((p["x"] + math.sin(t * 1.4 + p["phase"]) * 0.03) % 1.0) * W)
                    py = int(((p["y"] + t * 0.13 * spd) % 1.0) * H)
                    r = max(3, int((p["size"] + 1) * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(248, 252, 255, int(p_alpha * 0.78)))
                elif env_fx == "sparks":
                    px = int(((p["x"] + math.sin(t * 4.5 + p["phase"]) * 0.03) % 1.0) * W)
                    py = int(((p["y"] - t * 0.22 * spd) % 1.0) * H)
                    r = max(2, int((p["size"] + 1) * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.76)))
                elif env_fx == "confetti":
                    px = int(((p["x"] + math.sin(t * 2.2 + p["phase"]) * 0.04) % 1.0) * W)
                    py = int(((p["y"] + t * 0.15 * spd) % 1.0) * H)
                    r = max(4, int((p["size"] + 2) * depth))
                    c = p["col"]
                    odraw.rounded_rectangle([px - r, py - r // 2, px + r, py + r // 2], radius=2, fill=(c[0], c[1], c[2], int(p_alpha * 0.80)))
                elif env_fx == "dust":
                    px = int(((p["x"] + math.sin(t * 1.1 + p["phase"]) * 0.02) % 1.0) * W)
                    py = int(((p["y"] - t * 0.03 * spd) % 1.0) * H)
                    r = max(2, int(p["size"] * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.54)))

        graded = Image.alpha_composite(graded.convert("RGBA"), overlay).convert("RGB")

    return graded


def apply_camera_trajectory(base_img, move, local_p, scene_t, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    idle_breath = math.sin(t * 1.8) * 0.0025

    if move == "pull_back_reveal":
        zoom = (1.0 + max_z) - (max_z * _ease_out_quart(local_p)) + idle_breath
    elif move == "snap_zoom_face":
        if local_p < 0.10:
            zoom = 1.0 + (max_z * 1.15) * _ease_out_quart(local_p / 0.10)
        else:
            zoom = (1.0 + max_z * 1.15) - (max_z * 0.20 * _ease_in_out_sine((local_p - 0.10) / 0.90))
    elif move == "locked_deadpan":
        zoom = 1.02
    elif move == "gentle_float":
        zoom = 1.03 + math.sin(_ease_in_out_sine(local_p) * math.pi) * 0.025
    else:
        zoom = 1.0 + (max_z * _ease_in_out_sine(local_p)) + idle_breath

    zoom = max(1.02, zoom)
    crop_w = int(W / zoom)
    crop_h = int(H / zoom)
    max_dx = W - crop_w
    max_dy = H - crop_h

    if move == "pan_follow_left":
        x0 = int(max_dx * (1.0 - _ease_in_out_sine(local_p)))
        y0 = max_dy // 2
    elif move == "pan_follow_right":
        x0 = int(max_dx * _ease_in_out_sine(local_p))
        y0 = max_dy // 2
    elif move == "crane_tilt_up":
        x0 = max_dx // 2
        y0 = int(max_dy * (1.0 - _ease_out_quart(local_p)))
    else:
        x0 = max_dx // 2
        y0 = max_dy // 2

    return base_img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)


def apply_director_transition(prev_frame, curr_frame, transition_name, tr_p):
    eased = _ease_out_quart(tr_p)

    if transition_name == "hard_cut":
        return curr_frame

    if transition_name == "smash_zoom_cut":
        scale = 1.12 - 0.12 * eased
        cw, ch = int(W / scale), int(H / scale)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        return curr_frame.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)

    if transition_name in ("whip_pan_left", "whip_pan_right"):
        direction = -1 if transition_name == "whip_pan_left" else 1
        shift = int((1.0 - eased) * W * direction)
        canvas = Image.new("RGB", (W, H), (12, 14, 20))
        canvas.paste(prev_frame, (shift - W * direction, 0))
        canvas.paste(curr_frame, (shift, 0))
        return canvas

    if transition_name == "light_sweep":
        blended = Image.blend(prev_frame, curr_frame, eased)
        sweep = math.sin(tr_p * math.pi) * 0.20
        return Image.blend(blended, Image.new("RGB", (W, H), (255, 224, 155)), sweep)

    if transition_name == "blur_dissolve" and VISUAL_TUNING.get("enable_blur_transition", True):
        blended = Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))
        blur_r = math.sin(tr_p * math.pi) * 4.0
        if blur_r > 0.3:
            tiny = blended.resize((W // 4, H // 4), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=blur_r))
            return tiny.resize((W, H), Image.Resampling.BILINEAR)
        return blended

    return Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))


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


def draw_director_overlays(frame, chapter_tag, caption_style, sc, beat_idx, total_beats, scene_t, beat_dur, t, handle):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_lamp_night"), COLOR_GRADES["warm_lamp_night"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_lamp_night"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, beat_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg = g2["card_bg"]
    c_fg = g2["card_fg"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 1. Top Chapter / Moment Pill
    if chapter_tag:
        ent = _ease_out_quart(min(1.0, t / 0.25))
        tag_font = _load_font(30)
        tag_str = f"{beat_idx + 1}/{total_beats}  ·  {chapter_tag.strip().upper()}"
        bbox = odraw.textbbox((0, 0), tag_str, font=tag_font)
        tw = (bbox[2] - bbox[0]) + 54
        th = 54
        bx0 = (W - tw) // 2
        by0 = 165 + int((1.0 - ent) * -12)
        alpha = int(244 * ent)
        odraw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + th], radius=27, fill=(14, 16, 24, alpha), outline=(acc[0], acc[1], acc[2], alpha), width=3)
        odraw.text((W // 2, by0 + th // 2), tag_str, font=tag_font, fill=(acc[0], acc[1], acc[2], 255), anchor="mm")

    # 2. Subtle Emotion / Timestamp Cue
    emotion_cue = sc.get("emotion_cue", "")
    if emotion_cue and scene_t <= min(2.3, beat_dur * 0.65):
        pop_p = min(1.0, scene_t / 0.14)
        fade_start = min(1.85, beat_dur * 0.50)
        fade_out = 1.0 if scene_t < fade_start else max(0.0, 1.0 - (scene_t - fade_start) / 0.45)
        cue_scale = 1.10 - (0.10 * _ease_out_quart(pop_p))
        cue_alpha = int(255 * min(1.0, scene_t / 0.10) * fade_out)
        cue_font = _load_font(int(44 * cue_scale))
        odraw.text(
            (W // 2, 275),
            emotion_cue.strip().upper(),
            font=cue_font,
            fill=(acc[0], acc[1], acc[2], cue_alpha),
            anchor="mm",
            stroke_width=8,
            stroke_fill=(10, 10, 14, cue_alpha)
        )

    # 3. High-Visibility Story Caption in Instagram Reels Safe Zone
    story_caption = (sc.get("story_caption") or "").strip()
    if story_caption:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.18))
        time_left = max(0.0, beat_dur - scene_t)
        cap_out = 1.0 if (beat_idx == total_beats - 1 or time_left > 0.12) else max(0.0, time_left / 0.12)
        vis = cap_in * cap_out
        cap_alpha = int(252 * vis)

        if caption_style == "karaoke_pop":
            words = story_caption.split()
            active_idx = min(len(words) - 1, int(prog * len(words)))
            words[active_idx] = words[active_idx].upper()
            display_text = " ".join(words)
        else:
            display_text = story_caption

        wrapped = textwrap.fill(display_text, width=30)
        lines = wrapped.split("\n")

        if caption_style == "cinematic_minimal":
            sub_font = _load_font(44)
            box_h = 44 + len(lines) * 56
            y0 = 1345
            odraw.rounded_rectangle([64, y0, W - 64, y0 + box_h], radius=24, fill=(8, 10, 16, int(cap_alpha * 0.72)))
            odraw.multiline_text((W // 2, y0 + box_h // 2), wrapped, font=sub_font, fill=(255, 252, 245, cap_alpha), anchor="mm", align="center", spacing=12, stroke_width=6, stroke_fill=(8, 10, 16, cap_alpha))
        elif caption_style == "comic_callout":
            cap_font = _load_font(42)
            box_h = 52 + len(lines) * 54
            x0, y0 = 68, 1330 + int((1.0 - cap_in) * 10)
            x1, y1 = W - 68, y0 + box_h
            odraw.rounded_rectangle([x0 + 8, y0 + 8, x1 + 8, y1 + 8], radius=20, fill=(10, 10, 14, cap_alpha))
            odraw.rounded_rectangle([x0, y0, x1, y1], radius=20, fill=(255, 253, 244, cap_alpha), outline=(12, 12, 16, cap_alpha), width=5)
            odraw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=cap_font, fill=(14, 16, 22, cap_alpha), anchor="mm", align="center", spacing=11)
        else:
            cap_font = _load_font(42)
            box_h = 54 + len(lines) * 56
            x0, y0 = 62, 1330 + int((1.0 - cap_in) * 10)
            x1, y1 = W - 62, y0 + box_h
            odraw.rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 10], radius=26, fill=(4, 6, 10, int(cap_alpha * 0.65)))
            odraw.rounded_rectangle([x0, y0, x1, y1], radius=26, fill=(c_bg[0], c_bg[1], c_bg[2], min(255, int(cap_alpha * 0.96))), outline=(acc[0], acc[1], acc[2], cap_alpha), width=3)
            odraw.rounded_rectangle([x0 + 16, y0 + 22, x0 + 24, y1 - 22], radius=4, fill=(acc[0], acc[1], acc[2], cap_alpha))
            odraw.multiline_text((W // 2 + 8, (y0 + y1) // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=12)

    # 4. Handle Watermark
    handle_font = _load_font(28)
    odraw.text((W // 2, 1620), handle, font=handle_font, fill=(255, 255, 255, 232), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_director_reel(page_cfg, script_data, seed, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:4]
    total_beats = len(scenes)
    characters = seed["characters"]
    wardrobe_mood = seed["wardrobe_mood"]
    setting_continuity = script_data.get("setting_continuity", "Warm lived-in everyday setting")

    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        generate_scene_illustration(
            sc, characters, wardrobe_mood, setting_continuity, idx, total_beats, art_path
        )
        scene_imgs.append(Image.open(art_path).convert("RGB"))

    beat_durations = compute_beat_durations(scenes)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t
    print(f"Human-paced Reel timing ({total_dur:.2f}s total): {beat_durations}")

    final_wav = tmp_dir / "final_director.wav"
    build_director_audio(
        script_data.get("music_prompt", "warm indie lo-fi groove instrumental"),
        script_data.get("music_bpm", 102),
        scenes,
        beat_starts,
        total_dur,
        final_wav
    )

    total_frames = int(total_dur * FPS)
    chapter_tag = script_data.get("chapter_tag", "THE CHILL CLUB")
    caption_style = script_data.get("caption_style", "modern_card")
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
    particle_seeds = generate_particle_seeds(28)
    prev_rendered_frame = None

    for f_idx in range(total_frames):
        t = f_idx / FPS
        s_idx = total_beats - 1
        for i in range(total_beats):
            if i == total_beats - 1 or t < beat_starts[i + 1]:
                s_idx = i
                break

        sc = scenes[s_idx]
        beat_dur = beat_durations[s_idx]
        scene_t = t - beat_starts[s_idx]
        local_p = min(1.0, max(0.0, scene_t / beat_dur))
        base_img = scene_imgs[s_idx]

        if s_idx > 0 and sc.get("transition_in") == "freeze_record_scratch" and scene_t < 0.42 and prev_rendered_frame is not None:
            frame = ImageEnhance.Color(prev_rendered_frame).enhance(0.18)
        else:
            frame = apply_camera_trajectory(base_img, sc.get("camera_move", "dolly_push_in"), local_p, scene_t, t)
            frame = apply_progressive_grade_and_fx(frame, sc, local_p, t, vignette_mask, glow_mask, particle_seeds)

            trans_dur = VISUAL_TUNING["transition_sec"]
            if s_idx > 0 and scene_t < trans_dur and prev_rendered_frame is not None:
                tr_p = scene_t / trans_dur
                frame = apply_director_transition(prev_rendered_frame, frame, sc.get("transition_in", "hard_cut"), tr_p)
            else:
                prev_rendered_frame = frame.copy()

        # Top Progress Bar
        draw = ImageDraw.Draw(frame)
        prog = min(1.0, (f_idx + 1) / max(1, total_frames))
        g_curr = COLOR_GRADES.get(sc.get("end_grade", "warm_lamp_night"), COLOR_GRADES["warm_lamp_night"])
        bar_x = int(W * prog)
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=g_curr["accent"])

        frame = draw_director_overlays(
            frame=frame,
            chapter_tag=chapter_tag,
            caption_style=caption_style,
            sc=sc,
            beat_idx=s_idx,
            total_beats=total_beats,
            scene_t=scene_t,
            beat_dur=beat_dur,
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
    print(f"Rendered Human-Immersive Reel ({total_dur:.1f}s, {total_beats} scenes): {out_mp4}")


# ==============================================================================
# 7. GITHUB PAGES HOSTING & META GRAPH API V21.0 PUBLISHING
# ==============================================================================
def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish Reel {rel_path}"], check=True)
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
        time_slot_vibe = "MORNING SLOT: Waking up, coffee rituals, morning walks, or weekend relief."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT: Everyday errands, payday feelings, lunch breaks, or Friday countdowns."
    else:
        time_slot_vibe = "EVENING/NIGHT SLOT: Parked-car decompression, sunset drives, cozy apartment hangouts, or 2 AM deep talks."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('story_hook', '')}" for h in recent_history if h.get("story_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history)
        mood_cfg = WARDROBE_MOODS[seed["wardrobe_mood"]]

        cast_descriptions = "\n".join(
            f"- {c}: {CAST_IDENTITY[c]['archetype']} | Outfit in this Reel: {mood_cfg['outfits'][c]}"
            for c in seed["characters"]
        )

        prompt = (
            f"You are a Creative Director & Human-Behavior Storyteller for {page['handle']}.\n"
            f"CHANNEL IDENTITY: {page['domain']}\n\n"
            "### MANDATORY CREATIVE BRIEF\n"
            f"- Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Characters & Their Locked Outfits for All 4 Beats:\n{cast_descriptions}\n"
            f"- Wardrobe Mood: {mood_cfg['label']}\n"
            f"- Relatable Human Moment Seed: {seed['scenario']}\n"
            f"- Optional Pop-Culture Flavor (keep subtle—characters are real people first, NOT a movie parody): {seed['pop_flavor']}\n"
            f"- Art Style: {seed['art_style_key']}\n"
            f"- Caption Style: {seed['caption_style']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only weave in if completely natural): \n{trends}\n"
            f"- Previously Told Stories (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### HUMAN PSYCHOLOGY & IMMERSION RULES\n"
            "1. SELF-INSERTION: Write so the viewer immediately thinks 'that is literally me' or tags their best friend. Use natural relatable framing (POV, 'Me trying to...', or conversational inner monologue).\n"
            "2. NEVER RUSH TEXT: Keep every 'story_caption' crisp, punchy, and effortless to read (STRICTLY 7 to 13 words max per beat). Let the character's facial expression and body language carry half the comedy.\n"
            "3. 4-BEAT VISUAL PROGRESSION: Write 4 connected visual beats (Beat 1 Hook/Setup -> Beat 2 Relatable Escalation -> Beat 3 Reaction/Turn -> Beat 4 Human Punchline/Payoff) in ONE consistent setting ('setting_continuity').\n"
            "4. REAL HUMAN CHARACTERS: Keep their outfits identical across all 4 visual_prompts and describe natural human body language (leaning on a car door, holding a coffee cup, staring at a phone screen, slumping on a couch) rather than generic cartoon chaos.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "chapter_tag": "POV · 11:42 PM",\n'
            '  "caption_style": "' + seed["caption_style"] + '",\n'
            '  "setting_continuity": "Detailed consistent setting description shared across all 4 scenes",\n'
            '  "music_prompt": "Warm relatable indie lo-fi beat with soft guitar and bass instrumental",\n'
            '  "music_bpm": 100,\n'
            '  "scenes": [\n'
            '    {"story_caption": "Beat 1 relatable hook (7-13 words)", "emotion_cue": "11:42 PM", "visual_prompt": "Beat 1 full-body human action and expression, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "warm_lamp_night", "end_grade": "warm_lamp_night", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "dust", "sfx_cue": "pop_ding"},\n'
            '    {"story_caption": "Beat 2 escalation line (7-13 words)", "emotion_cue": "WAIT A SECOND.", "visual_prompt": "Beat 2 full-body human action and expression, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "warm_lamp_night", "end_grade": "cold_cyan_night", "camera_move": "pan_follow_right", "transition_in": "blur_dissolve", "env_effect": "screen_glow", "sfx_cue": "whoosh"},\n'
            '    {"story_caption": "Beat 3 reaction/turn line (7-13 words)", "emotion_cue": "EVERY TIME.", "visual_prompt": "Beat 3 full-body human reaction and body language, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "cold_cyan_night", "end_grade": "crimson_panic", "camera_move": "snap_zoom_face", "transition_in": "whip_pan_left", "env_effect": "none", "sfx_cue": "record_scratch"},\n'
            '    {"story_caption": "Beat 4 relatable payoff/punchline (7-13 words)", "emotion_cue": "WORTH IT.", "visual_prompt": "Beat 4 full-body ending pose and expression, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "warm_lamp_night", "end_grade": "golden_hour", "camera_move": "pull_back_reveal", "transition_in": "light_sweep", "env_effect": "none", "sfx_cue": "vine_boom_sub"}\n'
            "  ],\n"
            '  "ig_caption": "Warm relatable caption that invites followers to share their own version",\n'
            '  "pinned_comment": "Specific relatable question for the comments"\n'
            "}\n"
            f"Allowed art_style_key: {list(ART_STYLES.keys())}\n"
            f"Allowed start_grade / end_grade: {list(COLOR_GRADES.keys())}\n"
            f"Allowed camera_move: {ALL_CAMERA_MOVES}\n"
            f"Allowed transition_in: {ALL_TRANSITIONS}\n"
            f"Allowed env_effect: {ALL_ENV_EFFECTS}\n"
            f"Allowed sfx_cue: {ALL_SFX_CUES}"
        )

        script_data = ask_gemini_script(prompt, seed)
        final_caption = build_smart_hashtags(script_data.get("ig_caption", ""), script_data, seed)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"

        render_director_reel(page, script_data, seed, rel_mp4)
        act1_line = script_data["scenes"][0].get("story_caption", "")
        full_story_text = "\n".join(f"Beat {i+1}: {s.get('story_caption', '')}" for i, s in enumerate(script_data["scenes"][:4]))
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Cast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nWardrobe: {seed['wardrobe_mood']}\nStyle: {seed['art_style_key']}\n{script_data.get('chapter_tag', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "scenario_tag": seed["scenario"][:28],
            "cast_mode": seed["cast_mode"],
            "characters": seed["characters"],
            "wardrobe_mood": seed["wardrobe_mood"],
            "art_style_key": seed["art_style_key"],
            "story_hook": act1_line,
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
