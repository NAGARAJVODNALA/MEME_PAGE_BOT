#!/usr/bin/env python3
"""
@wearechillclub  -  animated couple-comedy Reels bot (MEME_PAGE_BOT / meme_agent.py)

pip install pillow numpy edge-tts gtts lunardate
(numpy and lunardate are optional but recommended; edge-tts / gtts are auto-installed if missing)

Environment variables
  GEMINI_API_KEY      required
  IG_ACCESS_TOKEN     required only when publishing
  IG_USER_ID          optional override
  PUBLISH_TO_IG       "true" to publish (DEFAULT IS FALSE - nothing is posted unless you set it)
  IG_UPLOAD_MODE      "url" (GitHub Pages, default) or "resumable" (upload file straight to Meta,
                      no video committed to your repo - needs Facebook Login for Business)
  KEEP_VIDEOS         "true" (default) keeps MP4s in posts/; "false" deletes them after posting
  ALLOW_FALLBACK      "true" to render (never publish) the built-in fallback story for local tests
  COMMIT_HISTORY      "true" to commit history/story files even when not publishing
  GRAPH_VERSION       Graph API version (default v25.0)
  MAX_REEL_SEC        hard cap for reel length (default 36)

Optional folders next to this file
  fonts/              drop a bold .ttf here (Poppins-Bold, Anton...) for nicer captions
  music/              royalty-free lo-fi loops (mp3/wav). music/<mood_name>/ is checked first
  festivals_extra.json   extra festivals, e.g.
      [{"name":"Karwa Chauth","date":"2027-10-19","location":"festival_diwali_home",
        "tag":"#karwachauth","hosts":["dev_priya"]}]
      ("date" may be "YYYY-MM-DD" for one year or "MM-DD" to repeat every year)
"""
import os
import re
import sys
import math
import json
import time
import wave
import array
import base64
import bisect
import random
import shutil
import struct
import asyncio
import pathlib
import textwrap
import functools
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone, timedelta, date
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

try:
    import numpy as np
except ImportError:  # numpy is optional
    np = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


def env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
DEFAULT_IG_USER_ID = "17841476835986162"
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v25.0").strip() or "v25.0"
FPS = 24
W, H = 1080, 1920
SS = 2  # 2x supersampling (2160x3840) so close-up zooms stay razor-sharp
SR = 48000

# ---- Story-driven length (NEVER padded) -------------------------------------
MAX_REEL_SEC = float(os.environ.get("MAX_REEL_SEC", "36") or 36)  # hard cap
WORD_SOFT_MAX = 72      # prompt asks for <= this many spoken words in total
WORD_HARD_MAX = 82      # above this the draft is rewritten / mechanically trimmed
MAX_WORDS_PER_LINE = 12
MIN_LINES_KEPT = 5
LEAD_IN_SEC = 0.30
LINE_GAP_SEC = 0.18
END_HOLD_SEC = 0.80

# ---- Instagram Reels safe zones on a 1080x1920 canvas -----------------------
SAFE_LEFT = 65
SAFE_RIGHT = 120          # like / comment / share column
SAFE_TOP = 270
SAFE_BOTTOM_START = 1250  # bottom ~670px holds username, caption, audio line
HOOK_Y = 305
PILL_Y = 1128
CAPTION_Y = 1180
CAPTION_CENTER_X = (SAFE_LEFT + (W - SAFE_RIGHT)) // 2
CAPTION_MAX_W = W - SAFE_LEFT - SAFE_RIGHT - 20

INK = (20, 20, 24)

# ==============================================================================
# 6 BOYFRIEND / GIRLFRIEND COUPLE CAST (CONSISTENT LOOKS, OUTFITS & UNIQUE VOICES)
# ==============================================================================
COUPLE_PROFILES = [
    {
        "id": "tom_olivia",
        "label": "Tom & Olivia",
        "personality": "Dry-humored, outdoorsy boyfriend Tom (overthinker) and quick-witted, unbothered girlfriend Olivia.",
        "him": {
            "name": "Tom",
            "skin": (246, 224, 206),
            "hair": (96, 64, 42),
            "hair_style": "cap",
            "cap_color": (146, 76, 54),
            "top_color": (242, 240, 236),
            "collar_color": (58, 76, 98),
            "pants_color": (52, 68, 92),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Puck",
            "edge_voice": "en-US-AndrewNeural",
            "voice_style": "Speak naturally like a laid-back, witty 25-year-old boyfriend",
        },
        "her": {
            "name": "Olivia",
            "skin": (248, 228, 212),
            "hair": (42, 30, 24),
            "hair_style": "bun",
            "top_color": (34, 38, 46),
            "skirt_color": (72, 92, 118),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Aoede",
            "edge_voice": "en-US-AvaNeural",
            "voice_style": "Speak naturally like an expressive, playful 24-year-old girlfriend",
        },
    },
    {
        "id": "dev_priya",
        "label": "Dev & Priya",
        "personality": "Charming, endlessly optimistic, food-loving boyfriend Dev and sharp, dry, warm girlfriend Priya.",
        "him": {
            "name": "Dev",
            "skin": (182, 132, 96),
            "hair": (22, 22, 26),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (68, 108, 86),
            "collar_color": (236, 224, 198),
            "pants_color": (44, 48, 56),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Orus",
            "edge_voice": "en-IN-PrabhatNeural",
            "voice_style": "Speak in natural, warm modern Indian English like a 26-year-old boyfriend",
        },
        "her": {
            "name": "Priya",
            "skin": (192, 142, 106),
            "hair": (20, 20, 24),
            "hair_style": "long_straight",
            "top_color": (186, 68, 62),
            "skirt_color": (232, 194, 112),
            "bindi": True,
            "hoops": True,
            "gemini_voice": "Kore",
            "edge_voice": "en-IN-NeerjaExpressiveNeural",
            "voice_style": "Speak in natural, expressive modern Indian English like a witty 25-year-old girlfriend",
        },
    },
    {
        "id": "wei_lin",
        "label": "Wei & Lin",
        "personality": "Deadpan, quiet-planner boyfriend Wei and clever, playful, cozy-loving, lucky-improviser girlfriend Lin.",
        "him": {
            "name": "Wei",
            "skin": (238, 214, 192),
            "hair": (24, 24, 28),
            "hair_style": "side_part",
            "cap_color": None,
            "top_color": (46, 66, 94),
            "collar_color": (224, 230, 238),
            "pants_color": (48, 52, 60),
            "beard": False,
            "glasses": True,
            "gemini_voice": "Charon",
            "edge_voice": "en-SG-WayneNeural",
            "voice_style": "Speak naturally like a calm, dry-humored 25-year-old boyfriend",
        },
        "her": {
            "name": "Lin",
            "skin": (242, 220, 200),
            "hair": (24, 24, 28),
            "hair_style": "sleek_bob",
            "top_color": (228, 212, 192),
            "skirt_color": (124, 88, 72),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Leda",
            "edge_voice": "en-SG-LunaNeural",
            "voice_style": "Speak naturally like a smart, warm, slightly sassy 24-year-old girlfriend",
        },
    },
    {
        "id": "minho_jisoo",
        "label": "Minho & Jisoo",
        "personality": "Smooth, dramatic worrier boyfriend Minho and expressive, cute-but-fiery, deadpan girlfriend Jisoo.",
        "him": {
            "name": "Minho",
            "skin": (242, 222, 204),
            "hair": (26, 26, 30),
            "hair_style": "comma_hair",
            "cap_color": None,
            "top_color": (214, 198, 178),
            "collar_color": (44, 46, 52),
            "pants_color": (42, 46, 54),
            "beard": False,
            "glasses": False,
            "gemini_voice": "Fenrir",
            "edge_voice": "en-US-BrianNeural",
            "voice_style": "Speak naturally like a charming, relaxed 24-year-old boyfriend",
        },
        "her": {
            "name": "Jisoo",
            "skin": (245, 226, 210),
            "hair": (32, 26, 26),
            "hair_style": "long_waves_bangs",
            "top_color": (182, 168, 214),
            "skirt_color": (54, 58, 72),
            "bindi": False,
            "hoops": False,
            "gemini_voice": "Zephyr",
            "edge_voice": "en-US-EmmaNeural",
            "voice_style": "Speak naturally like an expressive, sweet and playful 23-year-old girlfriend",
        },
    },
    {
        "id": "noah_aaliyah",
        "label": "Noah & Aaliyah",
        "personality": "Enthusiastic, over-prepared, lovable-klutz boyfriend Noah and sharp, hilarious, calm-fixer girlfriend Aaliyah.",
        "him": {
            "name": "Noah",
            "skin": (244, 222, 204),
            "hair": (128, 92, 58),
            "hair_style": "wavy_crop",
            "cap_color": None,
            "top_color": (58, 66, 74),
            "collar_color": (226, 228, 232),
            "pants_color": (54, 62, 74),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Achird",
            "edge_voice": "en-US-ChristopherNeural",
            "voice_style": "Speak naturally like a warm, humorous 26-year-old boyfriend",
        },
        "her": {
            "name": "Aaliyah",
            "skin": (118, 76, 52),
            "hair": (22, 18, 18),
            "hair_style": "afro_puffs",
            "top_color": (46, 122, 92),
            "skirt_color": (42, 46, 54),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Callirrhoe",
            "edge_voice": "en-US-AriaNeural",
            "voice_style": "Speak naturally like a confident, witty, expressive 25-year-old girlfriend",
        },
    },
    {
        "id": "elijah_imani",
        "label": "Elijah & Imani",
        "personality": "Smooth, big-plan-dreamer, sports-loving boyfriend Elijah and vibrant, quick-banter girlfriend Imani who gently pokes holes in his plans.",
        "him": {
            "name": "Elijah",
            "skin": (104, 66, 44),
            "hair": (20, 18, 18),
            "hair_style": "fade_lineup",
            "cap_color": None,
            "top_color": (128, 46, 54),
            "collar_color": (240, 234, 224),
            "pants_color": (40, 44, 52),
            "beard": True,
            "glasses": False,
            "gemini_voice": "Algenib",
            "edge_voice": "en-US-DavisNeural",
            "voice_style": "Speak naturally like a smooth, funny 26-year-old boyfriend",
        },
        "her": {
            "name": "Imani",
            "skin": (136, 88, 60),
            "hair": (22, 18, 18),
            "hair_style": "box_braids",
            "top_color": (212, 158, 64),
            "skirt_color": (52, 48, 56),
            "bindi": False,
            "hoops": True,
            "gemini_voice": "Sulafat",
            "edge_voice": "en-US-JennyNeural",
            "voice_style": "Speak naturally like a vibrant, expressive, loving 25-year-old girlfriend",
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
    # new settings
    "city_rooftop_night",
    "palace_garden",
    "beach_sunset",
    "airport_terminal",
    "road_trip_scenic",
    "kitchen_cooking",
    "snowy_window_christmas",
    "park_picnic",
    "festival_holi",
]

MOOD_LOCATIONS = {
    "Cozy": ["apartment_couch", "snowy_window_christmas", "kitchen_cooking", "movie_living_room"],
    "Comedy": ["apartment_couch", "kitchen_cooking", "sports_hangout", "cafe_campus", "airport_terminal"],
    "Playful Fighting": ["apartment_couch", "movie_living_room", "kitchen_cooking", "sports_hangout"],
    "Cozy Cuddling": ["apartment_couch", "snowy_window_christmas", "movie_living_room"],
    "Flirty Dinner": ["dinner_candlelight", "city_rooftop_night", "palace_garden"],
    "Coffee/Lunch Dates": ["cafe_campus", "park_picnic", "kitchen_cooking"],
    "Destination Trips": ["beach_sunset", "airport_terminal", "road_trip_scenic", "mountain_trek", "palace_garden", "city_rooftop_night"],
    "Sad-to-Sweet Comfort": ["apartment_couch", "city_rooftop_night", "park_picnic", "snowy_window_christmas"],
    "Couple Gifting": ["cafe_campus", "snowy_window_christmas", "dinner_candlelight", "park_picnic"],
}

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
    "Watching the big game together when one cheers for the rival team",
    "What to eat tonight when both say 'I don't care, you pick'",
    "Blanket hogging and thermostat wars at 2 AM",
    "Taking 50 photos at a scenic overlook to get one candid shot",
    "Splitting the bill vs sneaking the card to pay first on a lunch date",
    "Playful jealousy over an unnamed movie-star crush during a film",
    "Surprise couple gifting on a random Tuesday",
    "Cooking dinner together and setting off the smoke alarm",
    "Packing one carry-on bag for a weekend trip",
    "Double date coffee run where everyone orders overly complicated drinks",
    "Getting lost on a road trip while one refuses to ask for directions",
    "Airport check-in when one bag is five kilos overweight",
    "Picking a gift for each other and accidentally buying the same thing",
    "Who falls asleep first during movie night",
    "One of them rehearses a speech for meeting the other's parents",
    "A picnic where the ants clearly planned it better than we did",
    "Late-night grocery run that ends with a cart full of snacks, none of them on the list",
    "Rooftop stargazing where one only wants to talk about dinner",
    "Beach day, one hates sand, the other forgot sunscreen",
    "Learning a new recipe from a video that moves too fast",
    "Arguing over how to load the dishwasher correctly",
    "The 'where should we go for our anniversary' standoff",
    "Matching outfits that went wrong at the worst moment",
    "Rainy-day plans where plan A, B and C are all 'stay in'",
    "One partner is 'five minutes away' while still at home",
]

HASHTAG_POOLS = {
    "broad": ["#funnyreels", "#relatablecontent", "#comedyreels", "#dailylaughs", "#relatable"],
    "couple": ["#couplehumor", "#funnycouple", "#couplelife", "#couplememes", "#relationshiphumor", "#couplegoals"],
}

SITUATIONAL_KEYWORDS = {
    "#datenightfail": ["date night", "dinner", "restaurant", "reservation"],
    "#splitthebill": ["bill", "split", "pay", "check please", "card"],
    "#whattoeat": ["eat", "hungry", "food", "pizza", "takeout", "snack"],
    "#movienight": ["movie", "film", "watch", "netflix", "popcorn"],
    "#collegelife": ["college", "campus", "study", "library", "university", "exam"],
    "#hikingcouple": ["hike", "trek", "trail", "mountain"],
    "#coffeedate": ["coffee", "cafe", "latte", "espresso"],
    "#cozyvibes": ["cozy", "blanket", "cuddle", "snuggle"],
    "#coupletravel": ["trip", "travel", "airport", "beach", "suitcase", "road trip", "flight"],
    "#gameday": ["game", "match", "team", "score", "stadium"],
    "#couplecooking": ["cook", "kitchen", "recipe", "oven", "dishwasher"],
    "#giftideas": ["gift", "present", "surprise"],
    "#picnicdate": ["picnic", "park"],
    "#roadtrip": ["road trip", "highway", "directions", "gps"],
}

# ==============================================================================
# DATE-AWARE FESTIVAL CALENDAR (computed every year - nothing hardcoded to 2026)
# ==============================================================================
def _nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    return d + timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


# Fallback used only if the 'lunardate' package is not installed.
_LUNAR_FALLBACK = {
    (2026, 1, 1): date(2026, 2, 17), (2027, 1, 1): date(2027, 2, 6),
    (2026, 1, 15): date(2026, 3, 3), (2027, 1, 15): date(2027, 2, 20),
    (2026, 5, 5): date(2026, 6, 19), (2027, 5, 5): date(2027, 6, 9),
    (2026, 7, 7): date(2026, 8, 19), (2027, 7, 7): date(2027, 8, 8),
    (2026, 8, 15): date(2026, 9, 25), (2027, 8, 15): date(2027, 9, 15),
}


def _lunar(year, month, day):
    try:
        from lunardate import LunarDate
        return LunarDate(year, month, day).toSolarDate()
    except Exception:
        return _LUNAR_FALLBACK.get((year, month, day))


# Hindu-calendar dates are not computable with the standard library.
# Verify these once a year (or add more via festivals_extra.json).
_FESTIVAL_DATE_TABLE = {
    ("Diwali", 2026): date(2026, 11, 8),
    ("Diwali", 2027): date(2027, 10, 29),
    ("Holi", 2026): date(2026, 3, 4),
    ("Holi", 2027): date(2027, 3, 22),
}


def _table(name):
    return lambda y: _FESTIVAL_DATE_TABLE.get((name, y))


ALL_HOSTS = None
US_HOSTS = ["tom_olivia", "noah_aaliyah", "elijah_imani"]

FESTIVALS_BUILTIN = [
    {"name": "New Year's Day", "tag": "#newyearvibes", "location": "apartment_couch", "hosts": ALL_HOSTS,
     "moods": ["Cozy", "Cozy Cuddling", "Comedy"], "when": lambda y: date(y, 1, 1)},
    {"name": "Pongal / Makar Sankranti", "tag": "#pongal", "location": "festival_diwali_home", "hosts": ["dev_priya"],
     "moods": ["Cozy", "Comedy"], "when": lambda y: date(y, 1, 14)},
    {"name": "Black History Month", "tag": "#blackhistorymonth", "location": "cafe_campus",
     "hosts": ["elijah_imani", "noah_aaliyah"], "moods": ["Cozy", "Coffee/Lunch Dates"], "when": lambda y: date(y, 2, 1)},
    {"name": "Valentine's Day", "tag": "#valentinesdate", "location": "dinner_candlelight", "hosts": ALL_HOSTS,
     "moods": ["Flirty Dinner", "Cozy Cuddling", "Couple Gifting"], "when": lambda y: date(y, 2, 14)},
    {"name": "Lunar New Year", "tag": "#lunarnewyear", "location": "festival_lunar_chuseok", "hosts": ["wei_lin"],
     "moods": ["Cozy", "Comedy", "Couple Gifting"], "when": lambda y: _lunar(y, 1, 1)},
    {"name": "Seollal (Korean New Year)", "tag": "#seollal", "location": "festival_lunar_chuseok", "hosts": ["minho_jisoo"],
     "moods": ["Cozy", "Comedy"], "when": lambda y: _lunar(y, 1, 1)},
    {"name": "Lantern Festival", "tag": "#lanternfestival", "location": "festival_lunar_chuseok", "hosts": ["wei_lin"],
     "moods": ["Cozy Cuddling", "Flirty Dinner"], "when": lambda y: _lunar(y, 1, 15)},
    {"name": "Holi", "tag": "#holicelebration", "location": "festival_holi", "hosts": ["dev_priya"],
     "moods": ["Comedy", "Playful Fighting"], "when": _table("Holi")},
    {"name": "White Day", "tag": "#whiteday", "location": "cafe_campus", "hosts": ["minho_jisoo"],
     "moods": ["Couple Gifting", "Flirty Dinner", "Coffee/Lunch Dates"], "when": lambda y: date(y, 3, 14)},
    {"name": "Black Day", "tag": "#blackday", "location": "cafe_campus", "hosts": ["minho_jisoo"],
     "moods": ["Comedy", "Coffee/Lunch Dates"], "when": lambda y: date(y, 4, 14)},
    {"name": "Easter", "tag": "#eastersunday", "location": "park_picnic", "hosts": US_HOSTS,
     "moods": ["Cozy", "Comedy", "Coffee/Lunch Dates"], "when": _easter},
    {"name": "Mother's Day", "tag": "#mothersday", "location": "kitchen_cooking", "hosts": ALL_HOSTS,
     "moods": ["Couple Gifting", "Cozy"], "when": lambda y: _nth_weekday(y, 5, 6, 2)},
    {"name": "520 Love Day", "tag": "#520day", "location": "dinner_candlelight", "hosts": ["wei_lin"],
     "moods": ["Flirty Dinner", "Couple Gifting"], "when": lambda y: date(y, 5, 20)},
    {"name": "Dragon Boat Festival", "tag": "#dragonboatfestival", "location": "park_picnic", "hosts": ["wei_lin"],
     "moods": ["Comedy", "Coffee/Lunch Dates"], "when": lambda y: _lunar(y, 5, 5)},
    {"name": "Juneteenth", "tag": "#juneteenth", "location": "cookout_backyard", "hosts": ["elijah_imani", "noah_aaliyah"],
     "moods": ["Cozy", "Comedy"], "when": lambda y: date(y, 6, 19)},
    {"name": "Fourth of July", "tag": "#fourthofjuly", "location": "cookout_backyard", "hosts": US_HOSTS,
     "moods": ["Comedy", "Cozy"], "when": lambda y: date(y, 7, 4)},
    {"name": "Qixi Festival", "tag": "#qixifestival", "location": "city_rooftop_night", "hosts": ["wei_lin"],
     "moods": ["Flirty Dinner", "Cozy Cuddling"], "when": lambda y: _lunar(y, 7, 7)},
    {"name": "Mid-Autumn Festival", "tag": "#midautumnfestival", "location": "festival_lunar_chuseok", "hosts": ["wei_lin"],
     "moods": ["Cozy", "Cozy Cuddling", "Comedy"], "when": lambda y: _lunar(y, 8, 15)},
    {"name": "Chuseok (Korean Thanksgiving)", "tag": "#chuseok", "location": "festival_lunar_chuseok", "hosts": ["minho_jisoo"],
     "moods": ["Cozy", "Comedy"], "when": lambda y: _lunar(y, 8, 15)},
    {"name": "Halloween", "tag": "#halloweennight", "location": "movie_living_room", "hosts": ALL_HOSTS,
     "moods": ["Comedy", "Playful Fighting", "Cozy Cuddling"], "when": lambda y: date(y, 10, 31)},
    {"name": "Diwali", "tag": "#diwalivibes", "location": "festival_diwali_home", "hosts": ["dev_priya"],
     "moods": ["Cozy", "Comedy", "Couple Gifting", "Cozy Cuddling"], "when": _table("Diwali")},
    {"name": "Pepero Day", "tag": "#peperoday", "location": "cafe_campus", "hosts": ["minho_jisoo"],
     "moods": ["Couple Gifting", "Comedy"], "when": lambda y: date(y, 11, 11)},
    {"name": "Singles' Day (Double 11)", "tag": "#singlesday", "location": "cafe_campus", "hosts": ["wei_lin"],
     "moods": ["Couple Gifting", "Comedy"], "when": lambda y: date(y, 11, 11)},
    {"name": "Thanksgiving", "tag": "#thanksgivingdinner", "location": "festival_thanksgiving_harvest", "hosts": US_HOSTS,
     "moods": ["Cozy", "Comedy", "Cozy Cuddling"], "when": lambda y: _nth_weekday(y, 11, 3, 4)},
    {"name": "Christmas Eve", "tag": "#christmaseve", "location": "snowy_window_christmas", "hosts": ALL_HOSTS,
     "moods": ["Cozy", "Couple Gifting", "Cozy Cuddling"], "when": lambda y: date(y, 12, 24)},
    {"name": "Christmas", "tag": "#christmascozy", "location": "snowy_window_christmas", "hosts": ALL_HOSTS,
     "moods": ["Cozy", "Couple Gifting", "Comedy"], "when": lambda y: date(y, 12, 25)},
    {"name": "Kwanzaa", "tag": "#kwanzaa", "location": "apartment_couch", "hosts": ["elijah_imani"],
     "moods": ["Cozy", "Cozy Cuddling"], "when": lambda y: date(y, 12, 26)},
    {"name": "New Year's Eve", "tag": "#newyearseve", "location": "city_rooftop_night", "hosts": ALL_HOSTS,
     "moods": ["Flirty Dinner", "Comedy", "Cozy Cuddling"], "when": lambda y: date(y, 12, 31)},
]

FESTIVAL_WINDOW_DAYS = 5

_DISCOVERED_MODELS = None
_FALLBACK_DEPS_CHECKED = False
_FESTIVALS_CACHE = None


def load_extra_festivals():
    p = pathlib.Path("festivals_extra.json")
    extras = []
    if not p.exists():
        return extras
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
        for it in items:
            raw = str(it.get("date", "")).strip()
            name = str(it.get("name", "")).strip()
            if not raw or not name:
                continue
            if len(raw) == 10:
                fixed = date.fromisoformat(raw)
                when = (lambda y, d=fixed: d if y == d.year else None)
            else:
                mm, dd = raw.split("-")
                when = (lambda y, m=int(mm), d=int(dd): date(y, m, d))
            extras.append({
                "name": name,
                "tag": it.get("tag") or "",
                "location": it.get("location") if it.get("location") in LOCATIONS else "apartment_couch",
                "hosts": it.get("hosts"),
                "moods": it.get("moods"),
                "when": when,
            })
    except Exception as e:
        print(f"festivals_extra.json skipped ({e})")
    return extras


def get_all_festivals():
    global _FESTIVALS_CACHE
    if _FESTIVALS_CACHE is None:
        _FESTIVALS_CACHE = FESTIVALS_BUILTIN + load_extra_festivals()
    return _FESTIVALS_CACHE


def find_nearby_festival(now_dt):
    today = now_dt.date()
    matches = []
    for fest in get_all_festivals():
        for yr in (today.year - 1, today.year, today.year + 1):
            try:
                f_date = fest["when"](yr)
            except Exception:
                f_date = None
            if f_date and abs((f_date - today).days) <= FESTIVAL_WINDOW_DAYS:
                matches.append({k: v for k, v in fest.items() if k != "when"})
                break
    return random.choice(matches) if matches else None


# ==============================================================================
# GENERIC HELPERS
# ==============================================================================
def build_https_url(host, path, query_params=None):
    query = urllib.parse.urlencode(query_params) if query_params else ""
    return urllib.parse.urlunparse(("https", host, path, "", query, ""))


def get_graph_host(token):
    if token.startswith(("IGA", "IGQ")):
        return "graph.instagram.com"
    return "graph.facebook.com"


def get_now():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            pass
    return datetime.now(timezone(timedelta(hours=-5)))


def season_context(now_dt):
    m = now_dt.month
    season = "winter" if m in (12, 1, 2) else "spring" if m in (3, 4, 5) else "summer" if m in (6, 7, 8) else "autumn"
    return f"{now_dt.strftime('%B')} ({season}). Everyday relatable young-couple life."


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


def _gemini_post(path, payload, timeout=40):
    url = build_https_url("generativelanguage.googleapis.com", path)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def discover_gemini_models():
    global _DISCOVERED_MODELS
    if _DISCOVERED_MODELS is not None:
        return _DISCOVERED_MODELS

    text_candidates = []
    tts_candidates = []
    try:
        url = build_https_url("generativelanguage.googleapis.com", "/v1beta/models")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "x-goog-api-key": GEMINI_API_KEY})
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
# HISTORY, DAILY BALANCING & ORGANIC CAST / DATE-AWARE PLANNER
# ==============================================================================
def _hist_path(slug):
    return pathlib.Path("posts") / slug / "history.json"


