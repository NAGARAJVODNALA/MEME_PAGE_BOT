import os
import math
import json
import time
import wave
import base64
import random
import shutil
import asyncio
import pathlib
import subprocess
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
DEFAULT_IG_USER_ID = "17841476835986162"
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920
SS = 2  # 2x supersampling (2160x3840 -> 1080x1920 Lanczos)

# ==============================================================================
# 6 COUPLE CAST PROFILES (APPEARANCE, OUTFITS, VOICES & SPEAKING CADENCE)
# ==============================================================================
COUPLE_PROFILES = [
    {
        "id": "white_couple",
        "label": "Liam & Chloe",
        "tone_guide": "Natural American millennial/Gen-Z couple banter: witty, dry deadpan humor mixed with warm affection.",
        "him": {
            "name": "Liam",
            "skin": (246, 224, 206),
            "hair": (92, 62, 42),
            "hair_style": "cap",
            "cap_color": (148, 76, 54),
            "top_color": (244, 242, 238),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Puck",
            "edge_voice": "en-US-AndrewNeural",
            "voice_style": "Speak naturally like a laid-back, witty 27-year-old American guy:",
        },
        "her": {
            "name": "Chloe",
            "skin": (248, 228, 212),
            "hair": (38, 28, 24),
            "hair_style": "bun",
            "top_color": (30, 32, 38),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AvaNeural",
            "voice_style": "Speak naturally like an expressive, playful 26-year-old American woman:",
        },
    },
    {
        "id": "indian_couple",
        "label": "Arjun & Priya",
        "tone_guide": "Authentic modern Indian couple banter: warm Indian-English rhythm, expressive reactions, loving teasing, chai/food/travel & romantic chemistry.",
        "him": {
            "name": "Arjun",
            "skin": (182, 132, 96),
            "hair": (22, 22, 26),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (74, 102, 84),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Orus",
            "edge_voice": "en-IN-PrabhatNeural",
            "voice_style": "Speak in natural, warm modern Indian English like a 28-year-old guy from Mumbai or Bengaluru:",
        },
        "her": {
            "name": "Priya",
            "skin": (192, 142, 106),
            "hair": (20, 20, 24),
            "hair_style": "long_straight",
            "top_color": (178, 72, 64),
            "bindi": True,
            "hoops": True,
            "gemini_voice": "Kore",
            "edge_voice": "en-IN-NeerjaExpressiveNeural",
            "voice_style": "Speak in natural, expressive modern Indian English like a witty 27-year-old woman:",
        },
    },
    {
        "id": "chinese_couple",
        "label": "Kevin & Mei",
        "tone_guide": "Relatable Chinese-American / modern Chinese couple banter: sharp deadpan comebacks, cozy late-night food & coffee debates, sweet understated romance.",
        "him": {
            "name": "Kevin",
            "skin": (238, 214, 192),
            "hair": (24, 24, 28),
            "hair_style": "side_part",
            "cap_color": None,
            "top_color": (44, 62, 88),
            "beard": False,
            "glasses": True,
            "gemini_voice": "Charon",
            "edge_voice": "en-SG-WayneNeural",
            "voice_style": "Speak naturally like a calm, dry-humored 27-year-old Chinese-American guy:",
        },
        "her": {
            "name": "Mei",
            "skin": (242, 220, 200),
            "hair": (24, 24, 28),
            "hair_style": "sleek_bob",
            "top_color": (228, 214, 196),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Leda",
            "edge_voice": "en-SG-LunaNeural",
            "voice_style": "Speak naturally like a smart, warm, slightly sassy 26-year-old Chinese-American woman:",
        },
    },
    {
        "id": "korean_couple",
        "label": "Minho & Jisoo",
        "tone_guide": "Playful Korean couple energy: K-drama style dramatic reactions, cute pouting, sweet romantic tension, aesthetic cafe & dinner dates.",
        "him": {
            "name": "Minho",
            "skin": (242, 222, 204),
            "hair": (26, 26, 30),
            "hair_style": "comma_hair",
            "cap_color": None,
            "top_color": (212, 198, 178),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-BrianNeural",
            "voice_style": "Speak naturally like a charming, relaxed 26-year-old Korean-American guy:",
        },
        "her": {
            "name": "Jisoo",
            "skin": (245, 226, 210),
            "hair": (32, 26, 26),
            "hair_style": "long_waves_bangs",
            "top_color": (186, 172, 214),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Zephyr",
            "edge_voice": "en-US-EmmaNeural",
            "voice_style": "Speak naturally like an expressive, sweet and playful 25-year-old Korean-American woman:",
        },
    },
    {
        "id": "interracial_wb_couple",
        "label": "Noah & Maya",
        "tone_guide": "Interracial couple (White guy & Black woman): high-chemistry playful roasting, sharp comedic timing, cozy romance and honest everyday talk.",
        "him": {
            "name": "Noah",
            "skin": (244, 222, 204),
            "hair": (128, 92, 58),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (56, 62, 68),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Puck",
            "edge_voice": "en-US-ChristopherNeural",
            "voice_style": "Speak naturally like a warm, humorous 28-year-old American guy:",
        },
        "her": {
            "name": "Maya",
            "skin": (118, 76, 52),
            "hair": (22, 18, 18),
            "hair_style": "afro_puffs",
            "top_color": (46, 118, 88),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AriaNeural",
            "voice_style": "Speak naturally like a confident, witty, expressive 27-year-old Black American woman:",
        },
    },
    {
        "id": "black_couple",
        "label": "Marcus & Zuri",
        "tone_guide": "Black couple banter: rich conversational chemistry, expressive eyebrow/hand reactions, hilarious everyday debates mixed with smooth romance.",
        "him": {
            "name": "Marcus",
            "skin": (104, 66, 44),
            "hair": (20, 18, 18),
            "hair_style": "fade_lineup",
            "cap_color": None,
            "top_color": (124, 44, 52),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-DavisNeural",
            "voice_style": "Speak naturally like a smooth, funny 28-year-old Black American man:",
        },
        "her": {
            "name": "Zuri",
            "skin": (136, 88, 60),
            "hair": (22, 18, 18),
            "hair_style": "box_braids",
            "top_color": (208, 156, 64),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Kore",
            "edge_voice": "en-US-JennyNeural",
            "voice_style": "Speak naturally like a vibrant, expressive, loving 27-year-old Black American woman:",
        },
    },
]

STORY_GENRES = [
    "playful_argument",
    "cozy_cuddle_couch",
    "romantic_flirty_dinner",
    "coffee_or_lunch_date",
    "destination_adventure",
    "heartfelt_comfort_sweet",
]

SETTINGS = [
    "couch_cozy",
    "cafe_lunch",
    "dinner_romantic",
    "destination_sunset",
]

EXPRESSIONS = [
    "chill_smirk",
    "smug_eyes_closed",
    "deadpan",
    "excited_wide",
    "skeptical",
    "exasperated",
    "shocked",
    "pout_frown",
    "soft_love_smile",
]

HER_POSES = [
    "hands_on_lap_lean",
    "open_palm_invite",
    "both_hands_plead",
    "hands_on_hips",
    "arms_up_exasperated",
    "arms_crossed_pout",
    "facepalm_sigh",
    "cozy_lean_heart",
    "cheers_glass_raise",
]

HIM_POSES = [
    "couch_chill_recline",
    "couch_hand_gesture",
    "couch_shrug_palm",
    "couch_cozy_arm_around",
    "table_lean_talk",
    "table_count_two",
    "table_cheers_toast",
]


def build_https_url(host, path, query_params=None):
    query = urllib.parse.urlencode(query_params) if query_params else ""
    return urllib.parse.urlunparse(("https", host, path, "", query, ""))


def verify_runtime_environment():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY secret in GitHub Actions.")
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
            print(f"pages.json skipped ({e}), using default @wearechillclub config.")
    return [{
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "ig_user_id": os.environ.get("IG_USER_ID", DEFAULT_IG_USER_ID).strip() or DEFAULT_IG_USER_ID,
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "domain": (
            "Real-life couple stories: relatable comedy, playful arguments, cozy couch nights, "
            "flirty candlelight dinners, coffee/lunch dates, destination trips, and heartfelt moments"
        ),
    }]


def fetch_world_context():
    headlines = []
    try:
        rss_url = build_https_url("trends.google.com", "/trending/rss", {"geo": "US"})
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
            for el in root.findall(".//item/title")[:5]:
                if el.text:
                    headlines.append(el.text.strip())
    except Exception:
        pass
    return "\n".join(f"- {h}" for h in headlines) if headlines else "- Everyday real couple life"


# ==============================================================================
# PERSISTENT HISTORY & 6-COUPLE / GENRE ROTATION
# ==============================================================================
def load_story_history(slug, limit=120):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return items[-limit:]
        except Exception:
            return []
    return []


def save_story_record(slug, entry):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                items = []
        except Exception:
            items = []
    items.append(entry)
    hist_path.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


def pick_next_couple_and_genre(history_items):
    used_couples = [h.get("couple_id") for h in history_items[-5:] if h.get("couple_id")]
    available_couples = [c for c in COUPLE_PROFILES if c["id"] not in used_couples]
    couple = random.choice(available_couples or COUPLE_PROFILES)

    used_genres = [h.get("genre") for h in history_items[-4:] if h.get("genre")]
    available_genres = [g for g in STORY_GENRES if g not in used_genres]
    genre = random.choice(available_genres or STORY_GENRES)
    return couple, genre


