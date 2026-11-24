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
# CREATIVE DIRECTOR & RENDER TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.24,      # 0.0 to 0.50: cinematic edge depth
    "color_tint_strength": 0.14,    # 0.0 to 0.28: mood color grading wash
    "ambient_glow_strength": 0.16,  # 0.0 to 0.35: directional warm/cool rim glow
    "particle_opacity": 0.36,       # 0.0 to 0.70: atmospheric particles
    "max_zoom_delta": 0.11,         # Keeps character framing safe from over-cropping
    "transition_sec": 0.28,         # Duration of transitions between acts
    "enable_blur_transition": True  # Fast downsampled Gaussian blur cross-dissolve
}

# ==============================================================================
# 1. THE @WEARECHILLCLUB 4-CHARACTER ROSTER (HANGOVER-INSPIRED ARCHETYPES)
# ==============================================================================
CAST_PROFILES = {
    "Phil": {
        "role": "The Confident Instigator ('Trust me, it will take 10 minutes')",
        "visual": "Phil (minimalist white round head, muted-olive baseball cap, dark charcoal hoodie, sunglasses hooked on hoodie collar, confident smirk)",
        "cap_color": (92, 112, 78),
        "shirt_color": (44, 48, 60),
        "has_beard": False,
        "has_glasses": False
    },
    "Alan": {
        "role": "The Unfiltered Wildcard / Chaos Goblin (2:30 AM conspiracy theorist & accidental genius)",
        "visual": "Alan (minimalist white round head, messy brown beard, oversized retro graphic t-shirt with crossbody satchel bag, wide deadpan eyes)",
        "cap_color": None,
        "shirt_color": (122, 84, 58),
        "has_beard": True,
        "has_glasses": False
    },
    "Stu": {
        "role": "The Anxious Overthinker / Spreadsheet Worrier (checks bank balance 6x a day, sweats over 4:58 PM emails)",
        "visual": "Stu (minimalist white round head, thick black-rimmed glasses, neat navy cardigan over collared shirt, nervous expression)",
        "cap_color": None,
        "shirt_color": (48, 66, 96),
        "has_beard": False,
        "has_glasses": True
    },
    "Doug": {
        "role": "The Chill Grounded One / Missing-In-Action Legend (calm voice of reason who casually disappears during chaos)",
        "visual": "Doug (minimalist white round head, casual open plaid flannel shirt over white tee, calm half-lidded chill expression)",
        "cap_color": None,
        "shirt_color": (138, 56, 56),
        "has_beard": False,
        "has_glasses": False
    }
}

CAST_MODES = {
    "solo_spotlight": {
        "desc": "1 main character alone in their element",
        "lineups": [["Phil"], ["Alan"], ["Stu"], ["Doug"]]
    },
    "classic_duo": {
        "desc": "2 contrasting characters bouncing off each other",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Alan", "Stu"],
            ["Phil", "Alan"],
            ["Stu", "Doug"]
        ]
    },
    "trio_chaos": {
        "desc": "3 characters caught in escalating chaos or searching for Doug",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_club_4": {
        "desc": "All 4 members (Phil, Alan, Stu, and Doug) together for a celebration, trip, or disaster",
        "lineups": [["Phil", "Alan", "Stu", "Doug"]]
    }
}

# ==============================================================================
# 2. STORY-MOTIVATED ART STYLES & MOVIE PARODY LIBRARY
# ==============================================================================
ART_STYLES = {
    "clean_webcomic": {
        "prompt": "Clean vector-neat 2D webcomic illustration, uniform crisp black ink outlines, expressive marker shading, clean uncluttered framing",
        "overlay_fx": "none",
        "hashtags": ["#webcomic", "#2danimation", "#comicstrip"]
    },
    "manga_impact": {
        "prompt": "High-contrast anime and manga-inspired 2D illustration, dramatic ink hatching, dynamic perspective, expressive anime reaction faces",
        "overlay_fx": "speed_lines",
        "hashtags": ["#animememes", "#mangastyle", "#2danimation"]
    },
    "noir_monochrome": {
        "prompt": "High-contrast black-and-white film noir detective graphic novel illustration, dramatic Venetian blind shadows, moody rain lighting",
        "overlay_fx": "film_grain",
        "hashtags": ["#filmnoir", "#overthinking", "#animatedstory"]
    },
    "retro_vhs_90s": {
        "prompt": "Nostalgic 1990s/2017 retro home-video aesthetic 2D cartoon illustration, warm analog colors, throwback bedroom or arcade vibe",
        "overlay_fx": "vhs",
        "hashtags": ["#90snostalgia", "#vhsaesthetic", "#throwbackvibes"]
    },
    "cyberpunk_neon": {
        "prompt": "Vibrant cyberpunk night 2D illustration, deep midnight indigo sky, glowing electric magenta and cyan neon signs, rain-slicked reflections",
        "overlay_fx": "neon_scan",
        "hashtags": ["#cyberpunkvibes", "#nightdrive", "#neonlights"]
    },
    "comic_book_pop": {
        "prompt": "Bold classic comic-book pop-art illustration, saturated primary colors, dynamic action angles, dramatic rim highlights",
        "overlay_fx": "halftone",
        "hashtags": ["#comicart", "#popart", "#funnyreels"]
    },
    "sketch_rough": {
        "prompt": "Expressive hand-drawn graphite and ink sketchbook animation style on textured off-white paper, raw energetic linework",
        "overlay_fx": "paper_grain",
        "hashtags": ["#sketchbook", "#handdrawnanimation", "#relatableart"]
    },
    "cinematic_painterly": {
        "prompt": "Rich atmospheric 2D animated film background with expressive webcomic characters, dramatic golden-hour or storm lighting, deep perspective",
        "overlay_fx": "none",
        "hashtags": ["#indieanimation", "#storytelling", "#cinematicreels"]
    }
}

MOVIE_PARODIES = [
    "The Hangover Parody (waking up after a wild night with a mysterious receipt, missing Doug, and zero memory of what happened)",
    "Interstellar Time-Dilation Parody (waiting 45 seconds for a microwave meal or watching 4:58 PM Friday feel like 7 years on a water planet)",
    "The Office Mockumentary Parody (one character says something unhinged while another stares deadpan straight into the camera)",
    "Fast & Furious Errand Parody (driving a 2010 Corolla to get $5 tacos or groceries like a high-stakes street heist for 'family')",
    "Mission Impossible Stealth Parody (trying to sneak into the kitchen at 2:47 AM or close 47 Chrome tabs without making a sound)",
    "John Wick Revenge Parody (calmly gearing up in sweatpants to avenge a stolen leftover slice of pizza in the fridge)",
    "Inception Dream-Within-a-Dream Parody (hitting snooze for '5 more minutes' at 7:00 AM and living three entire lifetimes before 7:09 AM)",
    "None — Pure Slice-of-Life Comedy (original everyday friendship, celebration, travel, music hype, or workplace chaos)"
]

