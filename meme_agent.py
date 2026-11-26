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
SS = 2  # 2x supersampling (2160x3840 -> 1080x1920 Lanczos)

# ==============================================================================
# 10-15 SECOND STORY-FIRST PACING & VISUAL TUNING
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.14,
    "color_tint_strength": 0.06,
    "ambient_glow_strength": 0.12,
    "max_zoom_delta": 0.08,
    "transition_sec": 0.16,
    "enable_blur_transition": True,
    "target_min_sec": 10.0,
    "target_max_sec": 15.0,
    "min_beat_sec": 2.2,
    "max_beat_sec": 4.2,
}

# ==============================================================================
# SOLO CHARACTER BIBLE (@wearechillclub / v5_solo_pov)
# ==============================================================================
SOLO_CHARACTER_BIBLE = {
    "name": "Chill Solo",
    "cap_color": (122, 132, 92),     # Muted olive baseball cap
    "hoodie_color": (44, 47, 54),   # Dark charcoal hoodie
    "head_fill": (244, 242, 238),   # Clean white head
    "head_shadow": (214, 210, 204), # Warm marker shadow
    "ink_color": (18, 18, 22),      # Crisp uniform black ink
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

DEFAULT_PALETTE = {
    "tint": (210, 195, 175),
    "contrast": 1.04,
    "sat": 1.04,
    "card_bg": (20, 22, 28),
    "card_fg": (250, 250, 252),
    "accent": (255, 225, 45),
    "panic": (255, 75, 85),
}


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
            print(f"pages.json skipped ({e}), using default @wearechillclub config")
    return [{
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "layout_mode": "v5_solo_pov",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
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
            "Clean vector-neat 2D webcomic illustration starring ONE solo white-headed stickman "
            "character wearing a muted-olive baseball cap and dark charcoal hoodie, crisp uniform "
            "black ink outlines, cozy warm marker shading, atmospheric solo interior background, "
            "leave clean top space for a POV banner, strictly NO text or speech bubbles inside the drawing"
        ),
    }]


