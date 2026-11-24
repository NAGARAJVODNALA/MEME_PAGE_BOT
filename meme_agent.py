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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920

# ==============================================================================
# CREATIVE DIRECTOR & REFERENCE-STYLE TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.18,      # Subtle edge depth without muddying cel-shaded art
    "color_tint_strength": 0.10,    # Natural environment color wash
    "ambient_glow_strength": 0.14,  # Warm lamp / window / phone screen rim light
    "particle_opacity": 0.30,       # Gentle dust motes / sparks / rain
    "max_zoom_delta": 0.09,         # Purposeful camera framing & punch-ins
    "transition_sec": 0.22,         # Crisp comedic cut / whip-pan timing
    "enable_blur_transition": True,
    "min_beat_sec": 3.2,            # Enough time to absorb facial acting & props
    "max_beat_sec": 5.0,            # Keeps comedic momentum snappy
    "words_per_sec": 2.7            # Comfortable human reading speed
}

# ==============================================================================
# 1. REFERENCE-STYLE CHARACTER ROSTER (SHADED ROUND HEAD + STICK BODY + MITTENS)
# ==============================================================================
# Keeps Phil, Alan, Stu, and Doug while matching the exact visual DNA of the
# reference animations: large cel-shaded off-white/warm-gray round heads (#D5D2CD),
# thick black ink outlines, thin black stick spines/limbs, rounded black mitten
# hands, and expressive micro-facial acting.
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Confident Instigator (smug grin, effortless optimism, talks everyone into spontaneous plans)",
        "visual": (
            "Phil (2D webcomic character with large soft warm-gray cel-shaded round head #D5D2CD, "
            "thick black ink outline, wearing a curved terracotta/muted-olive baseball cap, confident smirk, "
            "thin black stick-figure body and limbs with rounded black mitten hands)"
        ),
        "cap_color": (166, 98, 72),
        "beard": False,
        "glasses": False,
        "satchel": False
    },
    "Alan": {
        "archetype": "The Deadpan Wildcard (earnest wide eyes, 2:30 AM life theories, unexpectedly loyal)",
        "visual": (
            "Alan (2D webcomic character with large soft warm-gray cel-shaded round head #D5D2CD, "
            "thick black ink outline, scruffy brown beard on lower jaw, wide earnest deadpan eyes, "
            "thin black stick-figure body with a brown crossbody satchel strap and rounded black mitten hands)"
        ),
        "cap_color": None,
        "beard": True,
        "glasses": False,
        "satchel": True
    },
    "Stu": {
        "archetype": "The Relatable Overthinker (checks bank app twice, sweats over alarms and budgets)",
        "visual": (
            "Stu (2D webcomic character with large soft warm-gray cel-shaded round head #D5D2CD, "
            "thick black ink outline, thick black-rimmed square glasses, small side-part hair tuft, "
            "anxious expressive eyes with forehead sweat drops, thin black stick-figure body and black mitten hands)"
        ),
        "cap_color": None,
        "beard": False,
        "glasses": True,
        "satchel": False
    },
    "Doug": {
        "archetype": "The Chill Grounded Friend (half-lidded calm eyes, unbothered voice of reason)",
        "visual": (
            "Doug (2D webcomic character with large soft warm-gray cel-shaded round head #D5D2CD, "
            "thick black ink outline, calm half-lidded eyes, relaxed deadpan smile, "
            "thin black stick-figure body and rounded black mitten hands)"
        ),
        "cap_color": None,
        "beard": False,
        "glasses": False,
        "satchel": False
    }
}

CAST_MODES = {
    "solo_pov": {
        "desc": "1 character in a relatable 'Pov: Me...' or 'Me at home' personal moment",
        "lineups": [["Stu"], ["Phil"], ["Alan"], ["Doug"]]
    },
    "classic_duo": {
        "desc": "2 contrasting friends bouncing off each other",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Alan", "Stu"],
            ["Phil", "Alan"],
            ["Stu", "Doug"]
        ]
    },
    "trio_hangout": {
        "desc": "3 friends caught in an everyday group-chat or apartment moment",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_crew_4": {
        "desc": "All 4 friends (Phil, Alan, Stu, and Doug) together for a trip, celebration, or disaster",
        "lineups": [["Phil", "Alan", "Stu", "Doug"]]
    }
}

FACIAL_EXPRESSIONS = [
    "smug_snooze",
    "exhausted_half_lidded",
    "sweat_grit",
    "guilty_puppy_eyes",
    "bloodshot_shock",
    "deadpan_camera_stare",
    "confident_smirk"
]

# ==============================================================================
# 2. REALITY-ANCHORED ENVIRONMENTS, ART STYLES & RELATABLE SCENARIOS
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "warm_desk_lamp": {
        "desc": "Warm amber-lit home desk with walnut wood surface, wall sconce lamp, potted green plant, red ceramic mug, and notebook",
        "wall": (196, 132, 84),
        "surface": (118, 72, 42),
        "accent_prop": (184, 58, 52)
    },
    "overcast_bedroom": {
        "desc": "Cozy minimalist bedroom with soft slate-gray blanket, white pillow, framed wall art, and overhead pendant lamp",
        "wall": (198, 204, 212),
        "surface": (146, 156, 168),
        "accent_prop": (235, 238, 244)
    },
    "living_room_window": {
        "desc": "Suburban living room with slate-blue couch and large window view showing butter-yellow house exterior and stacked delivery boxes",
        "wall": (176, 198, 222),
        "surface": (98, 122, 152),
        "accent_prop": (194, 148, 96)
    },
    "midnight_car_cabin": {
        "desc": "Parked car interior at night with warm dashboard glow, steering wheel, and twilight blue streetlights outside the window",
        "wall": (34, 46, 72),
        "surface": (24, 28, 38),
        "accent_prop": (118, 212, 255)
    },
    "kitchen_counter": {
        "desc": "Bright home kitchen counter with stove, frying pan, coffee maker, and snack bags",
        "wall": (214, 206, 194),
        "surface": (134, 138, 146),
        "accent_prop": (86, 156, 108)
    }
}

ART_STYLES = {
    "reference_webcomic_2d": {
        "prompt": (
            "Clean 2D Flash/webcomic animation frame in the exact style of classic relatable stick-character shorts: "
            "large soft warm-gray cel-shaded round heads (#D5D2CD) with thick uniform black ink outlines, "
            "thin black stick-figure bodies and limbs, small rounded black mitten hands, highly expressive cartoon faces, "
            "and clean hand-drawn 2D interior backgrounds with crisp ink lines and warm cel-shaded lighting"
        ),
        "overlay_fx": "none",
        "hashtags": ["#webcomic", "#2danimation", "#relatable"]
    },
    "cozy_lamp_cartoon": {
        "prompt": (
            "Warm 2D animated webcomic short with rich amber lamp lighting, cel-shaded round-head stick characters "
            "with thick black outlines, black mitten hands, detailed tabletop props (mugs, notebooks, phones), "
            "and expressive comedic micro-expressions"
        ),
        "overlay_fx": "none",
        "hashtags": ["#animatedshorts", "#relatablememes", "#2danimation"]
    },
    "manga_shock_comic": {
        "prompt": (
            "2D webcomic animation frame with cel-shaded round-head stick characters, thick black ink outlines, "
            "black mitten hands, and dramatic anime/manga comedic reaction framing with high-contrast impact"
        ),
        "overlay_fx": "speed_lines",
        "hashtags": ["#animememes", "#funnyreels", "#relatable"]
    },
    "suburban_cel_toon": {
        "prompt": (
            "Clean pastel-and-daylight 2D animated comedy short with cel-shaded round-head stick characters, "
            "black stick limbs, black mitten hands, crisp architectural interiors and window perspectives"
        ),
        "overlay_fx": "none",
        "hashtags": ["#cartoonmemes", "#sliceoflife", "#funnyvideos"]
    }
}

