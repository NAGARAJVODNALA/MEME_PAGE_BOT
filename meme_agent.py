#!/usr/bin/env python3
"""
Autonomous Multi-Account Viral Reels Engine (@wearechillclub v5_solo_pov)
- Reads account config from `accounts.json` (or `ACCOUNTS_JSON` env / built-in default)
- Autonomous Live Trend & Cultural Research (Google Trends RSS + Hacker News Pulse + History)
- Two-Step Gemini 3.x Showrunner (Research Analyst -> 5-Mode Retention Scriptwriter)
- Multi-Model Image Generation + Custom Vector-Neat 2D Solo Stickman Illustrator
  (White-headed stickman, muted-olive baseball cap, dark charcoal hoodie, crisp black ink outlines)
- Instagram Safe-Zone Compositor (`v5_solo_pov` layout with brand accent/panic colors)
- GitHub Pages Hosting + Meta Graph API v21.0 Auto-Publisher
"""

import os
import sys
import json
import math
import time
import wave
import struct
import random
import shutil
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# ==============================================================================
# 1. ACCOUNT CONFIGURATION & PATHS
# ==============================================================================
DEFAULT_ACCOUNTS = [
    {
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "layout_mode": "v5_solo_pov",
        "ig_user_id": "17841476835986162",
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": (
            "Strictly SOLO millennial/Gen-Z internal chaos, day-off rain euphoria, "
            "sibling random calls, $14.82 bank checks, remote-work tab closing, "
            "and 2:47 AM overthinking (100% solo character, ZERO couples or romantic partners)"
        ),
        "art_style": (
            "Clean vector-neat 2D webcomic illustration starring ONE solo white-headed "
            "stickman character wearing a muted-olive baseball cap and dark charcoal hoodie, "
            "crisp uniform black ink outlines, cozy warm marker shading, atmospheric solo "
            "interior background, leave clean top space for a POV banner, strictly NO text "
            "or speech bubbles inside the drawing"
        ),
    }
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GITHUB_PAGES_BASE_URL = os.environ.get("GITHUB_PAGES_BASE_URL", "").strip().rstrip("/")
USE_TRIAL_REELS = os.environ.get("TRIAL_REELS", "false").strip().lower() == "true"

WIDTH = 1080
HEIGHT = 1920
FPS = 24
DURATION_SEC = 10
TOTAL_FRAMES = FPS * DURATION_SEC  # 240 frames (4 beats x 2.5s)
SAMPLE_RATE = 44100

ROOT_DIR = Path(__file__).resolve().parent
ACCOUNTS_FILE = ROOT_DIR / "accounts.json"
DOCS_DIR = ROOT_DIR / "docs"
MEDIA_DIR = DOCS_DIR / "reels"
WORK_DIR = ROOT_DIR / "build_tmp"
HISTORY_FILE = ROOT_DIR / "history.json"
MANIFEST_FILE = DOCS_DIR / "latest_reel.json"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)

HOOK_ARCHETYPES = [
    "EQUATION_HOOK",
    "LEFT_VS_RIGHT",
    "DEFINITION_FRAME",
    "ANTICIPATION_COLD_OPEN",
    "MIRROR_QUESTION",
]


def load_accounts() -> List[Dict[str, Any]]:
    env_accounts = os.environ.get("ACCOUNTS_JSON", "").strip()
    if env_accounts:
        try:
            data = json.loads(env_accounts)
            if isinstance(data, list) and data:
                return data
        except Exception as exc:
            print(f"[Config] ACCOUNTS_JSON parse warning: {exc}")

    if ACCOUNTS_FILE.exists():
        try:
            data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception as exc:
            print(f"[Config] accounts.json parse warning: {exc}")

    return DEFAULT_ACCOUNTS


# ==============================================================================
# 2. FONT & SAFE-ZONE UTILITIES
# ==============================================================================
def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for w in words[1:]:
        test = f"{current} {w}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def load_history() -> Dict[str, Any]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"episode_count": 0, "reels": []}


def save_history(history: Dict[str, Any]) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


# ==============================================================================
# 3. LIVE CULTURAL & TREND RESEARCH ENGINE
# ==============================================================================
def fetch_url_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ChillClubTrendBot/4.0)",
            "Accept": "application/json, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def gather_google_trends() -> List[str]:
    url = "https://trends.google.com/trending/rss?geo=US"
    topics = []
    try:
        xml_data = fetch_url_text(url)
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item")[:10]:
            title_el = item.find("title")
            traffic_el = item.find("{https://trends.google.com/trending/rss}approx_traffic")
            if title_el is not None and title_el.text:
                traffic = f" ({traffic_el.text})" if (traffic_el is not None and traffic_el.text) else ""
                topics.append(f"{title_el.text.strip()}{traffic}")
    except Exception as exc:
        print(f"[Research] Google Trends RSS skipped ({exc})")
    return topics


