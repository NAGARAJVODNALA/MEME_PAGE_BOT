import os
import sys
import math
import json
import time
import wave
import base64
import random
import shutil
import struct
import asyncio
import pathlib
import textwrap
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta, date
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
DEFAULT_IG_USER_ID = "17841476835986162"
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920
SS = 2  # 2x supersampling (2160x3840) so close-up zooms stay crisp

# ==============================================================================
# 6 BOYFRIEND / GIRLFRIEND COUPLE CAST (CONSISTENT LOOKS, OUTFITS & VOICES)
# ==============================================================================
COUPLE_PROFILES = [
    {
        "id": "tom_olivia",
        "label": "Tom & Olivia",
        "personality": "Dry-humored, outdoorsy boyfriend Tom and quick-witted, expressive girlfriend Olivia.",
        "him": {
            "name": "Tom",
            "skin": (246, 224, 206),
            "hair": (96, 64, 42),
            "hair_style": "cap",
            "cap_color": (154, 78, 56),
            "top_color": (240, 238, 232),
            "collar_color": (56, 78, 104),
            "pants_color": (48, 64, 88),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Puck",
            "edge_voice": "en-US-AndrewNeural",
        },
        "her": {
            "name": "Olivia",
            "skin": (248, 228, 212),
            "hair": (54, 38, 30),
            "hair_style": "bun",
            "top_color": (42, 48, 62),
            "skirt_color": (74, 96, 126),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AvaNeural",
        },
    },
    {
        "id": "dev_priya",
        "label": "Dev & Priya",
        "personality": "Charming, food-loving boyfriend Dev and sharp, warm, expressive girlfriend Priya.",
        "him": {
            "name": "Dev",
            "skin": (186, 136, 100),
            "hair": (26, 24, 28),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (62, 112, 88),
            "collar_color": (238, 226, 200),
            "pants_color": (42, 46, 56),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Orus",
            "edge_voice": "en-IN-PrabhatNeural",
        },
        "her": {
            "name": "Priya",
            "skin": (196, 146, 110),
            "hair": (26, 24, 28),
            "hair_style": "long_straight",
            "top_color": (192, 68, 64),
            "skirt_color": (234, 194, 110),
            "bindi": True,
            "hoops": True,
            "gemini_voice": "Kore",
            "edge_voice": "en-IN-NeerjaExpressiveNeural",
        },
    },
    {
        "id": "wei_lin",
        "label": "Wei & Lin",
        "personality": "Deadpan, logical boyfriend Wei and clever, playful, cozy-loving girlfriend Lin.",
        "him": {
            "name": "Wei",
            "skin": (240, 216, 194),
            "hair": (30, 30, 36),
            "hair_style": "side_part",
            "cap_color": None,
            "top_color": (48, 72, 104),
            "collar_color": (228, 234, 242),
            "pants_color": (44, 48, 58),
            "beard": False,
            "glasses": True,
            "gemini_voice": "Charon",
            "edge_voice": "en-SG-WayneNeural",
        },
        "her": {
            "name": "Lin",
            "skin": (244, 222, 202),
            "hair": (36, 32, 36),
            "hair_style": "sleek_bob",
            "top_color": (218, 134, 116),
            "skirt_color": (64, 72, 92),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Leda",
            "edge_voice": "en-SG-LunaNeural",
        },
    },
    {
        "id": "minho_jisoo",
        "label": "Minho & Jisoo",
        "personality": "Smooth, slightly dramatic boyfriend Minho and expressive, cute-but-fiery girlfriend Jisoo.",
        "him": {
            "name": "Minho",
            "skin": (242, 222, 204),
            "hair": (32, 30, 34),
            "hair_style": "comma_hair",
            "cap_color": None,
            "top_color": (196, 178, 156),
            "collar_color": (44, 46, 52),
            "pants_color": (42, 46, 54),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-BrianNeural",
        },
        "her": {
            "name": "Jisoo",
            "skin": (245, 226, 210),
            "hair": (42, 34, 34),
            "hair_style": "long_waves_bangs",
            "top_color": (166, 148, 206),
            "skirt_color": (52, 56, 70),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Zephyr",
            "edge_voice": "en-US-EmmaNeural",
        },
    },
    {
        "id": "noah_aaliyah",
        "label": "Noah & Aaliyah",
        "personality": "Enthusiastic, over-prepared boyfriend Noah and sharp, hilarious, affectionate girlfriend Aaliyah.",
        "him": {
            "name": "Noah",
            "skin": (244, 222, 204),
            "hair": (128, 92, 58),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (58, 72, 84),
            "collar_color": (226, 228, 232),
            "pants_color": (50, 58, 70),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Puck",
            "edge_voice": "en-US-ChristopherNeural",
        },
        "her": {
            "name": "Aaliyah",
            "skin": (124, 80, 56),
            "hair": (26, 22, 22),
            "hair_style": "afro_puffs",
            "top_color": (46, 128, 96),
            "skirt_color": (42, 46, 54),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AriaNeural",
        },
    },
    {
        "id": "elijah_imani",
        "label": "Elijah & Imani",
        "personality": "Smooth, sports-loving boyfriend Elijah and vibrant, quick-banter girlfriend Imani.",
        "him": {
            "name": "Elijah",
            "skin": (110, 70, 48),
            "hair": (24, 22, 22),
            "hair_style": "fade_lineup",
            "cap_color": None,
            "top_color": (142, 52, 60),
            "collar_color": (240, 234, 224),
            "pants_color": (40, 44, 52),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-DavisNeural",
        },
        "her": {
            "name": "Imani",
            "skin": (142, 92, 64),
            "hair": (26, 22, 22),
            "hair_style": "box_braids",
            "top_color": (218, 162, 66),
            "skirt_color": (52, 48, 56),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Kore",
            "edge_voice": "en-US-JennyNeural",
        },
    },
]

STORY_MOODS = [
    "Cozy",
    "Comedy",
    "Playful Fighting",
    "Cozy Cuddling",
    "Flirty Dinner",
    "Coffee/Lunch Dates",
    "Destination Trips",
    "Sad-to-Sweet Comfort",
    "Couple Gifting",
]

LOCATIONS = [
    "apartment_couch",
    "cafe_campus",
    "dinner_candlelight",
    "mountain_trek",
    "movie_living_room",
    "sports_hangout",
    "festival_diwali_home",
    "festival_thanksgiving_harvest",
    "festival_lunar_chuseok",
    "cookout_backyard",
]

EMOTIONS = [
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

EVERGREEN_TOPICS = [
    "University library study session turning into snack negotiations",
    "Weekend mountain trek where one overpacked and the other brought zero water",
    "Movie night debate: picking a film for 40 minutes until falling asleep",
    "Watching the big sports game together when one cheers for the rival team",
    "What to eat tonight when both say 'I don't care, you pick'",
    "Blanket hogging and thermostat wars at 2 AM",
    "Taking 50 photos at a scenic overlook to get one candid shot",
    "Splitting the bill vs sneaking the card to pay first on a lunch date",
    "Playful jealousy over a celebrity crush during a show",
    "Surprise couple gifting on a random Tuesday",
    "Cooking dinner together and setting off the smoke alarm",
    "Packing one carry-on bag for a weekend road trip",
    "Sunday dinner / backyard cookout crossover with another couple",
    "Double date coffee run where everyone orders overly complicated drinks",
]

HASHTAG_POOLS = {
    "broad": ["#funnyreels", "#relatablecontent", "#comedyreels", "#dailylaughs", "#relatable"],
    "couple": ["#couplehumor", "#funnycouple", "#couplelife", "#couplememes", "#relationshiphumor", "#couplegoals"],
    "situational": [
        "#datenightfail", "#splitthebill", "#whattoeat", "#movienight", "#collegelife",
        "#hikingcouple", "#coffeedate", "#cozyvibes", "#coupletravel", "#gameday",
    ],
}

ANNUAL_FESTIVALS = [
    (1, 1, "New Year's Day", "apartment_couch", "#newyearvibes"),
    (2, 14, "Valentine's Day", "dinner_candlelight", "#valentinesdate"),
    (2, 17, "Lunar New Year / Seollal", "festival_lunar_chuseok", "#lunarnewyear"),
    (3, 14, "White Day", "cafe_campus", "#whiteday"),
    (4, 14, "Black Day", "cafe_campus", "#blackday"),
    (5, 20, "520 Love Day", "dinner_candlelight", "#520day"),
    (6, 19, "Juneteenth", "cookout_backyard", "#juneteenth"),
    (8, 19, "Qixi Festival", "dinner_candlelight", "#qixifestival"),
    (9, 25, "Mid-Autumn Festival / Chuseok", "festival_lunar_chuseok", "#midautumnfestival"),
    (10, 31, "Halloween", "movie_living_room", "#halloweennight"),
    (11, 8, "Diwali", "festival_diwali_home", "#diwalivibes"),
    (11, 11, "Pepero Day / Singles' Day", "cafe_campus", "#peperoday"),
    (11, 26, "Thanksgiving", "festival_thanksgiving_harvest", "#thanksgivingdinner"),
    (12, 25, "Christmas", "apartment_couch", "#christmascozy"),
    (12, 26, "Kwanzaa", "cookout_backyard", "#kwanzaa"),
    (12, 31, "New Year's Eve", "apartment_couch", "#nye2026"),
]

_DISCOVERED_MODELS = None
_FALLBACK_DEPS_CHECKED = False


def build_https_url(host, path, query_params=None):
    query = urllib.parse.urlencode(query_params) if query_params else ""
    return urllib.parse.urlunparse(("https", host, path, "", query, ""))


def get_graph_host(token):
    if token.startswith(("IGA", "IGQ")):
        return "graph.instagram.com"
    return "graph.facebook.com"


def verify_runtime_environment():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY secret in GitHub Actions.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg binary not found in PATH.")


def verify_instagram_credentials(ig_id, token):
    if not token:
        raise RuntimeError("Missing IG_ACCESS_TOKEN secret in GitHub Actions.")
    if not ig_id:
        raise RuntimeError("Missing IG_USER_ID.")

    host = get_graph_host(token)
    check_url = build_https_url(
        host,
        f"/{GRAPH_VERSION}/{ig_id}",
        {"fields": "id,username", "access_token": token},
    )
    try:
        with urllib.request.urlopen(check_url, timeout=15) as resp:
            info = json.loads(resp.read().decode())
            uname = info.get("username", ig_id)
            print(f"Verified Instagram target: @{uname} (ID: {info.get('id')}) via {host}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram token/ID check failed ({host} HTTP {e.code}): {err_body}") from e


def discover_gemini_models():
    global _DISCOVERED_MODELS
    if _DISCOVERED_MODELS is not None:
        return _DISCOVERED_MODELS

    text_candidates = []
    tts_candidates = []
    try:
        url = build_https_url("generativelanguage.googleapis.com", "/v1beta/models", {"key": GEMINI_API_KEY})
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())

        for m in data.get("models", []):
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            name = m.get("name", "").removeprefix("models/")
            low = name.lower()
            if not name or any(x in low for x in ("embedding", "aqa", "imagen", "veo", "lyria", "robotics", "computer-use")):
                continue
            if "tts" in low:
                tts_candidates.append(name)
            elif "image" not in low:
                text_candidates.append(name)

        def _rank_text(m_name):
            low = m_name.lower()
            if "gemini-3" in low and "flash" in low:
                return 0
            if "gemini-2.5-flash" in low and "lite" not in low:
                return 1
            if "gemini-2.5-flash-lite" in low:
                return 2
            if "gemini-flash-latest" in low:
                return 3
            if "flash" in low:
                return 4
            return 5

        def _rank_tts(m_name):
            low = m_name.lower()
            if "flash" in low and "lite" not in low:
                return 0
            if "flash" in low:
                return 1
            return 2

        text_candidates.sort(key=_rank_text)
        tts_candidates.sort(key=_rank_tts)
        print(f"Discovered Gemini text models: {text_candidates[:5]}")
        if tts_candidates:
            print(f"Discovered Gemini TTS models: {tts_candidates}")
    except Exception as e:
        print(f"Model discovery skipped: {e}")

    if not text_candidates:
        text_candidates = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
    if not tts_candidates:
        tts_candidates = ["gemini-2.5-flash-preview-tts"]

    _DISCOVERED_MODELS = {"text": text_candidates[:6], "tts": tts_candidates}
    return _DISCOVERED_MODELS


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
            "Relatable boyfriend-and-girlfriend comedy & life stories across university, sports, trekking, "
            "movies, coffee/lunch dates, flirty dinners, cozy nights, and warm couple crossovers"
        ),
    }]