RELATABLE_SCENARIOS = [
    {
        "hook": "Pov: Me trying to save money 😂",
        "env": "warm_desk_lamp",
        "clocks": ["DAY 1", "DAY 2", "DAY 3", "10 MINS LATER"],
        "story_seed": "Trying to eat cheap leftovers or open a stubborn can at home to save money, sweating and struggling until giving up and ordering food anyway"
    },
    {
        "hook": "When you have to wake up at 8 am",
        "env": "overcast_bedroom",
        "clocks": ["6:55am", "7:10am", "7:18am", "12:34pm"],
        "story_seed": "Setting 6 alarms, snoozing smugly under the blanket for '5 more minutes', and waking up at 12:34pm in bloodshot panic"
    },
    {
        "hook": "Me: I need to stay home so I don't spend money",
        "env": "living_room_window",
        "clocks": ["1:15 PM", "2:40 PM", "4:05 PM", "5:30 PM"],
        "story_seed": "Staying home on the couch to avoid spending money while online delivery boxes keep piling up outside the living room window"
    },
    {
        "hook": "Pov: You get home and sit in your parked car",
        "env": "midnight_car_cabin",
        "clocks": ["6:12 PM", "6:24 PM", "6:38 PM", "6:51 PM"],
        "story_seed": "Pulling into the driveway after a long day and sitting in total silence for 35 minutes just staring at the steering wheel"
    },
    {
        "hook": "Pov: Checking your bank app before tapping your card",
        "env": "warm_desk_lamp",
        "clocks": ["11:02 AM", "11:03 AM", "11:04 AM", "11:05 AM"],
        "story_seed": "Sweating while waiting for the banking app to load before buying a $6 iced coffee, then tapping the card anyway"
    },
    {
        "hook": "Pov: 'I'm going to sleep early tonight'",
        "env": "overcast_bedroom",
        "clocks": ["10:30 PM", "12:15 AM", "2:10 AM", "3:45 AM"],
        "story_seed": "Lying in dim bedroom light with only the smartphone screen glowing on your face, scrolling random thoughts until 3:45 AM"
    },
    {
        "hook": "Me walking into the store for ONE item",
        "env": "kitchen_counter",
        "clocks": ["5:10 PM", "5:18 PM", "5:29 PM", "5:40 PM"],
        "story_seed": "Walking out with arms overflowing with snacks and drinks while completely forgetting the one item you actually needed"
    },
    {
        "hook": "Group chat trying to pick one place to eat",
        "env": "living_room_window",
        "clocks": ["7:00 PM", "7:35 PM", "8:15 PM", "8:50 PM"],
        "story_seed": "47 messages of 'I'm down for whatever' until everyone ends up at the exact same spot as every Friday"
    }
]

# ==============================================================================
# 3. REALISTIC ENVIRONMENT COLOR GRADES, CAMERA MOVES & TRANSITIONS
# ==============================================================================
COLOR_GRADES = {
    "warm_amber_desk": {
        "tint": (235, 154, 88), "glow": (255, 208, 128), "contrast": 1.05, "sat": 1.08,
        "card_bg": (24, 18, 18), "card_fg": (255, 248, 240), "accent": (255, 184, 96)
    },
    "overcast_morning_bedroom": {
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.04, "sat": 0.86,
        "card_bg": (22, 24, 30), "card_fg": (248, 250, 255), "accent": (152, 196, 245)
    },
    "dim_night_phone_glow": {
        "tint": (58, 76, 112), "glow": (132, 214, 255), "contrast": 1.08, "sat": 0.90,
        "card_bg": (14, 18, 28), "card_fg": (238, 246, 255), "accent": (124, 212, 255)
    },
    "golden_morning_sunlight": {
        "tint": (248, 188, 112), "glow": (255, 232, 168), "contrast": 1.05, "sat": 1.12,
        "card_bg": (28, 22, 18), "card_fg": (255, 250, 242), "accent": (255, 196, 92)
    },
    "suburban_daylight_cel": {
        "tint": (196, 216, 238), "glow": (255, 244, 204), "contrast": 1.04, "sat": 1.06,
        "card_bg": (20, 24, 34), "card_fg": (250, 252, 255), "accent": (255, 210, 88)
    },
    "midnight_car_dashboard": {
        "tint": (64, 96, 148), "glow": (142, 214, 255), "contrast": 1.07, "sat": 0.96,
        "card_bg": (14, 20, 32), "card_fg": (240, 248, 255), "accent": (128, 212, 255)
    },
    "crimson_panic_shock": {
        "tint": (228, 72, 82), "glow": (255, 134, 102), "contrast": 1.12, "sat": 1.16,
        "card_bg": (42, 14, 18), "card_fg": (255, 244, 244), "accent": (255, 96, 102)
    },
    "sunset_golden_drive": {
        "tint": (246, 152, 84), "glow": (255, 208, 122), "contrast": 1.06, "sat": 1.12,
        "card_bg": (26, 18, 20), "card_fg": (255, 248, 240), "accent": (255, 174, 92)
    },
    "desaturated_gloom": {
        "tint": (128, 136, 148), "glow": (184, 194, 208), "contrast": 1.04, "sat": 0.56,
        "card_bg": (20, 22, 28), "card_fg": (236, 240, 246), "accent": (168, 186, 212)
    }
}

ALL_TRANSITIONS = [
    "hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right",
    "blur_dissolve", "fade_to_black_cut", "freeze_record_scratch"
]

ALL_CAMERA_MOVES = [
    "dolly_push_in", "pull_back_reveal", "snap_zoom_face",
    "locked_deadpan", "pan_follow_left", "pan_follow_right",
    "handheld_struggle", "gentle_float"
]

ALL_PROP_OVERLAYS = [
    "none", "sweat_drops", "phone_vibrate_arcs", "delivery_box_drop", "spark_burst", "zzz_float"
]

ALL_ENV_EFFECTS = [
    "none", "rain", "sparks", "confetti", "dust", "screen_glow"
]

