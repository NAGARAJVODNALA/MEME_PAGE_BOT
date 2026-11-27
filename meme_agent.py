#!/usr/bin/env python3
"""
MEME_PAGE_BOT — Automated Stickman Comedy Reels Engine
Upgrades included:
- Forward-Kinematics (FK) skeleton rig (zero detached shoulders/hands)
- 2x Supersampling anti-aliased rendering (2160x3840 -> 1080x1920)
- Dynamic story-driven environments & 2.5D foreground occlusion (zero sofa/home defaults)
- Character accessories, expressive faces, overshoot easing, & 1-frame manga impact flash
- Multi-hook retention pacing + alternating 1 Short (6s loop) / 1 Long (12s skit) cadence
- Pure-Python procedural SFX + character speech blips + Google Lyria RealTime (with synth fallback)
- Pre-publish FFprobe / pixel-variance QA gate + Meta Graph API v21.0 Insights feedback loop
"""

import asyncio
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import textwrap
import time
import wave
from typing import List, Literal, Optional, Tuple

import numpy as np
import requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, Field

# ==============================================================================
# 1. CONFIGURATION & CONSTANTS
# ==============================================================================

W, H = 1080, 1920
SCALE = 2  # 2x supersampling for crisp anti-aliased lines
FPS = 24
SAMPLE_RATE = 44100

# Fixed skeleton proportions in logical 1080x1920 space
TORSO_LEN = 148
UPPER_ARM = 80
FOREARM = 76
THIGH_LEN = 94
SHIN_LEN = 92
HEAD_R = 46
STROKE = 12

STATE_FILE = "pipeline_state.json"
SFX_DIR = "assets/sfx"
BUILD_DIR = "build"
REELS_OUT_DIR = "docs/reels"
GRAPH_BASE = "https://graph.facebook.com/v21.0"

ALL_SETTINGS = [
    "office_interview",
    "airport_security",
    "gym_weight_room",
    "courtroom",
    "drive_thru_lane",
    "supermarket_checkout",
    "doctor_exam_room",
    "crowded_elevator",
    "rooftop_ledge",
    "bank_vault",
]

# ==============================================================================
# 2. STRICT PYDANTIC SCHEMA (ELIMINATES JSON / KEYERROR CRASHES)
# ==============================================================================

SettingType = Literal[
    "office_interview",
    "airport_security",
    "gym_weight_room",
    "courtroom",
    "drive_thru_lane",
    "supermarket_checkout",
    "doctor_exam_room",
    "crowded_elevator",
    "rooftop_ledge",
    "bank_vault",
]

PropType = Literal[
    "none",
    "laptop",
    "briefcase",
    "dumbbell",
    "gavel",
    "clipboard",
    "megaphone",
    "shopping_cart",
    "coffee_cup",
    "red_button",
    "pile_of_cash",
]

AccessoryType = Literal[
    "none",
    "tie",
    "glasses",
    "police_cap",
    "gym_headband",
    "judge_wig",
    "crown",
]

SFXType = Literal[
    "none",
    "whoosh",
    "pop",
    "vine_boom",
    "bonk",
    "record_scratch",
    "ding",
]


class CharacterPose(BaseModel):
    x: int = Field(ge=210, le=870, description="Hip X on 1080px canvas")
    y: int = Field(ge=960, le=1520, description="Hip Y on 1080px canvas")
    spine_deg: float = Field(ge=-125, le=-55, description="-90 is straight upright")
    left_shoulder_deg: float = Field(ge=-180, le=180, description="Angle from neck")
    left_elbow_deg: float = Field(ge=-145, le=145, description="Relative elbow bend")
    right_shoulder_deg: float = Field(ge=-180, le=180, description="Angle from neck")
    right_elbow_deg: float = Field(ge=-145, le=145, description="Relative elbow bend")
    left_hip_deg: float = Field(ge=35, le=145, description="90 is straight down")
    left_knee_deg: float = Field(ge=-120, le=120, description="Relative knee bend")
    right_hip_deg: float = Field(ge=35, le=145, description="90 is straight down")
    right_knee_deg: float = Field(ge=-120, le=120, description="Relative knee bend")
    eyebrows: Literal["neutral", "angry", "shocked", "smug"] = "neutral"
    mouth: Literal["flat", "open_o", "grin", "wavy"] = "flat"
    accessory: AccessoryType = "none"
    held_prop: PropType = "none"
    speech_bubble: Optional[str] = Field(default=None, max_length=36)


class Keyframe(BaseModel):
    timestamp_sec: float = Field(ge=0.0, le=14.0)
    camera_zoom: float = Field(ge=1.0, le=1.55, description="1.0 wide, 1.4 closeup")
    camera_focus: Literal["center", "hero", "npc"] = "center"
    screen_shake: bool = False
    sfx: SFXType = "none"
    hero: CharacterPose
    npc: Optional[CharacterPose] = None


class ReelScript(BaseModel):
    mode: Literal["short_loop", "long_skit"]
    total_duration_sec: float = Field(ge=5.5, le=14.0)
    setting: SettingType
    top_hook_banner: str = Field(
        max_length=36,
        description="4-6 word curiosity gap hook displayed at 0.0s above IG UI",
    )
    lyria_music_prompt: str = Field(
        description="Instrumental tempo and comedy mood prompt for Google Lyria"
    )
    caption: str = Field(max_length=180)
    first_comment_hook: str = Field(
        max_length=95,
        description="Engagement question posted immediately after publishing",
    )
    keyframes: List[Keyframe] = Field(min_length=4, max_length=9)


