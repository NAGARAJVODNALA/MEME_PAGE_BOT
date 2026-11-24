import os
import io
import sys
import math
import json
import time
import wave
import base64
import random
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

VISUAL_TUNING = {
    "vignette_strength": 0.14,
    "color_tint_strength": 0.05,
    "ambient_glow_strength": 0.12,
    "particle_opacity": 0.30,
    "max_zoom_delta": 0.09,
    "transition_sec": 0.18,
    "enable_blur_transition": True,
    "min_beat_sec": 3.2,
    "max_beat_sec": 6.8
}


# ==============================================================================
# 0. DYNAMIC GEMINI MODEL DISCOVERY (PREVENTS 404 ON RETIRED MODEL IDS)
# ==============================================================================
def discover_gemini_models():
    """Queries /v1beta/models with your GEMINI_API_KEY to pick live text, image, and TTS models."""
    text_models = []
    gemini_image_models = []
    imagen_models = []
    tts_models = []

    url = "https://generativelanguage.googleapis.com/v1beta/models?key=" + GEMINI_API_KEY
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            for m in data.get("models", []):
                name = m.get("name", "").removeprefix("models/")
                methods = m.get("supportedGenerationMethods", [])
                low = name.lower()

                if "predict" in methods and "imagen" in low:
                    imagen_models.append(name)

                if "generateContent" in methods:
                    if "tts" in low:
                        tts_models.append(name)
                    elif "image" in low:
                        gemini_image_models.append(name)
                    elif "gemini" in low and not any(x in low for x in ("embedding", "aqa", "vision", "audio", "2.5-flash")):
                        text_models.append(name)
    except Exception as e:
        print(f"Model discovery warning: {e}")

    def _rank_text(m):
        low = m.lower()
        tier = 0 if "3." in low or "3-" in low else 1
        if "flash" in low and "lite" not in low:
            return (tier, 0, m)
        if "flash-lite" in low:
            return (tier, 1, m)
        if "pro" in low:
            return (tier, 2, m)
        return (tier, 3, m)

    text_models = sorted(set(text_models), key=_rank_text) or [
        "gemini-3-flash-preview", "gemini-3.5-flash"
    ]
    gemini_image_models = sorted(set(gemini_image_models), reverse=True) or [
        "gemini-3.1-flash-image"
    ]
    imagen_models = sorted(set(imagen_models), reverse=True) or [
        "imagen-4.0-generate-001", "imagen-4.0-fast-generate-001", "imagen-3.0-generate-002"
    ]
    tts_models = sorted(set(tts_models), reverse=True) or [
        "gemini-3.8-flash-tts"
    ]

    print(f"Discovered Text Models: {text_models[:4]}")
    print(f"Discovered Gemini Image Models: {gemini_image_models[:3]}")
    print(f"Discovered Imagen Models: {imagen_models[:3]}")
    print(f"Discovered TTS Models: {tts_models[:2]}")
    return {
        "text": text_models,
        "gemini_image": gemini_image_models,
        "imagen": imagen_models,
        "tts": tts_models
    }


LIVE_MODELS = discover_gemini_models()

# ==============================================================================
# 1. PERSISTENT CHARACTER VISUAL BIBLES & DISTINCT VOICES
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Smooth Confident Instigator (charismatic, quick-witted, persuasive swagger, turns bad ideas into 'life philosophy')",
        "visual_bible": (
            "Phil, a tall athletic 27-year-old man with sharp jawline, warm tan skin, styled messy brown hair, "
            "wearing a red baseball cap worn backwards properly with the brim at the back of his head, "
            "an open crimson red fleece zip-up hoodie over a crisp white crew-neck t-shirt, and dark blue jeans"
        ),
        "voice_style": "Charismatic, confident, smooth young man with natural comedic swagger and relaxed charm",
        "accent_rgb": (214, 58, 54),
        "gemini_voice": "Fenrir",
        "edge_voice": "en-US-GuyNeural",
        "edge_rate": "+5%",
        "edge_pitch": "+2Hz",
        "espeak_pitch": 54,
        "espeak_speed": 172
    },
    "Alan": {
        "archetype": "The Deadpan Oddball Wildcard (stocky, earnest, weirdly philosophical, drops absurd logic with 100% serious sincerity)",
        "visual_bible": (
            "Alan, a stocky broad-shouldered 28-year-old man with a full fluffy brown beard and mustache, curly brown hair, "
            "wearing a fitted olive-green cotton crew-neck t-shirt with ribbed collar and a brown leather crossbody satchel strap across his chest"
        ),
        "voice_style": "Deadpan, earnest, slightly quirky man speaking with serious sincerity and dry comedic timing",
        "accent_rgb": (96, 126, 76),
        "gemini_voice": "Puck",
        "edge_voice": "en-US-ChristopherNeural",
        "edge_rate": "-5%",
        "edge_pitch": "-3Hz",
        "espeak_pitch": 40,
        "espeak_speed": 148
    },
    "Stu": {
        "archetype": "The High-Strung Overthinker (anxious about schedules, melting groceries, bank balances, and alarms, yet easily roped in)",
        "visual_bible": (
            "Stu, a slim 27-year-old man with neat side-parted dark brown hair, thick rectangular dark-rimmed eyeglasses, "
            "wearing a fitted slate-blue collared cotton polo shirt with buttons and khaki chinos"
        ),
        "voice_style": "High-strung, expressive, slightly anxious guy whose voice rises when stressed or amazed",
        "accent_rgb": (74, 112, 158),
        "gemini_voice": "Orus",
        "edge_voice": "en-US-EricNeural",
        "edge_rate": "+9%",
        "edge_pitch": "+7Hz",
        "espeak_pitch": 66,
        "espeak_speed": 180
    },
    "Doug": {
        "archetype": "The Chill Grounded Straight-Man (laid-back, unbothered, dry baritone voice of reason who loves relaxing vibes)",
        "visual_bible": (
            "Doug, a tall relaxed 28-year-old man with short neat dark hair, light stubble, warm friendly eyes, "
            "wearing a comfortable forest-green crew-neck t-shirt with rolled sleeves and relaxed denim jeans"
        ),
        "voice_style": "Deep, warm, laid-back baritone straight-man who sounds chill, unbothered, and effortlessly funny",
        "accent_rgb": (58, 118, 82),
        "gemini_voice": "Charon",
        "edge_voice": "en-US-SteffanNeural",
        "edge_rate": "-2%",
        "edge_pitch": "-6Hz",
        "espeak_pitch": 32,
        "espeak_speed": 156
    }
}

CAST_MODES = {
    "solo_chill": {
        "desc": "1 character vibing solo, talking to camera or relaxing in an immersive real-world setting",
        "lineups": [["Doug"], ["Phil"], ["Alan"], ["Stu"]]
    },
    "classic_duo": {
        "desc": "2 contrasting friends in sharp comedic banter (alternating two-shots and close-ups)",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Phil", "Alan"],
            ["Stu", "Doug"],
            ["Alan", "Stu"],
            ["Phil", "Doug"]
        ]
    },
    "trio_hangout": {
        "desc": "3 friends hanging out, vibing, or debating an everyday dilemma",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_crew_4": {
        "desc": "All 4 friends (Phil, Alan, Stu, and Doug) together in a lively group moment",
        "lineups": [["Phil", "Alan", "Stu", "Doug"]]
    }
}

FACIAL_EXPRESSIONS = [
    "chill_relaxed_smile",
    "skeptical_side_eye",
    "panicked_wide_eyes",
    "smug_confident_grin",
    "deadpan_unbothered",
    "laughing_joyful",
    "shocked_jaw_drop",
    "exasperated_sigh",
    "scheming_eyebrow_raise",
    "vibing_eyes_closed_groove"
]

ALL_BODY_ACTIONS = [
    "driving_hands_on_wheel",
    "passenger_seat_recline",
    "party_dance_groove",
    "holding_iced_coffee",
    "phone_call_ear",
    "point_and_explain",
    "shrug_both_hands",
    "couch_chill_controller",
    "leaning_on_hood",
    "toast_drinks_laugh"
]