# ==============================================================================
# NATURAL COUPLE STORY GENERATOR (HOOK + REAL HUMAN DIALOGUE)
# ==============================================================================
def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def _genre_to_default_setting(genre):
    return {
        "playful_argument": "couch_cozy",
        "cozy_cuddle_couch": "couch_cozy",
        "romantic_flirty_dinner": "dinner_romantic",
        "coffee_or_lunch_date": "cafe_lunch",
        "destination_adventure": "destination_sunset",
        "heartfelt_comfort_sweet": "couch_cozy",
    }.get(genre, "couch_cozy")


def _fallback_couple_script(couple, genre, history_items):
    setting = _genre_to_default_setting(genre)
    him_name = couple["him"]["name"]
    her_name = couple["her"]["name"]

    bank = {
        "romantic_flirty_dinner": {
            "topic": f"{him_name} & {her_name}: Candlelight Dinner Confession",
            "setting": "dinner_romantic",
            "dialogue": [
                {"speaker": "B", "line": "Why are you staring at me instead of the menu?", "expr_a": "soft_love_smile", "expr_b": "chill_smirk", "pose_a": "table_lean_talk", "pose_b": "open_palm_invite", "camera": "two_shot"},
                {"speaker": "A", "line": "Because everything on the menu is second place tonight.", "expr_a": "soft_love_smile", "expr_b": "excited_wide", "pose_a": "table_lean_talk", "pose_b": "cozy_lean_heart", "camera": "focus_a"},
                {"speaker": "B", "line": "Oh so you practiced that line in the car?", "expr_a": "chill_smirk", "expr_b": "chill_smirk", "pose_a": "table_cheers_toast", "pose_b": "cheers_glass_raise", "camera": "two_shot"},
                {"speaker": "A", "line": "All afternoon. Did it work?", "expr_a": "smug_eyes_closed", "expr_b": "soft_love_smile", "pose_a": "table_cheers_toast", "pose_b": "cozy_lean_heart", "camera": "two_shot"},
                {"speaker": "B", "line": "Order the dessert and maybe I'll tell you.", "expr_a": "excited_wide", "expr_b": "chill_smirk", "pose_a": "table_lean_talk", "pose_b": "cheers_glass_raise", "camera": "punchline_b"},
            ],
            "ig_caption": f"Date night energy with {him_name} & {her_name}. #wearechillclub #couplegoals #datenight #animatedreels",
            "pinned_comment": "Smooth line or cheesy line—be honest in the comments!",
        },
        "destination_adventure": {
            "topic": f"{him_name} & {her_name}: Sunset Photo Shoot",
            "setting": "destination_sunset",
            "dialogue": [
                {"speaker": "B", "line": "Wait, take just one more picture before the sun drops!", "expr_a": "deadpan", "expr_b": "excited_wide", "pose_a": "table_lean_talk", "pose_b": "both_hands_plead", "camera": "two_shot"},
                {"speaker": "A", "line": "Babe, I already took forty-seven angles of this exact rock.", "expr_a": "deadpan", "expr_b": "pout_frown", "pose_a": "table_count_two", "pose_b": "hands_on_hips", "camera": "two_shot"},
                {"speaker": "B", "line": "None of them caught the golden hour wind!", "expr_a": "skeptical", "expr_b": "exasperated", "pose_a": "table_lean_talk", "pose_b": "arms_up_exasperated", "camera": "two_shot"},
                {"speaker": "A", "line": "Fine, look at me—actually, you really do look incredible.", "expr_a": "soft_love_smile", "expr_b": "soft_love_smile", "pose_a": "table_lean_talk", "pose_b": "cozy_lean_heart", "camera": "punchline_a"},
            ],
            "ig_caption": f"Every vacation starts with 47 test photos. #wearechillclub #coupletravel #relatable #reels",
            "pinned_comment": "How many photos does your partner make you take on vacation?",
        },
        "coffee_or_lunch_date": {
            "topic": f"{him_name} & {her_name}: 'I'm Not Hungry' Fries Tax",
            "setting": "cafe_lunch",
            "dialogue": [
                {"speaker": "A", "line": "Hey, didn't you say you weren't hungry ten minutes ago?", "expr_a": "skeptical", "expr_b": "chill_smirk", "pose_a": "table_lean_talk", "pose_b": "hands_on_lap_lean", "camera": "two_shot"},
                {"speaker": "B", "line": "I'm not! I'm just quality-testing your fries.", "expr_a": "deadpan", "expr_b": "smug_eyes_closed", "pose_a": "table_lean_talk", "pose_b": "open_palm_invite", "camera": "two_shot"},
                {"speaker": "A", "line": "You already ate half the basket!", "expr_a": "shocked", "expr_b": "chill_smirk", "pose_a": "table_count_two", "pose_b": "hands_on_hips", "camera": "two_shot"},
                {"speaker": "B", "line": "And I saved you from half the calories. You're welcome.", "expr_a": "deadpan", "expr_b": "smug_eyes_closed", "pose_a": "table_lean_talk", "pose_b": "cozy_lean_heart", "camera": "punchline_b"},
            ],
            "ig_caption": f"The universal girlfriend fry tax is undefeated. #wearechillclub #coffeedate #couplecomedy #reels",
            "pinned_comment": "Who steals whose food on lunch dates?",
        },
    }
    if genre in bank:
        return bank[genre]

    return {
        "topic": f"{him_name} & {her_name}: Cozy Night In",
        "setting": setting,
        "dialogue": [
            {"speaker": "B", "line": "Be honest. Are we actually going out tonight or staying in?", "expr_a": "chill_smirk", "expr_b": "skeptical", "pose_a": "couch_chill_recline", "pose_b": "hands_on_lap_lean", "camera": "two_shot"},
            {"speaker": "A", "line": "I already put on my comfort sweats. There's no turning back.", "expr_a": "smug_eyes_closed", "expr_b": "exasperated", "pose_a": "couch_shrug_palm", "pose_b": "hands_on_hips", "camera": "two_shot"},
            {"speaker": "B", "line": "You didn't even ask what I wanted to do!", "expr_a": "chill_smirk", "expr_b": "pout_frown", "pose_a": "couch_chill_recline", "pose_b": "arms_crossed_pout", "camera": "two_shot"},
            {"speaker": "A", "line": "I already ordered your favorite takeout and queued our show.", "expr_a": "soft_love_smile", "expr_b": "excited_wide", "pose_a": "couch_cozy_arm_around", "pose_b": "cozy_lean_heart", "camera": "two_shot"},
            {"speaker": "B", "line": "Okay fine, scoot over. Give me the blanket.", "expr_a": "soft_love_smile", "expr_b": "soft_love_smile", "pose_a": "couch_cozy_arm_around", "pose_b": "cozy_lean_heart", "camera": "punchline_a"},
        ],
        "ig_caption": f"Canceling plans together is true romance. #wearechillclub #cozycouple #relatable #reels",
        "pinned_comment": "Staying in with takeout or going out—what's your pick?",
    }


def normalize_script(raw, couple, genre, history_items):
    if not isinstance(raw, dict) or not isinstance(raw.get("dialogue"), list) or len(raw["dialogue"]) < 4:
        return _fallback_couple_script(couple, genre, history_items)

    setting = raw.get("setting") if raw.get("setting") in SETTINGS else _genre_to_default_setting(genre)
    default_pose_a = "couch_chill_recline" if setting == "couch_cozy" else "table_lean_talk"
    clean_lines = []
    raw_dialogue = [d for d in raw["dialogue"][:9] if isinstance(d, dict)]

    for idx, item in enumerate(raw_dialogue):
        sp = "A" if str(item.get("speaker", "A")).strip().upper().startswith("A") else "B"
        line = " ".join(str(item.get("line") or "").strip().split())
        if not line:
            continue
        words = line.split()
        if len(words) > 13:
            line = " ".join(words[:13])

        pose_a = item.get("pose_a") if item.get("pose_a") in HIM_POSES else default_pose_a
        if setting == "couch_cozy" and not pose_a.startswith("couch_"):
            pose_a = "couch_hand_gesture" if sp == "A" else "couch_chill_recline"
        elif setting != "couch_cozy" and not pose_a.startswith("table_"):
            pose_a = "table_cheers_toast" if setting == "dinner_romantic" else "table_lean_talk"

        pose_b = item.get("pose_b") if item.get("pose_b") in HER_POSES else "hands_on_lap_lean"
        last_sp_cam = "punchline_a" if sp == "A" else "punchline_b"
        cam = last_sp_cam if idx == len(raw_dialogue) - 1 else (
            item.get("camera") if item.get("camera") in ("two_shot", "focus_a", "focus_b", "punchline_a", "punchline_b") else "two_shot"
        )

        clean_lines.append({
            "speaker": sp,
            "line": line,
            "expr_a": item.get("expr_a") if item.get("expr_a") in EXPRESSIONS else "chill_smirk",
            "expr_b": item.get("expr_b") if item.get("expr_b") in EXPRESSIONS else "skeptical",
            "pose_a": pose_a,
            "pose_b": pose_b,
            "camera": cam,
        })

    if len(clean_lines) < 4:
        return _fallback_couple_script(couple, genre, history_items)

    topic = str(raw.get("topic") or f"{couple['label']} Story").strip()
    return {
        "couple_id": couple["id"],
        "couple_label": couple["label"],
        "genre": genre,
        "topic": topic,
        "setting": setting,
        "dialogue": clean_lines,
        "ig_caption": str(raw.get("ig_caption") or f"{topic} #wearechillclub #couplegoals #relatable #reels").strip(),
        "pinned_comment": str(raw.get("pinned_comment") or "Tag your person if this is literally you two!").strip(),
    }


