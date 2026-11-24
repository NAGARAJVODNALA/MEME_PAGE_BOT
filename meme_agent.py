import os
import sys
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

VISUAL_TUNING = {
    "vignette_strength": 0.16,
    "color_tint_strength": 0.07,
    "ambient_glow_strength": 0.14,
    "particle_opacity": 0.28,
    "max_zoom_delta": 0.08,
    "transition_sec": 0.18,
    "enable_blur_transition": True,
    "min_beat_sec": 2.8,
    "max_beat_sec": 6.8
}

# ==============================================================================
# 1. REALISTIC HUMAN PROPORTIONS, CLOTHING & HANGOVER-INSPIRED VOICES
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Smooth Confident Instigator (Phil Wenneck / Bradley Cooper vibe: charismatic, fast-talking, persuasive swagger)",
        "voice_style": "Charismatic, confident, persuasive young man with smooth mid-high energy and comedic swagger",
        "skin_tone": (236, 196, 168),
        "skin_shadow": (208, 162, 134),
        "hair_color": (72, 48, 34),
        "hair_style": "styled_messy",
        "cap_color": (188, 52, 50),
        "backwards_cap": True,
        "body_type": "athletic",
        "height_scale": 1.03,
        "shoulder_w": 122,
        "waist_w": 102,
        "outfit": "layered_hoodie",
        "shirt_color": (194, 52, 50),
        "inner_tee": (244, 245, 248),
        "pants_color": (46, 54, 72),
        "shoe_color": (188, 50, 48),
        "beard": False,
        "glasses": False,
        "satchel": False,
        "gemini_voice": "Fenrir",
        "edge_voice": "en-US-GuyNeural",
        "edge_rate": "+6%",
        "edge_pitch": "+2Hz",
        "espeak_pitch": 54,
        "espeak_speed": 172
    },
    "Alan": {
        "archetype": "The Deadpan Oddball Wildcard (Alan Garner / Zach Galifianakis vibe: earnest, stocky, bizarre 2 AM logic, serious deadpan)",
        "voice_style": "Deadpan, earnest, slightly nasal oddball man speaking with serious childlike sincerity and quirky pauses",
        "skin_tone": (238, 202, 176),
        "skin_shadow": (210, 168, 142),
        "hair_color": (64, 44, 32),
        "hair_style": "curly_full",
        "cap_color": None,
        "backwards_cap": False,
        "body_type": "stocky",
        "height_scale": 0.97,
        "shoulder_w": 144,
        "waist_w": 138,
        "outfit": "crew_tee",
        "shirt_color": (92, 114, 74),
        "inner_tee": (72, 92, 56),
        "pants_color": (132, 114, 88),
        "shoe_color": (74, 92, 60),
        "beard": True,
        "glasses": False,
        "satchel": True,
        "gemini_voice": "Puck",
        "edge_voice": "en-US-ChristopherNeural",
        "edge_rate": "-6%",
        "edge_pitch": "-3Hz",
        "espeak_pitch": 40,
        "espeak_speed": 148
    },
    "Stu": {
        "archetype": "The High-Strung Nervous Overthinker (Stu Price / Ed Helms vibe: stressed, panics over money/alarms/schedules)",
        "voice_style": "High-strung, anxious, exasperated guy whose pitch rises when stressed or panicking",
        "skin_tone": (240, 204, 180),
        "skin_shadow": (212, 170, 146),
        "hair_color": (56, 40, 30),
        "hair_style": "neat_part",
        "cap_color": None,
        "backwards_cap": False,
        "body_type": "slim",
        "height_scale": 0.99,
        "shoulder_w": 106,
        "waist_w": 92,
        "outfit": "polo_shirt",
        "shirt_color": (78, 108, 146),
        "inner_tee": (236, 240, 246),
        "pants_color": (162, 148, 124),
        "shoe_color": (56, 80, 112),
        "beard": False,
        "glasses": True,
        "satchel": False,
        "gemini_voice": "Orus",
        "edge_voice": "en-US-EricNeural",
        "edge_rate": "+10%",
        "edge_pitch": "+8Hz",
        "espeak_pitch": 66,
        "espeak_speed": 180
    },
    "Doug": {
        "archetype": "The Calm Grounded Straight-Man (Doug Billings / Justin Bartha vibe: deep relaxed baritone, unbothered voice of reason)",
        "voice_style": "Deep, relaxed, dry baritone straight-man who sounds calm and unbothered next to his chaotic friends",
        "skin_tone": (232, 190, 162),
        "skin_shadow": (202, 156, 128),
        "hair_color": (48, 36, 28),
        "hair_style": "short_crop",
        "cap_color": None,
        "backwards_cap": False,
        "body_type": "tall_regular",
        "height_scale": 1.04,
        "shoulder_w": 118,
        "waist_w": 100,
        "outfit": "crew_tee",
        "shirt_color": (58, 106, 76),
        "inner_tee": (44, 84, 58),
        "pants_color": (48, 58, 76),
        "shoe_color": (44, 82, 58),
        "beard": False,
        "glasses": False,
        "satchel": False,
        "gemini_voice": "Charon",
        "edge_voice": "en-US-SteffanNeural",
        "edge_rate": "-2%",
        "edge_pitch": "-7Hz",
        "espeak_pitch": 32,
        "espeak_speed": 156
    }
}

CAST_MODES = {
    "classic_duo": {
        "desc": "2 contrasting friends in sharp spoken banter (shot-reverse-shot)",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Phil", "Alan"],
            ["Alan", "Stu"],
            ["Stu", "Doug"],
            ["Phil", "Doug"]
        ]
    },
    "trio_hangout": {
        "desc": "3 friends debating an everyday apartment, money, or late-night dilemma",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_crew_4": {
        "desc": "All 4 friends (Phil, Alan, Stu, and Doug) trading rapid one-liners",
        "lineups": [["Phil", "Alan", "Stu", "Doug"]]
    }
}

FACIAL_EXPRESSIONS = [
    "skeptical_half_lid",
    "angry_brow",
    "tired_bags",
    "maniacal_3am_grin",
    "smug_snooze",
    "exhausted_half_lidded",
    "sweat_grit",
    "guilty_puppy_eyes",
    "bloodshot_shock",
    "deadpan_camera_stare",
    "confident_smirk",
    "genuine_smile"
]

ALL_BODY_ACTIONS = [
    "phone_call_ear",
    "point_argue",
    "shrug_palms",
    "count_fingers",
    "temple_tap",
    "sleep_breathe_toss",
    "phone_scroll_lean",
    "shock_recoil",
    "struggle_pull",
    "walk_stride",
    "slouch_sigh",
    "celebrate_groove"
]

# ==============================================================================
# 2. ENVIRONMENTS, ART STYLES & SPOKEN COMEDY SCENARIOS
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "warm_desk_lamp": {
        "desc": "Warm amber-lit apartment room with walnut desk, framed art, potted plant, and ceramic mug",
        "wall": (196, 132, 84),
        "surface": (118, 72, 42),
        "accent_prop": (184, 58, 52)
    },
    "overcast_bedroom": {
        "desc": "Cozy bedroom with textured headboard, soft slate blanket, folded top sheet, framed mountain art, and lamp glow",
        "wall": (198, 204, 212),
        "night_wall": (44, 54, 80),
        "surface": (136, 146, 160),
        "accent_prop": (238, 240, 246)
    },
    "living_room_window": {
        "desc": "Suburban living room with slate-blue couch, warm lamp, and window overlooking yellow house and stacked delivery boxes",
        "wall": (176, 198, 222),
        "surface": (98, 122, 152),
        "accent_prop": (194, 148, 96)
    },
    "sidewalk_hangout": {
        "desc": "Clean suburban sidewalk with crisp blue sky, low brick wall, trees, and neighborhood house",
        "wall": (164, 206, 242),
        "surface": (154, 158, 166),
        "accent_prop": (186, 102, 78)
    },
    "midnight_car_cabin": {
        "desc": "Parked car interior at night with dashboard glow, steering wheel, and streetlights outside",
        "wall": (34, 46, 72),
        "surface": (24, 28, 38),
        "accent_prop": (118, 212, 255)
    },
    "kitchen_counter": {
        "desc": "Bright apartment kitchen with tiled backsplash, counter, pendant light, and coffee mug",
        "wall": (214, 206, 194),
        "surface": (134, 138, 146),
        "accent_prop": (86, 156, 108)
    }
}

ART_STYLES = {
    "reference_webcomic_2d": {
        "prompt": "Realistic-proportioned 2D illustrated comedy short with distinct body builds, layered t-shirts and hoodies, sculpted facial expressions, and lip-sync mouth shapes",
        "hashtags": ["#animatedshorts", "#2danimation", "#relatable"]
    },
    "cozy_lamp_cartoon": {
        "prompt": "Warm 2D illustrated comedy short with rich indoor lighting, realistic body anatomy, expressive eyes and lip-sync acting",
        "hashtags": ["#comedyskit", "#relatablememes", "#funnyreels"]
    },
    "suburban_cel_toon": {
        "prompt": "Clean daylight 2D illustrated comedy short with realistic human proportions and sharp comedic timing",
        "hashtags": ["#cartoonmemes", "#sliceoflife", "#friendgroup"]
    }
}