def gather_culture_pulse() -> List[str]:
    stories = []
    try:
        ids = json.loads(fetch_url_text("https://hacker-news.firebaseio.com/v0/topstories.json"))[:8]
        for item_id in ids:
            item = json.loads(fetch_url_text(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"))
            title = (item or {}).get("title", "").strip()
            if title:
                stories.append(title[:140])
    except Exception as exc:
        print(f"[Research] Culture pulse skipped ({exc})")
    return stories


# ==============================================================================
# 4. GEMINI 3.X MODEL DISCOVERY & FALLBACK LLM CALLER
# ==============================================================================
def discover_models(client: Any) -> Tuple[List[str], List[str], List[str]]:
    text_candidates = []
    gemini_img_candidates = []
    imagen_candidates = []

    try:
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            lower = name.lower()
            if "2.0" in lower or lower == "gemini-2.5-flash":
                continue
            if "imagen" in lower:
                imagen_candidates.append(name)
            elif "image" in lower:
                gemini_img_candidates.append(name)
            elif "flash" in lower and "tts" not in lower and "audio" not in lower and "lite" not in lower:
                text_candidates.append(name)
    except Exception as exc:
        print(f"[Models] List warning: {exc}")

    priority_text = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3-flash-preview",
    ]
    ordered_text = [m for m in priority_text if m in text_candidates] + [
        m for m in text_candidates if m not in priority_text
    ]
    if not ordered_text:
        ordered_text = priority_text

    priority_img = [
        "gemini-3.1-flash-image",
        "gemini-3-pro-image",
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-lite-image",
    ]
    ordered_img = [m for m in priority_img if m in gemini_img_candidates] + [
        m for m in gemini_img_candidates if m not in priority_img
    ]

    print(f"[Models] TextQueue={ordered_text} | GeminiImage={ordered_img}")
    return ordered_text, ordered_img, imagen_candidates


def generate_json_with_fallback(
    client: Any,
    text_models: List[str],
    prompt: str,
    temperature: float = 0.85,
) -> Dict[str, Any]:
    last_err = None
    for model_name in text_models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            print(f"[LLM] Success with {model_name}")
            return json.loads(resp.text)
        except Exception as exc:
            print(f"[LLM] {model_name} skipped: {exc}")
            last_err = exc
    raise RuntimeError(f"All text models failed. Last error: {last_err}")


def run_autonomous_research(
    client: Any,
    text_models: List[str],
    account: Dict[str, Any],
    history: Dict[str, Any],
) -> Dict[str, Any]:
    print(f"[Research] Gathering live trends for {account['handle']}...")
    google_trends = gather_google_trends()
    culture_stories = gather_culture_pulse()

    past_hooks = [
        f"{r.get('hook_line_1', '')} {r.get('hook_line_2_gold', '')}".strip()
        for r in history.get("reels", [])[-15:]
    ]
    last_archetype = history.get("reels", [{}])[-1].get("archetype", "") if history.get("reels") else ""
    candidate_archetypes = [a for a in HOOK_ARCHETYPES if a != last_archetype]
    chosen_archetype = random.choice(candidate_archetypes)

    research_prompt = f"""
You are the viral creative strategist for {account['handle']}.
STRICT BRAND DOMAIN:
{account['domain']}

LIVE GOOGLE TRENDS TODAY:
{json.dumps(google_trends, indent=2)}

LIVE CULTURE & TECH PULSE TODAY:
{json.dumps(culture_stories, indent=2)}

RECENTLY USED HOOKS (DO NOT REPEAT):
{json.dumps(past_hooks, indent=2)}

ASSIGNED VIRAL RETENTION ARCHETYPE: {chosen_archetype}
- EQUATION_HOOK: Top hook presents an incomplete equation ("FRIDAY + RAINY WINDOW:" or "PAYDAY + 2 HOURS:") and Beat 4 reveals the 2-word truth ("PURE PEACE." or "$14.82 LEFT.").
- LEFT_VS_RIGHT: Side-by-side mental contrast of the SAME solo character ("COWORKERS THINK" vs "ME ON MUTE" or "9 AM ME" vs "2:47 AM ME").
- DEFINITION_FRAME: Framed as a universal law ("POV: THE DEFINITION OF" + "'$14.82 CONFIDENCE':") illustrated by an escalating 4-beat solo skit.
- ANTICIPATION_COLD_OPEN: Beat 1 starts AT THE CLIMAX ("HOW I ENDED UP HERE AT 2:47 AM:"), Beat 2 rewinds, Beat 3-4 show the absurd chain reaction.
- MIRROR_QUESTION: Opens with an ego-trap question ("WHY DO WE ALL DO THIS?" or "WHICH STAGE ARE YOU?") that forces viewers to watch all 4 beats.

HARD RULES:
1. 100% SOLO character only. ZERO couples, dating, or romantic partners.
2. Focus on solo millennial/Gen-Z internal chaos, day-off rain euphoria, sibling random calls, $14.82 bank checks, remote-work tab closing, or 2:47 AM overthinking.
3. Engineer a psychological curiosity gap in the first 1.5 seconds + a subtle comment-bait detail.

Return STRICT JSON only:
{{
  "chosen_archetype": "{chosen_archetype}",
  "trend_inspiration": "short note on what live trend or cultural mood inspired this",
  "core_relatable_truth": "one-sentence psychological insight",
  "curiosity_gap": "why the viewer cannot swipe away before second 10",
  "comment_bait_detail": "specific number, tab, or detail people will mention in comments"
}}
"""
    try:
        brief = generate_json_with_fallback(client, text_models, research_prompt, temperature=0.9)
        brief["chosen_archetype"] = chosen_archetype
        print(f"[Research] Archetype={chosen_archetype} | Premise={brief.get('core_relatable_truth', '')[:85]}")
        return brief
    except Exception as exc:
        print(f"[Research] Analyst fallback ({exc})")
        return {
            "chosen_archetype": chosen_archetype,
            "trend_inspiration": "Solo remote-work & late-night internal chaos",
            "core_relatable_truth": "Closing 27 browser tabs at 5:01 PM feels like winning an Olympic gold medal.",
            "curiosity_gap": "Starts at the 4:59 PM fake-busy typing sprint and reveals the 5:01 PM instant couch collapse.",
            "comment_bait_detail": "The Slack status stays green while the laptop is already closed.",
        }


def generate_viral_script(
    client: Any,
    text_models: List[str],
    account: Dict[str, Any],
    research_brief: Dict[str, Any],
    episode_num: int,
) -> Dict[str, Any]:
    archetype = research_brief.get("chosen_archetype", "DEFINITION_FRAME")
    art_style = account["art_style"]

    prompt = f"""
You are the showrunner of {account['handle']} (layout: {account['layout_mode']}).
This is Episode #{episode_num}.

BRAND DOMAIN:
{account['domain']}

MANDATORY ART STYLE FOR EVERY BEAT:
{art_style}

RESEARCH BRIEF:
{json.dumps(research_brief, indent=2)}

WRITE A 4-BEAT (10-SECOND) SOLO POV COMEDY REEL SCRIPT.
Rules for maximum retention (>130% watch time):
1. Top POV Hook Banner:
   - hook_line_1: 2-5 words in ALL CAPS (white text), e.g., "POV: CLOSING 27 TABS" or "BANK ACCOUNT + 2 AM:"
   - hook_line_2_gold: 2-4 words in ALL CAPS (accent gold highlight), e.g., "AT 5:01 PM SHARP:" or "'$14.82 CONFIDENCE':"
2. If archetype is LEFT_VS_RIGHT, provide left_label (e.g., "SLACK STATUS") and right_label (e.g., "REAL LIFE"). Otherwise leave empty strings.
3. Exactly 4 beats (Beat 1 = 0.0-2.5s, Beat 2 = 2.5-5.0s, Beat 3 = 5.0-7.5s, Beat 4 = 7.5-10.0s).
4. Each beat's spoken caption MUST be 4 to 7 punchy, lowercase/conversational words.
5. Each beat must specify:
   - `mood`: strictly one of ["chill", "panic", "manic", "defeated"]
   - `scene_prop`: strictly one of ["laptop_tabs", "rain_window", "bank_phone", "sibling_call", "bed_247am", "split_mind"]
   - `visual_prompt`: incorporates the exact art_style above starring ONE solo white-headed stickman in a muted-olive baseball cap and dark charcoal hoodie, NO text inside the drawing.
6. Beat 4 MUST end with a hilarious internal-monologue twist or seamless loop back into Beat 1.
7. Write a short, relatable Instagram caption + 5 targeted hashtags.

Return STRICT JSON only:
{{
  "archetype": "{archetype}",
  "hook_line_1": "POV: CHECKING YOUR BALANCE",
  "hook_line_2_gold": "AT 2:47 AM:",
  "left_label": "",
  "right_label": "",
  "instagram_caption": "why does $14.82 feel like either $0 or $10,000 depending on the day? 😭👇 #wearechillclub #relatable #webcomic #millennialhumor #genzhumor",
  "beats": [
    {{
      "beat_number": 1,
      "caption": "opening the banking app with one eye",
      "sfx": "whoosh",
      "mood": "chill",
      "scene_prop": "bank_phone",
      "visual_prompt": "{art_style}, sitting alone on a cozy couch in dim lamp light squinting nervously at a smartphone screen, no text"
    }},
    {{
      "beat_number": 2,
      "caption": "seeing $14.82 and three pending charges",
      "sfx": "pop",
      "mood": "panic",
      "scene_prop": "bank_phone",
      "visual_prompt": "{art_style}, wide-eyed panic expression while holding a glowing smartphone in a moody dark room, no text"
    }},
    {{
      "beat_number": 3,
      "caption": "suddenly calculating if iced coffee is essential",
      "sfx": "rise",
      "mood": "manic",
      "scene_prop": "bed_247am",
      "visual_prompt": "{art_style}, staring at the ceiling at 2:47 AM surrounded by cozy bedroom shadows and moonlight through blinds, no text"
    }},
    {{
      "beat_number": 4,
      "caption": "deciding future me will handle friday",
      "sfx": "bass_drop",
      "mood": "defeated",
      "scene_prop": "rain_window",
      "visual_prompt": "{art_style}, peacefully sipping a warm mug next to a rainy apartment window with cozy amber indoor lighting, no text"
    }}
  ]
}}
"""
    script_data = generate_json_with_fallback(client, text_models, prompt, temperature=0.85)
    if len(script_data.get("beats", [])) < 4:
        raise ValueError("Gemini returned fewer than 4 beats")
    script_data["beats"] = script_data["beats"][:4]
    return script_data


# ==============================================================================
# 5. MULTI-MODEL IMAGE GENERATOR + SOLO WEBCOMIC STICKMAN ILLUSTRATOR
# ==============================================================================
def draw_chillclub_stickman(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    scale: float,
    mood: str,
    rng: random.Random,
) -> None:
    """
    Draws @wearechillclub signature solo character:
    - White-headed stickman
    - Muted-olive baseball cap (#6B705C / #586349)
    - Dark charcoal hoodie (#2B2D33)
    - Crisp uniform black ink outlines (#141519)
    """
    s = scale
    ink = (18, 20, 24)
    olive_cap = (98, 108, 78)
    olive_brim = (76, 85, 60)
    charcoal_hoodie = (44, 47, 54)
    hoodie_shadow = (32, 34, 40)
    ink_w = max(3, int(6 * s))

    # Stickman legs (dark charcoal joggers)
    draw.line((cx - int(32 * s), cy + int(220 * s), cx - int(42 * s), cy + int(350 * s)), fill=ink, width=max(4, int(11 * s)))
    draw.line((cx + int(32 * s), cy + int(220 * s), cx + int(42 * s), cy + int(350 * s)), fill=ink, width=max(4, int(11 * s)))

    # Dark charcoal hoodie torso
    torso_box = (int(cx - 105 * s), int(cy + 55 * s), int(cx + 105 * s), int(cy + 245 * s))
    draw.rounded_rectangle(torso_box, radius=int(48 * s), fill=charcoal_hoodie, outline=ink, width=ink_w)
    # Hoodie front pocket & drawstrings
    draw.rounded_rectangle(
        (int(cx - 58 * s), int(cy + 150 * s), int(cx + 58 * s), int(cy + 225 * s)),
        radius=int(18 * s),
        fill=hoodie_shadow,
        outline=ink,
        width=max(2, int(4 * s)),
    )
    draw.line((cx - int(22 * s), int(cy + 65 * s), cx - int(26 * s), int(cy + 125 * s)), fill=(185, 190, 200), width=max(2, int(4 * s)))
    draw.line((cx + int(22 * s), int(cy + 65 * s), cx + int(26 * s), int(cy + 125 * s)), fill=(185, 190, 200), width=max(2, int(4 * s)))

    # Stickman arms (pose varies by mood)
    if mood == "panic":
        # Hands up near head in panic
        draw.line((cx - int(95 * s), int(cy + 95 * s), cx - int(145 * s), int(cy + 10 * s)), fill=ink, width=max(4, int(10 * s)))
        draw.line((cx + int(95 * s), int(cy + 95 * s), cx + int(145 * s), int(cy + 10 * s)), fill=ink, width=max(4, int(10 * s)))
    elif mood == "manic":
        # One hand scratching head, one holding phone
        draw.line((cx - int(95 * s), int(cy + 95 * s), cx - int(130 * s), int(cy - 25 * s)), fill=ink, width=max(4, int(10 * s)))
        draw.line((cx + int(95 * s), int(cy + 95 * s), cx + int(135 * s), int(cy + 145 * s)), fill=ink, width=max(4, int(10 * s)))
    else:
        # Relaxed hoodie-pocket / chill pose
        draw.line((cx - int(95 * s), int(cy + 95 * s), cx - int(65 * s), int(cy + 185 * s)), fill=ink, width=max(4, int(10 * s)))
        draw.line((cx + int(95 * s), int(cy + 95 * s), cx + int(65 * s), int(cy + 185 * s)), fill=ink, width=max(4, int(10 * s)))

    # Crisp white stickman head
    head_r = int(88 * s)
    head_cy = int(cy - 42 * s)
    draw.ellipse(
        (cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r),
        fill=(252, 252, 250),
        outline=ink,
        width=ink_w,
    )

    # Muted-olive baseball cap
    cap_box = (cx - int(92 * s), head_cy - int(102 * s), cx + int(92 * s), head_cy - int(14 * s))
    draw.pieslice(cap_box, start=180, end=360, fill=olive_cap, outline=ink, width=ink_w)
    # Cap visor/brim
    draw.rounded_rectangle(
        (cx - int(68 * s), head_cy - int(62 * s), cx + int(122 * s), head_cy - int(42 * s)),
        radius=int(10 * s),
        fill=olive_brim,
        outline=ink,
        width=max(2, int(5 * s)),
    )

    # Expressive ink eyes & eyebrows
    eye_y = head_cy - int(8 * s)
    for side in (-1, 1):
        ex = cx + side * int(30 * s)
        if mood == "panic":
            draw.ellipse((ex - int(14 * s), eye_y - int(14 * s), ex + int(14 * s), eye_y + int(14 * s)), fill=(255, 255, 255), outline=ink, width=max(2, int(4 * s)))
            draw.ellipse((ex - int(5 * s), eye_y - int(5 * s), ex + int(5 * s), eye_y + int(5 * s)), fill=ink)
        elif mood == "chill":
            draw.arc((ex - int(14 * s), eye_y - int(8 * s), ex + int(14 * s), eye_y + int(10 * s)), start=0, end=180, fill=ink, width=max(3, int(5 * s)))
        else:
            er = int(8 * s)
            draw.ellipse((ex - er, eye_y - er, ex + er, eye_y + er), fill=ink)

    # Expressive mouth
    mouth_y = head_cy + int(32 * s)
    if mood == "chill":
        draw.arc((cx - int(24 * s), mouth_y - int(12 * s), cx + int(24 * s), mouth_y + int(14 * s)), start=10, end=170, fill=ink, width=max(3, int(5 * s)))
    elif mood == "panic":
        draw.ellipse((cx - int(16 * s), mouth_y - int(12 * s), cx + int(16 * s), mouth_y + int(20 * s)), fill=(220, 60, 70), outline=ink, width=max(2, int(4 * s)))
    elif mood == "manic":
        draw.line((cx - int(26 * s), mouth_y + int(4 * s), cx + int(26 * s), mouth_y - int(4 * s)), fill=ink, width=max(3, int(5 * s)))
    else:
        draw.arc((cx - int(24 * s), mouth_y, cx + int(24 * s), mouth_y + int(22 * s)), start=190, end=350, fill=ink, width=max(3, int(5 * s)))


def render_webcomic_scene(
    beat: Dict[str, Any],
    account: Dict[str, Any],
    out_path: Path,
    seed: int,
) -> None:
    """Cozy warm marker-shaded 2D webcomic fallback tailored to @wearechillclub."""
    rng = random.Random(seed + beat.get("beat_number", 1) * 97)
    w, h = 1080, 1080
    mood = beat.get("mood", "chill").lower()
    prop = beat.get("scene_prop", "bank_phone").lower()

    accent_rgb = tuple(account.get("accent_color", [255, 225, 45]))
    panic_rgb = tuple(account.get("panic_color", [255, 75, 85]))

    # Cozy atmospheric interior wall palette
    wall_palettes = {
        "chill": ((38, 44, 58), (58, 68, 88)),
        "panic": ((52, 26, 36), (82, 36, 48)),
        "manic": ((28, 42, 52), (45, 68, 82)),
        "defeated": ((44, 38, 48), (66, 56, 72)),
    }
    wall_top, wall_bot = wall_palettes.get(mood, wall_palettes["chill"])

    img = Image.new("RGB", (w, h), wall_top)
    draw = ImageDraw.Draw(img)

    # Warm vertical marker gradient
    for y in range(0, 780, 8):
        ratio = y / 780.0
        c = tuple(int(wall_top[i] + (wall_bot[i] - wall_top[i]) * ratio) for i in range(3))
        draw.rectangle((0, y, w, y + 8), fill=c)

    # Cozy warm lamp glow orb in upper corner
    for r in range(260, 10, -14):
        alpha = 1.0 - (r / 260.0)
        glow_c = tuple(min(255, int(wall_top[i] + (accent_rgb[i] - wall_top[i]) * (alpha ** 2.4) * 0.42)) for i in range(3))
        draw.ellipse((180 - r, 210 - r, 180 + r, 210 + r), fill=glow_c)

    # Wooden apartment floor
    draw.rectangle((0, 780, w, h), fill=(48, 36, 32))
    draw.line((0, 780, w, 780), fill=(24, 20, 22), width=6)

    font_prop = load_font(32, bold=True)

    # Background interior storytelling props
    if prop == "rain_window":
        draw.rounded_rectangle((650, 160, 980, 520), radius=18, fill=(24, 34, 52), outline=(22, 24, 28), width=6)
        draw.line((815, 160, 815, 520), fill=(22, 24, 28), width=6)
        draw.line((650, 340, 980, 340), fill=(22, 24, 28), width=6)
        for _ in range(18):
            rx = rng.randint(670, 960)
            ry = rng.randint(180, 490)
            draw.line((rx, ry, rx - 10, ry + 24), fill=(125, 211, 252), width=3)
    elif prop == "bed_247am":
        draw.rounded_rectangle((660, 170, 960, 290), radius=18, fill=(20, 24, 32), outline=panic_rgb, width=5)
        draw.text((705, 205), "02:47 AM", font=load_font(44, bold=True), fill=panic_rgb)
    elif prop == "laptop_tabs":
        draw.rounded_rectangle((640, 210, 980, 440), radius=18, fill=(24, 28, 38), outline=accent_rgb, width=5)
        draw.text((675, 250), "27 OPEN TABS", font=font_prop, fill=accent_rgb)
        draw.text((675, 310), "Slack: Active", font=font_prop, fill=(74, 222, 128))
    elif prop == "sibling_call":
        draw.rounded_rectangle((660, 190, 970, 390), radius=24, fill=(24, 28, 38), outline=(74, 222, 128), width=5)
        draw.text((695, 235), "INCOMING CALL", font=font_prop, fill=(74, 222, 128))
        draw.text((695, 295), "Sibling (3x)", font=font_prop, fill=(255, 255, 255))

    if prop == "split_mind":
        draw.line((w // 2, 110, w // 2, 960), fill=(24, 26, 32), width=6)
        draw_chillclub_stickman(draw, 290, 500, 0.82, "chill", rng)
        draw_chillclub_stickman(draw, 790, 500, 0.82, "panic", rng)
    else:
        draw_chillclub_stickman(draw, 440, 500, 0.98, mood, rng)

    if prop == "bank_phone":
        draw.rounded_rectangle((660, 470, 950, 770), radius=28, fill=(22, 26, 36), outline=panic_rgb if mood == "panic" else accent_rgb, width=6)
        draw.text((700, 520), "CHECKING", font=font_prop, fill=(160, 170, 185))
        draw.text((700, 585), "$14.82", font=load_font(54, bold=True), fill=panic_rgb if mood == "panic" else accent_rgb)

    img = img.filter(ImageFilter.SMOOTH)
    img.save(out_path, "PNG")


def generate_beat_artwork(
    client: Any,
    gemini_img_models: List[str],
    imagen_models: List[str],
    beat: Dict[str, Any],
    account: Dict[str, Any],
    out_path: Path,
    seed: int,
    skip_api_images: bool = False,
) -> Tuple[str, bool]:
    prompt = beat.get("visual_prompt", account["art_style"])

    if not skip_api_images:
        for model_name in gemini_img_models:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )
                for cand in getattr(resp, "candidates", []) or []:
                    for part in getattr(cand.content, "parts", []) or []:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            out_path.write_bytes(inline.data)
                            return model_name, False
            except Exception as exc:
                err_str = str(exc)
                print(f"[Art] {model_name} skipped: {err_str[:130]}")
                if "limit: 0" in err_str:
                    skip_api_images = True
                    break

    if not skip_api_images:
        for model_name in imagen_models:
            try:
                resp = client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        output_mime_type="image/png",
                    ),
                )
                generated = getattr(resp, "generated_images", []) or []
                if generated and getattr(generated[0], "image", None):
                    generated[0].image.save(str(out_path))
                    return model_name, False
            except Exception as exc:
                print(f"[Art] {model_name} skipped: {str(exc)[:130]}")

    render_webcomic_scene(beat, account, out_path, seed)
    return "webcomic_solo_illustrator", skip_api_images