def generate_dialogue_with_gemini(page_cfg, couple, genre, history_items, world_context):
    past_topics = [f"- {h.get('topic', '')}" for h in history_items[-40:] if h.get("topic")]
    past_block = "\n".join(past_topics) if past_topics else "- None yet"
    default_setting = _genre_to_default_setting(genre)

    prompt = (
        f"Write a captivating, realistic 16-to-24-second animated COUPLE story for {page_cfg['handle']}.\n"
        f"FEATURED COUPLE: {couple['label']}\n"
        f"COUPLE VOICE & CULTURAL TONE: {couple['tone_guide']}\n"
        f"TODAY'S STORY MOOD / GENRE: {genre} (recommended setting: {default_setting})\n\n"
        "ALREADY USED TOPICS (NEVER REPEAT):\n"
        f"{past_block}\n\n"
        "OPTIONAL TRENDING INSPIRATION:\n"
        f"{world_context}\n\n"
        "STORYTELLING RULES (MAKE VIEWERS HOOKED FROM SECOND 1):\n"
        "1. Line 1 MUST be an immediate, relatable hook that stops scrolling (a bold question, playful accusation, romantic confession, or funny dilemma).\n"
        "2. Write 6 to 8 snappy, natural spoken lines (4 to 11 words each) sounding like real people talking—contractions, warmth, comedic timing, or tender emotion matching the genre.\n"
        "3. Vary body language across turns so both characters physically act out the scene.\n\n"
        "Return ONLY valid JSON with keys:\n"
        "- topic (short string)\n"
        "- setting ('couch_cozy', 'cafe_lunch', 'dinner_romantic', or 'destination_sunset')\n"
        "- dialogue (list of objects with: speaker ('A' for him, 'B' for her), line, expr_a, expr_b, pose_a, pose_b, camera)\n"
        "  Valid expr_a/expr_b: chill_smirk, smug_eyes_closed, deadpan, excited_wide, skeptical, exasperated, shocked, pout_frown, soft_love_smile\n"
        "  Valid pose_a (for couch_cozy): couch_chill_recline, couch_hand_gesture, couch_shrug_palm, couch_cozy_arm_around\n"
        "  Valid pose_a (for cafe_lunch/dinner_romantic/destination_sunset): table_lean_talk, table_count_two, table_cheers_toast\n"
        "  Valid pose_b: hands_on_lap_lean, open_palm_invite, both_hands_plead, hands_on_hips, arms_up_exasperated, arms_crossed_pout, facepalm_sigh, cozy_lean_heart, cheers_glass_raise\n"
        "  Valid camera: two_shot, focus_a, focus_b, punchline_a, punchline_b\n"
        "- ig_caption (engaging Instagram caption with 4 hashtags)\n"
        "- pinned_comment (short question to spark comments)"
    )

    for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        url = build_https_url(
            "generativelanguage.googleapis.com",
            f"/v1beta/models/{model}:generateContent",
            {"key": GEMINI_API_KEY},
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.0,
                "maxOutputTokens": 2100,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode())
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _extract_json_object(raw_text)
                script = normalize_script(parsed, couple, genre, history_items)
                print(f"Generated {genre} story for {couple['label']} via {model}: {script['topic']}")
                return script
        except Exception as e:
            print(f"Gemini ({model}) skipped: {e}")

    print("Using fallback couple story.")
    return _fallback_couple_script(couple, genre, history_items)


