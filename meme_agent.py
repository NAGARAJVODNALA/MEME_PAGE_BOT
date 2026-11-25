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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920
SS = 2  # 2x Supersampling (2160x3840 -> 1080x1920 Lanczos) for razor-sharp Flash/webcomic ink lines

# ==============================================================================
# CREATIVE DIRECTOR & FULL-BODY ANIMATION TUNING CONTROLS (FAST REELS PACING)
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.16,      # Subtle edge depth without muddying cel-shaded faces
    "color_tint_strength": 0.08,    # Clean environment color wash
    "ambient_glow_strength": 0.15,  # Warm lamp / window / phone screen rim light
    "particle_opacity": 0.28,       # Gentle dust motes / sparks / rain
    "max_zoom_delta": 0.10,         # Punchier comedic framing & snap-zooms
    "transition_sec": 0.16,         # Snappy comedic cut / whip-pan timing
    "enable_blur_transition": True,
    "min_beat_sec": 1.85,           # Fast viral Reels pacing (~8.5s total runtime)
    "max_beat_sec": 2.65,           # Prevents viewer drop-off between beats
    "words_per_sec": 3.4            # Crisp short-form reading speed
}

# ==============================================================================
# 1. REFERENCE-STYLE CHARACTER ROSTER (CEL-SHADED HEAD + ARTICULATED STICK BODY)
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Confident Instigator (smug grin, effortless optimism, talks himself into bad ideas)",
        "visual": (
            "Phil (2D webcomic character with large soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, wearing a curved terracotta/muted-olive baseball cap, confident smirk, "
            "thin black stick-figure body and articulated limbs with rounded black mitten hands)"
        ),
        "cap_color": (166, 98, 72),
        "beard": False,
        "glasses": False,
        "satchel": False
    },
    "Alan": {
        "archetype": "The Deadpan Wildcard (earnest wide eyes, 2:30 AM life theories, unexpectedly loyal)",
        "visual": (
            "Alan (2D webcomic character with large soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, scruffy brown beard on lower jaw, wide earnest deadpan eyes, "
            "thin black stick-figure body with a brown crossbody satchel strap and rounded black mitten hands)"
        ),
        "cap_color": None,
        "beard": True,
        "glasses": False,
        "satchel": True
    },
    "Stu": {
        "archetype": "The Relatable Overthinker (checks bank app with one eye open, sweats over alarms and emails)",
        "visual": (
            "Stu (2D webcomic character with large soft warm-gray cel-shaded round head #D8D5D0, "
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
            "Doug (2D webcomic character with large soft warm-gray cel-shaded round head #D8D5D0, "
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
        "desc": "1 solo character in a hyper-relatable internal monologue or everyday chaos moment",
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

ALL_BODY_ACTIONS = [
    "sleep_breathe_toss",
    "phone_scroll_lean",
    "shock_recoil",
    "struggle_pull",
    "walk_stride",
    "slouch_sigh",
    "celebrate_groove"
]

# ==============================================================================
# 2. REALITY-ANCHORED ENVIRONMENTS, ART STYLES & HYPER-SPECIFIC SCENARIOS
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "warm_desk_lamp": {
        "desc": "Warm amber-lit home desk with walnut wood surface, wall sconce lamp, potted green plant, red ceramic mug, and glowing laptop",
        "wall": (196, 132, 84),
        "surface": (118, 72, 42),
        "accent_prop": (184, 58, 52)
    },
    "overcast_bedroom": {
        "desc": "Cozy minimalist bedroom with soft slate-gray blanket, folded white top sheet, framed wall art, and overhead pendant lamp",
        "wall": (198, 204, 212),
        "night_wall": (46, 56, 82),
        "surface": (136, 146, 160),
        "accent_prop": (238, 240, 246)
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
            "Clean 2D webcomic animation background plate, hand-drawn ink lines with warm cel-shaded interior lighting, "
            "cozy minimalist aesthetic, NO characters, NO people, NO text, NO words"
        ),
        "hashtags": ["#webcomic", "#2danimation", "#relatable"]
    },
    "cozy_lamp_cartoon": {
        "prompt": (
            "Warm 2D animated short background room with rich amber lamp lighting, clean ink outlines, "
            "desktop props (mugs, notebooks, plant), NO characters, NO people, NO text"
        ),
        "hashtags": ["#animatedshorts", "#relatablememes", "#2danimation"]
    },
    "suburban_cel_toon": {
        "prompt": (
            "Clean daylight 2D animated comedy interior background with crisp ink lines and soft cel shading, "
            "NO characters, NO people, NO text"
        ),
        "hashtags": ["#cartoonmemes", "#sliceoflife", "#funnyreels"]
    }
}

