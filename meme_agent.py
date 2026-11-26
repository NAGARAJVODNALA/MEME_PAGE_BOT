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
SS = 2  # 2x supersampling (2160x3840 -> 1080x1920 Lanczos) for clean webcomic ink lines

# ==============================================================================
# PACING & VISUAL TUNING (HOOK-TO-END CHILL REELS RHYTHM)
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.14,
    "color_tint_strength": 0.07,
    "ambient_glow_strength": 0.14,
    "particle_opacity": 0.24,
    "max_zoom_delta": 0.09,
    "transition_sec": 0.16,
    "enable_blur_transition": True,
    "min_beat_sec": 1.85,
    "max_beat_sec": 2.55,
    "words_per_sec": 3.4,
}

# ==============================================================================
# CHARACTER ROSTER (CHILL CLUB CAST)
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "Calm Cap Instigator — understated confidence, pitches low-stakes side quests like master plans",
        "visual": (
            "Phil (2D webcomic character with soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, terracotta/olive baseball cap, calm deadpan smirk, "
            "thin black stick-figure body and articulated limbs with rounded black mitten hands)"
        ),
        "cap_color": (166, 98, 72),
        "beard": False,
        "glasses": False,
        "satchel": False,
    },
    "Stu": {
        "archetype": "Quiet Overthinker — reads way too much into a two-word text, deadpan analytical",
        "visual": (
            "Stu (2D webcomic character with soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, thick black-rimmed square glasses, small side-part hair tuft, "
            "expressive eyes, thin black stick-figure body and rounded black mitten hands)"
        ),
        "cap_color": None,
        "beard": False,
        "glasses": True,
        "satchel": False,
    },
    "Alan": {
        "archetype": "Deadpan Theorist — drops weird 'what if' logic calmly like it's peer-reviewed science",
        "visual": (
            "Alan (2D webcomic character with soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, scruffy brown lower beard, wide earnest eyes, "
            "thin black stick-figure body with brown crossbody satchel strap and black mitten hands)"
        ),
        "cap_color": None,
        "beard": True,
        "glasses": False,
        "satchel": True,
    },
    "Doug": {
        "archetype": "Unbothered Anchor — half-lidded calm eyes, zero urgency, delivers the quiet punchline",
        "visual": (
            "Doug (2D webcomic character with soft warm-gray cel-shaded round head #D8D5D0, "
            "thick black ink outline, calm half-lidded eyes, relaxed deadpan expression, "
            "thin black stick-figure body and rounded black mitten hands)"
        ),
        "cap_color": None,
        "beard": False,
        "glasses": False,
        "satchel": False,
    },
}

CAST_MODES = {
    "solo_chill": {
        "desc": "1 chill character in a deadpan confession or 'what if' inner thought",
        "lineups": [["Phil"], ["Stu"], ["Alan"], ["Doug"]],
    },
    "banter_duo": {
        "desc": "2 characters trading dry observational lines or silly 'what if' theories",
        "lineups": [["Phil", "Stu"], ["Alan", "Doug"], ["Phil", "Alan"], ["Stu", "Doug"]],
    },
    "role_call_trio": {
        "desc": "3 characters acting like distinct 'departments' (Strategy, Research, Intern) on a chill call/chat",
        "lineups": [["Phil", "Stu", "Alan"], ["Stu", "Alan", "Doug"], ["Phil", "Alan", "Doug"]],
    },
}

FACIAL_EXPRESSIONS = [
    "deadpan_camera_stare",
    "confident_smirk",
    "exhausted_half_lidded",
    "guilty_puppy_eyes",
    "sweat_grit",
    "bloodshot_shock",
    "smug_snooze",
]

ALL_BODY_ACTIONS = [
    "slouch_sigh",
    "phone_scroll_lean",
    "celebrate_groove",
    "struggle_pull",
    "walk_stride",
    "shock_recoil",
    "sleep_breathe_toss",
]

# ==============================================================================
# ENVIRONMENTS & ENDLESS CHILL COMEDY TOPIC BANK (DRY OBSERVATIONAL + SILLY WHAT-IF)
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "warm_desk_lamp": {
        "desc": "Warm amber-lit desk with walnut wood surface, wall lamp, potted plant, mug, and laptop",
        "wall": (196, 132, 84),
        "surface": (118, 72, 42),
        "accent_prop": (184, 58, 52),
    },
    "living_room_window": {
        "desc": "Cozy living room with slate-blue couch, bright window view, framed wall art, and side table",
        "wall": (176, 198, 222),
        "surface": (98, 122, 152),
        "accent_prop": (194, 148, 96),
    },
    "kitchen_counter": {
        "desc": "Clean home kitchen counter with kettle, coffee mug, snacks, and soft daylight",
        "wall": (214, 206, 194),
        "surface": (134, 138, 146),
        "accent_prop": (86, 156, 108),
    },
    "overcast_bedroom": {
        "desc": "Quiet minimalist bedroom with soft slate-gray blanket, framed art, and calm lamp light",
        "wall": (198, 204, 212),
        "night_wall": (46, 56, 82),
        "surface": (136, 146, 160),
        "accent_prop": (238, 240, 246),
    },
}

ART_STYLES = {
    "reference_webcomic_2d": {
        "prompt": (
            "Clean 2D webcomic animation background plate, crisp ink outlines and warm cel-shaded interior, "
            "minimalist cozy room with one clear focal prop, NO characters, NO people, NO text"
        ),
        "hashtags": ["#webcomic", "#2danimation", "#chillvibes"],
    },
    "cozy_lamp_cartoon": {
        "prompt": (
            "Warm 2D animated short interior background with soft amber lamp glow and clean ink lines, "
            "NO characters, NO people, NO text"
        ),
        "hashtags": ["#animatedshorts", "#deadpan", "#relatable"],
    },
}