# ==============================================================================
# REAL HUMAN VOICE ENGINE (GEMINI NATIVE TTS -> EDGE-TTS -> GTTS)
# ==============================================================================
def _synthesize_gemini_tts(line_text, char_cfg, out_wav):
    """Calls Gemini 2.5 Flash Preview TTS via existing GEMINI_API_KEY (immune to Edge IP blocks)."""
    url = build_https_url(
        "generativelanguage.googleapis.com",
        "/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",
        {"key": GEMINI_API_KEY},
    )
    styled_prompt = f"{char_cfg['voice_style']} \"{line_text}\""
    payload = {
        "contents": [{"parts": [{"text": styled_prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": char_cfg["gemini_voice"],
                    }
                }
            },
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        data = json.loads(resp.read().decode())

    parts = data["candidates"][0]["content"]["parts"]
    inline = next(p["inlineData"] for p in parts if "inlineData" in p)
    raw_bytes = base64.b64decode(inline["data"])
    mime_type = inline.get("mimeType", "").lower()

    raw_file = out_wav.with_suffix(".raw_gem")
    raw_file.write_bytes(raw_bytes)
    if "pcm" in mime_type or "l16" in mime_type or not raw_bytes[:4] in (b"RIFF", b"ID3\x03", b"OggS"):
        subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(raw_file), "-ar", "48000", "-ac", "1", str(out_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_file), "-ar", "48000", "-ac", "1", str(out_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


async def _synthesize_edge_tts_async(text, voice, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+5%")
    await comm.save(str(out_mp3))


def _synthesize_gtts_fallback(text, speaker, out_wav):
    from gtts import gTTS
    mp3_path = out_wav.with_suffix(".gtts.mp3")
    gTTS(text=text, lang="en", slow=False).save(str(mp3_path))
    pitch_factor = 0.88 if speaker == "A" else 1.08
    atempo = 1.0 / pitch_factor
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-af", f"asetrate=24000*{pitch_factor},aresample=48000,atempo={atempo:.3f}",
            "-ac", "1", str(out_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def synthesize_real_human_voice(line_text, speaker, char_cfg, tmp_dir, idx):
    raw_wav = tmp_dir / f"line_{idx}_raw.wav"

    # Tier 1: Gemini 2.5 Flash Preview TTS (natural emotion + cultural accent)
    try:
        _synthesize_gemini_tts(line_text, char_cfg, raw_wav)
        if raw_wav.exists() and raw_wav.stat().st_size > 4000:
            print(f"Line {idx} voice: Gemini TTS ({char_cfg['gemini_voice']})")
            return raw_wav
    except Exception as e:
        print(f"Line {idx} Gemini TTS skipped ({e}), trying Edge-TTS...")

    # Tier 2: Edge-TTS Neural Voice
    try:
        mp3_path = tmp_dir / f"line_{idx}.mp3"
        asyncio.run(_synthesize_edge_tts_async(line_text, char_cfg["edge_voice"], mp3_path))
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "48000", "-ac", "1", str(raw_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if raw_wav.exists() and raw_wav.stat().st_size > 4000:
            print(f"Line {idx} voice: Edge-TTS ({char_cfg['edge_voice']})")
            return raw_wav
    except Exception as e:
        print(f"Line {idx} Edge-TTS skipped ({e}), trying gTTS...")

    # Tier 3: gTTS + Formant Pitch Shift (never outputs synthetic sine-wave drones)
    _synthesize_gtts_fallback(line_text, speaker, raw_wav)
    print(f"Line {idx} voice: gTTS fallback")
    return raw_wav


def _write_silence_wav(path, sr, dur):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * int(sr * dur))


def build_dialogue_audio_and_lipsync(script, couple, tmp_dir):
    sr = 48000
    timeline = []
    padded_wavs = []
    cursor = 0.22

    lead_wav = tmp_dir / "lead.wav"
    _write_silence_wav(lead_wav, sr, cursor)
    padded_wavs.append(lead_wav)

    for idx, turn in enumerate(script["dialogue"]):
        speaker = turn["speaker"]
        char_cfg = couple["him"] if speaker == "A" else couple["her"]
        raw_wav = synthesize_real_human_voice(turn["line"], speaker, char_cfg, tmp_dir, idx)
        padded_wav = tmp_dir / f"line_{idx}_pad.wav"

        with wave.open(str(raw_wav), "r") as wf:
            frames_bytes = wf.readframes(wf.getnframes())
            samples = [int.from_bytes(frames_bytes[i:i + 2], "little", signed=True) for i in range(0, len(frames_bytes), 2)]

        speech_dur = len(samples) / sr
        pause_after = 0.72 if idx == len(script["dialogue"]) - 1 else 0.16
        total_turn_dur = speech_dur + pause_after

        spf = int(sr / FPS)
        mouth_env = []
        raw_rms = []
        peak_rms = 1.0
        for f in range(max(1, int(total_turn_dur * FPS))):
            s0 = f * spf
            s1 = min(len(samples), s0 + spf)
            if s1 > s0:
                chunk = samples[s0:s1]
                rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
            else:
                rms = 0.0
            raw_rms.append(rms)
            if rms > peak_rms:
                peak_rms = rms

        for rms in raw_rms:
            norm = min(1.0, (rms / max(800.0, peak_rms * 0.68)))
            mouth_env.append(0.0 if norm < 0.12 else norm)

        with wave.open(str(padded_wav), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(frames_bytes + (b"\x00\x00" * int(sr * pause_after)))

        padded_wavs.append(padded_wav)
        timeline.append({
            **turn,
            "start": cursor,
            "speech_end": cursor + speech_dur,
            "end": cursor + total_turn_dur,
            "mouth_env": mouth_env,
        })
        cursor += total_turn_dur

    concat_txt = tmp_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.name}'" for p in padded_wavs), encoding="utf-8")
    voice_wav = tmp_dir / "voice_all.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-ar", str(sr), "-ac", "2", str(voice_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Soft room tone so voices are 100% front-and-center with zero odd background sound
    final_wav = tmp_dir / "final_audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_wav),
            "-af", "acompressor=threshold=-18dB:ratio=2.5:attack=15:release=120,volume=1.15",
            "-ar", str(sr), "-ac", "2", str(final_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return timeline, cursor, final_wav


# ==============================================================================
# TRUE REMOTION DAMPED SPRING PHYSICS & FLUID HUMAN ANIMATION
# ==============================================================================
def remotion_spring(frame, fps=FPS, damping=12.0, stiffness=200.0, mass=0.5):
    """Exact analytical damped harmonic oscillator matching Remotion's spring()."""
    if frame <= 0:
        return 0.0
    t = frame / float(fps)
    omega0 = math.sqrt(stiffness / mass)
    zeta = damping / (2.0 * math.sqrt(stiffness * mass))
    if zeta < 1.0:
        omega_d = omega0 * math.sqrt(1.0 - zeta * zeta)
        envelope = math.exp(-zeta * omega0 * t)
        val = 1.0 - envelope * (math.cos(omega_d * t) + (zeta * omega0 / omega_d) * math.sin(omega_d * t))
    elif abs(zeta - 1.0) < 1e-6:
        val = 1.0 - math.exp(-omega0 * t) * (1.0 + omega0 * t)
    else:
        s1 = -omega0 * (zeta - math.sqrt(zeta * zeta - 1.0))
        s2 = -omega0 * (zeta + math.sqrt(zeta * zeta - 1.0))
        val = 1.0 - (s2 * math.exp(s1 * t) - s1 * math.exp(s2 * t)) / (s2 - s1)
    return val


def _render_background(setting, out_bg_path):
    bw, bh = W * SS, H * SS
    ink = (20, 20, 24)

    if setting == "dinner_romantic":
        img = Image.new("RGB", (bw, bh), (42, 28, 38))
        draw = ImageDraw.Draw(img)
        # Warm bokeh lights & restaurant window
        draw.rounded_rectangle([140 * SS, 260 * SS, 940 * SS, 860 * SS], radius=30 * SS, fill=(58, 38, 52), outline=(92, 64, 78), width=8 * SS)
        for bx, by, br, col in [(260, 410, 26, (255, 198, 110)), (440, 350, 18, (255, 165, 115)), (680, 440, 30, (255, 205, 125)), (820, 370, 20, (255, 180, 130))]:
            draw.ellipse([(bx - br) * SS, (by - br) * SS, (bx + br) * SS, (by + br) * SS], fill=col)
        # Floor & romantic dining table
        draw.rectangle([0, 1080 * SS, bw, bh], fill=(64, 42, 34), outline=ink, width=6 * SS)
        draw.ellipse([130 * SS, 1015 * SS, 950 * SS, 1195 * SS], fill=(238, 228, 218), outline=ink, width=8 * SS)
        draw.rectangle([490 * SS, 1185 * SS, 590 * SS, 1480 * SS], fill=(48, 32, 28), outline=ink, width=7 * SS)
        # Candlelight glow + candle + two wine glasses
        draw.ellipse([485 * SS, 945 * SS, 595 * SS, 1055 * SS], fill=(255, 224, 145))
        draw.rectangle([528 * SS, 1010 * SS, 552 * SS, 1085 * SS], fill=(248, 244, 236), outline=ink, width=5 * SS)
        draw.ellipse([532 * SS, 982 * SS, 548 * SS, 1008 * SS], fill=(255, 185, 45))
    elif setting == "cafe_lunch":
        img = Image.new("RGB", (bw, bh), (236, 222, 202))
        draw = ImageDraw.Draw(img)
        # Cafe window & hanging pendant lamps
        draw.rectangle([120 * SS, 290 * SS, 960 * SS, 820 * SS], fill=(204, 232, 244), outline=(112, 82, 58), width=9 * SS)
        draw.line([(540 * SS, 290 * SS), (540 * SS, 820 * SS)], fill=(112, 82, 58), width=8 * SS)
        for lx in (340, 740):
            draw.line([(lx * SS, 0), (lx * SS, 330 * SS)], fill=ink, width=6 * SS)
            draw.pieslice([(lx - 55) * SS, 310 * SS, (lx + 55) * SS, 385 * SS], start=180, end=360, fill=(214, 148, 72), outline=ink, width=6 * SS)
        draw.rectangle([0, 1090 * SS, bw, bh], fill=(176, 138, 102), outline=ink, width=6 * SS)
        # Cafe table + iced coffees & basket of fries
        draw.rounded_rectangle([160 * SS, 1035 * SS, 920 * SS, 1135 * SS], radius=24 * SS, fill=(166, 122, 82), outline=ink, width=8 * SS)
        draw.rectangle([505 * SS, 1135 * SS, 575 * SS, 1480 * SS], fill=(62, 58, 56), outline=ink, width=7 * SS)
        for cx in (395, 665):
            draw.polygon([(cx - 22) * SS, 975 * SS, (cx + 22) * SS, 975 * SS, (cx + 16) * SS, 1040 * SS, (cx - 16) * SS, 1040 * SS], fill=(148, 102, 68), outline=ink)
            draw.line([(cx + 6) * SS, 945 * SS, (cx - 2) * SS, 985 * SS], fill=(45, 145, 95), width=6 * SS)
        draw.rounded_rectangle([490 * SS, 1002 * SS, 590 * SS, 1042 * SS], radius=10 * SS, fill=(212, 68, 58), outline=ink, width=5 * SS)
    elif setting == "destination_sunset":
        img = Image.new("RGB", (bw, bh), (252, 174, 118))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, bw, 560 * SS], fill=(246, 142, 112))
        draw.ellipse([410 * SS, 680 * SS, 670 * SS, 940 * SS], fill=(255, 232, 148))
        # Ocean & scenic overlook balcony
        draw.rectangle([0, 860 * SS, bw, 1140 * SS], fill=(74, 132, 168), outline=ink, width=6 * SS)
        draw.rectangle([0, 1140 * SS, bw, bh], fill=(218, 198, 172), outline=ink, width=6 * SS)
        draw.rectangle([0, 1055 * SS, bw, 1085 * SS], fill=(244, 238, 228), outline=ink, width=6 * SS)
        for rx in range(60, W, 110):
            draw.rectangle([rx * SS, 1085 * SS, (rx + 24) * SS, 1145 * SS], fill=(236, 228, 218), outline=ink, width=5 * SS)
    else:
        # Cozy living room & green plaid sofa (couch_cozy)
        img = Image.new("RGB", (bw, bh), (222, 208, 186))
        draw = ImageDraw.Draw(img)
        draw.rectangle([85 * SS, 315 * SS, 355 * SS, 645 * SS], fill=(138, 116, 94), outline=ink, width=8 * SS)
        draw.rectangle([105 * SS, 335 * SS, 335 * SS, 625 * SS], fill=(176, 198, 172), outline=ink, width=5 * SS)
        draw.polygon([(105 * SS, 540 * SS), (210 * SS, 455 * SS), (335 * SS, 565 * SS), (335 * SS, 625 * SS), (105 * SS, 625 * SS)], fill=(116, 146, 108), outline=ink)

        draw.rectangle([825 * SS, 440 * SS, bw, 1185 * SS], fill=(154, 112, 74), outline=ink, width=8 * SS)
        for sy in (620, 800, 980):
            draw.line([(825 * SS, sy * SS), (bw, sy * SS)], fill=ink, width=7 * SS)

        draw.rectangle([0, 1165 * SS, bw, bh], fill=(178, 140, 104), outline=ink, width=7 * SS)
        draw.polygon(
            [(70 * SS, 1310 * SS), (965 * SS, 1310 * SS), (1045 * SS, 1560 * SS), (15 * SS, 1560 * SS)],
            fill=(236, 228, 214),
            outline=ink,
        )

        sofa_base = (138, 158, 108)
        sofa_light = (152, 172, 122)
        sofa_plaid = (114, 134, 88)
        draw.rounded_rectangle([120 * SS, 735 * SS, 915 * SS, 1255 * SS], radius=44 * SS, fill=sofa_base, outline=ink, width=8 * SS)
        for gx in range(210, 860, 95):
            draw.line([(gx * SS, 742 * SS), (gx * SS, 1040 * SS)], fill=sofa_plaid, width=4 * SS)
        for gy in range(810, 1030, 85):
            draw.line([(175 * SS, gy * SS), (860 * SS, gy * SS)], fill=sofa_plaid, width=4 * SS)

        draw.rounded_rectangle([95 * SS, 845 * SS, 205 * SS, 1255 * SS], radius=38 * SS, fill=sofa_light, outline=ink, width=8 * SS)
        draw.rounded_rectangle([830 * SS, 845 * SS, 935 * SS, 1255 * SS], radius=38 * SS, fill=sofa_light, outline=ink, width=8 * SS)
        draw.rounded_rectangle([195 * SS, 1015 * SS, 840 * SS, 1170 * SS], radius=26 * SS, fill=sofa_light, outline=ink, width=7 * SS)
        draw.line([(518 * SS, 1015 * SS), (518 * SS, 1170 * SS)], fill=ink, width=6 * SS)
        draw.rectangle([135 * SS, 1168 * SS, 900 * SS, 1255 * SS], fill=sofa_base, outline=ink, width=7 * SS)

        draw.rounded_rectangle([545 * SS, 1235 * SS, 1065 * SS, 1315 * SS], radius=16 * SS, fill=(168, 126, 86), outline=ink, width=7 * SS)
        draw.rectangle([585 * SS, 1315 * SS, 620 * SS, 1465 * SS], fill=(144, 104, 68), outline=ink, width=6 * SS)
        draw.rectangle([975 * SS, 1315 * SS, 1010 * SS, 1465 * SS], fill=(144, 104, 68), outline=ink, width=6 * SS)
        draw.rounded_rectangle([670 * SS, 1190 * SS, 722 * SS, 1242 * SS], radius=10 * SS, fill=(92, 138, 182), outline=ink, width=5 * SS)

    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _draw_human_hand(draw, x, y, angle_deg, skin_col, spread=1.0, scale=1.0):
    ink = (20, 20, 24)
    r = int(12 * scale * SS)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=skin_col, outline=ink, width=max(4 * SS, int(5 * scale * SS)))
    rad = math.radians(angle_deg)
    for f_off in (-0.38 * spread, 0.0, 0.38 * spread):
        fa = rad + f_off
        fx = x + int(math.cos(fa) * 21 * scale * SS)
        fy = y + int(math.sin(fa) * 21 * scale * SS)
        draw.line([(x, y), (fx, fy)], fill=ink, width=max(4 * SS, int(5 * scale * SS)))


def _draw_mouth(draw, hx, hy, scale, expr, mouth_open):
    ink = (20, 20, 24)
    mw = int(25 * scale * SS)
    if mouth_open > 0.12:
        mh = int((9 + 27 * mouth_open) * scale * SS)
        draw.ellipse(
            [hx - mw, hy + int(22 * scale * SS), hx + mw, hy + int(22 * scale * SS) + mh],
            fill=(168, 52, 60),
            outline=ink,
            width=max(4 * SS, int(5 * scale * SS)),
        )
        if mouth_open > 0.42:
            draw.chord(
                [hx - mw + 4 * SS, hy + int(25 * scale * SS), hx + mw - 4 * SS, hy + int(22 * scale * SS) + mh],
                start=15,
                end=165,
                fill=(238, 118, 124),
            )
    else:
        if expr in ("chill_smirk", "smug_eyes_closed", "excited_wide", "soft_love_smile"):
            draw.arc(
                [hx - int(24 * scale * SS), hy + int(16 * scale * SS), hx + int(26 * scale * SS), hy + int(44 * scale * SS)],
                start=10,
                end=170,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        elif expr in ("pout_frown", "exasperated"):
            draw.arc(
                [hx - int(20 * scale * SS), hy + int(30 * scale * SS), hx + int(20 * scale * SS), hy + int(52 * scale * SS)],
                start=190,
                end=350,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        elif expr == "shocked":
            draw.ellipse(
                [hx - int(12 * scale * SS), hy + int(24 * scale * SS), hx + int(12 * scale * SS), hy + int(46 * scale * SS)],
                fill=(168, 52, 60),
                outline=ink,
                width=max(4 * SS, int(5 * scale * SS)),
            )
        else:
            draw.line(
                [(hx - int(20 * scale * SS), hy + int(34 * scale * SS)), (hx + int(20 * scale * SS), hy + int(32 * scale * SS))],
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )


def _draw_eyes(draw, hx, hy, scale, expr, skin_col, t, look_x=1.0, look_y=0.0):
    ink = (20, 20, 24)
    eye_dx = int(31 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(19 * scale * SS)
    blinking = ((t + (0.85 if look_x < 0 else 0.0)) % 3.0) < 0.11
    px_off = int(6 * look_x * scale * SS)
    py_off = int(5 * look_y * scale * SS)

    if expr == "smug_eyes_closed" or blinking:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.arc(
                [ex - er, eye_y - int(8 * scale * SS), ex + er, eye_y + int(12 * scale * SS)],
                start=10,
                end=170,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        return

    for side in (-1, 1):
        ex = hx + side * eye_dx
        draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(254, 254, 255), outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        draw.ellipse([ex - 6 * SS + px_off, eye_y - 6 * SS + py_off, ex + 6 * SS + px_off, eye_y + 6 * SS + py_off], fill=ink)
        if expr in ("deadpan", "skeptical", "pout_frown"):
            draw.pieslice(
                [ex - er, eye_y - er, ex + er, eye_y + er],
                start=180,
                end=360,
                fill=skin_col,
                outline=ink,
                width=max(4 * SS, int(5 * scale * SS)),
            )
        brow_tilt = 0
        if expr in ("skeptical", "exasperated", "pout_frown"):
            brow_tilt = -7 * side * SS
        elif expr in ("excited_wide", "soft_love_smile"):
            brow_tilt = 5 * side * SS
        draw.line(
            [(ex - er, eye_y - er - 10 * SS - brow_tilt), (ex + er, eye_y - er - 10 * SS + brow_tilt)],
            fill=ink,
            width=max(4 * SS, int(6 * scale * SS)),
        )


def _draw_him_head(draw, hx, hy, scale, him_cfg, expr, mouth_open, t, look_x=1.0, look_y=-0.1):
    ink = (20, 20, 24)
    rx, ry = int(94 * scale * SS), int(94 * scale * SS)
    skin = him_cfg["skin"]
    hair = him_cfg["hair"]

    draw.ellipse([hx - rx, hy - ry, hx + rx, hy + ry], fill=skin, outline=ink, width=8 * SS)

    # Light beard/jawline option
    if him_cfg.get("beard"):
        draw.arc(
            [hx - int(rx * 0.86), hy - int(ry * 0.2), hx + int(rx * 0.86), hy + int(ry * 0.94)],
            start=15,
            end=165,
            fill=hair,
            width=max(6 * SS, int(10 * scale * SS)),
        )

    style = him_cfg.get("hair_style", "cap")
    if style == "cap":
        cap = him_cfg["cap_color"]
        draw.pieslice([hx - rx, hy - ry - 10 * SS, hx + rx, hy - int(ry * 0.14)], start=180, end=360, fill=cap, outline=ink, width=7 * SS)
        draw.rounded_rectangle([hx - 6 * SS, hy - int(ry * 0.56), hx + int(rx * 1.32), hy - int(ry * 0.34)], radius=8 * SS, fill=cap, outline=ink, width=6 * SS)
    elif style == "fade_lineup":
        draw.pieslice([hx - rx, hy - ry - 4 * SS, hx + rx, hy - int(ry * 0.36)], start=185, end=355, fill=hair, outline=ink, width=7 * SS)
    elif style == "comma_hair":
        draw.pieslice([hx - rx - 4 * SS, hy - ry - 10 * SS, hx + rx + 4 * SS, hy - int(ry * 0.18)], start=175, end=365, fill=hair, outline=ink, width=7 * SS)
        draw.arc([hx - 15 * SS, hy - int(ry * 0.65), hx + 48 * SS, hy - int(ry * 0.15)], start=250, end=70, fill=hair, width=14 * SS)
    else:
        draw.pieslice([hx - rx - 4 * SS, hy - ry - 10 * SS, hx + rx + 4 * SS, hy - int(ry * 0.22)], start=175, end=365, fill=hair, outline=ink, width=7 * SS)

    _draw_eyes(draw, hx, hy, scale, expr, skin, t, look_x=look_x, look_y=look_y)
    if him_cfg.get("glasses"):
        eye_dx = int(31 * scale * SS)
        eye_y = hy - int(10 * scale * SS)
        gr = int(25 * scale * SS)
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - gr, eye_y - gr, ex + gr, eye_y + gr], outline=ink, width=5 * SS)
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=5 * SS)

    if expr == "soft_love_smile":
        draw.ellipse([hx - 58 * SS, hy + 10 * SS, hx - 30 * SS, hy + 26 * SS], fill=(238, 128, 138))
        draw.ellipse([hx + 30 * SS, hy + 10 * SS, hx + 58 * SS, hy + 26 * SS], fill=(238, 128, 138))

    _draw_mouth(draw, hx, hy, scale, expr, mouth_open)


def _draw_her_head(draw, hx, hy, scale, her_cfg, expr, mouth_open, t, look_x=-1.0, look_y=0.2):
    ink = (20, 20, 24)
    rx, ry = int(92 * scale * SS), int(92 * scale * SS)
    skin = her_cfg["skin"]
    hair = her_cfg["hair"]
    style = her_cfg.get("hair_style", "bun")

    # Back hair styles (drawn behind head)
    if style == "bun":
        draw.ellipse([hx + rx - 22 * SS, hy - ry + 6 * SS, hx + rx + 38 * SS, hy - ry + 66 * SS], fill=hair, outline=ink, width=6 * SS)
    elif style == "afro_puffs":
        draw.ellipse([hx - rx - 46 * SS, hy - ry - 36 * SS, hx - rx + 26 * SS, hy - ry + 36 * SS], fill=hair, outline=ink, width=7 * SS)
        draw.ellipse([hx + rx - 26 * SS, hy - ry - 36 * SS, hx + rx + 46 * SS, hy - ry + 36 * SS], fill=hair, outline=ink, width=7 * SS)
    elif style in ("long_straight", "long_waves_bangs"):
        draw.rounded_rectangle([hx - rx - 14 * SS, hy - ry + 10 * SS, hx + rx + 14 * SS, hy + ry + 110 * SS], radius=38 * SS, fill=hair, outline=ink, width=7 * SS)
    elif style == "box_braids":
        for bx_off in (-86, -66, 66, 86):
            draw.line([(hx + bx_off * SS, hy - 20 * SS), (hx + (bx_off * 1.1) * SS, hy + ry + 125 * SS)], fill=hair, width=13 * SS)
    elif style == "sleek_bob":
        draw.rounded_rectangle([hx - rx - 12 * SS, hy - ry + 8 * SS, hx + rx + 12 * SS, hy + ry + 36 * SS], radius=32 * SS, fill=hair, outline=ink, width=7 * SS)

    draw.ellipse([hx - rx, hy - ry, hx + rx, hy + ry], fill=skin, outline=ink, width=8 * SS)
    draw.pieslice([hx - rx - 2 * SS, hy - ry - 6 * SS, hx + rx + 2 * SS, hy - int(ry * 0.16)], start=180, end=360, fill=hair, outline=ink, width=7 * SS)

    if her_cfg.get("bindi"):
        draw.ellipse([hx - 5 * SS, hy - 34 * SS, hx + 5 * SS, hy - 24 * SS], fill=(178, 32, 42))
    if her_cfg.get("hoops"):
        draw.ellipse([hx + rx - 10 * SS, hy + 12 * SS, hx + rx + 18 * SS, hy + 42 * SS], outline=(238, 194, 72), width=5 * SS)

    _draw_eyes(draw, hx, hy, scale, expr, skin, t, look_x=look_x, look_y=look_y)
    if expr == "soft_love_smile":
        draw.ellipse([hx - 56 * SS, hy + 10 * SS, hx - 28 * SS, hy + 26 * SS], fill=(238, 128, 138))
        draw.ellipse([hx + 28 * SS, hy + 10 * SS, hx + 56 * SS, hy + 26 * SS], fill=(238, 128, 138))

    _draw_mouth(draw, hx, hy, scale, expr, mouth_open)


def _draw_couch_couple_scene(draw, couple, expr_a, expr_b, pose_a, pose_b, active_speaker, mouth_open, t, turn_frame):
    ink = (20, 20, 24)
    limb_w = 8 * SS
    him_cfg, her_cfg = couple["him"], couple["her"]

    # Remotion damped springs with 2-frame follow-through lag
    body_spring = remotion_spring(turn_frame, FPS, damping=12.0, stiffness=200.0, mass=0.5)
    head_spring = remotion_spring(max(0, turn_frame - 2), FPS, damping=13.0, stiffness=180.0, mass=0.5)

    # HIM: Reclining horizontally on the green plaid sofa
    talk_bob_a = int(math.sin(t * 8.0) * 4 * SS) if (active_speaker == "A" and mouth_open > 0.1) else int(math.sin(t * 2.1) * 3 * SS)
    ahx = 248 * SS + int(head_spring * 6 * SS)
    ahy = 845 * SS + talk_bob_a

    torso_poly = [
        (285 * SS, 895 * SS),
        (535 * SS, 975 * SS),
        (515 * SS, 1068 * SS),
        (255 * SS, 1005 * SS),
    ]
    draw.polygon(torso_poly, fill=him_cfg["top_color"], outline=ink)
    draw.line(torso_poly + [torso_poly[0]], fill=ink, width=8 * SS)

    hip_a = (520 * SS, 1020 * SS)
    draw.line([hip_a, (605 * SS, 945 * SS), (630 * SS, 1030 * SS)], fill=ink, width=limb_w)
    draw.line([hip_a, (635 * SS, 965 * SS), (665 * SS, 1045 * SS)], fill=ink, width=limb_w)
    draw.line([(275 * SS, 935 * SS), (205 * SS, 965 * SS), (175 * SS, 910 * SS)], fill=ink, width=limb_w)

    if pose_a == "couch_cozy_arm_around":
        draw.line([(365 * SS, 940 * SS), (520 * SS, 910 * SS), (645 * SS, 915 * SS)], fill=ink, width=limb_w)
    elif pose_a == "couch_hand_gesture" or (active_speaker == "A" and mouth_open > 0.15):
        wave = int(math.sin(t * 7.5) * 16 * body_spring * SS)
        hand_a = (455 * SS, 925 * SS - wave)
        draw.line([(365 * SS, 940 * SS), (415 * SS, 995 * SS), hand_a], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_a[0], hand_a[1], -55, him_cfg["skin"], spread=1.1, scale=0.95)
    elif pose_a == "couch_shrug_palm":
        hand_a = (475 * SS, 940 * SS)
        draw.line([(365 * SS, 940 * SS), (420 * SS, 985 * SS), hand_a], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_a[0], hand_a[1], -30, him_cfg["skin"], spread=1.3, scale=0.95)
    else:
        draw.line([(365 * SS, 940 * SS), (410 * SS, 1015 * SS), (465 * SS, 1018 * SS)], fill=ink, width=limb_w)
        draw.ellipse([455 * SS, 1006 * SS, 482 * SS, 1030 * SS], fill=him_cfg["skin"], outline=ink, width=4 * SS)

    _draw_him_head(draw, ahx, ahy, 0.96, him_cfg, expr_a, mouth_open if active_speaker == "A" else 0.0, t, look_x=1.0, look_y=-0.2)

    # HER: Sitting on right side of sofa with spring-driven acting poses
    lean_x = 0
    if pose_b in ("hands_on_lap_lean", "both_hands_plead", "open_palm_invite", "cozy_lean_heart"):
        lean_x = int(-24 * body_spring * SS)
    elif pose_b == "arms_crossed_pout":
        lean_x = int(12 * body_spring * SS)

    talk_bob_b = int(math.sin(t * 8.5) * 5 * SS) if (active_speaker == "B" and mouth_open > 0.1) else int(math.sin(t * 2.3 + 1.0) * 3 * SS)
    bhx = 695 * SS + lean_x
    bhy = 745 * SS + talk_bob_b
    bneck_y = bhy + 88 * SS
    bhip_x = 708 * SS
    bhip_y = bneck_y + 185 * SS

    draw.line([(bhip_x - 20 * SS, bhip_y), (655 * SS, bhip_y + 95 * SS), (655 * SS, bhip_y + 185 * SS)], fill=ink, width=limb_w)
    draw.line([(bhip_x + 15 * SS, bhip_y), (685 * SS, bhip_y + 95 * SS), (685 * SS, bhip_y + 185 * SS)], fill=ink, width=limb_w)

    dress_poly = [(bhx - 42 * SS, bneck_y), (bhx + 42 * SS, bneck_y), (bhip_x + 68 * SS, bhip_y + 18 * SS), (bhip_x - 68 * SS, bhip_y + 18 * SS)]
    draw.polygon(dress_poly, fill=her_cfg["top_color"], outline=ink)
    draw.line(dress_poly + [dress_poly[0]], fill=ink, width=7 * SS)

    l_sh = (bhx - 38 * SS, bneck_y + 28 * SS)
    r_sh = (bhx + 38 * SS, bneck_y + 28 * SS)
    gest_wiggle = int(math.sin(t * 9.0) * 14 * SS) if active_speaker == "B" else 0

    if pose_b == "hands_on_hips":
        draw.line([l_sh, (l_sh[0] - 58 * SS, l_sh[1] + 55 * SS), (bhip_x - 52 * SS, bhip_y - 12 * SS)], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 58 * SS, r_sh[1] + 55 * SS), (bhip_x + 52 * SS, bhip_y - 12 * SS)], fill=ink, width=limb_w)
    elif pose_b == "arms_up_exasperated":
        lift = int(body_spring * 85 * SS) + gest_wiggle
        l_hand = (l_sh[0] - 110 * SS, l_sh[1] - lift)
        r_hand = (r_sh[0] + 110 * SS, r_sh[1] - lift)
        draw.line([l_sh, (l_sh[0] - 75 * SS, l_sh[1] - 10 * SS), l_hand], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 75 * SS, r_sh[1] - 10 * SS), r_hand], fill=ink, width=limb_w)
        _draw_human_hand(draw, l_hand[0], l_hand[1], -125, her_cfg["skin"], spread=1.35, scale=0.95)
        _draw_human_hand(draw, r_hand[0], r_hand[1], -55, her_cfg["skin"], spread=1.35, scale=0.95)
    elif pose_b == "both_hands_plead":
        l_hand = (l_sh[0] - 115 * SS, l_sh[1] + 28 * SS - gest_wiggle)
        r_hand = (r_sh[0] - 85 * SS, r_sh[1] + 42 * SS + gest_wiggle)
        draw.line([l_sh, (l_sh[0] - 55 * SS, l_sh[1] + 52 * SS), l_hand], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] - 25 * SS, r_sh[1] + 62 * SS), r_hand], fill=ink, width=limb_w)
        _draw_human_hand(draw, l_hand[0], l_hand[1], -165, her_cfg["skin"], spread=1.25, scale=0.92)
        _draw_human_hand(draw, r_hand[0], r_hand[1], -165, her_cfg["skin"], spread=1.25, scale=0.92)
    elif pose_b == "open_palm_invite":
        l_hand = (l_sh[0] - 125 * SS, l_sh[1] + 18 * SS - gest_wiggle)
        draw.line([l_sh, (l_sh[0] - 62 * SS, l_sh[1] + 45 * SS), l_hand], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 35 * SS, r_sh[1] + 65 * SS), (bhip_x + 25 * SS, bhip_y - 5 * SS)], fill=ink, width=limb_w)
        _draw_human_hand(draw, l_hand[0], l_hand[1], -160, her_cfg["skin"], spread=1.2, scale=0.95)
    elif pose_b == "arms_crossed_pout":
        draw.line([l_sh, (l_sh[0] - 32 * SS, l_sh[1] + 55 * SS), (r_sh[0] + 18 * SS, r_sh[1] + 58 * SS)], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 32 * SS, r_sh[1] + 62 * SS), (l_sh[0] - 18 * SS, l_sh[1] + 65 * SS)], fill=ink, width=limb_w)
    elif pose_b == "facepalm_sigh":
        l_hand = (bhx - 28 * SS, bhy - 18 * SS)
        draw.line([l_sh, (l_sh[0] - 68 * SS, l_sh[1] + 10 * SS), l_hand], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 35 * SS, r_sh[1] + 65 * SS), (bhip_x + 20 * SS, bhip_y)], fill=ink, width=limb_w)
        _draw_human_hand(draw, l_hand[0], l_hand[1], -90, her_cfg["skin"], spread=0.8, scale=0.92)
    elif pose_b == "cozy_lean_heart":
        draw.line([l_sh, (l_sh[0] - 75 * SS, l_sh[1] + 35 * SS), (490 * SS, 975 * SS)], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 25 * SS, r_sh[1] + 70 * SS), (bhip_x + 12 * SS, bhip_y - 6 * SS)], fill=ink, width=limb_w)
    else:
        draw.line([l_sh, (l_sh[0] - 42 * SS, l_sh[1] + 72 * SS), (bhip_x - 32 * SS, bhip_y - 6 * SS)], fill=ink, width=limb_w)
        draw.line([r_sh, (r_sh[0] + 32 * SS, r_sh[1] + 72 * SS), (bhip_x + 12 * SS, bhip_y - 6 * SS)], fill=ink, width=limb_w)

    _draw_her_head(draw, bhx, bhy, 0.95, her_cfg, expr_b, mouth_open if active_speaker == "B" else 0.0, t, look_x=-1.0, look_y=0.25)