# ==============================================================================
# 2. DIVERSE, RICH CGI WORLDS & NON-REPEATING COMEDY SCENARIOS
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "detailed_car_interior": {
        "desc": (
            "Inside a modern sedan parked on a suburban street at dusk: detailed leather seats with headrests, "
            "realistic steering wheel with center emblem in the driver's hands, glowing digital dashboard speedometer, "
            "windshield A-pillars, rearview mirror, warm amber streetlights and houses visible through the windshield and side windows"
        ),
        "grade": "midnight_car_dashboard",
        "effect": "none",
        "fallback_outro": "Still sitting in your parked car? Like, share & follow"
    },
    "rooftop_party_sunset": {
        "desc": (
            "Golden-hour rooftop lounge party overlooking a city skyline: warm string lights overhead, "
            "colorful bokeh party lights, DJ booth and speakers in the background, drinks on a high-top table, sunset sky"
        ),
        "grade": "golden_morning_sunlight",
        "effect": "confetti",
        "fallback_outro": "Send this to your party crew • Like & follow for more"
    },
    "neon_house_party": {
        "desc": (
            "Lively Friday night apartment party with purple and cyan LED strip lighting, disco reflections, "
            "friends dancing in the background, snacks and cups on the counter, energetic weekend vibe"
        ),
        "grade": "party_neon_glow",
        "effect": "sparks",
        "fallback_outro": "Tag your Irish-exit partner • Follow for daily laughs"
    },
    "beach_boardwalk_sunset": {
        "desc": (
            "Palm-lined coastal boardwalk at golden sunset with ocean waves, warm orange sky, "
            "cruiser bikes, iced drinks, and relaxed weekend vacation energy"
        ),
        "grade": "golden_morning_sunlight",
        "effect": "dust",
        "fallback_outro": "Save this for your next chill day • Like & follow"
    },
    "late_night_drive_thru": {
        "desc": (
            "Inside a car pulled up to a glowing neon fast-food drive-thru menu board at night, "
            "driver leaning toward the open window with dashboard lights glowing"
        ),
        "grade": "midnight_car_dashboard",
        "effect": "none",
        "fallback_outro": "Comment your 1 AM order • Share & follow"
    },
    "cozy_living_room_chill": {
        "desc": (
            "Sunlit modern apartment living room with plush sectional sofa, indoor monstera plants, "
            "warm floor lamp, framed art, coffee table with snacks, and big window"
        ),
        "grade": "warm_amber_desk",
        "effect": "dust",
        "fallback_outro": "Doing nothing in peace? Like, comment & follow"
    },
    "artisan_coffee_patio": {
        "desc": (
            "Trendy sunlit outdoor cafe patio with wooden tables, iced lattes, brick wall, "
            "string lights, and bustling weekend morning street behind"
        ),
        "grade": "suburban_daylight_cel",
        "effect": "none",
        "fallback_outro": "Share with your coffee math buddy • Follow"
    },
    "gym_weight_room": {
        "desc": (
            "Modern sunlit gym floor with dumbbell racks, squat rack, large mirrors, "
            "rubber gym flooring, and water bottles"
        ),
        "grade": "suburban_daylight_cel",
        "effect": "none",
        "fallback_outro": "Tag your gym spotter • Like & follow"
    },
    "airport_gate_lounge": {
        "desc": (
            "Bright airport terminal boarding gate with floor-to-ceiling windows showing parked passenger jets on the tarmac, "
            "rolling carry-on suitcases, and gate display screens"
        ),
        "grade": "overcast_morning_bedroom",
        "effect": "none",
        "fallback_outro": "Comment how early you get to the airport • Follow"
    },
    "supermarket_snack_aisle": {
        "desc": (
            "Colorful grocery store snack and ice cream aisle with stocked shelves, bright overhead lights, "
            "and a metal shopping cart"
        ),
        "grade": "suburban_daylight_cel",
        "effect": "none",
        "fallback_outro": "Tag who ruins the grocery budget • Share & follow"
    }
}

SCENARIO_LIBRARY = [
    {
        "id": "car_decompression",
        "vibe": "chill_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "Sitting in the parked car for 40 minutes after work",
        "env": "detailed_car_interior",
        "clocks": ["6:12 PM", "6:26 PM", "6:41 PM", "6:55 PM"],
        "story_seed": "Driver refuses to exit the parked car because 'driveway silence is free therapy' while passenger panics about melting ice cream in the trunk"
    },
    {
        "id": "solo_weekend_peace",
        "vibe": "solo_chill_relax",
        "allowed_modes": ["solo_chill"],
        "hook": "Canceling Friday plans just to chill in peace",
        "env": "cozy_living_room_chill",
        "clocks": ["8:30 PM", "9:15 PM", "10:00 PM", "11:10 PM"],
        "story_seed": "Solo character celebrates having zero obligations, plush couch, favorite snacks, and phone on Do Not Disturb — peak relaxation"
    },
    {
        "id": "rooftop_dance_vibe",
        "vibe": "party_dance",
        "allowed_modes": ["trio_hangout", "full_crew_4", "classic_duo"],
        "hook": "When the DJ finally plays that ONE throwback song",
        "env": "rooftop_party_sunset",
        "clocks": ["7:45 PM", "7:46 PM", "7:47 PM", "7:48 PM"],
        "story_seed": "The crew goes from acting too cool at a sunset rooftop party to full synchronized dance moves the second the beat drops"
    },
    {
        "id": "house_party_irish_exit",
        "vibe": "party_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "Planning the legendary 11:30 PM Irish exit at a party",
        "env": "neon_house_party",
        "clocks": ["11:18 PM", "11:24 PM", "11:29 PM", "11:31 PM"],
        "story_seed": "While neon lights flash and people dance behind them, two friends coordinate a stealthy goodbye-free escape to go get tacos"
    },
    {
        "id": "drive_thru_indecision",
        "vibe": "late_night_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "Pulling up to the drive-thru with zero game plan",
        "env": "late_night_drive_thru",
        "clocks": ["12:14 AM", "12:15 AM", "12:16 AM", "12:17 AM"],
        "story_seed": "Driver panics at the glowing drive-thru speaker while passenger orders three completely unrelated combos with deadpan confidence"
    },
    {
        "id": "beach_sunset_vibes",
        "vibe": "solo_chill_relax",
        "allowed_modes": ["solo_chill", "classic_duo"],
        "hook": "Zero emails, ocean breeze, and a $6 iced drink",
        "env": "beach_boardwalk_sunset",
        "clocks": ["5:30 PM", "5:50 PM", "6:10 PM", "6:30 PM"],
        "story_seed": "Soaking in golden sunset ocean vibes on the boardwalk and realizing 90% of weekday stress was completely made up"
    },
    {
        "id": "coffee_math_economics",
        "vibe": "banter_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "Friend math: how a $7 iced latte saves $30",
        "env": "artisan_coffee_patio",
        "clocks": ["10:15 AM", "10:16 AM", "10:17 AM", "10:18 AM"],
        "story_seed": "Phil and Alan prove on an outdoor cafe patio that skipping a $40 brunch for a $7 iced latte means they literally earned $33"
    },
    {
        "id": "gym_one_more_rep",
        "vibe": "banter_comedy",
        "allowed_modes": ["classic_duo", "solo_chill"],
        "hook": "Gym bro spotting: 'It's all you bro!' (lifts 90%)",
        "env": "gym_weight_room",
        "clocks": ["5:10 PM", "5:12 PM", "5:14 PM", "5:16 PM"],
        "story_seed": "Spotter claims 'you got this all yourself' while practically deadlifting the barbell for his struggling friend"
    },
    {
        "id": "airport_dad_early",
        "vibe": "travel_comedy",
        "allowed_modes": ["classic_duo", "full_crew_4"],
        "hook": "Arriving at the airport 4 hours early for a 1-hour flight",
        "env": "airport_gate_lounge",
        "clocks": ["5:00 AM", "6:15 AM", "7:30 AM", "8:45 AM"],
        "story_seed": "Stu insists on arriving at sunrise while Doug and Alan already ate two lunches and befriended the gate agent"
    },
    {
        "id": "grocery_budget_trap",
        "vibe": "relatable_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "Walking into the store for 'just milk and eggs'",
        "env": "supermarket_snack_aisle",
        "clocks": ["4:10 PM", "4:18 PM", "4:27 PM", "4:35 PM"],
        "story_seed": "They came in for two essentials and now the cart is overflowing with three flavors of ice cream, party chips, and zero milk"
    },
    {
        "id": "solo_car_concert",
        "vibe": "solo_chill_dance",
        "allowed_modes": ["solo_chill"],
        "hook": "Turning the driver's seat into a Grammy concert",
        "env": "detailed_car_interior",
        "clocks": ["5:42 PM", "5:44 PM", "5:46 PM", "5:48 PM"],
        "story_seed": "Solo driver stuck in evening traffic turns up the bass, puts on sunglasses, and performs a full steering-wheel drum solo"
    },
    {
        "id": "five_minutes_away_lie",
        "vibe": "banter_comedy",
        "allowed_modes": ["classic_duo", "trio_hangout"],
        "hook": "When your friend says 'I'm pulling up right now'",
        "env": "cozy_living_room_chill",
        "clocks": ["7:00 PM", "7:14 PM", "7:28 PM", "7:45 PM"],
        "story_seed": "Friend swears he is turning onto the street while still sitting comfortably on his own living room couch in sweatpants"
    }
]