STORY_SCENARIOS = [
    "Friday Night Road Trip Gone Sideways (Phil insists he knows a 'shortcut' with 4% battery and no signal)",
    "The $14.82 Payday Countdown (Stu guarding the group budget while Alan orders $38 of impulse snacks)",
    "Morning After Mystery (Phil, Alan, and Stu piecing together last night's receipts while Doug casually walks in with coffee)",
    "Kitchen & Living-Room Concert Break (Alan puts on an absolute banger while cooking and turns the apartment into a rock arena)",
    "6:15 AM Sunrise Trail Hike (Phil promised an 'easy 15-minute walk' that turned into a vertical mountain climb)",
    "Golden-Hour Sunset Highway Drive (windows down, favorite song blasting, zero stress, pure main-character freedom)",
    "The 4:58 PM Friday Slack Ping (Stu panicking over a last-minute message while Phil already closed his laptop)",
    "The 2:47 AM Deep Conversation (Alan asking an unhinged philosophical question while Stu is trying to sleep)",
    "Celebration Night Win (the whole crew hyping each other up over a small victory like they just won the championship)",
    "Grocery Store One-Item Mission (walking in for milk and coming out with a cart full of nonsense)"
]

# ==============================================================================
# 3. 14-GRADE COLOR & WITHIN-SCENE PROGRESSION ENGINE
# ==============================================================================
COLOR_GRADES = {
    "golden_hour": {
        "tint": (245, 148, 78), "glow": (255, 204, 115), "contrast": 1.06, "sat": 1.12,
        "card_bg": (34, 20, 22), "card_fg": (255, 246, 236), "accent": (255, 168, 86)
    },
    "neon_cyber": {
        "tint": (175, 78, 245), "glow": (95, 238, 255), "contrast": 1.12, "sat": 1.24,
        "card_bg": (18, 14, 38), "card_fg": (242, 248, 255), "accent": (110, 238, 255)
    },
    "crimson_panic": {
        "tint": (236, 68, 78), "glow": (255, 128, 92), "contrast": 1.10, "sat": 1.16,
        "card_bg": (52, 14, 20), "card_fg": (255, 242, 242), "accent": (255, 92, 98)
    },
    "noir_bw": {
        "tint": (135, 138, 145), "glow": (235, 238, 245), "contrast": 1.22, "sat": 0.08,
        "card_bg": (16, 17, 20), "card_fg": (248, 248, 250), "accent": (255, 215, 95)
    },
    "cold_cyan_night": {
        "tint": (82, 145, 215), "glow": (145, 218, 255), "contrast": 1.07, "sat": 1.02,
        "card_bg": (15, 24, 42), "card_fg": (236, 246, 255), "accent": (132, 212, 255)
    },
    "acid_absurd": {
        "tint": (145, 235, 82), "glow": (225, 255, 110), "contrast": 1.10, "sat": 1.25,
        "card_bg": (22, 36, 18), "card_fg": (246, 255, 238), "accent": (175, 250, 95)
    },
    "vintage_vhs": {
        "tint": (215, 175, 135), "glow": (255, 215, 165), "contrast": 0.96, "sat": 0.85,
        "card_bg": (34, 28, 26), "card_fg": (252, 244, 232), "accent": (255, 192, 118)
    },
    "comic_vibrant": {
        "tint": (255, 198, 72), "glow": (110, 210, 255), "contrast": 1.14, "sat": 1.26,
        "card_bg": (24, 22, 36), "card_fg": (255, 252, 240), "accent": (255, 214, 68)
    },
    "pastel_soft": {
        "tint": (242, 195, 215), "glow": (255, 232, 210), "contrast": 0.98, "sat": 0.95,
        "card_bg": (34, 28, 38), "card_fg": (255, 248, 252), "accent": (255, 192, 214)
    },
    "desaturated_gloom": {
        "tint": (118, 128, 142), "glow": (175, 188, 205), "contrast": 1.05, "sat": 0.45,
        "card_bg": (22, 25, 32), "card_fg": (232, 236, 242), "accent": (168, 186, 212)
    },
    "warm_sunrise": {
        "tint": (255, 176, 132), "glow": (255, 228, 168), "contrast": 1.05, "sat": 1.10,
        "card_bg": (34, 24, 28), "card_fg": (255, 248, 242), "accent": (255, 188, 128)
    },
    "forest_fresh": {
        "tint": (108, 195, 142), "glow": (225, 250, 198), "contrast": 1.06, "sat": 1.12,
        "card_bg": (18, 34, 26), "card_fg": (242, 252, 245), "accent": (122, 226, 154)
    },
    "purple_surreal": {
        "tint": (165, 98, 225), "glow": (225, 155, 255), "contrast": 1.09, "sat": 1.18,
        "card_bg": (28, 18, 44), "card_fg": (248, 240, 255), "accent": (212, 142, 255)
    },
    "invert_flash": {
        "tint": (255, 255, 255), "glow": (255, 85, 95), "contrast": 1.25, "sat": 1.30,
        "card_bg": (12, 12, 16), "card_fg": (255, 255, 255), "accent": (255, 85, 95)
    }
}

ALL_TRANSITIONS = [
    "hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right",
    "flash_white", "flash_crimson", "rgb_glitch", "blur_dissolve",
    "light_sweep", "freeze_record_scratch"
]

ALL_CAMERA_MOVES = [
    "dolly_push_in", "pull_back_reveal", "snap_zoom_face", "dutch_tilt_tension",
    "handheld_chaos", "locked_deadpan", "crane_tilt_up", "pan_follow_left",
    "pan_follow_right", "heartbeat_pulse"
]

ALL_CAPTION_STYLES = [
    "modern_card", "karaoke_pop", "meme_impact_top",
    "typewriter_terminal", "comic_callout", "cinematic_minimal"
]

ALL_ENV_EFFECTS = [
    "none", "rain", "snow", "sparks", "confetti", "dust", "lightning", "screen_glow"
]