RELATABLE_SCENARIOS = [
    {
        "hook": "closing 19 browser tabs at 5:01 PM like I just defused a bomb",
        "env": "warm_desk_lamp",
        "clocks": ["4:58 PM", "5:00 PM", "5:01 PM", "5:02 PM"],
        "story_seed": "Staring at an impossible work spreadsheet at 4:58 PM, furiously closing every browser tab at 5:01 PM, and instantly feeling like a retired millionaire"
    },
    {
        "hook": "checking my bank app with one eye half-closed on Sunday night",
        "env": "warm_desk_lamp",
        "clocks": ["9:12 PM", "9:13 PM", "9:14 PM", "9:15 PM"],
        "story_seed": "Saying 'I barely spent anything this weekend', sweating while FaceID unlocks the bank app, and seeing $14.82 left until Friday"
    },
    {
        "hook": "sitting in my parked car for 35 minutes after getting home",
        "env": "midnight_car_cabin",
        "clocks": ["6:12 PM", "6:24 PM", "6:38 PM", "6:47 PM"],
        "story_seed": "Pulling into the driveway after a long shift, turning off the engine, and staring into the void in total silence because stepping inside means adulthood resumes"
    },
    {
        "hook": "setting 6 alarms for 8 AM knowing I will negotiate with every single one",
        "env": "overcast_bedroom",
        "clocks": ["6:55 AM", "7:10 AM", "7:18 AM", "11:42 AM"],
        "story_seed": "Smugly snoozing four consecutive alarms thinking 'I still have plenty of time', then waking up in bloodshot shock at 11:42 AM"
    },
    {
        "hook": "telling myself I'm staying home to save money while packages keep arriving",
        "env": "living_room_window",
        "clocks": ["1:15 PM", "2:40 PM", "4:05 PM", "5:30 PM"],
        "story_seed": "Refusing to go out to save $20, while three separate online impulse-buy boxes thud onto the porch outside the window"
    },
    {
        "hook": "me at 2:47 AM suddenly remembering an awkward sentence I said in 2017",
        "env": "overcast_bedroom",
        "clocks": ["11:00 PM", "1:15 AM", "2:47 AM", "3:30 AM"],
        "story_seed": "Finally getting comfortable to sleep early when the brain replays a 9-year-old embarrassing conversation in 4K Ultra HD"
    },
    {
        "hook": "putting on a 45-minute YouTube video before taking a single bite of food",
        "env": "kitchen_counter",
        "clocks": ["7:10 PM", "7:18 PM", "7:26 PM", "7:27 PM"],
        "story_seed": "Food is hot and ready, refusing to eat until finding the exact right video, and finishing the entire meal before the sponsor intro ends"
    },
    {
        "hook": "saying 'I'm down for whatever' in the group chat and rejecting 6 ideas",
        "env": "living_room_window",
        "clocks": ["7:00 PM", "7:35 PM", "8:15 PM", "8:50 PM"],
        "story_seed": "47 messages of fake flexibility until everyone ends up ordering from the exact same spot as every Friday"
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
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.04, "sat": 0.90,
        "card_bg": (22, 24, 30), "card_fg": (248, 250, 255), "accent": (152, 196, 245)
    },
    "dim_night_phone_glow": {
        "tint": (58, 76, 112), "glow": (132, 214, 255), "contrast": 1.08, "sat": 0.94,
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
        "tint": (128, 136, 148), "glow": (184, 194, 208), "contrast": 1.04, "sat": 0.60,
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


def verify_runtime_environment():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg binary not found in PATH.")


def load_active_pages():
    cfg_path = pathlib.Path("pages.json")
    if cfg_path.exists():
        try:
            raw = cfg_path.read_text(encoding="utf-8").strip()
            if raw:
                pages = json.loads(raw)
                active = [p for p in pages if p.get("enabled")]
                if active:
                    return active
        except Exception as e:
            print(f"pages.json skipped ({e}), using default config")
    return [{
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "layout_mode": "v5_solo_pov",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Strictly relatable Gen-Z & millennial internal chaos, $14.82 bank checks, 5:01 PM tab closing, and 2:47 AM overthinking starring cel-shaded round-head stick characters",
        "art_style": "Clean 2D webcomic animation with cel-shaded warm-gray round heads, thick uniform black ink outlines, articulated stick limbs, black mitten hands, and lived-in interior backgrounds"
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
            "Sunday night bank app check before Monday morning",
            "Closing 19 work tabs at 5:01 PM sharp",
            "Sitting in the parked car after getting home"
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


def sample_creative_director_seed(recent_history, page_cfg):
    """Selects a fresh hyper-relatable scenario & cast lineup aligned with page layout_mode."""
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_hooks = {h.get("top_hook", "") for h in recent_history[-6:]}
    solo_bias = "solo" in (page_cfg.get("layout_mode", "") + page_cfg.get("domain", "")).lower()

    for _ in range(45):
        if solo_bias:
            cast_mode = "solo_pov" if random.random() < 0.80 else "classic_duo"
        else:
            cast_mode = random.choice(list(CAST_MODES.keys()))
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

    cast_mode = "solo_pov" if solo_bias else "classic_duo"
    return {
        "combo_key": f"ref_{int(time.time())}",
        "cast_mode": cast_mode,
        "characters": random.choice(CAST_MODES[cast_mode]["lineups"]),
        "scenario": random.choice(RELATABLE_SCENARIOS),
        "art_style_key": "reference_webcomic_2d"
    }


def compute_beat_durations(scenes):
    """Calculates snappy Reels retention timing (1.85s-2.65s per beat, ~8.5s total)."""
    durations = []
    for idx, sc in enumerate(scenes):
        words = len((sc.get("bottom_caption") or "").split())
        read_sec = words / VISUAL_TUNING["words_per_sec"]
        cushion = 1.35 if idx == len(scenes) - 1 else 1.15
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], read_sec + cushion)), 2)
        durations.append(dur)
    return durations