# Broad, non-repetitive chill comedy topics mixing dry observation & silly "what if"
CHILL_TOPICS = [
    {
        "flavor": "dry_observational",
        "hook": "closing 23 browser tabs at 5:01 PM like I just retired",
        "env": "warm_desk_lamp",
        "markers": ["STEP 1", "STEP 2", "STEP 3", "PAYOFF"],
        "story_seed": "Staring calmly at an open project, closing every tab at 5:01 PM, and acting like a seasoned veteran off duty",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if your brain's '5 more minutes' had a customer support desk",
        "env": "overcast_bedroom",
        "markers": ["TICKET #1", "HOLD MUSIC", "ESCALATION", "RESOLVED"],
        "story_seed": "Polite support agent explains that '5 more minutes' is now on a 40-minute hold queue with smooth jazz",
    },
    {
        "flavor": "dry_observational",
        "hook": "saying 'sounds good!' before finishing the second half of the sentence",
        "env": "living_room_window",
        "markers": ["BEAT 1", "BEAT 2", "BEAT 3", "TWIST"],
        "story_seed": "Enthusiastically agreeing to a plan immediately, then slowly reading the extra details five seconds later",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if your inner monologues joined a 3-person video call",
        "env": "warm_desk_lamp",
        "markers": ["LOGGED IN", "STRATEGY", "INTERN", "MUTE"],
        "story_seed": "Calm host tries to make a simple sandwich while Strategy, Research, and Intern overcomplicate toast",
    },
    {
        "flavor": "dry_observational",
        "hook": "putting on a 40-minute video just to eat a 6-minute snack",
        "env": "kitchen_counter",
        "markers": ["00:00", "04:12", "06:00", "06:01"],
        "story_seed": "Scrolling for the ideal background video until the snack is gone and the video finally gets to the good part",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if leftover snacks in the fridge had a union meeting",
        "env": "kitchen_counter",
        "markers": ["QUORUM", "MOTION", "OBJECTION", "PASSED"],
        "story_seed": "Half a slice of pizza and cold fries hold a calm committee vote on whether tonight is 'their night'",
    },
    {
        "flavor": "dry_observational",
        "hook": "re-reading a normal text five times to make sure it didn't sound mad",
        "env": "living_room_window",
        "markers": ["DRAFT", "SECOND LOOK", "ADD PERIOD", "SEND"],
        "story_seed": "Turning 'ok' into 'sounds good!' because a plain period suddenly felt slightly dramatic",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if your 'I'll start after one episode' had a referee",
        "env": "living_room_window",
        "markers": ["WHISTLE", "OVERTIME", "VAR CHECK", "FINAL"],
        "story_seed": "Referee reviews the 'one more episode' claim on instant replay and quietly adds three more",
    },
    {
        "flavor": "dry_observational",
        "hook": "buying a notebook specifically to organize how you're going to organize things",
        "env": "warm_desk_lamp",
        "markers": ["PAGE 1", "TITLE", "LISTS", "BLANK"],
        "story_seed": "Writing a neat table of contents for a grand master plan and immediately admiring the handwriting",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if motivation was a chill roommate who only visits on Tuesdays",
        "env": "kitchen_counter",
        "markers": ["MON 9AM", "TUE 2PM", "TUE 2:14PM", "WED"],
        "story_seed": "Roommate shows up with huge energy for twenty minutes, rearranges two mugs, and heads out",
    },
    {
        "flavor": "dry_observational",
        "hook": "forgetting why you walked into the room and standing there like a loading screen",
        "env": "living_room_window",
        "markers": ["ENTER ROOM", "BUFFERING", "STILL LOADING", "REMEMBERED"],
        "story_seed": "Walking across the room with quiet purpose, losing the file mid-step, and recovering two minutes later",
    },
    {
        "flavor": "silly_what_if",
        "hook": "what if your 'I'm almost ready' worked in dog years",
        "env": "overcast_bedroom",
        "markers": ["ALMOST READY", "5 MINS", "SHOES ON", "OUT DOOR"],
        "story_seed": "Saying 'be right there in two minutes' while calmly deciding which socks feel most authentic",
    },
]

COLOR_GRADES = {
    "warm_amber_desk": {
        "tint": (235, 154, 88), "glow": (255, 208, 128), "contrast": 1.04, "sat": 1.06,
        "card_bg": (22, 18, 18), "card_fg": (255, 248, 240), "accent": (255, 198, 92),
    },
    "suburban_daylight_cel": {
        "tint": (196, 216, 238), "glow": (255, 244, 204), "contrast": 1.03, "sat": 1.05,
        "card_bg": (20, 24, 34), "card_fg": (250, 252, 255), "accent": (255, 212, 88),
    },
    "overcast_morning_bedroom": {
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.03, "sat": 0.92,
        "card_bg": (22, 24, 30), "card_fg": (248, 250, 255), "accent": (152, 196, 245),
    },
    "dim_night_phone_glow": {
        "tint": (58, 76, 112), "glow": (132, 214, 255), "contrast": 1.06, "sat": 0.95,
        "card_bg": (14, 18, 28), "card_fg": (238, 246, 255), "accent": (124, 212, 255),
    },
    "desaturated_gloom": {
        "tint": (128, 136, 148), "glow": (184, 194, 208), "contrast": 1.03, "sat": 0.72,
        "card_bg": (20, 22, 28), "card_fg": (236, 240, 246), "accent": (175, 192, 218),
    },
}

ALL_TRANSITIONS = ["hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right", "blur_dissolve"]
ALL_CAMERA_MOVES = ["dolly_push_in", "pull_back_reveal", "snap_zoom_face", "locked_deadpan", "pan_follow_right", "gentle_float"]
ALL_PROP_OVERLAYS = ["none", "sweat_drops", "phone_vibrate_arcs", "zzz_float"]
ALL_ENV_EFFECTS = ["none", "dust", "screen_glow"]
ALL_SFX_CUES = ["pop_ding", "whoosh", "record_scratch", "vine_boom_sub", "riser_hit"]


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
        "layout_mode": "v10_chill_hybrid",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 212, 88],
        "panic_color": [255, 110, 100],
        "domain": "Endless chill comedy Reels blending dry deadpan observations and silly 'what if' premises that keep viewers hooked to the payoff",
        "art_style": "Clean 2D webcomic animation with cel-shaded round heads, crisp ink outlines, articulated limbs, mitten hands, and clear focal props",
    }]