ALL_SFX_CUES = [
    "whoosh", "record_scratch", "vine_boom_sub", "glitch_zap", "pop_ding", "riser_hit"
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
        "layout_mode": "v6_creative_director",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Multi-genre 2D webcomic storytelling & comedy starring the @wearechillclub crew: Phil, Alan, Stu, and Doug (Hangover-inspired comedic archetypes across solo, duo, trio, and full-crew adventures, celebrations, road trips, movie parodies, hype music breaks, and everyday chaos)",
        "art_style": "Clean vector-neat 2D webcomic storytelling illustration with minimalist white round-headed characters, crisp uniform black ink outlines, expressive faces, and dynamic poses"
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
            "Friday night group chat plans falling apart",
            "Golden hour sunset highway drives",
            "Waking up on Saturday thinking you missed work"
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
    """Weighted variety sampler ensuring consecutive Reels differ in cast, art style, scenario, and parody."""
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_styles = [h.get("art_style_key", "") for h in recent_history[-3:]]
    recent_casts = [h.get("cast_mode", "") for h in recent_history[-2:]]

    for _ in range(35):
        cast_mode = random.choice(list(CAST_MODES.keys()))
        if cast_mode in recent_casts and random.random() < 0.75:
            continue
        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        art_style_key = random.choice(list(ART_STYLES.keys()))
        if art_style_key in recent_styles and random.random() < 0.80:
            continue
        scenario = random.choice(STORY_SCENARIOS)
        parody = random.choice(MOVIE_PARODIES)
        caption_style = random.choice(ALL_CAPTION_STYLES)
        combo_key = f"{cast_mode}|{'+'.join(characters)}|{art_style_key}|{scenario[:22]}"
        if combo_key not in used_keys:
            return {
                "combo_key": combo_key,
                "cast_mode": cast_mode,
                "characters": characters,
                "art_style_key": art_style_key,
                "scenario": scenario,
                "movie_parody": parody,
                "caption_style": caption_style
            }

    cast_mode = random.choice(list(CAST_MODES.keys()))
    return {
        "combo_key": f"cd_{int(time.time())}",
        "cast_mode": cast_mode,
        "characters": random.choice(CAST_MODES[cast_mode]["lineups"]),
        "art_style_key": random.choice(list(ART_STYLES.keys())),
        "scenario": random.choice(STORY_SCENARIOS),
        "movie_parody": random.choice(MOVIE_PARODIES),
        "caption_style": random.choice(ALL_CAPTION_STYLES)
    }


def validate_and_fix_plan(script_data, seed):
    """Pre-render Quality Control Gate: enforces valid enums, non-repeating transitions/cameras, and clean text."""
    if not isinstance(script_data, dict):
        return _build_local_fallback_script(seed)

    scenes = script_data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 3:
        return _build_local_fallback_script(seed)

    scenes = scenes[:3]
    used_cams = set()
    used_trans = set()

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "comic_vibrant" if idx == 0 else ("crimson_panic" if idx == 1 else "golden_hour")
        if sc.get("end_grade") not in COLOR_GRADES:
            sc["end_grade"] = sc["start_grade"]
        if sc.get("art_style_key") not in ART_STYLES:
            sc["art_style_key"] = seed["art_style_key"]
        if sc.get("env_effect") not in ALL_ENV_EFFECTS:
            sc["env_effect"] = "none"
        if sc.get("sfx_cue") not in ALL_SFX_CUES:
            sc["sfx_cue"] = "pop_ding" if idx == 1 else "vine_boom_sub"

        cam = sc.get("camera_move")
        if cam not in ALL_CAMERA_MOVES or cam in used_cams:
            avail_cams = [c for c in ALL_CAMERA_MOVES if c not in used_cams]
            cam = random.choice(avail_cams)
        sc["camera_move"] = cam
        used_cams.add(cam)

        tr = sc.get("transition_in")
        if tr not in ALL_TRANSITIONS or tr in used_trans:
            avail_tr = [t for t in ALL_TRANSITIONS if t not in used_trans]
            tr = random.choice(avail_tr)
        sc["transition_in"] = tr
        used_trans.add(tr)

        cap = (sc.get("story_caption") or "").strip()
        words = cap.split()
        if len(words) > 22:
            sc["story_caption"] = " ".join(words[:21]) + "..."
        elif not cap:
            sc["story_caption"] = f"Act {idx + 1}: Things escalate fast for {', '.join(seed['characters'])}."

    if script_data.get("caption_style") not in ALL_CAPTION_STYLES:
        script_data["caption_style"] = seed["caption_style"]

    script_data["scenes"] = scenes
    return script_data


def build_smart_hashtags(raw_caption, script_data, seed):
    """Generates 6-7 clean, non-duplicate hashtags matched to cast, movie parody, style, and mood."""
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
    dynamic_tags.extend(ART_STYLES.get(style_key, ART_STYLES["clean_webcomic"]).get("hashtags", []))

    chars = seed.get("characters", [])
    if len(chars) >= 3:
        dynamic_tags.extend(["#friendgroup", "#squadgoals", "#hangovervibes"])
    elif len(chars) == 2:
        dynamic_tags.extend(["#bestfriends", "#duocomedy"])
    else:
        dynamic_tags.extend(["#sololife", "#introvertmemes"])

    parody = seed.get("movie_parody", "")
    if "Hangover" in parody:
        dynamic_tags.append("#thehangover")
    elif "Office" in parody:
        dynamic_tags.append("#theofficehumor")
    elif "Interstellar" in parody:
        dynamic_tags.append("#moviereference")

    dynamic_tags.extend(["#wearechillclub", "#funnyreels", "#animatedcomedy"])

    merged = []
    for tag in existing_tags + dynamic_tags:
        clean_tag = "#" + "".join(ch for ch in tag if ch.isalnum())
        if len(clean_tag) > 2 and clean_tag not in merged:
            merged.append(clean_tag)
        if len(merged) >= 7:
            break

    body_str = "\n".join(text_body).strip() or "Just another totally normal day with the club."
    return f"{body_str}\n\n{' '.join(merged)}"


def _build_local_fallback_script(seed):
    """Zero-dependency Creative Director fallback script if all Gemini endpoints return 503/429 simultaneously."""
    chars = seed["characters"]
    char_str = ", ".join(chars)
    scenario_title = seed["scenario"].split("(")[0].strip()
    style_key = seed["art_style_key"]

    return {
        "chapter_tag": f"{scenario_title.upper()[:24]}",
        "caption_style": seed["caption_style"],
        "music_prompt": "Upbeat comedic indie groove with bassline and crisp drums instrumental",
        "music_bpm": 116,
        "scenes": [
            {
                "story_caption": f"Phil said {scenario_title.lower()} would take ten minutes—{char_str} actually believed him.",
                "emotion_cue": "EASY WIN.",
                "visual_prompt": f"Starting pose: {char_str} confidently starting {scenario_title}, mid-scene animated gestures and smiling, ending confident pose, NO text in drawing",
                "art_style_key": style_key,
                "start_grade": "comic_vibrant",
                "end_grade": "golden_hour",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "dust",
                "sfx_cue": "pop_ding"
            },
            {
                "story_caption": "Three minutes later everything went completely off the rails and nobody had a backup plan.",
                "emotion_cue": "ABORT!",
                "visual_prompt": f"Mid-action chaos: {char_str} reacting in total shock and panic as things go wrong, dramatic exaggerated poses, NO text in drawing",
                "art_style_key": "manga_impact" if style_key != "manga_impact" else style_key,
                "start_grade": "desaturated_gloom",
                "end_grade": "crimson_panic",
                "camera_move": "dutch_tilt_tension",
                "transition_in": "whip_pan_left",
                "env_effect": "sparks",
                "sfx_cue": "record_scratch"
            },
            {
                "story_caption": "Somehow we survived with zero dignity left and immediately agreed to do it again next week.",
                "emotion_cue": "CLASSIC.",
                "visual_prompt": f"Ending payoff pose: {char_str} exhausted yet laughing together in deadpan acceptance, NO text in drawing",
                "art_style_key": style_key,
                "start_grade": "cold_cyan_night",
                "end_grade": "golden_hour",
                "camera_move": "pull_back_reveal",
                "transition_in": "freeze_record_scratch",
                "env_effect": "confetti" if len(chars) >= 3 else "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": f"Never trust Phil when he says 'it will only take 10 minutes.' ({char_str})",
        "pinned_comment": "Which member of the club are you in your friend group: Phil, Alan, Stu, or Doug?"
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
                    "temperature": 0.95,
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
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(raw_text, strict=False)
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 3:
                        print(f"Generated Creative Director script with {model}")
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

    print(f"All Gemini text endpoints busy ({last_err}); using Creative Director local seed script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. MULTI-CHARACTER ILLUSTRATION GENERATOR & EXPRESSIVE CAST FALLBACK
# ==============================================================================
def _render_multi_character_fallback(characters, start_grade, act_idx, out_png_path):
    """Renders 1 to 4 distinct named characters (Phil, Alan, Stu, Doug) with expressive poses if image API throttles."""
    g = COLOR_GRADES.get(start_grade, COLOR_GRADES["comic_vibrant"])
    bg = tuple(max(18, min(220, int(c * 0.45))) for c in g["tint"])
    floor = tuple(max(12, int(c * 0.65)) for c in bg)
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Dynamic background geometry (city skyline / room / horizon)
    draw.ellipse([W // 2 - 220, 460, W // 2 + 220, 900], fill=g["glow"])
    draw.rectangle([0, 1180, W, H], fill=floor)
    draw.line([(0, 1180), (W, 1180)], fill=(12, 12, 16), width=8)

    count = max(1, min(4, len(characters)))
    spacing = min(230, (W - 180) // count)
    start_x = (W // 2) - ((count - 1) * spacing) // 2
    scale = 1.0 if count <= 2 else (0.85 if count == 3 else 0.76)

    for idx, name in enumerate(characters[:4]):
        prof = CAST_PROFILES.get(name, CAST_PROFILES["Phil"])
        cx = start_x + idx * spacing
        cy = 960 + (idx % 2) * 18
        r_head = int(96 * scale)
        body_w = int(84 * scale)
        body_h = int(250 * scale)

        # Torso & dynamic arm pose per act
        draw.rounded_rectangle(
            [cx - body_w, cy + r_head - 12, cx + body_w, cy + r_head + body_h],
            radius=int(38 * scale),
            fill=prof["shirt_color"],
            outline=(12, 12, 16),
            width=max(6, int(9 * scale))
        )
        if act_idx == 1 or name == "Alan":
            draw.line([(cx - body_w + 8, cy + r_head + 30), (cx - body_w - int(55 * scale), cy + r_head - int(55 * scale))], fill=prof["shirt_color"], width=max(14, int(22 * scale)))
            draw.line([(cx + body_w - 8, cy + r_head + 30), (cx + body_w + int(55 * scale), cy + r_head - int(55 * scale))], fill=prof["shirt_color"], width=max(14, int(22 * scale)))

        # Minimalist white round head
        draw.ellipse(
            [cx - r_head, cy - r_head, cx + r_head, cy + r_head],
            fill=(252, 252, 255),
            outline=(12, 12, 16),
            width=max(7, int(10 * scale))
        )

        # Signature character details: Phil's olive cap, Alan's beard, Stu's glasses
        if prof["cap_color"]:
            draw.pieslice([cx - r_head - 2, cy - r_head - 14, cx + r_head + 2, cy - 8], start=180, end=360, fill=prof["cap_color"], outline=(12, 12, 16), width=max(6, int(8 * scale)))
            draw.rounded_rectangle([cx - 6, cy - int(r_head * 0.56), cx + int(r_head * 1.32), cy - int(r_head * 0.36)], radius=8, fill=prof["cap_color"], outline=(12, 12, 16), width=6)

        if prof["has_beard"]:
            draw.pieslice([cx - int(r_head * 0.85), cy - 4, cx + int(r_head * 0.85), cy + r_head + 4], start=0, end=180, fill=(88, 60, 42), outline=(12, 12, 16), width=6)

        eye_dx = int(34 * scale)
        eye_y = cy - int(16 * scale)
        eye_r = max(7, int((13 if act_idx == 1 else 10) * scale))
        draw.ellipse([cx - eye_dx - eye_r, eye_y - eye_r, cx - eye_dx + eye_r, eye_y + eye_r], fill=(12, 12, 16))
        draw.ellipse([cx + eye_dx - eye_r, eye_y - eye_r, cx + eye_dx + eye_r, eye_y + eye_r], fill=(12, 12, 16))

        if prof["has_glasses"]:
            gr = int(24 * scale)
            draw.rectangle([cx - eye_dx - gr, eye_y - gr, cx - eye_dx + gr, eye_y + gr], outline=(12, 12, 16), width=max(4, int(6 * scale)))
            draw.rectangle([cx + eye_dx - gr, eye_y - gr, cx + eye_dx + gr, eye_y + gr], outline=(12, 12, 16), width=max(4, int(6 * scale)))
            draw.line([(cx - eye_dx + gr, eye_y), (cx + eye_dx - gr, eye_y)], fill=(12, 12, 16), width=max(4, int(6 * scale)))

        # Expressive mouth per act
        my = cy + int(28 * scale)
        if act_idx == 0:
            draw.arc([cx - int(22 * scale), my - 10, cx + int(22 * scale), my + 16], start=10, end=170, fill=(12, 12, 16), width=5)
        elif act_idx == 1:
            draw.ellipse([cx - int(14 * scale), my - 10, cx + int(14 * scale), my + 18], outline=(12, 12, 16), width=5)
        else:
            draw.line([(cx - int(22 * scale), my + 4), (cx + int(22 * scale), my + 4)], fill=(12, 12, 16), width=6)

    img.save(out_png_path, format="PNG")


def generate_scene_illustration(scene_data, characters, act_idx, out_png_path):
    style_key = scene_data.get("art_style_key", "clean_webcomic")
    style_desc = ART_STYLES.get(style_key, ART_STYLES["clean_webcomic"])["prompt"]
    cast_desc = "; ".join(CAST_PROFILES[c]["visual"] for c in characters if c in CAST_PROFILES)
    grade_name = scene_data.get("start_grade", "comic_vibrant")

    full_prompt = (
        f"{style_desc}. Characters in scene ({len(characters)} total): {cast_desc}. "
        f"Act {act_idx + 1} Action & Story Beat: {scene_data['visual_prompt']}. "
        f"Color & Lighting Atmosphere: {grade_name.replace('_', ' ')}. "
        "Keep every character's face, wardrobe, and head shape 100% consistent. Vertical 9:16 portrait composition, "
        "frame characters clearly in the center zone with clean unobstructed space at top 20% and bottom 28% for captions, "
        "strictly NO text, NO letters, NO speech bubbles inside the artwork."
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
                print(f"Generated Act {act_idx + 1} artwork via {imagen_model} ({style_key}, cast={characters})")
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
                        print(f"Generated Act {act_idx + 1} artwork via {img_model} ({style_key}, cast={characters})")
                        return
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")[:180]
            print(f"{img_model} HTTP {e.code}: {err_msg}")
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    print(f"Using multi-character vector fallback for Act {act_idx + 1} (cast={characters})")
    _render_multi_character_fallback(characters, grade_name, act_idx, out_png_path)


# ==============================================================================
# 5. LYRIA MUSIC + MULTI-CUE AUDIO-REACTIVE SFX SYNTHESIZER
# ==============================================================================
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
        "-af", f"volume=0.86,afade=t=in:st=0:d=0.30,afade=t=out:st={max(0.5, duration_sec - 0.8):.3f}:d=0.8",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.28) * math.pi)
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * env * 0.28
    if cue == "record_scratch":
        env = math.exp(-dt * 6.5)
        freq = 680.0 * math.exp(-dt * 5.5) + 90.0 * math.sin(dt * 95.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.42
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.8)
        freq = 78.0 * math.exp(-dt * 1.8)
        return math.sin(2 * math.pi * freq * dt) * env * 0.52
    if cue == "glitch_zap":
        env = math.exp(-dt * 11.0)
        sq = 1.0 if math.sin(2 * math.pi * (340 + 900 * dt) * dt) >= 0 else -1.0
        return sq * env * 0.24
    if cue == "riser_hit":
        if dt < 0.35:
            return math.sin(2 * math.pi * (220 + 1400 * dt) * dt) * (dt / 0.35) * 0.30
        env = math.exp(-(dt - 0.35) * 8.0)
        return math.sin(2 * math.pi * 65.0 * dt) * env * 0.48
    # Default pop_ding
    env = math.exp(-dt * 16.0)
    return math.sin(2 * math.pi * 987.77 * dt) * env * 0.28


def build_director_audio(music_prompt, bpm, scenes, act_starts, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating groove synth bed...")
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
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.09
                s = int(max(-0.9, min(0.9, val)) * 32767)
                frames.extend(struct.pack("<hh", s, s))
            wf.writeframes(frames)

    sfx_wav = final_wav.parent / "director_sfx.wav"
    sr = 48000
    total_samples = int(sr * duration_sec)
    cues = [
        (0.15, scenes[0].get("sfx_cue", "pop_ding")),
        (act_starts[1], scenes[1].get("sfx_cue", "record_scratch")),
        (act_starts[2], scenes[2].get("sfx_cue", "vine_boom_sub"))
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
                if start_t <= t <= start_t + 0.60:
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
# 6. EASING, WITHIN-SCENE COLOR PROGRESSION, CAMERA, TRANSITIONS & OVERLAYS
# ==============================================================================
def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _lerp_color(c1, c2, p):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(3))


def build_vignette_mask(strength=0.24):
    small_w, small_h = 270, 480
    vig = Image.new("L", (small_w, small_h), 0)
    px = vig.load()
    cx, cy = small_w / 2.0, small_h * 0.50
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_d
            px[x, y] = int(max(0.0, min(255.0, (d ** 2.3) * 255.0 * strength)))
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def build_ambient_glow_mask(strength=0.16):
    small_w, small_h = 270, 480
    mask = Image.new("L", (small_w, small_h), 0)
    px = mask.load()
    lx, ly = small_w * 0.74, small_h * 0.24
    max_d = math.hypot(small_w, small_h) * 0.78
    for y in range(small_h):
        for x in range(small_w):
            d = min(1.0, math.hypot(x - lx, y - ly) / max_d)
            px[x, y] = int(max(0.0, min(255.0, pow(1.0 - d, 2.0) * 255.0 * strength)))
    return mask.resize((W, H), Image.Resampling.BILINEAR)


def generate_particle_seeds(count=32):
    rng = random.Random(42)
    colors = [(255, 215, 90), (235, 120, 255), (110, 238, 255), (135, 235, 165)]
    return [
        {
            "x": rng.uniform(0.03, 0.97),
            "y": rng.uniform(0.04, 0.96),
            "depth": rng.uniform(0.45, 1.0),
            "speed": rng.uniform(0.65, 1.35),
            "size": rng.randint(2, 5),
            "phase": rng.uniform(0, math.pi * 2),
            "col": rng.choice(colors)
        }
        for _ in range(count)
    ]


def apply_progressive_grade_and_fx(frame, sc, local_p, t, vignette_mask, glow_mask, particle_seeds):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "comic_vibrant"), COLOR_GRADES["comic_vibrant"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "comic_vibrant"), g1)
    prog = _ease_in_out_sine(local_p)

    # Brief color-invert punch on invert_flash grade
    if sc.get("end_grade") == "invert_flash" and 0.35 <= local_p <= 0.52:
        from PIL import ImageOps
        frame = ImageOps.invert(frame)

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

    # Style-specific procedural overlays (speed-lines, VHS scanlines, etc.) & environmental effects
    style_fx = ART_STYLES.get(sc.get("art_style_key", "clean_webcomic"), {}).get("overlay_fx", "none")
    env_fx = sc.get("env_effect", "none")

    if style_fx != "none" or env_fx != "none":
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if style_fx == "speed_lines":
            for i in range(28):
                ang = (i / 28.0) * math.pi * 2 + (t * 0.4)
                r0 = 430 + int(math.sin(t * 18.0 + i) * 35)
                r1 = 1080
                x0, y0 = int(W // 2 + math.cos(ang) * r0), int(H // 2 + math.sin(ang) * r0)
                x1, y1 = int(W // 2 + math.cos(ang) * r1), int(H // 2 + math.sin(ang) * r1)
                odraw.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 68), width=3)
        elif style_fx == "vhs":
            offset_y = int((t * 48) % 16)
            for y in range(offset_y, H, 16):
                odraw.line([(0, y), (W, y)], fill=(255, 255, 255, 22), width=2)
            odraw.text((92, 118), "PLAY  1998-09-08", font=_load_font(26), fill=(255, 255, 255, 145))

        base_alpha = 255 * VISUAL_TUNING["particle_opacity"]
        if env_fx == "lightning" and (int(t * 24) % 34 in (0, 2)):
            odraw.rectangle([0, 0, W, H], fill=(235, 245, 255, 95))
        elif env_fx == "screen_glow":
            pulse = int(35 + 22 * math.sin(t * 5.5))
            odraw.ellipse([W // 2 - 260, 720, W // 2 + 260, 1260], fill=(135, 215, 255, pulse))
        elif env_fx in ("rain", "snow", "sparks", "confetti", "dust"):
            for p in particle_seeds:
                depth = p["depth"]
                spd = p["speed"] * (0.6 + 0.5 * depth)
                p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
                if env_fx == "rain":
                    px = int(((p["x"] - t * 0.08 * spd) % 1.0) * W)
                    py = int(((p["y"] + t * 0.58 * spd) % 1.0) * H)
                    odraw.line([(px, py), (px - 7, py + 28)], fill=(195, 225, 255, int(p_alpha * 0.78)), width=2)
                elif env_fx == "snow":
                    px = int(((p["x"] + math.sin(t * 1.5 + p["phase"]) * 0.03) % 1.0) * W)
                    py = int(((p["y"] + t * 0.14 * spd) % 1.0) * H)
                    r = max(3, int((p["size"] + 1) * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(248, 252, 255, int(p_alpha * 0.8)))
                elif env_fx == "sparks":
                    px = int(((p["x"] + math.sin(t * 5.5 + p["phase"]) * 0.04) % 1.0) * W)
                    py = int(((p["y"] - t * 0.26 * spd) % 1.0) * H)
                    r = max(2, int((p["size"] + 1) * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.8)))
                elif env_fx == "confetti":
                    px = int(((p["x"] + math.sin(t * 2.4 + p["phase"]) * 0.04) % 1.0) * W)
                    py = int(((p["y"] + t * 0.16 * spd) % 1.0) * H)
                    r = max(4, int((p["size"] + 2) * depth))
                    c = p["col"]
                    odraw.rounded_rectangle([px - r, py - r // 2, px + r, py + r // 2], radius=2, fill=(c[0], c[1], c[2], int(p_alpha * 0.82)))
                elif env_fx == "dust":
                    px = int(((p["x"] + math.sin(t * 1.2 + p["phase"]) * 0.025) % 1.0) * W)
                    py = int(((p["y"] - t * 0.035 * spd) % 1.0) * H)
                    r = max(2, int(p["size"] * depth))
                    odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(p_alpha * 0.58)))

        graded = Image.alpha_composite(graded.convert("RGBA"), overlay).convert("RGB")

    return graded


def apply_camera_trajectory(base_img, move, local_p, scene_t, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    idle_breath = math.sin(t * 2.2) * 0.003

    if move == "pull_back_reveal":
        zoom = (1.0 + max_z) - (max_z * _ease_out_quart(local_p)) + idle_breath
    elif move == "snap_zoom_face":
        if local_p < 0.09:
            zoom = 1.0 + (max_z * 1.22) * _ease_out_quart(local_p / 0.09)
        else:
            zoom = (1.0 + max_z * 1.22) - (max_z * 0.25 * _ease_in_out_sine((local_p - 0.09) / 0.91))
    elif move == "heartbeat_pulse":
        pulse = pow(max(0.0, math.sin(t * 6.5)), 6) * 0.035
        zoom = 1.03 + pulse
    elif move == "locked_deadpan":
        zoom = 1.02
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
    elif move == "handheld_chaos":
        x0 = max(0, min(max_dx, (max_dx // 2) + int(math.sin(t * 17.0) * min(16, max_dx // 2))))
        y0 = max(0, min(max_dy, (max_dy // 2) + int(math.cos(t * 14.0) * min(14, max_dy // 2))))
    else:
        x0 = max_dx // 2
        y0 = max_dy // 2

    frame = base_img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)

    if move == "dutch_tilt_tension":
        angle = math.sin(_ease_in_out_sine(local_p) * math.pi) * 2.8
        rotated = frame.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)
        # Slight 1.06x crop to hide rotation corners cleanly
        m_w, m_h = int(W * 0.045), int(H * 0.045)
        frame = rotated.crop((m_w, m_h, W - m_w, H - m_h)).resize((W, H), Image.Resampling.BILINEAR)

    return frame


def apply_director_transition(prev_frame, curr_frame, transition_name, tr_p):
    eased = _ease_out_quart(tr_p)

    if transition_name == "hard_cut":
        return curr_frame

    if transition_name == "smash_zoom_cut":
        scale = 1.16 - 0.16 * eased
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

    if transition_name in ("flash_white", "flash_crimson"):
        flash_col = (255, 255, 255) if transition_name == "flash_white" else (245, 55, 70)
        blended = Image.blend(prev_frame, curr_frame, min(1.0, eased * 1.4))
        return Image.blend(blended, Image.new("RGB", (W, H), flash_col), (1.0 - tr_p) * 0.42)

    if transition_name == "rgb_glitch":
        r, g, b = curr_frame.split()
        shift = int((1.0 - tr_p) * 28 * math.sin(tr_p * 28.0))
        r = ImageChops.offset(r, shift, 0) if "ImageChops" in globals() else r
        return Image.merge("RGB", (r, g, b))

    if transition_name == "light_sweep":
        blended = Image.blend(prev_frame, curr_frame, eased)
        sweep = math.sin(tr_p * math.pi) * 0.24
        return Image.blend(blended, Image.new("RGB", (W, H), (255, 224, 155)), sweep)

    if transition_name == "blur_dissolve" and VISUAL_TUNING.get("enable_blur_transition", True):
        blended = Image.blend(prev_frame, curr_frame, _ease_in_out_sine(tr_p))
        blur_r = math.sin(tr_p * math.pi) * 4.5
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


def draw_director_overlays(frame, chapter_tag, caption_style, sc, act_idx, scene_t, act_dur, t, handle):
    g1 = COLOR_GRADES.get(sc.get("start_grade", "comic_vibrant"), COLOR_GRADES["comic_vibrant"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "comic_vibrant"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, act_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg = g2["card_bg"]
    c_fg = g2["card_fg"]

    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 1. Top Chapter / Cast Tag
    if chapter_tag:
        ent = _ease_out_quart(min(1.0, t / 0.28))
        tag_font = _load_font(32)
        tag_str = f"ACT {act_idx + 1}/3  ·  {chapter_tag.strip().upper()}"
        bbox = odraw.textbbox((0, 0), tag_str, font=tag_font)
        tw = (bbox[2] - bbox[0]) + 56
        th = 58
        bx0 = (W - tw) // 2
        by0 = 180 + int((1.0 - ent) * -14)
        alpha = int(242 * ent)
        odraw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + th], radius=29, fill=(16, 18, 26, alpha), outline=(acc[0], acc[1], acc[2], alpha), width=3)
        odraw.text((W // 2, by0 + th // 2), tag_str, font=tag_font, fill=(acc[0], acc[1], acc[2], 255), anchor="mm")

    # 2. Emotion Cue Callout
    emotion_cue = sc.get("emotion_cue", "")
    if emotion_cue and scene_t <= 1.70:
        pop_p = min(1.0, scene_t / 0.14)
        fade_out = 1.0 if scene_t < 1.30 else max(0.0, 1.0 - (scene_t - 1.30) / 0.40)
        cue_scale = 1.16 - (0.16 * _ease_out_quart(pop_p))
        cue_alpha = int(255 * min(1.0, scene_t / 0.08) * fade_out)
        cue_font = _load_font(int(50 * cue_scale))
        odraw.text(
            (W // 2, 318),
            emotion_cue.strip().upper(),
            font=cue_font,
            fill=(acc[0], acc[1], acc[2], cue_alpha),
            anchor="mm",
            stroke_width=8,
            stroke_fill=(12, 12, 16, cue_alpha)
        )

    # 3. 6-Style Story Caption Engine
    story_caption = (sc.get("story_caption") or "").strip()
    if story_caption:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.22))
        time_left = max(0.0, act_dur - scene_t)
        cap_out = 1.0 if (act_idx == 2 or time_left > 0.16) else max(0.0, time_left / 0.16)
        vis = cap_in * cap_out
        cap_alpha = int(248 * vis)

        if caption_style == "typewriter_terminal":
            char_count = max(1, int(len(story_caption) * min(1.0, scene_t / (act_dur * 0.58))))
            display_text = story_caption[:char_count]
        elif caption_style == "karaoke_pop":
            words = story_caption.split()
            active_idx = min(len(words) - 1, int(prog * len(words)))
            words[active_idx] = words[active_idx].upper()
            display_text = " ".join(words)
        else:
            display_text = story_caption

        wrapped = textwrap.fill(display_text, width=33)
        lines = wrapped.split("\n")

        if caption_style == "meme_impact_top":
            meme_font = _load_font(44)
            odraw.multiline_text((W // 2, 395), wrapped.upper(), font=meme_font, fill=(255, 255, 255, cap_alpha), anchor="mm", align="center", spacing=10, stroke_width=7, stroke_fill=(10, 10, 14, cap_alpha))
        elif caption_style == "cinematic_minimal":
            sub_font = _load_font(42)
            odraw.multiline_text((W // 2, 1410), wrapped, font=sub_font, fill=(255, 252, 245, cap_alpha), anchor="mm", align="center", spacing=12, stroke_width=6, stroke_fill=(10, 12, 18, cap_alpha))
        elif caption_style == "comic_callout":
            cap_font = _load_font(40)
            box_h = 48 + len(lines) * 50
            x0, y0 = 74, 1335 + int((1.0 - cap_in) * 14)
            x1, y1 = W - 74, y0 + box_h
            odraw.rounded_rectangle([x0 + 8, y0 + 8, x1 + 8, y1 + 8], radius=18, fill=(10, 10, 14, cap_alpha))
            odraw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=(255, 252, 240, cap_alpha), outline=(12, 12, 16, cap_alpha), width=5)
            odraw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=cap_font, fill=(14, 16, 22, cap_alpha), anchor="mm", align="center", spacing=10)
        else:
            # modern_card / karaoke_pop / typewriter_terminal card
            cap_font = _load_font(40)
            box_h = 50 + len(lines) * 52
            x0, y0 = 66, 1335 + int((1.0 - cap_in) * 14)
            x1, y1 = W - 66, y0 + box_h
            odraw.rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 10], radius=26, fill=(6, 8, 12, int(cap_alpha * 0.55)))
            odraw.rounded_rectangle([x0, y0, x1, y1], radius=26, fill=(c_bg[0], c_bg[1], c_bg[2], cap_alpha), outline=(acc[0], acc[1], acc[2], int(cap_alpha * 0.85)), width=3)
            odraw.rounded_rectangle([x0 + 14, y0 + 20, x0 + 22, y1 - 20], radius=4, fill=(acc[0], acc[1], acc[2], cap_alpha))
            odraw.multiline_text((W // 2 + 8, (y0 + y1) // 2), wrapped, font=cap_font, fill=(c_fg[0], c_fg[1], c_fg[2], cap_alpha), anchor="mm", align="center", spacing=11)

    # 4. Handle Watermark
    handle_font = _load_font(28)
    odraw.text((W // 2, 1625), handle, font=handle_font, fill=(255, 255, 255, 222), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 210))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_director_reel(page_cfg, script_data, seed, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:3]
    characters = seed["characters"]
    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        generate_scene_illustration(sc, characters, idx, art_path)
        scene_imgs.append(Image.open(art_path).convert("RGB"))

    act_durations = [3.5, 4.0, 3.5]
    act_starts = [0.0, 3.5, 7.5]
    total_dur = sum(act_durations)

    final_wav = tmp_dir / "final_director.wav"
    build_director_audio(
        script_data.get("music_prompt", "upbeat comedic indie groove instrumental"),
        script_data.get("music_bpm", 114),
        scenes,
        act_starts,
        total_dur,
        final_wav
    )

    total_frames = int(total_dur * FPS)
    chapter_tag = script_data.get("chapter_tag", "THE CHILL CLUB")
    caption_style = script_data.get("caption_style", "modern_card")
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    glow_mask = build_ambient_glow_mask(VISUAL_TUNING["ambient_glow_strength"])
    particle_seeds = generate_particle_seeds(32)
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

        # Freeze-frame record scratch hold on first 0.45s of Act 2/3 if chosen
        if s_idx > 0 and sc.get("transition_in") == "freeze_record_scratch" and scene_t < 0.45 and prev_rendered_frame is not None:
            frame = ImageEnhance.Color(prev_rendered_frame).enhance(0.15)
        else:
            frame = apply_camera_trajectory(base_img, sc.get("camera_move", "dolly_push_in"), local_p, scene_t, t)
            frame = apply_progressive_grade_and_fx(frame, sc, local_p, t, vignette_mask, glow_mask, particle_seeds)

            trans_dur = VISUAL_TUNING["transition_sec"]
            if s_idx > 0 and scene_t < trans_dur and prev_rendered_frame is not None:
                tr_p = scene_t / trans_dur
                frame = apply_director_transition(prev_rendered_frame, frame, sc.get("transition_in", "hard_cut"), tr_p)
            else:
                prev_rendered_frame = frame.copy()

        # Progress bar
        draw = ImageDraw.Draw(frame)
        prog = min(1.0, (f_idx + 1) / max(1, total_frames))
        g_curr = COLOR_GRADES.get(sc.get("end_grade", "comic_vibrant"), COLOR_GRADES["comic_vibrant"])
        bar_x = int(W * prog)
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=g_curr["accent"])
        if bar_x > 8:
            draw.rectangle([max(0, bar_x - 18), 0, bar_x, 8], fill=g_curr["glow"])

        frame = draw_director_overlays(
            frame=frame,
            chapter_tag=chapter_tag,
            caption_style=caption_style,
            sc=sc,
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
    print(f"Rendered Creative Director Reel: {out_mp4}")


# ==============================================================================
# 7. GITHUB PAGES HOSTING & META GRAPH API V21.0 PUBLISHING
# ==============================================================================
def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish Creative Director Reel {rel_path}"], check=True)
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
        time_slot_vibe = "MORNING SLOT (9 AM): Sunrise adventures, morning coffee chaos, waking up late, or Hangover-style morning-after mysteries."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT (2 PM): Kitchen dance breaks, payday debates, workplace Office-style stares, or road trip errands."
    else:
        time_slot_vibe = "EVENING/NIGHT SLOT (9 PM+): Golden-hour sunset drives, bedroom rock concerts, 2:47 AM Alan conspiracies, or late-night celebrations."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('story_hook', '')}" for h in recent_history if h.get("story_hook")) or "None yet"
        seed = sample_creative_director_seed(recent_history)
        cast_descriptions = "\n".join(f"- {c}: {CAST_PROFILES[c]['role']} | Visual: {CAST_PROFILES[c]['visual']}" for c in seed["characters"])

        prompt = (
            f"You are an award-winning Creative Director & Comedy Writer for {page['handle']}.\n"
            f"CHANNEL IDENTITY: {page['domain']}\n\n"
            "### MANDATORY CREATIVE DIRECTION BRIEF (FOLLOW STRICTLY)\n"
            f"- Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Characters in This Story:\n{cast_descriptions}\n"
            f"- Story Scenario Seed: {seed['scenario']}\n"
            f"- Pop-Culture / Movie Parody Angle: {seed['movie_parody']}\n"
            f"- Primary Art Style: {seed['art_style_key']} (you may switch 1 act to another style like 'manga_impact', 'noir_monochrome', or 'retro_vhs_90s' if a flashback or punchline warrants it)\n"
            f"- Caption Style: {seed['caption_style']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only weave in if natural): \n{trends}\n"
            f"- Previously Told Stories (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### DIRECTION RULES\n"
            "1. Write an escalating 3-act visual story (Act 1 Setup -> Act 2 Chaos/Turn -> Act 3 Payoff/Punchline) starring ONLY the Active Characters listed above.\n"
            "2. Keep each character's personality sharp (Phil = overconfident instigator, Alan = unfiltered wildcard, Stu = anxious overthinker, Doug = chill grounded legend).\n"
            "3. Every 'visual_prompt' MUST describe concrete physical actions (starting pose -> mid-scene movement/prop interaction -> ending reaction), NOT static standing.\n"
            "4. Vary 'start_grade', 'end_grade', 'camera_move', and 'transition_in' deliberately across all 3 acts so each act feels dynamically directed.\n\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            '  "chapter_tag": "FRIDAY · 11:42 PM",\n'
            '  "caption_style": "' + seed["caption_style"] + '",\n'
            '  "music_prompt": "Upbeat comedic funk guitar and drums driving groove instrumental",\n'
            '  "music_bpm": 118,\n'
            '  "scenes": [\n'
            '    {"story_caption": "Act 1 setup line (12-18 words)", "emotion_cue": "TRUST ME.", "visual_prompt": "Act 1 concrete action starting pose -> mid-action -> ending pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "comic_vibrant", "end_grade": "golden_hour", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "dust", "sfx_cue": "pop_ding"},\n'
            '    {"story_caption": "Act 2 escalation/chaos line (12-18 words)", "emotion_cue": "WAIT WHAT.", "visual_prompt": "Act 2 concrete action starting pose -> mid-action -> ending pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "desaturated_gloom", "end_grade": "crimson_panic", "camera_move": "dutch_tilt_tension", "transition_in": "whip_pan_left", "env_effect": "sparks", "sfx_cue": "record_scratch"},\n'
            '    {"story_caption": "Act 3 hilarious payoff/twist line (12-18 words)", "emotion_cue": "CLASSIC.", "visual_prompt": "Act 3 concrete action starting pose -> mid-action -> ending pose, NO text", "art_style_key": "' + seed["art_style_key"] + '", "start_grade": "cold_cyan_night", "end_grade": "golden_hour", "camera_move": "pull_back_reveal", "transition_in": "freeze_record_scratch", "env_effect": "none", "sfx_cue": "vine_boom_sub"}\n'
            "  ],\n"
            '  "ig_caption": "Punchy relatable caption referencing the crew",\n'
            '  "pinned_comment": "Fun question asking followers which character they relate to most"\n'
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
        full_story_text = "\n".join(f"Act {i+1}: {s.get('story_caption', '')}" for i, s in enumerate(script_data["scenes"][:3]))
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Cast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nStyle: {seed['art_style_key']}\n{script_data.get('chapter_tag', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "cast_mode": seed["cast_mode"],
            "characters": seed["characters"],
            "art_style_key": seed["art_style_key"],
            "story_hook": act1_line,
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, final_caption)
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, final_caption)