# ==============================================================================
# 3. COLOR GRADES, CAMERA MOVES & TRANSITIONS
# ==============================================================================
COLOR_GRADES = {
    "warm_amber_desk": {
        "tint": (235, 154, 88), "glow": (255, 208, 128), "contrast": 1.05, "sat": 1.07, "accent": (255, 192, 92)
    },
    "overcast_morning_bedroom": {
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.04, "sat": 0.96, "accent": (152, 196, 245)
    },
    "golden_morning_sunlight": {
        "tint": (248, 188, 112), "glow": (255, 232, 168), "contrast": 1.06, "sat": 1.12, "accent": (255, 204, 88)
    },
    "suburban_daylight_cel": {
        "tint": (196, 216, 238), "glow": (255, 244, 204), "contrast": 1.05, "sat": 1.06, "accent": (255, 214, 84)
    },
    "midnight_car_dashboard": {
        "tint": (64, 96, 148), "glow": (142, 214, 255), "contrast": 1.06, "sat": 1.04, "accent": (124, 214, 255)
    },
    "party_neon_glow": {
        "tint": (168, 86, 235), "glow": (255, 118, 214), "contrast": 1.08, "sat": 1.15, "accent": (255, 110, 224)
    },
    "crimson_panic_shock": {
        "tint": (228, 72, 82), "glow": (255, 134, 102), "contrast": 1.10, "sat": 1.14, "accent": (255, 96, 102)
    }
}

ALL_TRANSITIONS = [
    "hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right", "blur_dissolve"
]

ALL_CAMERA_MOVES = [
    "dolly_push_in", "pull_back_reveal", "snap_zoom_face",
    "pan_follow_left", "pan_follow_right", "party_dance_bounce", "gentle_float"
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
        "layout_mode": "v14_cgi_vfx_story_cta",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Pixar/Spider-Verse quality 3D CGI animated comedy shorts starring Phil, Alan, Stu, and Doug — chill vibes, party energy, real cars & detailed environments, sharp comedic banter, and word-synced karaoke captions"
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
            "Weekend chill vibes vs group chat chaos",
            "Friend math justifying iced coffee",
            "Sitting in the parked car listening to one more song"
        ]
    return "\n".join(f"- {t}" for t in trends)


def load_history(slug, limit=40):
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
    """Guarantees zero back-to-back theme/scenario/environment repetition across posts."""
    recent_ids = {h.get("scenario_id", "") for h in recent_history[-8:]}
    recent_envs = {h.get("environment_key", "") for h in recent_history[-3:]}
    recent_hooks = {h.get("top_hook", "") for h in recent_history[-10:]}
    used_combos = {h.get("combo_key", "") for h in recent_history}

    candidates = [
        s for s in SCENARIO_LIBRARY
        if s["id"] not in recent_ids and s["env"] not in recent_envs and s["hook"] not in recent_hooks
    ]
    if not candidates:
        candidates = [s for s in SCENARIO_LIBRARY if s["id"] not in recent_ids] or SCENARIO_LIBRARY

    scen = random.choice(candidates)
    cast_mode = random.choice(scen["allowed_modes"])
    characters = random.choice(CAST_MODES[cast_mode]["lineups"])
    combo_key = f"{scen['id']}|{cast_mode}|{'+'.join(characters)}"

    if combo_key in used_combos:
        alt_lineups = [
            lu for lu in CAST_MODES[cast_mode]["lineups"]
            if f"{scen['id']}|{cast_mode}|{'+'.join(lu)}" not in used_combos
        ]
        if alt_lineups:
            characters = random.choice(alt_lineups)
            combo_key = f"{scen['id']}|{cast_mode}|{'+'.join(characters)}"

    return {
        "combo_key": combo_key,
        "scenario_id": scen["id"],
        "vibe": scen["vibe"],
        "cast_mode": cast_mode,
        "characters": characters,
        "scenario": scen
    }