ALL_SFX_CUES = [
    "whoosh", "record_scratch", "vine_boom_sub", "alarm_buzz", "pop_ding", "riser_hit"
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
        "layout_mode": "v8_reference_webcomic",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Relatable 2D animated webcomic shorts starring Phil, Alan, Stu, and Doug — shaded round-head stick characters with black mitten hands, micro-facial acting, and realistic everyday environments",
        "art_style": "Clean 2D webcomic animation with cel-shaded warm-gray round heads, thick black outlines, black stick limbs, black mitten hands, and lived-in interior backgrounds"
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
            "Trying to save money at home vs ordering delivery",
            "Snoozing 6 alarms and waking up at noon",
            "Sitting in the parked car after work"
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
    """Selects a fresh relatable scenario, cast lineup, and visual style without repeating recent hooks."""
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_hooks = {h.get("top_hook", "") for h in recent_history[-6:]}
    recent_casts = [h.get("cast_mode", "") for h in recent_history[-2:]]

    for _ in range(45):
        cast_mode = random.choice(list(CAST_MODES.keys()))
        if cast_mode in recent_casts and random.random() < 0.65:
            continue
        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        scen = random.choice(RELATABLE_SCENARIOS)
        if scen["hook"] in recent_hooks and random.random() < 0.85:
            continue
        art_style_key = random.choice(list(ART_STYLES.keys()))
        combo_key = f"{cast_mode}|{'+'.join(characters)}|{scen['hook'][:24]}|{art_style_key}"
        if combo_key not in used_keys:
            return {
                "combo_key": combo_key,
                "cast_mode": cast_mode,
                "characters": characters,
                "scenario": scen,
                "art_style_key": art_style_key
            }

    cast_mode = random.choice(list(CAST_MODES.keys()))
    return {
        "combo_key": f"ref_{int(time.time())}",
        "cast_mode": cast_mode,
        "characters": random.choice(CAST_MODES[cast_mode]["lineups"]),
        "scenario": random.choice(RELATABLE_SCENARIOS),
        "art_style_key": "reference_webcomic_2d"
    }


def compute_beat_durations(scenes):
    """Calculates natural human reading & facial-reaction absorption time per beat."""
    durations = []
    for idx, sc in enumerate(scenes):
        words = len((sc.get("bottom_caption") or "").split())
        read_sec = words / VISUAL_TUNING["words_per_sec"]
        cushion = 1.65 if idx == len(scenes) - 1 else 1.40
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], read_sec + cushion)), 2)
        durations.append(dur)
    return durations