def fetch_live_trends():
    try:
        req = urllib.request.Request(
            "https://trends.google.com/trending/rss?geo=US",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            root = ET.fromstring(resp.read())
            items = [el.text.strip() for el in root.findall(".//item/title")[:6] if el.text]
            if items:
                return "\n".join(f"- {t}" for t in items)
    except Exception as e:
        print(f"Google Trends RSS skipped: {e}")
    return "- Everyday low-stakes overthinking\n- Silly 'what if' office and home logic"


def load_history(slug, limit=40):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    if hist_path.exists():
        try:
            return json.loads(hist_path.read_text(encoding="utf-8"))[-limit:]
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


def sample_chill_seed(recent_history):
    """Picks a fresh dry-observational or silly 'what if' chill topic and cast lineup."""
    used_hooks = {h.get("top_hook", "") for h in recent_history}
    recent_flavors = [h.get("flavor", "") for h in recent_history[-2:]]

    for _ in range(50):
        topic = random.choice(CHILL_TOPICS)
        if topic["hook"] in used_hooks:
            continue
        if recent_flavors and len(set(recent_flavors)) == 1 and topic["flavor"] == recent_flavors[0] and random.random() < 0.75:
            continue

        cast_mode = "role_call_trio" if "video call" in topic["hook"] or "union" in topic["hook"] else random.choice(
            ["solo_chill", "solo_chill", "banter_duo", "role_call_trio"]
        )
        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        style_key = random.choice(list(ART_STYLES.keys()))
        return {
            "combo_key": f"{topic['flavor']}|{cast_mode}|{'+'.join(characters)}|{topic['hook'][:28]}",
            "flavor": topic["flavor"],
            "cast_mode": cast_mode,
            "characters": characters,
            "topic": topic,
            "art_style_key": style_key,
        }

    fallback_topic = random.choice(CHILL_TOPICS)
    return {
        "combo_key": f"chill_{int(time.time())}",
        "flavor": fallback_topic["flavor"],
        "cast_mode": "solo_chill",
        "characters": ["Phil"],
        "topic": fallback_topic,
        "art_style_key": "reference_webcomic_2d",
    }


def compute_beat_durations(scenes):
    durations = []
    for idx, sc in enumerate(scenes):
        words = len((sc.get("bottom_caption") or "").split())
        read_sec = words / VISUAL_TUNING["words_per_sec"]
        cushion = 1.35 if idx == len(scenes) - 1 else 1.10
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], read_sec + cushion)), 2)
        durations.append(dur)
    return durations


def _build_local_fallback_script(seed):
    topic = seed["topic"]
    chars = seed["characters"]
    char_str = " and ".join(chars)
    style_key = seed["art_style_key"]
    markers = topic["markers"]

    return {
        "top_hook": topic["hook"],
        "environment_key": topic["env"],
        "setting_continuity": ENVIRONMENT_PRESETS[topic["env"]]["desc"],
        "music_prompt": "Chill laid-back lo-fi marimba, soft Rhodes keys, and gentle acoustic bass loop",
        "music_bpm": 98,
        "scenes": [
            {
                "clock_label": markers[0],
                "bottom_caption": "Calmly setting up the whole situation.",
                "expression": "confident_smirk",
                "end_expression": "deadpan_camera_stare",
                "body_action": "slouch_sigh",
                "prop_overlay": "none",
                "visual_prompt": f"{char_str} in {topic['env']} with calm deadpan poise, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_amber_desk",
                "end_grade": "warm_amber_desk",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "dust",
                "sfx_cue": "pop_ding",
            },
            {
                "clock_label": markers[1],
                "bottom_caption": "Wait... let's think this through.",
                "expression": "deadpan_camera_stare",
                "end_expression": "exhausted_half_lidded",
                "body_action": "phone_scroll_lean",
                "prop_overlay": "phone_vibrate_arcs",
                "visual_prompt": f"{char_str} leaning forward with deadpan focus, NO text",
                "art_style_key": style_key,
                "start_grade": "suburban_daylight_cel",
                "end_grade": "suburban_daylight_cel",
                "camera_move": "pan_follow_right",
                "transition_in": "blur_dissolve",
                "env_effect": "screen_glow",
                "sfx_cue": "whoosh",
            },
            {
                "clock_label": markers[2],
                "bottom_caption": "Hold on, it's getting weirdly specific.",
                "expression": "sweat_grit",
                "end_expression": "bloodshot_shock",
                "body_action": "struggle_pull",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Close-up reaction of {char_str} mid-thought, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_amber_desk",
                "end_grade": "dim_night_phone_glow",
                "camera_move": "snap_zoom_face",
                "transition_in": "whip_pan_left",
                "env_effect": "none",
                "sfx_cue": "record_scratch",
            },
            {
                "clock_label": markers[3],
                "bottom_caption": "Anyway. Back to doing nothing.",
                "expression": "deadpan_camera_stare",
                "end_expression": "confident_smirk",
                "body_action": "slouch_sigh",
                "prop_overlay": "none",
                "visual_prompt": f"Pulled-back shot of {char_str} back in chill deadpan mode, NO text",
                "art_style_key": style_key,
                "start_grade": "dim_night_phone_glow",
                "end_grade": "desaturated_gloom",
                "camera_move": "pull_back_reveal",
                "transition_in": "smash_zoom_cut",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub",
            },
        ],
        "ig_caption": f"{topic['hook']} — zero regrets.",
        "pinned_comment": "Is this a dry truth or a silly what-if to you?",
    }


def validate_and_fix_plan(script_data, seed):
    if not isinstance(script_data, dict):
        return _build_local_fallback_script(seed)
    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 4:
        return _build_local_fallback_script(seed)

    scenes = scenes[:4]
    topic = seed["topic"]
    used_cams = set()
    used_trans = set()

    if not script_data.get("top_hook"):
        script_data["top_hook"] = topic["hook"]
    if script_data.get("environment_key") not in ENVIRONMENT_PRESETS:
        script_data["environment_key"] = topic["env"]

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = list(COLOR_GRADES.keys())[idx % len(COLOR_GRADES)]
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]
        if sc.get("art_style_key") not in ART_STYLES:
            sc["art_style_key"] = seed["art_style_key"]
        if sc.get("expression") not in FACIAL_EXPRESSIONS:
            sc["expression"] = "deadpan_camera_stare"
        if sc.get("end_expression") not in FACIAL_EXPRESSIONS:
            sc["end_expression"] = sc["expression"]
        if sc.get("body_action") not in ALL_BODY_ACTIONS:
            sc["body_action"] = "slouch_sigh"
        if sc.get("prop_overlay") not in ALL_PROP_OVERLAYS:
            sc["prop_overlay"] = "none"
        if sc.get("env_effect") not in ALL_ENV_EFFECTS:
            sc["env_effect"] = "none"
        if sc.get("sfx_cue") not in ALL_SFX_CUES:
            sc["sfx_cue"] = ALL_SFX_CUES[idx % len(ALL_SFX_CUES)]
        if not sc.get("clock_label"):
            sc["clock_label"] = topic["markers"][idx]

        cam = sc.get("camera_move")
        if cam not in ALL_CAMERA_MOVES or cam in used_cams:
            avail = [c for c in ALL_CAMERA_MOVES if c not in used_cams]
            cam = random.choice(avail) if avail else "dolly_push_in"
        sc["camera_move"] = cam
        used_cams.add(cam)

        tr = sc.get("transition_in")
        if tr not in ALL_TRANSITIONS or tr in used_trans:
            avail_t = [t for t in ALL_TRANSITIONS if t not in used_trans]
            tr = random.choice(avail_t) if avail_t else "hard_cut"
        sc["transition_in"] = tr
        used_trans.add(tr)

        words = (sc.get("bottom_caption") or "").strip().split()
        if len(words) > 9:
            sc["bottom_caption"] = " ".join(words[:9])

    script_data["scenes"] = scenes
    return script_data