def validate_and_fix_plan(script_data, seed):
    if not isinstance(script_data, dict):
        return _build_local_fallback_script(seed)

    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return _build_local_fallback_script(seed)

    scenes = scenes[:4]
    used_cams = set()
    used_trans = set()
    scen = seed["scenario"]
    chars = seed["characters"]
    env_key = script_data.get("environment_key") if script_data.get("environment_key") in ENVIRONMENT_PRESETS else scen["env"]
    script_data["environment_key"] = env_key
    default_grade = ENVIRONMENT_PRESETS[env_key]["grade"]

    if not script_data.get("top_hook"):
        script_data["top_hook"] = scen["hook"]

    outro_line = (script_data.get("end_card_cta") or "").strip()
    if not outro_line or len(outro_line) > 58:
        outro_line = ENVIRONMENT_PRESETS[env_key]["fallback_outro"]
    script_data["end_card_cta"] = outro_line

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = default_grade
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]

        if sc.get("expression") not in FACIAL_EXPRESSIONS:
            sc["expression"] = "chill_relaxed_smile" if idx == 0 else "smug_confident_grin"
        if sc.get("end_expression") not in FACIAL_EXPRESSIONS:
            sc["end_expression"] = sc["expression"]
        if sc.get("body_action") not in ALL_BODY_ACTIONS:
            sc["body_action"] = "driving_hands_on_wheel" if env_key == "detailed_car_interior" else "point_and_explain"
        if sc.get("sfx_cue") not in ALL_SFX_CUES:
            sc["sfx_cue"] = "pop_ding" if idx < 2 else ("record_scratch" if idx == 2 else "vine_boom_sub")
        if not sc.get("clock_label"):
            sc["clock_label"] = scen["clocks"][idx]

        spk = (sc.get("speaker") or "").strip()
        if spk not in chars:
            spk = chars[idx % len(chars)]
        sc["speaker"] = spk

        dlg = (sc.get("dialogue") or "").strip()
        if not dlg:
            dlg = "Honestly, this right here is peak weekend energy."
        words = dlg.split()
        if len(words) > 15:
            dlg = " ".join(words[:14]) + "."
        sc["dialogue"] = dlg

        if len(chars) == 1:
            sc["shot_framing"] = "solo_medium" if idx in (0, 3) else "speaker_closeup"
        else:
            sc["shot_framing"] = (
                sc.get("shot_framing")
                if sc.get("shot_framing") in ("group_shot", "speaker_closeup")
                else ("speaker_closeup" if idx in (1, 2) else "group_shot")
            )

        if not sc.get("cgi_scene_description"):
            sc["cgi_scene_description"] = (
                f"{spk} {sc['body_action'].replace('_', ' ')} with a "
                f"{sc['expression'].replace('_', ' ')} expression"
            )

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

    vibe_tags = {
        "party_dance": ["#partyvibes", "#weekendmood", "#dancereels"],
        "solo_chill_relax": ["#chillvibes", "#peacefulmind", "#selfcarehumor"],
        "solo_chill_dance": ["#carconcert", "#goodvibes", "#chillclub"],
    }.get(seed.get("vibe", ""), ["#comedyskit", "#friendgroup", "#relatablehumor"])

    dynamic_tags = vibe_tags + ["#3danimation", "#animatedshorts", "#wearechillclub", "#funnyreels"]
    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Tag someone who matches this exact energy."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    chars = seed["characters"]
    c1 = chars[0]
    c2 = chars[-1]
    scen = seed["scenario"]
    env_key = scen["env"]
    grade = ENVIRONMENT_PRESETS[env_key]["grade"]

    return {
        "reel_mode": "spoken_skit",
        "top_hook": scen["hook"],
        "environment_key": env_key,
        "end_card_cta": ENVIRONMENT_PRESETS[env_key]["fallback_outro"],
        "music_prompt": "Chill upbeat funk-pop comedy groove instrumental",
        "music_bpm": 112,
        "scenes": [
            {
                "clock_label": scen["clocks"][0],
                "speaker": c1,
                "dialogue": "Tell me honestly, is there any better feeling than this right here?",
                "shot_framing": "group_shot" if len(chars) > 1 else "solo_medium",
                "expression": "chill_relaxed_smile",
                "end_expression": "chill_relaxed_smile",
                "body_action": "driving_hands_on_wheel" if env_key == "detailed_car_interior" else "party_dance_groove",
                "cgi_scene_description": f"{c1} smiling warmly and relaxed in the middle of {scen['story_seed']}",
                "start_grade": grade,
                "end_grade": grade,
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "sfx_cue": "pop_ding"
            },
            {
                "clock_label": scen["clocks"][1],
                "speaker": c2,
                "dialogue": "Bro, zero stress, good music, and nowhere we have to be!",
                "shot_framing": "speaker_closeup",
                "expression": "laughing_joyful",
                "end_expression": "smug_confident_grin",
                "body_action": "point_and_explain",
                "cgi_scene_description": f"Close-up of {c2} laughing joyfully and gesturing with his hands",
                "start_grade": grade,
                "end_grade": grade,
                "camera_move": "pan_follow_right",
                "transition_in": "whip_pan_left",
                "sfx_cue": "whoosh"
            },
            {
                "clock_label": scen["clocks"][2],
                "speaker": c1,
                "dialogue": "Wait a second... did anyone remember to check the time?",
                "shot_framing": "speaker_closeup",
                "expression": "skeptical_side_eye",
                "end_expression": "panicked_wide_eyes",
                "body_action": "shrug_both_hands",
                "cgi_scene_description": f"Close-up of {c1} raising eyebrows in sudden comedic realization",
                "start_grade": grade,
                "end_grade": grade,
                "camera_move": "snap_zoom_face",
                "transition_in": "smash_zoom_cut",
                "sfx_cue": "record_scratch"
            },
            {
                "clock_label": scen["clocks"][3],
                "speaker": c2,
                "dialogue": "Time is a social construct. Turn the volume up!",
                "shot_framing": "group_shot" if len(chars) > 1 else "solo_medium",
                "expression": "vibing_eyes_closed_groove",
                "end_expression": "laughing_joyful",
                "body_action": "party_dance_groove",
                "cgi_scene_description": f"{c2} grooving happily to the beat with a huge grin",
                "start_grade": grade,
                "end_grade": grade,
                "camera_move": "party_dance_bounce",
                "transition_in": "whip_pan_right",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": "Pure chill and zero stress. Send this to your favorite hangout partner.",
        "pinned_comment": "Are you the chill planner or the chaotic friend in your group?"
    }


def ask_gemini_script(prompt, seed):
    models = LIVE_MODELS["text"][:4]
    last_err = "Unknown error"

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.94,
                    "maxOutputTokens": 2800,
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
                        print(f"Generated CGI comedy script with {model}")
                        return validate_and_fix_plan(parsed, seed)
                    last_err = f"{model} returned incomplete JSON"
            except Exception as e:
                last_err = f"{model} attempt {attempt}: {e}"
                print(last_err)
                time.sleep(1.5)

    print(f"All Gemini text endpoints busy ({last_err}); using local script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. TRUE CGI / VFX SCENE RENDERER (GEMINI NATIVE IMAGE + IMAGEN + REF CONSISTENCY)
# ==============================================================================
def _build_cgi_prompt(characters, env_key, sc, story_context):
    env_desc = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["cozy_living_room_chill"])["desc"]
    speaker = (sc.get("speaker") or characters[0]).strip()
    framing = sc.get("shot_framing", "group_shot")
    expr_desc = sc.get("expression", "chill_relaxed_smile").replace("_", " ")
    action_desc = sc.get("body_action", "point_and_explain").replace("_", " ")
    beat_visual = sc.get("cgi_scene_description", "")

    if framing == "speaker_closeup" and speaker in CAST_IDENTITY:
        cast_block = (
            f"Close-up cinematic medium portrait of ONLY {CAST_IDENTITY[speaker]['visual_bible']}. "
            f"He has a highly expressive, lifelike {expr_desc} facial expression, detailed eyes with catchlights, "
            f"realistic skin texture and fabric folds, performing action: {action_desc}."
        )
    else:
        char_lines = []
        for idx, name in enumerate(characters):
            bible = CAST_IDENTITY[name]["visual_bible"]
            if name == speaker:
                role_note = f"(MAIN SPEAKER in foreground: expressive {expr_desc} face, {action_desc})"
            else:
                role_note = "(reacting naturally alongside him with lifelike comedic body language)"
            if env_key == "detailed_car_interior" and idx == 0:
                role_note += " sitting in the left driver's seat with hands on the steering wheel"
            elif env_key == "detailed_car_interior" and idx == 1:
                role_note += " sitting in the right front passenger seat"
            char_lines.append(f"- {bible} {role_note}")
        cast_block = "Characters in frame:\n" + "\n".join(char_lines)

    return (
        "High-budget 3D CGI animated feature film still (Pixar, DreamWorks, and Sony Spider-Verse VFX quality), "
        "vertical 9:16 portrait composition (1080x1920), rich cinematic volumetric lighting, realistic depth of field, "
        "detailed textures on clothing, hair, skin, and real-world objects.\n"
        f"SETTING & REAL PROPS: {env_desc}.\n"
        f"SCENE MOMENT: {story_context}. {beat_visual}.\n"
        f"{cast_block}\n"
        "CRITICAL FRAMING RULES: Frame all characters cleanly inside the middle zone (between 20% from the top and 65% from the top of the image) "
        "so the top 20% and bottom 35% remain uncluttered background space for UI banners and subtitles. "
        "ZERO text, ZERO speech bubbles, ZERO watermarks, ZERO captions, ZERO UI overlays inside the image."
    )


def _call_gemini_image_gen(prompt_text, out_path, ref_image_path=None):
    parts = []
    if ref_image_path and pathlib.Path(ref_image_path).exists():
        ref_b64 = base64.b64encode(pathlib.Path(ref_image_path).read_bytes()).decode("utf-8")
        parts.append({
            "inlineData": {
                "mimeType": "image/png",
                "data": ref_b64
            }
        })
        prompt_text = (
            "REFERENCE IMAGE PROVIDED ABOVE: Maintain the EXACT same character faces, hairstyles, "
            "clothing, and 3D CGI art style from the reference image.\n\n" + prompt_text
        )
    parts.append({"text": prompt_text})

    for model in LIVE_MODELS["gemini_image"][:3]:
        url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": "9:16"
                }
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    if "inlineData" in part and part["inlineData"].get("data"):
                        img_bytes = base64.b64decode(part["inlineData"]["data"])
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                        img.save(out_path, format="PNG")
                        print(f"[CGI OK] Rendered frame via {model} (ref={bool(ref_image_path)})")
                        return True
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:350]
            print(f"{model} HTTP {e.code}: {err_msg}")
            if "imageConfig" in err_msg:
                try:
                    payload["generationConfig"].pop("imageConfig", None)
                    req2 = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req2, timeout=60) as resp2:
                        data2 = json.loads(resp2.read().decode())
                        for part in data2.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                            if "inlineData" in part and part["inlineData"].get("data"):
                                img_bytes = base64.b64decode(part["inlineData"]["data"])
                                img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                                img.save(out_path, format="PNG")
                                print(f"[CGI OK] Rendered frame via {model} (fallback config)")
                                return True
                except Exception as e2:
                    print(f"{model} retry skipped: {e2}")
        except Exception as e:
            print(f"{model} skipped: {e}")
    return False