def load_story_history(slug, limit=150):
    hist_path = _hist_path(slug)
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return items[-limit:]
        except Exception:
            return []
    return []


def _load_all_history(slug):
    hist_path = _hist_path(slug)
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return items
        except Exception:
            pass
    return []


def save_story_record(slug, entry):
    hist_path = _hist_path(slug)
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    items = _load_all_history(slug)
    items.append(entry)
    hist_path.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


def update_story_record(slug, stamp, updates):
    hist_path = _hist_path(slug)
    items = _load_all_history(slug)
    for it in reversed(items):
        if it.get("timestamp") == stamp:
            it.update(updates)
            break
    hist_path.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


def write_history_table(slug, limit=300):
    items = _load_all_history(slug)[-limit:]
    lines = [
        "| # | Time | Lead | Couples | Mood | Festival | Hook | Setting | Sec | Posted |",
        "|---|------|------|---------|------|----------|------|---------|-----|--------|",
    ]

    def esc(v):
        return str(v if v is not None else "").replace("|", "/").replace("\n", " ")

    for i, h in enumerate(items, 1):
        lines.append(
            f"| {i} | {esc(h.get('timestamp'))} | {esc(h.get('lead_couple'))} | {esc(', '.join(h.get('couples', [])))} | "
            f"{esc(h.get('mood'))} | {esc(h.get('festival') or '-')} | {esc(h.get('hook'))} | {esc(h.get('environment'))} | "
            f"{esc(h.get('duration_sec', ''))} | {'yes' if h.get('posted') else 'no'} |"
        )
    pathlib.Path("posts", slug).mkdir(parents=True, exist_ok=True)
    pathlib.Path("posts", slug, "story_history_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plan_cast_and_premise(history_items, now_dt):
    today_str = now_dt.strftime("%Y-%m-%d")
    todays = [h for h in history_items if str(h.get("timestamp", "")).startswith(today_str)]
    by_id = {c["id"]: c for c in COUPLE_PROFILES}

    # Festival: about 3 of 10 daily reels are tied to a real nearby festival
    nearby = find_nearby_festival(now_dt)
    fest_today = sum(1 for h in todays if h.get("festival"))
    festival = nearby if (nearby and random.random() < (0.5 if fest_today < 3 else 0.1)) else None

    # Lead couple: host of the festival, least used today, never twice in a row when avoidable
    last_lead = history_items[-1].get("lead_couple") if history_items else None
    lead_counts = Counter(h.get("lead_couple") for h in todays)
    if festival and festival.get("hosts"):
        host_pool = [by_id[i] for i in festival["hosts"] if i in by_id] or list(COUPLE_PROFILES)
    else:
        host_pool = list(COUPLE_PROFILES)
    pool = [c for c in host_pool if c["label"] != last_lead] or host_pool
    lead = min(pool, key=lambda c: (lead_counts[c["label"]], random.random()))

    # Cast size: festivals lean crossover, everyday stories mostly one couple
    roll = random.random()
    if festival:
        num = 1 if roll < 0.40 else (2 if roll < 0.95 else 3)
    else:
        num = 1 if roll < 0.88 else (2 if roll < 0.99 else 3)
    others = [c for c in COUPLE_PROFILES if c["id"] != lead["id"]]
    guests = random.sample(others, k=num - 1) if num > 1 else []
    selected = [lead] + guests

    # Mood: least used today (within the festival's moods when there is one)
    last_mood = history_items[-1].get("mood") if history_items else None
    mood_counts = Counter(h.get("mood") for h in todays)
    mood_pool = festival.get("moods") if festival and festival.get("moods") else STORY_MOODS
    mood_candidates = [m for m in mood_pool if m != last_mood] or mood_pool
    mood = min(mood_candidates, key=lambda m: (mood_counts[m], random.random()))

    # Topic: not used in the last ~80 reels
    recent_topics = {str(h.get("topic", "")).strip().lower() for h in history_items[-80:]}
    topic_pool = [t for t in EVERGREEN_TOPICS if t.lower() not in recent_topics] or EVERGREEN_TOPICS
    topic = random.choice(topic_pool)

    return selected, mood, festival, topic


# ==============================================================================
# TEXT CLEANING
# ==============================================================================
_EMOJI_RE = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200d]")


def _clean_text(s, keep_emoji=False, strip_directions=True):
    s = str(s or "")
    if strip_directions:
        s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"[*_#`~<>|\\]+", "", s)
    if not keep_emoji:
        s = _EMOJI_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" \t\"'")
    return s


def _shorten_line(txt, max_words=MAX_WORDS_PER_LINE):
    words = txt.split()
    if len(words) <= max_words:
        return txt
    cut = words[:max_words]
    for i in range(len(cut) - 1, 4, -1):
        if cut[i][-1:] in ",;:.!?":
            cut = cut[: i + 1]
            break
    out = " ".join(cut).rstrip(",;:")
    if out[-1:] not in ".!?":
        out += "."
    return out


def _total_words(script):
    return sum(len(d["text"].split()) for b in script["beats"] for d in b["dialogue"])