def build_smart_hashtags(raw_caption, script_data, seed):
    base_text = (raw_caption or "").strip()
    body_lines = []
    tags = []

    for line in base_text.splitlines():
        kept = []
        for word in line.split():
            if word.startswith("#"):
                tags.append(word.lower())
            else:
                kept.append(word)
        if kept:
            body_lines.append(" ".join(kept))

    style_key = script_data.get("scenes", [{}])[0].get("art_style_key", seed["art_style_key"])
    tags.extend(ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"])["hashtags"])
    tags.extend(["#chillcomedy", "#wearechillclub", "#funnyreels"])

    clean_tags = []
    for tag in tags:
        norm = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(norm) > 2 and norm not in clean_tags:
            clean_tags.append(norm)
        if len(clean_tags) >= 6:
            break

    body = "\n".join(body_lines).strip() or "Tell me this isn't painfully accurate."
    return f"{body}\n\n{' '.join(clean_tags)}"


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
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.95,
                    "maxOutputTokens": 2400,
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
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 4:
                        print(f"Generated chill comedy script with {model}")
                        return validate_and_fix_plan(parsed, seed)
                    last_err = f"{model} returned incomplete JSON"
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                last_err = f"{model} ParseError: {e}"
                time.sleep(1)
            except urllib.error.HTTPError as e:
                err_txt = e.read().decode("utf-8", errors="replace")[:240]
                last_err = f"{model} HTTP {e.code}: {err_txt}"
                if e.code in (400, 404, 429):
                    break
                if e.code in (500, 503):
                    time.sleep(3 * attempt)
                else:
                    raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} Network/Timeout: {e}"
                time.sleep(2)

    print(f"Gemini script fallback ({last_err}); using local chill script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 2X-SUPERSAMPLED 24FPS WEBCOMIC RENDERER + OPTIONAL AI BACKGROUND PLATE
# ==============================================================================
def _is_night_scene(sc):
    grade = sc.get("start_grade", "")
    return "dim_night" in grade or "bedroom" in grade


def _try_generate_ai_room_plate(env_key, setting_continuity, style_key, out_bg_path):
    style_desc = ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"])["prompt"]
    prompt = (
        f"{style_desc}. Environment: {setting_continuity}. "
        "Keep the center clear for characters and include one clean focal prop. "
        "Strictly NO people, NO characters, NO faces, NO text."
    )
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=){GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode())
            for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in part:
                    img = Image.open(io.BytesIO(base64.b64decode(part["inlineData"]["data"]))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                    img.save(out_bg_path, format="PNG")
                    print("Generated AI 2D chill background plate")
                    return True
    except Exception as e:
        print(f"AI background plate skipped ({e}), using supersampled procedural room")
    return False


def _render_environment_background(env_key, sc, out_bg_path):
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)
    wall_col = env.get("night_wall", env["wall"]) if is_night else env["wall"]

    bw, bh = W * SS, H * SS
    img = Image.new("RGB", (bw, bh), color=wall_col)
    draw = ImageDraw.Draw(img)

    if env_key == "living_room_window":
        sky_col = (34, 48, 82) if is_night else (168, 214, 248)
        draw.rectangle([120 * SS, 370 * SS, (W - 120) * SS, 940 * SS], fill=sky_col, outline=ink, width=8 * SS)
        draw.line([(bw // 2, 370 * SS), (bw // 2, 940 * SS)], fill=ink, width=8 * SS)
        draw.rounded_rectangle([80 * SS, 990 * SS, (W - 80) * SS, 1250 * SS], radius=34 * SS, fill=env["surface"], outline=ink, width=8 * SS)
    elif env_key == "overcast_bedroom":
        draw.rounded_rectangle([120 * SS, 820 * SS, (W - 120) * SS, 1130 * SS], radius=24 * SS, fill=(150, 142, 134), outline=ink, width=7 * SS)
    elif env_key == "kitchen_counter":
        draw.rounded_rectangle([160 * SS, 420 * SS, (W - 160) * SS, 650 * SS], radius=20 * SS, fill=(240, 242, 246), outline=ink, width=6 * SS)
    else:
        draw.ellipse([(W // 2 - 280) * SS, 360 * SS, (W // 2 + 280) * SS, 920 * SS], fill=(236, 178, 112))

    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _lerp_color(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def _draw_articulated_character(draw, name, cx, cy, scale, expr, body_action, t, local_p, idx_in_cast):
    prof = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])
    ink = (18, 18, 22)
    head_fill = (216, 213, 208)
    head_shadow = (188, 185, 180)
    phase = idx_in_cast * 1.15

    pop_p = min(1.0, local_p / 0.10)
    squash_x = 1.0 + math.sin(pop_p * math.pi) * 0.07
    squash_y = 1.0 - math.sin(pop_p * math.pi) * 0.06

    body_dx = int(math.sin(t * 1.8 + phase) * 5 * scale)
    body_dy = int(math.sin(t * 2.6 + phase) * 5 * scale)
    head_tilt_x = int(math.sin(t * 1.6 + phase) * 8 * scale)
    torso_lean_x = 0

    if body_action == "phone_scroll_lean":
        torso_lean_x = int(14 * scale)
        head_tilt_x = int(16 * scale)
    elif body_action == "shock_recoil":
        recoil = math.sin(min(1.0, local_p * 4.0) * math.pi * 0.5)
        body_dy = int(-24 * recoil * scale) + int(math.sin(t * 44.0 + phase) * 5 * scale)
        torso_lean_x = int(-16 * recoil * scale)
    elif body_action == "struggle_pull":
        tug = math.sin(t * 13.0 + phase)
        body_dx += int(tug * 14 * scale)
        torso_lean_x = int(-14 * scale + tug * 10 * scale)
    elif body_action == "celebrate_groove":
        body_dy = int(-abs(math.sin(t * 7.5 + phase)) * 18 * scale)

    hx = int((cx + body_dx + head_tilt_x) * SS)
    hy = int((cy + body_dy) * SS)
    rx_head = int(106 * scale * squash_x * SS)
    ry_head = int(106 * scale * squash_y * SS)
    neck_x = int((cx + body_dx + torso_lean_x * 0.6) * SS)
    neck_y = hy + ry_head - 4 * SS
    hip_x = int((cx + body_dx) * SS)
    hip_y = neck_y + int(170 * scale * SS)
    limb_w = max(5 * SS, int(8 * scale * SS))
    mitten_r = max(10 * SS, int(15 * scale * SS))

    draw.line([(neck_x, neck_y), (hip_x, hip_y)], fill=ink, width=limb_w)
    for side in (-1, 1):
        kx = hip_x + side * int(50 * scale * SS)
        ky = hip_y + int(68 * scale * SS)
        fx = hip_x + side * int(52 * scale * SS)
        fy = hip_y + int(148 * scale * SS)
        draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)

    if prof["satchel"]:
        draw.line([(neck_x - int(18 * scale * SS), neck_y + 10 * SS), (hip_x + int(22 * scale * SS), hip_y - 8 * SS)], fill=(128, 84, 52), width=max(6 * SS, int(9 * scale * SS)))

    sh_x = neck_x + int(torso_lean_x * 0.2 * SS)
    sh_y = neck_y + int(28 * scale * SS)
    l_elb = (sh_x - int(66 * scale * SS), sh_y + int(44 * scale * SS))
    l_hand = (hx - int(32 * scale * SS), hy + int(80 * scale * SS))
    r_elb = (sh_x + int(64 * scale * SS), sh_y + int(46 * scale * SS))
    r_hand = (sh_x + int(70 * scale * SS), sh_y + int(84 * scale * SS))
    draw.line([(sh_x, sh_y), l_elb, l_hand], fill=ink, width=limb_w)
    draw.line([(sh_x, sh_y), r_elb, r_hand], fill=ink, width=limb_w)
    for mhx, mhy in (l_hand, r_hand):
        draw.ellipse([mhx - mitten_r, mhy - mitten_r, mhx + mitten_r, mhy + mitten_r], fill=ink)

    draw.ellipse([hx - rx_head, hy - ry_head, hx + rx_head, hy + ry_head], fill=head_fill)
    draw.pieslice([hx - rx_head + 6 * SS, hy - ry_head + 6 * SS, hx + rx_head - 2 * SS, hy + ry_head - 2 * SS], start=-55, end=65, fill=head_shadow)
    draw.ellipse([hx - rx_head, hy - ry_head, hx + rx_head, hy + ry_head], outline=ink, width=max(6 * SS, int(9 * scale * SS)))

    if prof["cap_color"]:
        cap_c = prof["cap_color"]
        draw.pieslice([hx - rx_head - 2 * SS, hy - ry_head - 12 * SS, hx + rx_head + 2 * SS, hy - int(ry_head * 0.12)], start=180, end=360, fill=cap_c, outline=ink, width=max(6 * SS, int(8 * scale * SS)))
        draw.rounded_rectangle([hx - int(10 * scale * SS), hy - int(ry_head * 0.56), hx + int(rx_head * 1.32), hy - int(ry_head * 0.34)], radius=8 * SS, fill=cap_c, outline=ink, width=max(5 * SS, int(7 * scale * SS)))

    if prof["beard"]:
        draw.pieslice([hx - int(rx_head * 0.86), hy + int(4 * scale * SS), hx + int(rx_head * 0.86), hy + ry_head + 4 * SS], start=0, end=180, fill=(92, 64, 46), outline=ink, width=max(5 * SS, int(7 * scale * SS)))

    eye_dx = int(36 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(22 * scale * SS)
    is_blinking = ((t + idx_in_cast * 0.9) % 2.8) < 0.11
    pupil_x = int(math.sin(t * 1.7 + phase) * 4 * scale * SS)

    if is_blinking and expr != "bloodshot_shock":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.line([(ex - er + 4 * SS, eye_y), (ex + er - 4 * SS, eye_y)], fill=ink, width=max(5 * SS, int(6 * scale * SS)))
    elif expr == "exhausted_half_lidded":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(252, 252, 255), outline=ink, width=4 * SS)
            draw.ellipse([ex - 6 * SS + pupil_x, eye_y - 4 * SS, ex + 6 * SS + pupil_x, eye_y + 8 * SS], fill=ink)
            draw.pieslice([ex - er, eye_y - er, ex + er, eye_y + er], start=180, end=360, fill=head_fill, outline=ink, width=4 * SS)
    elif expr == "bloodshot_shock":
        for side in (-1, 1):
            ex = hx + side * eye_dx
            er_big = int(28 * scale * SS)
            draw.ellipse([ex - er_big, eye_y - er_big, ex + er_big, eye_y + er_big], fill=(255, 250, 250), outline=ink, width=5 * SS)
            draw.ellipse([ex - 6 * SS, eye_y - 6 * SS, ex + 6 * SS, eye_y + 6 * SS], fill=ink)
    else:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - 11 * SS + pupil_x, eye_y - 11 * SS, ex + 11 * SS + pupil_x, eye_y + 11 * SS], fill=ink)

    if expr == "confident_smirk":
        draw.arc([hx - int(20 * scale * SS), hy + int(22 * scale * SS), hx + int(26 * scale * SS), hy + int(44 * scale * SS)], start=12, end=165, fill=ink, width=max(4 * SS, int(6 * scale * SS)))
    else:
        draw.line([(hx - int(22 * scale * SS), hy + int(36 * scale * SS)), (hx + int(22 * scale * SS), hy + int(34 * scale * SS))], fill=ink, width=max(4 * SS, int(6 * scale * SS)))

    if prof["glasses"]:
        gr = int(28 * scale * SS)
        for side in (-1, 1):
            gx = hx + side * eye_dx
            draw.rectangle([gx - gr, eye_y - gr, gx + gr, eye_y + gr], outline=ink, width=max(4 * SS, int(6 * scale * SS)))
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=max(4 * SS, int(6 * scale * SS)))


def _draw_foreground_occlusion(draw, env_key, sc):
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)

    if env_key == "overcast_bedroom":
        blanket_col = (74, 86, 112) if is_night else env["surface"]
        draw.rounded_rectangle([70 * SS, 1085 * SS, (W - 70) * SS, 1580 * SS], radius=34 * SS, fill=blanket_col, outline=ink, width=8 * SS)
    elif env_key == "living_room_window":
        draw.rounded_rectangle([80 * SS, 1145 * SS, (W - 80) * SS, 1520 * SS], radius=34 * SS, fill=env["surface"], outline=ink, width=8 * SS)
    else:
        draw.rectangle([0, 1130 * SS, W * SS, H * SS], fill=env["surface"])
        draw.line([(0, 1130 * SS), (W * SS, 1130 * SS)], fill=ink, width=8 * SS)
        draw.rounded_rectangle([835 * SS, 1050 * SS, 915 * SS, 1130 * SS], radius=12 * SS, fill=env["accent_prop"], outline=ink, width=5 * SS)