def _call_imagen_4(prompt_text, out_path):
    for model in LIVE_MODELS["imagen"][:3]:
        url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:predict?key={GEMINI_API_KEY}"
        payload = {
            "instances": [{"prompt": prompt_text}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "9:16"
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                preds = data.get("predictions", [])
                if preds and preds[0].get("bytesBase64Encoded"):
                    img_bytes = base64.b64decode(preds[0]["bytesBase64Encoded"])
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                    img.save(out_path, format="PNG")
                    print(f"[CGI OK] Rendered frame via {model}")
                    return True
        except urllib.error.HTTPError as e:
            print(f"{model} HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:350]}")
        except Exception as e:
            print(f"{model} skipped: {e}")
    return False


def generate_cgi_scene_frame(characters, env_key, sc, story_context, out_path, ref_image_path=None):
    prompt_text = _build_cgi_prompt(characters, env_key, sc, story_context)
    if _call_gemini_image_gen(prompt_text, out_path, ref_image_path=ref_image_path):
        return Image.open(out_path).convert("RGB")
    if _call_imagen_4(prompt_text, out_path):
        return Image.open(out_path).convert("RGB")

    raise RuntimeError(
        f"All CGI image generators failed for scene '{sc.get('dialogue', '')}'. "
        "Check GEMINI_API_KEY billing/quota and discovered models in logs above."
    )


# ==============================================================================
# 5. VERIFIED NEURAL HUMAN VOICE SYNTHESIS + WORD-BY-WORD KARAOKE SYNC
# ==============================================================================
def _ensure_edge_tts_installed():
    if shutil.which("edge-tts"):
        return True
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts"], check=True, timeout=60)
        return True
    except Exception as e:
        print(f"Could not auto-install edge-tts: {e}")
        return False


def _wav_has_audible_voice(wav_path):
    if not wav_path or not pathlib.Path(wav_path).exists():
        return False
    try:
        with wave.open(str(wav_path), "rb") as wf:
            n_ch = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())
        total = len(raw) // (2 * n_ch)
        if total < 2400:
            return False
        samples = struct.unpack(f"<{total * n_ch}h", raw)[::n_ch]
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
        return rms > 0.012
    except Exception:
        return False


def _analyze_wav_speech_sync(wav_path, dialogue_text, total_beat_frames, speech_offset_frames=3):
    speech_energy = [0.0] * total_beat_frames
    words = [w for w in (dialogue_text or "").split() if w]
    word_timings = []

    if not wav_path or not pathlib.Path(wav_path).exists():
        return speech_energy, word_timings

    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    total_samples = len(raw) // (2 * n_ch)
    if total_samples <= 0:
        return speech_energy, word_timings

    samples = struct.unpack(f"<{total_samples * n_ch}h", raw)
    mono = samples[::n_ch]
    spf = max(1, sr // FPS)
    num_audio_frames = len(mono) // spf

    energies = []
    for f in range(num_audio_frames):
        seg = mono[f * spf:(f + 1) * spf]
        if not seg:
            energies.append(0.0)
            continue
        rms = math.sqrt(sum(s * s for s in seg) / len(seg)) / 32768.0
        energies.append(rms)

    peak = max(energies) if energies else 0.0
    if peak < 0.005:
        return speech_energy, word_timings

    active_audio_frames = []
    for f in range(num_audio_frames):
        vid_f = f + speech_offset_frames
        if vid_f >= total_beat_frames:
            break
        norm_e = min(1.0, energies[f] / peak)
        speech_energy[vid_f] = norm_e
        if norm_e >= 0.14:
            active_audio_frames.append(f)

    if words:
        first_f = active_audio_frames[0] if active_audio_frames else 0
        last_f = active_audio_frames[-1] if active_audio_frames else max(1, num_audio_frames - 1)
        start_sec = (first_f + speech_offset_frames) / float(FPS)
        end_sec = max(start_sec + 0.35, (last_f + speech_offset_frames + 1) / float(FPS))
        span_sec = end_sec - start_sec

        weights = []
        for w in words:
            clean_len = max(2, sum(1 for ch in w if ch.isalnum()))
            punct_bonus = 2.4 if w[-1] in ".!?" else (1.3 if w[-1] in ",;:" else 0.0)
            weights.append(clean_len + punct_bonus)
        total_w = sum(weights) or 1.0

        cur_t = start_sec
        for w, wt in zip(words, weights):
            w_dur = span_sec * (wt / total_w)
            word_timings.append({
                "word": w,
                "start": cur_t,
                "end": cur_t + w_dur
            })
            cur_t += w_dur

    return speech_energy, word_timings


def _try_gemini_tts(dialogue_text, prof, out_wav):
    voice_name = prof.get("gemini_voice", "Fenrir")
    style_dir = prof.get("voice_style", "Expressive comedic voice")
    tts_model = LIVE_MODELS["tts"][0]
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){tts_model}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [{
                "text": f"Acting direction: {style_dir}.\nSpeak this line naturally: {dialogue_text}"
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            }
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        res = json.loads(resp.read().decode())
        for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                inline = part["inlineData"]
                mime = inline.get("mimeType", "")
                audio_bytes = base64.b64decode(inline["data"])
                raw_tmp = out_wav.parent / (out_wav.stem + "_gtts")
                if "L16" in mime or "pcm" in mime or not mime:
                    raw_pcm = raw_tmp.with_suffix(".wav")
                    with wave.open(str(raw_pcm), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(audio_bytes)
                    subprocess.run(["ffmpeg", "-y", "-i", str(raw_pcm), "-ar", "48000", "-ac", "2", str(out_wav)], check=True)
                    raw_pcm.unlink(missing_ok=True)
                else:
                    raw_bin = raw_tmp.with_suffix(".bin")
                    raw_bin.write_bytes(audio_bytes)
                    subprocess.run(["ffmpeg", "-y", "-i", str(raw_bin), "-ar", "48000", "-ac", "2", str(out_wav)], check=True)
                    raw_bin.unlink(missing_ok=True)
                return _wav_has_audible_voice(out_wav)
    return False


def _try_edge_neural_tts(dialogue_text, prof, out_wav):
    _ensure_edge_tts_installed()
    mp3_tmp = out_wav.parent / (out_wav.stem + "_edge.mp3")
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", prof.get("edge_voice", "en-US-GuyNeural"),
        f"--rate={prof.get('edge_rate', '+0%')}",
        f"--pitch={prof.get('edge_pitch', '+0Hz')}",
        "--text", dialogue_text,
        "--write-media", str(mp3_tmp)
    ]
    subprocess.run(cmd, check=True, timeout=30)
    subprocess.run(["ffmpeg", "-y", "-i", str(mp3_tmp), "-ar", "48000", "-ac", "2", str(out_wav)], check=True)
    mp3_tmp.unlink(missing_ok=True)
    return _wav_has_audible_voice(out_wav)


def synthesize_dialogue_beat(speaker, dialogue_text, out_wav):
    prof = CAST_IDENTITY.get(speaker, CAST_IDENTITY["Phil"])
    generated = False

    try:
        generated = _try_gemini_tts(dialogue_text, prof, out_wav)
        if generated:
            print(f"[VOICE OK] {speaker} -> Gemini Neural ({prof['gemini_voice']})")
    except Exception as e:
        print(f"Gemini TTS fallback for {speaker}: {e}")

    if not generated:
        try:
            generated = _try_edge_neural_tts(dialogue_text, prof, out_wav)
            if generated:
                print(f"[VOICE OK] {speaker} -> Edge Neural ({prof['edge_voice']})")
        except Exception as e:
            print(f"Edge Neural TTS fallback for {speaker}: {e}")

    if not generated:
        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak_bin:
            raw_esp = out_wav.parent / (out_wav.stem + "_esp.wav")
            subprocess.run([
                espeak_bin,
                "-v", "en-us+m3",
                "-s", str(prof.get("espeak_speed", 162)),
                "-p", str(prof.get("espeak_pitch", 48)),
                "-w", str(raw_esp),
                dialogue_text
            ], check=True)
            subprocess.run(["ffmpeg", "-y", "-i", str(raw_esp), "-ar", "48000", "-ac", "2", str(out_wav)], check=True)
            raw_esp.unlink(missing_ok=True)
            generated = _wav_has_audible_voice(out_wav)

    if not generated:
        raise RuntimeError(f"Failed to generate audible speech for {speaker}: '{dialogue_text}'")

    norm_wav = out_wav.parent / (out_wav.stem + "_norm.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(out_wav),
        "-af", "loudnorm=I=-15:TP=-1.5:LRA=9",
        "-ar", "48000", "-ac", "2", str(norm_wav)
    ], check=True)
    if _wav_has_audible_voice(norm_wav):
        shutil.move(str(norm_wav), str(out_wav))
    else:
        norm_wav.unlink(missing_ok=True)

    with wave.open(str(out_wav), "rb") as wf:
        dur = wf.getnframes() / float(wf.getframerate())
    return dur


def compute_beat_durations_and_voices(scenes, tmp_dir):
    durations = []
    voice_tracks = []
    energy_timelines = []
    word_timings_all = []

    for idx, sc in enumerate(scenes):
        dlg = (sc.get("dialogue") or "").strip()
        spk = (sc.get("speaker") or "Phil").strip()
        wav_path = tmp_dir / f"voice_{idx}.wav"
        speech_dur = synthesize_dialogue_beat(spk, dlg, wav_path)
        extra_tail = 0.75 if idx == len(scenes) - 1 else 0.45
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], speech_dur + extra_tail)), 2)
        durations.append(dur)
        voice_tracks.append(wav_path)
        energies, w_times = _analyze_wav_speech_sync(wav_path, dlg, int(dur * FPS) + 6, speech_offset_frames=3)
        energy_timelines.append(energies)
        word_timings_all.append(w_times)

    return durations, voice_tracks, energy_timelines, word_timings_all


# ==============================================================================
# 6. LYRIA / SYNTH MUSIC + VERIFIED LOUD VOICEOVER + SFX MIXER
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
        "-af", f"volume=0.32,afade=t=in:st=0:d=0.30,afade=t=out:st={max(0.5, duration_sec - 0.8):.3f}:d=0.8",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.28) * math.pi)
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * env * 0.20
    if cue == "record_scratch":
        env = math.exp(-dt * 6.0)
        freq = 660.0 * math.exp(-dt * 5.2) + 95.0 * math.sin(dt * 95.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.30
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.5)
        freq = 74.0 * math.exp(-dt * 1.7)
        return math.sin(2 * math.pi * freq * dt) * env * 0.36
    if cue == "riser_hit":
        if dt < 0.35:
            return math.sin(2 * math.pi * (220 + 1300 * dt) * dt) * (dt / 0.35) * 0.20
        env = math.exp(-(dt - 0.35) * 7.5)
        return math.sin(2 * math.pi * 64.0 * dt) * env * 0.32
    env = math.exp(-dt * 15.0)
    return math.sin(2 * math.pi * 987.77 * dt) * env * 0.18