# ==============================================================================
# 3. STATE & INSIGHTS FEEDBACK LOOP
# ==============================================================================

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("run_count", 0)
                data.setdefault("recent_settings", [])
                data.setdefault("published_history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"run_count": 0, "recent_settings": [], "published_history": []}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def fetch_top_performing_patterns(ig_user_id: str, access_token: str, history: list) -> str:
    """Queries Meta Graph API v21.0 Reels Insights to guide future comedy scripts."""
    if not ig_user_id or not access_token or not history:
        return "Maximize visual shock in the first 0.4 seconds and end on a sharp punchline."

    scored = []
    for item in history[-10:]:
        media_id = item.get("media_id")
        if not media_id:
            continue
        try:
            r = requests.get(
                f"{GRAPH_BASE}/{media_id}/insights",
                params={
                    "metric": "reach,saved,shares,ig_reels_avg_watch_time",
                    "access_token": access_token,
                },
                timeout=10,
            )
            if r.status_code != 200:
                continue
            metrics = {
                m["name"]: m["values"][0]["value"]
                for m in r.json().get("data", [])
                if m.get("values")
            }
            score = (
                (metrics.get("ig_reels_avg_watch_time", 0) / 1000.0)
                + metrics.get("shares", 0) * 5.0
                + metrics.get("saved", 0) * 4.0
            )
            scored.append((score, item))
        except requests.RequestException:
            continue

    if not scored:
        return "Maximize visual shock in the first 0.4 seconds and end on a sharp punchline."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [
        f"[Setting={x[1]['setting']}, Hook='{x[1]['hook']}', Mode={x[1]['mode']}]"
        for x in scored[:3]
    ]
    return "Replicate the comedic timing and hook style of these top performers: " + ", ".join(top)


# ==============================================================================
# 4. GEMINI SCRIPT GENERATOR + TIMESTAMP NORMALIZER
# ==============================================================================

def normalize_script(script: ReelScript) -> ReelScript:
    """Guarantees valid, monotonic keyframe timestamps so rendering never divides by zero."""
    kfs = sorted(script.keyframes, key=lambda k: k.timestamp_sec)
    kfs[0].timestamp_sec = 0.0
    for i in range(1, len(kfs)):
        min_ts = round(kfs[i - 1].timestamp_sec + 0.35, 2)
        if kfs[i].timestamp_sec < min_ts:
            kfs[i].timestamp_sec = min_ts
    final_dur = max(script.total_duration_sec, round(kfs[-1].timestamp_sec + 0.4, 2))
    kfs[-1].timestamp_sec = final_dur
    script.total_duration_sec = final_dur
    script.keyframes = kfs
    return script


def generate_script(
    client: genai.Client,
    mode: str,
    banned_settings: List[str],
    insights_hint: str,
) -> ReelScript:
    available = [s for s in ALL_SETTINGS if s not in banned_settings] or ALL_SETTINGS

    if mode == "short_loop":
        pacing_spec = (
            "MODE: short_loop (Target 6.0 seconds, 5 keyframes at 0.0s, 1.4s, 2.8s, 4.4s, 6.0s). "
            "Start IN MEDIA RES at 0.0s (mid-action/shock, NEVER idle standing). "
            "Hit a sudden escalation at 2.8s, deliver the visual twist at 4.4s with camera_zoom=1.4 and vine_boom/bonk, "
            "and pose the 6.0s frame so it visually loops seamlessly back into 0.0s."
        )
    else:
        pacing_spec = (
            "MODE: long_skit (Target 12.0 seconds, 8 keyframes spaced ~1.7s apart). "
            "Stack retention hooks every 2.5s: 0.0s immediate visual shock + top_hook_banner, "
            "3.5s awkward escalation + camera zoom, 7.0s false ending/twist, 10.5s ultimate punchline with screen_shake=true."
        )

    prompt = f"""
You are an elite viral short-form comedy director creating a vertical 9:16 stickman Instagram Reel.
{pacing_spec}

STRICT ENVIRONMENT & VISUAL RULES:
1. NEVER set the story at home, in a living room, bedroom, or on a sofa/couch.
2. Choose `setting` EXCLUSIVELY from this fresh list: {available}.
3. Use `hero` (left/center, x around 340-480) and `npc` (right, x around 640-760) with distinct `accessory` roles (e.g., boss with tie, judge with judge_wig, officer with police_cap, gym bro with gym_headband) and relevant `held_prop` items.
4. Keep every `speech_bubble` ultra-punchy (MAX 28 characters) and alternate speakers so bubbles don't overlap.
5. `top_hook_banner` must be 4-6 words creating an instant curiosity gap (e.g., "HR WAS NOT READY FOR THIS").
6. {insights_hint}
"""

    last_err = None
    for attempt in range(1, 4):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReelScript,
                    temperature=0.92,
                ),
            )
            script = ReelScript.model_validate_json(resp.text)
            return normalize_script(script)
        except Exception as exc:
            last_err = exc
            print(f"[Warn] Gemini script attempt {attempt} failed: {exc}")
            time.sleep(2 * attempt)

    raise RuntimeError(f"Failed to generate valid ReelScript after 3 attempts: {last_err}")


# ==============================================================================
# 5. FORWARD-KINEMATICS RENDERER (2X SUPERSAMPLED + 2.5D LAYERING + JUICE)
# ==============================================================================

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size * SCALE)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size * SCALE)
    except TypeError:
        return ImageFont.load_default()


