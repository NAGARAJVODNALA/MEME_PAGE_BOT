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
# CREATIVE DIRECTOR & ANIMATION TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.16,      # Subtle edge depth while keeping characters crisp
    "color_tint_strength": 0.08,    # Natural environment color wash
    "ambient_glow_strength": 0.13,  # Warm lamp / window / phone screen rim light
    "particle_opacity": 0.28,       # Gentle dust motes / sparks / rain
    "max_zoom_delta": 0.07,         # Purposeful camera framing & shot-reverse-shot punch-ins
    "transition_sec": 0.20,         # Crisp comedic cut / whip-pan timing
    "enable_blur_transition": True,
    "min_beat_sec": 3.0,            # Minimum beat duration for visual absorption
    "max_beat_sec": 5.5,            # Maximum beat duration
    "words_per_sec": 2.6            # Natural reading / speaking pace
}

# ==============================================================================
# 1. DRESSED CHARACTER ROSTER (PHIL, ALAN, STU, DOUG + VOICES & APPAREL)
# ==============================================================================
CAST_IDENTITY = {
    "Phil": {
        "archetype": "The Confident Instigator (smug grin, backwards snapback cap, talks everyone into wild logic)",
        "visual": (
            "Phil (2D webcomic character with large warm-gray cel-shaded round head #D8D5D0, thick black ink outline, "
            "backwards red snapback cap, large expressive eyes, wearing a red sleeveless zip-up hoodie vest with white drawstrings "
            "over thin black stick arms, white cartoon hands, stick legs, and red-and-white high-top sneakers)"
        ),
        "cap_color": (184, 56, 54),
        "backwards_cap": True,
        "outfit": "hoodie_vest",
        "shirt_color": (192, 54, 54),
        "shoe_color": (188, 52, 52),
        "beard": False,
        "glasses": False,
        "satchel": False,
        "voice_name": "Puck",
        "pitch_hz": 148.0
    },
    "Alan": {
        "archetype": "The Deadpan Wildcard (earnest wide eyes, brown beard, 2:30 AM life theories)",
        "visual": (
            "Alan (2D webcomic character with large warm-gray cel-shaded round head #D8D5D0, thick black ink outline, "
            "scruffy brown beard, large expressive eyes, wearing an olive crew-neck t-shirt with brown crossbody satchel strap "
            "over thin black stick arms, white cartoon hands, stick legs, and olive-and-white sneakers)"
        ),
        "cap_color": None,
        "backwards_cap": False,
        "outfit": "crew_tee",
        "shirt_color": (96, 116, 76),
        "shoe_color": (76, 94, 62),
        "beard": True,
        "glasses": False,
        "satchel": True,
        "voice_name": "Charon",
        "pitch_hz": 116.0
    },
    "Stu": {
        "archetype": "The Relatable Overthinker (square black glasses, checks bank app twice, sweats over alarms)",
        "visual": (
            "Stu (2D webcomic character with large warm-gray cel-shaded round head #D8D5D0, thick black ink outline, "
            "thick square black glasses, side-part hair tuft, large expressive eyes, wearing a slate-blue collared tee "
            "over thin black stick arms, white cartoon hands, stick legs, and slate-blue sneakers)"
        ),
        "cap_color": None,
        "backwards_cap": False,
        "outfit": "collared_tee",
        "shirt_color": (82, 112, 148),
        "shoe_color": (58, 82, 112),
        "beard": False,
        "glasses": True,
        "satchel": False,
        "voice_name": "Fenrir",
        "pitch_hz": 158.0
    },
    "Doug": {
        "archetype": "The Chill Grounded Friend (skeptical half-lidded eyes, unbothered voice of reason)",
        "visual": (
            "Doug (2D webcomic character with large warm-gray cel-shaded round head #D8D5D0, thick black ink outline, "
            "large half-lidded skeptical eyes, wearing a forest-green crew-neck t-shirt over thin black stick arms, "
            "white cartoon hands, stick legs, and dark green sneakers)"
        ),
        "cap_color": None,
        "backwards_cap": False,
        "outfit": "crew_tee",
        "shirt_color": (60, 108, 78),
        "shoe_color": (46, 84, 60),
        "beard": False,
        "glasses": False,
        "satchel": False,
        "voice_name": "Orus",
        "pitch_hz": 128.0
    }
}