def build_director_audio(music_prompt, bpm, scenes, beat_starts, voice_tracks, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating groove underscore...")
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
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.024
                s = int(max(-0.9, min(0.9, val)) * 32767)
                frames.extend(struct.pack("<hh", s, s))
            wf.writeframes(frames)

    sr = 48000
    total_samples = int(sr * duration_sec)
    voice_mix = [0.0] * (total_samples * 2)
    sfx_mix = [0.0] * (total_samples * 2)

    cues = [
        (beat_starts[i] + (0.05 if i == 0 else 0.0), scenes[i].get("sfx_cue", "pop_ding"))
        for i in range(len(scenes))
    ]
    if duration_sec > 3.2:
        cues.append((duration_sec - 2.6, "pop_ding"))

    for start_t, cue_name in cues:
        s0 = int(start_t * sr)
        s1 = min(total_samples, int((start_t + 0.55) * sr))
        for idx in range(s0, s1):
            val = _synth_cue_sample(cue_name, (idx / sr) - start_t)
            sfx_mix[idx * 2] += val
            sfx_mix[idx * 2 + 1] += val

    for i, v_path in enumerate(voice_tracks):
        if v_path and pathlib.Path(v_path).exists():
            with wave.open(str(v_path), "rb") as wf:
                raw = wf.readframes(wf.getnframes())
            v_ints = struct.unpack(f"<{len(raw) // 2}h", raw)
            offset_samp = int((beat_starts[i] + 0.12) * sr) * 2
            limit = min(len(v_ints), len(voice_mix) - offset_samp)
            for k in range(max(0, limit)):
                voice_mix[offset_samp + k] += (v_ints[k] / 32768.0) * 1.15

    voice_only_wav = final_wav.parent / "voice_only.wav"
    sfx_only_wav = final_wav.parent / "sfx_only.wav"

    for out_p, buf in ((voice_only_wav, voice_mix), (sfx_only_wav, sfx_mix)):
        with wave.open(str(out_p), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            out_bytes = bytearray()
            for val in buf:
                s = int(max(-0.96, min(0.96, val)) * 32767)
                out_bytes.extend(struct.pack("<h", s))
            wf.writeframes(out_bytes)

    if not _wav_has_audible_voice(voice_only_wav):
        raise RuntimeError("Master voice track check failed: voice_only.wav is silent!")

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(voice_only_wav), "-i", str(sfx_only_wav),
        "-filter_complex",
        "[1:a]asplit=2[v_sc][v_mix];"
        "[0:a][v_sc]sidechaincompress=threshold=0.015:ratio=14:attack=8:release=280[ducked_bed];"
        "[ducked_bed][2:a]amix=inputs=2:duration=first:weights=0.55 0.75[bg_sfx];"
        "[bg_sfx][v_mix]amix=inputs=2:duration=first:weights=0.45 1.35,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# 7. VFX LIGHTING, CAMERA CHOREOGRAPHY, KARAOKE CAPTIONS & STORY-MATCHED END CTA
# ==============================================================================
def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _lerp_color(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def build_vignette_mask(strength=0.14):
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


def build_ambient_glow_mask(strength=0.12):
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
    colors = [(255, 215, 110), (145, 218, 255), (255, 118, 214), (165, 235, 180)]
    return [
        {
            "x": rng.uniform(0.04, 0.96),
            "y": rng.uniform(0.05, 0.95),
            "depth": rng.uniform(0.45, 1.0),
            "speed": rng.uniform(0.55, 1.25),
            "size": rng.randint(3, 7),
            "phase": rng.uniform(0, math.pi * 2),
            "col": rng.choice(colors)
        }
        for _ in range(count)
    ]


def apply_vfx_grade_and_atmosphere(frame, sc, env_key, local_p, t, vignette_mask, glow_mask, particle_seeds):
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

    env_fx = ENVIRONMENT_PRESETS.get(env_key, {}).get("effect", "none")
    if env_fx != "none":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        base_alpha = 255 * VISUAL_TUNING["particle_opacity"]

        for p in particle_seeds:
            depth = p["depth"]
            spd = p["speed"] * (0.6 + 0.5 * depth)
            p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
            px = int(((p["x"] + math.sin(t * 1.4 + p["phase"]) * 0.03) % 1.0) * W)
            if env_fx == "confetti":
                py = int(((p["y"] + t * 0.08 * spd) % 1.0) * H)
                r = max(3, int(p["size"] * depth))
                odraw.rectangle([px - r, py - r // 2, px + r, py + r // 2], fill=(p["col"][0], p["col"][1], p["col"][2], p_alpha))
            elif env_fx == "sparks":
                py = int(((p["y"] - t * 0.10 * spd) % 1.0) * H)
                r = max(2, int(p["size"] * depth))
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 130, 230, p_alpha))
            else:
                py = int(((p["y"] - t * 0.025 * spd) % 1.0) * H)
                r = max(2, int(p["size"] * depth))
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.55)))

        graded = Image.alpha_composite(graded.convert("RGBA"), overlay).convert("RGB")

    return graded