def polar(origin: Tuple[float, float], length: float, angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    return (origin[0] + length * math.cos(rad), origin[1] + length * math.sin(rad))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_out_back(t: float, s: float = 1.45) -> float:
    """Snappy comedic overshoot easing so punchline poses pop."""
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((s + 1.0) * t + s) + 1.0


def interpolate_pose(p1: CharacterPose, p2: CharacterPose, t: float) -> CharacterPose:
    e = ease_out_back(t)
    return CharacterPose(
        x=int(max(210, min(870, lerp(p1.x, p2.x, e)))),
        y=int(max(960, min(1520, lerp(p1.y, p2.y, e)))),
        spine_deg=lerp(p1.spine_deg, p2.spine_deg, e),
        left_shoulder_deg=lerp(p1.left_shoulder_deg, p2.left_shoulder_deg, e),
        left_elbow_deg=lerp(p1.left_elbow_deg, p2.left_elbow_deg, e),
        right_shoulder_deg=lerp(p1.right_shoulder_deg, p2.right_shoulder_deg, e),
        right_elbow_deg=lerp(p1.right_elbow_deg, p2.right_elbow_deg, e),
        left_hip_deg=lerp(p1.left_hip_deg, p2.left_hip_deg, e),
        left_knee_deg=lerp(p1.left_knee_deg, p2.left_knee_deg, e),
        right_hip_deg=lerp(p1.right_hip_deg, p2.right_hip_deg, e),
        right_knee_deg=lerp(p1.right_knee_deg, p2.right_knee_deg, e),
        eyebrows=p2.eyebrows if t >= 0.35 else p1.eyebrows,
        mouth=p2.mouth if t >= 0.35 else p1.mouth,
        accessory=p2.accessory if t >= 0.2 else p1.accessory,
        held_prop=p2.held_prop if t >= 0.2 else p1.held_prop,
        speech_bubble=p1.speech_bubble if t < 0.85 else p2.speech_bubble,
    )


def draw_segment(
    draw: ImageDraw.ImageDraw,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    color=(22, 24, 28),
    width: int = STROKE,
):
    sp1 = (p1[0] * SCALE, p1[1] * SCALE)
    sp2 = (p2[0] * SCALE, p2[1] * SCALE)
    sw = width * SCALE
    r = sw // 2
    draw.line([sp1, sp2], fill=color, width=sw)
    draw.ellipse([sp1[0] - r, sp1[1] - r, sp1[0] + r, sp1[1] + r], fill=color)
    draw.ellipse([sp2[0] - r, sp2[1] - r, sp2[0] + r, sp2[1] + r], fill=color)


def draw_environment_bg(draw: ImageDraw.ImageDraw, setting: str):
    """Draws story-specific architectural backgrounds behind characters."""
    palettes = {
        "office_interview": ((236, 242, 248), (195, 205, 218)),
        "airport_security": ((228, 240, 246), (175, 190, 205)),
        "gym_weight_room": ((232, 232, 236), (130, 135, 145)),
        "courtroom": ((242, 232, 218), (165, 118, 78)),
        "drive_thru_lane": ((214, 238, 252), (110, 115, 122)),
        "supermarket_checkout": ((244, 246, 238), (190, 200, 185)),
        "doctor_exam_room": ((232, 248, 246), (185, 218, 216)),
        "crowded_elevator": ((222, 226, 232), (155, 162, 172)),
        "rooftop_ledge": ((188, 224, 252), (120, 125, 134)),
        "bank_vault": ((220, 225, 230), (140, 148, 158)),
    }
    wall_col, floor_col = palettes.get(setting, ((242, 242, 245), (195, 200, 210)))

    draw.rectangle([0, 0, W * SCALE, 1540 * SCALE], fill=wall_col)
    draw.rectangle([0, 1540 * SCALE, W * SCALE, H * SCALE], fill=floor_col)
    draw.line([(0, 1540 * SCALE), (W * SCALE, 1540 * SCALE)], fill=(40, 40, 45), width=6 * SCALE)

    if setting == "office_interview":
        draw.rectangle([110 * SCALE, 440 * SCALE, 510 * SCALE, 850 * SCALE], fill=(255, 255, 255), outline=(60, 70, 85), width=8 * SCALE)
        draw.line([(150 * SCALE, 530 * SCALE), (430 * SCALE, 530 * SCALE)], fill=(220, 65, 65), width=8 * SCALE)
        draw.line([(150 * SCALE, 610 * SCALE), (370 * SCALE, 610 * SCALE)], fill=(65, 115, 210), width=8 * SCALE)

    elif setting == "airport_security":
        draw.rectangle([140 * SCALE, 410 * SCALE, 940 * SCALE, 650 * SCALE], fill=(28, 34, 44), outline=(80, 90, 105), width=8 * SCALE)
        for row in range(3):
            y = (465 + row * 55) * SCALE
            draw.line([(180 * SCALE, y), (740 * SCALE, y)], fill=(245, 200, 66), width=10 * SCALE)

    elif setting == "gym_weight_room":
        draw.rectangle([150 * SCALE, 450 * SCALE, 930 * SCALE, 1210 * SCALE], fill=(212, 232, 242), outline=(90, 100, 112), width=8 * SCALE)
        draw.line([(720 * SCALE, 780 * SCALE), (720 * SCALE, 1540 * SCALE)], fill=(45, 48, 54), width=14 * SCALE)
        draw.line([(900 * SCALE, 780 * SCALE), (900 * SCALE, 1540 * SCALE)], fill=(45, 48, 54), width=14 * SCALE)
        draw.line([(660 * SCALE, 960 * SCALE), (960 * SCALE, 960 * SCALE)], fill=(30, 30, 35), width=12 * SCALE)

    elif setting == "courtroom":
        draw.ellipse([200 * SCALE, 500 * SCALE, 420 * SCALE, 720 * SCALE], outline=(165, 125, 55), width=10 * SCALE)

    elif setting == "drive_thru_lane":
        draw.rectangle([640 * SCALE, 640 * SCALE, 970 * SCALE, 1210 * SCALE], fill=(35, 42, 52), outline=(220, 60, 50), width=10 * SCALE)
        draw.rectangle([760 * SCALE, 1210 * SCALE, 840 * SCALE, 1540 * SCALE], fill=(70, 75, 82))

    elif setting == "supermarket_checkout":
        draw.rectangle([140 * SCALE, 460 * SCALE, 460 * SCALE, 760 * SCALE], fill=(255, 235, 100), outline=(40, 40, 40), width=7 * SCALE)

    elif setting == "doctor_exam_room":
        draw.rectangle([140 * SCALE, 450 * SCALE, 440 * SCALE, 860 * SCALE], fill=(255, 255, 255), outline=(70, 130, 130), width=7 * SCALE)
        draw.line([(290 * SCALE, 520 * SCALE), (290 * SCALE, 640 * SCALE)], fill=(210, 50, 50), width=14 * SCALE)
        draw.line([(230 * SCALE, 580 * SCALE), (350 * SCALE, 580 * SCALE)], fill=(210, 50, 50), width=14 * SCALE)

    elif setting == "crowded_elevator":
        draw.rectangle([170 * SCALE, 550 * SCALE, 910 * SCALE, 1540 * SCALE], fill=(182, 190, 200), outline=(60, 66, 75), width=10 * SCALE)
        draw.line([(540 * SCALE, 550 * SCALE), (540 * SCALE, 1540 * SCALE)], fill=(60, 66, 75), width=8 * SCALE)
        draw.rectangle([450 * SCALE, 430 * SCALE, 630 * SCALE, 510 * SCALE], fill=(25, 28, 32))

    elif setting == "rooftop_ledge":
        for idx, (bx, bw, bh) in enumerate([(80, 160, 520), (270, 190, 680), (520, 170, 490), (740, 220, 620)]):
            draw.rectangle([bx * SCALE, (1420 - bh) * SCALE, (bx + bw) * SCALE, 1420 * SCALE], fill=(135 + idx * 10, 150 + idx * 8, 172))

    elif setting == "bank_vault":
        draw.ellipse([300 * SCALE, 560 * SCALE, 780 * SCALE, 1040 * SCALE], fill=(165, 172, 180), outline=(45, 50, 58), width=16 * SCALE)
        draw.ellipse([440 * SCALE, 700 * SCALE, 640 * SCALE, 900 * SCALE], outline=(45, 50, 58), width=12 * SCALE)


def draw_environment_fg(draw: ImageDraw.ImageDraw, setting: str):
    """2.5D foreground desks/counters drawn OVER lower bodies for real scene depth."""
    if setting == "office_interview":
        draw.rectangle([520 * SCALE, 1290 * SCALE, 980 * SCALE, 1540 * SCALE], fill=(168, 122, 82), outline=(40, 30, 20), width=7 * SCALE)
    elif setting == "courtroom":
        draw.rectangle([530 * SCALE, 1180 * SCALE, 1000 * SCALE, 1540 * SCALE], fill=(138, 86, 48), outline=(45, 28, 15), width=8 * SCALE)
    elif setting == "supermarket_checkout":
        draw.rectangle([500 * SCALE, 1310 * SCALE, 980 * SCALE, 1540 * SCALE], fill=(85, 95, 110), outline=(30, 35, 42), width=7 * SCALE)
    elif setting == "airport_security":
        draw.rectangle([480 * SCALE, 1360 * SCALE, 960 * SCALE, 1540 * SCALE], fill=(95, 105, 118), outline=(35, 40, 48), width=7 * SCALE)
    elif setting == "rooftop_ledge":
        draw.rectangle([0, 1420 * SCALE, W * SCALE, 1540 * SCALE], fill=(150, 155, 162), outline=(55, 58, 64), width=8 * SCALE)


def draw_prop(draw: ImageDraw.ImageDraw, hand_xy: Tuple[float, float], prop: str):
    if prop == "none":
        return
    hx, hy = hand_xy[0] * SCALE, hand_xy[1] * SCALE
    if prop == "briefcase":
        draw.rectangle([hx - 44 * SCALE, hy, hx + 44 * SCALE, hy + 60 * SCALE], fill=(120, 74, 38), outline=(25, 20, 15), width=6 * SCALE)
    elif prop == "dumbbell":
        draw.line([(hx - 46 * SCALE, hy), (hx + 46 * SCALE, hy)], fill=(40, 40, 45), width=10 * SCALE)
        draw.rectangle([hx - 56 * SCALE, hy - 26 * SCALE, hx - 36 * SCALE, hy + 26 * SCALE], fill=(30, 30, 35))
        draw.rectangle([hx + 36 * SCALE, hy - 26 * SCALE, hx + 56 * SCALE, hy + 26 * SCALE], fill=(30, 30, 35))
    elif prop == "gavel":
        draw.line([(hx, hy), (hx + 40 * SCALE, hy - 45 * SCALE)], fill=(130, 80, 40), width=8 * SCALE)
        draw.rectangle([hx + 18 * SCALE, hy - 65 * SCALE, hx + 62 * SCALE, hy - 35 * SCALE], fill=(110, 62, 28))
    elif prop == "pile_of_cash":
        draw.rectangle([hx - 42 * SCALE, hy - 24 * SCALE, hx + 42 * SCALE, hy + 18 * SCALE], fill=(76, 175, 80), outline=(27, 94, 32), width=5 * SCALE)
    elif prop == "clipboard":
        draw.rectangle([hx - 32 * SCALE, hy - 44 * SCALE, hx + 32 * SCALE, hy + 28 * SCALE], fill=(248, 245, 232), outline=(50, 50, 55), width=5 * SCALE)
    elif prop == "coffee_cup":
        draw.rectangle([hx - 18 * SCALE, hy - 28 * SCALE, hx + 18 * SCALE, hy + 14 * SCALE], fill=(255, 255, 255), outline=(40, 40, 40), width=5 * SCALE)
    elif prop == "laptop":
        draw.polygon([(hx - 38 * SCALE, hy), (hx + 38 * SCALE, hy), (hx + 52 * SCALE, hy - 44 * SCALE), (hx - 24 * SCALE, hy - 44 * SCALE)], fill=(180, 190, 205), outline=(30, 35, 42))
    elif prop == "red_button":
        draw.rectangle([hx - 32 * SCALE, hy - 10 * SCALE, hx + 32 * SCALE, hy + 14 * SCALE], fill=(70, 75, 80))
        draw.ellipse([hx - 22 * SCALE, hy - 28 * SCALE, hx + 22 * SCALE, hy - 2 * SCALE], fill=(230, 45, 45))
    elif prop == "megaphone":
        draw.polygon([(hx, hy), (hx + 54 * SCALE, hy - 26 * SCALE), (hx + 54 * SCALE, hy + 26 * SCALE)], fill=(245, 165, 35), outline=(30, 30, 30))
    elif prop == "shopping_cart":
        draw.rectangle([hx - 10 * SCALE, hy - 20 * SCALE, hx + 75 * SCALE, hy + 38 * SCALE], outline=(60, 65, 72), width=6 * SCALE)


def draw_accessory(draw: ImageDraw.ImageDraw, head_xy: Tuple[float, float], neck_xy: Tuple[float, float], accessory: str):
    cx, cy = head_xy[0] * SCALE, head_xy[1] * SCALE
    nx, ny = neck_xy[0] * SCALE, neck_xy[1] * SCALE
    hr = HEAD_R * SCALE

    if accessory == "tie":
        draw.polygon([(nx, ny + 8 * SCALE), (nx - 12 * SCALE, ny + 68 * SCALE), (nx, ny + 84 * SCALE), (nx + 12 * SCALE, ny + 68 * SCALE)], fill=(210, 42, 42))
    elif accessory == "glasses":
        draw.rectangle([cx - 28 * SCALE, cy - 16 * SCALE, cx - 4 * SCALE, cy + 2 * SCALE], outline=(20, 20, 25), width=4 * SCALE)
        draw.rectangle([cx + 4 * SCALE, cy - 16 * SCALE, cx + 28 * SCALE, cy + 2 * SCALE], outline=(20, 20, 25), width=4 * SCALE)
        draw.line([(cx - 4 * SCALE, cy - 8 * SCALE), (cx + 4 * SCALE, cy - 8 * SCALE)], fill=(20, 20, 25), width=4 * SCALE)
    elif accessory == "police_cap":
        draw.rectangle([cx - hr, cy - hr - 14 * SCALE, cx + hr, cy - hr + 6 * SCALE], fill=(28, 48, 92))
        draw.rectangle([cx - hr - 10 * SCALE, cy - hr + 2 * SCALE, cx + hr + 10 * SCALE, cy - hr + 10 * SCALE], fill=(15, 20, 30))
    elif accessory == "gym_headband":
        draw.rectangle([cx - hr + 2 * SCALE, cy - 28 * SCALE, cx + hr - 2 * SCALE, cy - 16 * SCALE], fill=(225, 55, 55))
    elif accessory == "judge_wig":
        draw.ellipse([cx - hr - 14 * SCALE, cy - hr - 12 * SCALE, cx + hr + 14 * SCALE, cy + 12 * SCALE], outline=(235, 235, 240), width=14 * SCALE)
    elif accessory == "crown":
        draw.polygon([(cx - 30 * SCALE, cy - hr), (cx - 22 * SCALE, cy - hr - 28 * SCALE), (cx, cy - hr - 12 * SCALE), (cx + 22 * SCALE, cy - hr - 28 * SCALE), (cx + 30 * SCALE, cy - hr)], fill=(250, 205, 45), outline=(40, 30, 10))


def draw_stickman(draw: ImageDraw.ImageDraw, pose: CharacterPose, accent_color=(22, 24, 28)) -> Tuple[float, float]:
    """Renders a Forward-Kinematics stickman and returns head_center in logical coords."""
    hip = (float(pose.x), float(pose.y))
    neck = polar(hip, TORSO_LEN, pose.spine_deg)
    head_center = polar(neck, HEAD_R + 8, pose.spine_deg)

    # 1. Spine (shared anchor for both shoulders)
    draw_segment(draw, hip, neck, color=accent_color)

    # 2. Legs (anchored directly to hip)
    for side in ("left", "right"):
        hip_ang = getattr(pose, f"{side}_hip_deg")
        knee_ang = hip_ang + getattr(pose, f"{side}_knee_deg")
        knee = polar(hip, THIGH_LEN, hip_ang)
        foot = polar(knee, SHIN_LEN, knee_ang)
        draw_segment(draw, hip, knee, color=accent_color)
        draw_segment(draw, knee, foot, color=accent_color)

    # 3. Arms (anchored directly to neck — zero detachment)
    right_hand = neck
    for side in ("left", "right"):
        sh_ang = getattr(pose, f"{side}_shoulder_deg")
        el_ang = sh_ang + getattr(pose, f"{side}_elbow_deg")
        elbow = polar(neck, UPPER_ARM, sh_ang)
        hand = polar(elbow, FOREARM, el_ang)
        draw_segment(draw, neck, elbow, color=accent_color)
        draw_segment(draw, elbow, hand, color=accent_color)
        hx, hy = hand[0] * SCALE, hand[1] * SCALE
        hr = 10 * SCALE
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=accent_color)
        if side == "right":
            right_hand = hand

    # 4. Held Prop on right hand
    draw_prop(draw, right_hand, pose.held_prop)

    # 5. Head + Face + Role Accessory
    cx, cy = head_center[0] * SCALE, head_center[1] * SCALE
    hr = HEAD_R * SCALE
    draw.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=(255, 255, 255), outline=accent_color, width=STROKE * SCALE)

    eye_dx, eye_dy = 16 * SCALE, -6 * SCALE
    for dir_x in (-1, 1):
        ex = cx + dir_x * eye_dx
        ey = cy + eye_dy
        draw.ellipse([ex - 5 * SCALE, ey - 5 * SCALE, ex + 5 * SCALE, ey + 5 * SCALE], fill=accent_color)
        if pose.eyebrows == "angry":
            draw.line([(ex - 11 * SCALE, ey - 15 * SCALE * dir_x), (ex + 11 * SCALE, ey - 8 * SCALE)], fill=accent_color, width=5 * SCALE)
        elif pose.eyebrows == "shocked":
            draw.arc([ex - 11 * SCALE, ey - 23 * SCALE, ex + 11 * SCALE, ey - 8 * SCALE], 180, 360, fill=accent_color, width=5 * SCALE)
        elif pose.eyebrows == "smug":
            draw.line([(ex - 10 * SCALE, ey - 13 * SCALE), (ex + 10 * SCALE, ey - 15 * SCALE)], fill=accent_color, width=5 * SCALE)

    my = cy + 17 * SCALE
    if pose.mouth == "open_o":
        draw.ellipse([cx - 11 * SCALE, my - 11 * SCALE, cx + 11 * SCALE, my + 11 * SCALE], fill=(210, 55, 55), outline=accent_color, width=4 * SCALE)
    elif pose.mouth == "grin":
        draw.arc([cx - 18 * SCALE, my - 12 * SCALE, cx + 18 * SCALE, my + 12 * SCALE], 0, 180, fill=accent_color, width=5 * SCALE)
    elif pose.mouth == "wavy":
        draw.arc([cx - 16 * SCALE, my - 6 * SCALE, cx, my + 6 * SCALE], 0, 180, fill=accent_color, width=5 * SCALE)
        draw.arc([cx, my - 6 * SCALE, cx + 16 * SCALE, my + 6 * SCALE], 180, 360, fill=accent_color, width=5 * SCALE)
    else:
        draw.line([(cx - 14 * SCALE, my), (cx + 14 * SCALE, my)], fill=accent_color, width=5 * SCALE)

    draw_accessory(draw, head_center, neck, pose.accessory)
    return head_center