def _trim_script_to_budget(script, budget=WORD_SOFT_MAX + 4):
    """Mechanical last resort: drop the longest middle lines until the draft fits the word budget."""
    guard = 0
    while _total_words(script) > budget and guard < 20:
        guard += 1
        lines = [(bi, di, len(d["text"].split())) for bi, b in enumerate(script["beats"]) for di, d in enumerate(b["dialogue"])]
        if len(lines) <= 6:
            break
        middle = lines[1:-1]
        bi, di, _ = max(middle, key=lambda x: x[2])
        script["beats"][bi]["dialogue"].pop(di)
        if not script["beats"][bi]["dialogue"]:
            script["beats"].pop(bi)
    return script


# ==============================================================================
# HASHTAGS (story-matched, 5-8 per reel, mostly fresh versus the previous reel)
# ==============================================================================
def _normalize_tag(t):
    tag = str(t).strip().lower()
    if not tag:
        return ""
    if not tag.startswith("#"):
        tag = "#" + tag.lstrip("#")
    tag = "".join(ch for ch in tag if ch.isalnum() or ch == "#")
    return tag if len(tag) > 2 else ""


def _enforce_hashtag_diversity(raw_tags, festival_obj, history_items, story_text=""):
    prev_tags = set()
    if history_items:
        prev_tags = {t.lower() for t in history_items[-1].get("hashtags", [])}

    clean = []
    fest_tag = _normalize_tag(festival_obj.get("tag", "")) if festival_obj else ""
    if fest_tag:
        clean.append(fest_tag)
    for t in (raw_tags or []):
        tag = _normalize_tag(t)
        if tag and tag not in clean:
            clean.append(tag)
    clean = clean[:8]

    text = (story_text or "").lower()
    relevant = [tag for tag, kws in SITUATIONAL_KEYWORDS.items() if any(k in text for k in kws)]
    random.shuffle(relevant)
    couple = list(HASHTAG_POOLS["couple"])
    broad = list(HASHTAG_POOLS["broad"])
    random.shuffle(couple)
    random.shuffle(broad)
    candidates = relevant + couple + broad

    def fresh_count():
        return sum(1 for t in clean if t not in prev_tags)

    # replace stale tags (never the festival tag) with fresh, story-matched ones
    for stale in [t for t in clean if t in prev_tags and t != fest_tag]:
        if fresh_count() * 2 >= len(clean):
            break
        repl = next((c for c in candidates if c not in clean and c not in prev_tags), None)
        if repl:
            clean[clean.index(stale)] = repl

    for cand in candidates:
        if len(clean) >= 7:
            break
        if cand not in clean and cand not in prev_tags:
            clean.append(cand)

    for cand in candidates:
        if len(clean) >= 5:
            break
        if cand not in clean:
            clean.append(cand)

    return clean[:8]


def _story_text_blob(hook, caption, core_joke, beats, setting, festival_name):
    parts = [hook, caption, core_joke, setting, festival_name or ""]
    for b in beats:
        parts.append(b.get("action", ""))
        for d in b["dialogue"]:
            parts.append(d["text"])
    return " ".join(str(p) for p in parts)


# ==============================================================================
# STORY SCRIPT GENERATOR (STORY-DRIVEN LENGTH, 5-BEAT ARC)
# ==============================================================================
def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def _fallback_story_script(selected_couples, mood, festival_obj, history_items):
    lead = selected_couples[0]
    him = lead["him"]["name"]
    her = lead["her"]["name"]
    is_crossover = len(selected_couples) >= 2

    if festival_obj:
        loc = festival_obj["location"]
        fest_name = festival_obj["name"]
        guest_str = f" & {selected_couples[1]['label']}" if is_crossover else ""
        g_him = selected_couples[1]["him"]["name"] if is_crossover else him
        g_her = selected_couples[1]["her"]["name"] if is_crossover else her
        beats = [
            {"arc_stage": "hook", "location": loc, "action": f"{her} welcomes everyone while {him} guards the dessert platter.",
             "camera": "group_wide", "dialogue": [
                 {"speaker": her, "text": f"Happy {fest_name}! Nobody touches dessert before dinner.", "emotion": "excited_wide"},
                 {"speaker": him, "text": "I was only quality-testing the sweets for safety.", "emotion": "smug_eyes_closed"}]},
            {"arc_stage": "setup", "location": loc, "action": "Everyone gathers around the festive dishes.",
             "camera": "focus_couple_1" if is_crossover else "focus_speaker", "dialogue": [
                 {"speaker": g_her, "text": "Everything smells incredible! What should we try first?", "emotion": "excited_wide"},
                 {"speaker": g_him, "text": "I skipped lunch just to prepare for tonight.", "emotion": "chill_smirk"}]},
            {"arc_stage": "escalation", "location": loc, "action": f"{him} sneaks a second plate while {her} spots him.",
             "camera": "focus_couple_0", "dialogue": [
                 {"speaker": her, "text": "Is that already your second plate?", "emotion": "skeptical"},
                 {"speaker": him, "text": "Technically it is the same plate, structurally upgraded.", "emotion": "deadpan"}]},
            {"arc_stage": "twist", "location": loc, "action": "The guests back him up with their own full plates.",
             "camera": "group_wide", "dialogue": [
                 {"speaker": g_her, "text": "To be fair, we hid three sweets in napkins.", "emotion": "chill_smirk"},
                 {"speaker": her, "text": "I cannot leave you unsupervised for two minutes!", "emotion": "exasperated"}]},
            {"arc_stage": "ending", "location": loc, "action": "Everyone laughs and raises a toast.",
             "camera": "group_wide", "dialogue": [
                 {"speaker": him, "text": f"Best {fest_name} crew ever. Pass the dessert!", "emotion": "soft_love_smile"}]},
        ]
        hook_title = f"{fest_name} Dinner With The Crew"
        core_joke = f"Sneaking festive desserts before dinner during {fest_name}"
        caption = f"When the {fest_name} snack table has zero survivors{guest_str}."
    else:
        loc = "mountain_trek" if "Destination" in mood else ("cafe_campus" if "Coffee" in mood else "apartment_couch")
        beats = [
            {"arc_stage": "hook", "location": loc, "action": f"{her} stares in disbelief at {him}'s giant backpack.",
             "camera": "group_wide", "dialogue": [
                 {"speaker": her, "text": "Babe, this is a two-hour trek, not Everest.", "emotion": "exasperated"},
                 {"speaker": him, "text": "You will thank me when we need emergency snacks.", "emotion": "smug_eyes_closed"}]},
            {"arc_stage": "setup", "location": loc, "action": f"{him} lists the gear he packed.",
             "camera": "focus_speaker", "dialogue": [
                 {"speaker": him, "text": "Three power banks, a tripod, and four sandwiches.", "emotion": "chill_smirk"},
                 {"speaker": her, "text": "Did you pack actual drinking water?", "emotion": "skeptical"}]},
            {"arc_stage": "escalation", "location": loc, "action": f"{him} freezes and checks the side pockets.",
             "camera": "focus_speaker", "dialogue": [
                 {"speaker": him, "text": "I brought iced coffee, which I drank in the parking lot.", "emotion": "deadpan"},
                 {"speaker": her, "text": "A full studio setup and zero water!", "emotion": "shocked"}]},
            {"arc_stage": "twist", "location": loc, "action": f"{her} pulls two chilled bottles from her tiny tote.",
             "camera": "focus_couple_0", "dialogue": [
                 {"speaker": her, "text": "Good thing I packed two waters.", "emotion": "smug_eyes_closed"},
                 {"speaker": him, "text": "See? That is why we are an elite team.", "emotion": "chill_smirk"}]},
            {"arc_stage": "ending", "location": loc, "action": "They share a laugh and trade a sandwich for water.",
             "camera": "group_wide", "dialogue": [
                 {"speaker": her, "text": "One bottle of water costs two sandwiches.", "emotion": "soft_love_smile"}]},
        ]
        hook_title = "Overpacking For A Simple Trek"
        core_joke = "Packing camera gear and snacks for a hike while forgetting water"
        caption = f"{him} & {her} proving two halves make one prepared hiker."

    blob = _story_text_blob(hook_title, caption, core_joke, beats, loc, festival_obj["name"] if festival_obj else "")
    tags = _enforce_hashtag_diversity([], festival_obj, history_items, blob)
    return {
        "source": "fallback",
        "couples": [c["label"] for c in selected_couples],
        "mood": mood,
        "tone": "Witty sitcom banter with warm boyfriend-girlfriend chemistry",
        "festival": festival_obj["name"] if festival_obj else None,
        "hook_title": hook_title,
        "setting": beats[0]["location"],
        "beats": beats,
        "music_prompt": "Warm mellow lo-fi electric piano with soft acoustic groove and gentle vinyl warmth",
        "caption": caption,
        "hashtags": tags,
        "history_entry": {"hook": hook_title, "environment": beats[0]["location"], "core_joke": core_joke},
    }


def normalize_story_json(raw, selected_couples, mood, festival_obj, history_items):
    """Returns a clean script dict, or None when the Gemini draft is unusable."""
    if not isinstance(raw, dict) or not isinstance(raw.get("beats"), list) or len(raw["beats"]) < 2:
        return None

    valid_names = {}
    for c in selected_couples:
        valid_names[c["him"]["name"].lower()] = c["him"]["name"]
        valid_names[c["her"]["name"].lower()] = c["her"]["name"]
    default_him = selected_couples[0]["him"]["name"]
    default_her = selected_couples[0]["her"]["name"]

    valid_cams = {"group_wide", "focus_couple_0", "focus_couple_1", "focus_couple_2", "focus_speaker"}
    clean_beats = []
    used_locations = []
    stage_names = ["hook", "setup", "escalation", "twist", "ending"]

    for b_idx, b in enumerate(raw["beats"][:6]):
        if not isinstance(b, dict):
            continue
        fallback_loc = used_locations[-1] if used_locations else (
            festival_obj["location"] if festival_obj else "apartment_couch")
        loc = b.get("location") if b.get("location") in LOCATIONS else fallback_loc
        if loc not in used_locations:
            if len(used_locations) >= 3:
                loc = used_locations[-1]
            else:
                used_locations.append(loc)

        cam = b.get("camera") if b.get("camera") in valid_cams else (
            "group_wide" if b_idx in (0, len(raw["beats"]) - 1) else "focus_speaker")
        if cam == "focus_couple_1" and len(selected_couples) < 2:
            cam = "focus_couple_0"
        if cam == "focus_couple_2" and len(selected_couples) < 3:
            cam = "focus_couple_0"

        d_lines = []
        for idx, d in enumerate(b.get("dialogue") or []):
            if not isinstance(d, dict):
                continue
            sp_raw = _clean_text(d.get("speaker"), strip_directions=False)
            sp = valid_names.get(sp_raw.lower(), default_him if idx % 2 == 0 else default_her)
            txt = _clean_text(d.get("text") or d.get("line") or "")
            if len(txt.split()) < 2:
                continue
            txt = _shorten_line(txt)
            emo = d.get("emotion") if d.get("emotion") in EMOTIONS else "chill_smirk"
            d_lines.append({"speaker": sp, "text": txt, "emotion": emo})

        if d_lines:
            clean_beats.append({
                "arc_stage": _clean_text(b.get("arc_stage") or stage_names[min(4, b_idx)], strip_directions=False) or stage_names[min(4, b_idx)],
                "location": loc,
                "action": _clean_text(b.get("action") or "Expressive conversation", strip_directions=False),
                "camera": cam,
                "dialogue": d_lines,
            })

    total_lines = sum(len(b["dialogue"]) for b in clean_beats)
    if len(clean_beats) < 2 or total_lines < 5:
        return None

    hook_words = _clean_text(raw.get("hook_title") or "", strip_directions=False).split()
    hook_title = " ".join(hook_words[:7]) if len(hook_words) >= 3 else "Couple Night Gone Sideways"

    hist_raw = raw.get("history_entry") if isinstance(raw.get("history_entry"), dict) else {}
    caption = _clean_text(raw.get("caption") or f"{hook_title} with {' & '.join(c['label'] for c in selected_couples)}.",
                          keep_emoji=True, strip_directions=False)
    core_joke = _clean_text(hist_raw.get("core_joke") or hook_title, strip_directions=False)
    blob = _story_text_blob(hook_title, caption, core_joke, clean_beats, clean_beats[0]["location"],
                            festival_obj["name"] if festival_obj else "")
    tags = _enforce_hashtag_diversity(raw.get("hashtags"), festival_obj, history_items, blob)

    return {
        "source": "gemini",
        "couples": [c["label"] for c in selected_couples],
        "mood": mood,
        "tone": _clean_text(raw.get("tone") or "Witty sitcom banter with boyfriend-girlfriend chemistry", strip_directions=False),
        "festival": festival_obj["name"] if festival_obj else None,
        "hook_title": hook_title,
        "setting": clean_beats[0]["location"],
        "beats": clean_beats,
        "music_prompt": _clean_text(raw.get("music_prompt") or "Soft warm lo-fi electric piano with gentle acoustic pulse", strip_directions=False),
        "caption": caption,
        "hashtags": tags,
        "history_entry": {
            "hook": _clean_text(hist_raw.get("hook") or hook_title, strip_directions=False),
            "environment": clean_beats[0]["location"],
            "core_joke": core_joke,
        },
    }


def _gemini_json(model, prompt, timeout=60):
    """Call Gemini for JSON. Tries thinking-off variants first (thinking tokens can truncate the JSON)."""
    last_err = None
    for thinking in ({"thinkingBudget": 0}, {"thinkingLevel": "low"}, None):
        gen_cfg = {"temperature": 1.0, "maxOutputTokens": 8192, "responseMimeType": "application/json"}
        if thinking:
            gen_cfg["thinkingConfig"] = thinking
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen_cfg}
        try:
            data = _gemini_post(f"/v1beta/models/{model}:generateContent", payload, timeout=timeout)
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return _extract_json_object(text)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 400:
                continue  # this model does not accept that thinking setting - try the next variant
            raise
    raise last_err