def _draw_date_or_destination_couple(draw, setting, couple, expr_a, expr_b, pose_a, pose_b, active_speaker, mouth_open, t, turn_frame):
    ink = (20, 20, 24)
    limb_w = 8 * SS
    him_cfg, her_cfg = couple["him"], couple["her"]
    body_spring = remotion_spring(turn_frame, FPS, damping=12.0, stiffness=200.0, mass=0.5)

    # Him (Left)
    bob_a = int(math.sin(t * (7.5 if active_speaker == "A" and mouth_open > 0.1 else 2.2)) * 5 * SS)
    ahx = 340 * SS + int(body_spring * 10 * SS if active_speaker == "A" else 0)
    ahy = 795 * SS + bob_a
    aneck_y = ahy + 90 * SS
    ahip_y = aneck_y + 205 * SS

    draw.rounded_rectangle([ahx - 56 * SS, aneck_y, ahx + 56 * SS, ahip_y], radius=28 * SS, fill=him_cfg["top_color"], outline=ink, width=7 * SS)
    if setting == "destination_sunset":
        for side in (-1, 1):
            draw.line([(ahx + side * 26 * SS, ahip_y), (ahx + side * 30 * SS, ahip_y + 195 * SS)], fill=ink, width=limb_w)

    draw.line([(ahx - 52 * SS, aneck_y + 30 * SS), (ahx - 82 * SS, aneck_y + 115 * SS), (ahx - 55 * SS, aneck_y + 185 * SS)], fill=ink, width=limb_w)
    if pose_a == "table_cheers_toast":
        hand_a = (ahx + 125 * SS, aneck_y + 18 * SS - int(body_spring * 14 * SS))
        draw.line([(ahx + 52 * SS, aneck_y + 30 * SS), (ahx + 98 * SS, aneck_y + 82 * SS), hand_a], fill=ink, width=limb_w)
        # Wine glass
        draw.polygon([(hand_a[0] - 14 * SS, hand_a[1] - 58 * SS), (hand_a[0] + 14 * SS, hand_a[1] - 58 * SS), (hand_a[0] + 8 * SS, hand_a[1] - 26 * SS), (hand_a[0] - 8 * SS, hand_a[1] - 26 * SS)], fill=(182, 42, 62), outline=ink)
        draw.line([(hand_a[0], hand_a[1] - 26 * SS), (hand_a[0], hand_a[1] + 6 * SS)], fill=ink, width=4 * SS)
    elif pose_a == "table_count_two":
        hand_a = (ahx + 115 * SS, aneck_y + 24 * SS - int(body_spring * 14 * SS))
        draw.line([(ahx + 52 * SS, aneck_y + 30 * SS), (ahx + 96 * SS, aneck_y + 82 * SS), hand_a], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_a[0], hand_a[1], -85, him_cfg["skin"], spread=0.75, scale=0.95)
    else:
        wave = int(math.sin(t * 7.5) * 14 * SS) if active_speaker == "A" else 0
        hand_a = (ahx + 125 * SS, aneck_y + 62 * SS - wave)
        draw.line([(ahx + 52 * SS, aneck_y + 30 * SS), (ahx + 95 * SS, aneck_y + 98 * SS), hand_a], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_a[0], hand_a[1], -30, him_cfg["skin"], spread=1.15, scale=0.95)

    _draw_him_head(draw, ahx, ahy, 0.96, him_cfg, expr_a, mouth_open if active_speaker == "A" else 0.0, t, look_x=1.0, look_y=0.0)

    # Her (Right)
    bob_b = int(math.sin(t * (7.5 if active_speaker == "B" and mouth_open > 0.1 else 2.4) + 1.0) * 5 * SS)
    bhx = 735 * SS - int(body_spring * 10 * SS if active_speaker == "B" else 0)
    bhy = 795 * SS + bob_b
    bneck_y = bhy + 88 * SS
    bhip_y = bneck_y + 205 * SS

    draw.rounded_rectangle([bhx - 52 * SS, bneck_y, bhx + 52 * SS, bhip_y], radius=28 * SS, fill=her_cfg["top_color"], outline=ink, width=7 * SS)
    if setting == "destination_sunset":
        for side in (-1, 1):
            draw.line([(bhx + side * 24 * SS, bhip_y), (bhx + side * 28 * SS, bhip_y + 195 * SS)], fill=ink, width=limb_w)

    if pose_b == "cheers_glass_raise":
        hand_b = (bhx - 125 * SS, bneck_y + 18 * SS - int(body_spring * 14 * SS))
        draw.line([(bhx - 48 * SS, bneck_y + 30 * SS), (bhx - 98 * SS, bneck_y + 82 * SS), hand_b], fill=ink, width=limb_w)
        draw.polygon([(hand_b[0] - 14 * SS, hand_b[1] - 58 * SS), (hand_b[0] + 14 * SS, hand_b[1] - 58 * SS), (hand_b[0] + 8 * SS, hand_b[1] - 26 * SS), (hand_b[0] - 8 * SS, hand_b[1] - 26 * SS)], fill=(182, 42, 62), outline=ink)
        draw.line([(hand_b[0], hand_b[1] - 26 * SS), (hand_b[0], hand_b[1] + 6 * SS)], fill=ink, width=4 * SS)
    elif pose_b == "arms_up_exasperated":
        hand_b = (bhx - 115 * SS, bneck_y - 25 * SS)
        draw.line([(bhx - 48 * SS, bneck_y + 30 * SS), (bhx - 95 * SS, bneck_y + 25 * SS), hand_b], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_b[0], hand_b[1], -135, her_cfg["skin"], spread=1.3, scale=0.95)
    else:
        wave = int(math.sin(t * 8.0) * 14 * SS) if active_speaker == "B" else 0
        hand_b = (bhx - 125 * SS, bneck_y + 58 * SS - wave)
        draw.line([(bhx - 48 * SS, bneck_y + 30 * SS), (bhx - 95 * SS, bneck_y + 95 * SS), hand_b], fill=ink, width=limb_w)
        _draw_human_hand(draw, hand_b[0], hand_b[1], -150, her_cfg["skin"], spread=1.2, scale=0.95)

    draw.line([(bhx + 48 * SS, bneck_y + 30 * SS), (bhx + 78 * SS, bneck_y + 115 * SS), (bhx + 55 * SS, bneck_y + 185 * SS)], fill=ink, width=limb_w)
    _draw_her_head(draw, bhx, bhy, 0.95, her_cfg, expr_b, mouth_open if active_speaker == "B" else 0.0, t, look_x=-1.0, look_y=0.0)