# ==============================================================================
# HISTORY & ORGANIC CAST / DATE-AWARE TOPIC PLANNER
# ==============================================================================
def load_story_history(slug, limit=150):
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


def find_nearby_festival(now_dt):
    today = now_dt.date()
    matches = []
    for month, day, name, loc, tag in ANNUAL_FESTIVALS:
        for yr in (today.year - 1, today.year, today.year + 1):
            try:
                f_date = date(yr, month, day)
                if abs((f_date - today).days) <= 5:
                    matches.append({"name": name, "location": loc, "tag": tag})
            except ValueError:
                continue
    return random.choice(matches) if matches else None


def plan_cast_and_premise(history_items, now_dt):
    last_lead = history_items[-1].get("lead_couple") if history_items else None
    lead_pool = [c for c in COUPLE_PROFILES if c["label"] != last_lead]
    lead_couple = random.choice(lead_pool or COUPLE_PROFILES)

    roll = random.random()
    num_couples = 1 if roll < 0.55 else (2 if roll < 0.85 else 3)
    other_couples = [c for c in COUPLE_PROFILES if c["id"] != lead_couple["id"]]
    guest_couples = random.sample(other_couples, k=num_couples - 1)
    selected_couples = [lead_couple] + guest_couples

    last_mood = history_items[-1].get("mood") if history_items else None
    mood_pool = [m for m in STORY_MOODS if m != last_mood]
    mood = random.choice(mood_pool or STORY_MOODS)

    nearby_fest = find_nearby_festival(now_dt)
    chosen_festival = nearby_fest if (nearby_fest and random.random() < 0.25) else None

    past_jokes = {str(h.get("core_joke", "")).lower() for h in history_items[-50:]}
    topic_pool = [t for t in EVERGREEN_TOPICS if not any(w in t.lower() for w in past_jokes if len(w) > 12)]
    suggested_topic = random.choice(topic_pool or EVERGREEN_TOPICS)

    return selected_couples, mood, chosen_festival, suggested_topic