# ==============================================================================
# 6. PROCEDURAL FOLEY SFX & LO-FI AMBIENT AUDIO ENGINE
# ==============================================================================
def synthesize_reel_audio(beats: List[Dict[str, Any]], wav_path: Path, seed: int) -> None:
    rng = random.Random(seed)
    total_samples = SAMPLE_RATE * DURATION_SEC
    beat_samples = total_samples // 4

    chord_sets = [
        [220.0, 261.63, 329.63, 392.0],
        [174.61, 220.0, 261.63, 329.63],
        [196.0, 246.94, 293.66, 349.23],
        [164.81, 196.0, 246.94, 293.66],
    ]

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        frames_bytes = bytearray()
        for i in range(total_samples):
            t = i / SAMPLE_RATE
            beat_idx = min(3, i // beat_samples)
            local_t = (i % beat_samples) / SAMPLE_RATE
            sfx_type = beats[beat_idx].get("sfx", "pop")

            freqs = chord_sets[beat_idx]
            pad = 0.0
            for idx_f, f in enumerate(freqs):
                detune = 1.0 + (0.002 if idx_f % 2 == 0 else -0.002)
                pad += math.sin(2.0 * math.pi * f * detune * t) * 0.052
            lfo = 0.78 + 0.22 * math.sin(2.0 * math.pi * 1.5 * t)
            pad *= lfo

            sfx = 0.0
            if local_t < 0.28:
                env = math.exp(-local_t * 14.0)
                if sfx_type == "whoosh":
                    noise = rng.uniform(-1.0, 1.0)
                    sweep = math.sin(2.0 * math.pi * (180.0 + 900.0 * local_t) * local_t)
                    sfx = (noise * 0.20 + sweep * 0.18) * env
                elif sfx_type == "bass_drop":
                    freq = 130.0 * math.exp(-local_t * 6.5) + 42.0
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.40 * env
                elif sfx_type == "rise":
                    freq = 260.0 + 1100.0 * local_t
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.22 * env
                else:
                    freq = 520.0 + 420.0 * math.exp(-local_t * 25.0)
                    sfx = math.sin(2.0 * math.pi * freq * local_t) * 0.26 * env

            sample_val = max(-0.95, min(0.95, pad + sfx))
            pcm = int(sample_val * 32767)
            frames_bytes += struct.pack("<hh", pcm, pcm)

        wf.writeframes(bytes(frames_bytes))


# ==============================================================================
# 7. V5_SOLO_POV SAFE-ZONE COMPOSITOR (24 FPS x 10s = 240 FRAMES)
# ==============================================================================
def render_frames(
    script_data: Dict[str, Any],
    account: Dict[str, Any],
    art_paths: List[Path],
    episode_num: int,
    frames_dir: Path,
) -> Path:
    frames_dir.mkdir(parents=True, exist_ok=True)
    beats = script_data["beats"]
    hook_l1 = (script_data.get("hook_line_1") or "POV: CHECKING YOUR BALANCE").upper()
    hook_l2 = (script_data.get("hook_line_2_gold") or "AT 2:47 AM:").upper()
    left_label = (script_data.get("left_label") or "").upper()
    right_label = (script_data.get("right_label") or "").upper()

    accent_rgb = tuple(account.get("accent_color", [255, 225, 45]))
    panic_rgb = tuple(account.get("panic_color", [255, 75, 85]))
    handle_str = account.get("handle", "@wearechillclub")

    font_badge = load_font(32, bold=True)
    font_hook = load_font(54, bold=True)
    font_split = load_font(32, bold=True)
    font_sub = load_font(44, bold=True)
    font_wm = load_font(28, bold=True)

    loaded_arts = [Image.open(p).convert("RGB") for p in art_paths]
    frames_per_beat = TOTAL_FRAMES // 4
    cover_frame_path = frames_dir / "cover_frame.jpg"

    for f_idx in range(TOTAL_FRAMES):
        beat_idx = min(3, f_idx // frames_per_beat)
        local_f = f_idx % frames_per_beat
        progress = local_f / float(frames_per_beat)
        beat = beats[beat_idx]
        is_panic = beat.get("mood") == "panic"

        canvas = Image.new("RGB", (WIDTH, HEIGHT), (12, 13, 18))
        draw = ImageDraw.Draw(canvas)

        zoom = 1.0 + 0.07 * progress + (0.035 * max(0.0, 1.0 - local_f / 6.0))
        base_art = loaded_arts[beat_idx]
        stage_size = 940
        scaled = int(stage_size * zoom)
        art_resized = base_art.resize((scaled, scaled), Image.Resampling.LANCZOS)
        crop_off = (scaled - stage_size) // 2
        art_cropped = art_resized.crop((crop_off, crop_off, crop_off + stage_size, crop_off + stage_size))

        stage_x = (WIDTH - stage_size) // 2
        stage_y = 395
        mask = Image.new("L", (stage_size, stage_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, stage_size, stage_size), radius=42, fill=255)
        canvas.paste(art_cropped, (stage_x, stage_y), mask)

        border_color = panic_rgb if is_panic else (accent_rgb if beat_idx == 3 else (58, 64, 82))
        draw.rounded_rectangle(
            (stage_x - 3, stage_y - 3, stage_x + stage_size + 3, stage_y + stage_size + 3),
            radius=44,
            outline=border_color,
            width=4,
        )

        # Top-Left Episodic Badge + Handle Pill (y=130)
        badge_text = f"EP. {episode_num:02d}"
        b_box = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw = (b_box[2] - b_box[0]) + 32
        draw.rounded_rectangle((70, 130, 70 + bw, 184), radius=14, fill=panic_rgb)
        draw.text((86, 140), badge_text, font=font_badge, fill=(255, 255, 255))
        draw.text((70 + bw + 20, 142), handle_str, font=font_wm, fill=(165, 172, 188))

        # 2-Line Permanent Top POV Hook Banner (white line 1 + brand accent line 2)
        l1_lines = wrap_text(draw, hook_l1, font_hook, WIDTH - 120)[:1]
        l2_lines = wrap_text(draw, hook_l2, font_hook, WIDTH - 120)[:1]
        if l1_lines:
            bb1 = draw.textbbox((0, 0), l1_lines[0], font=font_hook)
            w1 = bb1[2] - bb1[0]
            draw.text(((WIDTH - w1) // 2, 215), l1_lines[0], font=font_hook, fill=(255, 255, 255))
        if l2_lines:
            bb2 = draw.textbbox((0, 0), l2_lines[0], font=font_hook)
            w2 = bb2[2] - bb2[0]
            draw.text(((WIDTH - w2) // 2, 285), l2_lines[0], font=font_hook, fill=accent_rgb)

        # Optional Left vs. Right Comparison Pills
        if left_label and right_label:
            draw.rounded_rectangle((stage_x + 28, stage_y + 24, stage_x + 430, stage_y + 82), radius=16, fill=(38, 42, 54))
            draw.text((stage_x + 48, stage_y + 36), left_label[:18], font=font_split, fill=(255, 255, 255))
            draw.rounded_rectangle((stage_x + stage_size - 430, stage_y + 24, stage_x + stage_size - 28, stage_y + 82), radius=16, fill=panic_rgb)
            draw.text((stage_x + stage_size - 410, stage_y + 36), right_label[:18], font=font_split, fill=(255, 255, 255))

        # Karaoke Active-Word Highlight Pill (y=1375)
        words = beat.get("caption", "").split()
        if words:
            active_word_idx = min(len(words) - 1, int(progress * len(words)))
            word_widths = []
            space_w = draw.textbbox((0, 0), " ", font=font_sub)[2]
            for w_str in words:
                wb = draw.textbbox((0, 0), w_str, font=font_sub)
                word_widths.append(wb[2] - wb[0])
            total_w = sum(word_widths) + space_w * (len(words) - 1)
            pill_w = min(WIDTH - 110, total_w + 68)
            pill_x = (WIDTH - pill_w) // 2
            pill_y = 1375
            draw.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + 86), radius=24, fill=(22, 25, 34), outline=(55, 62, 78), width=2)

            cur_x = (WIDTH - total_w) // 2
            for w_i, w_str in enumerate(words):
                color = (panic_rgb if is_panic else accent_rgb) if w_i == active_word_idx else (248, 250, 252)
                draw.text((cur_x, pill_y + 18), w_str, font=font_sub, fill=color)
                cur_x += word_widths[w_i] + space_w

        # Progress Bar
        overall_prog = (f_idx + 1) / float(TOTAL_FRAMES)
        draw.rounded_rectangle((140, 1488, WIDTH - 140, 1498), radius=5, fill=(36, 40, 52))
        draw.rounded_rectangle((140, 1488, 140 + int((WIDTH - 280) * overall_prog), 1498), radius=5, fill=accent_rgb)

        frame_file = frames_dir / f"frame_{f_idx:04d}.png"
        canvas.save(frame_file, "PNG")
        if f_idx == 12:
            canvas.save(cover_frame_path, "JPEG", quality=92)

    return cover_frame_path


# ==============================================================================
# 8. FFMPEG ENCODING & META GRAPH API REELS PUBLISHER
# ==============================================================================
def encode_mp4(frames_dir: Path, wav_path: Path, out_mp4: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "frame_%04d.png"),
        "-i", str(wav_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


def wait_for_public_url(url: str, max_wait_sec: int = 90) -> bool:
    print(f"[CDN] Waiting for {url} to go live on GitHub Pages...")
    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"[CDN] Verified live (HTTP 200): {url}")
                    return True
        except Exception:
            pass
        time.sleep(5)
    print(f"[CDN] Warning: Timed out waiting for {url} after {max_wait_sec}s.")
    return False


def graph_api_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/v21.0/{endpoint}"
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Graph API POST {endpoint} failed ({err.code}): {body}") from err


def graph_api_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    url = f"https://graph.facebook.com/v21.0/{endpoint}?{qs}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Graph API GET {endpoint} failed ({err.code}): {body}") from err


def publish_to_instagram(
    account: Dict[str, Any],
    video_url: str,
    cover_url: str,
    caption: str,
) -> Optional[str]:
    ig_user_id = (account.get("ig_user_id") or os.environ.get("IG_USER_ID", "")).strip()
    token_secret_name = account.get("token_secret", "IG_ACCESS_TOKEN")
    access_token = os.environ.get(token_secret_name, "").strip()

    if not ig_user_id:
        raise RuntimeError(f"Missing ig_user_id for {account.get('handle')}.")
    if not access_token:
        raise RuntimeError(f"Missing secret env var '{token_secret_name}' for {account.get('handle')}.")
    if not GITHUB_PAGES_BASE_URL:
        raise RuntimeError("Missing GITHUB_PAGES_BASE_URL variable/secret.")

    wait_for_public_url(video_url, max_wait_sec=90)

    container_payload: Dict[str, Any] = {
        "media_type": "REELS",
        "video_url": video_url,
        "cover_url": cover_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": access_token,
    }
    if USE_TRIAL_REELS:
        container_payload["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})

    print(f"[Publish] Creating IG Reel container on {account.get('handle')} ({ig_user_id})...")
    created = graph_api_post(f"{ig_user_id}/media", container_payload)
    creation_id = created.get("id")
    if not creation_id:
        raise RuntimeError(f"Failed to create IG container: {created}")

    for attempt in range(24):
        time.sleep(5)
        status_resp = graph_api_get(
            creation_id,
            {"fields": "status_code,status", "access_token": access_token},
        )
        code = status_resp.get("status_code")
        print(f"[Publish] Poll {attempt + 1}: status_code={code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"IG media processing failed: {status_resp}")
    else:
        raise TimeoutError("Timed out waiting for IG media container to finish processing.")

    published = graph_api_post(
        f"{ig_user_id}/media_publish",
        {"creation_id": creation_id, "access_token": access_token},
    )
    media_id = published.get("id")
    print(f"[Publish] Published Reel to {account.get('handle')}! Media ID: {media_id}")
    return media_id


# ==============================================================================
# 9. RENDER & PUBLISH PIPELINE
# ==============================================================================
def run_render_step() -> List[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    if genai is None:
        raise RuntimeError("google-genai package is not installed.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    accounts = [a for a in load_accounts() if a.get("enabled", True)]
    if not accounts:
        raise RuntimeError("No enabled accounts found in accounts configuration.")

    text_models, gemini_img_models, imagen_models = discover_models(client)
    history = load_history()
    manifests: List[Dict[str, Any]] = []

    for account in accounts:
        slug = account["slug"]
        episode_num = int(history.get("episode_count", 0)) + 1
        seed = int(datetime.now(timezone.utc).timestamp()) + episode_num

        research_brief = run_autonomous_research(client, text_models, account, history)
        script_data = generate_viral_script(client, text_models, account, research_brief, episode_num)
        print(f"[Script:{slug}] Hook: {script_data.get('hook_line_1')} / {script_data.get('hook_line_2_gold')}")

        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)
        WORK_DIR.mkdir(parents=True, exist_ok=True)

        art_paths = []
        used_generators = []
        skip_api_images = False
        for idx, beat in enumerate(script_data["beats"]):
            art_file = WORK_DIR / f"beat_{idx + 1}.png"
            gen_used, skip_api_images = generate_beat_artwork(
                client, gemini_img_models, imagen_models, beat, account, art_file, seed, skip_api_images
            )
            art_paths.append(art_file)
            used_generators.append(gen_used)
            print(f"[Art:{slug}] Beat {idx + 1} rendered via {gen_used}")

        wav_path = WORK_DIR / "audio.wav"
        synthesize_reel_audio(script_data["beats"], wav_path, seed)

        frames_dir = WORK_DIR / "frames"
        cover_local = render_frames(script_data, account, art_paths, episode_num, frames_dir)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        mp4_filename = f"{slug}_ep{episode_num:03d}_{stamp}.mp4"
        jpg_filename = f"{slug}_ep{episode_num:03d}_{stamp}.jpg"
        final_mp4 = MEDIA_DIR / mp4_filename
        final_jpg = MEDIA_DIR / jpg_filename

        encode_mp4(frames_dir, wav_path, final_mp4)
        shutil.copy2(cover_local, final_jpg)
        print(f"[Render:{slug}] Saved {final_mp4} ({final_mp4.stat().st_size // 1024} KB)")

        item_manifest = {
            "slug": slug,
            "handle": account["handle"],
            "episode": episode_num,
            "timestamp_utc": stamp,
            "mp4_filename": mp4_filename,
            "jpg_filename": jpg_filename,
            "caption": script_data.get("instagram_caption", ""),
            "archetype": script_data.get("archetype"),
            "hook_line_1": script_data.get("hook_line_1"),
            "hook_line_2_gold": script_data.get("hook_line_2_gold"),
            "trend_inspiration": research_brief.get("trend_inspiration"),
            "generators": used_generators,
            "published": False,
            "ig_media_id": None,
        }
        manifests.append(item_manifest)
        history["episode_count"] = episode_num
        history.setdefault("reels", []).append(item_manifest)

    MANIFEST_FILE.write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    save_history(history)
    return manifests


def run_publish_step() -> None:
    if not MANIFEST_FILE.exists():
        raise RuntimeError(f"Manifest {MANIFEST_FILE} not found. Run --render first.")

    raw_manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifests = raw_manifest if isinstance(raw_manifest, list) else [raw_manifest]
    accounts_by_slug = {a["slug"]: a for a in load_accounts()}
    base = GITHUB_PAGES_BASE_URL.rstrip("/")

    for item in manifests:
        if item.get("published"):
            print(f"[Publish] {item.get('handle')} Episode #{item.get('episode')} already published.")
            continue

        slug = item.get("slug", "wearechillclub")
        account = accounts_by_slug.get(slug, DEFAULT_ACCOUNTS[0])
        video_public_url = f"{base}/reels/{item['mp4_filename']}"
        cover_public_url = f"{base}/reels/{item['jpg_filename']}"

        media_id = publish_to_instagram(
            account,
            video_public_url,
            cover_public_url,
            item.get("caption", ""),
        )
        item["published"] = True
        item["ig_media_id"] = media_id

    MANIFEST_FILE.write_text(json.dumps(manifests, indent=2), encoding="utf-8")

    history = load_history()
    published_map = {m["episode"]: m["ig_media_id"] for m in manifests if m.get("published")}
    for h_item in history.get("reels", []):
        ep = h_item.get("episode")
        if ep in published_map:
            h_item["published"] = True
            h_item["ig_media_id"] = published_map[ep]
    save_history(history)


def main() -> None:
    args = set(sys.argv[1:])
    if "--render" in args:
        run_render_step()
    elif "--publish" in args:
        run_publish_step()
    else:
        run_render_step()
        run_publish_step()


if __name__ == "__main__":
    main()