def generate_story_with_gemini(page_cfg, selected_couples, mood, festival_obj, suggested_topic, history_items, season_text):
    past_hooks = [f"- {h.get('hook', '')} ({h.get('core_joke', '')})" for h in history_items[-45:] if h.get("hook")]
    past_block = "\n".join(past_hooks) if past_hooks else "- None yet"

    recent_envs = [str(h.get("environment", "")) for h in history_items[-12:]]
    available = [l for l in LOCATIONS if l not in recent_envs] or list(LOCATIONS)
    mood_locs = [l for l in MOOD_LOCATIONS.get(mood, []) if l in available]
    if festival_obj and festival_obj["location"] not in available:
        available.append(festival_obj["location"])

    cast_desc = "\n".join(
        f"- Couple {i + 1}: {c['label']} (Boyfriend: {c['him']['name']}, Girlfriend: {c['her']['name']}) - {c['personality']}"
        for i, c in enumerate(selected_couples)
    )

    if festival_obj:
        host = selected_couples[0]
        fest_line = (
            f"FESTIVAL TIE-IN (happening within a few days of today): {festival_obj['name']}. "
            f"Suggested setting: {festival_obj['location']}. "
        )
        if festival_obj.get("hosts"):
            fest_line += f"The host couple is {host['label']} at their own home. "
        if len(selected_couples) > 1:
            guests = ", ".join(c["label"] for c in selected_couples[1:])
            fest_line += (f"Guest couple(s): {guests}, visiting for the festival. Guests try the food and customs, "
                          "get something cutely wrong, and everyone ends up laughing together. ")
        fest_line += "Keep it warm, curious and respectful: humor comes from situations and personalities, never from stereotypes."
    else:
        fest_line = "FESTIVAL: null (this is an everyday boyfriend-girlfriend story, NOT a holiday)."

    prompt = (
        f"Write a funny, relatable animated sitcom Reel script for {page_cfg['handle']}.\n"
        "STYLE: crisp ensemble sitcom pacing - natural boyfriend-girlfriend chemistry, clever misunderstandings, "
        "deadpan comebacks and sharp timing.\n\n"
        f"CAST IN THIS REEL ({len(selected_couples)} couple(s), boyfriend & girlfriend, NOT married):\n{cast_desc}\n\n"
        f"MOOD: {mood}\n{fest_line}\n"
        f"TOPIC SPARK (or invent a fresher situation): {suggested_topic}\n"
        f"SEASON: {season_text}\n"
        f"AVAILABLE SETTINGS (use 1 to 3 of these exact ids): {', '.join(available)}\n"
        f"GOOD FITS FOR THIS MOOD: {', '.join(mood_locs) if mood_locs else 'any available setting'}\n\n"
        "ALREADY USED HOOKS & JOKES (NEVER REPEAT OR REWORD):\n"
        f"{past_block}\n\n"
        "LENGTH IS DRIVEN BY THE STORY (very important):\n"
        "- Write only as many lines as the joke needs. A tight, punchy joke can be 6 lines (about 40 words, 15-20 seconds). "
        f"A fuller story may use up to 10 lines, but the TOTAL spoken words must never exceed {WORD_SOFT_MAX}.\n"
        "- NEVER pad, repeat, or stretch to fill time. If the joke lands early, end it there.\n"
        "- Every line is 4 to 11 words, one idea per line, easy to say out loud.\n"
        f"- Count your words before answering: total spoken words between 38 and {WORD_SOFT_MAX}.\n\n"
        "STORY RULES:\n"
        "1. Arc: hook, setup, escalation, twist, ending. Beats can have 1-3 lines each.\n"
        "2. Only the cast speaks. Do NOT mention or invent any other named people, real celebrities, athletes, brands, "
        "shows, songs or copyrighted characters. No news, politics or religion jokes. No stereotypes.\n"
        "3. Vary the ending: sometimes sweet and romantic, sometimes a pure comedic twist.\n"
        "4. hook_title is plain text, 3-7 words, no asterisks, no markdown, no emoji.\n"
        "5. Dialogue is plain spoken words only: no stage directions, no parentheses, no emoji, no markdown.\n\n"
        "Return ONLY valid JSON with exactly these keys:\n"
        "- couples: list of couple labels\n- mood: string\n- tone: string\n- festival: string or null\n"
        "- hook_title: bold 3-to-7-word hook title\n- setting: primary setting id\n"
        "- beats: list of 4 or 5 objects, each with:\n"
        "  - arc_stage ('hook','setup','escalation','twist','ending')\n"
        "  - location (one of the available setting ids)\n"
        "  - action (short stage direction)\n"
        "  - camera ('group_wide','focus_couple_0','focus_couple_1','focus_couple_2','focus_speaker')\n"
        "  - dialogue: list of { speaker (exact first name from cast), text, emotion }\n"
        "    Valid emotion: chill_smirk, smug_eyes_closed, deadpan, excited_wide, skeptical, exasperated, shocked, pout_frown, soft_love_smile\n"
        "- music_prompt: description of a soft lo-fi / romantic background track\n"
        "- caption: one-line Instagram caption describing the situation\n"
        "- hashtags: list of 5-8 hashtags that match THIS story (mix of broad comedy, couple, situation, festival if any)\n"
        "- history_entry: { hook, environment, core_joke }"
    )

    for model in discover_gemini_models()["text"]:
        strict_note = ""
        for attempt in range(2):
            try:
                parsed = _gemini_json(model, prompt + strict_note)
            except urllib.error.HTTPError as e:
                print(f"Gemini ({model}) skipped: HTTP {e.code}")
                break
            except Exception as e:
                print(f"Gemini ({model}) skipped: {e}")
                break

            script = normalize_story_json(parsed, selected_couples, mood, festival_obj, history_items)
            if script is None:
                print(f"Gemini ({model}) returned an unusable draft.")
                break

            words = _total_words(script)
            if words <= WORD_HARD_MAX:
                print(f"Generated story ({script['couples']} | {mood} | {words} words) via {model}: {script['hook_title']}")
                return script

            print(f"Draft too long ({words} words > {WORD_HARD_MAX}).")
            if attempt == 0:
                strict_note = (
                    f"\n\nIMPORTANT: your previous draft had {words} spoken words, which is far too long. "
                    f"Rewrite it tighter: total spoken words between 38 and {WORD_SOFT_MAX}, at most 8 lines, "
                    "each line 4 to 10 words. Keep the best joke, cut everything else."
                )
                continue
            script = _trim_script_to_budget(script)
            print(f"Trimmed mechanically to {_total_words(script)} words.")
            return script

    print("Gemini failed on every model - returning the fallback story (it will NOT be published).")
    return _fallback_story_script(selected_couples, mood, festival_obj, history_items)


# ==============================================================================
# VOICES (TTS CHAIN) + SILENCE TRIMMING + WORD-ACCURATE CAPTION ALIGNMENT
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
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts", "gtts"], check=False)