def validate_and_fix_plan(script_data, seed):
    """Enforces 4 visual beats, valid expressions, non-repeating cameras/transitions, and concise captions."""
    if not isinstance(script_data, dict):
        return _build_local_fallback_script(seed)

    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return _build_local_fallback_script(seed)

    scenes = scenes[:4]
    used_cams = set()
    used_trans = set()
    scen = seed["scenario"]

    if not script_data.get("top_hook"):
        script_data["top_hook"] = scen["hook"]
    if script_data.get("environment_key") not in ENVIRONMENT_PRESETS:
        script_data["environment_key"] = scen["env"]

    default_exprs = ["exhausted_half_lidded", "sweat_grit", "guilty_puppy_eyes", "bloodshot_shock"]

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "warm_amber_desk" if idx < 3 else "crimson_panic_shock"
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]
        if sc.get("art_style_key") not in ART_STYLES:
            sc["art_style_key"] = seed["art_style_key"]
        if sc.get("expression") not in FACIAL_EXPRESSIONS:
            sc["expression"] = default_exprs[idx % len(default_exprs)]
        if sc.get("prop_overlay") not in ALL_PROP_OVERLAYS:
            sc["prop_overlay"] = "none"
        if sc.get("env_effect") not in ALL_ENV_EFFECTS:
            sc["env_effect"] = "none"
        if sc.get("sfx_cue") not in ALL_SFX_CUES:
            sc["sfx_cue"] = "pop_ding" if idx < 2 else ("alarm_buzz" if idx == 2 else "vine_boom_sub")
        if not sc.get("clock_label"):
            sc["clock_label"] = scen["clocks"][idx]

        cam = sc.get("camera_move")
        if cam not in ALL_CAMERA_MOVES or cam in used_cams:
            avail_cams = [c for c in ALL_CAMERA_MOVES if c not in used_cams]
            cam = random.choice(avail_cams) if avail_cams else "dolly_push_in"
        sc["camera_move"] = cam
        used_cams.add(cam)

        tr = sc.get("transition_in")
        if tr not in ALL_TRANSITIONS or tr in used_trans:
            avail_tr = [t for t in ALL_TRANSITIONS if t not in used_trans]
            tr = random.choice(avail_tr) if avail_tr else "hard_cut"
        sc["transition_in"] = tr
        used_trans.add(tr)

        cap = (sc.get("bottom_caption") or "").strip()
        words = cap.split()
        if len(words) > 12:
            sc["bottom_caption"] = " ".join(words[:11]) + "..."

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
    dynamic_tags.extend(ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"]).get("hashtags", []))

    chars = seed.get("characters", [])
    if len(chars) >= 3:
        dynamic_tags.extend(["#friendgroup", "#theboys", "#relatable"])
    elif len(chars) == 2:
        dynamic_tags.extend(["#bestfriends", "#duolife"])
    else:
        dynamic_tags.extend(["#literallyme", "#pov"])

    dynamic_tags.extend(["#wearechillclub", "#animatedshorts", "#funnyreels"])

    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Tell me this isn't literally you."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    chars = seed["characters"]
    char_str = " and ".join(chars) if len(chars) <= 2 else ", ".join(chars[:-1]) + f", and {chars[-1]}"
    scen = seed["scenario"]
    style_key = seed["art_style_key"]

    return {
        "top_hook": scen["hook"],
        "environment_key": scen["env"],
        "setting_continuity": ENVIRONMENT_PRESETS[scen["env"]]["desc"],
        "music_prompt": "Playful lo-fi indie marimba and acoustic guitar comedy loop instrumental",
        "music_bpm": 106,
        "scenes": [
            {
                "clock_label": scen["clocks"][0],
                "bottom_caption": "",
                "expression": "exhausted_half_lidded",
                "prop_overlay": "zzz_float",
                "visual_prompt": f"Medium shot of {char_str} in {scen['env']}, half-lidded tired eyes, leaning on hand, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_amber_desk",
                "end_grade": "warm_amber_desk",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "dust",
                "sfx_cue": "pop_ding"
            },
            {
                "clock_label": scen["clocks"][1],
                "bottom_caption": "Just five more minutes.",
                "expression": "smug_snooze",
                "prop_overlay": "phone_vibrate_arcs",
                "visual_prompt": f"Close-up of {char_str} smirking smugly with closed eyes while phone vibrates nearby, NO text",
                "art_style_key": style_key,
                "start_grade": "overcast_morning_bedroom",
                "end_grade": "overcast_morning_bedroom",
                "camera_move": "pan_follow_right",
                "transition_in": "blur_dissolve",
                "env_effect": "screen_glow",
                "sfx_cue": "alarm_buzz"
            },
            {
                "clock_label": scen["clocks"][2],
                "bottom_caption": "Wait... what time is it?!",
                "expression": "sweat_grit",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Extreme face close-up of {char_str} sweating nervously with wide panicked eyes, NO text",
                "art_style_key": style_key,
                "start_grade": "dim_night_phone_glow",
                "end_grade": "crimson_panic_shock",
                "camera_move": "snap_zoom_face",
                "transition_in": "whip_pan_left",
                "env_effect": "none",
                "sfx_cue": "record_scratch"
            },
            {
                "clock_label": scen["clocks"][3],
                "bottom_caption": "Every single time.",
                "expression": "bloodshot_shock",
                "prop_overlay": "delivery_box_drop",
                "visual_prompt": f"Pulled-back reveal of {char_str} with bloodshot wide shock eyes surrounded by the aftermath, NO text",
                "art_style_key": "manga_shock_comic",
                "start_grade": "crimson_panic_shock",
                "end_grade": "golden_morning_sunlight",
                "camera_move": "pull_back_reveal",
                "transition_in": "smash_zoom_cut",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": f"{scen['hook']} ({char_str})",
        "pinned_comment": "Be honest: how many times do you hit snooze before actually getting up?"
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
                        print(f"Generated reference-style script with {model}")
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

    print(f"All Gemini text endpoints busy ({last_err}); using local reference-style script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. REFERENCE-STYLE CEL-SHADED STICKMAN & ENVIRONMENT FALLBACK + AI GENERATOR
# ==============================================================================
def _draw_reference_character(draw, name, cx, cy, scale, expression, beat_idx):
    """Draws the exact reference-style character: cel-shaded round head, thin black stick limbs, mitten hands."""
    prof = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])
    ink = (18, 18, 22)
    head_fill = (216, 213, 208)   # Soft warm-gray cel-shaded head (#D8D5D0)
    head_shadow = (188, 185, 180) # Subtle right-side cel shading

    r_head = int(108 * scale)
    neck_y = cy + r_head
    hip_y = neck_y + int(175 * scale)
    limb_w = max(5, int(7 * scale))
    mitten_r = max(10, int(14 * scale))

    # 1. Thin Black Stick-Figure Spine, Legs & Expressive Mitten Hands
    draw.line([(cx, neck_y), (cx, hip_y)], fill=ink, width=limb_w)
    # Legs (seated or standing depending on beat)
    if beat_idx in (0, 1):
        # Seated bent knees
        draw.line([(cx, hip_y), (cx - int(55 * scale), hip_y + int(70 * scale))], fill=ink, width=limb_w)
        draw.line([(cx - int(55 * scale), hip_y + int(70 * scale)), (cx - int(55 * scale), hip_y + int(150 * scale))], fill=ink, width=limb_w)
        draw.line([(cx, hip_y), (cx + int(55 * scale), hip_y + int(70 * scale))], fill=ink, width=limb_w)
        draw.line([(cx + int(55 * scale), hip_y + int(70 * scale)), (cx + int(55 * scale), hip_y + int(150 * scale))], fill=ink, width=limb_w)
    else:
        draw.line([(cx, hip_y), (cx - int(45 * scale), hip_y + int(155 * scale))], fill=ink, width=limb_w)
        draw.line([(cx, hip_y), (cx + int(45 * scale), hip_y + int(155 * scale))], fill=ink, width=limb_w)

    # Crossbody satchel strap for Alan
    if prof["satchel"]:
        draw.line([(cx - int(22 * scale), neck_y + 10), (cx + int(26 * scale), hip_y - 10)], fill=(128, 84, 52), width=max(6, int(9 * scale)))

    # Arms + Rounded Black Mitten Hands
    sh_y = neck_y + int(28 * scale)
    if expression in ("sweat_grit", "bloodshot_shock") or beat_idx == 2:
        # Hands up near face in shock / panic
        l_hand = (cx - int(82 * scale), cy + int(24 * scale))
        r_hand = (cx + int(82 * scale), cy + int(24 * scale))
        draw.line([(cx, sh_y), (cx - int(96 * scale), sh_y + int(26 * scale)), l_hand], fill=ink, width=limb_w)
        draw.line([(cx, sh_y), (cx + int(96 * scale), sh_y + int(26 * scale)), r_hand], fill=ink, width=limb_w)
    elif beat_idx == 0:
        # Resting chin on hand / holding mug
        l_hand = (cx - int(28 * scale), cy + int(86 * scale))
        r_hand = (cx + int(76 * scale), sh_y + int(62 * scale))
        draw.line([(cx, sh_y), (cx - int(74 * scale), sh_y + int(42 * scale)), l_hand], fill=ink, width=limb_w)
        draw.line([(cx, sh_y), r_hand], fill=ink, width=limb_w)
    else:
        l_hand = (cx - int(74 * scale), sh_y + int(96 * scale))
        r_hand = (cx + int(74 * scale), sh_y + int(96 * scale))
        draw.line([(cx, sh_y), l_hand], fill=ink, width=limb_w)
        draw.line([(cx, sh_y), r_hand], fill=ink, width=limb_w)

    for hx, hy in (l_hand, r_hand):
        draw.ellipse([hx - mitten_r, hy - mitten_r, hx + mitten_r, hy + mitten_r], fill=ink)

    # 2. Large Cel-Shaded Round Head
    draw.ellipse([cx - r_head, cy - r_head, cx + r_head, cy + r_head], fill=head_fill)
    draw.pieslice([cx - r_head + 6, cy - r_head + 6, cx + r_head - 2, cy + r_head - 2], start=-55, end=65, fill=head_shadow)
    draw.ellipse([cx - r_head, cy - r_head, cx + r_head, cy + r_head], outline=ink, width=max(6, int(9 * scale)))

    # 3. Signature Character Features (Phil's cap, Alan's beard, Stu's glasses)
    if prof["cap_color"]:
        cap_c = prof["cap_color"]
        draw.pieslice([cx - r_head - 2, cy - r_head - 12, cx + r_head + 2, cy - int(r_head * 0.12)], start=180, end=360, fill=cap_c, outline=ink, width=max(6, int(8 * scale)))
        draw.rounded_rectangle([cx - int(10 * scale), cy - int(r_head * 0.56), cx + int(r_head * 1.32), cy - int(r_head * 0.34)], radius=8, fill=cap_c, outline=ink, width=max(5, int(7 * scale)))

    if prof["beard"]:
        draw.pieslice([cx - int(r_head * 0.86), cy + int(4 * scale), cx + int(r_head * 0.86), cy + r_head + 4], start=0, end=180, fill=(92, 64, 46), outline=ink, width=max(5, int(7 * scale)))

    # 4. Micro-Facial Acting (Reference Video Eye & Mouth States)
    eye_dx = int(36 * scale)
    eye_y = cy - int(10 * scale)
    er = int(22 * scale)

    if expression == "smug_snooze":
        # Curved closed eyelids (u u) + smug smirk
        draw.arc([cx - eye_dx - er, eye_y - 10, cx - eye_dx + er, eye_y + 18], start=10, end=170, fill=ink, width=max(5, int(6 * scale)))
        draw.arc([cx + eye_dx - er, eye_y - 10, cx + eye_dx + er, eye_y + 18], start=10, end=170, fill=ink, width=max(5, int(6 * scale)))
        draw.arc([cx - int(18 * scale), cy + int(24 * scale), cx + int(28 * scale), cy + int(46 * scale)], start=15, end=155, fill=ink, width=max(4, int(6 * scale)))
    elif expression == "exhausted_half_lidded":
        # Heavy horizontal upper eyelids cutting across pupils (- -)
        for side in (-1, 1):
            ex = cx + side * eye_dx
            draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(252, 252, 255), outline=ink, width=4)
            draw.ellipse([ex - 6, eye_y - 4, ex + 6, eye_y + 8], fill=ink)
            draw.pieslice([ex - er, eye_y - er, ex + er, eye_y + er], start=180, end=360, fill=head_fill, outline=ink, width=4)
        draw.line([(cx - int(22 * scale), cy + int(38 * scale)), (cx + int(22 * scale), cy + int(34 * scale))], fill=ink, width=max(4, int(6 * scale)))
    elif expression == "sweat_grit":
        # Squeezed shut eyes (> <) + clenched zig-zag teeth + sweat drops
        draw.line([(cx - eye_dx - 16, eye_y - 12), (cx - eye_dx + 12, eye_y), (cx - eye_dx - 16, eye_y + 12)], fill=ink, width=5)
        draw.line([(cx + eye_dx + 16, eye_y - 12), (cx + eye_dx - 12, eye_y), (cx + eye_dx + 16, eye_y + 12)], fill=ink, width=5)
        # Clenched teeth box
        mx0, my0 = cx - int(32 * scale), cy + int(24 * scale)
        mx1, my1 = cx + int(32 * scale), cy + int(48 * scale)
        draw.rounded_rectangle([mx0, my0, mx1, my1], radius=8, fill=(252, 252, 255), outline=ink, width=4)
        for tx in range(mx0 + 12, mx1 - 6, 14):
            draw.line([(tx, my0), (tx, my1)], fill=ink, width=3)
        # Forehead sweat teardrops
        for sx, sy in [(cx - int(58 * scale), cy - int(44 * scale)), (cx + int(62 * scale), cy - int(36 * scale)), (cx - int(72 * scale), cy - int(16 * scale))]:
            draw.ellipse([sx - 6, sy - 9, sx + 6, sy + 9], fill=(165, 224, 255), outline=ink, width=2)
    elif expression == "bloodshot_shock":
        # Wide white eyes with red veins + square shock mouth
        for side in (-1, 1):
            ex = cx + side * eye_dx
            er_big = int(28 * scale)
            draw.ellipse([ex - er_big, eye_y - er_big, ex + er_big, eye_y + er_big], fill=(255, 250, 250), outline=ink, width=5)
            draw.line([(ex - er_big + 4, eye_y - 6), (ex - 8, eye_y - 2)], fill=(224, 52, 62), width=2)
            draw.line([(ex + er_big - 4, eye_y + 8), (ex + 8, eye_y + 3)], fill=(224, 52, 62), width=2)
            draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=ink)
        draw.rounded_rectangle([cx - int(26 * scale), cy + int(24 * scale), cx + int(26 * scale), cy + int(64 * scale)], radius=10, fill=(252, 252, 255), outline=ink, width=5)
    elif expression == "guilty_puppy_eyes":
        # Big shiny sparkle eyes + raised worried eyebrows
        for side in (-1, 1):
            ex = cx + side * eye_dx
            er_big = int(25 * scale)
            draw.ellipse([ex - er_big, eye_y - er_big, ex + er_big, eye_y + er_big], fill=ink)
            draw.ellipse([ex - 11, eye_y - 12, ex - 1, eye_y - 2], fill=(255, 255, 255))
            draw.ellipse([ex + 3, eye_y + 4, ex + 9, eye_y + 10], fill=(255, 255, 255))
        draw.arc([cx - int(18 * scale), cy + int(34 * scale), cx + int(18 * scale), cy + int(52 * scale)], start=190, end=350, fill=ink, width=5)
    else:
        # Confident smirk / deadpan camera stare
        for side in (-1, 1):
            ex = cx + side * eye_dx
            draw.ellipse([ex - 11, eye_y - 11, ex + 11, eye_y + 11], fill=ink)
        if expression == "confident_smirk":
            draw.arc([cx - int(22 * scale), cy + int(22 * scale), cx + int(24 * scale), cy + int(44 * scale)], start=10, end=170, fill=ink, width=5)
        else:
            draw.line([(cx - int(22 * scale), cy + int(36 * scale)), (cx + int(22 * scale), cy + int(36 * scale))], fill=ink, width=5)

    if prof["glasses"]:
        gr = int(28 * scale)
        draw.rectangle([cx - eye_dx - gr, eye_y - gr, cx - eye_dx + gr, eye_y + gr], outline=ink, width=max(4, int(6 * scale)))
        draw.rectangle([cx + eye_dx - gr, eye_y - gr, cx + eye_dx + gr, eye_y + gr], outline=ink, width=max(4, int(6 * scale)))
        draw.line([(cx - eye_dx + gr, eye_y), (cx + eye_dx - gr, eye_y)], fill=ink, width=max(4, int(6 * scale)))


def _render_reference_webcomic_fallback(characters, env_key, start_grade, expression, beat_idx, out_png_path):
    """Renders lived-in 2D interior + cel-shaded round-head stick characters + realistic props."""
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    img = Image.new("RGB", (W, H), color=env["wall"])
    draw = ImageDraw.Draw(img)

    # 1. Realistic Lived-In Environment Background (Never Plain Solid Color)
    if env_key == "living_room_window":
        # Window showing yellow house exterior & stacked cardboard delivery boxes
        draw.rectangle([110, 360, W - 110, 960], fill=(168, 214, 248), outline=ink, width=8)
        draw.polygon([(220, 620), (540, 440), (860, 620)], fill=(196, 98, 72), outline=ink)
        draw.rectangle([260, 620, 820, 956], fill=(246, 214, 118), outline=ink, width=6)
        # Delivery boxes piling up outside window across beats
        for b in range(min(4, beat_idx + 1)):
            bx = 520 + (b % 2) * 110
            by = 850 - (b // 2) * 95
            draw.rectangle([bx, by, bx + 115, by + 95], fill=(198, 152, 98), outline=ink, width=5)
        draw.line([(W // 2, 360), (W // 2, 960)], fill=ink, width=8)
        # Slate-blue living room couch in foreground
        draw.rounded_rectangle([80, 1080, W - 80, 1460], radius=36, fill=env["surface"], outline=ink, width=8)
    elif env_key == "overcast_bedroom":
        # Framed wall art + pendant lamp + bed headboard & blanket
        draw.rectangle([170, 410, 390, 640], fill=(238, 240, 244), outline=ink, width=6)
        draw.rectangle([W - 390, 410, W - 170, 640], fill=(238, 240, 244), outline=ink, width=6)
        draw.rectangle([120, 840, W - 120, 1180], fill=(176, 162, 146), outline=ink, width=7)
        draw.rounded_rectangle([90, 1120, W - 90, 1540], radius=32, fill=env["surface"], outline=ink, width=8)
    elif env_key == "midnight_car_cabin":
        # Windshield + dashboard + steering wheel
        draw.rounded_rectangle([90, 380, W - 90, 980], radius=48, fill=(22, 32, 54), outline=ink, width=8)
        draw.ellipse([740, 470, 810, 540], fill=(255, 224, 148))
        draw.rounded_rectangle([60, 1080, W - 60, 1540], radius=42, fill=env["surface"], outline=ink, width=8)
        draw.ellipse([240, 1020, 480, 1260], outline=(14, 16, 20), width=18)
    else:
        # Warm Amber Desk / Kitchen Counter with wall sconce glow, potted plant & red mug
        draw.ellipse([W // 2 - 280, 380, W // 2 + 280, 940], fill=(236, 178, 112))
        # Potted plant on left
        draw.polygon([(140, 1020), (240, 1020), (222, 1140), (158, 1140)], fill=(178, 92, 64), outline=ink)
        draw.ellipse([135, 920, 245, 1030], fill=(76, 142, 82), outline=ink, width=5)
        # Desk / Counter surface
        draw.rectangle([0, 1135, W, H], fill=env["surface"])
        draw.line([(0, 1135), (W, 1135)], fill=ink, width=8)
        # Red ceramic mug on right
        draw.rounded_rectangle([830, 1055, 910, 1135], radius=12, fill=env["accent_prop"], outline=ink, width=5)

    # 2. Characters (1 to 4 cel-shaded round-head stickmen)
    count = max(1, min(4, len(characters)))
    # Beat 2 (idx=2) zooms closer on the lead character's reaction face
    if beat_idx == 2:
        _draw_reference_character(draw, characters[0], W // 2, 860, 1.38, expression, beat_idx)
    else:
        spacing = min(245, (W - 180) // count)
        start_x = (W // 2) - ((count - 1) * spacing) // 2
        scale = 1.04 if count == 1 else (0.92 if count == 2 else (0.80 if count == 3 else 0.72))
        for idx, name in enumerate(characters[:4]):
            cx = start_x + idx * spacing
            cy = 840 + (idx % 2) * 16
            expr = expression if idx == 0 else ("deadpan_camera_stare" if beat_idx == 3 else "exhausted_half_lidded")
            _draw_reference_character(draw, name, cx, cy, scale, expr, beat_idx)

    img.save(out_png_path, format="PNG")


def generate_scene_illustration(scene_data, characters, env_key, setting_continuity, beat_idx, total_beats, out_png_path):
    style_key = scene_data.get("art_style_key", "reference_webcomic_2d")
    style_desc = ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"])["prompt"]
    cast_desc = "; ".join(CAST_IDENTITY[c]["visual"] for c in characters if c in CAST_IDENTITY)
    grade_name = scene_data.get("start_grade", "warm_amber_desk")
    expr = scene_data.get("expression", "exhausted_half_lidded")

    full_prompt = (
        f"{style_desc}. "
        f"CHARACTERS ({len(characters)} total, MUST KEEP IDENTICAL PROPORTIONS & FEATURES ACROSS ALL {total_beats} SCENES): {cast_desc}. "
        f"SETTING CONTINUITY: {setting_continuity}. "
        f"Beat {beat_idx + 1}/{total_beats} Action & Facial Acting (expression={expr.replace('_', ' ')}): {scene_data['visual_prompt']}. "
        f"Lighting & Environment Color Grade: {grade_name.replace('_', ' ')}. "
        "Frame characters clearly in the middle 55% of the vertical 9:16 canvas so the top 24% and bottom 20% stay uncluttered for captions. "
        "Strictly NO text, NO words, NO numbers, NO speech bubbles inside the illustration."
    )

    # 1. Try native Gemini Image models first (reliable on standard Gemini API keys)
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
                for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        b64 = part["inlineData"]["data"]
                        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                        img.save(out_png_path, format="PNG")
                        print(f"Generated Beat {beat_idx + 1}/{total_beats} artwork via {img_model} (cast={characters})")
                        return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:180]
            print(f"{img_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    # 2. Secondary Imagen fallback
    for imagen_model in ["imagen-4.0-fast-generate-001", "imagen-4.0-generate-001"]:
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
                print(f"Generated Beat {beat_idx + 1}/{total_beats} artwork via {imagen_model} (cast={characters})")
                return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:180]
            print(f"{imagen_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{imagen_model} skipped ({e})")

    # 3. Reference-style cel-shaded round-head stickman + lived-in room fallback
    print(f"Using reference-style webcomic vector renderer for Beat {beat_idx + 1}/{total_beats} (cast={characters})")
    _render_reference_webcomic_fallback(characters, env_key, grade_name, expr, beat_idx, out_png_path)


# ==============================================================================
# 5. LYRIA MUSIC + AUDIO-REACTIVE SFX WITH MUSIC DUCKING
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
        "-af", f"volume=0.80,afade=t=in:st=0:d=0.30,afade=t=out:st={max(0.5, duration_sec - 0.8):.3f}:d=0.8",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.28) * math.pi)
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * env * 0.30
    if cue == "record_scratch":
        env = math.exp(-dt * 6.0)
        freq = 660.0 * math.exp(-dt * 5.2) + 95.0 * math.sin(dt * 95.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.44
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.5)
        freq = 74.0 * math.exp(-dt * 1.7)
        return math.sin(2 * math.pi * freq * dt) * env * 0.56
    if cue == "alarm_buzz":
        pulse = 1.0 if (int(dt * 14) % 2 == 0) else 0.15
        env = math.exp(-dt * 3.0) * pulse
        return (math.sin(2 * math.pi * 880.0 * dt) + 0.5 * math.sin(2 * math.pi * 1320.0 * dt)) * env * 0.26
    if cue == "riser_hit":
        if dt < 0.35:
            return math.sin(2 * math.pi * (220 + 1300 * dt) * dt) * (dt / 0.35) * 0.30
        env = math.exp(-(dt - 0.35) * 7.5)
        return math.sin(2 * math.pi * 64.0 * dt) * env * 0.50
    env = math.exp(-dt * 15.0)
    return math.sin(2 * math.pi * 987.77 * dt) * env * 0.28


def build_director_audio(music_prompt, bpm, scenes, beat_starts, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating playful comedic pluck synth bed...")
        sr = 48000
        total_samples = int(sr * duration_sec)
        chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
        bar_len = int(sr * 2.2)
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
                if start_t <= t <= start_t + 0.62:
                    sig += _synth_cue_sample(cue_name, t - start_t)
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            frames.extend(struct.pack("<hh", s, s))
        wf.writeframes(frames)

    # Sidechain-style ducking so punchline SFX & alarm buzzes cut cleanly through the music bed
    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex",
        "[1:a]asplit=2[sfx_sc][sfx_mix];"
        "[0:a][sfx_sc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=220[ducked_bed];"
        "[ducked_bed][sfx_mix]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# 6. CAMERA MOVEMENTS, MICRO-ANIMATED PROPS & UPPER-THIRD HOOK LAYOUT
# ==============================================================================
def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _lerp_color(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def build_vignette_mask(strength=0.18):
    small_w, small_h = 270, 480
    vig = Image.new("L", (small_w, small_h), 0)
    px = vig.load()
    cx, cy = small_w / 2.0, small_h * 0.50
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_d
            px[x, y] = int(max(0.0, min(255.0, (d ** 2.4) * 255.0 * strength)))
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def build_ambient_glow_mask(strength=0.14):
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


def generate_particle_seeds(count=26):
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
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
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

    style_fx = ART_STYLES.get(sc.get("art_style_key", "reference_webcomic_2d"), {}).get("overlay_fx", "none")
    prop_fx = sc.get("prop_overlay", "none")
    env_fx = sc.get("env_effect", "none")

    if style_fx != "none" or prop_fx != "none" or env_fx != "none":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        # Reference Video 2: Radial manga speed-lines on bloodshot shock frame
        if style_fx == "speed_lines" or sc.get("expression") == "bloodshot_shock":
            for i in range(32):
                ang = (i / 32.0) * math.pi * 2 + (t * 0.4)
                r0 = 420 + int(math.sin(t * 16.0 + i) * 32)
                r1 = 1080
                x0, y0 = int(W // 2 + math.cos(ang) * r0), int(H // 2 + math.sin(ang) * r0)
                x1, y1 = int(W // 2 + math.cos(ang) * r1), int(H // 2 + math.sin(ang) * r1)
                odraw.line([(x0, y0), (x1, y1)], fill=(18, 18, 22, 85), width=4)

        # Reference micro-animated props (sweat drops, vibrating phone arcs, flying delivery box, Zzz)
        if prop_fx == "sweat_drops":
            drop_y = int((t * 110) % 70)
            for sx, base_y in [(390, 740), (690, 760), (355, 810)]:
                yy = base_y + drop_y
                odraw.ellipse([sx - 8, yy - 13, sx + 8, yy + 13], fill=(165, 226, 255, 220), outline=(18, 18, 22, 220), width=3)
        elif prop_fx == "phone_vibrate_arcs":
            shake = int(math.sin(t * 42.0) * 10)
            px, py = 740 + shake, 1060
            odraw.rounded_rectangle([px - 36, py - 62, px + 36, py + 62], radius=14, fill=(32, 36, 46, 240), outline=(18, 18, 22, 255), width=4)
            odraw.rounded_rectangle([px - 28, py - 48, px + 28, py + 48], radius=8, fill=(138, 224, 255, 240))
            for r_arc in (76, 94):
                odraw.arc([px - r_arc, py - r_arc, px + r_arc, py + r_arc], start=-35, end=35, fill=(255, 255, 255, 220), width=4)
                odraw.arc([px - r_arc, py - r_arc, px + r_arc, py + r_arc], start=145, end=215, fill=(255, 255, 255, 220), width=4)
        elif prop_fx == "delivery_box_drop":
            # Reference Video 4: Delivery box arcing into frame and landing
            arc_p = min(1.0, local_p * 1.8)
            bx = int(140 + arc_p * 620)
            by = int(820 + (arc_p ** 2) * 340)
            odraw.rectangle([bx, by, bx + 130, by + 105], fill=(204, 156, 98, 245), outline=(18, 18, 22, 255), width=5)
            odraw.line([(bx, by + 35), (bx + 130, by + 35)], fill=(18, 18, 22, 220), width=4)
        elif prop_fx == "zzz_float":
            z_font = _load_font(36)
            for idx_z in range(3):
                zp = (t * 0.6 + idx_z * 0.33) % 1.0
                zx = int(660 + idx_z * 34 + math.sin(zp * 4.0) * 12)
                zy = int(760 - zp * 130)
                za = int(230 * (1.0 - zp))
                odraw.text((zx, zy), "Z", font=z_font, fill=(255, 255, 255, za), stroke_width=4, stroke_fill=(18, 18, 22, za))

        base_alpha = 255 * VISUAL_TUNING["particle_opacity"]
        if env_fx == "screen_glow":
            pulse = int(34 + 20 * math.sin(t * 4.5))
            odraw.ellipse([W // 2 - 240, 740, W // 2 + 240, 1220], fill=(135, 215, 255, pulse))
        elif env_fx in ("rain", "sparks", "confetti", "dust"):
            for p in particle_seeds:
                depth = p["depth"]
                spd = p["speed"] * (0.6 + 0.5 * depth)
                p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
                if env_fx == "rain":
                    px = int(((p["x"] - t * 0.07 * spd) % 1.0) * W)
                    py = int(((p["y"] + t * 0.52 * spd) % 1.0) * H)
                    odraw.line([(px, py), (px - 6, py + 26)], fill=(195, 225, 255, int(p_alpha * 0.72)), width=2)
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
            zoom = 1.0 + (max_z * 1.25) * _ease_out_quart(local_p / 0.10)
        else:
            zoom = (1.0 + max_z * 1.25) - (max_z * 0.22 * _ease_in_out_sine((local_p - 0.10) / 0.90))
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
    elif move == "handheld_struggle":
        x0 = max(0, min(max_dx, (max_dx // 2) + int(math.sin(t * 18.0) * min(12, max_dx // 2))))
        y0 = max(0, min(max_dy, (max_dy // 2) + int(math.cos(t * 15.0) * min(10, max_dy // 2))))
    else:
        x0 = max_dx // 2
        y0 = max_dy // 2

    return base_img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)


def apply_director_transition(prev_frame, curr_frame, transition_name, tr_p):
    eased = _ease_out_quart(tr_p)

    if transition_name == "hard_cut":
        return curr_frame

    if transition_name == "smash_zoom_cut":
        scale = 1.14 - 0.14 * eased
        cw, ch = int(W / scale), int(H / scale)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        return curr_frame.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)

    if transition_name in ("whip_pan_left", "whip_pan_right"):
        direction = -1 if transition_name == "whip_pan_left" else 1
        shift = int((1.0 - eased) * W * direction)
        canvas = Image.new("RGB", (W, H), (14, 16, 22))
        canvas.paste(prev_frame, (shift - W * direction, 0))
        canvas.paste(curr_frame, (shift, 0))
        return canvas

    if transition_name == "fade_to_black_cut":
        # Reference Video 3: Lights-out black dip between night and morning
        if tr_p < 0.5:
            return Image.blend(prev_frame, Image.new("RGB", (W, H), (8, 8, 12)), tr_p * 2.0)
        return Image.blend(Image.new("RGB", (W, H), (8, 8, 12)), curr_frame, (tr_p - 0.5) * 2.0)

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


def draw_reference_overlays(frame, top_hook, sc, beat_idx, total_beats, scene_t, beat_dur, t, handle):
    """Reference-style layout: Upper-third POV hook card + ticking clock beneath + clean open stage."""
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, beat_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg = g2["card_bg"]
    c_fg = g2["card_fg"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 1. Upper-Third POV Hook Banner (Matches Reference Videos 1, 2 & 4)
    hook_str = (top_hook or "").strip()
    if hook_str:
        ent = _ease_out_quart(min(1.0, t / 0.25))
        hook_font = _load_font(40)
        wrapped_hook = textwrap.fill(hook_str, width=30)
        h_lines = wrapped_hook.split("\n")
        box_h = 34 + len(h_lines) * 50
        bx0, by0 = 84, 130 + int((1.0 - ent) * -12)
        bx1 = W - 84
        alpha = int(246 * ent)
        odraw.rounded_rectangle([bx0, by0, bx1, by0 + box_h], radius=24, fill=(255, 253, 248, alpha), outline=(18, 18, 22, alpha), width=5)
        odraw.multiline_text((W // 2, by0 + box_h // 2), wrapped_hook, font=hook_font, fill=(18, 18, 22, alpha), anchor="mm", align="center", spacing=8)

        # 2. Live Escalating Timestamp Pill Directly Beneath Hook (Reference Video 2: 6:55am -> 12:34pm)
        clock_label = (sc.get("clock_label") or "").strip()
        if clock_label:
            clk_font = _load_font(32)
            cbbox = odraw.textbbox((0, 0), clock_label, font=clk_font)
            cw = (cbbox[2] - cbbox[0]) + 48
            ch = 48
            cx0 = (W - cw) // 2
            cy0 = by0 + box_h + 14
            odraw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=24, fill=(18, 20, 28, 238), outline=(acc[0], acc[1], acc[2], 240), width=3)
            odraw.text((W // 2, cy0 + ch // 2), clock_label, font=clk_font, fill=(acc[0], acc[1], acc[2], 255), anchor="mm")

    # 3. Optional Concise Bottom Reaction Caption (Only drawn when non-empty so visual-only beats stay pure)
    bottom_caption = (sc.get("bottom_caption") or "").strip()
    if bottom_caption:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.18))
        time_left = max(0.0, beat_dur - scene_t)
        cap_out = 1.0 if (beat_idx == total_beats - 1 or time_left > 0.12) else max(0.0, time_left / 0.12)
        cap_alpha = int(248 * cap_in * cap_out)
        cap_font = _load_font(40)
        wrapped = textwrap.fill(bottom_caption, width=30)
        lines = wrapped.split("\n")
        box_h = 46 + len(lines) * 52
        x0, y0 = 96, 1385 + int((1.0 - cap_in) * 10)
        x1, y1 = W - 96, y0 + box_h
        odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(c_bg[0], c_bg[1], c_bg[2], min(246, cap_alpha)), outline=(acc[0], acc[1], acc[2], cap_alpha), width=3)
        odraw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=10)

    # 4. Handle Watermark in Instagram Safe Zone
    handle_font = _load_font(28)
    odraw.text((W // 2, 1625), handle, font=handle_font, fill=(255, 255, 255, 235), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_director_reel(page_cfg, script_data, seed, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:4]
    total_beats = len(scenes)
    characters = seed["characters"]
    env_key = script_data.get("environment_key", seed["scenario"]["env"])
    setting_continuity = script_data.get("setting_continuity", ENVIRONMENT_PRESETS[env_key]["desc"])

    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        generate_scene_illustration(
            sc, characters, env_key, setting_continuity, idx, total_beats, art_path
        )
        scene_imgs.append(Image.open(art_path).convert("RGB"))

    beat_durations = compute_beat_durations(scenes)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t
    print(f"Reference-style Reel timing ({total_dur:.2f}s total): {beat_durations}")

    final_wav = tmp_dir / "final_director.wav"
    build_director_audio(
        script_data.get("music_prompt", "playful lo-fi indie comedy loop instrumental"),
        script_data.get("music_bpm", 104),
        scenes,
        beat_starts,
        total_dur,
        final_wav
    )

    total_frames = int(total_dur * FPS)
    top_hook = script_data.get("top_hook", seed["scenario"]["hook"])
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
    particle_seeds = generate_particle_seeds(26)
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
        g_curr = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
        bar_x = int(W * prog)
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=g_curr["accent"])

        frame = draw_reference_overlays(
            frame=frame,
            top_hook=top_hook,
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
    print(f"Rendered Reference-Style Reel ({total_dur:.1f}s, {total_beats} beats): {out_mp4}")


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
        time_slot_vibe = "MORNING SLOT: Snoozing alarms, waking up late in panic, or morning coffee habits."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT: Trying to save money at home, online delivery temptations, or checking bank balance."
    else:
        time_slot_vibe = "EVENING/NIGHT SLOT: Sitting in the parked car after work, scrolling in bed at 2 AM, or group chat dinner debates."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('top_hook', '')}" for h in recent_history if h.get("top_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history)
        scen = seed["scenario"]
        cast_descriptions = "\n".join(
            f"- {c}: {CAST_IDENTITY[c]['archetype']} | Visual: {CAST_IDENTITY[c]['visual']}"
            for c in seed["characters"]
        )

        prompt = (
            f"You are a 2D Webcomic Animation Director for {page['handle']}.\n"
            f"CHANNEL IDENTITY: {page['domain']}\n\n"
            "### MANDATORY CREATIVE DIRECTION BRIEF\n"
            f"- Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Characters (NEVER CHANGE NAMES OR PROPORTIONS):\n{cast_descriptions}\n"
            f"- Upper-Third Hook Concept: {scen['hook']}\n"
            f"- Story Seed: {scen['story_seed']}\n"
            f"- Environment Key: {scen['env']} ({ENVIRONMENT_PRESETS[scen['env']]['desc']})\n"
            f"- Suggested Ticking Clock Progression: {scen['clocks']}\n"
            f"- Art Style: {seed['art_style_key']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only if natural): \n{trends}\n"
            f"- Previously Used Hooks (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### VISUAL STORYTELLING & MICRO-ACTING RULES\n"
            "1. SHOW, DON'T OVER-WRITE: Put the setup in 'top_hook' (e.g. 'Pov: Me trying to save money 😂'). Keep 'bottom_caption' ultra-short (0 to 8 words max) or empty string \"\" so the character's facial acting and props tell the joke!\n"
            "2. 4-BEAT ESCALATION WITH TICKING CLOCK: Escalate across 4 beats using 'clock_label' (e.g. '6:55am' -> '7:10am' -> '7:18am' -> '12:34pm') and distinct 'expression' states ('exhausted_half_lidded', 'smug_snooze', 'sweat_grit', 'guilty_puppy_eyes', 'bloodshot_shock').\n"
            "3. REALISTIC LIGHTING SHIFTS: Use natural lighting transitions ('warm_amber_desk', 'overcast_morning_bedroom', 'dim_night_phone_glow', 'golden_morning_sunlight', 'crimson_panic_shock').\n"
            "4. CAMERA VARIETY: Use a tight face close-up ('snap_zoom_face') on Beat 3 and a pulled-back comedic reveal ('pull_back_reveal') on Beat 4.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "top_hook": "' + scen["hook"] + '",\n'
            '  "environment_key": "' + scen["env"] + '",\n'
            '  "setting_continuity": "' + ENVIRONMENT_PRESETS[scen["env"]]["desc"] + '",\n'
            '  "music_prompt": "Playful lo-fi indie marimba and acoustic guitar comedy loop instrumental",\n'
            '  "music_bpm": 106,\n'
            '  "scenes": [\n'
            '    {"clock_label": "' + scen["clocks"][0] + '", "bottom_caption": "", "expression": "exhausted_half_lidded", "prop_overlay": "none", "visual_prompt": "Beat 1 medium shot action & pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "warm_amber_desk", "end_grade": "warm_amber_desk", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "dust", "sfx_cue": "pop_ding"},\n'
            '    {"clock_label": "' + scen["clocks"][1] + '", "bottom_caption": "Short 3-6 word line", "expression": "smug_snooze", "prop_overlay": "phone_vibrate_arcs", "visual_prompt": "Beat 2 close-up action & pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "overcast_morning_bedroom", "end_grade": "overcast_morning_bedroom", "camera_move": "pan_follow_right", "transition_in": "blur_dissolve", "env_effect": "screen_glow", "sfx_cue": "alarm_buzz"},\n'
            '    {"clock_label": "' + scen["clocks"][2] + '", "bottom_caption": "Short 3-6 word reaction", "expression": "sweat_grit", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 3 tight face close-up sweating & struggling, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "dim_night_phone_glow", "end_grade": "crimson_panic_shock", "camera_move": "snap_zoom_face", "transition_in": "whip_pan_left", "env_effect": "none", "sfx_cue": "record_scratch"},\n'
            '    {"clock_label": "' + scen["clocks"][3] + '", "bottom_caption": "Short punchline", "expression": "bloodshot_shock", "prop_overlay": "none", "visual_prompt": "Beat 4 pulled-back comedic reveal with props, NO text", "art_style_key": "manga_shock_comic", "start_grade": "crimson_panic_shock", "end_grade": "golden_morning_sunlight", "camera_move": "pull_back_reveal", "transition_in": "smash_zoom_cut", "env_effect": "none", "sfx_cue": "vine_boom_sub"}\n'
            "  ],\n"
            '  "ig_caption": "Punchy relatable caption that invites followers to tag a friend",\n'
            '  "pinned_comment": "Specific relatable question for the comments"\n'
            "}\n"
            f"Allowed environment_key: {list(ENVIRONMENT_PRESETS.keys())}\n"
            f"Allowed expression: {FACIAL_EXPRESSIONS}\n"
            f"Allowed prop_overlay: {ALL_PROP_OVERLAYS}\n"
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
        full_story_text = "\n".join(
            f"Beat {i+1} [{s.get('clock_label', '')}] ({s.get('expression', '')}): {s.get('bottom_caption', '')}"
            for i, s in enumerate(script_data["scenes"][:4])
        )
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Cast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nEnvironment: {script_data.get('environment_key', '')}\nHook: {script_data.get('top_hook', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "top_hook": script_data.get("top_hook", ""),
            "cast_mode": seed["cast_mode"],
            "characters": seed["characters"],
            "environment_key": script_data.get("environment_key", ""),
            "art_style_key": seed["art_style_key"],
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