def fetch_world_context():
    headlines = []
    try:
        req = urllib.request.Request(
            "https://trends.google.com/trending/rss?geo=US",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            root = ET.fromstring(resp.read())
            for el in root.findall(".//item/title")[:6]:
                if el.text:
                    headlines.append(el.text.strip())
    except Exception as e:
        print(f"Trends feed skipped ({e}); continuing with open solo imagination.")
    return "\n".join(f"- {h}" for h in headlines) if headlines else "- Open everyday solo life"


# ==============================================================================
# PERSISTENT STORY & QUERY HISTORY TABLE (PREVENTING REPEATS)
# ==============================================================================
def load_story_history(slug, limit=80):
    hist_path = pathlib.Path("posts") / slug / "history.json"
    if hist_path.exists():
        try:
            items = json.loads(hist_path.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return items[-limit:]
        except Exception:
            return []
    return []


def build_history_table_text(history_items):
    if not history_items:
        return "| # | Date | Environment | Hook | Story Concept |\n|---|---|---|---|---|\n| - | None yet | - | - | - |"
    rows = ["| # | Date | Environment | Hook | Story Concept |", "|---|---|---|---|---|"]
    for i, item in enumerate(history_items[-40:], 1):
        dt = str(item.get("timestamp", ""))
        env = str(item.get("environment_name", ""))[:32].replace("|", "/")
        hook = str(item.get("top_hook", ""))[:45].replace("|", "/")
        concept = str(item.get("story_concept", ""))[:55].replace("|", "/")
        rows.append(f"| {i} | {dt} | {env} | {hook} | {concept} |")
    return "\n".join(rows)


def write_history_table_md(slug, history_items):
    out_dir = pathlib.Path("posts") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "story_history_table.md"
    md_path.write_text("# Chill Club Solo Story & Query History\n\n" + build_history_table_text(history_items) + "\n", encoding="utf-8")


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
    trimmed = items[-5000:]
    hist_path.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")
    write_history_table_md(slug, trimmed)


# ==============================================================================
# OPEN-ENDED SOLO GEMINI STORY GENERATOR
# ==============================================================================
def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def _fallback_solo_story(history_items):
    past_hooks = {h.get("top_hook", "") for h in history_items}
    candidates = [
        ("rainy apartment window sill at 4 PM", "POV: day off started and every responsibility suddenly feels optional"),
        ("dim bedroom desk at 2:47 AM", "POV: replaying a normal three-second sentence like it was a movie plot twist"),
        ("kitchen counter with iced coffee", "POV: checking the bank balance and negotiating with $14.82"),
        ("laptop glowing in a quiet room", "POV: closing 47 browser tabs one by one after the last meeting"),
    ]
    for env_name, hook in candidates:
        if hook not in past_hooks:
            break
    else:
        env_name = f"quiet_solo_corner_{int(time.time()) % 1000}"
        hook = "POV: solo chill mode activated with zero plans"

    return {
        "story_concept": f"12s solo story in {env_name}: {hook}",
        "query_used": f"open solo chill comedy about {hook} in {env_name}",
        "characters": ["Solo"],
        "top_hook": hook,
        "environment_name": env_name,
        "setting_continuity": (
            f"2D webcomic interior setting: {env_name}, cozy warm marker shading, "
            "crisp uniform black ink outlines, open top area for POV banner, strictly NO text"
        ),
        "music_prompt": "Chill laid-back lo-fi marimba, warm electric piano, and soft rain groove",
        "music_bpm": 98,
        "scenes": [
            {
                "marker": "SETUP",
                "duration_sec": 3.0,
                "bottom_caption": "Peaceful start. No rush.",
                "expression": "confident_smirk",
                "end_expression": "deadpan_camera_stare",
                "body_action": "slouch_sigh",
                "visual_prompt": f"Solo character in olive cap and dark charcoal hoodie at {env_name}, NO text",
                "camera_move": "dolly_push_in",
                "transition_in": "hard_cut",
                "sfx_cue": "pop_ding",
                "tint_rgb": [220, 198, 170],
            },
            {
                "marker": "SPIRAL",
                "duration_sec": 3.2,
                "bottom_caption": "One tiny thought starts doing laps.",
                "expression": "deadpan_camera_stare",
                "end_expression": "exhausted_half_lidded",
                "body_action": "phone_scroll_lean",
                "visual_prompt": f"Solo character leaning forward at {env_name} in quiet overthinking, NO text",
                "camera_move": "pan_follow_right",
                "transition_in": "blur_dissolve",
                "sfx_cue": "whoosh",
                "tint_rgb": [182, 200, 224],
            },
            {
                "marker": "PEAK",
                "duration_sec": 3.0,
                "bottom_caption": "Why did my brain zoom in 400%?",
                "expression": "sweat_grit",
                "end_expression": "bloodshot_shock",
                "body_action": "shock_recoil",
                "visual_prompt": f"Close reaction of solo character in olive cap and charcoal hoodie at {env_name}, NO text",
                "camera_move": "snap_zoom_face",
                "transition_in": "whip_pan_left",
                "sfx_cue": "record_scratch",
                "tint_rgb": [235, 145, 130],
            },
            {
                "marker": "CHILL PAYOFF",
                "duration_sec": 3.3,
                "bottom_caption": "Anyway. Back to doing nothing.",
                "expression": "deadpan_camera_stare",
                "end_expression": "confident_smirk",
                "body_action": "slouch_sigh",
                "visual_prompt": f"Wide calm solo payoff shot at {env_name}, NO text",
                "camera_move": "pull_back_reveal",
                "transition_in": "smash_zoom_cut",
                "sfx_cue": "vine_boom_sub",
                "tint_rgb": [162, 172, 188],
            },
        ],
        "ig_caption": f"{hook} #wearechillclub #chillreels #povcomedy",
        "pinned_comment": "Be honest—which beat is your daily routine?",
    }


def normalize_story(raw_data, history_items):
    if not isinstance(raw_data, dict):
        return _fallback_solo_story(history_items)

    scenes = raw_data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 4:
        return _fallback_solo_story(history_items)

    env_name = str(raw_data.get("environment_name") or "quiet solo room").strip()
    hook = str(raw_data.get("top_hook") or "").strip()
    if not hook:
        hook = "POV: solo chill mode with zero plans"

    fixed_scenes = []
    total = 0.0
    for idx, sc in enumerate(scenes[:5]):
        if not isinstance(sc, dict):
            continue
        dur = sc.get("duration_sec", 3.0)
        try:
            dur = float(dur)
        except Exception:
            dur = 3.0
        dur = max(VISUAL_TUNING["min_beat_sec"], min(VISUAL_TUNING["max_beat_sec"], dur))
        total += dur

        expr = sc.get("expression") if sc.get("expression") in FACIAL_EXPRESSIONS else "deadpan_camera_stare"
        end_expr = sc.get("end_expression") if sc.get("end_expression") in FACIAL_EXPRESSIONS else expr
        act = sc.get("body_action") if sc.get("body_action") in ALL_BODY_ACTIONS else "slouch_sigh"
        cap_words = str(sc.get("bottom_caption") or "").strip().split()
        cap = " ".join(cap_words[:10])

        tint = sc.get("tint_rgb")
        if not (isinstance(tint, list) and len(tint) == 3 and all(isinstance(v, (int, float)) for v in tint)):
            tint = list(DEFAULT_PALETTE["tint"])
        tint = [max(40, min(245, int(v))) for v in tint]

        fixed_scenes.append({
            "marker": str(sc.get("marker") or f"BEAT {idx + 1}").strip()[:18],
            "duration_sec": round(dur, 2),
            "bottom_caption": cap,
            "expression": expr,
            "end_expression": end_expr,
            "body_action": act,
            "visual_prompt": str(sc.get("visual_prompt") or f"Solo character in olive cap and charcoal hoodie at {env_name}, NO text").strip(),
            "camera_move": sc.get("camera_move") if sc.get("camera_move") in ["dolly_push_in", "pull_back_reveal", "snap_zoom_face", "locked_deadpan", "pan_follow_right", "gentle_float"] else "dolly_push_in",
            "transition_in": sc.get("transition_in") if sc.get("transition_in") in ["hard_cut", "smash_zoom_cut", "whip_pan_left", "whip_pan_right", "blur_dissolve"] else "hard_cut",
            "sfx_cue": sc.get("sfx_cue") if sc.get("sfx_cue") in ["pop_ding", "whoosh", "record_scratch", "vine_boom_sub", "riser_hit"] else "pop_ding",
            "tint_rgb": tint,
        })

    if len(fixed_scenes) < 4:
        return _fallback_solo_story(history_items)

    if total > 0:
        if total < VISUAL_TUNING["target_min_sec"]:
            factor = VISUAL_TUNING["target_min_sec"] / total
            for s in fixed_scenes:
                s["duration_sec"] = round(min(VISUAL_TUNING["max_beat_sec"], s["duration_sec"] * factor), 2)
        elif total > VISUAL_TUNING["target_max_sec"]:
            factor = VISUAL_TUNING["target_max_sec"] / total
            for s in fixed_scenes:
                s["duration_sec"] = round(max(VISUAL_TUNING["min_beat_sec"], s["duration_sec"] * factor), 2)

    return {
        "story_concept": str(raw_data.get("story_concept") or hook).strip(),
        "query_used": str(raw_data.get("query_used") or hook).strip(),
        "characters": ["Solo"],
        "top_hook": hook,
        "environment_name": env_name,
        "setting_continuity": str(raw_data.get("setting_continuity") or f"2D webcomic solo interior: {env_name}, NO text").strip(),
        "music_prompt": str(raw_data.get("music_prompt") or "Chill laid-back lo-fi marimba and soft groove").strip(),
        "music_bpm": int(raw_data.get("music_bpm") or 100),
        "scenes": fixed_scenes,
        "ig_caption": str(raw_data.get("ig_caption") or f"{hook} #wearechillclub").strip(),
        "pinned_comment": str(raw_data.get("pinned_comment") or "Can you relate to this solo moment?").strip(),
    }


def generate_story_with_gemini(page_cfg, history_items, world_context):
    history_table = build_history_table_text(history_items)

    prompt = (
        f"Act as a persistent chill comedy story writer and director for {page_cfg['handle']}.\n"
        f"CHANNEL FOCUS: {page_cfg['domain']}\n"
        f"ART STYLE: {page_cfg['art_style']}\n\n"
        "CAST RULE: Strictly ONE solo character (white-headed stickman wearing a muted-olive baseball cap "
        "and dark charcoal hoodie). NEVER include couples, partners, or multi-person romance.\n\n"
        "STORY & QUERY HISTORY TABLE (DO NOT REPEAT ANY HOOK, ENVIRONMENT, OR STORY IDEA ALREADY HERE):\n"
        f"{history_table}\n\n"
        "OPTIONAL WORLD / TRENDING CONTEXT (use only if a natural, chill solo angle sparks):\n"
        f"{world_context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Invent a brand-new, original CHILL solo comedy story lasting roughly 10 to 15 seconds across 4 beats.\n"
        "2. Imagine fresh settings and solo moments beyond repeating the same few examples while keeping the chill vibe.\n"
        "3. Write the story first with clear beats and 'duration_sec' summing to ~10.0-15.0 seconds.\n\n"
        "Return ONLY valid JSON with keys: story_concept, query_used, characters, top_hook, environment_name, "
        "setting_continuity, music_prompt, music_bpm, scenes (4 items with marker, duration_sec, bottom_caption, "
        "expression, end_expression, body_action, visual_prompt, camera_move, transition_in, sfx_cue, tint_rgb), "
        "ig_caption, pinned_comment."
    )

    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    last_err = "none"

    for model in models:
        url = "[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/)" + model + ":generateContent?key=" + GEMINI_API_KEY
        for attempt in range(1, 3):
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 1.0,
                    "maxOutputTokens": 2600,
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
                    story = normalize_story(parsed, history_items)
                    print(f"Invented fresh 10-15s solo story via {model}: {story['top_hook']}")
                    return story
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                last_err = f"{model} JSON parse error: {e}"
                time.sleep(1)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:240]
                last_err = f"{model} HTTP {e.code}: {body}"
                if e.code in (400, 404, 429, 503):
                    break
                time.sleep(2 * attempt)
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} network/timeout: {e}"
                time.sleep(2)

    print(f"Gemini fallback ({last_err}); using open solo fallback story.")
    return _fallback_solo_story(history_items)