def _ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _synthesize_gemini_tts(line_text, char_cfg, out_wav):
    tts_models = discover_gemini_models()["tts"]
    last_err = None
    time.sleep(1.5)  # polite pacing against per-minute limits
    style = char_cfg["voice_style"].rstrip(":.") + ", at a brisk conversational pace:"

    for attempt_round in range(3):
        if attempt_round > 0:
            wait_sec = 10 * attempt_round
            print(f"Gemini TTS rate-limited; waiting {wait_sec}s before retry {attempt_round}/2...")
            time.sleep(wait_sec)

        saw_retryable = False
        for tts_model in tts_models:
            payload = {
                "contents": [{"parts": [{"text": f"{style} \"{line_text}\""}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": char_cfg["gemini_voice"]}}},
                },
            }
            try:
                data = _gemini_post(f"/v1beta/models/{tts_model}:generateContent", payload, timeout=40)
                parts = data["candidates"][0]["content"]["parts"]
                inline = next(p["inlineData"] for p in parts if "inlineData" in p)
                raw_bytes = base64.b64decode(inline["data"])
                mime_type = inline.get("mimeType", "").lower()

                raw_file = out_wav.with_suffix(".raw_gem")
                raw_file.write_bytes(raw_bytes)
                if "pcm" in mime_type or "l16" in mime_type or raw_bytes[:4] not in (b"RIFF", b"ID3\x03", b"OggS"):
                    _ffmpeg(["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(raw_file), "-ar", str(SR), "-ac", "1", str(out_wav)])
                else:
                    _ffmpeg(["-i", str(raw_file), "-ar", str(SR), "-ac", "1", str(out_wav)])
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
    comm = edge_tts.Communicate(text, voice, rate="+8%")
    await comm.save(str(out_mp3))


def _synthesize_gtts_fallback(text, is_male, out_wav):
    from gtts import gTTS
    mp3_path = out_wav.with_suffix(".gtts.mp3")
    gTTS(text=text, lang="en", slow=False).save(str(mp3_path))
    pitch_factor = 0.88 if is_male else 1.08
    atempo = 1.0 / pitch_factor
    _ffmpeg(["-i", str(mp3_path), "-af", f"asetrate=24000*{pitch_factor},aresample={SR},atempo={atempo:.3f}",
             "-ar", str(SR), "-ac", "1", str(out_wav)])


def _write_silence_wav(path, sr, dur):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * int(sr * dur))


def _synthesize_offline_last_resort(text, is_male, out_wav):
    espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if espeak_bin:
        raw_espeak = out_wav.with_suffix(".espeak.wav")
        voice_flag = "en-us+m3" if is_male else "en-us+f3"
        subprocess.run([espeak_bin, "-v", voice_flag, "-s", "160", "-w", str(raw_espeak), text],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _ffmpeg(["-i", str(raw_espeak), "-ar", str(SR), "-ac", "1", str(out_wav)])
        return
    dur = max(1.6, min(4.2, len(text.split()) * 0.34))
    _write_silence_wav(out_wav, SR, dur)


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
        _ffmpeg(["-i", str(mp3_path), "-ar", str(SR), "-ac", "1", str(raw_wav)])
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


def _read_mono_samples(path, sr=SR):
    """Read a wav as mono 16-bit samples at `sr`. Re-encodes first when the file is not already in that format,
    so the timeline always matches the real audio (this prevents drift)."""
    path = pathlib.Path(path)
    with wave.open(str(path), "r") as wf:
        ch, rate, width = wf.getnchannels(), wf.getframerate(), wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if ch != 1 or rate != sr or width != 2:
        fixed = path.with_suffix(".norm.wav")
        _ffmpeg(["-i", str(path), "-ar", str(sr), "-ac", "1", "-sample_fmt", "s16", str(fixed)])
        with wave.open(str(fixed), "r") as wf:
            raw = wf.readframes(wf.getnframes())
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def _energy_envelope(samples, win):
    """RMS per window of `win` samples (partial last window dropped)."""
    n = len(samples) // win
    if n <= 0:
        return []
    if np is not None:
        arr = np.frombuffer(samples, dtype=np.int16)[: n * win].astype(np.float64)
        return np.sqrt((arr.reshape(n, win) ** 2).mean(axis=1)).tolist()
    return [math.sqrt(sum(x * x for x in samples[i * win:(i + 1) * win]) / win) for i in range(n)]


def _trim_silence(samples, sr=SR):
    """Cut leading/trailing silence from a TTS clip (keeps ~40ms before and ~60ms after the voice)."""
    win = int(sr * 0.010)
    env = _energy_envelope(samples, win)
    if not env:
        return samples
    peak = max(env)
    thr = max(180.0, 0.05 * peak)
    idx = [i for i, v in enumerate(env) if v > thr]
    if not idx:
        return samples
    first = max(0, idx[0] - 4)
    last = min(len(env) - 1, idx[-1] + 6)
    return samples[first * win:(last + 1) * win]


def _syllables(word):
    core = re.sub(r"[^a-z0-9']", "", word.lower())
    if not core:
        return 1.0
    if core.isdigit():
        return max(2.0, len(core) / 1.5)
    groups = re.findall(r"[aeiouy]+", core)
    n = len(groups)
    if core.endswith("e") and n > 1 and not core.endswith(("le", "ee")):
        n -= 1
    return float(max(1, n))


def _align_words(words, samples, sr=SR):
    """Estimate (start, end) seconds for every word, relative to the start of the (trimmed) clip.

    Words are spread over the *voiced* part of the audio (silences and pauses are skipped), weighted by
    syllables. This follows the real rhythm of the voice far better than a straight-line interpolation."""
    n_words = len(words)
    if n_words == 0:
        return []
    total_dur = len(samples) / sr
    weights = [_syllables(w) + 0.10 * len(re.sub(r"\W", "", w)) for w in words]
    tw = sum(weights) or 1.0

    def even_split():
        out, acc = [], 0.0
        for wgt in weights:
            out.append((acc / tw * total_dur, (acc + wgt) / tw * total_dur))
            acc += wgt
        return out

    win = int(sr * 0.010)
    env = _energy_envelope(samples, win)
    if not env or max(env) < 60:
        return even_split()
    dt = win / sr
    thr = max(200.0, 0.07 * max(env))
    cum = [0.0]
    for v in env:
        cum.append(cum[-1] + (1.0 if v > thr else 0.0))
    voiced_total = cum[-1]
    if voiced_total < 3:
        return even_split()

    out, acc = [], 0.0
    for wgt in weights:
        f0 = acc / tw * voiced_total
        acc += wgt
        f1 = acc / tw * voiced_total
        k0 = min(len(env) - 1, max(0, bisect.bisect_right(cum, f0) - 1))
        k1 = min(len(env), bisect.bisect_left(cum, f1))
        s = k0 * dt
        e = min(total_dur, max(s + 0.05, k1 * dt))
        out.append((s, e))
    return out


def _caption_chunks(words, max_words=3):
    """Group words into short on-screen phrases that break at natural punctuation."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        end_sentence = w[-1:] in ".!?\u2026"
        end_clause = w[-1:] in ",;:"
        if len(cur) >= max_words or end_sentence or (end_clause and len(cur) >= 2):
            chunks.append((cur[0], cur[-1]))
            cur = []
    if cur:
        chunks.append((cur[0], cur[-1]))
    if len(chunks) >= 2 and chunks[-1][0] == chunks[-1][1]:
        prev = chunks[-2]
        if (prev[1] - prev[0] + 1) < max_words and words[prev[1]][-1:] not in ".!?\u2026":
            chunks[-2:] = [(prev[0], chunks[-1][1])]
    return chunks


def _mouth_envelope(samples, sr, total_turn_dur):
    win = int(sr / FPS)
    env = _energy_envelope(samples, win)
    nf = max(1, int(math.ceil(total_turn_dur * FPS)) + 1)
    peak = max(env) if env else 1.0
    out = []
    for i in range(nf):
        r = env[i] if i < len(env) else 0.0
        norm = min(1.0, r / max(800.0, peak * 0.68))
        out.append(0.0 if norm < 0.12 else norm)
    return out


# ==============================================================================
# MUSIC (optional music/ folder, else warm procedural lo-fi) + MIX WITH AUTO-DUCKING
# ==============================================================================
def _find_music_track(mood):
    root = pathlib.Path("music")
    if not root.is_dir():
        return None
    slug = re.sub(r"[^a-z0-9]+", "_", mood.lower()).strip("_")
    for folder in (root / slug, root):
        if not folder.is_dir():
            continue
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".flac")]
        if files:
            return random.choice(files)
    return None


def _synthesize_procedural_lofi_bed(music_prompt, mood, total_dur, sr, out_wav):
    low = f"{music_prompt} {mood}".lower()
    if any(k in low for k in ("romantic", "flirty", "dinner", "love", "sweet")):
        chords = [(174.61, 220.00, 261.63, 329.63), (164.81, 196.00, 246.94, 293.66),
                  (146.83, 174.61, 220.00, 261.63), (130.81, 164.81, 196.00, 246.94)]
        bar_sec = 2.4
    elif any(k in low for k in ("comedy", "upbeat", "sports", "cookout", "party")):
        chords = [(261.63, 329.63, 392.00, 493.88), (220.00, 261.63, 329.63, 392.00),
                  (174.61, 220.00, 261.63, 329.63), (196.00, 246.94, 293.66, 329.63)]
        bar_sec = 1.8
    else:
        chords = [(146.83, 185.00, 220.00, 277.18), (123.47, 146.83, 185.00, 220.00),
                  (196.00, 246.94, 293.66, 369.99), (220.00, 277.18, 329.63, 369.99)]
        bar_sec = 2.2

    total_samples = int(sr * total_dur)
    bar_samples = int(sr * bar_sec)

    if np is not None:
        idx = np.arange(total_samples)
        t = idx / sr
        bar_idx = (idx // bar_samples) % len(chords)
        bar_pos = (idx % bar_samples) / float(bar_samples)
        env = np.minimum(1.0, bar_pos * 14.0) * np.exp(-bar_pos * 1.15) * np.minimum(1.0, (1.0 - bar_pos) * 24.0)
        freqs = np.array(chords)[bar_idx]
        det = (1.0015, 0.9985, 1.0015, 0.9985)
        val = np.zeros(total_samples)
        for k in range(4):
            val += np.sin(2 * np.pi * freqs[:, k] * det[k] * t) * 0.22
            val += np.sin(4 * np.pi * freqs[:, k] * t) * 0.04
        val += np.sin(2 * np.pi * freqs[:, 0] * 0.5 * t) * 0.18
        base = val * env * 0.34
        left = np.clip(base * (1.0 + 0.05 * np.sin(t * 1.3)), -0.85, 0.85)
        right = np.clip(base * (1.0 - 0.05 * np.sin(t * 1.3)), -0.85, 0.85)
        stereo = (np.stack([left, right], axis=1) * 32767).astype("<i2")
        with wave.open(str(out_wav), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(stereo.tobytes())
        return

    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(total_samples):
            t = i / sr
            bar_idx = (i // bar_samples) % len(chords)
            bar_pos = (i % bar_samples) / float(bar_samples)
            env = min(1.0, bar_pos * 14.0) * math.exp(-bar_pos * 1.15) * min(1.0, (1.0 - bar_pos) * 24.0)
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


def _build_music_bed(script, dur, sr, tmp_dir):
    out = tmp_dir / "music_bed.wav"
    track = _find_music_track(script["mood"])
    if track is not None:
        try:
            _ffmpeg(["-stream_loop", "-1", "-i", str(track), "-t", f"{dur:.3f}", "-af", f"aresample={sr}",
                     "-ac", "2", str(out)])
            print(f"Music: {track.name}")
            return out
        except Exception as e:
            print(f"Music file failed ({e}), using procedural bed.")

    raw = tmp_dir / "music_raw.wav"
    _synthesize_procedural_lofi_bed(script["music_prompt"], script["mood"], dur, sr, raw)
    try:  # make the synth chords sound like warm, slightly worn lo-fi
        _ffmpeg([
            "-i", str(raw),
            "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.02:sample_rate={sr}:duration={dur:.3f}",
            "-filter_complex",
            "[0:a]lowpass=f=3600,highpass=f=70,vibrato=f=0.6:d=0.10,aecho=0.8:0.5:70:0.22[a];"
            "[1:a]highpass=f=1800,lowpass=f=7000,volume=0.22[n];"
            "[a][n]amix=inputs=2:duration=first:normalize=0[out]",
            "-map", "[out]", "-ar", str(sr), "-ac", "2", str(out),
        ])
    except Exception as e:
        print(f"Lo-fi filter skipped ({e}).")
        shutil.copy(raw, out)
    return out


def build_audio_and_timeline(script, selected_couples, tmp_dir):
    sr = SR
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

    # ---- Pass 1: synthesize every line and trim its silence ------------------------------------
    clips = []
    for idx, turn in enumerate(flat_turns):
        char_cfg, is_male, couple_idx = char_lookup.get(turn["speaker"], (selected_couples[0]["him"], True, 0))
        raw_wav = synthesize_character_voice(turn["text"], char_cfg, is_male, tmp_dir, idx)
        samples = _trim_silence(_read_mono_samples(raw_wav, sr), sr)
        if len(samples) < sr * 0.15:
            print(f"Line {idx}: empty audio, skipped.")
            continue
        clips.append({"turn": turn, "is_male": is_male, "couple_idx": couple_idx,
                      "samples": samples, "dur": len(samples) / sr})
    if not clips:
        raise RuntimeError("No usable voice audio was produced.")

    # ---- Pass 2: story-driven length. Never pad; only trim if the hard cap is exceeded ---------
    def total_len(cl):
        return LEAD_IN_SEC + sum(c["dur"] for c in cl) + LINE_GAP_SEC * max(0, len(cl) - 1) + END_HOLD_SEC

    dropped = 0
    while total_len(clips) > MAX_REEL_SEC and len(clips) > MIN_LINES_KEPT:
        drop_i = max(range(1, len(clips) - 1), key=lambda i: clips[i]["dur"])
        print(f"Over {MAX_REEL_SEC:.0f}s cap ({total_len(clips):.1f}s): dropping line '{clips[drop_i]['turn']['text']}'")
        clips.pop(drop_i)
        dropped += 1

    # ---- Pass 3: build timeline, per-word caption times and the voice track --------------------
    timeline = []
    padded_wavs = []
    cursor = LEAD_IN_SEC
    lead_wav = tmp_dir / "lead.wav"
    _write_silence_wav(lead_wav, sr, LEAD_IN_SEC)
    padded_wavs.append(lead_wav)

    for idx, clip in enumerate(clips):
        gap = END_HOLD_SEC if idx == len(clips) - 1 else LINE_GAP_SEC
        turn = clip["turn"]
        words = turn["text"].split()
        word_times = [(cursor + a, cursor + b) for a, b in _align_words(words, clip["samples"], sr)]
        total_turn = clip["dur"] + gap

        padded_wav = tmp_dir / f"line_{idx}_pad.wav"
        with wave.open(str(padded_wav), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(clip["samples"].tobytes() + b"\x00\x00" * int(sr * gap))
        padded_wavs.append(padded_wav)

        timeline.append({
            **turn,
            "couple_idx": clip["couple_idx"],
            "is_male": clip["is_male"],
            "start": cursor,
            "speech_end": cursor + clip["dur"],
            "end": cursor + total_turn,
            "words": words,
            "word_times": word_times,
            "chunks": _caption_chunks(words),
            "mouth_env": _mouth_envelope(clip["samples"], sr, total_turn),
        })
        cursor += total_turn

    concat_txt = tmp_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.name}'" for p in padded_wavs), encoding="utf-8")
    voice_wav = tmp_dir / "voice_all.wav"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_txt), "-ar", str(sr), "-ac", "2", str(voice_wav)])

    music_wav = _build_music_bed(script, cursor + 0.5, sr, tmp_dir)

    final_wav = tmp_dir / "final_audio.wav"
    fade_start = max(0.0, cursor - 0.9)
    _ffmpeg([
        "-i", str(voice_wav),
        "-i", str(music_wav),
        "-filter_complex",
        "[0:a]acompressor=threshold=-18dB:ratio=2.4:attack=15:release=120,volume=1.22,asplit=2[v_mix][v_sc];"
        "[1:a]volume=0.42[m_raw];"
        "[m_raw][v_sc]sidechaincompress=threshold=0.015:ratio=9:attack=35:release=320[m_ducked];"
        f"[v_mix][m_ducked]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={fade_start:.3f}:d=0.9[out]",
        "-map", "[out]", "-ar", str(sr), "-ac", "2", str(final_wav),
    ])

    info = {"duration": round(cursor, 2), "dropped_lines": dropped,
            "words": sum(len(t["words"]) for t in timeline), "lines": len(timeline)}
    return timeline, cursor, final_wav, info


# ==============================================================================
# SPRING PHYSICS, RICH ENVIRONMENTS & CARTOON CHARACTER RENDERER
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


def _draw_curved_sleeve_arm(draw, shoulder, elbow, wrist, sleeve_col, skin_col, width_px):
    ink = INK
    pts = _quad_bezier(shoulder, elbow, wrist, steps=14)
    draw.line(pts, fill=ink, width=width_px + 10 * SS, joint="curve")
    draw.line(pts, fill=sleeve_col, width=width_px, joint="curve")
    draw.ellipse([wrist[0] - width_px // 2, wrist[1] - width_px // 2, wrist[0] + width_px // 2, wrist[1] + width_px // 2],
                 fill=skin_col, outline=ink, width=4 * SS)


def _draw_cartoon_hand(draw, x, y, angle_deg, skin_col, spread=1.0, scale=1.0):
    ink = INK
    r = int(14 * scale * SS)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=skin_col, outline=ink, width=max(4 * SS, int(5 * scale * SS)))
    rad = math.radians(angle_deg)
    for f_off in (-0.42 * spread, -0.14 * spread, 0.14 * spread, 0.42 * spread):
        fa = rad + f_off
        fx = x + int(math.cos(fa) * 20 * scale * SS)
        fy = y + int(math.sin(fa) * 20 * scale * SS)
        draw.line([(x, y), (fx, fy)], fill=ink, width=max(4 * SS, int(5 * scale * SS)))


# ---- small drawing helper for the new backgrounds (coordinates are in 1080x1920 space) ------
class _Pen:
    def __init__(self, draw):
        self.d = draw

    @staticmethod
    def _w(width):
        return max(1, int(width * SS))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=5):
        self.d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill, outline=outline, width=self._w(width))

    def rrect(self, x0, y0, x1, y1, r=12, fill=None, outline=None, width=5):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=int(r * SS), fill=fill, outline=outline,
                                 width=self._w(width))

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, width=5):
        self.d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill, outline=outline, width=self._w(width))

    def pie(self, x0, y0, x1, y1, start, end, fill=None, outline=None, width=5):
        self.d.pieslice([x0 * SS, y0 * SS, x1 * SS, y1 * SS], start=start, end=end, fill=fill, outline=outline,
                        width=self._w(width))

    def arc(self, x0, y0, x1, y1, start, end, fill=INK, width=5):
        self.d.arc([x0 * SS, y0 * SS, x1 * SS, y1 * SS], start=start, end=end, fill=fill, width=self._w(width))

    def poly(self, pts, fill=None, outline=None):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill, outline=outline)

    def line(self, pts, fill=INK, width=5):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=self._w(width), joint="curve")

    def text(self, x, y, s, size, fill=(255, 255, 255), anchor="mm"):
        self.d.text((x * SS, y * SS), s, font=_load_font(max(8, int(size * SS))), fill=fill, anchor=anchor)


def _vgrad(p, y0, y1, c0, c1, step=4):
    span = max(1, y1 - y0)
    for y in range(y0, y1, step):
        f = (y - y0) / span
        col = tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
        p.rect(0, y, 1080, min(y1, y + step + 1), fill=col)


def _string_lights(p, x0, y0, x1, y1, n=10, col=(255, 236, 148)):
    p.arc(x0, y0, x1, y1, 0, 180, fill=INK, width=5)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    for i in range(1, n):
        a = math.pi * i / n
        bx, by = cx + rx * math.cos(a), cy + ry * math.sin(a)
        p.ell(bx - 11, by - 2, bx + 11, by + 26, fill=col, outline=INK, width=3)


def _cloud(p, cx, cy, s=1.0):
    for dx, dy, rx_, ry_ in ((-60, 8, 70, 34), (0, -14, 70, 44), (62, 10, 66, 32)):
        p.ell(cx + dx * s - rx_ * s, cy + dy * s - ry_ * s, cx + dx * s + rx_ * s, cy + dy * s + ry_ * s, fill=(255, 255, 255))


def _bg_city_rooftop_night(p):
    _vgrad(p, 0, 1140, (16, 18, 48), (122, 70, 124))
    rnd = random.Random(7)
    for _ in range(70):
        x, y, r = rnd.randint(20, 1060), rnd.randint(40, 560), rnd.choice((2, 3, 4))
        p.ell(x, y, x + r, y + r, fill=(255, 250, 222))
    p.ell(800, 280, 910, 390, fill=(252, 246, 214))
    p.ell(836, 304, 884, 352, fill=(236, 228, 196))
    rnd2 = random.Random(11)
    x = -20
    while x < 1080:
        bw_, bh_ = rnd2.randint(80, 160), rnd2.randint(260, 640)
        top = 1140 - bh_
        p.rect(x, top, x + bw_, 1140, fill=(32, 30, 68), outline=INK, width=4)
        for wy in range(top + 30, 1100, 48):
            for wx in range(x + 16, x + bw_ - 22, 32):
                if rnd2.random() < 0.55:
                    p.rect(wx, wy, wx + 14, wy + 22, fill=(255, 214, 128))
        x += bw_ + rnd2.randint(0, 12)
    p.rect(0, 1140, 1080, 1920, fill=(72, 64, 88), outline=INK, width=6)
    p.rect(0, 1096, 1080, 1110, fill=(132, 122, 150), outline=INK, width=3)
    for rx_ in range(30, 1080, 80):
        p.rect(rx_, 1110, rx_ + 10, 1146, fill=(132, 122, 150))
    _string_lights(p, 40, 250, 1040, 470, n=11)


def _bg_palace_garden(p):
    _vgrad(p, 0, 1140, (150, 206, 240), (252, 232, 200))
    p.ell(60, 120, 260, 320, fill=(255, 244, 190))
    for cx, cy in ((720, 190), (930, 330), (330, 430)):
        _cloud(p, cx, cy, 0.9)
    cream, gold, blue = (244, 232, 206), (220, 178, 86), (98, 150, 190)
    for tx in (120, 880):
        p.rect(tx, 560, tx + 80, 1060, fill=cream, outline=INK, width=5)
        p.pie(tx - 4, 500, tx + 84, 620, 180, 360, fill=gold, outline=INK, width=5)
        p.line([(tx + 40, 505), (tx + 40, 450)], fill=INK, width=5)
    p.rect(230, 780, 850, 1080, fill=cream, outline=INK, width=6)
    p.rect(420, 650, 660, 790, fill=cream, outline=INK, width=6)
    p.pie(380, 470, 700, 790, 180, 360, fill=gold, outline=INK, width=6)
    p.line([(540, 475), (540, 410)], fill=INK, width=6)
    p.ell(528, 392, 552, 416, fill=gold, outline=INK, width=4)
    for dx in (260, 760):
        p.pie(dx, 700, dx + 120, 820, 180, 360, fill=gold, outline=INK, width=5)
    for ax in range(270, 800, 110):
        p.rect(ax, 900, ax + 70, 1080, fill=blue, outline=INK, width=4)
        p.pie(ax, 866, ax + 70, 934, 180, 360, fill=blue, outline=INK, width=4)
    p.rect(0, 1040, 1080, 1140, fill=(70, 140, 84), outline=INK, width=5)
    for hx in range(30, 1080, 120):
        p.ell(hx, 1010, hx + 100, 1090, fill=(84, 158, 96), outline=INK, width=4)
    p.rect(0, 1140, 1080, 1920, fill=(214, 194, 160), outline=INK, width=6)
    p.poly([(440, 1140), (640, 1140), (900, 1920), (180, 1920)], fill=(236, 220, 190), outline=INK)


def _bg_beach_sunset(p):
    _vgrad(p, 0, 760, (255, 176, 108), (248, 112, 132))
    p.ell(400, 520, 680, 800, fill=(255, 232, 160))
    _vgrad(p, 760, 1040, (246, 150, 120), (64, 112, 170))
    for i, wd in enumerate((300, 220, 160, 110)):
        y = 800 + i * 55
        p.rect(540 - wd, y, 540 + wd, y + 8, fill=(255, 224, 170))
    p.rect(0, 1040, 1080, 1920, fill=(238, 210, 162), outline=INK, width=6)
    for wx in range(-40, 1100, 180):
        p.arc(wx, 1010, wx + 180, 1070, 0, 180, fill=(255, 255, 255), width=6)
    p.line([(120, 1140), (140, 940), (190, 760)], fill=(120, 84, 52), width=26)
    for dx, dy in ((-190, 50), (-130, -60), (130, -70), (200, 40), (0, -100)):
        p.poly([(190, 760), (190 + dx * 0.5, 760 + dy * 0.5 - 30), (190 + dx, 760 + dy), (190 + dx * 0.5, 760 + dy * 0.5 + 30)],
               fill=(54, 130, 80), outline=INK)
    p.ell(850, 1010, 1010, 1100, fill=(230, 80, 90), outline=INK, width=5)  # beach ball
    p.arc(850, 1010, 1010, 1100, 200, 340, fill=(255, 255, 255), width=8)


def _bg_airport_terminal(p):
    p.rect(0, 0, 1080, 1920, fill=(226, 232, 240))
    _vgrad(p, 280, 820, (150, 200, 240), (222, 238, 250))
    p.ell(360, 520, 760, 590, fill=(250, 250, 252), outline=INK, width=4)
    p.poly([(520, 545), (640, 430), (690, 430), (620, 550)], fill=(210, 216, 226), outline=INK)
    p.poly([(700, 530), (770, 450), (800, 450), (770, 545)], fill=(196, 60, 60), outline=INK)
    for gx in (300, 540, 780):
        p.line([(gx, 280), (gx, 820)], fill=(90, 100, 118), width=8)
    p.rect(70, 280, 1010, 820, outline=(90, 100, 118), width=12)
    for lx in range(120, 1000, 240):
        p.rrect(lx, 60, lx + 160, 100, r=10, fill=(255, 250, 228), outline=INK, width=3)
    p.rrect(340, 140, 740, 240, r=16, fill=(32, 58, 110), outline=INK, width=5)
    p.text(540, 190, "GATE 12", 54, fill=(255, 226, 90))
    p.rect(0, 1140, 1080, 1920, fill=(176, 184, 198), outline=INK, width=6)
    p.rect(0, 1190, 1080, 1210, fill=(250, 200, 60))
    p.rrect(50, 1000, 190, 1140, r=16, fill=(196, 60, 60), outline=INK, width=5)
    p.line([(120, 1000), (120, 960)], fill=INK, width=6)
    p.rrect(900, 1030, 1020, 1140, r=14, fill=(60, 110, 170), outline=INK, width=5)
    p.line([(960, 1030), (960, 995)], fill=INK, width=6)


def _bg_road_trip_scenic(p):
    _vgrad(p, 0, 760, (140, 200, 240), (255, 226, 190))
    p.poly([(0, 760), (220, 520), (460, 760)], fill=(150, 128, 170), outline=INK)
    p.poly([(300, 760), (620, 460), (980, 760)], fill=(128, 108, 156), outline=INK)
    p.poly([(700, 760), (930, 560), (1080, 640), (1080, 760)], fill=(160, 138, 176), outline=INK)
    p.ell(100, 150, 240, 290, fill=(255, 240, 180))
    p.rect(0, 760, 1080, 1920, fill=(206, 176, 128), outline=INK, width=6)
    p.poly([(500, 760), (580, 760), (1000, 1920), (80, 1920)], fill=(74, 76, 88), outline=INK)
    for y, h in ((800, 20), (850, 28), (925, 38), (1030, 54), (1170, 76), (1360, 106), (1620, 150)):
        hw = 4 + (y - 760) * 0.012
        p.poly([(540 - hw, y), (540 + hw, y), (540 + hw * 1.2, y + h), (540 - hw * 1.2, y + h)], fill=(250, 214, 80))
    for cx, cy in ((110, 1010), (980, 960)):
        p.rrect(cx - 20, cy - 150, cx + 20, cy + 100, r=18, fill=(70, 140, 80), outline=INK, width=5)
        p.rrect(cx - 60, cy - 90, cx - 20, cy - 60, r=14, fill=(70, 140, 80), outline=INK, width=4)
        p.rrect(cx + 20, cy - 60, cx + 58, cy - 32, r=14, fill=(70, 140, 80), outline=INK, width=4)
    p.rect(860, 830, 876, 1010, fill=(120, 84, 52), outline=INK, width=4)
    p.rrect(790, 800, 1010, 880, r=10, fill=(236, 200, 90), outline=INK, width=5)
    p.text(900, 840, "ROAD TRIP", 38, fill=INK)


def _bg_kitchen_cooking(p):
    p.rect(0, 0, 1080, 1920, fill=(240, 228, 206))
    for x in range(0, 1080, 90):
        p.line([(x, 300), (x, 1000)], fill=(214, 198, 172), width=3)
    for y in range(300, 1000, 90):
        p.line([(0, y), (1080, y)], fill=(214, 198, 172), width=3)
    p.rect(110, 330, 450, 700, fill=(190, 226, 244), outline=(118, 84, 58), width=9)
    p.line([(280, 330), (280, 700)], fill=(118, 84, 58), width=7)
    p.line([(110, 515), (450, 515)], fill=(118, 84, 58), width=7)
    p.ell(140, 560, 240, 660, fill=(70, 150, 84), outline=INK, width=4)
    p.rrect(150, 640, 230, 720, r=10, fill=(190, 102, 70), outline=INK, width=4)
    p.rect(520, 300, 1080, 560, fill=(176, 128, 86), outline=INK, width=6)
    for x in (530, 805):
        p.rect(x, 316, x + 262, 544, outline=(120, 84, 52), width=5)
    for x in (770, 810):
        p.ell(x, 420, x + 16, 436, fill=(236, 204, 120), outline=INK, width=3)
    p.line([(560, 620), (1000, 620)], fill=INK, width=6)
    for x in (600, 680, 760, 840, 920):
        p.line([(x, 620), (x, 700)], fill=INK, width=5)
        p.ell(x - 18, 700, x + 18, 740, fill=(190, 190, 200), outline=INK, width=4)
    p.rect(0, 1000, 1080, 1140, fill=(168, 122, 84), outline=INK, width=7)
    p.rect(0, 990, 1080, 1030, fill=(222, 210, 190), outline=INK, width=6)
    p.rrect(380, 940, 700, 1000, r=10, fill=(70, 74, 86), outline=INK, width=5)
    p.rrect(430, 850, 650, 945, r=14, fill=(196, 200, 210), outline=INK, width=6)
    for sx in (470, 540, 610):
        p.arc(sx - 20, 760, sx + 20, 850, 200, 340, fill=(250, 250, 252), width=6)
    for gx, x in enumerate(range(0, 1080, 120)):
        for gy, y in enumerate(range(1140, 1920, 120)):
            p.rect(x, y, x + 120, y + 120, fill=(226, 190, 150) if (gx + gy) % 2 == 0 else (196, 120, 90))


def _bg_snowy_window_christmas(p):
    p.rect(0, 0, 1080, 1920, fill=(176, 112, 92))
    for x in range(0, 1080, 90):
        p.rect(x, 0, x + 40, 1140, fill=(184, 120, 98))
    p.rect(80, 300, 460, 860, fill=(30, 44, 92), outline=(118, 84, 58), width=12)
    rnd = random.Random(3)
    for _ in range(50):
        x, y = rnd.randint(95, 445), rnd.randint(315, 845)
        p.ell(x, y, x + 8, y + 8, fill=(255, 255, 255))
    p.line([(270, 300), (270, 860)], fill=(118, 84, 58), width=8)
    p.line([(80, 580), (460, 580)], fill=(118, 84, 58), width=8)
    p.rect(60, 860, 480, 900, fill=(250, 250, 255), outline=INK, width=5)
    p.arc(60, 230, 480, 380, 0, 180, fill=(42, 112, 64), width=18)
    for bx in (120, 200, 280, 360, 430):
        p.ell(bx - 9, 330 + int(34 * math.sin((bx - 60) / 420 * math.pi)), bx + 9, 348 + int(34 * math.sin((bx - 60) / 420 * math.pi)),
              fill=(210, 40, 50), outline=INK, width=2)
    for w, y in ((260, 520), (340, 660), (420, 800), (470, 940)):
        p.poly([(860, y - 150), (860 - w / 2, y + 40), (860 + w / 2, y + 40)], fill=(40, 120, 66), outline=INK)
    p.poly([(860, 330), (872, 362), (906, 362), (878, 382), (890, 416), (860, 396), (830, 416), (842, 382), (814, 362), (848, 362)],
           fill=(255, 220, 70), outline=INK)
    rnd2 = random.Random(5)
    for _ in range(14):
        oy = rnd2.randint(480, 980)
        half = 30 + (oy - 400) * 0.25
        ox = 860 + rnd2.randint(-int(half), int(half))
        p.ell(ox - 12, oy - 12, ox + 12, oy + 12, fill=rnd2.choice([(210, 40, 50), (240, 190, 50), (70, 130, 220)]), outline=INK, width=3)
    p.rect(0, 1140, 1080, 1920, fill=(150, 108, 76), outline=INK, width=6)
    for y in range(1200, 1920, 60):
        p.line([(0, y), (1080, y)], fill=(130, 92, 64), width=3)
    p.ell(180, 1110, 900, 1270, fill=(176, 50, 56), outline=INK, width=5)
    for gx, col in ((700, (60, 110, 200)), (780, (240, 190, 50)), (960, (60, 160, 100))):
        p.rect(gx, 1060, gx + 70, 1140, fill=col, outline=INK, width=4)
        p.rect(gx + 30, 1060, gx + 40, 1140, fill=(250, 250, 250))


def _bg_park_picnic(p):
    _vgrad(p, 0, 820, (146, 204, 246), (214, 238, 252))
    for cx, cy in ((220, 260), (700, 200), (900, 380)):
        _cloud(p, cx, cy)
    p.poly([(0, 820), (0, 640), (260, 560), (520, 700), (780, 580), (1080, 700), (1080, 820)], fill=(120, 176, 104), outline=INK)
    for tx in (90, 960):
        p.rect(tx - 18, 700, tx + 18, 940, fill=(120, 84, 52), outline=INK, width=5)
        p.ell(tx - 120, 500, tx + 120, 760, fill=(66, 140, 80), outline=INK, width=5)
        p.ell(tx - 70, 440, tx + 70, 600, fill=(84, 160, 96), outline=INK, width=5)
    p.rect(0, 900, 1080, 1920, fill=(112, 184, 92), outline=INK, width=6)
    p.poly([(150, 1070), (930, 1070), (1010, 1270), (70, 1270)], fill=(238, 238, 242), outline=INK)
    rows = 5
    for r_ in range(rows):
        y0 = 1070 + r_ * 40
        y1 = y0 + 40
        lx0 = 150 - 80 * (y0 - 1070) / 200
        rx0 = 930 + 80 * (y0 - 1070) / 200
        cw = (rx0 - lx0) / 14
        for c_ in range(14):
            if (r_ + c_) % 2 == 0:
                p.rect(int(lx0 + c_ * cw), y0, int(lx0 + (c_ + 1) * cw), y1, fill=(214, 70, 70))
    p.rrect(780, 1000, 920, 1100, r=14, fill=(176, 128, 78), outline=INK, width=5)
    p.arc(800, 950, 900, 1050, 180, 360, fill=INK, width=6)


def _bg_festival_holi(p):
    p.rect(0, 0, 1080, 1920, fill=(246, 238, 226))
    cols = [(236, 72, 140), (250, 196, 40), (56, 168, 222), (92, 196, 96), (150, 80, 200), (250, 120, 50)]
    rnd = random.Random(21)
    for _ in range(26):
        x, y, r = rnd.randint(0, 1080), rnd.randint(260, 900), rnd.randint(50, 130)
        c = rnd.choice(cols)
        p.ell(x - r, y - r, x + r, y + r, fill=c)
        lc = tuple((v + 255) // 2 for v in c)
        p.ell(x - r * 0.6, y - r * 0.6, x + r * 0.6, y + r * 0.6, fill=lc)
    p.arc(20, 150, 1060, 380, 0, 180, fill=INK, width=4)
    for i in range(1, 14):
        a = math.pi * i / 14
        bx, by = 540 + 520 * math.cos(a), 265 + 115 * math.sin(a)
        p.poly([(bx - 22, by), (bx + 22, by), (bx, by + 50)], fill=cols[i % len(cols)], outline=INK)
    p.rect(0, 1140, 1080, 1920, fill=(196, 172, 146), outline=INK, width=6)
    rnd2 = random.Random(8)
    for _ in range(14):
        x, y = rnd2.randint(40, 1040), rnd2.randint(1180, 1500)
        w_, h_ = rnd2.randint(60, 150), rnd2.randint(20, 50)
        p.ell(x - w_, y - h_, x + w_, y + h_, fill=rnd2.choice(cols))


_NEW_BACKGROUNDS = {
    "city_rooftop_night": _bg_city_rooftop_night,
    "palace_garden": _bg_palace_garden,
    "beach_sunset": _bg_beach_sunset,
    "airport_terminal": _bg_airport_terminal,
    "road_trip_scenic": _bg_road_trip_scenic,
    "kitchen_cooking": _bg_kitchen_cooking,
    "snowy_window_christmas": _bg_snowy_window_christmas,
    "park_picnic": _bg_park_picnic,
    "festival_holi": _bg_festival_holi,
}


def render_location_background(location):
    """Returns the background at full 2x resolution (no down/up-scaling, so close-ups stay sharp)."""
    bw, bh = W * SS, H * SS
    ink = INK

    if location in _NEW_BACKGROUNDS:
        img = Image.new("RGB", (bw, bh), (255, 255, 255))
        _NEW_BACKGROUNDS[location](_Pen(ImageDraw.Draw(img)))
        return img

    if location == "mountain_trek":
        img = Image.new("RGB", (bw, bh), (252, 184, 126))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, bw, 540 * SS], fill=(244, 148, 118))
        draw.ellipse([390 * SS, 520 * SS, 690 * SS, 820 * SS], fill=(255, 236, 158))
        draw.polygon([(0, 940 * SS), (280 * SS, 620 * SS), (560 * SS, 940 * SS)], fill=(138, 122, 156), outline=ink)
        draw.polygon([(420 * SS, 940 * SS), (760 * SS, 580 * SS), (bw, 940 * SS)], fill=(118, 104, 142), outline=ink)
        draw.polygon([(280 * SS, 620 * SS), (225 * SS, 685 * SS), (265 * SS, 675 * SS), (295 * SS, 692 * SS), (335 * SS, 685 * SS)], fill=(248, 248, 252))
        draw.polygon([(760 * SS, 580 * SS), (695 * SS, 655 * SS), (745 * SS, 645 * SS), (780 * SS, 662 * SS), (825 * SS, 655 * SS)], fill=(248, 248, 252))
        draw.rectangle([0, 920 * SS, bw, 1180 * SS], fill=(84, 134, 92), outline=ink, width=6 * SS)
        for tx in (110, 210, 880, 970):
            draw.polygon([(tx * SS, 790 * SS), ((tx - 48) * SS, 935 * SS), ((tx + 48) * SS, 935 * SS)], fill=(52, 96, 64), outline=ink)
        draw.rectangle([0, 1140 * SS, bw, bh], fill=(208, 186, 156), outline=ink, width=6 * SS)
        draw.rectangle([90 * SS, 970 * SS, 112 * SS, 1160 * SS], fill=(132, 92, 58), outline=ink, width=5 * SS)
        draw.rounded_rectangle([48 * SS, 985 * SS, 195 * SS, 1032 * SS], radius=8 * SS, fill=(168, 122, 78), outline=ink, width=5 * SS)

    elif location == "cafe_campus":
        img = Image.new("RGB", (bw, bh), (236, 222, 202))
        draw = ImageDraw.Draw(img)
        draw.rectangle([80 * SS, 290 * SS, 640 * SS, 820 * SS], fill=(204, 232, 244), outline=(112, 82, 58), width=9 * SS)
        draw.line([(360 * SS, 290 * SS), (360 * SS, 820 * SS)], fill=(112, 82, 58), width=8 * SS)
        draw.rounded_rectangle([685 * SS, 320 * SS, 1005 * SS, 740 * SS], radius=16 * SS, fill=(42, 48, 52), outline=(136, 98, 64), width=10 * SS)
        for ly in (390, 460, 530, 600):
            draw.line([(725 * SS, ly * SS), (960 * SS, ly * SS)], fill=(238, 234, 222), width=6 * SS)
        draw.text((845 * SS, 355 * SS), "MENU", font=_load_font(40 * SS), fill=(238, 234, 222), anchor="mm")
        for ly, word in ((380, "LATTE"), (450, "MOCHA"), (520, "CHAI"), (590, "MATCHA")):
            draw.text((730 * SS, ly * SS), word, font=_load_font(28 * SS), fill=(236, 214, 150), anchor="ls")
        for lx in (250, 520):
            draw.line([(lx * SS, 0), (lx * SS, 330 * SS)], fill=ink, width=6 * SS)
            draw.pieslice([(lx - 52) * SS, 310 * SS, (lx + 52) * SS, 382 * SS], start=180, end=360, fill=(214, 148, 72), outline=ink, width=6 * SS)
        draw.rectangle([0, 1120 * SS, bw, bh], fill=(176, 138, 102), outline=ink, width=6 * SS)
        draw.rounded_rectangle([120 * SS, 1110 * SS, 960 * SS, 1195 * SS], radius=22 * SS, fill=(166, 122, 82), outline=ink, width=8 * SS)

    elif location == "dinner_candlelight":
        img = Image.new("RGB", (bw, bh), (44, 28, 40))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([120 * SS, 260 * SS, 960 * SS, 860 * SS], radius=32 * SS, fill=(62, 40, 56), outline=(98, 68, 84), width=8 * SS)
        for bx, by, br, col in [(240, 390, 26, (255, 198, 110)), (440, 340, 20, (255, 165, 115)), (680, 420, 30, (255, 205, 125)), (840, 360, 22, (255, 180, 130))]:
            draw.ellipse([(bx - br) * SS, (by - br) * SS, (bx + br) * SS, (by + br) * SS], fill=col)
        draw.rectangle([0, 1120 * SS, bw, bh], fill=(64, 42, 34), outline=ink, width=6 * SS)
        draw.ellipse([110 * SS, 1085 * SS, 970 * SS, 1245 * SS], fill=(238, 228, 218), outline=ink, width=8 * SS)
        draw.ellipse([495 * SS, 1015 * SS, 585 * SS, 1105 * SS], fill=(255, 224, 145))
        draw.rectangle([530 * SS, 1070 * SS, 550 * SS, 1140 * SS], fill=(248, 244, 236), outline=ink, width=5 * SS)
        draw.ellipse([533 * SS, 1044 * SS, 547 * SS, 1068 * SS], fill=(255, 185, 45))

    elif location == "festival_diwali_home":
        img = Image.new("RGB", (bw, bh), (236, 198, 148))
        draw = ImageDraw.Draw(img)
        for gx in range(90, W, 180):
            draw.arc([gx * SS, 220 * SS, (gx + 180) * SS, 370 * SS], start=0, end=180, fill=(246, 142, 28), width=16 * SS)
            draw.ellipse([(gx + 82) * SS, 355 * SS, (gx + 98) * SS, 375 * SS], fill=(255, 234, 128))
        draw.rounded_rectangle([180 * SS, 390 * SS, 900 * SS, 1120 * SS], radius=140 * SS, fill=(214, 166, 114), outline=(156, 88, 42), width=10 * SS)
        draw.rectangle([0, 1120 * SS, bw, bh], fill=(168, 118, 78), outline=ink, width=7 * SS)
        for dx in (220, 540, 860):
            draw.pieslice([(dx - 28) * SS, 1100 * SS, (dx + 28) * SS, 1138 * SS], start=0, end=180, fill=(186, 78, 46), outline=ink, width=4 * SS)
            draw.ellipse([(dx - 8) * SS, 1078 * SS, (dx + 8) * SS, 1102 * SS], fill=(255, 212, 68))

    elif location == "festival_thanksgiving_harvest":
        img = Image.new("RGB", (bw, bh), (226, 196, 162))
        draw = ImageDraw.Draw(img)
        draw.arc([80 * SS, 230 * SS, 1000 * SS, 410 * SS], start=0, end=180, fill=(188, 86, 42), width=14 * SS)
        for lx, col in [(220, (218, 128, 38)), (390, (176, 62, 42)), (540, (226, 156, 48)), (710, (176, 62, 42)), (860, (218, 128, 38))]:
            draw.ellipse([(lx - 18) * SS, 385 * SS, (lx + 18) * SS, 415 * SS], fill=col)
        draw.rectangle([0, 1120 * SS, bw, bh], fill=(164, 122, 84), outline=ink, width=7 * SS)
        draw.rounded_rectangle([110 * SS, 1110 * SS, 970 * SS, 1205 * SS], radius=24 * SS, fill=(242, 232, 216), outline=ink, width=8 * SS)
        draw.ellipse([490 * SS, 1072 * SS, 550 * SS, 1118 * SS], fill=(228, 118, 42), outline=ink, width=5 * SS)
        draw.ellipse([545 * SS, 1080 * SS, 595 * SS, 1118 * SS], fill=(238, 168, 56), outline=ink, width=5 * SS)

    elif location == "festival_lunar_chuseok":
        img = Image.new("RGB", (bw, bh), (234, 214, 188))
        draw = ImageDraw.Draw(img)
        for lx in (240, 540, 840):
            draw.line([(lx * SS, 0), (lx * SS, 290 * SS)], fill=ink, width=5 * SS)
            draw.ellipse([(lx - 48) * SS, 285 * SS, (lx + 48) * SS, 395 * SS], fill=(208, 46, 46), outline=(238, 188, 64), width=6 * SS)
            draw.line([(lx * SS, 395 * SS), (lx * SS, 435 * SS)], fill=(238, 188, 64), width=6 * SS)
        draw.rectangle([0, 1120 * SS, bw, bh], fill=(166, 124, 86), outline=ink, width=7 * SS)
        draw.rounded_rectangle([120 * SS, 1110 * SS, 960 * SS, 1200 * SS], radius=24 * SS, fill=(142, 64, 54), outline=ink, width=8 * SS)

    elif location == "cookout_backyard":
        img = Image.new("RGB", (bw, bh), (176, 218, 240))
        draw = ImageDraw.Draw(img)
        draw.arc([40 * SS, 230 * SS, 1040 * SS, 400 * SS], start=0, end=180, fill=ink, width=6 * SS)
        for bx in range(130, 980, 115):
            draw.ellipse([(bx - 12) * SS, 375 * SS, (bx + 12) * SS, 402 * SS], fill=(255, 236, 148), outline=ink, width=3 * SS)
        draw.rectangle([0, 980 * SS, bw, 1150 * SS], fill=(92, 164, 88), outline=ink, width=6 * SS)
        draw.rectangle([0, 1150 * SS, bw, bh], fill=(196, 184, 166), outline=ink, width=6 * SS)

    elif location in ("movie_living_room", "sports_hangout"):
        wall_col = (54, 62, 84) if location == "movie_living_room" else (214, 206, 194)
        img = Image.new("RGB", (bw, bh), wall_col)
        draw = ImageDraw.Draw(img)
        screen_col = (128, 178, 236) if location == "movie_living_room" else (84, 168, 92)
        draw.rounded_rectangle([240 * SS, 330 * SS, 840 * SS, 670 * SS], radius=18 * SS, fill=screen_col, outline=ink, width=9 * SS)
        draw.rectangle([0, 1130 * SS, bw, bh], fill=(142, 112, 86), outline=ink, width=7 * SS)
        draw.rounded_rectangle([120 * SS, 820 * SS, 960 * SS, 1210 * SS], radius=42 * SS, fill=(116, 134, 102), outline=ink, width=8 * SS)

    else:  # apartment_couch
        img = Image.new("RGB", (bw, bh), (224, 210, 188))
        draw = ImageDraw.Draw(img)
        draw.arc([60 * SS, 230 * SS, 1020 * SS, 385 * SS], start=0, end=180, fill=(110, 92, 74), width=5 * SS)
        for bx in range(140, 960, 120):
            draw.ellipse([(bx - 10) * SS, 365 * SS, (bx + 10) * SS, 388 * SS], fill=(255, 232, 146))
        draw.rectangle([85 * SS, 395 * SS, 345 * SS, 685 * SS], fill=(138, 116, 94), outline=ink, width=8 * SS)
        draw.rectangle([105 * SS, 415 * SS, 325 * SS, 665 * SS], fill=(176, 198, 172), outline=ink, width=5 * SS)
        draw.rectangle([825 * SS, 440 * SS, bw, 1160 * SS], fill=(154, 112, 74), outline=ink, width=8 * SS)
        for sy in (620, 800, 980):
            draw.line([(825 * SS, sy * SS), (bw, sy * SS)], fill=ink, width=7 * SS)
        draw.rectangle([0, 1140 * SS, bw, bh], fill=(178, 140, 104), outline=ink, width=7 * SS)
        draw.rounded_rectangle([100 * SS, 780 * SS, 980 * SS, 1225 * SS], radius=42 * SS, fill=(138, 158, 108), outline=ink, width=8 * SS)
        draw.rounded_rectangle([150 * SS, 1020 * SS, 930 * SS, 1165 * SS], radius=24 * SS, fill=(152, 172, 122), outline=ink, width=7 * SS)

    return img


def _draw_mouth(draw, hx, hy, scale, expr, mouth_open):
    ink = INK
    mw = int(24 * scale * SS)
    if mouth_open > 0.12:
        mh = int((9 + 26 * mouth_open) * scale * SS)
        draw.ellipse(
            [hx - mw, hy + int(22 * scale * SS), hx + mw, hy + int(22 * scale * SS) + mh],
            fill=(168, 52, 60), outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        if mouth_open > 0.42:
            draw.chord(
                [hx - mw + 4 * SS, hy + int(25 * scale * SS), hx + mw - 4 * SS, hy + int(22 * scale * SS) + mh],
                start=15, end=165, fill=(238, 118, 124))
    else:
        if expr in ("chill_smirk", "smug_eyes_closed", "excited_wide", "soft_love_smile"):
            draw.arc(
                [hx - int(23 * scale * SS), hy + int(16 * scale * SS), hx + int(25 * scale * SS), hy + int(43 * scale * SS)],
                start=10, end=170, fill=ink, width=max(4 * SS, int(6 * scale * SS)))
        elif expr in ("pout_frown", "exasperated"):
            draw.arc(
                [hx - int(19 * scale * SS), hy + int(30 * scale * SS), hx + int(19 * scale * SS), hy + int(50 * scale * SS)],
                start=190, end=350, fill=ink, width=max(4 * SS, int(6 * scale * SS)))
        elif expr == "shocked":
            draw.ellipse(
                [hx - int(12 * scale * SS), hy + int(24 * scale * SS), hx + int(12 * scale * SS), hy + int(46 * scale * SS)],
                fill=(168, 52, 60), outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        else:
            draw.line(
                [(hx - int(19 * scale * SS), hy + int(33 * scale * SS)), (hx + int(19 * scale * SS), hy + int(31 * scale * SS))],
                fill=ink, width=max(4 * SS, int(6 * scale * SS)))


def _draw_eyes(draw, hx, hy, scale, expr, skin_col, t, look_x=1.0):
    ink = INK
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
                start=10, end=170, fill=ink, width=max(4 * SS, int(6 * scale * SS)))
        return

    for side in (-1, 1):
        ex = hx + side * eye_dx
        draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(254, 254, 255), outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        draw.ellipse([ex - 5 * SS + px_off, eye_y - 5 * SS, ex + 5 * SS + px_off, eye_y + 5 * SS], fill=ink)
        if expr in ("deadpan", "skeptical", "pout_frown"):
            draw.pieslice([ex - er, eye_y - er, ex + er, eye_y + er], start=180, end=360, fill=skin_col, outline=ink,
                          width=max(4 * SS, int(5 * scale * SS)))
        brow_tilt = 0
        if expr in ("skeptical", "exasperated", "pout_frown"):
            brow_tilt = -7 * side * SS
        elif expr in ("excited_wide", "soft_love_smile"):
            brow_tilt = 5 * side * SS
        draw.line([(ex - er, eye_y - er - 9 * SS - brow_tilt), (ex + er, eye_y - er - 9 * SS + brow_tilt)],
                  fill=ink, width=max(4 * SS, int(6 * scale * SS)))


def _draw_full_cartoon_person(draw, cx, base_y, scale, char_cfg, is_male, expr, is_speaking, mouth_open, t, turn_frame, look_x=1.0):
    ink = INK
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

    pants_col = char_cfg.get("pants_color" if is_male else "skirt_color", (46, 52, 64))
    for side in (-1, 1):
        lx = hx + int(side * 24 * scale * SS)
        draw.rounded_rectangle(
            [lx - int(15 * scale * SS), hip_y - 8 * SS, lx + int(15 * scale * SS), hip_y + leg_h],
            radius=int(12 * scale * SS), fill=pants_col, outline=ink, width=6 * SS)
        draw.rounded_rectangle(
            [lx - int(18 * scale * SS), hip_y + leg_h - 14 * SS, lx + int(24 * scale * SS), hip_y + leg_h + 10 * SS],
            radius=int(10 * scale * SS), fill=(242, 242, 246), outline=ink, width=5 * SS)

    top_col = char_cfg["top_color"]
    if is_male:
        draw.rounded_rectangle(
            [hx - int(58 * scale * SS), neck_y, hx + int(58 * scale * SS), hip_y + 10 * SS],
            radius=int(26 * scale * SS), fill=top_col, outline=ink, width=7 * SS)
        collar_col = char_cfg.get("collar_color", (220, 224, 230))
        draw.pieslice(
            [hx - int(26 * scale * SS), neck_y - 12 * SS, hx + int(26 * scale * SS), neck_y + int(24 * scale * SS)],
            start=0, end=180, fill=collar_col, outline=ink, width=5 * SS)
    else:
        dress_poly = [
            (hx - int(44 * scale * SS), neck_y), (hx + int(44 * scale * SS), neck_y),
            (hx + int(68 * scale * SS), hip_y + 22 * SS), (hx - int(68 * scale * SS), hip_y + 22 * SS),
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
            draw.rounded_rectangle([hx - rx - int(10 * scale * SS), h_hy - ry + int(8 * scale * SS), hx + rx + int(10 * scale * SS), h_hy + ry + int(32 * scale * SS)], radius=int(28 * scale * SS), fill=hair, outline=ink, width=6 * SS)

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
    """Feet land at about y=1135 so the captions (y=1128+) sit just below them, inside the Reels safe zone."""
    n = len(selected_couples)
    if n == 1:
        return [
            {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 350, "base_y": 950, "scale": 1.02, "look_x": 1.0, "z": 1},
            {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 700, "base_y": 950, "scale": 1.00, "look_x": -1.0, "z": 1},
        ]
    if n == 2:
        return [
            {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 195, "base_y": 975, "scale": 0.86, "look_x": 1.0, "z": 1},
            {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 395, "base_y": 975, "scale": 0.85, "look_x": 0.6, "z": 1},
            {"couple_idx": 1, "is_male": True, "cfg": selected_couples[1]["him"], "x": 665, "base_y": 975, "scale": 0.86, "look_x": -0.6, "z": 1},
            {"couple_idx": 1, "is_male": False, "cfg": selected_couples[1]["her"], "x": 855, "base_y": 975, "scale": 0.85, "look_x": -1.0, "z": 1},
        ]
    return [
        {"couple_idx": 2, "is_male": True, "cfg": selected_couples[2]["him"], "x": 445, "base_y": 905, "scale": 0.72, "look_x": 0.4, "z": 0},
        {"couple_idx": 2, "is_male": False, "cfg": selected_couples[2]["her"], "x": 615, "base_y": 905, "scale": 0.71, "look_x": -0.4, "z": 0},
        {"couple_idx": 0, "is_male": True, "cfg": selected_couples[0]["him"], "x": 165, "base_y": 985, "scale": 0.82, "look_x": 1.0, "z": 1},
        {"couple_idx": 0, "is_male": False, "cfg": selected_couples[0]["her"], "x": 340, "base_y": 985, "scale": 0.81, "look_x": 0.6, "z": 1},
        {"couple_idx": 1, "is_male": True, "cfg": selected_couples[1]["him"], "x": 715, "base_y": 985, "scale": 0.82, "look_x": -0.6, "z": 1},
        {"couple_idx": 1, "is_male": False, "cfg": selected_couples[1]["her"], "x": 880, "base_y": 985, "scale": 0.81, "look_x": -1.0, "z": 1},
    ]


def apply_2x_sitcom_camera(stage_hi, num_couples, camera_mode, active_couple_idx, speaker_head_xy, turn_frame):
    eased = remotion_spring(turn_frame, FPS, damping=200.0, stiffness=140.0, mass=1.0)
    sw, sh = W * SS, H * SS

    if camera_mode == "focus_speaker" and speaker_head_xy:
        zoom = 1.68 + 0.14 * eased
        cx = int(speaker_head_xy[0] * SS)
        cy = int((speaker_head_xy[1] + 130) * SS)
    elif camera_mode.startswith("focus_couple_"):
        try:
            c_idx = int(camera_mode.split("_")[-1])
        except ValueError:
            c_idx = active_couple_idx
        if num_couples == 1:
            zoom, cx, cy = 1.12 + 0.08 * eased, sw // 2, int(sh * 0.46)
        elif num_couples == 2:
            zoom = 1.54 + 0.08 * eased
            cx = int(sw * (0.28 if c_idx == 0 else 0.72))
            cy = int(sh * 0.46)
        else:
            zoom = 1.62 + 0.08 * eased
            if c_idx == 0:
                cx, cy = int(sw * 0.24), int(sh * 0.47)
            elif c_idx == 1:
                cx, cy = int(sw * 0.76), int(sh * 0.47)
            else:
                cx, cy = int(sw * 0.50), int(sh * 0.43)
    else:
        zoom = 1.02 + 0.03 * eased
        cx, cy = sw // 2, sh // 2

    cw, ch = int(sw / zoom), int(sh / zoom)
    x0 = max(0, min(sw - cw, cx - cw // 2))
    y0 = max(0, min(sh - ch, cy - ch // 2))
    return stage_hi.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# SAFE-ZONE OVERLAYS: TOP HOOK TITLE + WORD-SYNCED CAPTIONS ABOVE THE INSTAGRAM UI
# ==============================================================================
@functools.lru_cache(maxsize=64)
def _load_font(size):
    cands = []
    fd = pathlib.Path("fonts")
    if fd.is_dir():
        files = sorted(list(fd.glob("*.ttf")) + list(fd.glob("*.otf")))
        cands += [str(p) for p in files if any(k in p.name.lower() for k in ("bold", "black", "heavy"))]
        cands += [str(p) for p in files]
    cands += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_safe_zone_overlays(frame, script, active_turn, t, page_cfg):
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # --- hook title: top of the screen, just below the Instagram top bar --------------------------
    if t <= 3.9:
        alpha = 255 if t <= 3.3 else int(255 * max(0.0, (3.9 - t) / 0.6))
        hook_font = _load_font(46)
        hook_lines = textwrap.wrap(script["hook_title"].upper(), width=22)[:2]
        box_h = 70 + (len(hook_lines) - 1) * 54
        odraw.rounded_rectangle(
            [110, HOOK_Y, W - 110, HOOK_Y + box_h], radius=22,
            fill=(16, 18, 24, int(alpha * 0.82)), outline=(255, 225, 45, alpha), width=4)
        for idx_h, h_line in enumerate(hook_lines):
            odraw.text((W // 2, HOOK_Y + 36 + idx_h * 54), h_line, font=hook_font,
                       fill=(255, 255, 255, alpha), anchor="mm")

    if not active_turn:
        return Image.alpha_composite(rgba, overlay).convert("RGB")

    word_times = active_turn["word_times"]
    if not word_times:
        return Image.alpha_composite(rgba, overlay).convert("RGB")
    first_start, last_end = word_times[0][0], word_times[-1][1]
    if t < first_start - 0.06 or t > last_end + 0.22:
        return Image.alpha_composite(rgba, overlay).convert("RGB")

    # --- speaker pill ----------------------------------------------------------------------------
    sp_font = _load_font(26)
    name = active_turn["speaker"].upper()
    nb = odraw.textbbox((0, 0), name, font=sp_font)
    pill_w = (nb[2] - nb[0]) + 44
    odraw.rounded_rectangle([CAPTION_CENTER_X - pill_w // 2, PILL_Y, CAPTION_CENTER_X + pill_w // 2, PILL_Y + 42],
                            radius=16, fill=(18, 20, 26, 215))
    odraw.text((CAPTION_CENTER_X, PILL_Y + 21), name, font=sp_font, fill=(255, 225, 45, 255), anchor="mm")

    # --- current word and phrase (chosen from the measured word times) -------------------------
    words = active_turn["words"]
    cur_idx = 0
    for i, (s, _e) in enumerate(word_times):
        if s <= t:
            cur_idx = i
    chunk = next((c for c in active_turn["chunks"] if c[0] <= cur_idx <= c[1]), (cur_idx, cur_idx))
    chunk_words = [w.upper() for w in words[chunk[0]:chunk[1] + 1]]
    local_active = cur_idx - chunk[0]

    acc = tuple(page_cfg.get("accent_color", (255, 225, 45)))
    size = 54
    while True:
        font = _load_font(size)
        space_w = odraw.textbbox((0, 0), " ", font=font)[2] + 4
        boxes = [odraw.textbbox((0, 0), w, font=font) for w in chunk_words]
        total_w = sum((b[2] - b[0]) for b in boxes) + space_w * max(0, len(chunk_words) - 1)
        if total_w <= CAPTION_MAX_W or size <= 34:
            break
        size -= 4

    cur_x = CAPTION_CENTER_X - total_w // 2
    for i, w in enumerate(chunk_words):
        fill_col = (acc[0], acc[1], acc[2], 255) if i == local_active else (255, 255, 255, 255)
        odraw.text((cur_x, CAPTION_Y), w, font=font, fill=fill_col, anchor="la", stroke_width=8, stroke_fill=(14, 16, 20, 252))
        cur_x += (boxes[i][2] - boxes[i][0]) + space_w

    return Image.alpha_composite(rgba, overlay).convert("RGB")


# ==============================================================================
# FULL REEL RENDERER (RAW FRAMES PIPED STRAIGHT INTO FFMPEG)
# ==============================================================================
def render_sitcom_reel(page_cfg, selected_couples, script, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        timeline, total_dur, final_wav, info = build_audio_and_timeline(script, selected_couples, tmp_dir)

        bg_cache = {}
        for loc in {t["location"] for t in timeline} | {script["setting"]}:
            bg_cache[loc] = render_location_background(loc)

        layout_sorted = sorted(compute_ensemble_layout(selected_couples), key=lambda item: item["z"])
        pathlib.Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", str(final_wav),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(out_mp4),
        ]
        log_path = tmp_dir / "ffmpeg.log"
        total_frames = int(round(total_dur * FPS))
        with open(log_path, "wb") as log_f:
            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log_f)
            try:
                for f_idx in range(total_frames):
                    t = f_idx / FPS
                    active_turn = None
                    for turn in timeline:
                        if turn["start"] <= t < turn["end"]:
                            active_turn = turn
                            break

                    if active_turn:
                        turn_frame = max(0, int((t - active_turn["start"]) * FPS))
                        mouth_open = active_turn["mouth_env"][min(len(active_turn["mouth_env"]) - 1, turn_frame)]
                        speaker_name = active_turn["speaker"]
                        speaker_emo = active_turn["emotion"]
                        loc = active_turn["location"]
                        cam = active_turn["camera"]
                        act_c_idx = active_turn["couple_idx"]
                    else:
                        turn_frame, mouth_open = 0, 0.0
                        speaker_name, speaker_emo = "", "chill_smirk"
                        loc, cam, act_c_idx = script["setting"], "group_wide", 0

                    stage_hi = bg_cache[loc].copy()
                    draw = ImageDraw.Draw(stage_hi)
                    speaker_head_xy = None
                    for actor in layout_sorted:
                        is_sp = (actor["cfg"]["name"] == speaker_name)
                        emo = speaker_emo if is_sp else (
                            "soft_love_smile" if "Romantic" in script["mood"] or "Cozy" in script["mood"] else "chill_smirk")
                        head_xy = _draw_full_cartoon_person(
                            draw=draw, cx=actor["x"], base_y=actor["base_y"], scale=actor["scale"], char_cfg=actor["cfg"],
                            is_male=actor["is_male"], expr=emo, is_speaking=is_sp, mouth_open=mouth_open if is_sp else 0.0,
                            t=t, turn_frame=turn_frame, look_x=actor["look_x"])
                        if is_sp:
                            speaker_head_xy = head_xy

                    frame = apply_2x_sitcom_camera(stage_hi, len(selected_couples), cam, act_c_idx, speaker_head_xy, turn_frame)
                    frame = ImageEnhance.Contrast(frame).enhance(1.03)
                    frame = draw_safe_zone_overlays(frame, script, active_turn, t, page_cfg)
                    proc.stdin.write(frame.tobytes())
            except BrokenPipeError:
                pass
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
            rc = proc.wait()
        if rc != 0:
            tail = log_path.read_bytes()[-800:].decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg encode failed: {tail}")

        print(f"Rendered {total_dur:.1f}s Reel ({', '.join(script['couples'])} | {script['mood']}, "
              f"{info['lines']} lines, {info['words']} words) -> {out_mp4}")
        return info
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


# ==============================================================================
# GIT / GITHUB PAGES ARCHIVE + INSTAGRAM REELS PUBLISHING
# ==============================================================================
def git_commit_push(message, add_args):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add"] + list(add_args), check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "commit", "-m", message], check=True)
    for attempt in range(1, 4):
        pulled = subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"])
        if pulled.returncode == 0 and subprocess.run(["git", "push", "origin", "HEAD:main"]).returncode == 0:
            return
        time.sleep(3 * attempt)
    raise RuntimeError("git push failed after 3 attempts")


def archive_and_get_pages_url(rel_path):
    nojekyll = pathlib.Path(".nojekyll")
    if not nojekyll.exists():
        nojekyll.write_text("", encoding="utf-8")
    git_commit_push(f"Publish Reel {rel_path}", ["posts/", ".nojekyll"])

    owner, repo = REPO_NAME.split("/", 1)
    base_pages_url = build_https_url(f"{owner.lower()}.github.io", f"/{repo}/{rel_path}")
    for attempt in range(1, 37):
        time.sleep(5)
        probe_url = f"{base_pages_url}?cb={attempt}_{int(time.time())}"
        try:
            req = urllib.request.Request(
                probe_url, headers={"User-Agent": "facebookexternalhit/1.1", "Range": "bytes=0-1023"}, method="GET")
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
        "(Verify GitHub repo Settings -> Pages -> Source is 'Deploy from a branch: main / (root)').")


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API {e.code} on {url}: {e.read().decode('utf-8', errors='replace')}") from e


def _finish_container_and_publish(host, ig_id, token, creation_id):
    print(f"Created IG media container: {creation_id}")
    for attempt in range(1, 41):
        time.sleep(5)
        status_url = build_https_url(host, f"/{GRAPH_VERSION}/{creation_id}",
                                     {"fields": "status_code,status", "access_token": token})
        try:
            status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        except Exception as e:
            print(f"IG status check hiccup ({e}); retrying...")
            continue
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
        permalink = json.loads(urllib.request.urlopen(link_url, timeout=15).read().decode()).get("permalink", "")
    except Exception:
        pass
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {media_id} {permalink}")
    return {"media_id": media_id, "permalink": permalink}


def publish_to_instagram(ig_id, token, video_url, caption):
    host = get_graph_host(token)
    container = post_request(
        build_https_url(host, f"/{GRAPH_VERSION}/{ig_id}/media"),
        {"media_type": "REELS", "video_url": video_url, "caption": caption, "share_to_feed": "true", "access_token": token})
    return _finish_container_and_publish(host, ig_id, token, container["id"])


def publish_to_instagram_resumable(ig_id, token, mp4_path, caption):
    """Uploads the MP4 straight to Meta (no GitHub Pages, nothing committed). Needs Facebook Login for Business."""
    host = get_graph_host(token)
    container = post_request(
        build_https_url(host, f"/{GRAPH_VERSION}/{ig_id}/media"),
        {"media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true", "access_token": token})
    creation_id = container["id"]
    upload_uri = container.get("uri") or build_https_url("rupload.facebook.com", f"/ig-api-upload/{GRAPH_VERSION}/{creation_id}")
    data = pathlib.Path(mp4_path).read_bytes()
    req = urllib.request.Request(
        upload_uri, data=data, method="POST",
        headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(data))})
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Resumable upload failed {e.code}: {e.read().decode('utf-8', errors='replace')}") from e
    return _finish_container_and_publish(host, ig_id, token, creation_id)


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    verify_runtime_environment()
    now = get_now()
    season_text = season_context(now)

    publish_enabled = env_flag("PUBLISH_TO_IG", False)
    upload_mode = os.environ.get("IG_UPLOAD_MODE", "url").strip().lower()
    keep_videos = env_flag("KEEP_VIDEOS", True)
    allow_fallback = env_flag("ALLOW_FALLBACK", False)
    commit_history = env_flag("COMMIT_HISTORY", publish_enabled)
    print(f"PUBLISH_TO_IG={publish_enabled} | IG_UPLOAD_MODE={upload_mode} | KEEP_VIDEOS={keep_videos} | "
          f"MAX_REEL_SEC={MAX_REEL_SEC:.0f}")

    for fest_name in ("Diwali", "Holi"):
        if (fest_name, now.year) not in _FESTIVAL_DATE_TABLE:
            print(f"NOTE: no {fest_name} date for {now.year}. Add it to festivals_extra.json to enable {fest_name} stories.")

    failures = []
    for page in load_active_pages():
        slug = page["slug"]
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
        ig_id = (page.get("ig_user_id") or os.environ.get("IG_USER_ID") or DEFAULT_IG_USER_ID).strip()

        try:
            if publish_enabled:
                verify_instagram_credentials(ig_id, token)

            history_items = load_story_history(slug, limit=150)
            selected_couples, mood, festival_obj, suggested_topic = plan_cast_and_premise(history_items, now)
            script = generate_story_with_gemini(
                page, selected_couples, mood, festival_obj, suggested_topic, history_items, season_text)
            script["topic"] = suggested_topic
            is_fallback = script.get("source") != "gemini"

            if is_fallback and not allow_fallback:
                raise RuntimeError("Gemini did not produce a valid story; skipping so the fallback is never posted "
                                   "(set ALLOW_FALLBACK=true to render it locally).")

            stamp = now.strftime("%Y-%m-%d_%H%M")
            out_dir = pathlib.Path("posts") / slug
            out_dir.mkdir(parents=True, exist_ok=True)
            video_dir = out_dir if upload_mode != "resumable" else pathlib.Path("out") / slug
            video_dir.mkdir(parents=True, exist_ok=True)
            rel_mp4 = (video_dir / f"reel_{stamp}.mp4").as_posix()

            hist_entry = script.get("history_entry", {})
            save_story_record(slug, {
                "timestamp": stamp,
                "lead_couple": selected_couples[0]["label"],
                "couples": script["couples"],
                "mood": script["mood"],
                "festival": script.get("festival"),
                "topic": suggested_topic,
                "hook": hist_entry.get("hook", script["hook_title"]),
                "environment": hist_entry.get("environment", script["setting"]),
                "core_joke": hist_entry.get("core_joke", script["hook_title"]),
                "hashtags": script["hashtags"],
                "posted": False,
                "media_id": None,
            })

            info = render_sitcom_reel(page, selected_couples, script, rel_mp4)
            script["render_info"] = info
            out_dir.joinpath(f"story_{stamp}.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
            update_story_record(slug, stamp, {"duration_sec": info["duration"], "words": info["words"]})
            write_history_table(slug)

            if publish_enabled and not is_fallback:
                caption = f"{script['caption']}\n\n{' '.join(script['hashtags'])}"[:2200]
                if upload_mode == "resumable":
                    result = publish_to_instagram_resumable(ig_id, token, rel_mp4, caption)
                else:
                    public_url = archive_and_get_pages_url(rel_mp4)
                    result = publish_to_instagram(ig_id, token, public_url, caption)

                update_story_record(slug, stamp, {"posted": True, "media_id": result["media_id"],
                                                  "permalink": result.get("permalink", "")})
                write_history_table(slug)

                if upload_mode != "resumable" and not keep_videos:
                    try:
                        pathlib.Path(rel_mp4).unlink(missing_ok=True)
                    except Exception as e:
                        print(f"Could not delete {rel_mp4}: {e}")
                try:
                    git_commit_push(f"History update {stamp}", ["-A", "posts/"])
                except Exception as e:
                    print(f"History commit skipped: {e}")
            elif commit_history:
                try:
                    git_commit_push(f"History update {stamp}", ["-A", "posts/"])
                except Exception as e:
                    print(f"History commit skipped: {e}")
            elif publish_enabled and is_fallback:
                print("Fallback story rendered but NOT published.")
        except Exception as e:
            print(f"ERROR on page {slug}: {e}")
            failures.append(slug)

    if failures:
        sys.exit(1)