def validate_and_fix_plan(script_data, seed):
    """Enforces 4 visual beats, mid-beat expressions, full-body actions, and non-repeating cameras/transitions."""
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

    default_exprs = ["exhausted_half_lidded", "smug_snooze", "sweat_grit", "bloodshot_shock"]
    default_actions = ["sleep_breathe_toss", "phone_scroll_lean", "struggle_pull", "shock_recoil"]

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "warm_amber_desk" if idx < 3 else "crimson_panic_shock"
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]
        if sc.get("art_style_key") not in ART_STYLES:
            sc["art_style_key"] = seed["art_style_key"]

        expr_start = sc.get("expression") if sc.get("expression") in FACIAL_EXPRESSIONS else default_exprs[idx % len(default_exprs)]
        sc["expression"] = expr_start
        expr_end = sc.get("end_expression") if sc.get("end_expression") in FACIAL_EXPRESSIONS else expr_start
        sc["end_expression"] = expr_end

        if sc.get("body_action") not in ALL_BODY_ACTIONS:
            sc["body_action"] = default_actions[idx % len(default_actions)]
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
        if len(words) > 9:
            sc["bottom_caption"] = " ".join(words[:9])

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
    if len(chars) >= 2:
        dynamic_tags.extend(["#friendgroup", "#relatable"])
    else:
        dynamic_tags.extend(["#literallyme", "#adulting"])

    dynamic_tags.extend(["#wearechillclub", "#animatedshorts", "#funnyreels"])

    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 6:
            break

    body_str = "\n".join(text_body).strip() or "Tell me this isn't literally you."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    chars = seed["characters"]
    char_str = " and ".join(chars)
    scen = seed["scenario"]
    style_key = seed["art_style_key"]

    return {
        "top_hook": scen["hook"],
        "environment_key": scen["env"],
        "setting_continuity": ENVIRONMENT_PRESETS[scen["env"]]["desc"],
        "music_prompt": "Playful lo-fi indie marimba and acoustic guitar comedy loop instrumental",
        "music_bpm": 112,
        "scenes": [
            {
                "clock_label": scen["clocks"][0],
                "bottom_caption": "I barely spent anything this weekend.",
                "expression": "confident_smirk",
                "end_expression": "smug_snooze",
                "body_action": "slouch_sigh",
                "prop_overlay": "none",
                "visual_prompt": f"Medium shot of {char_str} in {scen['env']}, relaxed confident smirk, NO text",
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
                "bottom_caption": "Let me just check real quick...",
                "expression": "exhausted_half_lidded",
                "end_expression": "sweat_grit",
                "body_action": "phone_scroll_lean",
                "prop_overlay": "phone_vibrate_arcs",
                "visual_prompt": f"Close-up of {char_str} holding a glowing phone nervously, NO text",
                "art_style_key": style_key,
                "start_grade": "dim_night_phone_glow",
                "end_grade": "dim_night_phone_glow",
                "camera_move": "pan_follow_right",
                "transition_in": "blur_dissolve",
                "env_effect": "screen_glow",
                "sfx_cue": "alarm_buzz"
            },
            {
                "clock_label": scen["clocks"][2],
                "bottom_caption": "Available balance: $14.82",
                "expression": "sweat_grit",
                "end_expression": "bloodshot_shock",
                "body_action": "struggle_pull",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Extreme face close-up of {char_str} sweating in total panic, NO text",
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
                "bottom_caption": "Suddenly I'm not even hungry.",
                "expression": "bloodshot_shock",
                "end_expression": "deadpan_camera_stare",
                "body_action": "shock_recoil",
                "prop_overlay": "none",
                "visual_prompt": f"Pulled-back reveal of {char_str} staring deadpan at camera, NO text",
                "art_style_key": style_key,
                "start_grade": "crimson_panic_shock",
                "end_grade": "desaturated_gloom",
                "camera_move": "pull_back_reveal",
                "transition_in": "smash_zoom_cut",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": f"{scen['hook']} — every single Sunday night.",
        "pinned_comment": "What is the lowest balance you've ever seen before payday?"
    }


def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def ask_gemini_script(prompt, seed):
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    last_err = "Unknown error"

    for model in models:
        url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.92,
                    "maxOutputTokens": 2400,
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
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = _extract_json_object(raw_text)
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 4:
                        print(f"Generated full-body articulated script with {model}")
                        return validate_and_fix_plan(parsed, seed)
                    last_err = f"{model} returned incomplete JSON"
                    print(last_err)
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                last_err = f"{model} ParseError: {e}"
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
                    time.sleep(3 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} Network/Timeout: {e}"
                print(last_err)
                time.sleep(2)
                continue

    print(f"All Gemini text endpoints busy ({last_err}); using local articulated script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. 2X SUPERSAMPLED 24FPS VECTOR-CRISP ANIMATOR + OPTIONAL AI ROOM PLATES
# ==============================================================================
def _is_night_scene(sc):
    clk = (sc.get("clock_label") or "").upper()
    grade = sc.get("start_grade", "")
    if "dim_night" in grade or "midnight" in grade:
        return True
    if any(h in clk for h in ("10:", "11:", "12:1", "12:2", "12:3", "1:", "2:", "3:", "4:", "5:")):
        if "AM" in clk or ("PM" in clk and any(h in clk for h in ("10:", "11:"))):
            return True
    return False


def _try_generate_ai_room_plate(env_key, setting_continuity, style_key, out_bg_path):
    """Generates a single clean 2D hand-drawn background room plate (no characters) so 24fps rig moves smoothly on top."""
    style_desc = ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"])["prompt"]
    prompt = (
        f"{style_desc}. Environment: {setting_continuity}. "
        "Leave open space in the middle of the frame for a seated character. "
        "Strictly NO people, NO characters, NO faces, NO text, NO speech bubbles."
    )
    for img_model in ["gemini-2.5-flash-image"]:
        try:
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){img_model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                res = json.loads(resp.read().decode())
                for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        b64 = part["inlineData"]["data"]
                        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                        img.save(out_bg_path, format="PNG")
                        print(f"Generated AI 2D room plate via {img_model}")
                        return True
        except Exception as e:
            print(f"AI room plate skipped ({e}), using crisp procedural room")
    return False


def _render_environment_background(env_key, sc, beat_idx, out_bg_path):
    """Renders a 2x supersampled crisp vector-style room background layer."""
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)
    wall_col = env.get("night_wall", env["wall"]) if is_night else env["wall"]

    bw, bh = W * SS, H * SS
    img = Image.new("RGB", (bw, bh), color=wall_col)
    draw = ImageDraw.Draw(img)

    if env_key == "living_room_window":
        sky_col = (28, 42, 74) if is_night else (168, 214, 248)
        draw.rectangle([110 * SS, 360 * SS, (W - 110) * SS, 960 * SS], fill=sky_col, outline=ink, width=8 * SS)
        draw.polygon([(220 * SS, 620 * SS), (540 * SS, 440 * SS), (860 * SS, 620 * SS)], fill=(196, 98, 72), outline=ink)
        draw.rectangle([260 * SS, 620 * SS, 820 * SS, 956 * SS], fill=(246, 214, 118), outline=ink, width=6 * SS)
        for b in range(min(4, beat_idx + 1)):
            bx = (520 + (b % 2) * 110) * SS
            by = (850 - (b // 2) * 95) * SS
            draw.rectangle([bx, by, bx + 115 * SS, by + 95 * SS], fill=(198, 152, 98), outline=ink, width=5 * SS)
        draw.line([(bw // 2, 360 * SS), (bw // 2, 960 * SS)], fill=ink, width=8 * SS)
        draw.rounded_rectangle([80 * SS, 990 * SS, (W - 80) * SS, 1260 * SS], radius=34 * SS, fill=env["surface"], outline=ink, width=8 * SS)
    elif env_key == "overcast_bedroom":
        halo_col = (74, 88, 124) if is_night else (218, 224, 234)
        draw.ellipse([(W // 2 - 320) * SS, 320 * SS, (W // 2 + 320) * SS, 960 * SS], fill=halo_col)
        frame_bg = (196, 206, 224) if is_night else (242, 244, 248)
        for fx0 in (165, W - 395):
            fx1 = fx0 + 230
            draw.rectangle([fx0 * SS, 410 * SS, fx1 * SS, 635 * SS], fill=frame_bg, outline=ink, width=6 * SS)
            draw.polygon([((fx0 + 22) * SS, 628 * SS), ((fx0 + 95) * SS, 510 * SS), ((fx0 + 160) * SS, 628 * SS)], fill=(124, 138, 162), outline=ink)
            draw.polygon([((fx0 + 105) * SS, 628 * SS), ((fx0 + 165) * SS, 530 * SS), ((fx0 + 212) * SS, 628 * SS)], fill=(96, 110, 134), outline=ink)
            draw.ellipse([((fx0 + 155) * SS, 442 * SS), ((fx0 + 188) * SS, 475 * SS)], fill=(255, 222, 128), outline=ink, width=3 * SS)
        hb_col = (94, 82, 74) if is_night else (168, 152, 136)
        pillow_col = (176, 184, 202) if is_night else (244, 246, 250)
        draw.rounded_rectangle([110 * SS, 815 * SS, (W - 110) * SS, 1140 * SS], radius=24 * SS, fill=hb_col, outline=ink, width=7 * SS)
        draw.rounded_rectangle([180 * SS, 930 * SS, 510 * SS, 1085 * SS], radius=28 * SS, fill=pillow_col, outline=ink, width=5 * SS)
        draw.rounded_rectangle([570 * SS, 930 * SS, (W - 180) * SS, 1085 * SS], radius=28 * SS, fill=pillow_col, outline=ink, width=5 * SS)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([90 * SS, 380 * SS, (W - 90) * SS, 980 * SS], radius=48 * SS, fill=(22, 32, 54), outline=ink, width=8 * SS)
        draw.ellipse([740 * SS, 470 * SS, 810 * SS, 540 * SS], fill=(255, 224, 148))
        draw.rounded_rectangle([240 * SS, 790 * SS, 440 * SS, 1040 * SS], radius=28 * SS, fill=(38, 44, 56), outline=ink, width=6 * SS)
        draw.rounded_rectangle([640 * SS, 790 * SS, 840 * SS, 1040 * SS], radius=28 * SS, fill=(38, 44, 56), outline=ink, width=6 * SS)
    else:
        draw.ellipse([(W // 2 - 290) * SS, 360 * SS, (W // 2 + 290) * SS, 940 * SS], fill=(236, 178, 112))

    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _draw_articulated_character(draw, name, cx, cy, scale, expr, body_action, t, local_p, idx_in_cast):
    """Draws a 2x-supersampled full-body character with squash-and-stretch impact, bending joints & phone grip."""
    prof = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])
    ink = (18, 18, 22)
    head_fill = (216, 213, 208)
    head_shadow = (188, 185, 180)
    phase = idx_in_cast * 1.15

    # Squash-and-stretch entrance pop (first 0.16s of each beat gives snappy Flash animation feel)
    pop_p = min(1.0, local_p / 0.10)
    squash_x = 1.0 + math.sin(pop_p * math.pi) * 0.08
    squash_y = 1.0 - math.sin(pop_p * math.pi) * 0.07

    body_dx = 0
    body_dy = 0
    head_tilt_x = 0
    torso_lean_x = 0

    if body_action == "sleep_breathe_toss":
        breath = math.sin(t * 2.8 + phase)
        body_dy = int(breath * 6 * scale)
        head_tilt_x = int(math.sin(t * 1.5 + phase) * 8 * scale)
    elif body_action == "phone_scroll_lean":
        torso_lean_x = int(16 * scale)
        head_tilt_x = int(20 * scale)
        body_dy = int(math.sin(t * 3.4 + phase) * 3 * scale)
    elif body_action == "shock_recoil":
        recoil = math.sin(min(1.0, local_p * 4.0) * math.pi * 0.5)
        jitter = int(math.sin(t * 52.0 + phase) * 6 * scale)
        body_dy = int(-28 * recoil * scale) + jitter
        torso_lean_x = int(-20 * recoil * scale)
        head_tilt_x = int(-24 * recoil * scale)
    elif body_action == "struggle_pull":
        tug = math.sin(t * 15.0 + phase)
        body_dx = int(tug * 16 * scale)
        body_dy = int(abs(tug) * 9 * scale)
        torso_lean_x = int(-18 * scale + tug * 12 * scale)
    elif body_action == "walk_stride":
        stride = math.sin(t * 8.5 + phase)
        body_dy = int(-abs(stride) * 16 * scale)
        torso_lean_x = int(12 * scale)
    elif body_action == "celebrate_groove":
        bounce = abs(math.sin(t * 8.0 + phase))
        body_dy = int(-bounce * 22 * scale)
        head_tilt_x = int(math.sin(t * 4.0 + phase) * 14 * scale)
    else:
        sigh = _ease_in_out_sine(min(1.0, local_p * 1.6))
        body_dy = int(sigh * 15 * scale)
        torso_lean_x = int(-12 * sigh * scale)

    hx = int((cx + body_dx + head_tilt_x) * SS)
    hy = int((cy + body_dy) * SS)
    rx_head = int(106 * scale * squash_x * SS)
    ry_head = int(106 * scale * squash_y * SS)

    neck_x = int((cx + body_dx + torso_lean_x * 0.6) * SS)
    neck_y = hy + ry_head - 4 * SS
    hip_x = int((cx + body_dx) * SS)
    hip_y = neck_y + int(172 * scale * SS)
    limb_w = max(5 * SS, int(8 * scale * SS))
    mitten_r = max(10 * SS, int(15 * scale * SS))

    # Spine & Full Legs
    draw.line([(neck_x, neck_y), (hip_x, hip_y)], fill=ink, width=limb_w)

    if body_action == "walk_stride":
        swing = math.sin(t * 8.5 + phase) * 46 * scale * SS
        for side, s_mult in ((-1, 1.0), (1, -1.0)):
            kx = hip_x + int(swing * s_mult * 0.6)
            ky = hip_y + int(82 * scale * SS)
            fx = hip_x + int(swing * s_mult)
            fy = hip_y + int(162 * scale * SS)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)
            draw.ellipse([fx - 10 * SS, fy - 7 * SS, fx + 14 * SS, fy + 7 * SS], fill=ink)
    elif body_action in ("celebrate_groove", "struggle_pull", "shock_recoil"):
        knee_bend = int((16 if body_action != "shock_recoil" else 8) * scale * SS)
        for side in (-1, 1):
            kx = hip_x + side * (int(42 * scale * SS) + knee_bend)
            ky = hip_y + int(80 * scale * SS)
            fx = hip_x + side * int(46 * scale * SS)
            fy = hip_y + int(160 * scale * SS)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)
            draw.ellipse([fx - 10 * SS, fy - 7 * SS, fx + 12 * SS, fy + 7 * SS], fill=ink)
    else:
        for side in (-1, 1):
            kx = hip_x + side * int(52 * scale * SS)
            ky = hip_y + int(68 * scale * SS)
            fx = hip_x + side * int(54 * scale * SS)
            fy = hip_y + int(152 * scale * SS)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)

    if prof["satchel"]:
        draw.line([(neck_x - int(20 * scale * SS), neck_y + 10 * SS), (hip_x + int(24 * scale * SS), hip_y - 8 * SS)], fill=(128, 84, 52), width=max(6 * SS, int(9 * scale * SS)))

    # Articulated Arms (Shoulder -> Elbow -> Rounded Black Mitten Hand)
    sh_x = neck_x + int(torso_lean_x * 0.2 * SS)
    sh_y = neck_y + int(28 * scale * SS)
    holding_phone = False
    phone_pos = (0, 0)

    if body_action == "phone_scroll_lean":
        l_elb = (sh_x - int(58 * scale * SS), sh_y + int(52 * scale * SS))
        l_hand = (sh_x + int(18 * scale * SS), sh_y + int(42 * scale * SS) + int(math.sin(t * 10.0) * 6 * SS))
        r_elb = (sh_x + int(68 * scale * SS), sh_y + int(58 * scale * SS))
        shake_x = int(math.sin(t * 42.0) * 5 * SS)
        r_hand = (sh_x + int(76 * scale * SS) + shake_x, hy + int(46 * scale * SS))
        holding_phone = True
        phone_pos = (r_hand[0], r_hand[1] - int(18 * scale * SS))
    elif body_action == "shock_recoil" or expr == "bloodshot_shock":
        wave_y = int(math.sin(t * 24.0 + phase) * 8 * scale * SS)
        l_elb = (sh_x - int(98 * scale * SS), sh_y + int(18 * scale * SS))
        l_hand = (hx - int(94 * scale * SS), hy + int(16 * scale * SS) + wave_y)
        r_elb = (sh_x + int(98 * scale * SS), sh_y + int(18 * scale * SS))
        r_hand = (hx + int(94 * scale * SS), hy + int(16 * scale * SS) - wave_y)
    elif body_action == "struggle_pull":
        pump = int(math.sin(t * 15.0 + phase) * 26 * scale * SS)
        l_elb = (sh_x - int(54 * scale * SS), sh_y + int(34 * scale * SS))
        l_hand = (sh_x + int(22 * scale * SS) + pump, sh_y + int(24 * scale * SS))
        r_elb = (sh_x + int(64 * scale * SS), sh_y + int(42 * scale * SS))
        r_hand = (sh_x + int(44 * scale * SS) + pump, sh_y + int(32 * scale * SS))
    elif body_action == "celebrate_groove":
        pump_l = int(math.sin(t * 8.0 + phase) * 32 * scale * SS)
        pump_r = int(math.cos(t * 8.0 + phase) * 32 * scale * SS)
        l_elb = (sh_x - int(84 * scale * SS), sh_y - int(10 * scale * SS))
        l_hand = (sh_x - int(92 * scale * SS), sh_y - int(68 * scale * SS) + pump_l)
        r_elb = (sh_x + int(84 * scale * SS), sh_y - int(10 * scale * SS))
        r_hand = (sh_x + int(92 * scale * SS), sh_y - int(68 * scale * SS) + pump_r)
    elif body_action == "walk_stride":
        arm_sw = int(math.sin(t * 8.5 + phase) * 42 * scale * SS)
        l_elb = (sh_x - int(28 * scale * SS) - arm_sw // 2, sh_y + int(48 * scale * SS))
        l_hand = (sh_x - int(34 * scale * SS) - arm_sw, sh_y + int(94 * scale * SS))
        r_elb = (sh_x + int(28 * scale * SS) + arm_sw // 2, sh_y + int(48 * scale * SS))
        r_hand = (sh_x + int(34 * scale * SS) + arm_sw, sh_y + int(94 * scale * SS))
    else:
        l_elb = (sh_x - int(68 * scale * SS), sh_y + int(44 * scale * SS))
        l_hand = (hx - int(32 * scale * SS), hy + int(82 * scale * SS))
        r_elb = (sh_x + int(62 * scale * SS), sh_y + int(46 * scale * SS))
        r_hand = (sh_x + int(68 * scale * SS), hy + int(88 * scale * SS))

    draw.line([(sh_x, sh_y), l_elb, l_hand], fill=ink, width=limb_w)
    draw.line([(sh_x, sh_y), r_elb, r_hand], fill=ink, width=limb_w)
    for mhx, mhy in (l_hand, r_hand):
        draw.ellipse([mhx - mitten_r, mhy - mitten_r, mhx + mitten_r, mhy + mitten_r], fill=ink)

    # Large Cel-Shaded Round Head (with squash & stretch)
    draw.ellipse([hx - rx_head, hy - ry_head, hx + rx_head, hy + ry_head], fill=head_fill)
    draw.pieslice([hx - rx_head + 6 * SS, hy - ry_head + 6 * SS, hx + rx_head - 2 * SS, hy + ry_head - 2 * SS], start=-55, end=65, fill=head_shadow)
    draw.ellipse([hx - rx_head, hy - ry_head, hx + rx_head, hy + ry_head], outline=ink, width=max(6 * SS, int(9 * scale * SS)))

    if prof["cap_color"]:
        cap_c = prof["cap_color"]
        draw.pieslice([hx - rx_head - 2 * SS, hy - ry_head - 12 * SS, hx + rx_head + 2 * SS, hy - int(ry_head * 0.12)], start=180, end=360, fill=cap_c, outline=ink, width=max(6 * SS, int(8 * scale * SS)))
        draw.rounded_rectangle([hx - int(10 * scale * SS), hy - int(ry_head * 0.56), hx + int(rx_head * 1.32), hy - int(ry_head * 0.34)], radius=8 * SS, fill=cap_c, outline=ink, width=max(5 * SS, int(7 * scale * SS)))

    if prof["beard"]:
        draw.pieslice([hx - int(rx_head * 0.86), hy + int(4 * scale * SS), hx + int(rx_head * 0.86), hy + ry_head + 4 * SS], start=0, end=180, fill=(92, 64, 46), outline=ink, width=max(5 * SS, int(7 * scale * SS)))

    # Dynamic Facial Acting + Blinks & Pupil Tracking
    eye_dx = int(36 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(22 * scale * SS)
    is_blinking = ((t + idx_in_cast * 0.9) % 2.8) < 0.11
    pupil_look_x = int(5 * scale * SS) if holding_phone else int(math.sin(t * 1.8 + phase) * 3 * scale * SS)

    if is_blinking and expr not in ("bloodshot_shock", "sweat_grit"):
        draw.line([(hx - eye_dx - er + 4 * SS, eye_y), (hx - eye_dx + er - 4 * SS, eye_y)], fill=ink, width=max(5 * SS, int(6 * scale * SS)))
        draw.line([(hx + eye_dx - er + 4 * SS, eye_y), (hx + eye_dx + er - 4 * SS, eye_y)], fill=ink, width=max(5 * SS, int(6 * scale * SS)))
    elif expr == "smug_snooze":
        draw.arc([hx - eye_dx - er, eye_y - 10 * SS, hx - eye_dx + er, eye_y + 18 * SS], start=10, end=170, fill=ink, width=max(5 * SS, int(6 * scale * SS)))
        draw.arc([hx + eye_dx - er, eye_y - 10 * SS, hx + eye_dx + er, eye_y + 18 * SS], start=10, end=170, fill=ink, width=max(5 * SS, int(6 * scale * SS)))
    elif expr == "exhausted_half_lidded":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(252, 252, 255), outline=ink, width=4 * SS)
            draw.ellipse([ex - 6 * SS + pupil_look_x, eye_y - 4 * SS, ex + 6 * SS + pupil_look_x, eye_y + 8 * SS], fill=ink)
            draw.pieslice([ex - er, eye_y - er, ex + er, eye_y + er], start=180, end=360, fill=head_fill, outline=ink, width=4 * SS)
    elif expr == "sweat_grit":
        draw.line([(hx - eye_dx - 16 * SS, eye_y - 12 * SS), (hx - eye_dx + 12 * SS, eye_y), (hx - eye_dx - 16 * SS, eye_y + 12 * SS)], fill=ink, width=5 * SS)
        draw.line([(hx + eye_dx + 16 * SS, eye_y - 12 * SS), (hx + eye_dx - 12 * SS, eye_y), (hx + eye_dx + 16 * SS, eye_y + 12 * SS)], fill=ink, width=5 * SS)
        for sx, sy in [(hx - int(58 * scale * SS), hy - int(44 * scale * SS)), (hx + int(62 * scale * SS), hy - int(36 * scale * SS))]:
            draw.ellipse([sx - 6 * SS, sy - 9 * SS, sx + 6 * SS, sy + 9 * SS], fill=(165, 224, 255), outline=ink, width=2 * SS)
    elif expr == "bloodshot_shock":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            er_big = int(28 * scale * SS)
            draw.ellipse([ex - er_big, eye_y - er_big, ex + er_big, eye_y + er_big], fill=(255, 250, 250), outline=ink, width=5 * SS)
            draw.line([(ex - er_big + 4 * SS, eye_y - 6 * SS), (ex - 8 * SS, eye_y - 2 * SS)], fill=(224, 52, 62), width=2 * SS)
            draw.line([(ex + er_big - 4 * SS, eye_y + 8 * SS), (ex + 8 * SS, eye_y + 3 * SS)], fill=(224, 52, 62), width=2 * SS)
            draw.ellipse([ex - 6 * SS, eye_y - 6 * SS, ex + 6 * SS, eye_y + 6 * SS], fill=ink)
    elif expr == "guilty_puppy_eyes":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            er_big = int(25 * scale * SS)
            draw.ellipse([ex - er_big, eye_y - er_big, ex + er_big, eye_y + er_big], fill=ink)
            draw.ellipse([ex - 11 * SS, eye_y - 12 * SS, ex - 1 * SS, eye_y - 2 * SS], fill=(255, 255, 255))
            draw.ellipse([ex + 3 * SS, eye_y + 4 * SS, ex + 9 * SS, eye_y + 10 * SS], fill=(255, 255, 255))
    else:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - 11 * SS + pupil_look_x, eye_y - 11 * SS, ex + 11 * SS + pupil_look_x, eye_y + 11 * SS], fill=ink)

    if expr in ("smug_snooze", "confident_smirk"):
        draw.arc([hx - int(20 * scale * SS), hy + int(22 * scale * SS), hx + int(26 * scale * SS), hy + int(44 * scale * SS)], start=12, end=165, fill=ink, width=max(4 * SS, int(6 * scale * SS)))
    elif expr == "sweat_grit":
        mx0, my0 = hx - int(30 * scale * SS), hy + int(24 * scale * SS)
        mx1, my1 = hx + int(30 * scale * SS), hy + int(48 * scale * SS)
        draw.rounded_rectangle([mx0, my0, mx1, my1], radius=8 * SS, fill=(252, 252, 255), outline=ink, width=4 * SS)
        for tx in range(mx0 + 12 * SS, mx1 - 6 * SS, 14 * SS):
            draw.line([(tx, my0), (tx, my1)], fill=ink, width=3 * SS)
    elif expr == "bloodshot_shock":
        jaw_open = int((56 + math.sin(t * 26.0) * 6) * scale * SS)
        draw.rounded_rectangle([hx - int(26 * scale * SS), hy + int(22 * scale * SS), hx + int(26 * scale * SS), hy + jaw_open], radius=10 * SS, fill=(252, 252, 255), outline=ink, width=5 * SS)
    elif expr == "guilty_puppy_eyes":
        draw.arc([hx - int(18 * scale * SS), hy + int(34 * scale * SS), hx + int(18 * scale * SS), hy + int(52 * scale * SS)], start=190, end=350, fill=ink, width=5 * SS)
    else:
        draw.line([(hx - int(22 * scale * SS), hy + int(36 * scale * SS)), (hx + int(22 * scale * SS), hy + int(34 * scale * SS))], fill=ink, width=max(4 * SS, int(6 * scale * SS)))

    if prof["glasses"]:
        gr = int(28 * scale * SS)
        draw.rectangle([hx - eye_dx - gr, eye_y - gr, hx - eye_dx + gr, eye_y + gr], outline=ink, width=max(4 * SS, int(6 * scale * SS)))
        draw.rectangle([hx + eye_dx - gr, eye_y - gr, hx + eye_dx + gr, eye_y + gr], outline=ink, width=max(4 * SS, int(6 * scale * SS)))
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=max(4 * SS, int(6 * scale * SS)))

    if holding_phone:
        px, py = phone_pos
        pw, ph = int(34 * scale * SS), int(58 * scale * SS)
        draw.rounded_rectangle([px - pw, py - ph, px + pw, py + ph], radius=12 * SS, fill=(26, 30, 40), outline=ink, width=4 * SS)
        draw.rounded_rectangle([px - pw + 6 * SS, py - ph + 10 * SS, px + pw - 6 * SS, py + ph - 10 * SS], radius=6 * SS, fill=(142, 224, 255))
        for r_arc in (int(56 * scale * SS), int(72 * scale * SS)):
            draw.arc([px - r_arc, py - r_arc, px + r_arc, py + r_arc], start=-30, end=30, fill=(255, 255, 255), width=4 * SS)
            draw.arc([px - r_arc, py - r_arc, px + r_arc, py + r_arc], start=150, end=210, fill=(255, 255, 255), width=4 * SS)


def _draw_foreground_occlusion(draw, env_key, sc):
    """Draws 2x-supersampled blankets, desks, and car dashboards IN FRONT OF characters' lower bodies."""
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)

    if env_key == "overcast_bedroom":
        blanket_col = (74, 86, 112) if is_night else env["surface"]
        sheet_col = (196, 204, 220) if is_night else (244, 246, 250)
        draw.rounded_rectangle([70 * SS, 1085 * SS, (W - 70) * SS, 1580 * SS], radius=34 * SS, fill=blanket_col, outline=ink, width=8 * SS)
        draw.rounded_rectangle([70 * SS, 1085 * SS, (W - 70) * SS, 1138 * SS], radius=18 * SS, fill=sheet_col, outline=ink, width=7 * SS)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([60 * SS, 1095 * SS, (W - 60) * SS, 1580 * SS], radius=42 * SS, fill=env["surface"], outline=ink, width=8 * SS)
        draw.ellipse([235 * SS, 1035 * SS, 475 * SS, 1275 * SS], outline=(12, 14, 18), width=18 * SS)
    elif env_key == "living_room_window":
        draw.rounded_rectangle([80 * SS, 1145 * SS, (W - 80) * SS, 1520 * SS], radius=34 * SS, fill=env["surface"], outline=ink, width=8 * SS)
    else:
        draw.rectangle([0, 1130 * SS, W * SS, H * SS], fill=env["surface"])
        draw.line([(0, 1130 * SS), (W * SS, 1130 * SS)], fill=ink, width=8 * SS)
        draw.polygon([(130 * SS, 1015 * SS), (230 * SS, 1015 * SS), (212 * SS, 1130 * SS), (148 * SS, 1130 * SS)], fill=(178, 92, 64), outline=ink)
        draw.ellipse([125 * SS, 915 * SS, 235 * SS, 1025 * SS], fill=(76, 142, 82), outline=ink, width=5 * SS)
        draw.rounded_rectangle([835 * SS, 1050 * SS, 915 * SS, 1130 * SS], radius=12 * SS, fill=env["accent_prop"], outline=ink, width=5 * SS)


def render_animated_fallback_frame(bg_img, characters, env_key, sc, beat_idx, t, local_p):
    """Composites 2x-supersampled 24fps articulated characters + foreground occlusion onto the room background."""
    frame_hi = bg_img.resize((W * SS, H * SS), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(frame_hi)

    expr = sc.get("expression", "exhausted_half_lidded") if local_p < 0.42 else sc.get("end_expression", sc.get("expression", "exhausted_half_lidded"))
    body_action = sc.get("body_action", "sleep_breathe_toss")
    count = max(1, min(4, len(characters)))

    if beat_idx == 2:
        _draw_articulated_character(draw, characters[0], W // 2, 855, 1.34, expr, body_action, t, local_p, 0)
    else:
        spacing = min(245, (W - 180) // count)
        start_x = (W // 2) - ((count - 1) * spacing) // 2
        scale = 1.04 if count == 1 else (0.90 if count == 2 else (0.78 if count == 3 else 0.70))
        for idx, name in enumerate(characters[:4]):
            cx = start_x + idx * spacing
            cy = 845 + (idx % 2) * 14
            char_expr = expr if idx == 0 else ("deadpan_camera_stare" if beat_idx == 3 else "exhausted_half_lidded")
            char_act = body_action if idx == 0 else ("slouch_sigh" if body_action != "walk_stride" else "walk_stride")
            _draw_articulated_character(draw, name, cx, cy, scale, char_expr, char_act, t, local_p, idx)

    if body_action != "walk_stride":
        _draw_foreground_occlusion(draw, env_key, sc)

    return frame_hi.resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# 5. LYRIA MUSIC + AUDIO-REACTIVE SFX WITH SIDECHAIN DUCKING
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

        deadline = time.time() + 26
        async for message in session.receive():
            if message.server_content and message.server_content.audio_chunks:
                for chunk in message.server_content.audio_chunks:
                    if chunk.data:
                        pcm_buffer.extend(chunk.data)
            if len(pcm_buffer) >= target_bytes or time.time() >= deadline:
                break
        await session.stop()

    if len(pcm_buffer) < int(48000 * 2 * 2 * 3):
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
        "-af", f"volume=0.80,afade=t=in:st=0:d=0.25,afade=t=out:st={max(0.5, duration_sec - 0.6):.3f}:d=0.6",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.25) * math.pi)
        return math.sin(2 * math.pi * (180 + 540 * dt) * dt) * env * 0.30
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
        if dt < 0.32:
            return math.sin(2 * math.pi * (220 + 1350 * dt) * dt) * (dt / 0.32) * 0.30
        env = math.exp(-(dt - 0.32) * 7.5)
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
        bar_len = int(sr * 1.8)
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
        (beat_starts[i] + (0.10 if i == 0 else 0.0), scenes[i].get("sfx_cue", "pop_ding"))
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


def build_vignette_mask(strength=0.16):
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

    active_expr = sc.get("expression", "") if local_p < 0.42 else sc.get("end_expression", sc.get("expression", ""))
    is_shock_beat = (active_expr == "bloodshot_shock" or sc.get("body_action") == "shock_recoil")
    prop_fx = sc.get("prop_overlay", "none")
    env_fx = sc.get("env_effect", "none")

    if is_shock_beat or prop_fx != "none" or env_fx != "none":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if is_shock_beat:
            for i in range(32):
                ang = (i / 32.0) * math.pi * 2 + (t * 0.4)
                r0 = 420 + int(math.sin(t * 16.0 + i) * 32)
                r1 = 1080
                x0, y0 = int(W // 2 + math.cos(ang) * r0), int(H // 2 + math.sin(ang) * r0)
                x1, y1 = int(W // 2 + math.cos(ang) * r1), int(H // 2 + math.sin(ang) * r1)
                odraw.line([(x0, y0), (x1, y1)], fill=(18, 18, 22, 85), width=4)

        if prop_fx == "sweat_drops":
            drop_y = int((t * 110) % 70)
            for sx, base_y in [(390, 740), (690, 760), (355, 810)]:
                yy = base_y + drop_y
                odraw.ellipse([sx - 8, yy - 13, sx + 8, yy + 13], fill=(165, 226, 255, 220), outline=(18, 18, 22, 220), width=3)
        elif prop_fx == "delivery_box_drop":
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
        if env_fx == "screen_glow" or sc.get("body_action") == "phone_scroll_lean":
            pulse = int(42 + 22 * math.sin(t * 4.5))
            odraw.ellipse([W // 2 - 230, 720, W // 2 + 230, 1140], fill=(135, 215, 255, pulse))
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
        if local_p < 0.12:
            zoom = 1.0 + (max_z * 1.35) * _ease_out_quart(local_p / 0.12)
        else:
            zoom = (1.0 + max_z * 1.35) - (max_z * 0.22 * _ease_in_out_sine((local_p - 0.12) / 0.88))
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
        scale = 1.15 - 0.15 * eased
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
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, beat_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg = g2["card_bg"]
    c_fg = g2["card_fg"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    hook_str = (top_hook or "").strip()
    if hook_str:
        ent = _ease_out_quart(min(1.0, t / 0.20))
        hook_font = _load_font(40)
        wrapped_hook = textwrap.fill(hook_str, width=30)
        h_lines = wrapped_hook.split("\n")
        box_h = 34 + len(h_lines) * 50
        bx0, by0 = 84, 130 + int((1.0 - ent) * -12)
        bx1 = W - 84
        alpha = int(248 * ent)
        odraw.rounded_rectangle([bx0, by0, bx1, by0 + box_h], radius=24, fill=(255, 253, 248, alpha), outline=(18, 18, 22, alpha), width=5)
        odraw.multiline_text((W // 2, by0 + box_h // 2), wrapped_hook, font=hook_font, fill=(18, 18, 22, alpha), anchor="mm", align="center", spacing=8)

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

    bottom_caption = (sc.get("bottom_caption") or "").strip()
    if bottom_caption:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.14))
        time_left = max(0.0, beat_dur - scene_t)
        cap_out = 1.0 if (beat_idx == total_beats - 1 or time_left > 0.10) else max(0.0, time_left / 0.10)
        cap_alpha = int(248 * cap_in * cap_out)
        cap_font = _load_font(40)
        wrapped = textwrap.fill(bottom_caption, width=30)
        lines = wrapped.split("\n")
        box_h = 46 + len(lines) * 52
        x0, y0 = 96, 1385 + int((1.0 - cap_in) * 10)
        x1, y1 = W - 96, y0 + box_h
        odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(c_bg[0], c_bg[1], c_bg[2], min(246, cap_alpha)), outline=(acc[0], acc[1], acc[2], cap_alpha), width=3)
        odraw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=10)

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

    # Generate clean room background plates once per environment state so characters stay 24fps animated
    shared_ai_bg = tmp_dir / "shared_ai_bg.png"
    has_ai_bg = _try_generate_ai_room_plate(env_key, setting_continuity, seed["art_style_key"], shared_ai_bg)

    scene_bgs = []
    for idx, sc in enumerate(scenes):
        if has_ai_bg:
            scene_bgs.append(Image.open(shared_ai_bg).convert("RGB"))
        else:
            bg_path = tmp_dir / f"bg_{idx}.png"
            _render_environment_background(env_key, sc, idx, bg_path)
            scene_bgs.append(Image.open(bg_path).convert("RGB"))
        print(f"Prepared 2x-supersampled 24fps rig for Beat {idx + 1}/{total_beats} (action={sc.get('body_action')})")

    beat_durations = compute_beat_durations(scenes)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t
    print(f"Snappy Reels Timing ({total_dur:.2f}s total): {beat_durations}")

    final_wav = tmp_dir / "final_director.wav"
    build_director_audio(
        script_data.get("music_prompt", "playful lo-fi indie comedy loop instrumental"),
        script_data.get("music_bpm", 112),
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

        raw_stage = render_animated_fallback_frame(scene_bgs[s_idx], characters, env_key, sc, s_idx, t, local_p)

        if s_idx > 0 and sc.get("transition_in") == "freeze_record_scratch" and scene_t < 0.34 and prev_rendered_frame is not None:
            frame = ImageEnhance.Color(prev_rendered_frame).enhance(0.18)
        else:
            frame = apply_camera_trajectory(raw_stage, sc.get("camera_move", "dolly_push_in"), local_p, scene_t, t)
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
    print(f"Rendered 2x-Supersampled 24fps Reel ({total_dur:.1f}s, {total_beats} beats): {out_mp4}")


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

    rupload_url = f"[https://rupload.facebook.com/video-upload/](https://rupload.facebook.com/video-upload/){GRAPH_VERSION}/{video_id}"
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
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    hour = now_est.hour

    if 5 <= hour < 12:
        time_slot_vibe = "MORNING SLOT: Negotiating with 6 alarms, waking up late in panic, or first-sip coffee clarity."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT: Closing 19 tabs at 5:01 PM, checking $14.82 bank balance, or impulse delivery boxes."
    else:
        time_slot_vibe = "EVENING/NIGHT SLOT: Sitting in the parked car after work, 2:47 AM awkward memories, or YouTube before eating."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('top_hook', '')}" for h in recent_history if h.get("top_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history, page)
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
            "### VIRAL COMEDY & MICRO-ACTING RULES (2026 REELS)\n"
            "1. HYPER-SPECIFIC HOOKS ONLY: Lowercase/natural observational hook in 'top_hook' with ZERO emojis. Make it painfully specific.\n"
            "2. PUNCHY CAPTIONS (MAX 7 WORDS): Keep 'bottom_caption' ultra-short (0 to 7 words max) so viewers absorb the facial acting fast.\n"
            "3. ESCALATE -> SNAP ZOOM -> DEADPAN TWIST: Beat 1 sets confidence/calm, Beat 2 shows the check/temptation, Beat 3 is 'snap_zoom_face' panic, Beat 4 is 'pull_back_reveal' with 'deadpan_camera_stare' or 'bloodshot_shock'.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "top_hook": "' + scen["hook"] + '",\n'
            '  "environment_key": "' + scen["env"] + '",\n'
            '  "setting_continuity": "' + ENVIRONMENT_PRESETS[scen["env"]]["desc"] + '",\n'
            '  "music_prompt": "Playful lo-fi indie marimba and acoustic guitar comedy loop instrumental",\n'
            '  "music_bpm": 112,\n'
            '  "scenes": [\n'
            '    {"clock_label": "' + scen["clocks"][0] + '", "bottom_caption": "I barely spent anything this weekend.", "expression": "confident_smirk", "end_expression": "smug_snooze", "body_action": "slouch_sigh", "prop_overlay": "none", "visual_prompt": "Beat 1 medium shot action & pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "warm_amber_desk", "end_grade": "warm_amber_desk", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "dust", "sfx_cue": "pop_ding"},\n'
            '    {"clock_label": "' + scen["clocks"][1] + '", "bottom_caption": "Let me just check real quick...", "expression": "exhausted_half_lidded", "end_expression": "sweat_grit", "body_action": "phone_scroll_lean", "prop_overlay": "phone_vibrate_arcs", "visual_prompt": "Beat 2 close-up holding glowing phone, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "dim_night_phone_glow", "end_grade": "dim_night_phone_glow", "camera_move": "pan_follow_right", "transition_in": "blur_dissolve", "env_effect": "screen_glow", "sfx_cue": "alarm_buzz"},\n'
            '    {"clock_label": "' + scen["clocks"][2] + '", "bottom_caption": "Available balance: $14.82", "expression": "sweat_grit", "end_expression": "bloodshot_shock", "body_action": "struggle_pull", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 3 tight face close-up sweating & struggling, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "dim_night_phone_glow", "end_grade": "crimson_panic_shock", "camera_move": "snap_zoom_face", "transition_in": "whip_pan_left", "env_effect": "none", "sfx_cue": "record_scratch"},\n'
            '    {"clock_label": "' + scen["clocks"][3] + '", "bottom_caption": "Suddenly I am not even hungry.", "expression": "bloodshot_shock", "end_expression": "deadpan_camera_stare", "body_action": "shock_recoil", "prop_overlay": "none", "visual_prompt": "Beat 4 pulled-back comedic shock reveal, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "crimson_panic_shock", "end_grade": "desaturated_gloom", "camera_move": "pull_back_reveal", "transition_in": "smash_zoom_cut", "env_effect": "none", "sfx_cue": "vine_boom_sub"}\n'
            "  ],\n"
            '  "ig_caption": "Punchy relatable caption inviting followers to tag someone who does this",\n'
            '  "pinned_comment": "Specific relatable question for the comments"\n'
            "}\n"
            f"Allowed environment_key: {list(ENVIRONMENT_PRESETS.keys())}\n"
            f"Allowed expression / end_expression: {FACIAL_EXPRESSIONS}\n"
            f"Allowed body_action: {ALL_BODY_ACTIONS}\n"
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
            f"Beat {i+1} [{s.get('clock_label', '')}] ({s.get('body_action', '')} | {s.get('expression', '')}->{s.get('end_expression', '')}): {s.get('bottom_caption', '')}"
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