# ==============================================================================
# STORY-DRIVEN 24FPS SOLO RENDERER
# ==============================================================================
def _try_generate_ai_scene_plate(story, page_cfg, out_bg_path):
    prompt = (
        f"{page_cfg['art_style']}. Solo interior setting: {story['setting_continuity']}. "
        f"Mood for '{story['story_concept']}'. Leave clean top space for POV banner. "
        "Keep center open for the solo character. Strictly NO characters drawn yet, NO text."
    )
    url = "[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=)" + GEMINI_API_KEY
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
                    print("Generated AI background plate for solo story environment")
                    return True
    except Exception as e:
        print(f"AI plate skipped ({e}); rendering crisp supersampled backdrop")
    return False


def _render_procedural_backdrop(out_bg_path):
    bw, bh = W * SS, H * SS
    img = Image.new("RGB", (bw, bh), (206, 196, 182))
    draw = ImageDraw.Draw(img)
    ink = SOLO_CHARACTER_BIBLE["ink_color"]
    draw.rectangle([90 * SS, 390 * SS, (W - 90) * SS, 1020 * SS], fill=(226, 218, 204), outline=ink, width=7 * SS)
    draw.rectangle([0, 1140 * SS, bw, bh], fill=(116, 104, 94), outline=ink)
    draw.line([(0, 1140 * SS), (bw, 1140 * SS)], fill=ink, width=8 * SS)
    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _ease_out_quart(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - pow(1.0 - p, 4)


def _ease_in_out_sine(p):
    p = max(0.0, min(1.0, p))
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _draw_solo_character(draw, cx, cy, scale, expr, body_action, t, local_p):
    ink = SOLO_CHARACTER_BIBLE["ink_color"]
    head_fill = SOLO_CHARACTER_BIBLE["head_fill"]
    head_shadow = SOLO_CHARACTER_BIBLE["head_shadow"]
    cap_c = SOLO_CHARACTER_BIBLE["cap_color"]
    hoodie_c = SOLO_CHARACTER_BIBLE["hoodie_color"]

    pop_p = min(1.0, local_p / 0.10)
    sx = 1.0 + math.sin(pop_p * math.pi) * 0.06
    sy = 1.0 - math.sin(pop_p * math.pi) * 0.05

    dx = int(math.sin(t * 1.8) * 5 * scale)
    dy = int(math.sin(t * 2.5) * 5 * scale)
    head_tilt = int(math.sin(t * 1.5) * 8 * scale)
    lean = 0

    if body_action == "phone_scroll_lean":
        lean = int(14 * scale)
        head_tilt += int(12 * scale)
    elif body_action == "shock_recoil":
        recoil = math.sin(min(1.0, local_p * 4.0) * math.pi * 0.5)
        dy -= int(22 * recoil * scale)
        lean = int(-14 * recoil * scale)
    elif body_action == "struggle_pull":
        tug = math.sin(t * 12.0)
        dx += int(tug * 12 * scale)
        lean = int(-12 * scale + tug * 8 * scale)
    elif body_action == "celebrate_groove":
        dy -= int(abs(math.sin(t * 7.0)) * 16 * scale)

    hx = int((cx + dx + head_tilt) * SS)
    hy = int((cy + dy) * SS)
    rx = int(106 * scale * sx * SS)
    ry = int(106 * scale * sy * SS)

    neck_x = int((cx + dx + lean * 0.6) * SS)
    neck_y = hy + ry - 4 * SS
    hip_x = int((cx + dx) * SS)
    hip_y = neck_y + int(170 * scale * SS)
    limb_w = max(5 * SS, int(8 * scale * SS))
    mitten_r = max(10 * SS, int(15 * scale * SS))

    # Legs & stick torso
    draw.line([(neck_x, neck_y), (hip_x, hip_y)], fill=ink, width=limb_w)
    for side in (-1, 1):
        kx = hip_x + side * int(50 * scale * SS)
        ky = hip_y + int(68 * scale * SS)
        fx = hip_x + side * int(52 * scale * SS)
        fy = hip_y + int(148 * scale * SS)
        draw.line([(hip_x, hip_y), (kx, ky), (fx, fy)], fill=ink, width=limb_w)

    # Dark charcoal hoodie torso & hood collar
    sh_x = neck_x + int(lean * 0.2 * SS)
    sh_y = neck_y + int(28 * scale * SS)
    draw.rounded_rectangle(
        [sh_x - int(66 * scale * SS), neck_y - int(6 * scale * SS), sh_x + int(66 * scale * SS), hip_y + int(24 * scale * SS)],
        radius=int(26 * scale * SS),
        fill=hoodie_c,
        outline=ink,
        width=max(5 * SS, int(7 * scale * SS)),
    )

    l_elb = (sh_x - int(74 * scale * SS), sh_y + int(44 * scale * SS))
    l_hand = (hx - int(32 * scale * SS), hy + int(80 * scale * SS))
    r_elb = (sh_x + int(72 * scale * SS), sh_y + int(46 * scale * SS))
    r_hand = (sh_x + int(76 * scale * SS), sh_y + int(84 * scale * SS))
    draw.line([(sh_x - int(58 * scale * SS), sh_y), l_elb, l_hand], fill=ink, width=limb_w)
    draw.line([(sh_x + int(58 * scale * SS), sh_y), r_elb, r_hand], fill=ink, width=limb_w)
    for mhx, mhy in (l_hand, r_hand):
        draw.ellipse([mhx - mitten_r, mhy - mitten_r, mhx + mitten_r, mhy + mitten_r], fill=ink)

    # White head with warm marker shading
    draw.ellipse([hx - rx, hy - ry, hx + rx, hy + ry], fill=head_fill)
    draw.pieslice([hx - rx + 6 * SS, hy - ry + 6 * SS, hx + rx - 2 * SS, hy + ry - 2 * SS], start=-55, end=65, fill=head_shadow)
    draw.ellipse([hx - rx, hy - ry, hx + rx, hy + ry], outline=ink, width=max(6 * SS, int(9 * scale * SS)))

    # Muted-olive baseball cap
    draw.pieslice([hx - rx - 2 * SS, hy - ry - 12 * SS, hx + rx + 2 * SS, hy - int(ry * 0.12)], start=180, end=360, fill=cap_c, outline=ink, width=max(6 * SS, int(8 * scale * SS)))
    draw.rounded_rectangle([hx - int(10 * scale * SS), hy - int(ry * 0.56), hx + int(rx * 1.32), hy - int(ry * 0.34)], radius=8 * SS, fill=cap_c, outline=ink, width=max(5 * SS, int(7 * scale * SS)))

    eye_dx = int(36 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(22 * scale * SS)
    blinking = (t % 2.8) < 0.11
    pupil_x = int(math.sin(t * 1.7) * 4 * scale * SS)

    if blinking and expr != "bloodshot_shock":
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


def render_scene_frame(bg_img, sc, beat_idx, t, local_p):
    frame_hi = bg_img.resize((W * SS, H * SS), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(frame_hi)

    expr = sc["expression"] if local_p < 0.45 else sc["end_expression"]
    body_action = sc["body_action"]
    scale = 1.26 if beat_idx == 2 else 1.04
    _draw_solo_character(draw, W // 2, 855, scale, expr, body_action, t, local_p)
    return frame_hi.resize((W, H), Image.Resampling.LANCZOS)


# ==============================================================================
# AUDIO (LYRIA REALTIME WITH SAFE FALLBACK + CUES)
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
        raise RuntimeError("Insufficient Lyria audio data")

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


def _synth_cue_sample(cue, dt):
    if cue == "whoosh":
        return math.sin(2 * math.pi * (180 + 520 * dt) * dt) * math.sin(min(1.0, dt / 0.25) * math.pi) * 0.28
    if cue == "record_scratch":
        return math.sin(2 * math.pi * (640.0 * math.exp(-dt * 5.0) + 90.0 * math.sin(dt * 90.0)) * dt) * math.exp(-dt * 6.0) * 0.40
    if cue == "vine_boom_sub":
        return math.sin(2 * math.pi * (72.0 * math.exp(-dt * 1.7)) * dt) * math.exp(-dt * 4.5) * 0.50
    if cue == "riser_hit":
        if dt < 0.30:
            return math.sin(2 * math.pi * (220 + 1200 * dt) * dt) * (dt / 0.30) * 0.28
        return math.sin(2 * math.pi * 64.0 * dt) * math.exp(-(dt - 0.30) * 7.5) * 0.45
    return math.sin(2 * math.pi * 987.77 * dt) * math.exp(-dt * 15.0) * 0.25


def build_audio(music_prompt, bpm, scenes, beat_starts, total_dur, final_wav):
    bed_wav = final_wav.parent / "bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, total_dur))
    except Exception as e:
        print(f"Lyria skipped ({e}); using soft chill synth bed.")
        sr = 48000
        chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
        bar_len = int(sr * 1.8)
        with wave.open(str(bed_wav), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            buf = bytearray()
            for i in range(int(sr * total_dur)):
                t = i / sr
                chord = chords[(i // bar_len) % len(chords)]
                val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.08
                s = int(max(-0.9, min(0.9, val)) * 32767)
                buf.extend(struct.pack("<hh", s, s))
            wf.writeframes(buf)

    sfx_wav = final_wav.parent / "sfx.wav"
    sr = 48000
    cues = [(beat_starts[i], scenes[i].get("sfx_cue", "pop_ding")) for i in range(len(scenes))]
    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(int(sr * total_dur)):
            t = i / sr
            sig = sum(_synth_cue_sample(c, t - st) for st, c in cues if st <= t <= st + 0.55)
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            buf.extend(struct.pack("<hh", s, s))
        wf.writeframes(buf)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex",
        "[1:a]asplit=2[sfx_sc][sfx_mix];"
        "[0:a][sfx_sc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=220[ducked];"
        "[ducked][sfx_mix]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav),
    ], check=True)


# ==============================================================================
# CAMERA, GRADE, POV BANNER / CAPTIONS & VIDEO ASSEMBLY
# ==============================================================================
def build_vignette_mask(strength=0.14):
    sw, sh = 270, 480
    vig = Image.new("L", (sw, sh), 0)
    px = vig.load()
    cx, cy = sw / 2.0, sh * 0.5
    max_d = math.hypot(cx, cy)
    for y in range(sh):
        for x in range(sw):
            d = math.hypot(x - cx, y - cy) / max_d
            px[x, y] = int(max(0.0, min(255.0, (d ** 2.4) * 255.0 * strength)))
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def apply_scene_grade(frame, sc, vignette_mask):
    tint = tuple(sc.get("tint_rgb", list(DEFAULT_PALETTE["tint"])))
    graded = Image.blend(frame, Image.new("RGB", (W, H), tint), VISUAL_TUNING["color_tint_strength"])
    graded = ImageEnhance.Contrast(graded).enhance(DEFAULT_PALETTE["contrast"])
    graded = ImageEnhance.Color(graded).enhance(DEFAULT_PALETTE["sat"])
    return Image.composite(Image.new("RGB", (W, H), (10, 12, 18)), graded, vignette_mask)


def apply_camera(base_img, move, local_p, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    breath = math.sin(t * 1.8) * 0.002
    if move == "pull_back_reveal":
        zoom = (1.0 + max_z) - (max_z * _ease_out_quart(local_p)) + breath
    elif move == "snap_zoom_face":
        zoom = (1.0 + max_z * 1.2) - (max_z * 0.18 * _ease_in_out_sine(local_p))
    elif move == "gentle_float":
        zoom = 1.03 + math.sin(_ease_in_out_sine(local_p) * math.pi) * 0.02
    else:
        zoom = 1.02 + (max_z * _ease_in_out_sine(local_p)) + breath

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
        scale = 1.12 - 0.12 * eased
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
        blur_r = math.sin(tr_p * math.pi) * 3.0
        if blur_r > 0.25:
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


def draw_overlays(frame, top_hook, sc, beat_idx, total_beats, scene_t, beat_dur, t, page_cfg):
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    acc = tuple(page_cfg.get("accent_color", DEFAULT_PALETTE["accent"]))
    panic = tuple(page_cfg.get("panic_color", DEFAULT_PALETTE["panic"]))
    use_panic = sc.get("expression") in ("sweat_grit", "bloodshot_shock")
    hi_col = panic if use_panic else acc

    if top_hook:
        ent = _ease_out_quart(min(1.0, t / 0.20))
        font = _load_font(38)
        wrapped = textwrap.fill(top_hook, width=32)
        lines = wrapped.split("\n")
        box_h = 34 + len(lines) * 48
        bx0, by0 = 84, 130 + int((1.0 - ent) * -12)
        alpha = int(248 * ent)
        odraw.rounded_rectangle([bx0, by0, W - 84, by0 + box_h], radius=24, fill=(255, 253, 248, alpha), outline=(18, 18, 22, alpha), width=5)
        odraw.multiline_text((W // 2, by0 + box_h // 2), wrapped, font=font, fill=(18, 18, 22, alpha), anchor="mm", align="center", spacing=8)

        marker = (sc.get("marker") or "").strip()
        if marker:
            m_font = _load_font(28)
            mb = odraw.textbbox((0, 0), marker, font=m_font)
            mw = (mb[2] - mb[0]) + 44
            cx0 = (W - mw) // 2
            cy0 = by0 + box_h + 14
            odraw.rounded_rectangle([cx0, cy0, cx0 + mw, cy0 + 44], radius=22, fill=(18, 20, 28, 238), outline=(hi_col[0], hi_col[1], hi_col[2], 240), width=3)
            odraw.text((W // 2, cy0 + 22), marker, font=m_font, fill=(hi_col[0], hi_col[1], hi_col[2], 255), anchor="mm")

    cap = (sc.get("bottom_caption") or "").strip()
    if cap:
        cap_in = _ease_out_quart(min(1.0, scene_t / 0.14))
        time_left = max(0.0, beat_dur - scene_t)
        cap_out = 1.0 if (beat_idx == total_beats - 1 or time_left > 0.10) else max(0.0, time_left / 0.10)
        cap_alpha = int(248 * cap_in * cap_out)
        c_font = _load_font(38)
        wrapped = textwrap.fill(cap, width=32)
        lines = wrapped.split("\n")
        box_h = 44 + len(lines) * 50
        x0, y0 = 96, 1385 + int((1.0 - cap_in) * 10)
        odraw.rounded_rectangle([x0, y0, W - 96, y0 + box_h], radius=24, fill=(20, 22, 28, min(246, cap_alpha)), outline=(hi_col[0], hi_col[1], hi_col[2], cap_alpha), width=3)
        odraw.multiline_text((W // 2, y0 + box_h // 2), wrapped, font=c_font, fill=(250, 250, 252, cap_alpha), anchor="mm", align="center", spacing=8)

    odraw.text((W // 2, 1625), page_cfg["handle"], font=_load_font(28), fill=(255, 255, 255, 235), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_story_reel(page_cfg, story, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = story["scenes"]
    total_beats = len(scenes)
    acc_col = tuple(page_cfg.get("accent_color", DEFAULT_PALETTE["accent"]))

    ai_bg = tmp_dir / "ai_bg.png"
    if _try_generate_ai_scene_plate(story, page_cfg, ai_bg):
        bg_img = Image.open(ai_bg).convert("RGB")
    else:
        proc_bg = tmp_dir / "proc_bg.png"
        _render_procedural_backdrop(proc_bg)
        bg_img = Image.open(proc_bg).convert("RGB")

    beat_durations = [s["duration_sec"] for s in scenes]
    beat_starts = []
    acc = 0.0
    for d in beat_durations:
        beat_starts.append(acc)
        acc += d
    total_dur = acc

    final_wav = tmp_dir / "final_audio.wav"
    build_audio(story["music_prompt"], story["music_bpm"], scenes, beat_starts, total_dur, final_wav)

    total_frames = int(total_dur * FPS)
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
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

        stage = render_scene_frame(bg_img, sc, s_idx, t, local_p)
        frame = apply_camera(stage, sc["camera_move"], local_p, t)
        frame = apply_scene_grade(frame, sc, vignette_mask)

        trans_dur = VISUAL_TUNING["transition_sec"]
        if s_idx > 0 and scene_t < trans_dur and prev_frame is not None:
            frame = apply_transition(prev_frame, frame, sc["transition_in"], scene_t / trans_dur)
        else:
            prev_frame = frame.copy()

        draw = ImageDraw.Draw(frame)
        bar_x = int(W * min(1.0, (f_idx + 1) / max(1, total_frames)))
        draw.rectangle([0, 0, W, 8], fill=(14, 16, 22))
        draw.rectangle([0, 0, bar_x, 8], fill=acc_col)

        frame = draw_overlays(frame, story["top_hook"], sc, s_idx, total_beats, scene_t, beat_dur, t, page_cfg)
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
    print(f"Rendered {total_dur:.1f}s solo story Reel -> {out_mp4}")


# ==============================================================================
# GITHUB PAGES ARCHIVE + INSTAGRAM REELS PUBLISHING
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
    for attempt in range(1, 18):
        time.sleep(5)
        try:
            req = urllib.request.Request(pages_url, headers={"User-Agent": "facebookexternalhit/1.1"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and ("video/" in ctype or "octet-stream" in ctype):
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages ({attempt}/18): {e}")
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
    if not token or not ig_id or not video_url:
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
    for attempt in range(1, 24):
        time.sleep(5)
        status_url = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{creation_id}?fields=status_code,status&access_token={token}"
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel status ({attempt}/24): {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram Reel failed: {status_data}")
    published = post_request(f"{base}/media_publish", {"creation_id": creation_id, "access_token": token})
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {published['id']}")


if __name__ == "__main__":
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    world_context = fetch_world_context()
    publish_enabled = os.environ.get("PUBLISH_TO_IG", "").strip().lower() in ("1", "true", "yes")

    for page in load_active_pages():
        slug = page["slug"]
        history_items = load_story_history(slug, limit=80)

        story = generate_story_with_gemini(page, history_items, world_context)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"
        out_dir.joinpath(f"story_{stamp}.json").write_text(json.dumps(story, indent=2), encoding="utf-8")

        save_story_record(slug, {
            "timestamp": stamp,
            "characters": story["characters"],
            "environment_name": story["environment_name"],
            "top_hook": story["top_hook"],
            "story_concept": story["story_concept"],
            "query_used": story["query_used"],
            "duration_sec": round(sum(s["duration_sec"] for s in story["scenes"]), 2),
        })

        render_story_reel(page, story, rel_mp4)

        if publish_enabled:
            token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
            ig_id = (page.get("ig_user_id") or os.environ.get("IG_USER_ID", "")).strip()
            if token and ig_id:
                public_url = archive_and_get_pages_url(rel_mp4)
                publish_to_instagram(ig_id, token, public_url, story["ig_caption"])
            else:
                print("PUBLISH_TO_IG enabled, but IG_USER_ID or token is missing; skipped posting.")