RELATABLE_SCENARIOS = [
    {
        "reel_mode": "spoken_skit",
        "hook": "When your friend says 'I'm 5 minutes away' 📞",
        "env": "sidewalk_hangout",
        "clocks": ["7:00 PM", "7:14 PM", "7:29 PM", "7:42 PM"],
        "story_seed": "Stu calls Phil who swears he is pulling onto the street right now while Stu hears Phil's microwave beeping in the background"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Friend math: why buying a $7 iced coffee saves money",
        "env": "kitchen_counter",
        "clocks": ["10:15 AM", "10:16 AM", "10:17 AM", "10:18 AM"],
        "story_seed": "Phil and Alan use finger-counting math to convince panicked Stu that buying a $7 iced coffee actually saves $20"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Trying to pick ONE restaurant with the boys",
        "env": "sidewalk_hangout",
        "clocks": ["8:05 PM", "8:22 PM", "8:40 PM", "9:02 PM"],
        "story_seed": "Doug asks where everyone wants to eat; Alan says 'anything works' and then vetoes tacos, burgers, and pizza"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "When you ask your friend to spot you 'until Friday'",
        "env": "warm_desk_lamp",
        "clocks": ["TUESDAY", "FRIDAY", "NEXT MONTH", "RIGHT NOW"],
        "story_seed": "Alan earnestly asks Stu to spot him $12 until Friday while conveniently forgetting the three previous Friday loans"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Me vs. my brain at 2:45 AM on a work night",
        "env": "overcast_bedroom",
        "clocks": ["22:00", "23:45", "01:30", "03:00"],
        "story_seed": "Tired Stu tries to go to sleep at 22:00 while Phil convinces him to watch just one more video until 03:00"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Stay home so we don't spend money, they said",
        "env": "living_room_window",
        "clocks": ["1:15 PM", "2:40 PM", "4:05 PM", "5:30 PM"],
        "story_seed": "Doug tries to stay on the couch to save money while Alan keeps ordering mystery packages to the front porch"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Sitting in the parked car after work for 40 minutes",
        "env": "midnight_car_cabin",
        "clocks": ["6:12 PM", "6:24 PM", "6:38 PM", "6:51 PM"],
        "story_seed": "Stu asks why they haven't gotten out of the parked car yet; Doug and Alan defend sacred driveway decompression time"
    }
]