def apply_camera_trajectory(base_img, move, local_p, speech_amp, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    idle_breath = math.sin(t * 2.0) * 0.003
    voice_micro_pulse = speech_amp * 0.012

    if move == "pull_back_reveal":
        zoom = (1.03 + max_z) - (max_z * _ease_out_quart(local_p)) + idle_breath + voice_micro_pulse
    elif move == "snap_zoom_face":
        if local_p < 0.12:
            zoom = 1.02 + (max_z * 1.25) * _ease_out_quart(local_p / 0.12)
        else:
            zoom = (1.02 + max_z * 1.25) - (max_z * 0.20 * _ease_in_out_sine((local_p - 0.12) / 0.88)) + voice_micro_pulse
    elif move == "party_dance_bounce":
        beat_bounce = abs(math.sin(t * 7.4)) * 0.028
        zoom = 1.04 + beat_bounce + voice_micro_pulse
    elif move == "gentle_float":
        zoom = 1.03 + math.sin(_ease_in_out_sine(local_p) * math.pi) * 0.03 + voice_micro_pulse
    else:
        zoom = 1.02 + (max_z * _ease_in_out_sine(local_p)) + idle_breath + voice_micro_pulse

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
    elif move == "party_dance_bounce":
        x0 = max(0, min(max_dx, (max_dx // 2) + int(math.sin(t * 3.7) * min(16, max_dx // 2))))
        y0 = max(0, min(max_dy, (max_dy // 2) + int(abs(math.cos(t * 7.4)) * min(14, max_dy // 2))))
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


def _draw_vector_social_icons(odraw, cx, cy, alpha, accent):
    """Draws crisp vector Heart, Comment Bubble, Share Arrow, and Follow '+' badges."""
    hx = cx - 210
    odraw.ellipse([hx - 11, cy - 8, hx, cy + 3], fill=(255, 82, 102, alpha))
    odraw.ellipse([hx, cy - 8, hx + 11, cy + 3], fill=(255, 82, 102, alpha))
    odraw.polygon([(hx - 11, cy - 1), (hx + 11, cy - 1), (hx, cy + 12)], fill=(255, 82, 102, alpha))

    bx = cx - 72
    odraw.rounded_rectangle([bx - 12, cy - 10, bx + 12, cy + 7], radius=5, fill=(130, 212, 255, alpha))
    odraw.polygon([(bx - 6, cy + 7), (bx, cy + 7), (bx - 9, cy + 13)], fill=(130, 212, 255, alpha))

    sx = cx + 68
    odraw.polygon([(sx - 12, cy + 1), (sx + 12, cy - 10), (sx + 3, cy + 11), (sx - 1, cy + 3)], fill=(142, 240, 178, alpha))

    fx = cx + 206
    odraw.ellipse([fx - 12, cy - 12, fx + 12, cy + 12], fill=(accent[0], accent[1], accent[2], alpha))
    odraw.line([(fx - 6, cy), (fx + 6, cy)], fill=(18, 18, 22, alpha), width=3)
    odraw.line([(fx, cy - 6), (fx, cy + 6)], fill=(18, 18, 22, alpha), width=3)


def draw_story_matched_end_card(frame, script_data, sc, handle, remaining_sec):
    """Positioned safely above Instagram's native bottom UI overlay (y < 1600) and below subtitles."""
    if remaining_sec > 2.6:
        return frame

    appear_p = min(1.0, (2.6 - remaining_sec) / 0.30)
    eased = _ease_out_quart(appear_p)
    alpha = int(244 * eased)

    g1 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    acc = g1["accent"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    prompt_font = _load_font(25)
    action_font = _load_font(23)

    story_cta = (script_data.get("end_card_cta") or f"Enjoyed the vibe? Follow {handle}").strip()
    actions_line = f"LIKE    •    COMMENT    •    SHARE    •    FOLLOW {handle}"

    b1 = odraw.textbbox((0, 0), story_cta, font=prompt_font)
    b2 = odraw.textbbox((0, 0), actions_line, font=action_font)
    card_w = min(W - 110, max(b1[2] - b1[0], b2[2] - b2[0]) + 84)
    card_h = 114

    slide_y = int((1.0 - eased) * 18)
    x0 = (W - card_w) // 2
    x1 = x0 + card_w
    y0 = 1480 + slide_y
    y1 = y0 + card_h

    odraw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=26,
        fill=(14, 16, 24, alpha),
        outline=(acc[0], acc[1], acc[2], alpha),
        width=3
    )

    odraw.text((W // 2, y0 + 26), story_cta, font=prompt_font, fill=(acc[0], acc[1], acc[2], alpha), anchor="mm")
    _draw_vector_social_icons(odraw, W // 2, y0 + 60, alpha, acc)
    odraw.text((W // 2, y0 + 91), actions_line, font=action_font, fill=(248, 250, 255, alpha), anchor="mm")

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def draw_karaoke_speech_overlays(frame, top_hook, sc, word_timings, speech_amp, scene_t, t, handle, show_watermark=True):
    """Renders upper hook + live voice-reactive speaker pill + word-by-word karaoke captions in IG safe zone."""
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    acc = g1["accent"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 1. Upper-Third Hook Banner
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

    # 2. Speaker Name Tag + Live Equalizer Bars + Word-by-Word Karaoke Subtitles (Safe Zone y=1218..1465)
    spk = (sc.get("speaker") or "Phil").strip()
    spk_col = CAST_IDENTITY.get(spk, CAST_IDENTITY["Phil"])["accent_rgb"]
    cap_in = _ease_out_quart(min(1.0, scene_t / 0.14))
    cap_alpha = int(252 * cap_in)

    tag_font = _load_font(28)
    tag_text = f"{spk.upper()}"
    tbbox = odraw.textbbox((0, 0), tag_text, font=tag_font)
    tw = (tbbox[2] - tbbox[0]) + 78
    th = 44
    tx0 = 104
    ty0 = 1218
    odraw.rounded_rectangle([tx0, ty0, tx0 + tw, ty0 + th], radius=16, fill=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), outline=(18, 18, 22, cap_alpha), width=4)

    for b_idx in range(3):
        bar_h = int(8 + speech_amp * 20 * (0.65 + 0.35 * abs(math.sin(t * 16.0 + b_idx * 1.4))))
        bx = tx0 + 22 + b_idx * 8
        by_mid = ty0 + th // 2
        odraw.rounded_rectangle([bx, by_mid - bar_h // 2, bx + 4, by_mid + bar_h // 2], radius=2, fill=(255, 255, 255, cap_alpha))

    odraw.text((tx0 + 54, ty0 + th // 2), tag_text, font=tag_font, fill=(255, 255, 255, cap_alpha), anchor="lm")

    dlg_font = _load_font(40)
    items = word_timings if word_timings else [{"word": w, "start": 0.0, "end": 99.0} for w in (sc.get("dialogue") or "").split()]
    rows = []
    cur_row = []
    cur_w = 0
    max_row_w = W - 240

    for idx_w, item in enumerate(items):
        w_str = item["word"]
        wb = odraw.textbbox((0, 0), w_str + " ", font=dlg_font)
        ww = wb[2] - wb[0]
        if cur_row and (cur_w + ww > max_row_w):
            rows.append(cur_row)
            cur_row = [(idx_w, item, ww)]
            cur_w = ww
        else:
            cur_row.append((idx_w, item, ww))
            cur_w += ww
    if cur_row:
        rows.append(cur_row)

    line_h = 56
    box_h = max(88, 30 + len(rows) * line_h)
    x0, y0 = 92, 1268
    x1, y1 = W - 92, y0 + box_h
    odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(14, 16, 24, min(244, cap_alpha)), outline=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), width=4)

    start_y = y0 + (box_h - len(rows) * line_h) // 2 + line_h // 2
    for r_idx, row in enumerate(rows):
        row_total_w = sum(entry[2] for entry in row)
        rx = (W - row_total_w) // 2
        ry = start_y + r_idx * line_h

        for idx_w, item, ww in row:
            w_str = item["word"]
            w_start = item["start"]
            w_end = item["end"]
            is_current = (w_start <= scene_t <= w_end)
            is_spoken = (scene_t >= w_start)

            wb_exact = odraw.textbbox((0, 0), w_str, font=dlg_font)
            word_w = wb_exact[2] - wb_exact[0]
            word_h = wb_exact[3] - wb_exact[1]

            if is_current:
                odraw.rounded_rectangle(
                    [rx - 8, ry - word_h // 2 - 7, rx + word_w + 8, ry + word_h // 2 + 9],
                    radius=12,
                    fill=(255, 224, 66, cap_alpha),
                    outline=(18, 18, 22, cap_alpha),
                    width=3
                )
                txt_col = (18, 18, 22, cap_alpha)
            elif is_spoken:
                txt_col = (255, 255, 255, cap_alpha)
            else:
                txt_col = (175, 182, 198, int(cap_alpha * 0.72))

            odraw.text((rx, ry), w_str, font=dlg_font, fill=txt_col, anchor="lm")
            rx += ww

    # 3. Clean Handle Watermark (clears Instagram's bottom UI overlay)
    if show_watermark:
        handle_font = _load_font(28)
        odraw.text((W // 2, 1545), handle, font=handle_font, fill=(255, 255, 255, 235), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_director_reel(page_cfg, script_data, seed, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        scenes = script_data["scenes"][:4]
        total_beats = len(scenes)
        characters = seed["characters"]
        env_key = script_data.get("environment_key", seed["scenario"]["env"])
        story_context = seed["scenario"]["story_seed"]

        cgi_frames = []
        anchor_path = None
        for idx, sc in enumerate(scenes):
            cgi_path = tmp_dir / f"cgi_{idx}.png"
            img = generate_cgi_scene_frame(
                characters, env_key, sc, story_context, cgi_path, ref_image_path=anchor_path
            )
            if idx == 0:
                anchor_path = cgi_path
            cgi_frames.append(img)

        beat_durations, voice_tracks, energy_timelines, word_timings_all = compute_beat_durations_and_voices(scenes, tmp_dir)
        beat_starts = []
        acc_t = 0.0
        for d in beat_durations:
            beat_starts.append(acc_t)
            acc_t += d
        total_dur = acc_t
        print(f"Rendered CGI voiced timing ({total_dur:.2f}s total): {beat_durations}")

        final_wav = tmp_dir / "final_director.wav"
        build_director_audio(
            script_data.get("music_prompt", "Chill upbeat funk-pop comedy groove instrumental"),
            script_data.get("music_bpm", 112),
            scenes,
            beat_starts,
            voice_tracks,
            total_dur,
            final_wav
        )

        total_frames = int(total_dur * FPS)
        top_hook = script_data.get("top_hook", seed["scenario"]["hook"])
        vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
        glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
        particle_seeds = generate_particle_seeds(28)
        prev_rendered_frame = None

        ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{W}x{H}",
                "-r", str(FPS),
                "-i", "-",
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
            ],
            stdin=subprocess.PIPE
        )

        try:
            for f_idx in range(total_frames):
                t = f_idx / FPS
                remaining_sec = max(0.0, total_dur - t)
                s_idx = total_beats - 1
                for i in range(total_beats):
                    if i == total_beats - 1 or t < beat_starts[i + 1]:
                        s_idx = i
                        break

                sc = scenes[s_idx]
                beat_dur = beat_durations[s_idx]
                scene_t = t - beat_starts[s_idx]
                local_p = min(1.0, max(0.0, scene_t / beat_dur))
                local_f = int(scene_t * FPS)
                e_list = energy_timelines[s_idx]
                speech_amp = e_list[local_f] if local_f < len(e_list) else 0.0

                frame = apply_camera_trajectory(cgi_frames[s_idx], sc.get("camera_move", "dolly_push_in"), local_p, speech_amp, t)
                frame = apply_vfx_grade_and_atmosphere(frame, sc, env_key, local_p, t, vignette_mask, glow_mask, particle_seeds)

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

                frame = draw_karaoke_speech_overlays(
                    frame=frame,
                    top_hook=top_hook,
                    sc=sc,
                    word_timings=word_timings_all[s_idx],
                    speech_amp=speech_amp,
                    scene_t=scene_t,
                    t=t,
                    handle=page_cfg["handle"],
                    show_watermark=(remaining_sec > 2.6)
                )

                frame = draw_story_matched_end_card(
                    frame=frame,
                    script_data=script_data,
                    sc=sc,
                    handle=page_cfg["handle"],
                    remaining_sec=remaining_sec
                )

                ffmpeg_proc.stdin.write(frame.tobytes())
        finally:
            if ffmpeg_proc.stdin:
                ffmpeg_proc.stdin.close()
            ret = ffmpeg_proc.wait()
            if ret != 0:
                raise RuntimeError(f"FFmpeg video encoding failed with exit code {ret}")

        print(f"Rendered CGI/VFX Voiced Reel with Story-Matched End CTA ({total_dur:.1f}s): {out_mp4}")
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# 8. GITHUB PAGES HOSTING & META GRAPH API V21.0 PUBLISHING
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
    base = f"https://{host}/{GRAPH_VERSION}/{ig_id}"

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
        status_url = f"https://{host}/{GRAPH_VERSION}/{creation_id}?fields=status_code,status&access_token={token}"
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
    base = f"https://{host}/{GRAPH_VERSION}/{fb_page_id}/video_reels"

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
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    hour = now_est.hour

    if 5 <= hour < 12:
        time_slot_vibe = "MORNING CHILL & HUMOR: Coffee math, airport early birds, or morning patio vibes."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON VIBE: Beach sunset boardwalk, gym buddy comedy, grocery cart traps, or couch relaxation."
    else:
        time_slot_vibe = "EVENING / NIGHT ENERGY: Sunset rooftop party dance, Friday house party escape, late-night drive-thru, or solo car concert."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=40)
        recent_hooks = "\n".join(f"- {h.get('top_hook', '')}" for h in recent_history[-12:] if h.get("top_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history)
        scen = seed["scenario"]
        cast_descriptions = "\n".join(
            f"- {c}: {CAST_IDENTITY[c]['archetype']} | Visuals: {CAST_IDENTITY[c]['visual_bible']}"
            for c in seed["characters"]
        )

        prompt = (
            f"You are an Emmy-winning Comedy Showrunner & 3D CGI Animation Director for {page['handle']}.\n"
            f"BRAND IDENTITY: {page['domain']}\n\n"
            "### CREATIVE DIRECTION BRIEF (FRESH, NON-REPEATING EPISODE)\n"
            f"- Episode Vibe: {scen['vibe']} | Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Cast (KEEP EXACT NAMES & PERSONALITIES):\n{cast_descriptions}\n"
            f"- Hook Title: {scen['hook']}\n"
            f"- Story Premise: {scen['story_seed']}\n"
            f"- Real-World Setting: {scen['env']} ({ENVIRONMENT_PRESETS[scen['env']]['desc']})\n"
            f"- Clock / Progression Labels: {scen['clocks']}\n"
            f"- Time of Day Mood: {time_slot_vibe}\n"
            f"- Optional Cultural Inspiration:\n{trends}\n"
            f"- NEVER REPEAT THESE RECENT HOOKS:\n{recent_hooks}\n\n"
            "### HUMAN COMEDY & CINEMATIC CGI STORYBOARD RULES\n"
            "1. WRITE LIKE A REAL COMEDY WRITER: Funny, witty, warm, chill, and relatable. Avoid robotic phrasing. Give each character their distinct voice (Phil = smooth charmer, Alan = deadpan philosopher, Stu = lovable overthinker, Doug = chill laid-back king).\n"
            "2. EVEN IN SOLO REELS: Make it a vibe — relaxing, dancing in the driver's seat, enjoying peace on the couch, or hyping up the weekend with charismatic monologue/banter.\n"
            "3. SPOKEN DIALOGUE: Every beat has 1 active 'speaker' from the active cast and 7–13 words of punchy spoken 'dialogue' that syncs cleanly to voiceover.\n"
            "4. RICH CGI SCENE DESCRIPTIONS: In 'cgi_scene_description', describe exact physical poses, real objects (steering wheel, dashboard gauges, iced coffee cups, disco lights, leather seats, shopping cart), and facial expressions so the 3D CGI renderer creates a movie-grade frame.\n"
            "5. STORY-MATCHED END CTA ('end_card_cta'): Write ONE short, witty, non-spammy outro prompt (max 50 characters, NO emojis) tailored specifically to THIS episode's joke that naturally invites viewers to like, comment, share, or follow.\n\n"
            "### RETURN ONLY VALID JSON\n"
            "{\n"
            '  "reel_mode": "spoken_skit",\n'
            f'  "top_hook": "{scen["hook"]}",\n'
            f'  "environment_key": "{scen["env"]}",\n'
            '  "end_card_cta": "Short witty episode-specific CTA (max 50 chars, no emojis)",\n'
            '  "music_prompt": "Chill upbeat funk-pop comedy groove instrumental",\n'
            '  "music_bpm": 112,\n'
            '  "scenes": [\n'
            f'    {{"clock_label": "{scen["clocks"][0]}", "speaker": "{seed["characters"][0]}", "dialogue": "Spoken line 1 (7-13 words)", "shot_framing": "group_shot", "expression": "chill_relaxed_smile", "end_expression": "chill_relaxed_smile", "body_action": "driving_hands_on_wheel", "cgi_scene_description": "Detailed 3D CGI visual description of Beat 1 with real objects and expressions", "start_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "end_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "sfx_cue": "pop_ding"}},\n'
            f'    {{"clock_label": "{scen["clocks"][1]}", "speaker": "{seed["characters"][-1]}", "dialogue": "Spoken line 2 (7-13 words)", "shot_framing": "speaker_closeup", "expression": "laughing_joyful", "end_expression": "smug_confident_grin", "body_action": "point_and_explain", "cgi_scene_description": "Detailed 3D CGI close-up of speaker reacting", "start_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "end_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "camera_move": "pan_follow_right", "transition_in": "whip_pan_left", "sfx_cue": "whoosh"}},\n'
            f'    {{"clock_label": "{scen["clocks"][2]}", "speaker": "{seed["characters"][0]}", "dialogue": "Spoken line 3 (7-13 words)", "shot_framing": "speaker_closeup", "expression": "skeptical_side_eye", "end_expression": "panicked_wide_eyes", "body_action": "shrug_both_hands", "cgi_scene_description": "Detailed 3D CGI close-up comedic twist", "start_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "end_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "camera_move": "snap_zoom_face", "transition_in": "smash_zoom_cut", "sfx_cue": "record_scratch"}},\n'
            f'    {{"clock_label": "{scen["clocks"][3]}", "speaker": "{seed["characters"][-1]}", "dialogue": "Spoken line 4 punchline (7-13 words)", "shot_framing": "group_shot", "expression": "vibing_eyes_closed_groove", "end_expression": "laughing_joyful", "body_action": "party_dance_groove", "cgi_scene_description": "Detailed 3D CGI finale punchline shot", "start_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "end_grade": "{ENVIRONMENT_PRESETS[scen["env"]]["grade"]}", "camera_move": "party_dance_bounce", "transition_in": "whip_pan_right", "sfx_cue": "vine_boom_sub"}}\n'
            "  ],\n"
            '  "ig_caption": "Witty relatable caption inviting followers to tag a friend",\n'
            '  "pinned_comment": "Fun question for the comments"\n'
            "}\n"
            f"Allowed environment_key: {list(ENVIRONMENT_PRESETS.keys())}\n"
            f"Allowed expression / end_expression: {FACIAL_EXPRESSIONS}\n"
            f"Allowed body_action: {ALL_BODY_ACTIONS}\n"
            f"Allowed start_grade / end_grade: {list(COLOR_GRADES.keys())}\n"
            f"Allowed camera_move: {ALL_CAMERA_MOVES}\n"
            f"Allowed transition_in: {ALL_TRANSITIONS}\n"
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
            f"Beat {i+1} [{s.get('clock_label', '')}] ({s.get('speaker', 'Phil')}): {s.get('dialogue', '')}"
            for i, s in enumerate(script_data["scenes"][:4])
        )
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Scenario: {seed['scenario_id']} ({seed['vibe']})\nCast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nEnvironment: {script_data.get('environment_key', '')}\nHook: {script_data.get('top_hook', '')}\n{full_story_text}\nEnd CTA: {script_data.get('end_card_cta', '')}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "scenario_id": seed["scenario_id"],
            "vibe": seed["vibe"],
            "top_hook": script_data.get("top_hook", ""),
            "cast_mode": seed["cast_mode"],
            "characters": seed["characters"],
            "environment_key": script_data.get("environment_key", ""),
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