def render_animated_frame(bg_img, characters, env_key, sc, beat_idx, t, local_p):
    frame_hi = bg_img.resize((W * SS, H * SS), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(frame_hi)

    expr = sc.get("expression", "deadpan_camera_stare") if local_p < 0.45 else sc.get("end_expression", "deadpan_camera_stare")
    body_action = sc.get("body_action", "slouch_sigh")
    count = max(1, min(3, len(characters)))

    if beat_idx == 2:
        _draw_articulated_character(draw, characters[0], W // 2, 855, 1.32, expr, body_action, t, local_p, 0)
    else:
        spacing = min(260, (W - 200) // count)
        start_x = (W // 2) - ((count - 1) * spacing) // 2
        scale = 1.04 if count == 1 else (0.90 if count == 2 else 0.78)
        for idx, name in enumerate(characters[:3]):
            cx = start_x + idx * spacing
            cy = 845 + (idx % 2) * 10
            char_expr = expr if idx == 0 else "deadpan_camera_stare"
            _draw_articulated_character(draw, name, cx, cy, scale, char_expr, body_action, t, local_p, idx)

    if body_action != "walk_stride":
        _draw_foreground_occlusion(draw, env_key, sc)

    return frame_hi.resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# AUDIO (LYRIA REALTIME WITH SAFE SYNTH FALLBACK + SIDECHAIN SFX)
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

        deadline = time.time() + 25
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
        str(out_wav),
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria chill score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.25) * math.pi)
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * env * 0.28
    if cue == "record_scratch":
        env = math.exp(-dt * 6.0)
        freq = 640.0 * math.exp(-dt * 5.0) + 90.0 * math.sin(dt * 90.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.40
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.5)
        freq = 72.0 * math.exp(-dt * 1.7)
        return math.sin(2 * math.pi * freq * dt) * env * 0.52
    if cue == "riser_hit":
        if dt < 0.30:
            return math.sin(2 * math.pi * (220 + 1200 * dt) * dt) * (dt / 0.30) * 0.28
        return math.sin(2 * math.pi * 64.0 * dt) * math.exp(-(dt - 0.30) * 7.5) * 0.46
    return math.sin(2 * math.pi * 987.77 * dt) * math.exp(-dt * 15.0) * 0.25


def build_director_audio(music_prompt, bpm, scenes, beat_starts, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating chill pluck bed...")
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
    cues = [(beat_starts[i] + (0.10 if i == 0 else 0.0), scenes[i].get("sfx_cue", "pop_ding")) for i in range(len(scenes))]

    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sr
            sig = sum(_synth_cue_sample(c, t - st) for st, c in cues if st <= t <= st + 0.58)
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            frames.extend(struct.pack("<hh", s, s))
        wf.writeframes(frames)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex",
        "[1:a]asplit=2[sfx_sc][sfx_mix];"
        "[0:a][sfx_sc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=220[ducked_bed];"
        "[ducked_bed][sfx_mix]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav),
    ], check=True)


# ==============================================================================
# CAMERA, GRADE & OVERLAYS
# ==============================================================================
def build_vignette_mask(strength=0.14):
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


def apply_grade(frame, sc, local_p, vignette_mask, glow_mask):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
    prog = _ease_in_out_sine(local_p)

    graded = Image.blend(frame, Image.new("RGB", (W, H), _lerp_color(g1["tint"], g2["tint"], prog)), VISUAL_TUNING["color_tint_strength"])
    if VISUAL_TUNING["ambient_glow_strength"] > 0:
        graded = Image.composite(Image.new("RGB", (W, H), _lerp_color(g1["glow"], g2["glow"], prog)), graded, glow_mask)
    graded = ImageEnhance.Contrast(graded).enhance(g1["contrast"] + (g2["contrast"] - g1["contrast"]) * prog)
    graded = ImageEnhance.Color(graded).enhance(g1["sat"] + (g2["sat"] - g1["sat"]) * prog)
    return Image.composite(Image.new("RGB", (W, H), (10, 12, 18)), graded, vignette_mask)


def apply_camera(base_img, move, local_p, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    breath = math.sin(t * 1.8) * 0.002

    if move == "pull_back_reveal":
        zoom = (1.0 + max_z) - (max_z * _ease_out_quart(local_p)) + breath
    elif move == "snap_zoom_face":
        zoom = (1.0 + max_z * 1.25) - (max_z * 0.2 * _ease_in_out_sine(local_p))
    elif move == "locked_deadpan":
        zoom = 1.02
    elif move == "gentle_float":
        zoom = 1.03 + math.sin(_ease_in_out_sine(local_p) * math.pi) * 0.02
    else:
        zoom = 1.0 + (max_z * _ease_in_out_sine(local_p)) + breath

    zoom = max(1.02, zoom)
    cw, ch = int(W / zoom), int(H / zoom)
    max_dx, max_dy = W - cw, H - ch
    x0 = int(max_dx * _ease_in_out_sine(local_p)) if move == "pan_follow_right" else max_dx // 2
    y0 = max_dy // 2
    return base_img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)


def apply_transition(prev_frame, curr_frame, tr_name, tr_p):
    eased = _ease_out_quart(tr_p)
    if tr_name == "hard_cut":
        return curr_frame
    if tr_name == "smash_zoom_cut":
        scale = 1.14 - 0.14 * eased
        cw, ch = int(W / scale), int(H / scale)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        return curr_frame.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)
    if tr_name in ("whip_pan_left", "whip_pan_right"):
        direction = -1 if tr_name == "whip_pan_left" else 1
        shift = int((1.0 - eased) * W * direction)
        canvas = Image.new("RGB", (W, H), (14, 16, 22))
        canvas.paste(prev_frame, (shift - W * direction, 0))
        canvas.paste(curr_frame, (shift, 0))
        return canvas
    if tr_name == "blur_dissolve" and VISUAL_TUNING.get("enable_blur_transition", True):
        blended = Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))
        blur_r = math.sin(tr_p * math.pi) * 3.5
        if blur_r > 0.3:
            return blended.resize((W // 4, H // 4), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=blur_r)).resize((W, H), Image.Resampling.BILINEAR)
        return blended
    return Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))