def draw_speech_bubble_with_tail(draw: ImageDraw.ImageDraw, head_xy: Tuple[float, float], text: str):
    """Draws an IG safe-zone clamped speech bubble with a triangular pointer to the speaker."""
    if not text:
        return
    font = get_font(32, bold=True)
    lines = textwrap.wrap(text.strip(), width=18)[:2]
    bw = 390 * SCALE
    bh = (68 + len(lines) * 38) * SCALE

    bx = max(70 * SCALE, min(520 * SCALE, int((head_xy[0] - 195) * SCALE)))
    by = max(375 * SCALE, min(1150 * SCALE, int((head_xy[1] - 220) * SCALE)))

    hx = max(bx + 40 * SCALE, min(bx + bw - 40 * SCALE, head_xy[0] * SCALE))
    hy = (head_xy[1] - 54) * SCALE
    tail = [(bx + bw // 2 - 18 * SCALE, by + bh - 4 * SCALE), (bx + bw // 2 + 18 * SCALE, by + bh - 4 * SCALE), (hx, hy)]
    draw.polygon(tail, fill=(255, 255, 255), outline=(20, 20, 25))
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24 * SCALE, fill=(255, 255, 255), outline=(20, 20, 25), width=6 * SCALE)

    for idx, line in enumerate(lines):
        draw.text((bx + 24 * SCALE, by + (22 + idx * 38) * SCALE), line, fill=(15, 15, 20), font=font)


def draw_top_hook_banner(draw: ImageDraw.ImageDraw, text: str):
    """High-contrast 0.0s curiosity hook placed above Instagram's UI overlay."""
    font = get_font(44, bold=True)
    box = [70 * SCALE, 180 * SCALE, (W - 70) * SCALE, 325 * SCALE]
    draw.rounded_rectangle(box, radius=26 * SCALE, fill=(255, 224, 48), outline=(18, 18, 22), width=8 * SCALE)
    draw.text((100 * SCALE, 224 * SCALE), text.upper()[:34], fill=(18, 18, 22), font=font)


def render_frame(script: ReelScript, t_sec: float, frame_idx: int) -> Image.Image:
    kfs = script.keyframes
    kf1, kf2 = kfs[0], kfs[-1]
    local_t = 0.0
    frames_since_kf1 = 999

    for i in range(len(kfs) - 1):
        if kfs[i].timestamp_sec <= t_sec <= kfs[i + 1].timestamp_sec:
            kf1, kf2 = kfs[i], kfs[i + 1]
            span = max(0.001, kf2.timestamp_sec - kf1.timestamp_sec)
            local_t = (t_sec - kf1.timestamp_sec) / span
            frames_since_kf1 = int(round((t_sec - kf1.timestamp_sec) * FPS))
            break

    canvas = Image.new("RGB", (W * SCALE, H * SCALE), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Background architecture
    draw_environment_bg(draw, script.setting)

    # 2. NPC (drawn before foreground desks so NPC stands behind counters)
    npc_pose = None
    npc_head = None
    if kf1.npc and kf2.npc:
        npc_pose = interpolate_pose(kf1.npc, kf2.npc, local_t)
        npc_head = draw_stickman(draw, npc_pose, accent_color=(32, 68, 128))

    # 3. 2.5D Foreground furniture occlusion
    draw_environment_fg(draw, script.setting)

    # 4. Hero character
    hero_pose = interpolate_pose(kf1.hero, kf2.hero, local_t)
    hero_head = draw_stickman(draw, hero_pose, accent_color=(20, 22, 26))

    # 5. Speech bubbles with pointers
    if npc_pose and npc_head and npc_pose.speech_bubble:
        draw_speech_bubble_with_tail(draw, npc_head, npc_pose.speech_bubble)
    if hero_pose.speech_bubble:
        draw_speech_bubble_with_tail(draw, hero_head, hero_pose.speech_bubble)

    # 6. Dynamic Camera Zoom + Screen Shake
    zoom = lerp(kf1.camera_zoom, kf2.camera_zoom, ease_out_back(local_t))
    if zoom > 1.01 or kf1.screen_shake:
        if kf2.camera_focus == "hero":
            focus_x, focus_y = hero_pose.x * SCALE, (hero_pose.y - 120) * SCALE
        elif kf2.camera_focus == "npc" and npc_pose:
            focus_x, focus_y = npc_pose.x * SCALE, (npc_pose.y - 120) * SCALE
        else:
            focus_x, focus_y = (W * SCALE) // 2, (H * SCALE) // 2

        shake_x = ((frame_idx % 3) - 1) * 18 * SCALE if kf1.screen_shake else 0
        shake_y = (((frame_idx + 1) % 3) - 1) * 18 * SCALE if kf1.screen_shake else 0

        crop_w = int((W * SCALE) / zoom)
        crop_h = int((H * SCALE) / zoom)
        x1 = max(0, min(W * SCALE - crop_w, int(focus_x - crop_w // 2 + shake_x)))
        y1 = max(0, min(H * SCALE - crop_h, int(focus_y - crop_h // 2 + shake_y)))
        canvas = canvas.crop((x1, y1, x1 + crop_w, y1 + crop_h)).resize(
            (W * SCALE, H * SCALE), Image.Resampling.BICUBIC
        )
        draw = ImageDraw.Draw(canvas)

    # 7. Pinned Top Hook Banner
    draw_top_hook_banner(draw, script.top_hook_banner)

    # 8. 1-Frame Manga Impact Flash on heavy comedic hits
    if kf1.sfx in ("vine_boom", "bonk") and frames_since_kf1 == 0 and frame_idx > 0:
        canvas = ImageOps.invert(canvas)

    # 9. Downsample 2x -> 1x for crisp anti-aliased 1080x1920 output
    return canvas.resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# 6. PURE-PYTHON SFX PACK + GOOGLE LYRIA REALTIME (WITH SYNTH FALLBACK)
# ==============================================================================

def write_mono_wav(path: str, samples: np.ndarray, sample_rate: int = SAMPLE_RATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def ensure_sfx_pack():
    """Generates zero-dependency comedy SFX and character speech blips."""
    # Pop
    t = np.linspace(0, 0.09, int(SAMPLE_RATE * 0.09), False)
    write_mono_wav(f"{SFX_DIR}/pop.wav", np.sin(2 * np.pi * np.linspace(380, 920, len(t)) * t) * np.exp(-t * 28))

    # Bonk
    t = np.linspace(0, 0.18, int(SAMPLE_RATE * 0.18), False)
    write_mono_wav(f"{SFX_DIR}/bonk.wav", np.tanh(2.2 * np.sin(2 * np.pi * np.linspace(260, 95, len(t)) * t)) * np.exp(-t * 16))

    # Vine Boom
    t = np.linspace(0, 0.65, int(SAMPLE_RATE * 0.65), False)
    write_mono_wav(f"{SFX_DIR}/vine_boom.wav", np.tanh(3.0 * np.sin(2 * np.pi * np.linspace(115, 36, len(t)) * t)) * np.exp(-t * 4.5))

    # Whoosh
    t = np.linspace(0, 0.22, int(SAMPLE_RATE * 0.22), False)
    rng = np.random.default_rng(42)
    write_mono_wav(f"{SFX_DIR}/whoosh.wav", rng.normal(0, 1, len(t)) * (np.sin(np.pi * (t / 0.22)) ** 2) * 0.45)

    # Ding
    t = np.linspace(0, 0.45, int(SAMPLE_RATE * 0.45), False)
    write_mono_wav(f"{SFX_DIR}/ding.wav", (np.sin(2 * np.pi * 1318 * t) + 0.4 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 7))

    # Record Scratch
    t = np.linspace(0, 0.28, int(SAMPLE_RATE * 0.28), False)
    chirp = np.sin(2 * np.pi * (950 + 450 * np.sin(2 * np.pi * 18 * t) - 2200 * t) * t)
    write_mono_wav(f"{SFX_DIR}/record_scratch.wav", np.tanh(2.5 * chirp) * np.exp(-t * 6) * 0.6)

    # Character Speech Blips
    for role, base_hz in [("blip_hero", 440), ("blip_npc", 235)]:
        chunks = []
        for i in range(4):
            bt = np.linspace(0, 0.055, int(SAMPLE_RATE * 0.055), False)
            pitch = base_hz * (1.0 + 0.14 * ((i % 2) - 0.5))
            chunks.append(np.sin(2 * np.pi * pitch * bt) * np.exp(-bt * 24))
            chunks.append(np.zeros(int(SAMPLE_RATE * 0.025)))
        write_mono_wav(f"{SFX_DIR}/{role}.wav", np.concatenate(chunks) * 0.65)


def synthesize_fallback_beat(out_wav: str, duration_sec: float):
    """Generates an upbeat 132 BPM comedy synth-bass backing track if Lyria times out."""
    n = int(SAMPLE_RATE * (duration_sec + 1.0))
    t = np.linspace(0, duration_sec + 1.0, n, False)
    bpm = 132.0
    beat_pos = (t * bpm / 60.0) % 1.0
    bar_step = ((t * bpm / 60.0).astype(int)) % 8

    notes = [130.81, 130.81, 155.56, 174.61, 196.00, 174.61, 155.56, 146.83]
    freqs = np.array([notes[s] for s in bar_step])
    bass = np.tanh(1.8 * np.sin(2 * np.pi * freqs * t)) * np.exp(-beat_pos * 6.5) * 0.35
    kick = np.sin(2 * np.pi * (110 * np.exp(-beat_pos * 18) + 42) * t) * np.exp(-beat_pos * 12) * 0.45
    write_mono_wav(out_wav, bass + kick)


async def _lyria_stream_to_wav(api_key: str, prompt: str, out_wav: str, duration_sec: float):
    lyria_client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    lyria_rate = 48000
    channels = 2
    target_bytes = int((duration_sec + 1.0) * lyria_rate * channels * 2)
    pcm_buffer = bytearray()

    async with lyria_client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(
            prompts=[types.WeightedPrompt(text=prompt, weight=1.0)]
        )
        await session.set_music_generation_config(
            config=types.LiveMusicGenerationConfig(bpm=130, temperature=1.0)
        )
        await session.play()
        async for msg in session.receive():
            server_content = getattr(msg, "server_content", None)
            if server_content and getattr(server_content, "audio_chunks", None):
                for chunk in server_content.audio_chunks:
                    if chunk.data:
                        pcm_buffer.extend(chunk.data)
            if len(pcm_buffer) >= target_bytes:
                break

    if len(pcm_buffer) < lyria_rate * channels * 2:
        raise RuntimeError("Insufficient audio bytes received from Lyria RealTime")

    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    with wave.open(out_wav, "w") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(lyria_rate)
        wf.writeframes(bytes(pcm_buffer[:target_bytes]))


def generate_background_music(api_key: str, prompt: str, out_wav: str, duration_sec: float):
    """Calls Google Lyria RealTime with a 25s guard and seamless synth fallback."""
    try:
        asyncio.run(
            asyncio.wait_for(
                _lyria_stream_to_wav(api_key, prompt, out_wav, duration_sec),
                timeout=25.0,
            )
        )
        print("[Info] Generated custom instrumental track via Google Lyria RealTime.")
    except Exception as exc:
        print(f"[Warn] Lyria RealTime unavailable ({exc}); using procedural comedy beat fallback.")
        synthesize_fallback_beat(out_wav, duration_sec)


def mix_audio_and_mux(
    silent_mp4: str,
    bg_wav: str,
    script: ReelScript,
    out_mp4: str,
):
    """Mixes background music + keyframe SFX + character speech blips at -14 LUFS."""
    dur = script.total_duration_sec
    events: List[Tuple[float, str]] = []

    for kf in script.keyframes:
        if kf.sfx != "none":
            events.append((kf.timestamp_sec, kf.sfx))
        if kf.hero and kf.hero.speech_bubble:
            events.append((kf.timestamp_sec + 0.05, "blip_hero"))
        if kf.npc and kf.npc.speech_bubble:
            events.append((kf.timestamp_sec + 0.05, "blip_npc"))

    cmd = ["ffmpeg", "-y", "-i", silent_mp4, "-i", bg_wav]
    valid_events = []
    for ts, name in events:
        wav_path = os.path.join(SFX_DIR, f"{name}.wav")
        if os.path.exists(wav_path) and ts < dur - 0.1:
            cmd.extend(["-i", wav_path])
            valid_events.append(int(ts * 1000))

    filters = [f"[1:a]apad,atrim=0:{dur:.2f},volume=0.65[bg]"]
    mix_inputs = ["[bg]"]
    for idx, delay_ms in enumerate(valid_events, start=2):
        filters.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume=1.15[sfx{idx}]")
        mix_inputs.append(f"[sfx{idx}]")

    filter_complex = (
        ";".join(filters)
        + f";{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0,"
        + "loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )

    os.makedirs(os.path.dirname(out_mp4), exist_ok=True)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{dur:.2f}",
        out_mp4,
    ])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio mux failed:\n{res.stderr}")


# ==============================================================================
# 7. PRE-PUBLISH QA GATE & META GRAPH API V21.0 PUBLISHER
# ==============================================================================

def run_qa_gate(mp4_path: str, expected_duration: float, sample_frames: List[Image.Image]):
    """Blocks publishing if streams, resolution, duration, or pixel variance fail."""
    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height:format=duration",
            "-of",
            "json",
            mp4_path,
        ],
        text=True,
    )
    meta = json.loads(probe)
    streams = {s["codec_type"]: s for s in meta.get("streams", [])}
    duration = float(meta["format"]["duration"])

    assert "video" in streams and streams["video"]["codec_name"] == "h264", "Invalid H.264 stream"
    assert streams["video"]["width"] == W and streams["video"]["height"] == H, "Invalid 1080x1920 resolution"
    assert "audio" in streams and streams["audio"]["codec_name"] == "aac", "Missing AAC audio stream"
    assert abs(duration - expected_duration) <= 0.45, f"Duration drift: {duration}s vs {expected_duration}s"

    for idx, img in enumerate(sample_frames):
        std = float(np.asarray(img).std())
        assert std > 12.0, f"Sample frame {idx} failed non-blank variance check (std={std:.2f})"

    print(f"[QA Passed] {mp4_path} verified ({duration:.2f}s, 1080x1920 H.264 + AAC).")


def prune_old_reels(directory: str, max_age_days: int = 7):
    """Keeps GitHub Pages repository lean while avoiding CDN cache collisions."""
    if not os.path.isdir(directory):
        return
    cutoff = time.time() - max_age_days * 86400
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if fname.endswith(".mp4") and os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
            os.remove(fpath)


def wait_for_github_pages(video_url: str, timeout_sec: int = 150):
    """Polls public GitHub Pages URL until HTTP 200 before calling Meta Graph API."""
    print(f"[Info] Waiting for GitHub Pages to serve {video_url} ...")
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.head(video_url, timeout=8, allow_redirects=True)
            if r.status_code == 200 and int(r.headers.get("Content-Length", "0")) > 25000:
                print("[Info] Public MP4 confirmed live on GitHub Pages.")
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    raise TimeoutError(f"GitHub Pages did not serve {video_url} within {timeout_sec}s")


def publish_to_instagram(
    ig_user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
    thumb_offset_ms: int,
    first_comment: str,
) -> str:
    """Creates Reels container, polls processing status, publishes, and posts first comment."""
    create_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "thumb_offset": thumb_offset_ms,
            "share_to_feed": "true",
            "access_token": access_token,
        },
        timeout=20,
    )
    create_data = create_resp.json()
    if "id" not in create_data:
        raise RuntimeError(f"IG container creation failed: {create_data}")
    creation_id = create_data["id"]

    # Poll until IG finishes processing the uploaded MP4
    for _ in range(30):
        status_resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}",
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=15,
        ).json()
        code = status_resp.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"IG media processing error: {status_resp}")
        time.sleep(5)
    else:
        raise TimeoutError("Timed out waiting for IG media container to finish processing")

    pub_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=20,
    ).json()
    if "id" not in pub_resp:
        raise RuntimeError(f"IG media_publish failed: {pub_resp}")
    media_id = pub_resp["id"]
    print(f"[Published] Instagram Reel ID: {media_id}")

    # Post immediate engagement-bait first comment
    if first_comment:
        requests.post(
            f"{GRAPH_BASE}/{media_id}/comments",
            data={"message": first_comment, "access_token": access_token},
            timeout=15,
        )
    return media_id