# ==============================================================================
# 3. ENVIRONMENT COLOR GRADES, CAMERA MOVES & TRANSITIONS
# ==============================================================================
COLOR_GRADES = {
    "warm_amber_desk": {
        "tint": (235, 154, 88), "glow": (255, 208, 128), "contrast": 1.06, "sat": 1.08,
        "card_bg": (24, 18, 18), "card_fg": (255, 248, 240), "accent": (255, 184, 96)
    },
    "overcast_morning_bedroom": {
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.05, "sat": 0.94,
        "card_bg": (22, 24, 30), "card_fg": (248, 250, 255), "accent": (152, 196, 245)
    },
    "dim_night_phone_glow": {
        "tint": (58, 76, 112), "glow": (132, 214, 255), "contrast": 1.08, "sat": 0.96,
        "card_bg": (14, 18, 28), "card_fg": (238, 246, 255), "accent": (124, 212, 255)
    },
    "golden_morning_sunlight": {
        "tint": (248, 188, 112), "glow": (255, 232, 168), "contrast": 1.06, "sat": 1.12,
        "card_bg": (28, 22, 18), "card_fg": (255, 250, 242), "accent": (255, 196, 92)
    },
    "suburban_daylight_cel": {
        "tint": (196, 216, 238), "glow": (255, 244, 204), "contrast": 1.05, "sat": 1.06,
        "card_bg": (20, 24, 34), "card_fg": (250, 252, 255), "accent": (255, 210, 88)
    },
    "midnight_car_dashboard": {
        "tint": (64, 96, 148), "glow": (142, 214, 255), "contrast": 1.07, "sat": 0.96,
        "card_bg": (14, 20, 32), "card_fg": (240, 248, 255), "accent": (128, 212, 255)
    },
    "crimson_panic_shock": {
        "tint": (228, 72, 82), "glow": (255, 134, 102), "contrast": 1.12, "sat": 1.16,
        "card_bg": (42, 14, 18), "card_fg": (255, 244, 244), "accent": (255, 96, 102)
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
    "none", "sweat_drops", "phone_vibrate_arcs", "delivery_box_drop", "zzz_float"
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
        "layout_mode": "v12_realistic_humans_karaoke",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Relatable 2D illustrated comedy shorts starring Phil, Alan, Stu, and Doug — distinct realistic body builds, layered clothes, real facial expressions, Hangover-inspired voices, and word-by-word karaoke captions",
        "art_style": "Realistic-proportioned 2D illustrated comedy animation with distinct body builds, layered tees and hoodies, expressive eyes, smile/shock/anger acting, and word-synced karaoke captions"
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
            "Friend saying I am 5 minutes away while still at home",
            "Friend math justifying a $7 iced coffee",
            "Trying to pick one restaurant with the group chat"
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
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_hooks = {h.get("top_hook", "") for h in recent_history[-6:]}

    for _ in range(50):
        scen = random.choice(RELATABLE_SCENARIOS)
        if scen["hook"] in recent_hooks and random.random() < 0.85:
            continue

        cast_mode = random.choice(["classic_duo", "classic_duo", "trio_hangout", "full_crew_4"])
        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        art_style_key = random.choice(list(ART_STYLES.keys()))
        combo_key = f"spoken_skit|{cast_mode}|{'+'.join(characters)}|{scen['hook'][:24]}"
        if combo_key not in used_keys:
            return {
                "combo_key": combo_key,
                "reel_mode": "spoken_skit",
                "cast_mode": cast_mode,
                "characters": characters,
                "scenario": scen,
                "art_style_key": art_style_key
            }

    scen = random.choice(RELATABLE_SCENARIOS)
    return {
        "combo_key": f"spoken_{int(time.time())}",
        "reel_mode": "spoken_skit",
        "cast_mode": "classic_duo",
        "characters": ["Phil", "Stu"],
        "scenario": scen,
        "art_style_key": "reference_webcomic_2d"
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
    script_data["reel_mode"] = "spoken_skit"

    if not script_data.get("top_hook"):
        script_data["top_hook"] = scen["hook"]
    if script_data.get("environment_key") not in ENVIRONMENT_PRESETS:
        script_data["environment_key"] = scen["env"]

    default_exprs = ["skeptical_half_lid", "genuine_smile", "angry_brow", "bloodshot_shock"]
    default_actions = ["phone_call_ear", "point_argue", "temple_tap", "shrug_palms"]

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "suburban_daylight_cel"
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
            sc["sfx_cue"] = "pop_ding" if idx < 2 else ("record_scratch" if idx == 2 else "vine_boom_sub")
        if not sc.get("clock_label"):
            sc["clock_label"] = scen["clocks"][idx]

        spk = (sc.get("speaker") or "").strip()
        if spk not in chars:
            spk = chars[idx % len(chars)]
        sc["speaker"] = spk

        dlg = (sc.get("dialogue") or sc.get("bottom_caption") or "").strip()
        if not dlg:
            dlg = "Bro, you literally said five minutes twenty minutes ago."
        words = dlg.split()
        if len(words) > 15:
            dlg = " ".join(words[:14]) + "."
        sc["dialogue"] = dlg
        sc["shot_framing"] = sc.get("shot_framing") if sc.get("shot_framing") in ("two_shot", "speaker_closeup") else ("speaker_closeup" if idx in (1, 2) else "two_shot")

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

    dynamic_tags = []
    style_key = script_data.get("scenes", [{}])[0].get("art_style_key", seed["art_style_key"])
    dynamic_tags.extend(ART_STYLES.get(style_key, ART_STYLES["reference_webcomic_2d"]).get("hashtags", []))
    dynamic_tags.extend(["#comedyskit", "#voiceacting", "#friendgroup", "#wearechillclub", "#funnyreels"])

    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Tell me this isn't literally your friend group."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    chars = seed["characters"]
    c1 = chars[0]
    c2 = chars[1] if len(chars) > 1 else chars[0]
    c3 = chars[2] if len(chars) > 2 else c1
    scen = seed["scenario"]
    style_key = seed["art_style_key"]

    return {
        "reel_mode": "spoken_skit",
        "top_hook": scen["hook"],
        "environment_key": scen["env"],
        "setting_continuity": ENVIRONMENT_PRESETS[scen["env"]]["desc"],
        "music_prompt": "Light upbeat pizzicato comedy underscore instrumental",
        "music_bpm": 108,
        "scenes": [
            {
                "clock_label": scen["clocks"][0],
                "speaker": c1,
                "dialogue": "Yo, where are you? We were supposed to leave ten minutes ago.",
                "shot_framing": "two_shot",
                "bottom_caption": "",
                "expression": "skeptical_half_lid",
                "end_expression": "angry_brow",
                "body_action": "phone_call_ear",
                "prop_overlay": "none",
                "visual_prompt": f"{c1} holding phone to ear looking annoyed at {c2}, NO text",
                "art_style_key": style_key,
                "start_grade": "suburban_daylight_cel",
                "end_grade": "suburban_daylight_cel",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "none",
                "sfx_cue": "pop_ding"
            },
            {
                "clock_label": scen["clocks"][1],
                "speaker": c2,
                "dialogue": "Relax bro, I am literally turning onto your street right now!",
                "shot_framing": "speaker_closeup",
                "bottom_caption": "",
                "expression": "genuine_smile",
                "end_expression": "confident_smirk",
                "body_action": "point_argue",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Close-up of {c2} smiling confidently while clearly still inside his apartment, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_amber_desk",
                "end_grade": "warm_amber_desk",
                "camera_move": "pan_follow_right",
                "transition_in": "whip_pan_left",
                "env_effect": "none",
                "sfx_cue": "whoosh"
            },
            {
                "clock_label": scen["clocks"][2],
                "speaker": c3,
                "dialogue": "Then why do I hear your microwave beeping in the background?!",
                "shot_framing": "speaker_closeup",
                "bottom_caption": "",
                "expression": "angry_brow",
                "end_expression": "skeptical_half_lid",
                "body_action": "temple_tap",
                "prop_overlay": "none",
                "visual_prompt": f"Tight reaction shot of {c3} tapping his temple in disbelief, NO text",
                "art_style_key": style_key,
                "start_grade": "suburban_daylight_cel",
                "end_grade": "suburban_daylight_cel",
                "camera_move": "snap_zoom_face",
                "transition_in": "smash_zoom_cut",
                "env_effect": "none",
                "sfx_cue": "record_scratch"
            },
            {
                "clock_label": scen["clocks"][3],
                "speaker": c2,
                "dialogue": "That is my car pedestrian chime. See you in two!",
                "shot_framing": "two_shot",
                "bottom_caption": "",
                "expression": "sweat_grit",
                "end_expression": "bloodshot_shock",
                "body_action": "shrug_palms",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Pulled-back shot of {c2} shrugging nervously with both hands up, NO text",
                "art_style_key": style_key,
                "start_grade": "warm_amber_desk",
                "end_grade": "crimson_panic_shock",
                "camera_move": "pull_back_reveal",
                "transition_in": "whip_pan_right",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": "Tag the friend whose '5 minutes away' means they haven't even showered yet.",
        "pinned_comment": "What is the worst excuse your friend gave for being late?"
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
                        print(f"Generated voiced script with {model}")
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

    print(f"All Gemini text endpoints busy ({last_err}); using local voiced script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. VERIFIED NEURAL HUMAN VOICE SYNTHESIS + WORD-BY-WORD KARAOKE & LIP-SYNC
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
    """Extracts 24fps lip-sync visemes AND exact word-by-word timestamps directly from the spoken WAV."""
    viseme_timeline = ["closed"] * total_beat_frames
    words = [w for w in (dialogue_text or "").split() if w]
    word_timings = []

    if not wav_path or not pathlib.Path(wav_path).exists():
        return viseme_timeline, word_timings

    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    total_samples = len(raw) // (2 * n_ch)
    if total_samples <= 0:
        return viseme_timeline, word_timings

    samples = struct.unpack(f"<{total_samples * n_ch}h", raw)
    mono = samples[::n_ch]
    spf = max(1, sr // FPS)
    num_audio_frames = len(mono) // spf

    energies = []
    zcrs = []
    for f in range(num_audio_frames):
        seg = mono[f * spf:(f + 1) * spf]
        if not seg:
            energies.append(0.0)
            zcrs.append(0.0)
            continue
        rms = math.sqrt(sum(s * s for s in seg) / len(seg)) / 32768.0
        zc = sum(1 for i in range(1, len(seg)) if (seg[i - 1] < 0) != (seg[i] < 0)) / len(seg)
        energies.append(rms)
        zcrs.append(zc)

    peak = max(energies) if energies else 0.0
    if peak < 0.005:
        return viseme_timeline, word_timings

    active_audio_frames = []
    for f in range(num_audio_frames):
        vid_f = f + speech_offset_frames
        if vid_f >= total_beat_frames:
            break
        norm_e = energies[f] / peak
        if norm_e < 0.12:
            viseme_timeline[vid_f] = "closed"
        elif norm_e > 0.60 and zcrs[f] < 0.08:
            viseme_timeline[vid_f] = "o_vowel"
            active_audio_frames.append(f)
        elif zcrs[f] > 0.16 and norm_e < 0.42:
            viseme_timeline[vid_f] = "gritted_teeth"
            active_audio_frames.append(f)
        else:
            viseme_timeline[vid_f] = "open_teeth"
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

    return viseme_timeline, word_timings


def _try_gemini_tts(dialogue_text, prof, out_wav):
    """Generates expressive human speech via Gemini 2.5 Flash Preview TTS."""
    voice_name = prof.get("gemini_voice", "Fenrir")
    style_dir = prof.get("voice_style", "Expressive comedic voice")
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=){GEMINI_API_KEY}"

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
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
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
    """Generates Microsoft Neural human voices via python -m edge_tts (distinct voice, pitch & rate per character)."""
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
    """Generates distinct audible human speech for Phil, Alan, Stu, or Doug and verifies non-silent audio."""
    prof = CAST_IDENTITY.get(speaker, CAST_IDENTITY["Phil"])
    generated = False

    # Tier 1: Gemini Dedicated Neural TTS
    try:
        generated = _try_gemini_tts(dialogue_text, prof, out_wav)
        if generated:
            print(f"[VOICE OK] {speaker} -> Gemini Neural ({prof['gemini_voice']})")
    except Exception as e:
        print(f"Gemini TTS fallback for {speaker}: {e}")

    # Tier 2: Edge Neural Human Voices (en-US-GuyNeural / Christopher / Eric / Steffan)
    if not generated:
        try:
            generated = _try_edge_neural_tts(dialogue_text, prof, out_wav)
            if generated:
                print(f"[VOICE OK] {speaker} -> Edge Neural ({prof['edge_voice']})")
        except Exception as e:
            print(f"Edge Neural TTS fallback for {speaker}: {e}")

    # Tier 3: Local espeak-ng fallback
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
            if generated:
                print(f"[VOICE OK] {speaker} -> {espeak_bin}")

    if not generated:
        raise RuntimeError(f"Failed to generate audible speech for {speaker}: '{dialogue_text}'")

    # Normalize speech loudness cleanly so every speaker comes out loud and clear
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
    viseme_timelines = []
    word_timings_all = []

    for idx, sc in enumerate(scenes):
        dlg = (sc.get("dialogue") or "").strip()
        spk = (sc.get("speaker") or "Phil").strip()
        wav_path = tmp_dir / f"voice_{idx}.wav"
        speech_dur = synthesize_dialogue_beat(spk, dlg, wav_path)
        dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], speech_dur + 0.50)), 2)
        durations.append(dur)
        voice_tracks.append(wav_path)
        visemes, w_times = _analyze_wav_speech_sync(wav_path, dlg, int(dur * FPS) + 6, speech_offset_frames=3)
        viseme_timelines.append(visemes)
        word_timings_all.append(w_times)

    return durations, voice_tracks, viseme_timelines, word_timings_all


# ==============================================================================
# 5. REALISTIC HUMAN BODY PROPORTIONS, LAYERED CLOTHING & FACIAL ACTING ENGINE
# ==============================================================================
def _is_night_scene(sc):
    clk = (sc.get("clock_label") or "").upper()
    grade = sc.get("start_grade", "")
    if "dim_night" in grade or "midnight" in grade:
        return True
    if any(h in clk for h in ("22:", "23:", "00:", "01:", "02:", "03:", "04:", "10:", "11:", "12:1", "12:2", "12:3", "1:", "2:", "3:", "4:", "5:")):
        if "PM" not in clk or any(h in clk for h in ("10:", "11:")):
            return True
    return False


def _render_environment_background(env_key, sc, beat_idx, out_bg_path):
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (22, 22, 28)
    is_night = _is_night_scene(sc)
    wall_col = env.get("night_wall", env["wall"]) if is_night else env["wall"]

    img = Image.new("RGB", (W, H), color=wall_col)
    draw = ImageDraw.Draw(img)

    if env_key == "sidewalk_hangout":
        # Sky gradient + warm sunlight glow + neighborhood depth
        for y in range(0, 1080, 12):
            p = y / 1080.0
            c = tuple(int(wall_col[i] * (1.0 - p * 0.14) + 235 * p * 0.14) for i in range(3))
            draw.rectangle([0, y, W, y + 12], fill=c)
        draw.ellipse([110, 360, 270, 520], fill=(255, 240, 172))
        # Distant trees & house
        draw.ellipse([70, 660, 260, 860], fill=(78, 128, 76), outline=ink, width=4)
        draw.polygon([(160, 770), (380, 590), (600, 770)], fill=(184, 92, 72), outline=ink)
        draw.rectangle([200, 770, 560, 1080], fill=(242, 226, 192), outline=ink, width=5)
        draw.rectangle([250, 830, 340, 930], fill=(168, 210, 238), outline=ink, width=4)
        draw.rectangle([420, 890, 500, 1080], fill=(138, 86, 56), outline=ink, width=4)
        draw.rectangle([620, 850, W - 80, 1080], fill=(176, 98, 78), outline=ink, width=5)
        # Sidewalk & curb
        draw.rectangle([0, 1080, W, H], fill=env["surface"])
        draw.line([(0, 1080), (W, 1080)], fill=ink, width=7)
        for sx in range(180, W, 260):
            draw.line([(sx, 1080), (sx - 90, H)], fill=(122, 126, 134), width=4)
    elif env_key == "living_room_window":
        sky_col = (28, 42, 74) if is_night else (168, 214, 248)
        draw.rectangle([110, 360, W - 110, 960], fill=sky_col, outline=ink, width=7)
        draw.polygon([(220, 620), (540, 440), (860, 620)], fill=(196, 98, 72), outline=ink)
        draw.rectangle([260, 620, 820, 956], fill=(246, 214, 118), outline=ink, width=5)
        for b in range(min(4, beat_idx + 1)):
            bx = 520 + (b % 2) * 110
            by = 850 - (b // 2) * 95
            draw.rectangle([bx, by, bx + 115, by + 95], fill=(198, 152, 98), outline=ink, width=4)
        draw.line([(W // 2, 360), (W // 2, 960)], fill=ink, width=7)
        draw.rounded_rectangle([80, 990, W - 80, 1260], radius=34, fill=env["surface"], outline=ink, width=7)
    elif env_key == "overcast_bedroom":
        halo_col = (68, 82, 118) if is_night else (218, 224, 234)
        draw.ellipse([W // 2 - 340, 310, W // 2 + 340, 970], fill=halo_col)
        frame_bg = (196, 206, 224) if is_night else (242, 244, 248)
        for fx0 in (165, W - 395):
            fx1 = fx0 + 230
            draw.rectangle([fx0, 410, fx1, 635], fill=frame_bg, outline=ink, width=5)
            draw.polygon([(fx0 + 22, 628), (fx0 + 95, 510), (fx0 + 160, 628)], fill=(124, 138, 162), outline=ink)
            draw.polygon([(fx0 + 105, 628), (fx0 + 165, 530), (fx0 + 212, 628)], fill=(96, 110, 134), outline=ink)
            draw.ellipse([fx0 + 155, 442, fx0 + 188, 475], fill=(255, 222, 128), outline=ink, width=3)
        hb_col = (94, 82, 74) if is_night else (168, 152, 136)
        pillow_col = (176, 184, 202) if is_night else (244, 246, 250)
        draw.rounded_rectangle([110, 815, W - 110, 1140], radius=24, fill=hb_col, outline=ink, width=6)
        draw.rounded_rectangle([180, 930, 510, 1085], radius=28, fill=pillow_col, outline=ink, width=5)
        draw.rounded_rectangle([570, 930, W - 180, 1085], radius=28, fill=pillow_col, outline=ink, width=5)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([90, 380, W - 90, 980], radius=48, fill=(22, 32, 54), outline=ink, width=7)
        draw.ellipse([740, 470, 810, 540], fill=(255, 224, 148))
        draw.rounded_rectangle([240, 790, 440, 1040], radius=28, fill=(38, 44, 56), outline=ink, width=5)
        draw.rounded_rectangle([640, 790, 840, 1040], radius=28, fill=(38, 44, 56), outline=ink, width=5)
    else:
        draw.ellipse([W // 2 - 310, 340, W // 2 + 310, 960], fill=(236, 178, 112))
        draw.rectangle([160, 430, 380, 670], fill=(244, 238, 226), outline=ink, width=5)
        draw.ellipse([210, 480, 330, 600], fill=(214, 118, 76))

    # Subtle depth-of-field blur on background so foreground human characters pop with cinematic realism
    img = img.filter(ImageFilter.GaussianBlur(radius=1.6))
    img.save(out_bg_path, format="PNG")


def _draw_anatomical_arm(draw, sh, elb, hand, sleeve_col, skin_col, skin_shadow, scale, ink, short_sleeve=True):
    """Draws tapered clothed upper sleeve + realistic skin forearm + articulated hand with fingers."""
    sw_top = int(20 * scale)
    sw_elb = int(16 * scale)
    wr_r = int(12 * scale)

    # Upper arm (sleeve if short_sleeve, else full hoodie sleeve)
    arm_col = sleeve_col
    dx = elb[0] - sh[0]
    dy = elb[1] - sh[1]
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length

    upper_poly = [
        (sh[0] + nx * sw_top, sh[1] + ny * sw_top),
        (sh[0] - nx * sw_top, sh[1] - ny * sw_top),
        (elb[0] - nx * sw_elb, elb[1] - ny * sw_elb),
        (elb[0] + nx * sw_elb, elb[1] + ny * sw_elb),
    ]
    draw.polygon(upper_poly, fill=arm_col, outline=ink, width=max(3, int(4 * scale)))

    # Forearm (skin for t-shirts/polos, sleeve for hoodie)
    fore_col = skin_col if short_sleeve else sleeve_col
    dx2 = hand[0] - elb[0]
    dy2 = hand[1] - elb[1]
    len2 = max(1.0, math.hypot(dx2, dy2))
    nx2, ny2 = -dy2 / len2, dx2 / len2

    fore_poly = [
        (elb[0] + nx2 * sw_elb, elb[1] + ny2 * sw_elb),
        (elb[0] - nx2 * sw_elb, elb[1] - ny2 * sw_elb),
        (hand[0] - nx2 * wr_r, hand[1] - ny2 * wr_r),
        (hand[0] + nx2 * wr_r, hand[1] + ny2 * wr_r),
    ]
    draw.polygon(fore_poly, fill=fore_col, outline=ink, width=max(3, int(4 * scale)))
    draw.ellipse([elb[0] - sw_elb + 2, elb[1] - sw_elb + 2, elb[0] + sw_elb - 2, elb[1] + sw_elb - 2], fill=fore_col)

    # Realistic Human Hand (palm + thumb + finger contours)
    hr = int(16 * scale)
    draw.ellipse([hand[0] - hr, hand[1] - hr, hand[0] + hr, hand[1] + hr], fill=skin_col, outline=ink, width=max(3, int(4 * scale)))
    draw.ellipse([hand[0] - hr - int(5 * scale), hand[1] - int(4 * scale), hand[0] - int(3 * scale), hand[1] + int(8 * scale)], fill=skin_shadow, outline=ink, width=3)
    for f_off in (-6, 0, 6):
        fx = hand[0] + int(f_off * scale)
        draw.line([(fx, hand[1] - hr + 3), (fx, hand[1] - int(4 * scale))], fill=ink, width=2)


def _draw_sneaker(draw, fx, fy, scale, shoe_col, facing_dir=1):
    ink = (22, 22, 28)
    sw = int(52 * scale)
    sh = int(26 * scale)
    x0 = fx - int(16 * scale) if facing_dir >= 0 else fx - sw + int(16 * scale)
    x1 = x0 + sw
    y0 = fy - sh
    y1 = fy + int(7 * scale)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=int(10 * scale), fill=shoe_col, outline=ink, width=max(3, int(4 * scale)))
    # White rubber midsole
    draw.rectangle([x0 + 2, y1 - int(8 * scale), x1 - 2, y1], fill=(246, 247, 250), outline=ink, width=3)
    # Laces & toe cap
    if facing_dir >= 0:
        draw.pieslice([x1 - int(24 * scale), y0 + int(6 * scale), x1, y1 - int(5 * scale)], start=270, end=90, fill=(246, 247, 250), outline=ink, width=3)
        for lx in (x0 + int(14 * scale), x0 + int(22 * scale)):
            draw.line([(lx, y0 + 2), (lx + 4, y0 + int(10 * scale))], fill=(246, 247, 250), width=3)
    else:
        draw.pieslice([x0, y0 + int(6 * scale), x0 + int(24 * scale), y1 - int(5 * scale)], start=90, end=270, fill=(246, 247, 250), outline=ink, width=3)
        for lx in (x1 - int(14 * scale), x1 - int(22 * scale)):
            draw.line([(lx, y0 + 2), (lx - 4, y0 + int(10 * scale))], fill=(246, 247, 250), width=3)


def _draw_realistic_character(draw, name, cx, cy, base_scale, expr, body_action, viseme, t, local_p, idx_in_cast, facing_dir=1):
    """Renders realistic human proportions: distinct height & shoulder/waist build, sculpted jaw/cheekbones, layered clothing, detailed eyes, and dynamic facial acting."""
    prof = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])
    scale = base_scale * prof.get("height_scale", 1.0)
    ink = (24, 22, 28)
    skin = prof["skin_tone"]
    skin_sh = prof["skin_shadow"]
    phase = idx_in_cast * 1.15

    body_dx = 0
    body_dy = 0
    head_tilt_x = 0
    torso_lean_x = 0
    is_speaking = (viseme != "closed")

    if body_action == "sleep_breathe_toss":
        breath = math.sin(t * 2.4 + phase)
        body_dy = int(breath * 6 * scale)
        head_tilt_x = int(math.sin(t * 1.2 + phase) * 8 * scale)
    elif body_action == "phone_scroll_lean":
        torso_lean_x = int(14 * scale * facing_dir)
        head_tilt_x = int(16 * scale * facing_dir)
        body_dy = int(math.sin(t * 3.0 + phase) * 3 * scale)
    elif body_action == "shock_recoil":
        recoil = math.sin(min(1.0, local_p * 3.2) * math.pi * 0.5)
        jitter = int(math.sin(t * 48.0 + phase) * 5 * scale)
        body_dy = int(-20 * recoil * scale) + jitter
        torso_lean_x = int(-15 * recoil * scale * facing_dir)
        head_tilt_x = int(-18 * recoil * scale * facing_dir)
    elif body_action == "struggle_pull":
        tug = math.sin(t * 13.0 + phase)
        body_dx = int(tug * 14 * scale)
        body_dy = int(abs(tug) * 8 * scale)
        torso_lean_x = int(-14 * scale + tug * 10 * scale)
    elif body_action == "walk_stride":
        stride = math.sin(t * 7.5 + phase)
        body_dy = int(-abs(stride) * 14 * scale)
        torso_lean_x = int(10 * scale * facing_dir)
    elif body_action == "celebrate_groove":
        bounce = abs(math.sin(t * 7.2 + phase))
        body_dy = int(-bounce * 18 * scale)
        head_tilt_x = int(math.sin(t * 3.6 + phase) * 12 * scale)
    else:
        talk_bob = int(-6 * scale) if is_speaking else int(math.sin(t * 2.2 + phase) * 3 * scale)
        body_dy = talk_bob
        head_tilt_x = int(6 * scale * facing_dir) if is_speaking else 0

    hx = cx + body_dx + head_tilt_x
    hy = cy + body_dy
    head_w = int(78 * scale)
    head_h = int(94 * scale)

    # Realistic Neck & Collarbone Transition
    neck_x = cx + body_dx + int(torso_lean_x * 0.45)
    neck_y = hy + head_h - int(8 * scale)
    neck_w = int(28 * scale) if prof["body_type"] != "stocky" else int(34 * scale)
    sh_y = neck_y + int(32 * scale)
    hip_x = cx + body_dx
    hip_y = sh_y + int(196 * scale)

    # Anatomical Trousers / Jeans + Sneakers
    pants_c = prof["pants_color"]
    pants_sh = tuple(max(0, c - 22) for c in pants_c)
    leg_w_top = int(28 * scale) if prof["body_type"] != "stocky" else int(34 * scale)
    leg_w_bot = int(21 * scale) if prof["body_type"] != "stocky" else int(26 * scale)

    if body_action == "walk_stride":
        swing = math.sin(t * 7.5 + phase) * 48 * scale
        leg_targets = [(-1, 1.0), (1, -1.0)]
    else:
        swing = 0.0
        leg_targets = [(-1, 0.0), (1, 0.0)]

    for side, s_mult in leg_targets:
        hip_off = side * int(34 * scale)
        kx = hip_x + hip_off + int(swing * s_mult * 0.55)
        ky = hip_y + int(105 * scale)
        fx = hip_x + hip_off + int(swing * s_mult)
        fy = hip_y + int(205 * scale)

        # Thigh polygon
        draw.polygon([
            (hip_x + hip_off - leg_w_top, hip_y - 4),
            (hip_x + hip_off + leg_w_top, hip_y - 4),
            (kx + leg_w_bot + 3, ky),
            (kx - leg_w_bot - 3, ky),
        ], fill=pants_c if side == -1 else pants_sh, outline=ink, width=max(3, int(4 * scale)))
        # Calf/Shin polygon
        draw.polygon([
            (kx - leg_w_bot - 2, ky - 4),
            (kx + leg_w_bot + 2, ky - 4),
            (fx + leg_w_bot, fy),
            (fx - leg_w_bot, fy),
        ], fill=pants_c if side == -1 else pants_sh, outline=ink, width=max(3, int(4 * scale)))
        # Pant cuff fold
        draw.line([(fx - leg_w_bot, fy - int(10 * scale)), (fx + leg_w_bot, fy - int(10 * scale))], fill=ink, width=3)
        _draw_sneaker(draw, fx, fy, scale, prof["shoe_color"], facing_dir)

    # Skin Neck + Shading under Jaw
    draw.rectangle([neck_x - neck_w, neck_y - 6, neck_x + neck_w, sh_y + 10], fill=skin, outline=ink, width=max(3, int(4 * scale)))
    draw.pieslice([neck_x - neck_w, neck_y - 12, neck_x + neck_w, neck_y + int(24 * scale)], start=0, end=180, fill=skin_sh)

    # Realistic Build Torso (Athletic V-Taper, Stocky Broad, Slim, or Tall Regular)
    tw_top = int(prof["shoulder_w"] * scale)
    tw_bot = int(prof["waist_w"] * scale)
    shirt_c = prof["shirt_color"]
    shirt_shadow = tuple(max(0, c - 26) for c in shirt_c)
    shirt_highlight = tuple(min(255, c + 18) for c in shirt_c)
    outline_w = max(4, int(5 * scale))

    # Torso silhouette with natural shoulder slope
    torso_poly = [
        (neck_x - neck_w - int(8 * scale), neck_y + int(14 * scale)),
        (neck_x - tw_top, sh_y + int(8 * scale)),
        (hip_x - tw_bot, hip_y + int(12 * scale)),
        (hip_x + tw_bot, hip_y + int(12 * scale)),
        (neck_x + tw_top, sh_y + int(8 * scale)),
        (neck_x + neck_w + int(8 * scale), neck_y + int(14 * scale)),
    ]
    draw.polygon(torso_poly, fill=shirt_c)

    # Pectoral / side-torso shading for 3D volume
    draw.polygon([
        (neck_x + int(22 * scale), sh_y + int(12 * scale)),
        (neck_x + tw_top, sh_y + int(8 * scale)),
        (hip_x + tw_bot, hip_y + int(12 * scale)),
        (hip_x + int(28 * scale), hip_y + int(12 * scale)),
    ], fill=shirt_shadow)
    draw.line([(neck_x - int(32 * scale), sh_y + int(34 * scale)), (neck_x - int(18 * scale), sh_y + int(95 * scale))], fill=shirt_shadow, width=3)
    draw.line([(neck_x + int(32 * scale), sh_y + int(34 * scale)), (neck_x + int(18 * scale), sh_y + int(95 * scale))], fill=shirt_shadow, width=3)
    draw.polygon(torso_poly, outline=ink, width=outline_w)

    # Outfit-Specific Realistic Details (Layered Hoodie + Inner Tee, Polo Collar + Buttons, Ribbed Crew Tee)
    if prof["outfit"] == "layered_hoodie":
        # Hood collar behind neck
        draw.pieslice([neck_x - int(58 * scale), neck_y - int(14 * scale), neck_x + int(58 * scale), neck_y + int(42 * scale)], start=180, end=360, fill=shirt_shadow, outline=ink, width=outline_w)
        # Inner white crew t-shirt panel
        inner_c = prof["inner_tee"]
        draw.polygon([
            (neck_x - int(26 * scale), neck_y + int(14 * scale)),
            (neck_x + int(26 * scale), neck_y + int(14 * scale)),
            (hip_x + int(22 * scale), hip_y + int(12 * scale)),
            (hip_x - int(22 * scale), hip_y + int(12 * scale)),
        ], fill=inner_c, outline=ink, width=3)
        # Zipper tracks & drawstrings
        draw.line([(neck_x - int(24 * scale), neck_y + int(16 * scale)), (hip_x - int(22 * scale), hip_y + int(12 * scale))], fill=(210, 214, 222), width=4)
        draw.line([(neck_x + int(24 * scale), neck_y + int(16 * scale)), (hip_x + int(22 * scale), hip_y + int(12 * scale))], fill=(210, 214, 222), width=4)
        draw.line([(neck_x - int(18 * scale), neck_y + int(22 * scale)), (neck_x - int(20 * scale), neck_y + int(78 * scale))], fill=(250, 250, 252), width=4)
        draw.line([(neck_x + int(18 * scale), neck_y + int(22 * scale)), (neck_x + int(20 * scale), neck_y + int(78 * scale))], fill=(250, 250, 252), width=4)
    elif prof["outfit"] == "polo_shirt":
        # Polo collar + placket + 2 buttons + chest pocket
        collar_c = prof["inner_tee"]
        draw.polygon([(neck_x - int(34 * scale), neck_y + 12), (neck_x, neck_y + int(36 * scale)), (neck_x - int(12 * scale), neck_y + int(48 * scale))], fill=collar_c, outline=ink, width=3)
        draw.polygon([(neck_x + int(34 * scale), neck_y + 12), (neck_x, neck_y + int(36 * scale)), (neck_x + int(12 * scale), neck_y + int(48 * scale))], fill=collar_c, outline=ink, width=3)
        draw.rectangle([neck_x - int(8 * scale), neck_y + int(34 * scale), neck_x + int(8 * scale), neck_y + int(88 * scale)], fill=shirt_highlight, outline=ink, width=3)
        for by in (neck_y + int(50 * scale), neck_y + int(72 * scale)):
            draw.ellipse([neck_x - 3, by - 3, neck_x + 3, by + 3], fill=(245, 245, 248), outline=ink, width=2)
        draw.rectangle([neck_x + int(30 * scale), sh_y + int(36 * scale), neck_x + int(64 * scale), sh_y + int(74 * scale)], fill=shirt_shadow, outline=ink, width=3)
    else:
        # Ribbed crew-neck collar + hem stitching
        draw.arc([neck_x - int(34 * scale), neck_y + int(2 * scale), neck_x + int(34 * scale), neck_y + int(34 * scale)], start=0, end=180, fill=ink, width=max(5, int(6 * scale)))
        draw.arc([neck_x - int(34 * scale), neck_y + int(8 * scale), neck_x + int(34 * scale), neck_y + int(40 * scale)], start=0, end=180, fill=shirt_highlight, width=3)
        draw.line([(hip_x - tw_bot + 6, hip_y + int(4 * scale)), (hip_x + tw_bot - 6, hip_y + int(4 * scale))], fill=shirt_shadow, width=3)

    if prof["satchel"]:
        draw.line([(neck_x - int(48 * scale), neck_y + 14), (hip_x + int(56 * scale), hip_y + 8)], fill=(124, 78, 46), width=max(10, int(14 * scale)))
        draw.line([(neck_x - int(48 * scale), neck_y + 14), (hip_x + int(56 * scale), hip_y + 8)], fill=(164, 112, 72), width=max(3, int(4 * scale)))

    # Anatomical Arms + Sleeves + Hands
    l_sh = (neck_x - tw_top + int(10 * scale), sh_y + int(22 * scale))
    r_sh = (neck_x + tw_top - int(10 * scale), sh_y + int(22 * scale))
    holding_phone = False
    phone_pos = (0, 0)
    gesture_beat = int(math.sin(t * 10.0 + phase) * 16 * scale) if is_speaking else 0
    is_short_sleeve = (prof["outfit"] != "layered_hoodie")

    if body_action == "phone_call_ear":
        l_elb = (l_sh[0] - int(58 * scale), l_sh[1] + int(12 * scale))
        l_hand = (hx - head_w - int(10 * scale), hy + int(8 * scale))
        r_elb = (r_sh[0] + int(46 * scale), r_sh[1] + int(46 * scale))
        r_hand = (r_sh[0] + int(82 * scale), r_sh[1] + int(14 * scale) + gesture_beat)
        holding_phone = True
        phone_pos = (l_hand[0] - int(8 * scale), l_hand[1] - int(12 * scale))
    elif body_action == "point_argue":
        l_elb = (l_sh[0] - int(36 * scale), l_sh[1] + int(54 * scale))
        l_hand = (hip_x - tw_bot, hip_y - int(10 * scale))
        r_elb = (r_sh[0] + int(52 * scale), r_sh[1] + int(28 * scale))
        r_hand = (r_sh[0] + int(116 * scale * facing_dir), r_sh[1] - int(4 * scale) + gesture_beat)
    elif body_action == "shrug_palms":
        l_elb = (l_sh[0] - int(54 * scale), l_sh[1] + int(46 * scale))
        l_hand = (l_sh[0] - int(92 * scale), l_sh[1] - int(4 * scale) + gesture_beat)
        r_elb = (r_sh[0] + int(54 * scale), r_sh[1] + int(46 * scale))
        r_hand = (r_sh[0] + int(92 * scale), r_sh[1] - int(4 * scale) - gesture_beat)
    elif body_action == "count_fingers":
        l_elb = (l_sh[0] - int(34 * scale), l_sh[1] + int(56 * scale))
        l_hand = (l_sh[0] - int(22 * scale), hip_y)
        r_elb = (r_sh[0] + int(58 * scale), r_sh[1] + int(24 * scale))
        r_hand = (r_sh[0] + int(76 * scale), hy + int(46 * scale) + gesture_beat)
    elif body_action == "temple_tap":
        l_elb = (l_sh[0] - int(36 * scale), l_sh[1] + int(54 * scale))
        l_hand = (hip_x - tw_bot, hip_y - int(10 * scale))
        r_elb = (r_sh[0] + int(76 * scale), r_sh[1] - int(8 * scale))
        r_hand = (hx + head_w + int(6 * scale), hy - int(18 * scale))
    elif body_action == "phone_scroll_lean":
        l_elb = (l_sh[0] - int(34 * scale), l_sh[1] + int(52 * scale))
        l_hand = (neck_x + int(16 * scale), sh_y + int(48 * scale) + int(math.sin(t * 9.0) * 6))
        r_elb = (r_sh[0] + int(46 * scale), r_sh[1] + int(48 * scale))
        r_hand = (r_sh[0] + int(56 * scale), hy + int(54 * scale))
        holding_phone = True
        phone_pos = (r_hand[0], r_hand[1] - int(18 * scale))
    elif body_action == "shock_recoil" or expr == "bloodshot_shock":
        wave_y = int(math.sin(t * 22.0 + phase) * 8 * scale)
        l_elb = (l_sh[0] - int(68 * scale), l_sh[1] + int(22 * scale))
        l_hand = (hx - int(94 * scale), hy + int(18 * scale) + wave_y)
        r_elb = (r_sh[0] + int(68 * scale), r_sh[1] + int(22 * scale))
        r_hand = (hx + int(94 * scale), hy + int(18 * scale) - wave_y)
    else:
        l_elb = (l_sh[0] - int(34 * scale), l_sh[1] + int(58 * scale))
        l_hand = (l_sh[0] - int(26 * scale), hip_y + int(6 * scale))
        r_elb = (r_sh[0] + int(34 * scale), r_sh[1] + int(58 * scale))
        r_hand = (r_sh[0] + int(26 * scale), hip_y + int(6 * scale))

    _draw_anatomical_arm(draw, l_sh, l_elb, l_hand, shirt_c, skin, skin_sh, scale, ink, short_sleeve=is_short_sleeve)
    _draw_anatomical_arm(draw, r_sh, r_elb, r_hand, shirt_c, skin, skin_sh, scale, ink, short_sleeve=is_short_sleeve)

    if body_action == "point_argue":
        p_dir = 1 if r_hand[0] >= neck_x else -1
        draw.line([(r_hand[0], r_hand[1] - 4), (r_hand[0] + p_dir * int(22 * scale), r_hand[1] - 4)], fill=skin, width=max(7, int(9 * scale)))
        draw.line([(r_hand[0], r_hand[1] - 4), (r_hand[0] + p_dir * int(22 * scale), r_hand[1] - 4)], fill=ink, width=3)

    # Realistic Human Ears
    for side in (-1, 1):
        ear_x = hx + side * (head_w - 2)
        ear_y = hy + int(4 * scale)
        draw.ellipse([ear_x - int(12 * scale), ear_y - int(18 * scale), ear_x + int(12 * scale), ear_y + int(18 * scale)], fill=skin_sh, outline=ink, width=max(3, int(4 * scale)))

    # Sculpted Human Head & Jawline (Cranium + Cheekbones + Tapered Chin)
    jaw_w = int(head_w * 0.72) if prof["body_type"] != "stocky" else int(head_w * 0.86)
    head_poly = [
        (hx - head_w, hy - int(head_h * 0.35)),
        (hx - int(head_w * 0.92), hy - int(head_h * 0.85)),
        (hx, hy - head_h),
        (hx + int(head_w * 0.92), hy - int(head_h * 0.85)),
        (hx + head_w, hy - int(head_h * 0.35)),
        (hx + int(head_w * 0.94), hy + int(head_h * 0.25)),
        (hx + jaw_w, hy + int(head_h * 0.72)),
        (hx, hy + head_h),
        (hx - jaw_w, hy + int(head_h * 0.72)),
        (hx - int(head_w * 0.94), hy + int(head_h * 0.25)),
    ]
    draw.polygon(head_poly, fill=skin)
    # Soft facial side-plane shadow for realistic depth
    draw.polygon([
        (hx + int(head_w * 0.35), hy - int(head_h * 0.88)),
        (hx + int(head_w * 0.92), hy - int(head_h * 0.85)),
        (hx + head_w, hy - int(head_h * 0.35)),
        (hx + jaw_w, hy + int(head_h * 0.72)),
        (hx + int(head_w * 0.22), hy + int(head_h * 0.94)),
    ], fill=skin_sh)
    draw.polygon(head_poly, outline=ink, width=max(4, int(6 * scale)))

    # Hair / Beard / Snapback Cap
    hair_c = prof["hair_color"]
    if prof["hair_style"] == "curly_full":
        for bx_off, by_off, br in [(-66, -68, 28), (-36, -86, 32), (0, -92, 34), (36, -86, 32), (66, -68, 28), (-74, -36, 24), (74, -36, 24)]:
            draw.ellipse([hx + int((bx_off - br) * scale), hy + int((by_off - br) * scale), hx + int((bx_off + br) * scale), hy + int((by_off + br) * scale)], fill=hair_c, outline=ink, width=3)
    elif prof["hair_style"] == "neat_part":
        draw.pieslice([hx - head_w - 2, hy - head_h - 10, hx + head_w + 2, hy - int(head_h * 0.18)], start=180, end=360, fill=hair_c, outline=ink, width=4)
        draw.polygon([(hx - int(18 * scale), hy - head_h), (hx + int(44 * scale), hy - int(head_h * 0.56)), (hx - int(26 * scale), hy - int(head_h * 0.52))], fill=hair_c)
    else:
        draw.pieslice([hx - head_w - 2, hy - head_h - 10, hx + head_w + 2, hy - int(head_h * 0.22)], start=180, end=360, fill=hair_c, outline=ink, width=4)

    if prof["cap_color"]:
        cap_c = prof["cap_color"]
        draw.pieslice([hx - head_w - 4, hy - head_h - 14, hx + head_w + 4, hy - int(head_h * 0.24)], start=180, end=360, fill=cap_c, outline=ink, width=max(4, int(5 * scale)))
        if prof.get("backwards_cap"):
            draw.rounded_rectangle([hx - int(head_w * 1.38), hy - int(head_h * 0.56), hx + int(10 * scale), hy - int(head_h * 0.36)], radius=8, fill=cap_c, outline=ink, width=max(4, int(5 * scale)))
            draw.pieslice([hx - int(24 * scale), hy - int(head_h * 0.66), hx + int(24 * scale), hy - int(head_h * 0.36)], start=180, end=360, fill=skin, outline=ink, width=3)

    if prof["beard"]:
        draw.pieslice([hx - int(head_w * 0.88), hy + int(8 * scale), hx + int(head_w * 0.88), hy + head_h + 4], start=0, end=180, fill=(76, 52, 36), outline=ink, width=max(4, int(5 * scale)))
        # Mustache arch above mouth
        draw.arc([hx - int(36 * scale), hy + int(22 * scale), hx + int(36 * scale), hy + int(48 * scale)], start=185, end=355, fill=(76, 52, 36), width=max(8, int(11 * scale)))

    # Sculpted Nose Bridge & Tip
    nose_y = hy + int(10 * scale)
    draw.line([(hx - int(3 * scale), hy - int(12 * scale)), (hx - int(6 * scale), nose_y), (hx + int(6 * scale), nose_y + int(4 * scale))], fill=ink, width=max(3, int(4 * scale)))

    # Realistic Human Eyes (Almond Sclera + Colored Iris + Pupil + Catchlight + Eyelids)
    eye_dx = int(31 * scale)
    eye_y = hy - int(14 * scale)
    er_x = int(19 * scale)
    er_y = int(14 * scale) if expr not in ("bloodshot_shock", "maniacal_3am_grin") else int(19 * scale)
    is_blinking = ((t + idx_in_cast * 0.9) % 3.4) < 0.11
    pupil_look_x = int(5 * scale * facing_dir) if (is_speaking or holding_phone) else int(math.sin(t * 1.4 + phase) * 3 * scale)
    iris_col = (78, 108, 134) if name in ("Phil", "Stu") else (96, 74, 54)

    if is_blinking and expr not in ("bloodshot_shock", "sweat_grit", "maniacal_3am_grin"):
        draw.line([(hx - eye_dx - er_x + 3, eye_y), (hx - eye_dx + er_x - 3, eye_y)], fill=ink, width=max(4, int(5 * scale)))
        draw.line([(hx + eye_dx - er_x + 3, eye_y), (hx + eye_dx + er_x - 3, eye_y)], fill=ink, width=max(4, int(5 * scale)))
    elif expr in ("smug_snooze", "genuine_smile"):
        # Happy / smug curved eyes + cheek lift
        if expr == "genuine_smile":
            for side in (-1, 1):
                ex = hx + side * eye_dx
                draw.arc([ex - er_x, eye_y - 10, ex + er_x, eye_y + 12], start=190, end=350, fill=ink, width=max(4, int(5 * scale)))
                draw.arc([ex - er_x - 4, eye_y + 8, ex + er_x + 4, eye_y + 22], start=10, end=170, fill=skin_sh, width=3)
        else:
            draw.arc([hx - eye_dx - er_x, eye_y - 8, hx - eye_dx + er_x, eye_y + 14], start=10, end=170, fill=ink, width=max(4, int(5 * scale)))
            draw.arc([hx + eye_dx - er_x, eye_y - 8, hx + eye_dx + er_x, eye_y + 14], start=10, end=170, fill=ink, width=max(4, int(5 * scale)))
    elif expr == "sweat_grit":
        draw.line([(hx - eye_dx - 14, eye_y - 10), (hx - eye_dx + 10, eye_y), (hx - eye_dx - 14, eye_y + 10)], fill=ink, width=4)
        draw.line([(hx + eye_dx + 14, eye_y - 10), (hx + eye_dx - 10, eye_y), (hx + eye_dx + 14, eye_y + 10)], fill=ink, width=4)
    else:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - er_x, eye_y - er_y, ex + er_x, eye_y + er_y], fill=(252, 253, 255), outline=ink, width=max(3, int(4 * scale)))
            if expr == "bloodshot_shock":
                draw.line([(ex - er_x + 3, eye_y - 4), (ex - 7, eye_y - 1)], fill=(224, 52, 62), width=2)
                draw.line([(ex + er_x - 3, eye_y + 5), (ex + 7, eye_y + 2)], fill=(224, 52, 62), width=2)
            ir_r = int(8 * scale) if expr == "bloodshot_shock" else int(10 * scale)
            pr = int(4 * scale) if expr == "bloodshot_shock" else int(5 * scale)
            px_c = ex + pupil_look_x
            draw.ellipse([px_c - ir_r, eye_y - ir_r, px_c + ir_r, eye_y + ir_r], fill=iris_col)
            draw.ellipse([px_c - pr, eye_y - pr, px_c + pr, eye_y + pr], fill=ink)
            draw.ellipse([px_c - pr + 1, eye_y - pr + 1, px_c - pr + 5, eye_y - pr + 5], fill=(255, 255, 255))

            if expr in ("skeptical_half_lid", "exhausted_half_lidded", "tired_bags"):
                draw.pieslice([ex - er_x, eye_y - er_y, ex + er_x, eye_y + er_y], start=180, end=360, fill=skin, outline=ink, width=max(3, int(4 * scale)))
            if expr == "tired_bags":
                draw.arc([ex - er_x + 2, eye_y + int(7 * scale), ex + er_x - 2, eye_y + er_y + int(10 * scale)], start=15, end=165, fill=skin_sh, width=3)

    # Expressive Eyebrows + Forehead Creases
    brow_y = eye_y - er_y - int(8 * scale)
    brow_w = max(5, int(6 * scale))
    if expr == "angry_brow":
        draw.line([(hx - eye_dx - 16, brow_y - 6), (hx - eye_dx + 14, brow_y + 8)], fill=hair_c, width=brow_w)
        draw.line([(hx + eye_dx + 16, brow_y - 6), (hx + eye_dx - 14, brow_y + 8)], fill=hair_c, width=brow_w)
        draw.line([(hx - 5, brow_y + 2), (hx - 5, brow_y + 12)], fill=ink, width=2)
        draw.line([(hx + 5, brow_y + 2), (hx + 5, brow_y + 12)], fill=ink, width=2)
    elif expr in ("guilty_puppy_eyes", "tired_bags"):
        draw.line([(hx - eye_dx - 16, brow_y + 6), (hx - eye_dx + 14, brow_y - 6)], fill=hair_c, width=brow_w)
        draw.line([(hx + eye_dx + 16, brow_y + 6), (hx + eye_dx - 14, brow_y - 6)], fill=hair_c, width=brow_w)
    elif expr in ("bloodshot_shock", "maniacal_3am_grin"):
        draw.arc([hx - eye_dx - 16, brow_y - 14, hx - eye_dx + 16, brow_y + 4], start=190, end=350, fill=hair_c, width=brow_w)
        draw.arc([hx + eye_dx - 16, brow_y - 14, hx + eye_dx + 16, brow_y + 4], start=190, end=350, fill=hair_c, width=brow_w)
        draw.line([(hx - 24, brow_y - 18), (hx + 24, brow_y - 18)], fill=skin_sh, width=2)
    else:
        draw.line([(hx - eye_dx - 16, brow_y), (hx - eye_dx + 16, brow_y)], fill=hair_c, width=brow_w)
        draw.line([(hx + eye_dx - 16, brow_y), (hx + eye_dx + 16, brow_y)], fill=hair_c, width=brow_w)

    # 4-Shape Lip-Sync Mouth Rig + Smile/Shock/Anger Expressions
    my = hy + int(38 * scale)
    effective_viseme = "gritted_teeth" if expr == "sweat_grit" else viseme

    if effective_viseme == "open_teeth":
        mw, mh = int(26 * scale), int(22 * scale)
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, fill=(76, 26, 34), outline=ink, width=max(3, int(4 * scale)))
        draw.rectangle([hx - mw + 5, my, hx + mw - 5, my + int(7 * scale)], fill=(252, 252, 255))
        draw.pieslice([hx - int(13 * scale), my + int(7 * scale), hx + int(13 * scale), my + mh - 2], start=0, end=180, fill=(232, 118, 134))
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, outline=ink, width=max(3, int(4 * scale)))
    elif effective_viseme == "o_vowel":
        ow, oh = int(16 * scale), int(20 * scale)
        draw.ellipse([hx - ow, my - int(4 * scale), hx + ow, my + oh], fill=(76, 26, 34), outline=ink, width=max(3, int(4 * scale)))
    elif effective_viseme == "gritted_teeth":
        mx0, my0 = hx - int(24 * scale), my - int(5 * scale)
        mx1, my1 = hx + int(24 * scale), my + int(14 * scale)
        draw.rounded_rectangle([mx0, my0, mx1, my1], radius=7, fill=(252, 252, 255), outline=ink, width=3)
        for tx in range(mx0 + 10, mx1 - 5, 12):
            draw.line([(tx, my0), (tx, my1)], fill=ink, width=2)
    elif expr in ("genuine_smile", "maniacal_3am_grin"):
        mw, mh = int(30 * scale), int(22 * scale)
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, fill=(252, 252, 255), outline=ink, width=max(3, int(4 * scale)))
        draw.line([(hx - mw + 5, my + int(8 * scale)), (hx + mw - 5, my + int(8 * scale))], fill=ink, width=2)
    elif expr == "bloodshot_shock":
        jaw_open = int((28 + math.sin(t * 24.0) * 5) * scale)
        draw.rounded_rectangle([hx - int(19 * scale), my - int(6 * scale), hx + int(19 * scale), my + jaw_open], radius=9, fill=(76, 26, 34), outline=ink, width=4)
    elif expr in ("smug_snooze", "confident_smirk"):
        draw.arc([hx - int(18 * scale), my - int(8 * scale), hx + int(22 * scale), my + int(10 * scale)], start=12, end=165, fill=ink, width=max(3, int(5 * scale)))
    elif expr in ("angry_brow", "guilty_puppy_eyes"):
        draw.arc([hx - int(18 * scale), my + int(2 * scale), hx + int(18 * scale), my + int(16 * scale)], start=190, end=350, fill=ink, width=max(3, int(5 * scale)))
    else:
        draw.line([(hx - int(18 * scale), my + int(4 * scale)), (hx + int(18 * scale), my + int(2 * scale))], fill=ink, width=max(3, int(5 * scale)))

    if prof["glasses"]:
        gr = int(24 * scale)
        draw.rounded_rectangle([hx - eye_dx - gr, eye_y - int(gr * 0.85), hx - eye_dx + gr, eye_y + int(gr * 0.85)], radius=6, outline=ink, width=max(4, int(5 * scale)))
        draw.rounded_rectangle([hx + eye_dx - gr, eye_y - int(gr * 0.85), hx + eye_dx + gr, eye_y + int(gr * 0.85)], radius=6, outline=ink, width=max(4, int(5 * scale)))
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=max(4, int(5 * scale)))

    if holding_phone:
        px, py = phone_pos
        pw, ph = int(24 * scale), int(44 * scale)
        draw.rounded_rectangle([px - pw, py - ph, px + pw, py + ph], radius=9, fill=(26, 30, 40), outline=ink, width=4)
        if body_action == "phone_scroll_lean":
            draw.rounded_rectangle([px - pw + 4, py - ph + 7, px + pw - 4, py + ph - 7], radius=5, fill=(142, 224, 255))


def _draw_foreground_occlusion(draw, env_key, sc):
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (22, 22, 28)
    is_night = _is_night_scene(sc)

    if env_key == "overcast_bedroom":
        blanket_col = (74, 86, 112) if is_night else env["surface"]
        sheet_col = (196, 204, 220) if is_night else (244, 246, 250)
        draw.rounded_rectangle([70, 1085, W - 70, 1580], radius=34, fill=blanket_col, outline=ink, width=7)
        draw.rounded_rectangle([70, 1085, W - 70, 1138], radius=18, fill=sheet_col, outline=ink, width=6)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([60, 1095, W - 60, 1580], radius=42, fill=env["surface"], outline=ink, width=7)
        draw.ellipse([235, 1035, 475, 1275], outline=(12, 14, 18), width=16)
    elif env_key == "living_room_window":
        draw.rounded_rectangle([80, 1145, W - 80, 1520], radius=34, fill=env["surface"], outline=ink, width=7)
    elif env_key in ("warm_desk_lamp", "kitchen_counter"):
        draw.rectangle([0, 1130, W, H], fill=env["surface"])
        draw.line([(0, 1130), (W, 1130)], fill=ink, width=7)
        draw.polygon([(130, 1015), (230, 1015), (212, 1130), (148, 1130)], fill=(178, 92, 64), outline=ink)
        draw.ellipse([125, 915, 235, 1025], fill=(76, 142, 82), outline=ink, width=4)
        draw.rounded_rectangle([835, 1050, 915, 1130], radius=12, fill=env["accent_prop"], outline=ink, width=4)


def render_animated_stage_frame(bg_img, characters, env_key, sc, reel_mode, beat_idx, t, local_p, active_viseme):
    frame = bg_img.copy()
    draw = ImageDraw.Draw(frame)

    expr = sc.get("expression", "skeptical_half_lid") if local_p < 0.45 else sc.get("end_expression", sc.get("expression", "skeptical_half_lid"))
    body_action = sc.get("body_action", "point_argue")
    speaker = (sc.get("speaker") or "").strip()
    framing = sc.get("shot_framing", "two_shot")
    count = max(1, min(4, len(characters)))

    if framing == "speaker_closeup" and speaker in characters:
        f_dir = 1 if characters.index(speaker) % 2 == 0 else -1
        _draw_realistic_character(draw, speaker, W // 2, 795, 1.24, expr, body_action, active_viseme, t, local_p, characters.index(speaker), facing_dir=f_dir)
    else:
        spacing = min(285, (W - 140) // count)
        start_x = (W // 2) - ((count - 1) * spacing) // 2
        scale = 1.04 if count == 1 else (0.95 if count == 2 else (0.82 if count == 3 else 0.72))
        for idx, name in enumerate(characters[:4]):
            cx = start_x + idx * spacing
            cy = 775 if env_key == "sidewalk_hangout" else (805 + (idx % 2) * 14)
            is_active_spk = (name == speaker)
            char_expr = expr if is_active_spk else "skeptical_half_lid"
            char_act = body_action if is_active_spk else ("slouch_sigh" if body_action != "walk_stride" else "walk_stride")
            char_vis = active_viseme if is_active_spk else "closed"
            f_dir = 1 if idx == 0 else -1
            _draw_realistic_character(draw, name, cx, cy, scale, char_expr, char_act, char_vis, t, local_p, idx, facing_dir=f_dir)

    if env_key != "sidewalk_hangout" and body_action != "walk_stride":
        _draw_foreground_occlusion(draw, env_key, sc)

    return frame


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
    if cue == "alarm_buzz":
        pulse = 1.0 if (int(dt * 14) % 2 == 0) else 0.15
        env = math.exp(-dt * 3.0) * pulse
        return (math.sin(2 * math.pi * 880.0 * dt) + 0.5 * math.sin(2 * math.pi * 1320.0 * dt)) * env * 0.16
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
        print(f"Lyria skipped ({e}), generating subtle background underscore...")
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

    # Mix voice at full presence while ducking background music cleanly
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
# 7. CAMERA MOVEMENTS, MICRO-ANIMATED PROPS & WORD-BY-WORD KARAOKE CAPTIONS
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


def generate_particle_seeds(count=24):
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

    active_expr = sc.get("expression", "") if local_p < 0.45 else sc.get("end_expression", sc.get("expression", ""))
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
            for sx, base_y in [(390, 740), (690, 760)]:
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
        elif env_fx == "dust":
            for p in particle_seeds:
                depth = p["depth"]
                spd = p["speed"] * (0.6 + 0.5 * depth)
                p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
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


def draw_karaoke_speech_overlays(frame, top_hook, sc, word_timings, scene_t, t, handle):
    """Renders upper hook + speaker badge + word-by-word karaoke pop-in captions synced to the voice."""
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

    # 2. Speaker Name Tag + Word-by-Word Karaoke Subtitles Synced to Voice Timestamps
    spk = (sc.get("speaker") or "Phil").strip()
    spk_col = CAST_IDENTITY.get(spk, CAST_IDENTITY["Phil"])["shirt_color"]
    cap_in = _ease_out_quart(min(1.0, scene_t / 0.14))
    cap_alpha = int(252 * cap_in)

    tag_font = _load_font(28)
    tag_text = f"● {spk.upper()}"
    tbbox = odraw.textbbox((0, 0), tag_text, font=tag_font)
    tw = (tbbox[2] - tbbox[0]) + 44
    th = 42
    tx0 = 104
    ty0 = 1316
    odraw.rounded_rectangle([tx0, ty0, tx0 + tw, ty0 + th], radius=16, fill=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), outline=(18, 18, 22, cap_alpha), width=4)
    odraw.text((tx0 + tw // 2, ty0 + th // 2), tag_text, font=tag_font, fill=(255, 255, 255, cap_alpha), anchor="mm")

    dlg_font = _load_font(42)
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

    line_h = 62
    box_h = max(96, 36 + len(rows) * line_h)
    x0, y0 = 92, 1364
    x1, y1 = W - 92, y0 + box_h
    odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(16, 18, 26, min(244, cap_alpha)), outline=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), width=4)

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
                    [rx - 8, ry - word_h // 2 - 8, rx + word_w + 8, ry + word_h // 2 + 10],
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

    # 3. Handle Watermark in Instagram Safe Zone
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
    reel_mode = "spoken_skit"
    env_key = script_data.get("environment_key", seed["scenario"]["env"])

    bg_imgs = []
    for idx, sc in enumerate(scenes):
        bg_path = tmp_dir / f"bg_{idx}.png"
        _render_environment_background(env_key, sc, idx, bg_path)
        bg_imgs.append(Image.open(bg_path).convert("RGB"))

    beat_durations, voice_tracks, viseme_timelines, word_timings_all = compute_beat_durations_and_voices(scenes, tmp_dir)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t
    print(f"Rendered voiced timing ({total_dur:.2f}s total): {beat_durations}")

    final_wav = tmp_dir / "final_director.wav"
    build_director_audio(
        script_data.get("music_prompt", "playful lo-fi indie comedy loop instrumental"),
        script_data.get("music_bpm", 106),
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
    particle_seeds = generate_particle_seeds(24)
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
        local_f = int(scene_t * FPS)
        v_list = viseme_timelines[s_idx]
        active_viseme = v_list[local_f] if local_f < len(v_list) else "closed"

        raw_stage = render_animated_stage_frame(
            bg_imgs[s_idx], characters, env_key, sc, reel_mode, s_idx, t, local_p, active_viseme
        )

        if s_idx > 0 and sc.get("transition_in") == "freeze_record_scratch" and scene_t < 0.42 and prev_rendered_frame is not None:
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

        frame = draw_karaoke_speech_overlays(
            frame=frame,
            top_hook=top_hook,
            sc=sc,
            word_timings=word_timings_all[s_idx],
            scene_t=scene_t,
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
    print(f"Rendered Realistic Voiced Karaoke Reel ({total_dur:.1f}s, {total_beats} beats): {out_mp4}")


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
        time_slot_vibe = "MORNING SLOT: Snoozing alarms, friend coffee math, or morning lateness excuses."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT: Trying to save money at home, delivery boxes piling up, or friend lunch loans."
    else:
        time_slot_vibe = "EVENING/NIGHT SLOT: 'I'm 5 minutes away' phone calls, picking a dinner spot, or scrolling in bed until 03:00."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('top_hook', '')}" for h in recent_history if h.get("top_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history)
        scen = seed["scenario"]
        cast_descriptions = "\n".join(
            f"- {c}: {CAST_IDENTITY[c]['archetype']} | Voice Tone: {CAST_IDENTITY[c]['voice_style']}"
            for c in seed["characters"]
        )

        prompt = (
            f"You are a 2D Comedy Animation Director for {page['handle']}.\n"
            f"CHANNEL IDENTITY: {page['domain']}\n\n"
            "### MANDATORY CREATIVE DIRECTION BRIEF\n"
            f"- Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Characters (NEVER CHANGE NAMES — MATCH EACH CHARACTER'S PERSONALITY & VOICE TONE):\n{cast_descriptions}\n"
            f"- Upper-Third Hook Concept: {scen['hook']}\n"
            f"- Story Seed: {scen['story_seed']}\n"
            f"- Environment Key: {scen['env']} ({ENVIRONMENT_PRESETS[scen['env']]['desc']})\n"
            f"- Suggested Ticking Clock Progression: {scen['clocks']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only if natural): \n{trends}\n"
            f"- Previously Used Hooks (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### VOICED DIALOGUE & SHOT-REVERSE-SHOT RULES\n"
            "1. EVERY SINGLE BEAT MUST BE SPOKEN OUT LOUD: Assign 'speaker' to one of the active characters (rotate speakers across the 4 beats!) and write punchy, natural spoken 'dialogue' (7 to 13 words max per beat) matching their Hangover-style personality.\n"
            "2. SHOT-REVERSE-SHOT FRAMING: Alternate 'shot_framing' between 'two_shot' and 'speaker_closeup' so the camera cuts between friends talking.\n"
            "3. CONVERSATIONAL GESTURES: Use 'phone_call_ear', 'point_argue', 'shrug_palms', 'count_fingers', and 'temple_tap' in 'body_action'.\n"
            "4. REAL FACIAL ACTING: Use 'skeptical_half_lid', 'genuine_smile', 'angry_brow', 'confident_smirk', 'sweat_grit', and 'bloodshot_shock'.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "reel_mode": "spoken_skit",\n'
            f'  "top_hook": "{scen["hook"]}",\n'
            f'  "environment_key": "{scen["env"]}",\n'
            f'  "setting_continuity": "{ENVIRONMENT_PRESETS[scen["env"]]["desc"]}",\n'
            '  "music_prompt": "Light upbeat pizzicato comedy underscore instrumental",\n'
            '  "music_bpm": 106,\n'
            '  "scenes": [\n'
            f'    {{"clock_label": "{scen["clocks"][0]}", "speaker": "{seed["characters"][0]}", "dialogue": "Yo where are you, we were supposed to leave ten minutes ago.", "shot_framing": "two_shot", "bottom_caption": "", "expression": "skeptical_half_lid", "end_expression": "angry_brow", "body_action": "phone_call_ear", "prop_overlay": "none", "visual_prompt": "Beat 1 action, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "suburban_daylight_cel", "end_grade": "suburban_daylight_cel", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "none", "sfx_cue": "pop_ding"}},\n'
            f'    {{"clock_label": "{scen["clocks"][1]}", "speaker": "{seed["characters"][-1]}", "dialogue": "Relax bro I am literally turning onto your street right now!", "shot_framing": "speaker_closeup", "bottom_caption": "", "expression": "genuine_smile", "end_expression": "confident_smirk", "body_action": "point_argue", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 2 action, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "warm_amber_desk", "end_grade": "warm_amber_desk", "camera_move": "pan_follow_right", "transition_in": "whip_pan_left", "env_effect": "none", "sfx_cue": "whoosh"}},\n'
            f'    {{"clock_label": "{scen["clocks"][2]}", "speaker": "{seed["characters"][0]}", "dialogue": "Then why do I hear your microwave beeping in the background?!", "shot_framing": "speaker_closeup", "bottom_caption": "", "expression": "angry_brow", "end_expression": "skeptical_half_lid", "body_action": "temple_tap", "prop_overlay": "none", "visual_prompt": "Beat 3 tight reaction, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "suburban_daylight_cel", "end_grade": "suburban_daylight_cel", "camera_move": "snap_zoom_face", "transition_in": "smash_zoom_cut", "env_effect": "none", "sfx_cue": "record_scratch"}},\n'
            f'    {{"clock_label": "{scen["clocks"][3]}", "speaker": "{seed["characters"][-1]}", "dialogue": "That is my car pedestrian chime. See you in two!", "shot_framing": "two_shot", "bottom_caption": "", "expression": "sweat_grit", "end_expression": "bloodshot_shock", "body_action": "shrug_palms", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 4 comedic reveal, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "warm_amber_desk", "end_grade": "crimson_panic_shock", "camera_move": "pull_back_reveal", "transition_in": "whip_pan_right", "env_effect": "none", "sfx_cue": "vine_boom_sub"}}\n'
            "  ],\n"
            '  "ig_caption": "Punchy relatable caption inviting followers to tag a friend",\n'
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
            f"Beat {i+1} [{s.get('clock_label', '')}] ({s.get('speaker', 'Phil')} | {s.get('body_action', '')}): {s.get('dialogue', '')}"
            for i, s in enumerate(script_data["scenes"][:4])
        )
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Mode: spoken_skit\nCast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nEnvironment: {script_data.get('environment_key', '')}\nHook: {script_data.get('top_hook', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "reel_mode": "spoken_skit",
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