# ==============================================================================
# SITCOM / WEB-SERIES SCRIPT GENERATOR (5-BEAT ARC, 25-32S TIGHT PACING)
# ==============================================================================
def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def _enforce_hashtag_diversity(raw_tags, festival_obj, history_items):
    prev_tags = set()
    if history_items:
        prev_tags = {t.lower() for t in history_items[-1].get("hashtags", [])}

    clean = []
    for t in (raw_tags or []):
        tag = str(t).strip().lower()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag.lstrip("#")
        tag = "".join(ch for ch in tag if ch.isalnum() or ch == "#")
        if len(tag) > 2 and tag not in clean:
            clean.append(tag)

    if festival_obj and festival_obj.get("tag") and festival_obj["tag"] not in clean:
        clean.append(festival_obj["tag"])

    fresh_count = sum(1 for t in clean if t not in prev_tags)
    candidates = (
        random.sample(HASHTAG_POOLS["broad"], 2)
        + random.sample(HASHTAG_POOLS["couple"], 3)
        + random.sample(HASHTAG_POOLS["situational"], 2)
    )
    for cand in candidates:
        if len(clean) >= 7 and fresh_count >= max(3, len(clean) // 2 + 1):
            break
        if cand not in clean and cand not in prev_tags:
            clean.append(cand)
            fresh_count += 1

    while len(clean) < 5:
        for cand in HASHTAG_POOLS["broad"] + HASHTAG_POOLS["couple"]:
            if cand not in clean:
                clean.append(cand)
                break
        else:
            break

    return clean[:8]


def _fallback_story_script(selected_couples, mood, festival_obj, history_items):
    lead = selected_couples[0]
    him = lead["him"]["name"]
    her = lead["her"]["name"]
    loc = festival_obj["location"] if festival_obj else (
        "mountain_trek" if "Destination" in mood else ("cafe_campus" if "Coffee" in mood else "apartment_couch")
    )
    beats = [
        {
            "arc_stage": "hook",
            "time_range": "0.0-6.0s",
            "location": loc,
            "action": f"{her} asks {him} what they should eat tonight.",
            "camera": "group_wide",
            "dialogue": [
                {"speaker": her, "text": "Babe, I am starving. Pick literally anywhere for dinner.", "emotion": "excited_wide"},
                {"speaker": him, "text": "Easy. Let's get spicy tacos right down the street.", "emotion": "smug_eyes_closed"},
            ],
        },
        {
            "arc_stage": "setup",
            "time_range": "6.0-12.5s",
            "location": loc,
            "action": f"{her} immediately shoots down the first idea.",
            "camera": "focus_speaker",
            "dialogue": [
                {"speaker": her, "text": "Mmm, no, I had Mexican food for lunch yesterday.", "emotion": "skeptical"},
                {"speaker": him, "text": "Okay, how about that new wood-fired pizza spot?", "emotion": "chill_smirk"},
            ],
        },
        {
            "arc_stage": "escalation",
            "time_range": "12.5-19.0s",
            "location": loc,
            "action": f"{her} rejects pizza and pasta too while claiming she does not care.",
            "camera": "focus_couple_0",
            "dialogue": [
                {"speaker": her, "text": "Too heavy. Honestly I don't care, you just decide!", "emotion": "pout_frown"},
                {"speaker": him, "text": "Alright, sushi it is. Grab your jacket.", "emotion": "deadpan"},
            ],
        },
        {
            "arc_stage": "twist",
            "time_range": "19.0-25.0s",
            "location": loc,
            "action": f"{her} admits she already ordered what she wanted ten minutes ago.",
            "camera": "focus_speaker",
            "dialogue": [
                {"speaker": her, "text": "Wait, don't leave. Our Thai food arrives in four minutes.", "emotion": "smug_eyes_closed"},
                {"speaker": him, "text": "You ordered before even asking me, didn't you?", "emotion": "shocked"},
            ],
        },
        {
            "arc_stage": "ending",
            "time_range": "25.0-30.0s",
            "location": loc,
            "action": "Both laugh as the delivery alert chimes.",
            "camera": "group_wide",
            "dialogue": [
                {"speaker": her, "text": "I just wanted to see if you would guess right!", "emotion": "soft_love_smile"},
            ],
        },
    ]
    hook_title = "Pick Anywhere For Dinner"
    tags = _enforce_hashtag_diversity([], festival_obj, history_items)
    return {
        "couples": [c["label"] for c in selected_couples],
        "mood": mood,
        "tone": "Snappy, natural sitcom banter",
        "festival": festival_obj["name"] if festival_obj else None,
        "hook_title": hook_title,
        "setting": loc,
        "beats": beats,
        "music_prompt": "Warm mellow lo-fi electric piano with soft acoustic groove",
        "caption": f"When 'you pick' really means 'guess what I already ordered.'",
        "hashtags": tags,
        "history_entry": {
            "hook": hook_title,
            "environment": loc,
            "core_joke": "Saying 'you pick dinner' after already ordering takeout",
        },
    }


def normalize_story_json(raw, selected_couples, mood, festival_obj, history_items):
    if not isinstance(raw, dict) or not isinstance(raw.get("beats"), list) or len(raw["beats"]) < 3:
        return _fallback_story_script(selected_couples, mood, festival_obj, history_items)

    valid_names = {}
    for c in selected_couples:
        valid_names[c["him"]["name"].lower()] = c["him"]["name"]
        valid_names[c["her"]["name"].lower()] = c["her"]["name"]
    default_him = selected_couples[0]["him"]["name"]
    default_her = selected_couples[0]["her"]["name"]

    valid_cams = {"group_wide", "focus_couple_0", "focus_couple_1", "focus_couple_2", "focus_speaker"}
    clean_beats = []
    used_locations = []

    for b_idx, b in enumerate(raw["beats"][:5]):
        if not isinstance(b, dict):
            continue
        loc = b.get("location") if b.get("location") in LOCATIONS else (used_locations[-1] if used_locations else "apartment_couch")
        if loc not in used_locations:
            if len(used_locations) >= 2:
                loc = used_locations[-1]
            else:
                used_locations.append(loc)

        # Guarantee dynamic camera cuts across beats (never stuck on group_wide all reel)
        default_cam_cycle = ["group_wide", "focus_speaker", "focus_couple_0", "focus_speaker", "group_wide"]
        cam = b.get("camera") if b.get("camera") in valid_cams else default_cam_cycle[min(4, b_idx)]
        if b_idx in (1, 2, 3) and cam == "group_wide":
            cam = "focus_speaker" if b_idx % 2 == 1 else "focus_couple_0"
        if cam == "focus_couple_1" and len(selected_couples) < 2:
            cam = "focus_speaker"
        if cam == "focus_couple_2" and len(selected_couples) < 3:
            cam = "focus_speaker"

        d_lines = []
        for idx, d in enumerate(b.get("dialogue") or []):
            if not isinstance(d, dict):
                continue
            sp_raw = str(d.get("speaker") or "").strip()
            sp = valid_names.get(sp_raw.lower(), default_him if idx % 2 == 0 else default_her)
            txt = " ".join(str(d.get("text") or d.get("line") or "").strip().split())
            if not txt:
                continue
            words = txt.split()
            if len(words) > 13:
                txt = " ".join(words[:13])
            emo = d.get("emotion") if d.get("emotion") in EMOTIONS else "chill_smirk"
            d_lines.append({"speaker": sp, "text": txt, "emotion": emo})

        if d_lines:
            clean_beats.append({
                "arc_stage": str(b.get("arc_stage") or ["hook", "setup", "escalation", "twist", "ending"][min(4, b_idx)]),
                "time_range": str(b.get("time_range") or f"{b_idx * 6}-{(b_idx + 1) * 6}s"),
                "location": loc,
                "action": str(b.get("action") or "Expressive conversation").strip(),
                "camera": cam,
                "dialogue": d_lines,
            })

    total_lines = sum(len(b["dialogue"]) for b in clean_beats)
    if len(clean_beats) < 3 or total_lines < 6:
        return _fallback_story_script(selected_couples, mood, festival_obj, history_items)

    hook_words = str(raw.get("hook_title") or "Couple Night Gone Sideways").strip().split()
    hook_title = " ".join(hook_words[:6]) if len(hook_words) >= 2 else "Couple Night Gone Sideways"

    hist_raw = raw.get("history_entry") if isinstance(raw.get("history_entry"), dict) else {}
    tags = _enforce_hashtag_diversity(raw.get("hashtags"), festival_obj, history_items)

    return {
        "couples": [c["label"] for c in selected_couples],
        "mood": mood,
        "tone": str(raw.get("tone") or "Snappy, natural sitcom banter").strip(),
        "festival": festival_obj["name"] if festival_obj else None,
        "hook_title": hook_title,
        "setting": clean_beats[0]["location"],
        "beats": clean_beats,
        "music_prompt": str(raw.get("music_prompt") or "Soft warm lo-fi electric piano with gentle acoustic pulse").strip(),
        "caption": str(raw.get("caption") or f"{hook_title} with {' & '.join(c['label'] for c in selected_couples)}.").strip(),
        "hashtags": tags,
        "history_entry": {
            "hook": str(hist_raw.get("hook") or hook_title).strip(),
            "environment": str(hist_raw.get("environment") or clean_beats[0]["location"]).strip(),
            "core_joke": str(hist_raw.get("core_joke") or hook_title).strip(),
        },
    }


def generate_story_with_gemini(page_cfg, selected_couples, mood, festival_obj, suggested_topic, history_items):
    past_hooks = [f"- {h.get('hook', '')} ({h.get('core_joke', '')})" for h in history_items[-45:] if h.get("hook")]
    past_block = "\n".join(past_hooks) if past_hooks else "- None yet"

    cast_desc = "\n".join(
        f"- Couple {i + 1}: {c['label']} (Boyfriend: {c['him']['name']}, Girlfriend: {c['her']['name']}) — {c['personality']}"
        for i, c in enumerate(selected_couples)
    )
    fest_line = (
        f"SEASONAL TIE-IN: {festival_obj['name']} (use location: {festival_obj['location']}). "
        "Keep it warm, natural, and relatable."
        if festival_obj
        else "FESTIVAL: null (everyday boyfriend-girlfriend slice-of-life comedy)."
    )

    prompt = (
        f"Write a crisp, genuinely funny 26-to-32-second animated sitcom Reel script for {page_cfg['handle']}.\n"
        "VOICE & DIALOGUE QUALITY RULES (CRITICAL):\n"
        "- Write like real 24-year-olds talking in 'Kim's Convenience' or 'Modern Family'—short, punchy, natural spoken English.\n"
        "- NEVER use weird robotic/academic words (no 'structural integrity', no 'seasonal vegetable management', no random celebrity/sports names).\n"
        "- Keep a clear, logical setup -> escalation -> punchline that anyone understands in 2 seconds.\n\n"
        f"CAST IN THIS REEL:\n{cast_desc}\n\n"
        f"MOOD: {mood}\n"
        f"{fest_line}\n"
        f"SITUATION IDEA: {suggested_topic}\n\n"
        "ALREADY USED JOKES (NEVER REPEAT):\n"
        f"{past_block}\n\n"
        "STRUCTURE & TIMING:\n"
        "1. Exactly 5 beats: hook, setup, escalation, twist, ending.\n"
        "2. Exactly 8 to 9 total spoken lines across the 5 beats (6 to 11 words per line) so the spoken Reel runs 26–32 seconds.\n"
        "3. Use 1 location across all beats (or max 2) from: apartment_couch, cafe_campus, dinner_candlelight, mountain_trek, movie_living_room, sports_hangout, festival_diwali_home, festival_thanksgiving_harvest, festival_lunar_chuseok, cookout_backyard.\n"
        "4. Alternate camera cuts: beat 0 'group_wide', beat 1 'focus_speaker', beat 2 'focus_couple_0', beat 3 'focus_speaker', beat 4 'group_wide'.\n\n"
        "Return ONLY valid JSON with exact keys:\n"
        "- couples: list of couple labels\n"
        "- mood: string\n"
        "- tone: string\n"
        "- festival: string or null\n"
        "- hook_title: bold 3-to-5-word hook title\n"
        "- setting: primary location string\n"
        "- beats: list of 5 objects with { arc_stage, time_range, location, action, camera, dialogue: [{ speaker, text, emotion }] }\n"
        "  Valid emotion: chill_smirk, smug_eyes_closed, deadpan, excited_wide, skeptical, exasperated, shocked, pout_frown, soft_love_smile\n"
        "- music_prompt: description of soft lo-fi / romantic background track\n"
        "- caption: one-line relatable Instagram caption\n"
        "- hashtags: list of 5-8 hashtags\n"
        "- history_entry: { hook, environment, core_joke }"
    )

    for model in discover_gemini_models()["text"]:
        url = build_https_url(
            "generativelanguage.googleapis.com",
            f"/v1beta/models/{model}:generateContent",
            {"key": GEMINI_API_KEY},
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
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
            with urllib.request.urlopen(req, timeout=50) as resp:
                data = json.loads(resp.read().decode())
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _extract_json_object(raw_text)
                script = normalize_story_json(parsed, selected_couples, mood, festival_obj, history_items)
                print(f"Generated 5-beat story ({script['couples']} | {mood}) via {model}: {script['hook_title']}")
                return script
        except urllib.error.HTTPError as e:
            print(f"Gemini ({model}) skipped: HTTP {e.code}")
        except Exception as e:
            print(f"Gemini ({model}) skipped: {e}")

    print("Using fallback sitcom couple script.")
    return _fallback_story_script(selected_couples, mood, festival_obj, history_items)


# ==============================================================================
# REAL HUMAN VOICES (CLEAN DIALOGUE ONLY -> 1:1 LIP & CAPTION SYNC)
# ==============================================================================
def _ensure_fallback_tts_packages():
    global _FALLBACK_DEPS_CHECKED
    if _FALLBACK_DEPS_CHECKED:
        return
    _FALLBACK_DEPS_CHECKED = True
    try:
        import edge_tts  # noqa: F401
        import gtts  # noqa: F401
    except ImportError:
        print("Installing fallback TTS packages (edge-tts, gtts)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "edge-tts", "gtts"],
            check=False,
        )


def _synthesize_gemini_tts(line_text, char_cfg, out_wav):
    tts_models = discover_gemini_models()["tts"]
    last_err = None
    time.sleep(1.5)

    for attempt_round in range(3):
        if attempt_round > 0:
            wait_sec = 10 * attempt_round
            print(f"Gemini TTS rate-limited; waiting {wait_sec}s before retry {attempt_round}/2...")
            time.sleep(wait_sec)

        saw_retryable = False
        for tts_model in tts_models:
            url = build_https_url(
                "generativelanguage.googleapis.com",
                f"/v1beta/models/{tts_model}:generateContent",
                {"key": GEMINI_API_KEY},
            )
            # CRITICAL: Pass ONLY line_text so Gemini TTS never speaks stage directions aloud!
            payload = {
                "contents": [{"parts": [{"text": line_text}]}],
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
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode())

                parts = data["candidates"][0]["content"]["parts"]
                inline = next(p["inlineData"] for p in parts if "inlineData" in p)
                raw_bytes = base64.b64decode(inline["data"])
                mime_type = inline.get("mimeType", "").lower()

                raw_file = out_wav.with_suffix(".raw_gem")
                raw_file.write_bytes(raw_bytes)
                if "pcm" in mime_type or "l16" in mime_type or raw_bytes[:4] not in (b"RIFF", b"ID3\x03", b"OggS"):
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
                return tts_model
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code} on {tts_model}"
                if e.code in (429, 500, 502, 503, 504):
                    saw_retryable = True
                    time.sleep(1.5)
            except Exception as e:
                last_err = str(e)

        if not saw_retryable:
            break

    raise RuntimeError(last_err or "Gemini TTS unavailable")


async def _synthesize_edge_tts_async(text, voice, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+5%")
    await comm.save(str(out_mp3))


def _synthesize_gtts_fallback(text, is_male, out_wav):
    from gtts import gTTS
    mp3_path = out_wav.with_suffix(".gtts.mp3")
    gTTS(text=text, lang="en", slow=False).save(str(mp3_path))
    pitch_factor = 0.88 if is_male else 1.08
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


def _synthesize_offline_last_resort(text, is_male, out_wav):
    espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if espeak_bin:
        raw_espeak = out_wav.with_suffix(".espeak.wav")
        voice_flag = "en-us+m3" if is_male else "en-us+f3"
        subprocess.run(
            [espeak_bin, "-v", voice_flag, "-s", "160", "-w", str(raw_espeak), text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_espeak), "-ar", "48000", "-ac", "1", str(out_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    dur = max(1.6, min(4.2, len(text.split()) * 0.34))
    _write_silence_wav(out_wav, 48000, dur)


def synthesize_character_voice(line_text, char_cfg, is_male, tmp_dir, idx):
    raw_wav = tmp_dir / f"line_{idx}_raw.wav"
    try:
        used_model = _synthesize_gemini_tts(line_text, char_cfg, raw_wav)
        if raw_wav.exists() and raw_wav.stat().st_size > 4000:
            print(f"Line {idx} ({char_cfg['name']}): {used_model} ({char_cfg['gemini_voice']})")
            return raw_wav
    except Exception as e:
        print(f"Line {idx} Gemini TTS skipped ({e}), trying Edge-TTS...")

    _ensure_fallback_tts_packages()

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
            print(f"Line {idx} ({char_cfg['name']}): Edge-TTS ({char_cfg['edge_voice']})")
            return raw_wav
    except Exception as e:
        print(f"Line {idx} Edge-TTS skipped ({e}), trying gTTS...")

    try:
        _synthesize_gtts_fallback(line_text, is_male, raw_wav)
        if raw_wav.exists() and raw_wav.stat().st_size > 4000:
            print(f"Line {idx} ({char_cfg['name']}): gTTS fallback")
            return raw_wav
    except Exception as e:
        print(f"Line {idx} gTTS skipped ({e}), using offline voice fallback...")

    _synthesize_offline_last_resort(line_text, is_male, raw_wav)
    print(f"Line {idx} ({char_cfg['name']}): offline fallback")
    return raw_wav


def _write_silence_wav(path, sr, dur):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * int(sr * dur))


def _synthesize_procedural_lofi_bed(music_prompt, mood, total_dur, sr, out_wav):
    low = f"{music_prompt} {mood}".lower()
    if any(k in low for k in ("romantic", "flirty", "dinner", "love", "sweet")):
        chords = [
            (174.61, 220.00, 261.63, 329.63),
            (164.81, 196.00, 246.94, 293.66),
            (146.83, 174.61, 220.00, 261.63),
            (130.81, 164.81, 196.00, 246.94),
        ]
        bar_sec = 2.4
    elif any(k in low for k in ("comedy", "upbeat", "sports", "cookout", "party")):
        chords = [
            (261.63, 329.63, 392.00, 493.88),
            (220.00, 261.63, 329.63, 392.00),
            (174.61, 220.00, 261.63, 329.63),
            (196.00, 246.94, 293.66, 329.63),
        ]
        bar_sec = 1.8
    else:
        chords = [
            (146.83, 185.00, 220.00, 277.18),
            (123.47, 146.83, 185.00, 220.00),
            (196.00, 246.94, 293.66, 369.99),
            (220.00, 277.18, 329.63, 369.99),
        ]
        bar_sec = 2.2

    total_samples = int(sr * total_dur)
    bar_samples = int(sr * bar_sec)
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(total_samples):
            t = i / sr
            bar_idx = (i // bar_samples) % len(chords)
            bar_pos = (i % bar_samples) / float(bar_samples)
            env = min(1.0, bar_pos * 14.0) * math.exp(-bar_pos * 1.15)
            chord = chords[bar_idx]
            val = 0.0
            for idx_n, freq in enumerate(chord):
                detune = 1.0 + (0.0015 if idx_n % 2 == 0 else -0.0015)
                val += math.sin(2.0 * math.pi * freq * detune * t) * 0.22
                val += math.sin(4.0 * math.pi * freq * t) * 0.04
            val += math.sin(2.0 * math.pi * (chord[0] * 0.5) * t) * 0.18
            sample_val = val * env * 0.34
            s_l = int(max(-0.85, min(0.85, sample_val * (1.0 + 0.05 * math.sin(t * 1.3)))) * 32767)
            s_r = int(max(-0.85, min(0.85, sample_val * (1.0 - 0.05 * math.sin(t * 1.3)))) * 32767)
            buf.extend(struct.pack("<hh", s_l, s_r))
        wf.writeframes(buf)


def build_audio_and_timeline(script, selected_couples, tmp_dir):
    sr = 48000
    char_lookup = {}
    for c_idx, c in enumerate(selected_couples):
        char_lookup[c["him"]["name"]] = (c["him"], True, c_idx)
        char_lookup[c["her"]["name"]] = (c["her"], False, c_idx)

    flat_turns = []
    for beat in script["beats"]:
        for d in beat["dialogue"]:
            flat_turns.append({
                "arc_stage": beat["arc_stage"],
                "location": beat["location"],
                "camera": beat["camera"],
                "speaker": d["speaker"],
                "text": d["text"],
                "emotion": d["emotion"],
            })

    timeline = []
    padded_wavs = []
    cursor = 0.30

    lead_wav = tmp_dir / "lead.wav"
    _write_silence_wav(lead_wav, sr, cursor)
    padded_wavs.append(lead_wav)

    for idx, turn in enumerate(flat_turns):
        char_cfg, is_male, couple_idx = char_lookup.get(
            turn["speaker"], (selected_couples[0]["him"], True, 0)
        )
        raw_wav = synthesize_character_voice(turn["text"], char_cfg, is_male, tmp_dir, idx)
        padded_wav = tmp_dir / f"line_{idx}_pad.wav"

        with wave.open(str(raw_wav), "r") as wf:
            frames_bytes = wf.readframes(wf.getnframes())
            samples = [int.from_bytes(frames_bytes[i:i + 2], "little", signed=True) for i in range(0, len(frames_bytes), 2)]

        # Trim trailing TTS silence so caption timing matches actual spoken words
        while len(samples) > sr // 4 and abs(samples[-1]) < 180:
            samples.pop()
        trimmed_bytes = b"".join(int(s).to_bytes(2, "little", signed=True) for s in samples)

        speech_dur = len(samples) / sr
        pause_after = 0.70 if idx == len(flat_turns) - 1 else 0.20
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
            wf.writeframes(trimmed_bytes + (b"\x00\x00" * int(sr * pause_after)))

        padded_wavs.append(padded_wav)
        timeline.append({
            **turn,
            "couple_idx": couple_idx,
            "is_male": is_male,
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

    music_wav = tmp_dir / "music_bed.wav"
    _synthesize_procedural_lofi_bed(script["music_prompt"], script["mood"], cursor + 0.4, sr, music_wav)

    final_wav = tmp_dir / "final_audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_wav),
            "-i", str(music_wav),
            "-filter_complex",
            "[0:a]acompressor=threshold=-18dB:ratio=2.4:attack=15:release=120,volume=1.22,asplit=2[v_mix][v_sc];"
            "[1:a]volume=0.38[m_raw];"
            "[m_raw][v_sc]sidechaincompress=threshold=0.015:ratio=9:attack=35:release=320[m_ducked];"
            "[v_mix][m_ducked]amix=inputs=2:duration=first:normalize=0[out]",
            "-map", "[out]", "-ar", str(sr), "-ac", "2", str(final_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return timeline, cursor, final_wav

# ==============================================================================
# REMOTION SPRING PHYSICS, LAYERED BACKGROUNDS & EXPRESSIVE CHARACTERS
# ==============================================================================
def remotion_spring(frame, fps=FPS, damping=12.0, stiffness=200.0, mass=0.5):
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


def _quad_bezier(p0, p1, p2, steps=14):
    pts = []
    for i in range(steps + 1):
        u = i / float(steps)
        inv = 1.0 - u
        x = int(inv * inv * p0[0] + 2 * inv * u * p1[0] + u * u * p2[0])
        y = int(inv * inv * p0[1] + 2 * inv * u * p1[1] + u * u * p2[1])
        pts.append((x, y))
    return pts


def _draw_vertical_gradient(draw, x0, y0, x1, y1, top_rgb, bot_rgb):
    h = max(1, y1 - y0)
    for step in range(0, h, 4):
        u = step / float(h)
        col = (
            int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * u),
            int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * u),
            int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * u),
        )
        draw.rectangle([x0, y0 + step, x1, min(y1, y0 + step + 4)], fill=col)


def _draw_potted_plant(draw, x, floor_y):
    ink = (26, 28, 34)
    draw.polygon(
        [((x - 36) * SS, (floor_y - 78) * SS), ((x + 36) * SS, (floor_y - 78) * SS),
         ((x + 26) * SS, floor_y * SS), ((x - 26) * SS, floor_y * SS)],
        fill=(188, 102, 72),
        outline=ink,
    )
    for dx, dy, rx, ry, col in [
        (-24, -108, 22, 34, (68, 134, 88)),
        (22, -104, 22, 32, (58, 118, 78)),
        (0, -126, 24, 40, (82, 152, 102)),
    ]:
        draw.ellipse(
            [(x + dx - rx) * SS, (floor_y + dy - ry) * SS, (x + dx + rx) * SS, (floor_y + dy + ry) * SS],
            fill=col,
            outline=ink,
            width=5 * SS,
        )


def _draw_curved_sleeve_arm(draw, shoulder, elbow, wrist, sleeve_col, skin_col, width_px):
    ink = (24, 24, 30)
    pts = _quad_bezier(shoulder, elbow, wrist, steps=14)
    draw.line(pts, fill=ink, width=width_px + 10 * SS, joint="curve")
    draw.line(pts, fill=sleeve_col, width=width_px, joint="curve")
    draw.ellipse(
        [wrist[0] - width_px // 2, wrist[1] - width_px // 2, wrist[0] + width_px // 2, wrist[1] + width_px // 2],
        fill=skin_col,
        outline=ink,
        width=4 * SS,
    )


def _draw_cartoon_hand(draw, x, y, angle_deg, skin_col, spread=1.0, scale=1.0):
    ink = (24, 24, 30)
    r = int(14 * scale * SS)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=skin_col, outline=ink, width=max(4 * SS, int(5 * scale * SS)))
    rad = math.radians(angle_deg)
    for f_off in (-0.42 * spread, -0.14 * spread, 0.14 * spread, 0.42 * spread):
        fa = rad + f_off
        fx = x + int(math.cos(fa) * 20 * scale * SS)
        fy = y + int(math.sin(fa) * 20 * scale * SS)
        draw.line([(x, y), (fx, fy)], fill=ink, width=max(4 * SS, int(5 * scale * SS)))


def render_location_background(location, out_bg_path):
    bw, bh = W * SS, H * SS
    ink = (26, 28, 34)
    img = Image.new("RGB", (bw, bh), (242, 232, 218))
    draw = ImageDraw.Draw(img)

    if location == "mountain_trek":
        _draw_vertical_gradient(draw, 0, 0, bw, 960 * SS, (96, 158, 224), (252, 198, 146))
        draw.ellipse([410 * SS, 470 * SS, 670 * SS, 730 * SS], fill=(255, 244, 186))
        draw.polygon([(0, 940 * SS), (280 * SS, 590 * SS), (560 * SS, 940 * SS)], fill=(104, 118, 152), outline=ink)
        draw.polygon([(420 * SS, 940 * SS), (760 * SS, 550 * SS), (bw, 940 * SS)], fill=(86, 102, 138), outline=ink)
        draw.polygon([(280 * SS, 590 * SS), (225 * SS, 660 * SS), (275 * SS, 648 * SS), (335 * SS, 660 * SS)], fill=(250, 252, 255))
        draw.polygon([(760 * SS, 550 * SS), (695 * SS, 630 * SS), (755 * SS, 618 * SS), (825 * SS, 630 * SS)], fill=(250, 252, 255))
        _draw_vertical_gradient(draw, 0, 920 * SS, bw, 1150 * SS, (92, 156, 98), (64, 124, 74))
        for tx in (110, 200, 880, 970):
            draw.polygon([(tx * SS, 780 * SS), ((tx - 48) * SS, 935 * SS), ((tx + 48) * SS, 935 * SS)], fill=(44, 92, 58), outline=ink)
        _draw_vertical_gradient(draw, 0, 1140 * SS, bw, bh, (214, 188, 152), (178, 150, 116))

    elif location == "cafe_campus":
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, (246, 234, 214), (226, 208, 184))
        draw.rounded_rectangle([80 * SS, 290 * SS, 620 * SS, 820 * SS], radius=16 * SS, fill=(176, 222, 244), outline=(92, 64, 44), width=10 * SS)
        draw.ellipse([160 * SS, 620 * SS, 420 * SS, 815 * SS], fill=(108, 172, 112))
        draw.line([(350 * SS, 290 * SS), (350 * SS, 820 * SS)], fill=(92, 64, 44), width=8 * SS)
        draw.rounded_rectangle([675 * SS, 320 * SS, 1005 * SS, 740 * SS], radius=16 * SS, fill=(38, 46, 52), outline=(126, 86, 54), width=10 * SS)
        for ly, col in [(395, (255, 224, 130)), (465, (244, 240, 232)), (535, (186, 234, 212)), (605, (244, 240, 232))]:
            draw.line([(720 * SS, ly * SS), (960 * SS, ly * SS)], fill=col, width=7 * SS)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (164, 122, 86), (124, 88, 58))
        _draw_potted_plant(draw, 115, 1140)

    elif location == "dinner_candlelight":
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, (36, 28, 52), (68, 42, 64))
        draw.rounded_rectangle([120 * SS, 260 * SS, 960 * SS, 860 * SS], radius=32 * SS, fill=(48, 38, 68), outline=(112, 82, 104), width=8 * SS)
        for bx, by, br, col in [(240, 390, 26, (255, 206, 118)), (440, 340, 20, (255, 175, 125)), (680, 420, 30, (255, 215, 135)), (840, 360, 22, (255, 190, 140))]:
            draw.ellipse([(bx - br) * SS, (by - br) * SS, (bx + br) * SS, (by + br) * SS], fill=col)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (74, 48, 40), (48, 30, 26))

    elif location == "festival_diwali_home":
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, (252, 216, 162), (236, 178, 122))
        for gx in range(90, W, 180):
            draw.arc([gx * SS, 220 * SS, (gx + 180) * SS, 370 * SS], start=0, end=180, fill=(244, 128, 24), width=16 * SS)
            draw.ellipse([(gx + 80) * SS, 352 * SS, (gx + 100) * SS, 376 * SS], fill=(255, 238, 120))
        draw.rounded_rectangle([180 * SS, 380 * SS, 900 * SS, 1130 * SS], radius=140 * SS, fill=(224, 164, 108), outline=(168, 86, 38), width=10 * SS)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (168, 112, 72), (126, 80, 48))

    elif location == "festival_thanksgiving_harvest":
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, (248, 226, 196), (228, 192, 152))
        draw.rounded_rectangle([120 * SS, 320 * SS, 460 * SS, 760 * SS], radius=16 * SS, fill=(255, 214, 156), outline=(112, 74, 46), width=10 * SS)
        draw.line([(290 * SS, 320 * SS), (290 * SS, 760 * SS)], fill=(112, 74, 46), width=8 * SS)
        draw.arc([80 * SS, 230 * SS, 1000 * SS, 400 * SS], start=0, end=180, fill=(196, 82, 38), width=14 * SS)
        for lx, col in [(220, (226, 126, 36)), (390, (184, 58, 42)), (540, (234, 162, 46)), (710, (184, 58, 42)), (860, (226, 126, 36))]:
            draw.ellipse([(lx - 18) * SS, 375 * SS, (lx + 18) * SS, 405 * SS], fill=col)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (158, 112, 74), (118, 80, 50))
        _draw_potted_plant(draw, 955, 1140)

    elif location == "festival_lunar_chuseok":
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, (246, 224, 198), (226, 196, 166))
        for lx in (240, 540, 840):
            draw.line([(lx * SS, 0), (lx * SS, 290 * SS)], fill=ink, width=5 * SS)
            draw.ellipse([(lx - 48) * SS, 285 * SS, (lx + 48) * SS, 395 * SS], fill=(214, 48, 48), outline=(242, 192, 64), width=6 * SS)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (166, 124, 86), (124, 88, 58))

    elif location == "cookout_backyard":
        _draw_vertical_gradient(draw, 0, 0, bw, 980 * SS, (124, 196, 244), (206, 236, 252))
        draw.arc([40 * SS, 230 * SS, 1040 * SS, 400 * SS], start=0, end=180, fill=ink, width=6 * SS)
        for bx in range(130, 980, 115):
            draw.ellipse([(bx - 12) * SS, 375 * SS, (bx + 12) * SS, 402 * SS], fill=(255, 238, 146), outline=ink, width=3 * SS)
        _draw_vertical_gradient(draw, 0, 980 * SS, bw, 1145 * SS, (96, 174, 88), (74, 142, 68))
        _draw_vertical_gradient(draw, 0, 1145 * SS, bw, bh, (204, 192, 176), (168, 156, 142))

    elif location in ("movie_living_room", "sports_hangout"):
        top_c = (44, 54, 78) if location == "movie_living_room" else (232, 224, 212)
        bot_c = (66, 78, 106) if location == "movie_living_room" else (212, 202, 188)
        _draw_vertical_gradient(draw, 0, 0, bw, 1130 * SS, top_c, bot_c)
        screen_col = (112, 172, 238) if location == "movie_living_room" else (76, 168, 88)
        draw.rounded_rectangle([240 * SS, 320 * SS, 840 * SS, 660 * SS], radius=18 * SS, fill=screen_col, outline=ink, width=9 * SS)
        _draw_vertical_gradient(draw, 0, 1130 * SS, bw, bh, (148, 114, 84), (112, 82, 58))
        draw.rounded_rectangle([110 * SS, 800 * SS, 970 * SS, 1190 * SS], radius=42 * SS, fill=(98, 124, 112), outline=ink, width=8 * SS)

    else:
        # Warm, cozy apartment living room with sunlit window, fairy lights, art & sofa
        _draw_vertical_gradient(draw, 0, 0, bw, 1135 * SS, (244, 232, 214), (224, 206, 182))
        draw.arc([60 * SS, 230 * SS, 1020 * SS, 380 * SS], start=0, end=180, fill=(116, 94, 76), width=5 * SS)
        for bx in range(140, 960, 120):
            draw.ellipse([(bx - 11) * SS, 360 * SS, (bx + 11) * SS, 384 * SS], fill=(255, 232, 138))
        draw.rounded_rectangle([90 * SS, 390 * SS, 355 * SS, 695 * SS], radius=12 * SS, fill=(182, 222, 242), outline=(104, 78, 58), width=9 * SS)
        draw.line([(222 * SS, 390 * SS), (222 * SS, 695 * SS)], fill=(104, 78, 58), width=7 * SS)
        draw.rounded_rectangle([740 * SS, 410 * SS, 975 * SS, 645 * SS], radius=12 * SS, fill=(248, 242, 232), outline=(124, 88, 62), width=8 * SS)
        draw.ellipse([795 * SS, 465 * SS, 920 * SS, 590 * SS], fill=(236, 146, 112))
        _draw_vertical_gradient(draw, 0, 1135 * SS, bw, bh, (172, 132, 96), (132, 96, 66))
        draw.rounded_rectangle([110 * SS, 795 * SS, 970 * SS, 1190 * SS], radius=42 * SS, fill=(118, 148, 116), outline=ink, width=8 * SS)
        draw.rounded_rectangle([155 * SS, 1015 * SS, 925 * SS, 1150 * SS], radius=24 * SS, fill=(138, 168, 134), outline=ink, width=7 * SS)
        _draw_potted_plant(draw, 95, 1145)

    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _draw_mouth(draw, hx, hy, scale, expr, mouth_open):
    ink = (24, 24, 30)
    mw = int(24 * scale * SS)
    if mouth_open > 0.12:
        mh = int((9 + 26 * mouth_open) * scale * SS)
        draw.ellipse(
            [hx - mw, hy + int(22 * scale * SS), hx + mw, hy + int(22 * scale * SS) + mh],
            fill=(176, 56, 64),
            outline=ink,
            width=max(4 * SS, int(5 * scale * SS)),
        )
        if mouth_open > 0.42:
            draw.chord(
                [hx - mw + 4 * SS, hy + int(25 * scale * SS), hx + mw - 4 * SS, hy + int(22 * scale * SS) + mh],
                start=15,
                end=165,
                fill=(240, 122, 128),
            )
    else:
        if expr in ("chill_smirk", "smug_eyes_closed", "excited_wide", "soft_love_smile"):
            draw.arc(
                [hx - int(23 * scale * SS), hy + int(16 * scale * SS), hx + int(25 * scale * SS), hy + int(43 * scale * SS)],
                start=10,
                end=170,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        elif expr in ("pout_frown", "exasperated"):
            draw.arc(
                [hx - int(19 * scale * SS), hy + int(30 * scale * SS), hx + int(19 * scale * SS), hy + int(50 * scale * SS)],
                start=190,
                end=350,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        elif expr == "shocked":
            draw.ellipse(
                [hx - int(12 * scale * SS), hy + int(24 * scale * SS), hx + int(12 * scale * SS), hy + int(46 * scale * SS)],
                fill=(176, 56, 64),
                outline=ink,
                width=max(4 * SS, int(5 * scale * SS)),
            )
        else:
            draw.line(
                [(hx - int(19 * scale * SS), hy + int(33 * scale * SS)), (hx + int(19 * scale * SS), hy + int(31 * scale * SS))],
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )


def _draw_eyes(draw, hx, hy, scale, expr, skin_col, t, look_x=1.0):
    ink = (24, 24, 30)
    eye_dx = int(30 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(18 * scale * SS)
    blinking = ((t + (0.85 if look_x < 0 else 0.0)) % 3.1) < 0.11
    px_off = int(5 * look_x * scale * SS)

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
        draw.ellipse([ex - 5 * SS + px_off, eye_y - 5 * SS, ex + 5 * SS + px_off, eye_y + 5 * SS], fill=ink)
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
            [(ex - er, eye_y - er - 9 * SS - brow_tilt), (ex + er, eye_y - er - 9 * SS + brow_tilt)],
            fill=ink,
            width=max(4 * SS, int(6 * scale * SS)),
        )


def _draw_full_cartoon_person(draw, cx, base_y, scale, char_cfg, is_male, expr, is_speaking, mouth_open, t, turn_frame, look_x=1.0):
    ink = (24, 24, 30)
    spring_val = remotion_spring(turn_frame, FPS, damping=12.0, stiffness=200.0, mass=0.5)
    head_lag = remotion_spring(max(0, turn_frame - 2), FPS, damping=13.0, stiffness=180.0, mass=0.5)

    talk_bob = int(math.sin(t * 8.2) * 5 * scale * SS) if (is_speaking and mouth_open > 0.1) else int(math.sin(t * 2.2 + (0.0 if is_male else 1.1)) * 3 * scale * SS)
    lean = int(12 * look_x * spring_val * scale * SS) if is_speaking else 0

    hx = int((cx + lean * 0.4) * SS)
    hy = int((base_y - 255 * scale) * SS) + talk_bob
    rx = int(86 * scale * SS)
    ry = int(86 * scale * SS)
    neck_y = hy + ry - 4 * SS
    torso_h = int(175 * scale * SS)
    hip_y = neck_y + torso_h
    leg_h = int(165 * scale * SS)

    # Soft ground shadow under shoes
    foot_y = hip_y + leg_h + 10 * SS
    draw.ellipse(
        [hx - int(66 * scale * SS), foot_y - int(10 * scale * SS), hx + int(66 * scale * SS), foot_y + int(16 * scale * SS)],
        fill=(96, 74, 56),
    )

    pants_col = char_cfg.get("pants_color" if is_male else "skirt_color", (46, 52, 64))
    for side in (-1, 1):
        lx = hx + int(side * 24 * scale * SS)
        draw.rounded_rectangle(
            [lx - int(15 * scale * SS), hip_y - 8 * SS, lx + int(15 * scale * SS), hip_y + leg_h],
            radius=int(12 * scale * SS),
            fill=pants_col,
            outline=ink,
            width=6 * SS,
        )
        draw.rounded_rectangle(
            [lx - int(18 * scale * SS), hip_y + leg_h - 14 * SS, lx + int(24 * scale * SS), hip_y + leg_h + 10 * SS],
            radius=int(10 * scale * SS),
            fill=(246, 246, 250),
            outline=ink,
            width=5 * SS,
        )

    top_col = char_cfg["top_color"]
    if is_male:
        draw.rounded_rectangle(
            [hx - int(58 * scale * SS), neck_y, hx + int(58 * scale * SS), hip_y + 10 * SS],
            radius=int(26 * scale * SS),
            fill=top_col,
            outline=ink,
            width=7 * SS,
        )
        collar_col = char_cfg.get("collar_color", (220, 224, 230))
        draw.pieslice(
            [hx - int(26 * scale * SS), neck_y - 12 * SS, hx + int(26 * scale * SS), neck_y + int(24 * scale * SS)],
            start=0,
            end=180,
            fill=collar_col,
            outline=ink,
            width=5 * SS,
        )
    else:
        dress_poly = [
            (hx - int(44 * scale * SS), neck_y),
            (hx + int(44 * scale * SS), neck_y),
            (hx + int(68 * scale * SS), hip_y + 22 * SS),
            (hx - int(68 * scale * SS), hip_y + 22 * SS),
        ]
        draw.polygon(dress_poly, fill=top_col, outline=ink)
        draw.line(dress_poly + [dress_poly[0]], fill=ink, width=7 * SS)

    arm_w = max(14 * SS, int(22 * scale * SS))
    skin = char_cfg["skin"]
    l_sh = (hx - int(50 * scale * SS), neck_y + int(28 * scale * SS))
    r_sh = (hx + int(50 * scale * SS), neck_y + int(28 * scale * SS))
    gest_wave = int(math.sin(t * 8.5) * 16 * scale * SS) if is_speaking else 0

    if is_speaking and expr in ("exasperated", "shocked", "excited_wide"):
        l_wrist = (l_sh[0] - int(65 * scale * SS), l_sh[1] - int((55 * spring_val) * scale * SS) + gest_wave)
        r_wrist = (r_sh[0] + int(65 * scale * SS), r_sh[1] - int((55 * spring_val) * scale * SS) - gest_wave)
        _draw_curved_sleeve_arm(draw, l_sh, (l_sh[0] - int(72 * scale * SS), l_sh[1] + int(20 * scale * SS)), l_wrist, top_col, skin, arm_w)
        _draw_curved_sleeve_arm(draw, r_sh, (r_sh[0] + int(72 * scale * SS), r_sh[1] + int(20 * scale * SS)), r_wrist, top_col, skin, arm_w)
        _draw_cartoon_hand(draw, l_wrist[0], l_wrist[1], -125, skin, spread=1.25, scale=scale)
        _draw_cartoon_hand(draw, r_wrist[0], r_wrist[1], -55, skin, spread=1.25, scale=scale)
    elif is_speaking:
        dir_s = 1 if look_x >= 0 else -1
        active_sh = r_sh if dir_s > 0 else l_sh
        idle_sh = l_sh if dir_s > 0 else r_sh
        act_wrist = (active_sh[0] + int(dir_s * 78 * scale * SS), active_sh[1] + int(18 * scale * SS) - gest_wave)
        act_elbow = (active_sh[0] + int(dir_s * 55 * scale * SS), active_sh[1] + int(78 * scale * SS))
        _draw_curved_sleeve_arm(draw, active_sh, act_elbow, act_wrist, top_col, skin, arm_w)
        _draw_cartoon_hand(draw, act_wrist[0], act_wrist[1], -35 if dir_s > 0 else -145, skin, spread=1.15, scale=scale)

        idle_wrist = (idle_sh[0] - int(dir_s * 22 * scale * SS), idle_sh[1] + int(115 * scale * SS))
        idle_elbow = (idle_sh[0] - int(dir_s * 38 * scale * SS), idle_sh[1] + int(62 * scale * SS))
        _draw_curved_sleeve_arm(draw, idle_sh, idle_elbow, idle_wrist, top_col, skin, arm_w)
    elif expr == "pout_frown":
        _draw_curved_sleeve_arm(draw, l_sh, (l_sh[0] - int(28 * scale * SS), l_sh[1] + int(48 * scale * SS)), (r_sh[0] + int(10 * scale * SS), r_sh[1] + int(52 * scale * SS)), top_col, skin, arm_w)
        _draw_curved_sleeve_arm(draw, r_sh, (r_sh[0] + int(28 * scale * SS), r_sh[1] + int(54 * scale * SS)), (l_sh[0] - int(10 * scale * SS), l_sh[1] + int(58 * scale * SS)), top_col, skin, arm_w)
    else:
        _draw_curved_sleeve_arm(draw, l_sh, (l_sh[0] - int(32 * scale * SS), l_sh[1] + int(62 * scale * SS)), (l_sh[0] - int(18 * scale * SS), l_sh[1] + int(118 * scale * SS)), top_col, skin, arm_w)
        _draw_curved_sleeve_arm(draw, r_sh, (r_sh[0] + int(32 * scale * SS), r_sh[1] + int(62 * scale * SS)), (r_sh[0] + int(18 * scale * SS), r_sh[1] + int(118 * scale * SS)), top_col, skin, arm_w)

    h_hy = hy + int(head_lag * 3 * scale * SS)
    hair = char_cfg["hair"]
    style = char_cfg.get("hair_style", "wavy_crop")

    if not is_male:
        if style == "bun":
            draw.ellipse([hx + rx - int(20 * scale * SS), h_hy - ry + int(6 * scale * SS), hx + rx + int(34 * scale * SS), h_hy - ry + int(60 * scale * SS)], fill=hair, outline=ink, width=6 * SS)
        elif style == "afro_puffs":
            draw.ellipse([hx - rx - int(42 * scale * SS), h_hy - ry - int(32 * scale * SS), hx - rx + int(24 * scale * SS), h_hy - ry + int(32 * scale * SS)], fill=hair, outline=ink, width=6 * SS)
            draw.ellipse([hx + rx - int(24 * scale * SS), h_hy - ry - int(32 * scale * SS), hx + rx + int(42 * scale * SS), h_hy - ry + int(32 * scale * SS)], fill=hair, outline=ink, width=6 * SS)
        elif style in ("long_straight", "long_waves_bangs"):
            draw.rounded_rectangle([hx - rx - int(12 * scale * SS), h_hy - ry + int(10 * scale * SS), hx + rx + int(12 * scale * SS), h_hy + ry + int(95 * scale * SS)], radius=int(34 * scale * SS), fill=hair, outline=ink, width=6 * SS)
        elif style == "box_braids":
            for bx_off in (-78, -58, 58, 78):
                draw.line([(hx + int(bx_off * scale * SS), h_hy - int(16 * scale * SS)), (hx + int(bx_off * 1.1 * scale * SS), h_hy + ry + int(108 * scale * SS))], fill=hair, width=max(8 * SS, int(12 * scale * SS)))
        elif style == "sleek_bob":
            bob_poly = [
                (hx - rx - int(6 * scale * SS), h_hy - int(10 * scale * SS)),
                (hx + rx + int(6 * scale * SS), h_hy - int(10 * scale * SS)),
                (hx + rx + int(18 * scale * SS), h_hy + ry + int(34 * scale * SS)),
                (hx - rx - int(18 * scale * SS), h_hy + ry + int(34 * scale * SS)),
            ]
            draw.polygon(bob_poly, fill=hair, outline=ink)
            draw.line(bob_poly + [bob_poly[0]], fill=ink, width=6 * SS)

    draw.ellipse([hx - rx, h_hy - ry, hx + rx, h_hy + ry], fill=skin, outline=ink, width=7 * SS)

    if is_male:
        if char_cfg.get("beard"):
            draw.arc([hx - int(rx * 0.85), h_hy - int(ry * 0.2), hx + int(rx * 0.85), h_hy + int(ry * 0.92)], start=15, end=165, fill=hair, width=max(6 * SS, int(9 * scale * SS)))
        if style == "cap":
            cap = char_cfg["cap_color"]
            draw.pieslice([hx - rx, h_hy - ry - int(8 * scale * SS), hx + rx, h_hy - int(ry * 0.14)], start=180, end=360, fill=cap, outline=ink, width=7 * SS)
            draw.rounded_rectangle([hx - int(6 * scale * SS), h_hy - int(ry * 0.56), hx + int(rx * 1.30), h_hy - int(ry * 0.34)], radius=8 * SS, fill=cap, outline=ink, width=6 * SS)
        elif style == "fade_lineup":
            draw.pieslice([hx - rx, h_hy - ry - 4 * SS, hx + rx, h_hy - int(ry * 0.36)], start=185, end=355, fill=hair, outline=ink, width=7 * SS)
        else:
            draw.pieslice([hx - rx - 4 * SS, h_hy - ry - 8 * SS, hx + rx + 4 * SS, h_hy - int(ry * 0.22)], start=175, end=365, fill=hair, outline=ink, width=7 * SS)
    else:
        draw.pieslice([hx - rx - 2 * SS, h_hy - ry - 6 * SS, hx + rx + 2 * SS, h_hy - int(ry * 0.16)], start=180, end=360, fill=hair, outline=ink, width=7 * SS)
        if char_cfg.get("bindi"):
            draw.ellipse([hx - int(5 * scale * SS), h_hy - int(32 * scale * SS), hx + int(5 * scale * SS), h_hy - int(22 * scale * SS)], fill=(178, 32, 42))
        if char_cfg.get("hoops"):
            draw.ellipse([hx + rx - int(8 * scale * SS), h_hy + int(10 * scale * SS), hx + rx + int(16 * scale * SS), h_hy + int(38 * scale * SS)], outline=(238, 194, 72), width=max(4 * SS, int(5 * scale * SS)))

    _draw_eyes(draw, hx, h_hy, scale, expr, skin, t, look_x=look_x)
    if char_cfg.get("glasses"):
        eye_dx = int(30 * scale * SS)
        eye_y = h_hy - int(10 * scale * SS)
        gr = int(24 * scale * SS)
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.ellipse([ex - gr, eye_y - gr, ex + gr, eye_y + gr], outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        draw.line([(hx - eye_dx + gr, eye_y), (hx + eye_dx - gr, eye_y)], fill=ink, width=max(4 * SS, int(5 * scale * SS)))

    if expr == "soft_love_smile":
        draw.ellipse([hx - int(52 * scale * SS), h_hy + int(10 * scale * SS), hx - int(26 * scale * SS), h_hy + int(24 * scale * SS)], fill=(238, 128, 138))
        draw.ellipse([hx + int(26 * scale * SS), h_hy + int(10 * scale * SS), hx + int(52 * scale * SS), h_hy + int(24 * scale * SS)], fill=(238, 128, 138))

    _draw_mouth(draw, hx, h_hy, scale, expr, mouth_open if is_speaking else 0.0)
    return (hx // SS, h_hy // SS)


def compute_ensemble_layout(selected_couples):
    n = len(selected_couples)
    if n == 1:
        return [
            {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 360, "base_y": 1150, "scale": 1.02, "look_x": 1.0, "z": 1},
            {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 720, "base_y": 1150, "scale": 1.00, "look_x": -1.0, "z": 1},
        ]
    if n == 2:
        return [
            {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 205, "base_y": 1155, "scale": 0.86, "look_x": 1.0, "z": 1},
            {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 405, "base_y": 1155, "scale": 0.85, "look_x": 0.6, "z": 1},
            {"couple_idx": 1, "is_male": True, "cfg": selected_couples[1]["him"], "x": 675, "base_y": 1155, "scale": 0.86, "look_x": -0.6, "z": 1},
            {"couple_idx": 1, "is_male": False, "cfg": selected_couples[1]["her"], "x": 875, "base_y": 1155, "scale": 0.85, "look_x": -1.0, "z": 1},
        ]
    return [
        {"couple_idx": 2, "is_male": True, "cfg": selected_couples[2]["him"], "x": 455, "base_y": 1075, "scale": 0.72, "look_x": 0.4, "z": 0},
        {"couple_idx": 2, "is_male": False, "cfg": selected_couples[2]["her"], "x": 625, "base_y": 1075, "scale": 0.71, "look_x": -0.4, "z": 0},
        {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 170, "base_y": 1175, "scale": 0.82, "look_x": 1.0, "z": 1},
        {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 350, "base_y": 1175, "scale": 0.81, "look_x": 0.6, "z": 1},
        {"couple_idx": 1, "is_male": True, "cfg": selected_couples[1]["him"], "x": 730, "base_y": 1175, "scale": 0.82, "look_x": -0.6, "z": 1},
        {"couple_idx": 1, "is_male": False, "cfg": selected_couples[1]["her"], "x": 910, "base_y": 1175, "scale": 0.81, "look_x": -1.0, "z": 1},
    ]


def apply_2x_sitcom_camera(stage_hi, num_couples, camera_mode, active_couple_idx, speaker_head_xy, turn_frame):
    eased = remotion_spring(turn_frame, FPS, damping=200.0, stiffness=140.0, mass=1.0)
    sw, sh = W * SS, H * SS

    if camera_mode == "focus_speaker" and speaker_head_xy:
        zoom = 1.62 + 0.12 * eased
        cx = int(speaker_head_xy[0] * SS)
        cy = int((speaker_head_xy[1] + 130) * SS)
    elif camera_mode.startswith("focus_couple_"):
        try:
            c_idx = int(camera_mode.split("_")[-1])
        except ValueError:
            c_idx = active_couple_idx
        if num_couples == 1:
            zoom, cx, cy = 1.18 + 0.08 * eased, sw // 2, int(sh * 0.48)
        elif num_couples == 2:
            zoom = 1.54 + 0.08 * eased
            cx = int(sw * (0.28 if c_idx == 0 else 0.72))
            cy = int(sh * 0.48)
        else:
            zoom = 1.62 + 0.08 * eased
            if c_idx == 0:
                cx, cy = int(sw * 0.24), int(sh * 0.49)
            elif c_idx == 1:
                cx, cy = int(sw * 0.76), int(sh * 0.49)
            else:
                cx, cy = int(sw * 0.50), int(sh * 0.44)
    else:
        zoom = 1.02 + 0.03 * eased
        cx, cy = sw // 2, sh // 2

    cw, ch = int(sw / zoom), int(sh / zoom)
    x0 = max(0, min(sw - cw, cx - cw // 2))
    y0 = max(0, min(sh - ch, cy - ch // 2))
    return stage_hi.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# SAFE-ZONE TEXT OVERLAYS: 3.5s TOP HOOK TITLE + MIDDLE-LOWER KARAOKE CAPTIONS
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


def draw_safe_zone_overlays(frame, script, active_turn, t, page_cfg):
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    if t <= 3.5:
        alpha = 255 if t <= 3.0 else int(255 * max(0.0, (3.5 - t) / 0.5))
        hook_font = _load_font(44)
        hook_lines = textwrap.wrap(script["hook_title"].upper(), width=24)[:2]
        box_h = 66 + (len(hook_lines) - 1) * 52
        odraw.rounded_rectangle(
            [110, 255, W - 110, 255 + box_h],
            radius=22,
            fill=(16, 18, 24, int(alpha * 0.82)),
            outline=(255, 225, 45, alpha),
            width=4,
        )
        for idx_h, h_line in enumerate(hook_lines):
            odraw.text(
                (W // 2, 288 + idx_h * 50),
                h_line,
                font=hook_font,
                fill=(255, 255, 255, alpha),
                anchor="mm",
            )

    odraw.text(
        (500, 1565),
        page_cfg["handle"],
        font=_load_font(24),
        fill=(255, 255, 255, 190),
        anchor="mm",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 185),
    )

    if not active_turn or t > active_turn["speech_end"] + 0.12:
        return Image.alpha_composite(rgba, overlay).convert("RGB")

    sp_font = _load_font(26)
    odraw.rounded_rectangle([415, 1320, 585, 1362], radius=16, fill=(18, 20, 26, 215))
    odraw.text((500, 1341), active_turn["speaker"].upper(), font=sp_font, fill=(255, 225, 45, 255), anchor="mm")

    words = active_turn["text"].split()
    speech_dur = max(0.25, active_turn["speech_end"] - active_turn["start"])
    progress = max(0.0, min(0.999, (t - active_turn["start"]) / speech_dur))
    global_word_idx = int(progress * len(words))

    chunk_size = 3
    chunk_idx = global_word_idx // chunk_size
    chunk_words = words[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size]
    local_active = global_word_idx % chunk_size

    acc = tuple(page_cfg.get("accent_color", (255, 225, 45)))
    font = _load_font(52)
    space_w = odraw.textbbox((0, 0), " ", font=font)[2]
    word_boxes = [odraw.textbbox((0, 0), w.upper(), font=font) for w in chunk_words]
    total_w = sum((b[2] - b[0]) for b in word_boxes) + space_w * max(0, len(chunk_words) - 1)
    cur_x = max(70, 500 - total_w // 2)
    cur_y = 1385

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


# ==============================================================================
# FULL REEL RENDERER (DIRECT FFMPEG RAW-FRAME PIPE)
# ==============================================================================
def render_sitcom_reel(page_cfg, selected_couples, script, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        timeline, total_dur, final_wav = build_audio_and_timeline(script, selected_couples, tmp_dir)

        bg_cache = {}
        for turn in timeline:
            loc = turn["location"]
            if loc not in bg_cache:
                bg_p = tmp_dir / f"bg_{loc}.png"
                render_location_background(loc, bg_p)
                bg_cache[loc] = Image.open(bg_p).convert("RGB").resize((W * SS, H * SS), Image.Resampling.BILINEAR)

        layout = compute_ensemble_layout(selected_couples)
        layout_sorted = sorted(layout, key=lambda item: item["z"])

        ffmpeg_cmd = [
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
            "-preset", "medium",
            "-crf", "20",
            "-vsync", "cfr",
            "-c:a", "aac",
            "-ar", "48000",
            "-ac", "2",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

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
                speaker_name = active_turn["speaker"]
                speaker_emo = active_turn["emotion"]
                loc = active_turn["location"]
                cam = active_turn["camera"]
                act_c_idx = active_turn["couple_idx"]
            else:
                turn_frame = 0
                mouth_open = 0.0
                speaker_name = ""
                speaker_emo = "chill_smirk"
                loc = script["setting"]
                cam = "group_wide"
                act_c_idx = 0

            stage_hi = bg_cache[loc].copy()
            draw = ImageDraw.Draw(stage_hi)
            speaker_head_xy = None

            for actor in layout_sorted:
                c_name = actor["cfg"]["name"]
                is_sp = (c_name == speaker_name)
                emo = speaker_emo if is_sp else ("soft_love_smile" if "Romantic" in script["mood"] or "Cozy" in script["mood"] else "chill_smirk")
                head_xy = _draw_full_cartoon_person(
                    draw=draw,
                    cx=actor["x"],
                    base_y=actor["base_y"],
                    scale=actor["scale"],
                    char_cfg=actor["cfg"],
                    is_male=actor["is_male"],
                    expr=emo,
                    is_speaking=is_sp,
                    mouth_open=mouth_open if is_sp else 0.0,
                    t=t,
                    turn_frame=turn_frame,
                    look_x=actor["look_x"],
                )
                if is_sp:
                    speaker_head_xy = head_xy

            frame = apply_2x_sitcom_camera(stage_hi, len(selected_couples), cam, act_c_idx, speaker_head_xy, turn_frame)
            frame = ImageEnhance.Contrast(frame).enhance(1.03)
            frame = draw_safe_zone_overlays(frame, script, active_turn, t, page_cfg)
            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        _, stderr_bytes = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encode failed: {stderr_bytes.decode('utf-8', errors='replace')[-800:]}")

        print(f"Rendered {total_dur:.1f}s Reel ({', '.join(script['couples'])} | {script['mood']}) -> {out_mp4}")
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


# ==============================================================================
# GITHUB PAGES ARCHIVE + INSTAGRAM REELS PUBLISHING
# ==============================================================================
def archive_and_get_pages_url(rel_path):
    nojekyll = pathlib.Path(".nojekyll")
    if not nojekyll.exists():
        nojekyll.write_text("", encoding="utf-8")

    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/", ".nojekyll"], check=True)
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Publish Reel {rel_path}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)

    owner, repo = REPO_NAME.split("/", 1)
    base_pages_url = build_https_url(f"{owner.lower()}.github.io", f"/{repo}/{rel_path}")
    for attempt in range(1, 37):
        time.sleep(5)
        probe_url = f"{base_pages_url}?cb={attempt}_{int(time.time())}"
        try:
            req = urllib.request.Request(
                probe_url,
                headers={"User-Agent": "facebookexternalhit/1.1", "Range": "bytes=0-1023"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status in (200, 206) and ("video/" in ctype or "octet-stream" in ctype):
                    live_url = f"{base_pages_url}?v={int(time.time())}"
                    print(f"GitHub Pages video live ({attempt * 5}s): {live_url}")
                    return live_url
        except Exception as e:
            print(f"Waiting for GitHub Pages deploy ({attempt}/36): {e}")
    raise RuntimeError(
        f"GitHub Pages did not serve MP4 within 180s: {base_pages_url} "
        "(Verify GitHub repo Settings -> Pages -> Source is 'Deploy from a branch: main / (root)')."
    )


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API {e.code} on {url}: {e.read().decode('utf-8', errors='replace')}") from e


def publish_to_instagram(ig_id, token, video_url, caption):
    host = get_graph_host(token)
    media_url = build_https_url(host, f"/{GRAPH_VERSION}/{ig_id}/media")
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

    for attempt in range(1, 41):
        time.sleep(5)
        status_url = build_https_url(
            host,
            f"/{GRAPH_VERSION}/{creation_id}",
            {"fields": "status_code,status", "access_token": token},
        )
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel processing ({attempt}/40): {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram Reel container failed: {status_data}")
    else:
        raise RuntimeError(f"Instagram Reel container timed out: {creation_id}")

    publish_url = build_https_url(host, f"/{GRAPH_VERSION}/{ig_id}/media_publish")
    published = post_request(publish_url, {"creation_id": creation_id, "access_token": token})
    media_id = published["id"]

    permalink = ""
    try:
        link_url = build_https_url(host, f"/{GRAPH_VERSION}/{media_id}", {"fields": "permalink", "access_token": token})
        link_data = json.loads(urllib.request.urlopen(link_url, timeout=15).read().decode())
        permalink = link_data.get("permalink", "")
    except Exception:
        pass

    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {media_id} {permalink}")


if __name__ == "__main__":
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    publish_enabled = os.environ.get("PUBLISH_TO_IG", "true").strip().lower() not in ("0", "false", "no")
    print(f"PUBLISH_TO_IG = {publish_enabled}")

    for page in load_active_pages():
        slug = page["slug"]
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
        ig_id = (page.get("ig_user_id") or os.environ.get("IG_USER_ID") or DEFAULT_IG_USER_ID).strip()

        if publish_enabled:
            verify_instagram_credentials(ig_id, token)

        history_items = load_story_history(slug, limit=150)
        selected_couples, mood, festival_obj, suggested_topic = plan_cast_and_premise(history_items, now_est)
        script = generate_story_with_gemini(
            page, selected_couples, mood, festival_obj, suggested_topic, history_items
        )

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"
        out_dir.joinpath(f"story_{stamp}.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        hist_entry = script.get("history_entry", {})
        save_story_record(slug, {
            "timestamp": stamp,
            "lead_couple": selected_couples[0]["label"],
            "couples": script["couples"],
            "mood": script["mood"],
            "festival": script.get("festival"),
            "hook": hist_entry.get("hook", script["hook_title"]),
            "environment": hist_entry.get("environment", script["setting"]),
            "core_joke": hist_entry.get("core_joke", script["hook_title"]),
            "hashtags": script["hashtags"],
        })

        render_sitcom_reel(page, selected_couples, script, rel_mp4)

        if publish_enabled:
            public_url = archive_and_get_pages_url(rel_mp4)
            full_ig_caption = f"{script['caption']}\n\n{' '.join(script['hashtags'])}"
            publish_to_instagram(ig_id, token, public_url, full_ig_caption)