# ==============================================================================
# SINGLE SYNCHRONIZED SUBTITLE OVERLAY (1-3 WORDS AT A TIME, ZERO CLUTTER)
# ==============================================================================
def _load_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_single_phrase_caption(frame, turn, t, page_cfg):
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    odraw.text(
        (W // 2, 1660),
        page_cfg["handle"],
        font=_load_font(26),
        fill=(255, 255, 255, 195),
        anchor="mm",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 180),
    )

    if not turn or t > turn["speech_end"] + 0.10:
        return Image.alpha_composite(rgba, overlay).convert("RGB")

    words = turn["line"].split()
    speech_dur = max(0.25, turn["speech_end"] - turn["start"])
    progress = max(0.0, min(0.999, (t - turn["start"]) / speech_dur))
    global_word_idx = int(progress * len(words))

    chunk_size = 3
    chunk_idx = global_word_idx // chunk_size
    chunk_words = words[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size]
    local_active = global_word_idx % chunk_size

    acc = tuple(page_cfg.get("accent_color", (255, 225, 45)))
    font = _load_font(56)
    space_w = odraw.textbbox((0, 0), " ", font=font)[2]
    word_boxes = [odraw.textbbox((0, 0), w.upper(), font=font) for w in chunk_words]
    total_w = sum((b[2] - b[0]) for b in word_boxes) + space_w * max(0, len(chunk_words) - 1)
    cur_x = (W - total_w) // 2
    cur_y = 1435

    for i, w in enumerate(chunk_words):
        w_up = w.upper()
        fill_col = (acc[0], acc[1], acc[2], 255) if i == local_active else (255, 255, 255, 255)
        odraw.text(
            (cur_x, cur_y),
            w_up,
            font=font,
            fill=fill_col,
            anchor="la",
            stroke_width=8,
            stroke_fill=(14, 16, 20, 252),
        )
        cur_x += (word_boxes[i][2] - word_boxes[i][0]) + space_w

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def apply_camera_framing(img, setting, camera_mode, turn_frame):
    # Remotion smooth no-bounce spring (damping: 200)
    eased = remotion_spring(turn_frame, FPS, damping=200.0, stiffness=140.0, mass=1.0)
    if camera_mode == "punchline_a":
        zoom = 1.06 + 0.32 * eased
        cx = int(W * (0.28 if setting == "couch_cozy" else 0.34))
        cy = int(H * (0.46 if setting == "couch_cozy" else 0.44))
    elif camera_mode == "punchline_b":
        zoom = 1.06 + 0.32 * eased
        cx = int(W * (0.65 if setting == "couch_cozy" else 0.68))
        cy = int(H * (0.42 if setting == "couch_cozy" else 0.44))
    elif camera_mode == "focus_a":
        zoom = 1.14
        cx = int(W * 0.33)
        cy = int(H * 0.45)
    elif camera_mode == "focus_b":
        zoom = 1.14
        cx = int(W * 0.66)
        cy = int(H * 0.45)
    else:
        zoom = 1.02 + 0.03 * eased
        cx, cy = W // 2, H // 2

    cw, ch = int(W / zoom), int(H / zoom)
    x0 = max(0, min(W - cw, cx - cw // 2))
    y0 = max(0, min(H - ch, cy - ch // 2))
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)


def render_couple_reel(page_cfg, couple, script, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        timeline, total_dur, final_wav = build_dialogue_audio_and_lipsync(script, couple, tmp_dir)
        bg_path = tmp_dir / "bg.png"
        _render_background(script["setting"], bg_path)
        bg_img = Image.open(bg_path).convert("RGB")

        total_frames = int(total_dur * FPS)
        for f_idx in range(total_frames):
            t = f_idx / FPS
            active_turn = None
            for turn in timeline:
                if turn["start"] <= t < turn["end"]:
                    active_turn = turn
                    break

            if active_turn:
                turn_frame = max(0, int((t - active_turn["start"]) * FPS))
                local_f = min(len(active_turn["mouth_env"]) - 1, turn_frame)
                mouth_open = active_turn["mouth_env"][local_f]
                speaker = active_turn["speaker"]
                expr_a = active_turn["expr_a"]
                expr_b = active_turn["expr_b"]
                pose_a = active_turn["pose_a"]
                pose_b = active_turn["pose_b"]
                camera = active_turn["camera"]
            else:
                turn_frame = 0
                mouth_open = 0.0
                speaker = "A"
                expr_a = "chill_smirk"
                expr_b = "skeptical"
                pose_a = "couch_chill_recline" if script["setting"] == "couch_cozy" else "table_lean_talk"
                pose_b = "hands_on_lap_lean"
                camera = "two_shot"

            stage_hi = bg_img.resize((W * SS, H * SS), Image.Resampling.BILINEAR)
            draw = ImageDraw.Draw(stage_hi)
            if script["setting"] == "couch_cozy":
                _draw_couch_couple_scene(draw, couple, expr_a, expr_b, pose_a, pose_b, speaker, mouth_open, t, turn_frame)
            else:
                _draw_date_or_destination_couple(draw, script["setting"], couple, expr_a, expr_b, pose_a, pose_b, speaker, mouth_open, t, turn_frame)

            frame = stage_hi.resize((W, H), Image.Resampling.LANCZOS)
            frame = apply_camera_framing(frame, script["setting"], camera, turn_frame)
            frame = ImageEnhance.Contrast(frame).enhance(1.03)
            frame = draw_single_phrase_caption(frame, active_turn, t, page_cfg)
            frame.save(tmp_dir / f"frame_{f_idx:04d}.png", format="PNG")

        subprocess.run(
            [
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
                str(out_mp4),
            ],
            check=True,
        )
        print(f"Rendered {total_dur:.1f}s Reel ({couple['label']} | {script['genre']}) -> {out_mp4}")
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


# ==============================================================================
# GITHUB PAGES ARCHIVE + INSTAGRAM REELS PUBLISHING
# ==============================================================================
def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Publish Reel {rel_path}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)

    owner, repo = REPO_NAME.split("/", 1)
    pages_url = build_https_url(f"{owner.lower()}.github.io", f"/{repo}/{rel_path}")
    for attempt in range(1, 25):
        time.sleep(5)
        try:
            req = urllib.request.Request(pages_url, headers={"User-Agent": "facebookexternalhit/1.1"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and ("video/" in ctype or "octet-stream" in ctype):
                    print(f"GitHub Pages video live: {pages_url}")
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages ({attempt}/24): {e}")
    raise RuntimeError(f"GitHub Pages did not serve MP4 in time: {pages_url}")


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API {e.code} on {url}: {e.read().decode('utf-8', errors='replace')}") from e


def publish_to_instagram(ig_id, token, video_url, caption, pinned_comment=""):
    if not token:
        raise RuntimeError("Missing IG_ACCESS_TOKEN secret in GitHub Actions.")
    if not ig_id:
        raise RuntimeError("Missing IG_USER_ID.")

    media_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{ig_id}/media")
    container = post_request(
        media_url,
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
    )
    creation_id = container["id"]
    print(f"Created IG media container: {creation_id}")

    for attempt in range(1, 31):
        time.sleep(5)
        status_url = build_https_url(
            "graph.facebook.com",
            f"/{GRAPH_VERSION}/{creation_id}",
            {"fields": "status_code,status", "access_token": token},
        )
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel status ({attempt}/30): {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram Reel container failed: {status_data}")
    else:
        raise RuntimeError(f"Instagram Reel container timed out: {creation_id}")

    publish_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{ig_id}/media_publish")
    published = post_request(publish_url, {"creation_id": creation_id, "access_token": token})
    media_id = published["id"]
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {media_id}")

    if pinned_comment:
        try:
            comment_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{media_id}/comments")
            post_request(comment_url, {"message": pinned_comment, "access_token": token})
        except Exception as e:
            print(f"Comment skipped ({e}); Reel is already live.")


if __name__ == "__main__":
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    world_context = fetch_world_context()
    publish_enabled = os.environ.get("PUBLISH_TO_IG", "true").strip().lower() not in ("0", "false", "no")

    for page in load_active_pages():
        slug = page["slug"]
        history_items = load_story_history(slug, limit=120)
        couple, genre = pick_next_couple_and_genre(history_items)
        script = generate_dialogue_with_gemini(page, couple, genre, history_items, world_context)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"
        out_dir.joinpath(f"story_{stamp}.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        save_story_record(slug, {
            "timestamp": stamp,
            "couple_id": couple["id"],
            "couple_label": couple["label"],
            "genre": script["genre"],
            "topic": script["topic"],
            "setting": script["setting"],
            "lines": [d["line"] for d in script["dialogue"]],
        })

        render_couple_reel(page, couple, script, rel_mp4)

        if publish_enabled:
            token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
            ig_id = (page.get("ig_user_id") or os.environ.get("IG_USER_ID") or DEFAULT_IG_USER_ID).strip()
            public_url = archive_and_get_pages_url(rel_mp4)
            publish_to_instagram(ig_id, token, public_url, script["ig_caption"], script.get("pinned_comment", ""))