def _load_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_overlays(frame, top_hook, sc, beat_idx, total_beats, scene_t, beat_dur, t, handle):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, beat_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg, c_fg = g2["card_bg"], g2["card_fg"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    hook_str = (top_hook or "").strip()
    if hook_str:
        ent = _ease_out_quart(min(1.0, t / 0.20))
        hook_font = _load_font(38)
        wrapped_hook = textwrap.fill(hook_str, width=32)
        h_lines = wrapped_hook.split("\n")
        box_h = 34 + len(h_lines) * 48
        bx0, by0 = 84, 130 + int((1.0 - ent) * -12)
        alpha = int(248 * ent)
        odraw.rounded_rectangle([bx0, by0, W - 84, by0 + box_h], radius=24, fill=(255, 253, 248, alpha), outline=(18, 18, 22, alpha), width=5)
        odraw.multiline_text((W // 2, by0 + box_h // 2), wrapped_hook, font=hook_font, fill=(18, 18, 22, alpha), anchor="mm", align="center", spacing=8)

        marker = (sc.get("clock_label") or "").strip()
        if marker:
            m_font = _load_font(30)
            mb = odraw.textbbox((0, 0), marker, font=m_font)
            mw = (mb[2] - mb[0]) + 46
            cx0 = (W - mw) // 2
            cy0 = by0 + box_h + 14
            odraw.rounded_rectangle([cx0, cy0, cx0 + mw, cy0 + 46], radius=23, fill=(18, 20, 28, 238), outline=(acc[0], acc[1], acc[2], 240), width=3)
            odraw.text((W // 2, cy0 + 23), marker, font=m_font, fill=(acc[0], acc[1], acc[2], 255), anchor="mm")

    cap = (sc.get("bottom_caption") or "").strip()
    if cap:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.14))
        time_left = max(0.0, beat_dur - scene_t)
        cap_out = 1.0 if (beat_idx == total_beats - 1 or time_left > 0.10) else max(0.0, time_left / 0.10)
        cap_alpha = int(248 * cap_in * cap_out)
        cap_font = _load_font(38)
        wrapped = textwrap.fill(cap, width=32)
        lines = wrapped.split("\n")
        box_h = 44 + len(lines) * 50
        x0, y0 = 96, 1385 + int((1.0 - cap_in) * 10)
        odraw.rounded_rectangle([x0, y0, W - 96, y0 + box_h], radius=24, fill=(c_bg[0], c_bg[1], c_bg[2], min(246, cap_alpha)), outline=(acc[0], acc[1], acc[2], cap_alpha), width=3)
        odraw.multiline_text((W // 2, y0 + box_h // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=8)

    odraw.text((W // 2, 1625), handle, font=_load_font(28), fill=(255, 255, 255, 235), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_chill_reel(page_cfg, script_data, seed, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:4]
    total_beats = len(scenes)
    characters = seed["characters"]
    env_key = script_data.get("environment_key", seed["topic"]["env"])
    setting_continuity = script_data.get("setting_continuity", ENVIRONMENT_PRESETS[env_key]["desc"])

    shared_ai_bg = tmp_dir / "ai_bg.png"
    has_ai_bg = _try_generate_ai_room_plate(env_key, setting_continuity, seed["art_style_key"], shared_ai_bg)

    scene_bgs = []
    for idx, sc in enumerate(scenes):
        if has_ai_bg:
            scene_bgs.append(Image.open(shared_ai_bg).convert("RGB"))
        else:
            bg_p = tmp_dir / f"bg_{idx}.png"
            _render_environment_background(env_key, sc, bg_p)
            scene_bgs.append(Image.open(bg_p).convert("RGB"))

    beat_durations = compute_beat_durations(scenes)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t

    final_wav = tmp_dir / "final_audio.wav"
    build_director_audio(
        script_data.get("music_prompt", "chill laid-back lo-fi marimba comedy loop"),
        script_data.get("music_bpm", 98),
        scenes,
        beat_starts,
        total_dur,
        final_wav,
    )

    total_frames = int(total_dur * FPS)
    top_hook = script_data.get("top_hook", seed["topic"]["hook"])
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
    prev_frame = None

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

        stage = render_animated_frame(scene_bgs[s_idx], characters, env_key, sc, s_idx, t, local_p)
        frame = apply_camera(stage, sc.get("camera_move", "dolly_push_in"), local_p, t)
        frame = apply_grade(frame, sc, local_p, vignette_mask, glow_mask)

        trans_dur = VISUAL_TUNING["transition_sec"]
        if s_idx > 0 and scene_t < trans_dur and prev_frame is not None:
            frame = apply_transition(prev_frame, frame, sc.get("transition_in", "hard_cut"), scene_t / trans_dur)
        else:
            prev_frame = frame.copy()

        draw = ImageDraw.Draw(frame)
        g_curr = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
        bar_x = int(W * min(1.0, (f_idx + 1) / max(1, total_frames)))
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=g_curr["accent"])

        frame = draw_overlays(frame, top_hook, sc, s_idx, total_beats, scene_t, beat_dur, t, page_cfg["handle"])
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
        str(out_mp4),
    ], check=True)
    shutil.rmtree(tmp_dir)
    print(f"Rendered chill Reel ({total_dur:.1f}s): {out_mp4}")


# ==============================================================================
# GITHUB PAGES & META GRAPH API V21.0 PUBLISHING
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
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages ({attempt}/15): {e}")

    raise RuntimeError(f"GitHub Pages did not serve MP4 in time: {pages_url}")


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API {e.code} on {url}: {e.read().decode('utf-8', errors='replace')}") from e


def publish_to_instagram(ig_id, token, video_url, caption):
    if not token or not ig_id:
        return
    base = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{ig_id}"
    container = post_request(f"{base}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token,
    })
    creation_id = container["id"]
    for attempt in range(1, 20):
        time.sleep(5)
        status_url = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{creation_id}?fields=status_code,status&access_token={token}"
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel status ({attempt}/20): {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram Reel failed: {status_data}")

    published = post_request(f"{base}/media_publish", {"creation_id": creation_id, "access_token": token})
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {published['id']}")


def publish_to_facebook_reels(fb_page_id, token, video_url, description):
    if not token or not fb_page_id:
        return
    base = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{fb_page_id}/video_reels"
    start = post_request(base, {"upload_phase": "start", "access_token": token})
    video_id = start["video_id"]

    rupload_url = f"[https://rupload.facebook.com/video-upload/](https://rupload.facebook.com/video-upload/){GRAPH_VERSION}/{video_id}"
    req = urllib.request.Request(rupload_url, method="POST", headers={"Authorization": f"OAuth {token}", "file_url": video_url})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("Uploaded MP4 to Facebook Reels:", resp.read().decode())

    finish = post_request(base, {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": description,
        "access_token": token,
    })
    print(f"LIVE ON FACEBOOK REELS ({fb_page_id})! Response: {finish}")


if __name__ == "__main__":
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    trends = fetch_live_trends()

    for page in load_active_pages():
        slug = page["slug"]
        recent_history = load_history(slug, limit=40)
        recent_hooks = "\n".join(f"- {h.get('top_hook', '')}" for h in recent_history if h.get("top_hook")) or "None yet"
        seed = sample_chill_seed(recent_history)
        topic = seed["topic"]
        cast_lines = "\n".join(f"- {c}: {CAST_IDENTITY[c]['archetype']}" for c in seed["characters"])

        prompt = (
            f"You write chill comedy Reels for {page['handle']}.\n"
            f"CHANNEL VIBE: {page['domain']}\n"
            f"COMEDY FLAVOR THIS RUN: {seed['flavor']} (blend dry deadpan observation and silly 'what if' logic without loud yelling or clichés)\n"
            f"CAST MODE: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"CHARACTERS:\n{cast_lines}\n"
            f"HOOK IDEA: {topic['hook']}\n"
            f"STORY IDEA: {topic['story_seed']}\n"
            f"ENVIRONMENT: {topic['env']} ({ENVIRONMENT_PRESETS[topic['env']]['desc']})\n"
            f"MARKERS: {topic['markers']}\n"
            f"OPTIONAL TRENDS:\n{trends}\n"
            f"AVOID REPEATING HOOKS:\n{recent_hooks}\n\n"
            "Write a tight 4-beat script where viewers stay hooked to the final beat. "
            "Keep 'top_hook' natural with zero emojis, and keep each 'bottom_caption' under 8 words.\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            f'  "top_hook": "{topic["hook"]}",\n'
            f'  "environment_key": "{topic["env"]}",\n'
            f'  "setting_continuity": "{ENVIRONMENT_PRESETS[topic["env"]]["desc"]}",\n'
            '  "music_prompt": "Chill laid-back lo-fi marimba and soft Rhodes comedy loop",\n'
            '  "music_bpm": 98,\n'
            '  "scenes": [\n'
            f'    {{"clock_label": "{topic["markers"][0]}", "bottom_caption": "Calmly setting up the whole situation.", "expression": "confident_smirk", "end_expression": "deadpan_camera_stare", "body_action": "slouch_sigh", "prop_overlay": "none", "visual_prompt": "Beat 1 setup pose, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "warm_amber_desk", "end_grade": "warm_amber_desk", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "dust", "sfx_cue": "pop_ding"}},\n'
            f'    {{"clock_label": "{topic["markers"][1]}", "bottom_caption": "Wait... let\'s think this through.", "expression": "deadpan_camera_stare", "end_expression": "exhausted_half_lidded", "body_action": "phone_scroll_lean", "prop_overlay": "phone_vibrate_arcs", "visual_prompt": "Beat 2 escalation pose, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "suburban_daylight_cel", "end_grade": "suburban_daylight_cel", "camera_move": "pan_follow_right", "transition_in": "blur_dissolve", "env_effect": "screen_glow", "sfx_cue": "whoosh"}},\n'
            f'    {{"clock_label": "{topic["markers"][2]}", "bottom_caption": "Hold on, it\'s getting weirdly specific.", "expression": "sweat_grit", "end_expression": "bloodshot_shock", "body_action": "struggle_pull", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 3 close reaction, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "warm_amber_desk", "end_grade": "dim_night_phone_glow", "camera_move": "snap_zoom_face", "transition_in": "whip_pan_left", "env_effect": "none", "sfx_cue": "record_scratch"}},\n'
            f'    {{"clock_label": "{topic["markers"][3]}", "bottom_caption": "Anyway. Back to doing nothing.", "expression": "deadpan_camera_stare", "end_expression": "confident_smirk", "body_action": "slouch_sigh", "prop_overlay": "none", "visual_prompt": "Beat 4 deadpan payoff, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "dim_night_phone_glow", "end_grade": "desaturated_gloom", "camera_move": "pull_back_reveal", "transition_in": "smash_zoom_cut", "env_effect": "none", "sfx_cue": "vine_boom_sub"}}\n'
            "  ],\n"
            '  "ig_caption": "Short chill caption inviting a tag or reply",\n'
            '  "pinned_comment": "Fun chill question for the comments"\n'
            "}"
        )

        script_data = ask_gemini_script(prompt, seed)
        final_caption = build_smart_hashtags(script_data.get("ig_caption", ""), script_data, seed)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"

        render_chill_reel(page, script_data, seed, rel_mp4)
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Flavor: {seed['flavor']}\nCast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nHook: {script_data.get('top_hook', '')}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8",
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "flavor": seed["flavor"],
            "top_hook": script_data.get("top_hook", ""),
            "cast_mode": seed["cast_mode"],
            "characters": seed["characters"],
            "environment_key": script_data.get("environment_key", ""),
            "pinned_comment": script_data["pinned_comment"],
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