# ==============================================================================
# 8. CLI ENTRYPOINTS: `render` (STEP 1) & `publish` (STEP 2 AFTER GIT PUSH)
# ==============================================================================

def cmd_render():
    api_key = os.environ["GEMINI_API_KEY"]
    ig_user_id = os.environ.get("IG_USER_ID", "")
    ig_token = os.environ.get("IG_ACCESS_TOKEN", "")
    pages_base = os.environ.get("GITHUB_PAGES_BASE_URL", "").rstrip("/")

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(REELS_OUT_DIR, exist_ok=True)
    ensure_sfx_pack()
    prune_old_reels(REELS_OUT_DIR, max_age_days=7)

    state = load_state()
    mode = "short_loop" if state["run_count"] % 2 == 0 else "long_skit"
    insights_hint = fetch_top_performing_patterns(ig_user_id, ig_token, state["published_history"])

    client = genai.Client(api_key=api_key)
    script = generate_script(client, mode=mode, banned_settings=state["recent_settings"], insights_hint=insights_hint)
    print(f"[Script] Mode={script.mode} | Setting={script.setting} | Hook='{script.top_hook_banner}' | Dur={script.total_duration_sec}s")

    total_frames = int(round(script.total_duration_sec * FPS))
    silent_mp4 = os.path.join(BUILD_DIR, "silent.mp4")

    ffmpeg_proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", silent_mp4,
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    sample_frames = []
    sample_indices = {int(total_frames * 0.15), int(total_frames * 0.50), int(total_frames * 0.85)}

    try:
        for idx in range(total_frames):
            frame = render_frame(script, t_sec=idx / FPS, frame_idx=idx)
            if idx in sample_indices:
                sample_frames.append(frame)
            ffmpeg_proc.stdin.write(frame.tobytes())
        ffmpeg_proc.stdin.close()
        ret = ffmpeg_proc.wait()
        if ret != 0:
            err_msg = ffmpeg_proc.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg rawvideo pipe failed:\n{err_msg}")
    finally:
        if ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
            ffmpeg_proc.stdin.close()

    bg_wav = os.path.join(BUILD_DIR, "bg_music.wav")
    generate_background_music(api_key, script.lyria_music_prompt, bg_wav, script.total_duration_sec)

    run_stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    rel_mp4_path = f"reels/reel_{run_stamp}.mp4"
    final_mp4 = os.path.join("docs", rel_mp4_path)

    mix_audio_and_mux(silent_mp4, bg_wav, script, final_mp4)
    run_qa_gate(final_mp4, expected_duration=script.total_duration_sec, sample_frames=sample_frames)

    # Pick punchline keyframe (highest camera_zoom) as Explore cover frame
    punchline_kf = max(script.keyframes, key=lambda k: k.camera_zoom)
    thumb_offset_ms = int(min(script.total_duration_sec - 0.3, punchline_kf.timestamp_sec) * 1000)

    pending_meta = {
        "video_url": f"{pages_base}/{rel_mp4_path}" if pages_base else "",
        "caption": f"{script.caption}\n\n#stickman #animation #relatable #comedy #reels",
        "first_comment": script.first_comment_hook,
        "thumb_offset_ms": max(0, thumb_offset_ms),
        "mode": script.mode,
        "setting": script.setting,
        "hook": script.top_hook_banner,
    }
    with open(os.path.join(BUILD_DIR, "pending_publish.json"), "w", encoding="utf-8") as f:
        json.dump(pending_meta, f, indent=2)

    state["run_count"] += 1
    state["recent_settings"] = (state["recent_settings"] + [script.setting])[-5:]
    save_state(state)
    print(f"[Ready] Rendered {final_mp4} and saved metadata to build/pending_publish.json")


def cmd_publish():
    ig_user_id = os.environ["IG_USER_ID"]
    ig_token = os.environ["IG_ACCESS_TOKEN"]
    meta_path = os.path.join(BUILD_DIR, "pending_publish.json")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    wait_for_github_pages(meta["video_url"], timeout_sec=150)
    media_id = publish_to_instagram(
        ig_user_id=ig_user_id,
        access_token=ig_token,
        video_url=meta["video_url"],
        caption=meta["caption"],
        thumb_offset_ms=meta["thumb_offset_ms"],
        first_comment=meta["first_comment"],
    )

    state = load_state()
    state["published_history"].append({
        "media_id": media_id,
        "mode": meta["mode"],
        "setting": meta["setting"],
        "hook": meta["hook"],
        "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    state["published_history"] = state["published_history"][-25:]
    save_state(state)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "render"
    if action == "render":
        cmd_render()
    elif action == "publish":
        cmd_publish()
    else:
        raise ValueError(f"Unknown command '{action}'. Use 'render' or 'publish'.")