CAST_MODES = {
    "solo_pov": {
        "desc": "1 character in a relatable 'Pov: Me...' personal moment",
        "lineups": [["Stu"], ["Phil"], ["Alan"], ["Doug"]]
    },
    "classic_duo": {
        "desc": "2 contrasting friends in spoken banter or shared comedy",
        "lineups": [
            ["Phil", "Stu"],
            ["Alan", "Doug"],
            ["Phil", "Doug"],
            ["Alan", "Stu"],
            ["Stu", "Doug"]
        ]
    },
    "trio_hangout": {
        "desc": "3 friends caught in an everyday apartment or group-chat debate",
        "lineups": [
            ["Phil", "Alan", "Stu"],
            ["Phil", "Stu", "Doug"],
            ["Alan", "Stu", "Doug"]
        ]
    },
    "full_crew_4": {
        "desc": "All 4 friends (Phil, Alan, Stu, and Doug) together",
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
    "confident_smirk"
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
# 2. ENVIRONMENTS, ART STYLES & DUAL-MODE SCENARIOS (SPOKEN SKIT + VISUAL POV)
# ==============================================================================
ENVIRONMENT_PRESETS = {
    "warm_desk_lamp": {
        "desc": "Warm amber-lit apartment room with walnut desk, wall sconce lamp, potted plant, and red ceramic mug",
        "wall": (196, 132, 84),
        "surface": (118, 72, 42),
        "accent_prop": (184, 58, 52)
    },
    "overcast_bedroom": {
        "desc": "Cozy bedroom with soft slate-gray blanket, folded white top sheet, framed mountain wall art, and lamp glow",
        "wall": (198, 204, 212),
        "night_wall": (44, 54, 80),
        "surface": (136, 146, 160),
        "accent_prop": (238, 240, 246)
    },
    "living_room_window": {
        "desc": "Suburban living room with slate-blue couch and window overlooking yellow house and stacked delivery boxes",
        "wall": (176, 198, 222),
        "surface": (98, 122, 152),
        "accent_prop": (194, 148, 96)
    },
    "sidewalk_hangout": {
        "desc": "Clean suburban sidewalk with crisp blue sky, low brick wall, streetlamp, and neighborhood trees",
        "wall": (164, 206, 242),
        "surface": (154, 158, 166),
        "accent_prop": (186, 102, 78)
    },
    "midnight_car_cabin": {
        "desc": "Parked car interior at night with warm dashboard glow, steering wheel, and streetlights outside",
        "wall": (34, 46, 72),
        "surface": (24, 28, 38),
        "accent_prop": (118, 212, 255)
    },
    "kitchen_counter": {
        "desc": "Bright apartment kitchen with tiled backsplash, counter, frying pan, and coffee maker",
        "wall": (214, 206, 194),
        "surface": (134, 138, 146),
        "accent_prop": (86, 156, 108)
    }
}

ART_STYLES = {
    "reference_webcomic_2d": {
        "prompt": (
            "Clean 2D Flash/webcomic animation frame: large warm-gray cel-shaded round heads (#D8D5D0) with thick black ink outlines, "
            "large expressive eyes with eyelids and eyebrows, structured 2D crew-neck t-shirts or sleeveless hoodie vests over thin black stick arms, "
            "white cartoon hands, stick legs with high-top sneakers, and clean lived-in 2D backgrounds"
        ),
        "hashtags": ["#webcomic", "#2danimation", "#relatable"]
    },
    "cozy_lamp_cartoon": {
        "prompt": (
            "Warm 2D animated comedy short with rich indoor lighting, dressed round-head stick characters in t-shirts and sneakers, "
            "thick black ink outlines, large expressive eyes, and detailed everyday props"
        ),
        "hashtags": ["#animatedshorts", "#relatablememes", "#2danimation"]
    },
    "suburban_cel_toon": {
        "prompt": (
            "Clean daylight 2D animated comedy short with dressed round-head stick characters, expressive lip-sync acting, "
            "bold ink outlines, and crisp suburban apartment and sidewalk backgrounds"
        ),
        "hashtags": ["#cartoonmemes", "#sliceoflife", "#funnyvideos"]
    }
}

RELATABLE_SCENARIOS = [
    # --- SPOKEN DIALOGUE SKITS (Shot-Reverse-Shot + Lip-Sync + Gestures) ---
    {
        "reel_mode": "spoken_skit",
        "hook": "When your friend says 'I'm 5 minutes away' 📞",
        "env": "sidewalk_hangout",
        "clocks": ["7:00 PM", "7:14 PM", "7:29 PM", "7:42 PM"],
        "story_seed": "Calling a friend who claims he is 'pulling up right now' while clearly still at home putting on his shoes"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Friend math: why buying a $7 iced coffee saves money",
        "env": "kitchen_counter",
        "clocks": ["10:15 AM", "10:16 AM", "10:17 AM", "10:18 AM"],
        "story_seed": "Confidently arguing with finger-counting logic that spending $7 on iced coffee actually saves $20 in emotional stress"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "Trying to pick ONE restaurant with the boys",
        "env": "sidewalk_hangout",
        "clocks": ["8:05 PM", "8:22 PM", "8:40 PM", "9:02 PM"],
        "story_seed": "Two friends saying 'I don't care, you pick' and then rejecting every single restaurant suggestion on the block"
    },
    {
        "reel_mode": "spoken_skit",
        "hook": "When you ask your friend to spot you 'until Friday'",
        "env": "warm_desk_lamp",
        "clocks": ["TUESDAY", "FRIDAY", "NEXT MONTH", "RIGHT NOW"],
        "story_seed": "Dramatically pleading for a $12 lunch loan while conveniently forgetting the three previous 'until Friday' loans"
    },
    # --- VISUAL POV REELS (Music + SFX + Ticking Clocks + Real Eyes/Blankets) ---
    {
        "reel_mode": "visual_pov",
        "hook": "Pov: 'I'm going to sleep early tonight'",
        "env": "overcast_bedroom",
        "clocks": ["22:00", "23:30", "01:15", "03:00"],
        "story_seed": "Starting with tired under-eye bags at 22:00, getting frustrated at 23:30, and hitting a maniacal 3 AM phone-scroll grin at 03:00"
    },
    {
        "reel_mode": "visual_pov",
        "hook": "When you have to wake up at 8 am",
        "env": "overcast_bedroom",
        "clocks": ["6:55am", "7:10am", "7:18am", "12:34pm"],
        "story_seed": "Snoozing smugly under the blanket for '5 more minutes' and waking up at 12:34pm in bloodshot panic"
    },
    {
        "reel_mode": "visual_pov",
        "hook": "Me: I need to stay home so I don't spend money",
        "env": "living_room_window",
        "clocks": ["1:15 PM", "2:40 PM", "4:05 PM", "5:30 PM"],
        "story_seed": "Staying home on the couch to avoid spending money while online delivery boxes keep piling up outside the window"
    },
    {
        "reel_mode": "visual_pov",
        "hook": "Pov: You get home and sit in your parked car",
        "env": "midnight_car_cabin",
        "clocks": ["6:12 PM", "6:24 PM", "6:38 PM", "6:51 PM"],
        "story_seed": "Pulling into the driveway after a long day and sitting in total silence for 39 minutes staring at the steering wheel"
    }
]

# ==============================================================================
# 3. ENVIRONMENT COLOR GRADES, CAMERA MOVES & TRANSITIONS
# ==============================================================================
COLOR_GRADES = {
    "warm_amber_desk": {
        "tint": (235, 154, 88), "glow": (255, 208, 128), "contrast": 1.05, "sat": 1.08,
        "card_bg": (24, 18, 18), "card_fg": (255, 248, 240), "accent": (255, 184, 96)
    },
    "overcast_morning_bedroom": {
        "tint": (182, 192, 206), "glow": (232, 238, 246), "contrast": 1.04, "sat": 0.92,
        "card_bg": (22, 24, 30), "card_fg": (248, 250, 255), "accent": (152, 196, 245)
    },
    "dim_night_phone_glow": {
        "tint": (58, 76, 112), "glow": (132, 214, 255), "contrast": 1.08, "sat": 0.96,
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
        "layout_mode": "v10_dressed_lipsync",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Relatable 2D animated webcomic shorts starring Phil, Alan, Stu, and Doug — dressed characters with structured tees/hoodies, sneakers, real eyes with eyelids/brows, and lip-synced dialogue + POV comedy",
        "art_style": "Clean 2D webcomic animation with cel-shaded warm-gray round heads, thick black outlines, structured crew-neck tees and hoodies, sneakers, real expressive eyes, and lip-sync mouth shapes"
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
            "Staying up scrolling until 3 AM after saying I will sleep early",
            "Friend math justifying a $7 iced coffee"
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
    """Selects a fresh scenario (alternating spoken_skit and visual_pov), cast lineup, and art style."""
    used_keys = {h.get("combo_key", "") for h in recent_history}
    recent_hooks = {h.get("top_hook", "") for h in recent_history[-6:]}
    last_mode = recent_history[-1].get("reel_mode", "") if recent_history else ""

    for _ in range(50):
        scen = random.choice(RELATABLE_SCENARIOS)
        if scen["hook"] in recent_hooks and random.random() < 0.85:
            continue
        if scen["reel_mode"] == last_mode and random.random() < 0.70:
            continue

        if scen["reel_mode"] == "spoken_skit":
            cast_mode = random.choice(["classic_duo", "trio_hangout"])
        else:
            cast_mode = random.choice(list(CAST_MODES.keys()))

        characters = random.choice(CAST_MODES[cast_mode]["lineups"])
        art_style_key = random.choice(list(ART_STYLES.keys()))
        combo_key = f"{scen['reel_mode']}|{cast_mode}|{'+'.join(characters)}|{scen['hook'][:24]}"
        if combo_key not in used_keys:
            return {
                "combo_key": combo_key,
                "reel_mode": scen["reel_mode"],
                "cast_mode": cast_mode,
                "characters": characters,
                "scenario": scen,
                "art_style_key": art_style_key
            }

    scen = random.choice(RELATABLE_SCENARIOS)
    cast_mode = "classic_duo" if scen["reel_mode"] == "spoken_skit" else "solo_pov"
    return {
        "combo_key": f"ref_{int(time.time())}",
        "reel_mode": scen["reel_mode"],
        "cast_mode": cast_mode,
        "characters": random.choice(CAST_MODES[cast_mode]["lineups"]),
        "scenario": scen,
        "art_style_key": "reference_webcomic_2d"
    }


def validate_and_fix_plan(script_data, seed):
    """Enforces 4 beats, valid expressions, dressed actions, spoken dialogue rules, and unique cameras."""
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
    reel_mode = script_data.get("reel_mode") if script_data.get("reel_mode") in ("spoken_skit", "visual_pov") else seed["reel_mode"]
    script_data["reel_mode"] = reel_mode

    if not script_data.get("top_hook"):
        script_data["top_hook"] = scen["hook"]
    if script_data.get("environment_key") not in ENVIRONMENT_PRESETS:
        script_data["environment_key"] = scen["env"]

    default_exprs = ["tired_bags", "skeptical_half_lid", "angry_brow", "bloodshot_shock"]
    default_actions = (
        ["phone_call_ear", "point_argue", "count_fingers", "shrug_palms"]
        if reel_mode == "spoken_skit"
        else ["sleep_breathe_toss", "phone_scroll_lean", "struggle_pull", "shock_recoil"]
    )

    for idx, sc in enumerate(scenes):
        if sc.get("start_grade") not in COLOR_GRADES:
            sc["start_grade"] = "suburban_daylight_cel" if reel_mode == "spoken_skit" else "dim_night_phone_glow"
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

        # Spoken skit vs visual POV validation
        if reel_mode == "spoken_skit":
            spk = sc.get("speaker")
            if spk not in chars:
                spk = chars[idx % len(chars)]
            sc["speaker"] = spk
            dlg = (sc.get("dialogue") or sc.get("bottom_caption") or "").strip()
            if not dlg:
                dlg = "Bro, you said five minutes twenty minutes ago."
            words = dlg.split()
            if len(words) > 15:
                dlg = " ".join(words[:14]) + "."
            sc["dialogue"] = dlg
            sc["shot_framing"] = sc.get("shot_framing") if sc.get("shot_framing") in ("two_shot", "speaker_closeup") else ("speaker_closeup" if idx in (1, 2) else "two_shot")
        else:
            sc["speaker"] = ""
            sc["dialogue"] = ""
            sc["shot_framing"] = "two_shot"
            cap = (sc.get("bottom_caption") or "").strip()
            words = cap.split()
            if len(words) > 12:
                sc["bottom_caption"] = " ".join(words[:11]) + "..."

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

    if script_data.get("reel_mode") == "spoken_skit":
        dynamic_tags.extend(["#comedyskit", "#voiceacting", "#friendgroup"])
    else:
        dynamic_tags.extend(["#literallyme", "#pov", "#relatable"])

    dynamic_tags.extend(["#wearechillclub", "#animatedshorts", "#funnyreels"])

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
    scen = seed["scenario"]
    style_key = seed["art_style_key"]
    reel_mode = seed["reel_mode"]

    if reel_mode == "spoken_skit":
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
                    "expression": "confident_smirk",
                    "end_expression": "sweat_grit",
                    "body_action": "point_argue",
                    "prop_overlay": "sweat_drops",
                    "visual_prompt": f"Close-up of {c2} gesturing confidently while clearly still inside his apartment, NO text",
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
                    "speaker": c1,
                    "dialogue": "Then why do I hear your microwave beeping in the background?!",
                    "shot_framing": "speaker_closeup",
                    "bottom_caption": "",
                    "expression": "angry_brow",
                    "end_expression": "skeptical_half_lid",
                    "body_action": "temple_tap",
                    "prop_overlay": "none",
                    "visual_prompt": f"Tight reaction shot of {c1} tapping his temple in disbelief, NO text",
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
                    "dialogue": "That is my car's... uh... pedestrian safety chime. See you in two!",
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
            "ig_caption": f"Tag the friend whose '5 minutes away' means they haven't even showered yet.",
            "pinned_comment": "What is the worst excuse your friend gave for being late?"
        }

    return {
        "reel_mode": "visual_pov",
        "top_hook": scen["hook"],
        "environment_key": scen["env"],
        "setting_continuity": ENVIRONMENT_PRESETS[scen["env"]]["desc"],
        "music_prompt": "Playful lo-fi indie marimba and acoustic guitar comedy loop instrumental",
        "music_bpm": 104,
        "scenes": [
            {
                "clock_label": scen["clocks"][0],
                "speaker": "",
                "dialogue": "",
                "shot_framing": "two_shot",
                "bottom_caption": "",
                "expression": "tired_bags",
                "end_expression": "exhausted_half_lidded",
                "body_action": "sleep_breathe_toss",
                "prop_overlay": "zzz_float",
                "visual_prompt": f"Medium shot of {c1} with tired under-eye bags in dim bedroom, NO text",
                "art_style_key": style_key,
                "start_grade": "dim_night_phone_glow",
                "end_grade": "dim_night_phone_glow",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "env_effect": "dust",
                "sfx_cue": "pop_ding"
            },
            {
                "clock_label": scen["clocks"][1],
                "speaker": "",
                "dialogue": "",
                "shot_framing": "two_shot",
                "bottom_caption": "Just one quick video.",
                "expression": "skeptical_half_lid",
                "end_expression": "angry_brow",
                "body_action": "phone_scroll_lean",
                "prop_overlay": "none",
                "visual_prompt": f"Close-up of {c1} holding glowing smartphone in bed at night, NO text",
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
                "speaker": "",
                "dialogue": "",
                "shot_framing": "speaker_closeup",
                "bottom_caption": "",
                "expression": "confident_smirk",
                "end_expression": "maniacal_3am_grin",
                "body_action": "phone_scroll_lean",
                "prop_overlay": "none",
                "visual_prompt": f"Tight face close-up of {c1} with wide maniacal 3 AM phone-lit grin, NO text",
                "art_style_key": style_key,
                "start_grade": "dim_night_phone_glow",
                "end_grade": "dim_night_phone_glow",
                "camera_move": "snap_zoom_face",
                "transition_in": "whip_pan_left",
                "env_effect": "screen_glow",
                "sfx_cue": "record_scratch"
            },
            {
                "clock_label": scen["clocks"][3],
                "speaker": "",
                "dialogue": "",
                "shot_framing": "two_shot",
                "bottom_caption": "Alarm rings in 2 hours.",
                "expression": "maniacal_3am_grin",
                "end_expression": "bloodshot_shock",
                "body_action": "shock_recoil",
                "prop_overlay": "sweat_drops",
                "visual_prompt": f"Pulled-back reveal of {c1} in bloodshot shock seeing the 3 AM clock, NO text",
                "art_style_key": style_key,
                "start_grade": "crimson_panic_shock",
                "end_grade": "golden_morning_sunlight",
                "camera_move": "pull_back_reveal",
                "transition_in": "smash_zoom_cut",
                "env_effect": "none",
                "sfx_cue": "vine_boom_sub"
            }
        ],
        "ig_caption": f"{scen['hook']} — tell me this isn't your exact sleep schedule.",
        "pinned_comment": "What time did you actually fall asleep last night?"
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
                        print(f"Generated {parsed.get('reel_mode', seed['reel_mode'])} script with {model}")
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

    print(f"All Gemini text endpoints busy ({last_err}); using local script.")
    return validate_and_fix_plan(_build_local_fallback_script(seed), seed)


# ==============================================================================
# 4. VOICE SYNTHESIS & 24FPS LIP-SYNC VISEME ENVELOPE GENERATOR
# ==============================================================================
def _extract_viseme_timeline(wav_path, total_beat_frames, speech_offset_frames=3):
    """Analyzes 48kHz WAV samples per 24fps video frame to output exact mouth visemes."""
    timeline = ["closed"] * total_beat_frames
    if not wav_path or not pathlib.Path(wav_path).exists():
        return timeline

    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    total_samples = len(raw) // (2 * n_ch)
    if total_samples <= 0:
        return timeline

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
        return timeline

    for f in range(num_audio_frames):
        vid_f = f + speech_offset_frames
        if vid_f >= total_beat_frames:
            break
        norm_e = energies[f] / peak
        if norm_e < 0.14:
            timeline[vid_f] = "closed"
        elif norm_e > 0.62 and zcrs[f] < 0.08:
            timeline[vid_f] = "o_vowel"
        elif zcrs[f] > 0.16 and norm_e < 0.42:
            timeline[vid_f] = "gritted_teeth"
        else:
            timeline[vid_f] = "open_teeth"

    return timeline


def _try_gemini_tts(dialogue_text, voice_name, out_wav):
    """Generates natural spoken voice WAV via Gemini 2.5 Flash native audio output."""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=){GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Speak this single comedic line naturally with expressive timing, and output ONLY the spoken audio: \"{dialogue_text}\""
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
                raw_tmp = out_wav.parent / (out_wav.stem + "_raw")
                if "L16" in mime or "pcm" in mime:
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
                return True
    return False


def _synth_formant_speech_fallback(dialogue_text, pitch_hz, out_wav):
    """Zero-dependency expressive syllable formant synthesizer when TTS endpoints are offline."""
    sr = 48000
    words = [w for w in dialogue_text.split() if w]
    if not words:
        return
    frames = bytearray()
    rng = random.Random(hash(dialogue_text) & 0xFFFF)

    for w_idx, word in enumerate(words):
        syllables = max(1, min(4, len(word) // 3 + 1))
        for s_idx in range(syllables):
            dur = rng.uniform(0.11, 0.17)
            n_samp = int(sr * dur)
            f0 = pitch_hz * rng.uniform(0.92, 1.14) * (1.06 if word.endswith("?") and w_idx == len(words) - 1 else 1.0)
            f1 = rng.choice([420.0, 560.0, 720.0, 340.0])
            f2 = rng.choice([1250.0, 1680.0, 2100.0, 980.0])
            for i in range(n_samp):
                t = i / sr
                env = math.sin((i / max(1, n_samp - 1)) * math.pi)
                # Glottal pulse harmonics shaped by two vocal formants
                glottal = sum((1.0 / h) * math.sin(2 * math.pi * f0 * h * t) for h in range(1, 7))
                formant = 0.55 * math.sin(2 * math.pi * f1 * t) + 0.30 * math.sin(2 * math.pi * f2 * t)
                sig = (glottal * 0.45 + formant * 0.55) * env * 0.42
                val = int(max(-0.92, min(0.92, sig)) * 32767)
                frames.extend(struct.pack("<hh", val, val))
            # Short inter-syllable gap
            frames.extend(b"\x00\x00\x00\x00" * int(sr * 0.025))
        # Inter-word pause
        frames.extend(b"\x00\x00\x00\x00" * int(sr * 0.055))

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(frames)


def synthesize_dialogue_beat(speaker, dialogue_text, out_wav):
    """Generates spoken WAV for a character line and returns its duration in seconds."""
    prof = CAST_IDENTITY.get(speaker, CAST_IDENTITY["Phil"])
    voice_name = prof.get("voice_name", "Puck")
    pitch_hz = prof.get("pitch_hz", 140.0)

    generated = False
    try:
        generated = _try_gemini_tts(dialogue_text, voice_name, out_wav)
        if generated:
            print(f"Synthesized {speaker} voice ({voice_name}) via Gemini TTS")
    except Exception as e:
        print(f"Gemini TTS skipped for {speaker} ({e})")

    if not generated:
        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak_bin:
            raw_espeak = out_wav.parent / (out_wav.stem + "_esp.wav")
            pitch_val = int(max(25, min(85, (pitch_hz - 95.0) * 0.85)))
            subprocess.run([espeak_bin, "-s", "158", "-p", str(pitch_val), "-w", str(raw_espeak), dialogue_text], check=True)
            subprocess.run(["ffmpeg", "-y", "-i", str(raw_espeak), "-ar", "48000", "-ac", "2", str(out_wav)], check=True)
            raw_espeak.unlink(missing_ok=True)
            generated = True
            print(f"Synthesized {speaker} voice via {espeak_bin}")

    if not generated:
        _synth_formant_speech_fallback(dialogue_text, pitch_hz, out_wav)
        print(f"Synthesized {speaker} voice via formant cadence fallback")

    with wave.open(str(out_wav), "rb") as wf:
        dur = wf.getnframes() / float(wf.getframerate())
    return dur


def compute_beat_durations_and_voices(scenes, tmp_dir):
    """Computes beat durations (driven by spoken dialogue length in spoken_skit mode) + lip-sync timelines."""
    durations = []
    voice_tracks = []
    viseme_timelines = []

    for idx, sc in enumerate(scenes):
        dlg = (sc.get("dialogue") or "").strip()
        spk = (sc.get("speaker") or "").strip()
        if dlg and spk:
            wav_path = tmp_dir / f"voice_{idx}.wav"
            speech_dur = synthesize_dialogue_beat(spk, dlg, wav_path)
            dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"] + 1.2, speech_dur + 0.55)), 2)
            durations.append(dur)
            voice_tracks.append(wav_path)
            viseme_timelines.append(_extract_viseme_timeline(wav_path, int(dur * FPS) + 6, speech_offset_frames=3))
        else:
            words = len((sc.get("bottom_caption") or "").split())
            read_sec = words / VISUAL_TUNING["words_per_sec"]
            cushion = 1.65 if idx == len(scenes) - 1 else 1.40
            dur = round(max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], read_sec + cushion)), 2)
            durations.append(dur)
            voice_tracks.append(None)
            viseme_timelines.append(["closed"] * (int(dur * FPS) + 6))

    return durations, voice_tracks, viseme_timelines


# ==============================================================================
# 5. DRESSED FULL-BODY CHARACTER RIG + REAL EYES + 4-VISEME LIP-SYNC RENDERER
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
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)
    wall_col = env.get("night_wall", env["wall"]) if is_night else env["wall"]

    img = Image.new("RGB", (W, H), color=wall_col)
    draw = ImageDraw.Draw(img)

    if env_key == "sidewalk_hangout":
        # Suburban sky, neighborhood house silhouette, brick wall & clean sidewalk
        draw.ellipse([130, 390, 250, 510], fill=(255, 236, 156))
        draw.polygon([(140, 790), (360, 620), (580, 790)], fill=(192, 98, 76), outline=ink)
        draw.rectangle([180, 790, 540, 1080], fill=(242, 224, 184), outline=ink, width=6)
        draw.rectangle([620, 860, W - 90, 1080], fill=(182, 104, 82), outline=ink, width=6)
        # Sidewalk ground
        draw.rectangle([0, 1080, W, H], fill=env["surface"])
        draw.line([(0, 1080), (W, 1080)], fill=ink, width=8)
        for sx in range(180, W, 260):
            draw.line([(sx, 1080), (sx - 90, H)], fill=(122, 126, 134), width=5)
    elif env_key == "living_room_window":
        sky_col = (28, 42, 74) if is_night else (168, 214, 248)
        draw.rectangle([110, 360, W - 110, 960], fill=sky_col, outline=ink, width=8)
        draw.polygon([(220, 620), (540, 440), (860, 620)], fill=(196, 98, 72), outline=ink)
        draw.rectangle([260, 620, 820, 956], fill=(246, 214, 118), outline=ink, width=6)
        for b in range(min(4, beat_idx + 1)):
            bx = 520 + (b % 2) * 110
            by = 850 - (b // 2) * 95
            draw.rectangle([bx, by, bx + 115, by + 95], fill=(198, 152, 98), outline=ink, width=5)
        draw.line([(W // 2, 360), (W // 2, 960)], fill=ink, width=8)
        draw.rounded_rectangle([80, 990, W - 80, 1260], radius=34, fill=env["surface"], outline=ink, width=8)
    elif env_key == "overcast_bedroom":
        halo_col = (68, 82, 118) if is_night else (218, 224, 234)
        draw.ellipse([W // 2 - 320, 320, W // 2 + 320, 960], fill=halo_col)
        frame_bg = (196, 206, 224) if is_night else (242, 244, 248)
        for fx0 in (165, W - 395):
            fx1 = fx0 + 230
            draw.rectangle([fx0, 410, fx1, 635], fill=frame_bg, outline=ink, width=6)
            draw.polygon([(fx0 + 22, 628), (fx0 + 95, 510), (fx0 + 160, 628)], fill=(124, 138, 162), outline=ink)
            draw.polygon([(fx0 + 105, 628), (fx0 + 165, 530), (fx0 + 212, 628)], fill=(96, 110, 134), outline=ink)
            draw.ellipse([fx0 + 155, 442, fx0 + 188, 475], fill=(255, 222, 128), outline=ink, width=3)
        hb_col = (94, 82, 74) if is_night else (168, 152, 136)
        pillow_col = (176, 184, 202) if is_night else (244, 246, 250)
        draw.rounded_rectangle([110, 815, W - 110, 1140], radius=24, fill=hb_col, outline=ink, width=7)
        draw.rounded_rectangle([180, 930, 510, 1085], radius=28, fill=pillow_col, outline=ink, width=5)
        draw.rounded_rectangle([570, 930, W - 180, 1085], radius=28, fill=pillow_col, outline=ink, width=5)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([90, 380, W - 90, 980], radius=48, fill=(22, 32, 54), outline=ink, width=8)
        draw.ellipse([740, 470, 810, 540], fill=(255, 224, 148))
        draw.rounded_rectangle([240, 790, 440, 1040], radius=28, fill=(38, 44, 56), outline=ink, width=6)
        draw.rounded_rectangle([640, 790, 840, 1040], radius=28, fill=(38, 44, 56), outline=ink, width=6)
    else:
        draw.ellipse([W // 2 - 290, 360, W // 2 + 290, 940], fill=(236, 178, 112))

    img.save(out_bg_path, format="PNG")


def _draw_sneaker(draw, fx, fy, scale, shoe_col, facing_dir=1):
    """Draws structured high-top sneakers with white soles and white toe caps."""
    ink = (18, 18, 22)
    sw = int(42 * scale)
    sh = int(24 * scale)
    x0 = fx - int(14 * scale) if facing_dir >= 0 else fx - sw + int(14 * scale)
    x1 = x0 + sw
    y0 = fy - sh
    y1 = fy + int(6 * scale)
    # Upper shoe body
    draw.rounded_rectangle([x0, y0, x1, y1], radius=int(9 * scale), fill=shoe_col, outline=ink, width=max(4, int(5 * scale)))
    # White rubber sole
    draw.rectangle([x0 + 2, y1 - int(7 * scale), x1 - 2, y1], fill=(248, 248, 252), outline=ink, width=3)
    # White toe cap
    if facing_dir >= 0:
        draw.pieslice([x1 - int(22 * scale), y0 + int(6 * scale), x1, y1 - int(4 * scale)], start=270, end=90, fill=(248, 248, 252), outline=ink, width=3)
    else:
        draw.pieslice([x0, y0 + int(6 * scale), x0 + int(22 * scale), y1 - int(4 * scale)], start=90, end=270, fill=(248, 248, 252), outline=ink, width=3)


def _draw_dressed_character(draw, name, cx, cy, scale, expr, body_action, viseme, t, local_p, idx_in_cast, facing_dir=1):
    """Draws a dressed 2D webcomic character with structured t-shirt/hoodie, sneakers, real eyes & lip-sync mouth."""
    prof = CAST_IDENTITY.get(name, CAST_IDENTITY["Phil"])
    ink = (18, 18, 22)
    head_fill = (216, 213, 208)
    head_shadow = (188, 185, 180)
    phase = idx_in_cast * 1.15

    # 1. Full-Body Kinematics (Talking bounce, lean, stride, recoil)
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
        head_tilt_x = int(18 * scale * facing_dir)
        body_dy = int(math.sin(t * 3.0 + phase) * 3 * scale)
    elif body_action == "shock_recoil":
        recoil = math.sin(min(1.0, local_p * 3.2) * math.pi * 0.5)
        jitter = int(math.sin(t * 48.0 + phase) * 5 * scale)
        body_dy = int(-22 * recoil * scale) + jitter
        torso_lean_x = int(-16 * recoil * scale * facing_dir)
        head_tilt_x = int(-20 * recoil * scale * facing_dir)
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
        # Conversational speaking head-nod & torso emphasis
        talk_bob = int(-6 * scale) if is_speaking else int(math.sin(t * 2.2 + phase) * 3 * scale)
        body_dy = talk_bob
        head_tilt_x = int(6 * scale * facing_dir) if is_speaking else 0

    hx = cx + body_dx + head_tilt_x
    hy = cy + body_dy
    r_head = int(100 * scale)
    neck_x = cx + body_dx + int(torso_lean_x * 0.5)
    neck_y = hy + r_head - 4
    hip_x = cx + body_dx
    hip_y = neck_y + int(176 * scale)
    limb_w = max(5, int(7 * scale))
    hand_r = max(11, int(15 * scale))

    # 2. Stick Legs + Structured Sneakers
    if body_action == "walk_stride":
        swing = math.sin(t * 7.5 + phase) * 46 * scale
        for side, s_mult in ((-1, 1.0), (1, -1.0)):
            kx = hip_x + int(swing * s_mult * 0.6)
            ky = hip_y + int(82 * scale)
            fx = hip_x + int(swing * s_mult)
            fy = hip_y + int(162 * scale)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)
            _draw_sneaker(draw, fx, fy, scale, prof["shoe_color"], facing_dir)
    elif body_action in ("sleep_breathe_toss", "phone_scroll_lean", "slouch_sigh"):
        for side in (-1, 1):
            kx = hip_x + side * int(50 * scale)
            ky = hip_y + int(68 * scale)
            fx = hip_x + side * int(54 * scale)
            fy = hip_y + int(154 * scale)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)
            _draw_sneaker(draw, fx, fy, scale, prof["shoe_color"], facing_dir)
    else:
        # Standing conversational stance with hip-to-knee bend & sneakers planted
        for side in (-1, 1):
            kx = hip_x + side * int(30 * scale)
            ky = hip_y + int(82 * scale)
            fx = hip_x + side * int(34 * scale)
            fy = hip_y + int(164 * scale)
            draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)
            _draw_sneaker(draw, fx, fy, scale, prof["shoe_color"], facing_dir)

    # 3. Structured 2D Clothing Torso (Sleeveless Hoodie Vest / Crew-Neck T-Shirt / Collared Tee)
    sh_y = neck_y + int(22 * scale)
    tw_top = int(42 * scale)
    tw_bot = int(48 * scale)
    shirt_c = prof["shirt_color"]
    shirt_shadow = tuple(max(0, c - 26) for c in shirt_c)
    outline_w = max(5, int(7 * scale))

    # Hood collar rim behind neck for Phil's hoodie vest
    if prof["outfit"] == "hoodie_vest":
        draw.pieslice([neck_x - int(48 * scale), neck_y - int(18 * scale), neck_x + int(48 * scale), neck_y + int(34 * scale)], start=180, end=360, fill=shirt_shadow, outline=ink, width=outline_w)

    # Short sleeves for crew_tee and collared_tee
    if prof["outfit"] in ("crew_tee", "collared_tee"):
        draw.polygon([
            (neck_x - tw_top, sh_y - 4),
            (neck_x - tw_top - int(26 * scale), sh_y + int(34 * scale)),
            (neck_x - tw_top + int(4 * scale), sh_y + int(46 * scale))
        ], fill=shirt_c, outline=ink)
        draw.polygon([
            (neck_x + tw_top, sh_y - 4),
            (neck_x + tw_top + int(26 * scale), sh_y + int(34 * scale)),
            (neck_x + tw_top - int(4 * scale), sh_y + int(46 * scale))
        ], fill=shirt_c, outline=ink)

    # Main torso garment polygon
    torso_poly = [
        (neck_x - tw_top, neck_y + int(6 * scale)),
        (neck_x + tw_top, neck_y + int(6 * scale)),
        (hip_x + tw_bot, hip_y + int(10 * scale)),
        (hip_x - tw_bot, hip_y + int(10 * scale))
    ]
    draw.polygon(torso_poly, fill=shirt_c)
    # Right-side cel shade on shirt
    draw.polygon([
        (neck_x + int(10 * scale), neck_y + int(8 * scale)),
        (neck_x + tw_top, neck_y + int(6 * scale)),
        (hip_x + tw_bot, hip_y + int(10 * scale)),
        (hip_x + int(14 * scale), hip_y + int(10 * scale))
    ], fill=shirt_shadow)
    draw.polygon(torso_poly, outline=ink, width=outline_w)

    # Garment-specific details (Zipper + drawstrings + kangaroo pocket OR crew collar OR polo collar + satchel)
    if prof["outfit"] == "hoodie_vest":
        draw.line([(neck_x, neck_y + int(14 * scale)), (hip_x, hip_y + int(10 * scale))], fill=ink, width=max(4, int(5 * scale)))
        # White drawstrings
        draw.line([(neck_x - int(14 * scale), neck_y + int(16 * scale)), (neck_x - int(16 * scale), neck_y + int(66 * scale))], fill=(248, 248, 252), width=max(3, int(4 * scale)))
        draw.line([(neck_x + int(14 * scale), neck_y + int(16 * scale)), (neck_x + int(16 * scale), neck_y + int(66 * scale))], fill=(248, 248, 252), width=max(3, int(4 * scale)))
        # Kangaroo pocket lines
        draw.line([(hip_x - int(36 * scale), hip_y - int(36 * scale)), (hip_x - int(12 * scale), hip_y - int(8 * scale))], fill=ink, width=4)
        draw.line([(hip_x + int(36 * scale), hip_y - int(36 * scale)), (hip_x + int(12 * scale), hip_y - int(8 * scale))], fill=ink, width=4)
    elif prof["outfit"] == "collared_tee":
        draw.polygon([(neck_x - int(22 * scale), neck_y + 6), (neck_x, neck_y + int(28 * scale)), (neck_x - int(6 * scale), neck_y + int(36 * scale))], fill=(238, 242, 248), outline=ink)
        draw.polygon([(neck_x + int(22 * scale), neck_y + 6), (neck_x, neck_y + int(28 * scale)), (neck_x + int(6 * scale), neck_y + int(36 * scale))], fill=(238, 242, 248), outline=ink)
    else:
        # Thick black crew-neck collar ring
        draw.arc([neck_x - int(24 * scale), neck_y - int(4 * scale), neck_x + int(24 * scale), neck_y + int(22 * scale)], start=0, end=180, fill=ink, width=max(5, int(7 * scale)))

    if prof["satchel"]:
        draw.line([(neck_x - int(34 * scale), neck_y + 10), (hip_x + int(38 * scale), hip_y + 4)], fill=(128, 84, 52), width=max(7, int(10 * scale)))

    # 4. Articulated Stick Arms + White Outlined Cartoon Hands + Conversational Gestures
    l_sh = (neck_x - tw_top, sh_y + int(14 * scale))
    r_sh = (neck_x + tw_top, sh_y + int(14 * scale))
    holding_phone = False
    phone_pos = (0, 0)
    gesture_beat = int(math.sin(t * 9.0 + phase) * 14 * scale) if is_speaking else 0

    if body_action == "phone_call_ear":
        # One hand holding smartphone up to ear, other hand gesturing while talking
        l_elb = (l_sh[0] - int(54 * scale), l_sh[1] - int(18 * scale))
        l_hand = (hx - r_head - int(10 * scale), hy + int(10 * scale))
        r_elb = (r_sh[0] + int(46 * scale), r_sh[1] + int(36 * scale))
        r_hand = (r_sh[0] + int(78 * scale), r_sh[1] + int(10 * scale) + gesture_beat)
        holding_phone = True
        phone_pos = (l_hand[0] - int(8 * scale), l_hand[1] - int(12 * scale))
    elif body_action == "point_argue":
        # Classic persuasive pointing hand toward listener + hand on hip
        l_elb = (l_sh[0] - int(38 * scale), l_sh[1] + int(44 * scale))
        l_hand = (hip_x - tw_bot, hip_y - int(16 * scale))
        r_elb = (r_sh[0] + int(48 * scale), r_sh[1] + int(22 * scale))
        r_hand = (r_sh[0] + int(112 * scale * facing_dir), r_sh[1] - int(6 * scale) + gesture_beat)
    elif body_action == "shrug_palms":
        # Two-hand open-palm conversational shrug
        l_elb = (l_sh[0] - int(52 * scale), l_sh[1] + int(38 * scale))
        l_hand = (l_sh[0] - int(88 * scale), l_sh[1] - int(6 * scale) + gesture_beat)
        r_elb = (r_sh[0] + int(52 * scale), r_sh[1] + int(38 * scale))
        r_hand = (r_sh[0] + int(88 * scale), r_sh[1] - int(6 * scale) - gesture_beat)
    elif body_action == "count_fingers":
        # Raised hand counting points ("1, 2, 3")
        l_elb = (l_sh[0] - int(34 * scale), l_sh[1] + int(52 * scale))
        l_hand = (l_sh[0] - int(22 * scale), hip_y)
        r_elb = (r_sh[0] + int(58 * scale), r_sh[1] + int(18 * scale))
        r_hand = (r_sh[0] + int(74 * scale), hy + int(42 * scale) + gesture_beat)
    elif body_action == "temple_tap":
        # Tapping side of head in disbelief ("Think about it!")
        l_elb = (l_sh[0] - int(38 * scale), l_sh[1] + int(44 * scale))
        l_hand = (hip_x - tw_bot, hip_y - int(16 * scale))
        r_elb = (r_sh[0] + int(76 * scale), r_sh[1] - int(12 * scale))
        r_hand = (hx + r_head + int(6 * scale), hy - int(18 * scale))
    elif body_action == "phone_scroll_lean":
        l_elb = (l_sh[0] - int(34 * scale), l_sh[1] + int(46 * scale))
        l_hand = (neck_x + int(16 * scale), sh_y + int(42 * scale) + int(math.sin(t * 9.0) * 6))
        r_elb = (r_sh[0] + int(46 * scale), r_sh[1] + int(44 * scale))
        r_hand = (r_sh[0] + int(56 * scale), hy + int(48 * scale))
        holding_phone = True
        phone_pos = (r_hand[0], r_hand[1] - int(18 * scale))
    elif body_action == "shock_recoil" or expr == "bloodshot_shock":
        wave_y = int(math.sin(t * 22.0 + phase) * 8 * scale)
        l_elb = (l_sh[0] - int(68 * scale), l_sh[1] + int(14 * scale))
        l_hand = (hx - int(94 * scale), hy + int(16 * scale) + wave_y)
        r_elb = (r_sh[0] + int(68 * scale), r_sh[1] + int(14 * scale))
        r_hand = (hx + int(94 * scale), hy + int(16 * scale) - wave_y)
    else:
        l_elb = (l_sh[0] - int(36 * scale), l_sh[1] + int(48 * scale))
        l_hand = (l_sh[0] - int(28 * scale), hip_y + int(4 * scale))
        r_elb = (r_sh[0] + int(36 * scale), r_sh[1] + int(48 * scale))
        r_hand = (r_sh[0] + int(28 * scale), hip_y + int(4 * scale))

    draw.line([l_sh, l_elb, l_hand], fill=ink, width=limb_w)
    draw.line([r_sh, r_elb, r_hand], fill=ink, width=limb_w)

    # White cartoon hands with crisp black ink outlines (matching reference video 1)
    for mhx, mhy in (l_hand, r_hand):
        draw.ellipse([mhx - hand_r, mhy - hand_r, mhx + hand_r, mhy + hand_r], fill=(250, 250, 254), outline=ink, width=max(4, int(5 * scale)))

    # Extended pointing finger for point_argue
    if body_action == "point_argue":
        p_dir = 1 if r_hand[0] >= neck_x else -1
        draw.line([(r_hand[0], r_hand[1] - 4), (r_hand[0] + p_dir * int(24 * scale), r_hand[1] - 4)], fill=ink, width=max(5, int(6 * scale)))

    # 5. Large Cel-Shaded Round Head
    draw.ellipse([hx - r_head, hy - r_head, hx + r_head, hy + r_head], fill=head_fill)
    draw.pieslice([hx - r_head + 6, hy - r_head + 6, hx + r_head - 2, hy + r_head - 2], start=-55, end=65, fill=head_shadow)
    draw.ellipse([hx - r_head, hy - r_head, hx + r_head, hy + r_head], outline=ink, width=max(6, int(9 * scale)))

    # 6. Signature Character Details (Phil's backwards cap, Alan's beard, Stu's glasses)
    if prof["cap_color"]:
        cap_c = prof["cap_color"]
        draw.pieslice([hx - r_head - 2, hy - r_head - 12, hx + r_head + 2, hy - int(r_head * 0.14)], start=180, end=360, fill=cap_c, outline=ink, width=max(6, int(8 * scale)))
        if prof.get("backwards_cap"):
            # Backwards snapback brim pointing left + plastic strap cutout on forehead
            draw.rounded_rectangle([hx - int(r_head * 1.32), hy - int(r_head * 0.56), hx + int(8 * scale), hy - int(r_head * 0.34)], radius=8, fill=cap_c, outline=ink, width=max(5, int(7 * scale)))
            draw.pieslice([hx - int(26 * scale), hy - int(r_head * 0.68), hx + int(26 * scale), hy - int(r_head * 0.34)], start=180, end=360, fill=head_fill, outline=ink, width=4)
        else:
            draw.rounded_rectangle([hx - int(10 * scale), hy - int(r_head * 0.56), hx + int(r_head * 1.32), hy - int(r_head * 0.34)], radius=8, fill=cap_c, outline=ink, width=max(5, int(7 * scale)))

    if prof["beard"]:
        draw.pieslice([hx - int(r_head * 0.86), hy + int(4 * scale), hx + int(r_head * 0.86), hy + r_head + 4], start=0, end=180, fill=(92, 64, 46), outline=ink, width=max(5, int(7 * scale)))

    # 7. "REAL EYES": Large Sclera Eyes + Irises + Eyelids + Under-Eye Bags + Eyebrows
    eye_dx = int(35 * scale)
    eye_y = hy - int(12 * scale)
    er_x = int(23 * scale)
    er_y = int(26 * scale)
    is_blinking = ((t + idx_in_cast * 0.9) % 3.4) < 0.11
    pupil_look_x = int(6 * scale * facing_dir) if (is_speaking or holding_phone) else int(math.sin(t * 1.4 + phase) * 3 * scale)

    if is_blinking and expr not in ("bloodshot_shock", "sweat_grit", "maniacal_3am_grin"):
        draw.line([(hx - eye_dx - er_x + 4, eye_y), (hx - eye_dx + er_x - 4, eye_y)], fill=ink, width=max(5, int(6 * scale)))
        draw.line([(hx + eye_dx - er_x + 4, eye_y), (hx + eye_dx + er_x - 4, eye_y)], fill=ink, width=max(5, int(6 * scale)))
    elif expr == "smug_snooze":
        draw.arc([hx - eye_dx - er_x, eye_y - 10, hx - eye_dx + er_x, eye_y + 18], start=10, end=170, fill=ink, width=max(5, int(6 * scale)))
        draw.arc([hx + eye_dx - er_x, eye_y - 10, hx + eye_dx + er_x, eye_y + 18], start=10, end=170, fill=ink, width=max(5, int(6 * scale)))
    elif expr == "sweat_grit":
        draw.line([(hx - eye_dx - 16, eye_y - 12), (hx - eye_dx + 12, eye_y), (hx - eye_dx - 16, eye_y + 12)], fill=ink, width=5)
        draw.line([(hx + eye_dx + 16, eye_y - 12), (hx + eye_dx - 12, eye_y), (hx + eye_dx + 16, eye_y + 12)], fill=ink, width=5)
        for sx, sy in [(hx - int(58 * scale), hy - int(44 * scale)), (hx + int(62 * scale), hy - int(36 * scale))]:
            draw.ellipse([sx - 6, sy - 9, sx + 6, sy + 9], fill=(165, 224, 255), outline=ink, width=2)
    else:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            # White sclera oval
            draw.ellipse([ex - er_x, eye_y - er_y, ex + er_x, eye_y + er_y], fill=(254, 254, 255), outline=ink, width=max(4, int(5 * scale)))
            # Bloodshot veins if shocked
            if expr == "bloodshot_shock":
                draw.line([(ex - er_x + 4, eye_y - 6), (ex - 8, eye_y - 2)], fill=(224, 52, 62), width=2)
                draw.line([(ex + er_x - 4, eye_y + 8), (ex + 8, eye_y + 3)], fill=(224, 52, 62), width=2)
            # Dark iris + white catchlight highlight
            pr = int(7 * scale) if expr == "bloodshot_shock" else int(9 * scale)
            px_c = ex + pupil_look_x
            draw.ellipse([px_c - pr, eye_y - pr, px_c + pr, eye_y + pr], fill=ink)
            draw.ellipse([px_c - pr + 2, eye_y - pr + 2, px_c - pr + 6, eye_y - pr + 6], fill=(255, 255, 255))

            # Eyelid cutoffs & tired under-eye bags
            if expr in ("skeptical_half_lid", "exhausted_half_lidded", "tired_bags"):
                draw.pieslice([ex - er_x, eye_y - er_y, ex + er_x, eye_y + er_y], start=180, end=360, fill=head_fill, outline=ink, width=max(4, int(5 * scale)))
            if expr == "tired_bags":
                draw.arc([ex - er_x + 2, eye_y + int(10 * scale), ex + er_x - 2, eye_y + er_y + int(12 * scale)], start=15, end=165, fill=(138, 134, 130), width=max(3, int(4 * scale)))
            elif expr == "maniacal_3am_grin":
                # Upturned happy-maniacal lower cheek push
                draw.pieslice([ex - er_x, eye_y + int(4 * scale), ex + er_x, eye_y + er_y + 4], start=0, end=180, fill=head_fill, outline=ink, width=4)

    # Independent Floating Eyebrows
    brow_y = eye_y - er_y - int(8 * scale)
    brow_w = max(5, int(6 * scale))
    if expr == "angry_brow":
        draw.line([(hx - eye_dx - 16, brow_y - 6), (hx - eye_dx + 14, brow_y + 8)], fill=ink, width=brow_w)
        draw.line([(hx + eye_dx + 16, brow_y - 6), (hx + eye_dx - 14, brow_y + 8)], fill=ink, width=brow_w)
    elif expr in ("guilty_puppy_eyes", "tired_bags"):
        draw.line([(hx - eye_dx - 16, brow_y + 6), (hx - eye_dx + 14, brow_y - 6)], fill=ink, width=brow_w)
        draw.line([(hx + eye_dx + 16, brow_y + 6), (hx + eye_dx - 14, brow_y - 6)], fill=ink, width=brow_w)
    elif expr in ("bloodshot_shock", "maniacal_3am_grin"):
        draw.arc([hx - eye_dx - 16, brow_y - 14, hx - eye_dx + 16, brow_y + 4], start=190, end=350, fill=ink, width=brow_w)
        draw.arc([hx + eye_dx - 16, brow_y - 14, hx + eye_dx + 16, brow_y + 4], start=190, end=350, fill=ink, width=brow_w)
    else:
        draw.line([(hx - eye_dx - 16, brow_y), (hx - eye_dx + 16, brow_y)], fill=ink, width=brow_w)
        draw.line([(hx + eye_dx - 16, brow_y), (hx + eye_dx + 16, brow_y)], fill=ink, width=brow_w)

    # 8. 4-Shape Lip-Sync Mouth Rig (Driven by Audio Amplitude + Expression)
    my = hy + int(34 * scale)
    effective_viseme = "gritted_teeth" if expr == "sweat_grit" else viseme

    if effective_viseme == "open_teeth":
        # D-shaped open talking mouth with upper white teeth & pink tongue
        mw, mh = int(28 * scale), int(24 * scale)
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, fill=(68, 22, 30), outline=ink, width=max(4, int(5 * scale)))
        # Upper teeth bar
        draw.rectangle([hx - mw + 6, my, hx + mw - 6, my + int(7 * scale)], fill=(252, 252, 255))
        # Pink tongue curve at bottom
        draw.pieslice([hx - int(14 * scale), my + int(8 * scale), hx + int(14 * scale), my + mh - 2], start=0, end=180, fill=(236, 122, 138))
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, outline=ink, width=max(4, int(5 * scale)))
    elif effective_viseme == "o_vowel":
        # Circular/oval O-shape for "Oh / What / Bro" vowels
        ow, oh = int(18 * scale), int(22 * scale)
        draw.ellipse([hx - ow, my - int(6 * scale), hx + ow, my + oh], fill=(68, 22, 30), outline=ink, width=max(4, int(5 * scale)))
    elif effective_viseme == "gritted_teeth":
        mx0, my0 = hx - int(28 * scale), my - int(6 * scale)
        mx1, my1 = hx + int(28 * scale), my + int(16 * scale)
        draw.rounded_rectangle([mx0, my0, mx1, my1], radius=8, fill=(252, 252, 255), outline=ink, width=4)
        for tx in range(mx0 + 12, mx1 - 6, 14):
            draw.line([(tx, my0), (tx, my1)], fill=ink, width=3)
    elif expr == "maniacal_3am_grin":
        mw, mh = int(34 * scale), int(26 * scale)
        draw.chord([hx - mw, my - mh, hx + mw, my + mh], start=0, end=180, fill=(252, 252, 255), outline=ink, width=max(4, int(5 * scale)))
        draw.line([(hx - mw + 6, my + int(10 * scale)), (hx + mw - 6, my + int(10 * scale))], fill=ink, width=3)
    elif expr == "bloodshot_shock":
        jaw_open = int((34 + math.sin(t * 24.0) * 6) * scale)
        draw.rounded_rectangle([hx - int(24 * scale), my - int(8 * scale), hx + int(24 * scale), my + jaw_open], radius=10, fill=(68, 22, 30), outline=ink, width=5)
    elif expr in ("smug_snooze", "confident_smirk"):
        draw.arc([hx - int(20 * scale), my - int(10 * scale), hx + int(26 * scale), my + int(12 * scale)], start=12, end=165, fill=ink, width=max(4, int(6 * scale)))
    elif expr in ("angry_brow", "guilty_puppy_eyes"):
        draw.arc([hx - int(20 * scale), my + int(2 * scale), hx + int(20 * scale), my + int(18 * scale)], start=190, end=350, fill=ink, width=max(4, int(6 * scale)))
    else:
        draw.line([(hx - int(22 * scale), my + int(4 * scale)), (hx + int(22 * scale), my + int(2 * scale))], fill=ink, width=max(4, int(6 * scale)))

    if prof["glasses"]:
        gr = int(28 * scale)
        draw.rectangle([hx - eye_dx - gr, eye_y - gr, hx - eye_dx + gr, eye_y + gr], outline=ink, width=max(4, int(6 * scale)))
        draw.rectangle([hx + eye_dx - gr, eye_y - gr, hx + eye_dx + gr, eye_y + gr], outline=ink, width=max(4, int(6 * scale)))
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=max(4, int(6 * scale)))

    # 9. Held Smartphone (At Ear during phone_call_ear, or Glowing in Hand during phone_scroll_lean)
    if holding_phone:
        px, py = phone_pos
        pw, ph = int(26 * scale), int(48 * scale)
        draw.rounded_rectangle([px - pw, py - ph, px + pw, py + ph], radius=10, fill=(26, 30, 40), outline=ink, width=4)
        if body_action == "phone_scroll_lean":
            draw.rounded_rectangle([px - pw + 5, py - ph + 8, px + pw - 5, py + ph - 8], radius=6, fill=(142, 224, 255))


def _draw_foreground_occlusion(draw, env_key, sc):
    """Draws blankets, desks, and dashboards IN FRONT OF characters' lower bodies in seated indoor scenes."""
    env = ENVIRONMENT_PRESETS.get(env_key, ENVIRONMENT_PRESETS["warm_desk_lamp"])
    ink = (18, 18, 22)
    is_night = _is_night_scene(sc)

    if env_key == "overcast_bedroom":
        blanket_col = (74, 86, 112) if is_night else env["surface"]
        sheet_col = (196, 204, 220) if is_night else (244, 246, 250)
        draw.rounded_rectangle([70, 1085, W - 70, 1580], radius=34, fill=blanket_col, outline=ink, width=8)
        draw.rounded_rectangle([70, 1085, W - 70, 1138], radius=18, fill=sheet_col, outline=ink, width=7)
    elif env_key == "midnight_car_cabin":
        draw.rounded_rectangle([60, 1095, W - 60, 1580], radius=42, fill=env["surface"], outline=ink, width=8)
        draw.ellipse([235, 1035, 475, 1275], outline=(12, 14, 18), width=18)
    elif env_key == "living_room_window":
        draw.rounded_rectangle([80, 1145, W - 80, 1520], radius=34, fill=env["surface"], outline=ink, width=8)
    elif env_key in ("warm_desk_lamp", "kitchen_counter"):
        draw.rectangle([0, 1130, W, H], fill=env["surface"])
        draw.line([(0, 1130), (W, 1130)], fill=ink, width=8)
        draw.polygon([(130, 1015), (230, 1015), (212, 1130), (148, 1130)], fill=(178, 92, 64), outline=ink)
        draw.ellipse([125, 915, 235, 1025], fill=(76, 142, 82), outline=ink, width=5)
        draw.rounded_rectangle([835, 1050, 915, 1130], radius=12, fill=env["accent_prop"], outline=ink, width=5)


def render_animated_stage_frame(bg_img, characters, env_key, sc, reel_mode, beat_idx, t, local_p, active_viseme):
    """Composites 24fps dressed characters (with shot-reverse-shot framing & lip-sync) onto the background."""
    frame = bg_img.copy()
    draw = ImageDraw.Draw(frame)

    expr = sc.get("expression", "skeptical_half_lid") if local_p < 0.45 else sc.get("end_expression", sc.get("expression", "skeptical_half_lid"))
    body_action = sc.get("body_action", "point_argue")
    speaker = (sc.get("speaker") or "").strip()
    framing = sc.get("shot_framing", "two_shot")
    count = max(1, min(4, len(characters)))

    if reel_mode == "spoken_skit" and framing == "speaker_closeup" and speaker in characters:
        # Shot-reverse-shot medium close-up on the active speaker (shows dressed torso + face + gesturing hands!)
        f_dir = 1 if characters.index(speaker) % 2 == 0 else -1
        _draw_dressed_character(draw, speaker, W // 2, 830, 1.24, expr, body_action, active_viseme, t, local_p, characters.index(speaker), facing_dir=f_dir)
    elif reel_mode == "visual_pov" and beat_idx == 2:
        _draw_dressed_character(draw, characters[0], W // 2, 850, 1.30, expr, body_action, "closed", t, local_p, 0, facing_dir=1)
    else:
        spacing = min(275, (W - 160) // count)
        start_x = (W // 2) - ((count - 1) * spacing) // 2
        scale = 1.02 if count == 1 else (0.94 if count == 2 else (0.80 if count == 3 else 0.72))
        for idx, name in enumerate(characters[:4]):
            cx = start_x + idx * spacing
            cy = 815 if env_key == "sidewalk_hangout" else (845 + (idx % 2) * 14)
            is_active_spk = (reel_mode == "spoken_skit" and name == speaker) or (reel_mode == "visual_pov" and idx == 0)
            char_expr = expr if is_active_spk else ("skeptical_half_lid" if reel_mode == "spoken_skit" else "tired_bags")
            char_act = body_action if is_active_spk else ("slouch_sigh" if body_action != "walk_stride" else "walk_stride")
            char_vis = active_viseme if (reel_mode == "spoken_skit" and name == speaker) else "closed"
            f_dir = 1 if idx == 0 else -1
            _draw_dressed_character(draw, name, cx, cy, scale, char_expr, char_act, char_vis, t, local_p, idx, facing_dir=f_dir)

    # Foreground occlusion for seated indoor scenes (never covers standing sidewalk shots)
    if env_key != "sidewalk_hangout" and body_action != "walk_stride":
        _draw_foreground_occlusion(draw, env_key, sc)

    return frame


# ==============================================================================
# 6. LYRIA / SYNTH MUSIC + SPOKEN DIALOGUE + SFX MIXER WITH SIDECHAIN DUCKING
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
        "-af", f"volume=0.72,afade=t=in:st=0:d=0.30,afade=t=out:st={max(0.5, duration_sec - 0.8):.3f}:d=0.8",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        env = math.sin(min(1.0, dt / 0.28) * math.pi)
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * env * 0.26
    if cue == "record_scratch":
        env = math.exp(-dt * 6.0)
        freq = 660.0 * math.exp(-dt * 5.2) + 95.0 * math.sin(dt * 95.0)
        return math.sin(2 * math.pi * freq * dt) * env * 0.40
    if cue == "vine_boom_sub":
        env = math.exp(-dt * 4.5)
        freq = 74.0 * math.exp(-dt * 1.7)
        return math.sin(2 * math.pi * freq * dt) * env * 0.50
    if cue == "alarm_buzz":
        pulse = 1.0 if (int(dt * 14) % 2 == 0) else 0.15
        env = math.exp(-dt * 3.0) * pulse
        return (math.sin(2 * math.pi * 880.0 * dt) + 0.5 * math.sin(2 * math.pi * 1320.0 * dt)) * env * 0.22
    if cue == "riser_hit":
        if dt < 0.35:
            return math.sin(2 * math.pi * (220 + 1300 * dt) * dt) * (dt / 0.35) * 0.26
        env = math.exp(-(dt - 0.35) * 7.5)
        return math.sin(2 * math.pi * 64.0 * dt) * env * 0.44
    env = math.exp(-dt * 15.0)
    return math.sin(2 * math.pi * 987.77 * dt) * env * 0.24


def build_director_audio(music_prompt, bpm, scenes, beat_starts, voice_tracks, duration_sec, final_wav):
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
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.065
                s = int(max(-0.9, min(0.9, val)) * 32767)
                frames.extend(struct.pack("<hh", s, s))
            wf.writeframes(frames)

    # Combine SFX cues + Spoken Dialogue Tracks into one foreground speech/SFX bus
    fg_wav = final_wav.parent / "director_fg.wav"
    sr = 48000
    total_samples = int(sr * duration_sec)
    fg_samples = [0.0] * (total_samples * 2)

    cues = [
        (beat_starts[i] + (0.10 if i == 0 else 0.0), scenes[i].get("sfx_cue", "pop_ding"))
        for i in range(len(scenes))
    ]
    for start_t, cue_name in cues:
        s0 = int(start_t * sr)
        s1 = min(total_samples, int((start_t + 0.62) * sr))
        for idx in range(s0, s1):
            val = _synth_cue_sample(cue_name, (idx / sr) - start_t)
            fg_samples[idx * 2] += val
            fg_samples[idx * 2 + 1] += val

    # Overlay spoken character WAVs at each beat start + 0.12s
    for i, v_path in enumerate(voice_tracks):
        if v_path and pathlib.Path(v_path).exists():
            with wave.open(str(v_path), "rb") as wf:
                raw = wf.readframes(wf.getnframes())
            v_ints = struct.unpack(f"<{len(raw) // 2}h", raw)
            offset_samp = int((beat_starts[i] + 0.12) * sr) * 2
            limit = min(len(v_ints), len(fg_samples) - offset_samp)
            for k in range(max(0, limit)):
                fg_samples[offset_samp + k] += (v_ints[k] / 32768.0) * 1.15

    with wave.open(str(fg_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        out_bytes = bytearray()
        for val in fg_samples:
            s = int(max(-0.95, min(0.95, val)) * 32767)
            out_bytes.extend(struct.pack("<h", s))
        wf.writeframes(out_bytes)

    # Sidechain-duck the music bed whenever characters speak or SFX hit
    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(fg_wav),
        "-filter_complex",
        "[1:a]asplit=2[fg_sc][fg_mix];"
        "[0:a][fg_sc]sidechaincompress=threshold=0.03:ratio=8:attack=12:release=240[ducked_bed];"
        "[ducked_bed][fg_mix]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# 7. CAMERA MOVEMENTS, MICRO-ANIMATED PROPS & DUAL-MODE CAPTIONS
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


def build_ambient_glow_mask(strength=0.13):
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
        elif env_fx in ("rain", "sparks", "confetti", "dust"):
            for p in particle_seeds:
                depth = p["depth"]
                spd = p["speed"] * (0.6 + 0.5 * depth)
                p_alpha = int(base_alpha * (0.45 + 0.55 * depth))
                if env_fx == "dust":
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


def draw_dual_mode_overlays(frame, top_hook, reel_mode, sc, beat_idx, total_beats, scene_t, beat_dur, t, handle):
    """Renders upper-third hook + ticking clock + either bold spoken subtitles (spoken_skit) or POV reaction card."""
    g1 = COLOR_GRADES.get(sc.get("start_grade", "warm_amber_desk"), COLOR_GRADES["warm_amber_desk"])
    g2 = COLOR_GRADES.get(sc.get("end_grade", "warm_amber_desk"), g1)
    prog = min(1.0, max(0.0, scene_t / max(0.1, beat_dur)))
    acc = _lerp_color(g1["accent"], g2["accent"], prog)
    c_bg = g2["card_bg"]
    c_fg = g2["card_fg"]

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

    # 2. Spoken Dialogue Subtitle (spoken_skit) OR Optional POV Caption (visual_pov)
    if reel_mode == "spoken_skit" and (sc.get("dialogue") or "").strip():
        spk = (sc.get("speaker") or "Phil").strip()
        dlg = sc["dialogue"].strip()
        spk_col = CAST_IDENTITY.get(spk, CAST_IDENTITY["Phil"])["shirt_color"]
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.16))
        cap_alpha = int(250 * cap_in)

        # Speaker Name Tag Pill above dialogue
        tag_font = _load_font(28)
        tag_text = spk.upper()
        tbbox = odraw.textbbox((0, 0), tag_text, font=tag_font)
        tw = (tbbox[2] - tbbox[0]) + 44
        th = 42
        tx0 = 112
        ty0 = 1320
        odraw.rounded_rectangle([tx0, ty0, tx0 + tw, ty0 + th], radius=16, fill=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), outline=(18, 18, 22, cap_alpha), width=4)
        odraw.text((tx0 + tw // 2, ty0 + th // 2), tag_text, font=tag_font, fill=(255, 255, 255, cap_alpha), anchor="mm")

        # Bold Outlined Spoken Dialogue Card
        dlg_font = _load_font(42)
        wrapped = textwrap.fill(f'"{dlg}"', width=28)
        lines = wrapped.split("\n")
        box_h = 44 + len(lines) * 54
        x0, y0 = 92, 1368
        x1, y1 = W - 92, y0 + box_h
        odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(18, 20, 28, min(244, cap_alpha)), outline=(spk_col[0], spk_col[1], spk_col[2], cap_alpha), width=4)
        odraw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=dlg_font, fill=(255, 255, 255, cap_alpha), anchor="mm", align="center", spacing=10)
    else:
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
    reel_mode = script_data.get("reel_mode", seed["reel_mode"])
    env_key = script_data.get("environment_key", seed["scenario"]["env"])

    bg_imgs = []
    for idx, sc in enumerate(scenes):
        bg_path = tmp_dir / f"bg_{idx}.png"
        _render_environment_background(env_key, sc, idx, bg_path)
        bg_imgs.append(Image.open(bg_path).convert("RGB"))

    beat_durations, voice_tracks, viseme_timelines = compute_beat_durations_and_voices(scenes, tmp_dir)
    beat_starts = []
    acc_t = 0.0
    for d in beat_durations:
        beat_starts.append(acc_t)
        acc_t += d
    total_dur = acc_t
    print(f"Rendered {reel_mode} timing ({total_dur:.2f}s total): {beat_durations}")

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

        frame = draw_dual_mode_overlays(
            frame=frame,
            top_hook=top_hook,
            reel_mode=reel_mode,
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
    print(f"Rendered Dressed Lip-Sync / POV Reel ({total_dur:.1f}s, {total_beats} beats): {out_mp4}")


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
        reel_mode = seed["reel_mode"]
        cast_descriptions = "\n".join(
            f"- {c}: {CAST_IDENTITY[c]['archetype']} | Visual: {CAST_IDENTITY[c]['visual']}"
            for c in seed["characters"]
        )

        if reel_mode == "spoken_skit":
            mode_instructions = (
                "### SPOKEN DIALOGUE SKIT RULES (VOICE ACTING + LIP-SYNC)\n"
                "1. EVERY BEAT HAS SPOKEN BANTER: Assign 'speaker' to one of the active characters and write crisp, natural spoken 'dialogue' (7 to 13 words max per beat) so two friends bounce jokes back and forth.\n"
                "2. SHOT-REVERSE-SHOT FRAMING: Alternate 'shot_framing' between 'two_shot' and 'speaker_closeup' so the camera cuts between friends talking.\n"
                "3. CONVERSATIONAL GESTURES: Use 'phone_call_ear', 'point_argue', 'shrug_palms', 'count_fingers', and 'temple_tap' in 'body_action'.\n"
                "4. REAL EYE ACTING: Use 'skeptical_half_lid', 'angry_brow', 'confident_smirk', 'sweat_grit', and 'bloodshot_shock'.\n"
            )
        else:
            mode_instructions = (
                "### VISUAL POV REEL RULES (MUSIC + SFX + REAL EYE ACTING)\n"
                "1. SHOW, DON'T OVER-WRITE: Set 'speaker': \"\" and 'dialogue': \"\". Put the hook in 'top_hook' and keep 'bottom_caption' ultra-short (0 to 7 words) or empty \"\" so facial acting & ticking clocks tell the joke.\n"
                "2. ESCALATING EYE & BODY ACTING: Progress expressions across the 4 beats (e.g. 'tired_bags' -> 'skeptical_half_lid' -> 'maniacal_3am_grin' -> 'bloodshot_shock') with 'sleep_breathe_toss', 'phone_scroll_lean', and 'shock_recoil'.\n"
            )

        prompt = (
            f"You are a 2D Webcomic Animation Director for {page['handle']}.\n"
            f"CHANNEL IDENTITY: {page['domain']}\n\n"
            "### MANDATORY CREATIVE DIRECTION BRIEF\n"
            f"- Reel Mode: {reel_mode}\n"
            f"- Cast Mode: {seed['cast_mode']} ({CAST_MODES[seed['cast_mode']]['desc']})\n"
            f"- Active Characters (NEVER CHANGE NAMES OR OUTFITS):\n{cast_descriptions}\n"
            f"- Upper-Third Hook Concept: {scen['hook']}\n"
            f"- Story Seed: {scen['story_seed']}\n"
            f"- Environment Key: {scen['env']} ({ENVIRONMENT_PRESETS[scen['env']]['desc']})\n"
            f"- Suggested Ticking Clock Progression: {scen['clocks']}\n"
            f"- Time of Day Context: {time_slot_vibe}\n"
            f"- Optional US Trends (only if natural): \n{trends}\n"
            f"- Previously Used Hooks (NEVER REPEAT):\n{recent_hooks}\n\n"
            f"{mode_instructions}\n"
            "### RETURN ONLY VALID JSON WITH THESE EXACT KEYS\n"
            "{\n"
            f'  "reel_mode": "{reel_mode}",\n'
            f'  "top_hook": "{scen["hook"]}",\n'
            f'  "environment_key": "{scen["env"]}",\n'
            f'  "setting_continuity": "{ENVIRONMENT_PRESETS[scen["env"]]["desc"]}",\n'
            '  "music_prompt": "Playful lo-fi pizzicato and indie guitar comedy underscore instrumental",\n'
            '  "music_bpm": 106,\n'
            '  "scenes": [\n'
            f'    {{"clock_label": "{scen["clocks"][0]}", "speaker": "{seed["characters"][0] if reel_mode == "spoken_skit" else ""}", "dialogue": "{"Yo where are you, we were supposed to leave ten minutes ago." if reel_mode == "spoken_skit" else ""}", "shot_framing": "two_shot", "bottom_caption": "", "expression": "tired_bags", "end_expression": "skeptical_half_lid", "body_action": "{"phone_call_ear" if reel_mode == "spoken_skit" else "sleep_breathe_toss"}", "prop_overlay": "none", "visual_prompt": "Beat 1 action, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "suburban_daylight_cel", "end_grade": "suburban_daylight_cel", "camera_move": "dolly_push_in", "transition_in": "hard_cut", "env_effect": "none", "sfx_cue": "pop_ding"}},\n'
            f'    {{"clock_label": "{scen["clocks"][1]}", "speaker": "{seed["characters"][-1] if reel_mode == "spoken_skit" else ""}", "dialogue": "{"Relax bro I am literally turning onto your street right now!" if reel_mode == "spoken_skit" else ""}", "shot_framing": "speaker_closeup", "bottom_caption": "{"Just one quick scroll." if reel_mode == "visual_pov" else ""}", "expression": "confident_smirk", "end_expression": "angry_brow", "body_action": "{"point_argue" if reel_mode == "spoken_skit" else "phone_scroll_lean"}", "prop_overlay": "none", "visual_prompt": "Beat 2 action, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "warm_amber_desk", "end_grade": "warm_amber_desk", "camera_move": "pan_follow_right", "transition_in": "whip_pan_left", "env_effect": "screen_glow", "sfx_cue": "whoosh"}},\n'
            f'    {{"clock_label": "{scen["clocks"][2]}", "speaker": "{seed["characters"][0] if reel_mode == "spoken_skit" else ""}", "dialogue": "{"Then why do I hear your microwave beeping in the background?!" if reel_mode == "spoken_skit" else ""}", "shot_framing": "speaker_closeup", "bottom_caption": "", "expression": "angry_brow", "end_expression": "{"sweat_grit" if reel_mode == "spoken_skit" else "maniacal_3am_grin"}", "body_action": "{"temple_tap" if reel_mode == "spoken_skit" else "phone_scroll_lean"}", "prop_overlay": "sweat_drops", "visual_prompt": "Beat 3 tight reaction, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "dim_night_phone_glow", "end_grade": "crimson_panic_shock", "camera_move": "snap_zoom_face", "transition_in": "smash_zoom_cut", "env_effect": "none", "sfx_cue": "record_scratch"}},\n'
            f'    {{"clock_label": "{scen["clocks"][3]}", "speaker": "{seed["characters"][-1] if reel_mode == "spoken_skit" else ""}", "dialogue": "{"That is my car pedestrian chime. See you in two!" if reel_mode == "spoken_skit" else ""}", "shot_framing": "two_shot", "bottom_caption": "{"Every single time." if reel_mode == "visual_pov" else ""}", "expression": "sweat_grit", "end_expression": "bloodshot_shock", "body_action": "{"shrug_palms" if reel_mode == "spoken_skit" else "shock_recoil"}", "prop_overlay": "none", "visual_prompt": "Beat 4 comedic reveal, NO text", "art_style_key": "{seed["art_style_key"]}", "start_grade": "crimson_panic_shock", "end_grade": "golden_morning_sunlight", "camera_move": "pull_back_reveal", "transition_in": "whip_pan_right", "env_effect": "none", "sfx_cue": "vine_boom_sub"}}\n'
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
            f"Beat {i+1} [{s.get('clock_label', '')}] ({s.get('speaker') or 'POV'} | {s.get('body_action', '')}): {s.get('dialogue') or s.get('bottom_caption', '')}"
            for i, s in enumerate(script_data["scenes"][:4])
        )
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"Mode: {script_data.get('reel_mode', reel_mode)}\nCast: {', '.join(seed['characters'])} ({seed['cast_mode']})\nEnvironment: {script_data.get('environment_key', '')}\nHook: {script_data.get('top_hook', '')}\n{full_story_text}\n\n{final_caption}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": seed["combo_key"],
            "reel_mode": script_data.get("reel_mode", reel_mode),
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
