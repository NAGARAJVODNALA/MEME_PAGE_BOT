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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageChops

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920

# ==============================================================================
# CREATIVE DIRECTION & VISUAL TUNING CONTROLS
# ==============================================================================
VISUAL_TUNING = {
    "vignette_strength": 0.26,      # 0.0 to 0.50: subtle cinematic edge darkening
    "color_tint_strength": 0.14,    # 0.0 to 0.30: atmospheric mood color wash
    "particle_opacity": 0.35,       # 0.0 to 0.70: subtle rain/dust/spark layer
    "max_zoom_delta": 0.11,         # Keeps character framing safe from over-cropping
    "transition_sec": 0.22          # Duration of cross-scene flash/dip transitions
}

MOOD_PALETTES = {
    "cozy_amber": {
        "tint": (255, 196, 130),
        "glow": (255, 214, 153),
        "hud_bg": (46, 34, 26),
        "hud_fg": (255, 215, 130),
        "accent": (255, 200, 110),
        "particles": "dust",
        "prompt_light": "warm amber lamp glow, soft peach and cream shadows, cozy safe indoor atmosphere"
    },
    "night_overthink": {
        "tint": (95, 115, 210),
        "glow": (125, 175, 255),
        "hud_bg": (22, 26, 48),
        "hud_fg": (150, 215, 255),
        "accent": (140, 195, 255),
        "particles": "dust",
        "prompt_light": "deep midnight blue room, soft violet shadows, subtle cool cyan phone or window glow"
    },
    "work_stress": {
        "tint": (125, 148, 175),
        "glow": (175, 210, 240),
        "hud_bg": (28, 35, 46),
        "hud_fg": (190, 220, 250),
        "accent": (165, 205, 245),
        "particles": "none",
        "prompt_light": "muted slate blue-gray interior, cool pale laptop monitor glow on face, tired deadpan lighting"
    },
    "money_anxiety": {
        "tint": (110, 165, 135),
        "glow": (245, 195, 95),
        "hud_bg": (24, 42, 34),
        "hud_fg": (255, 205, 95),
        "accent": (130, 225, 165),
        "particles": "none",
        "prompt_light": "restrained muted sage-green ambient shadow with stark pale screen light"
    },
    "panic_crimson": {
        "tint": (235, 78, 88),
        "glow": (255, 125, 95),
        "hud_bg": (155, 28, 38),
        "hud_fg": (255, 255, 255),
        "accent": (255, 90, 95),
        "particles": "sparks",
        "prompt_light": "dramatic coral-red and warm orange rim lighting, high-contrast comedic shock expression"
    },
    "rain_relief": {
        "tint": (115, 165, 215),
        "glow": (255, 205, 145),
        "hud_bg": (24, 38, 54),
        "hud_fg": (255, 222, 155),
        "accent": (145, 205, 255),
        "particles": "rain",
        "prompt_light": "cool rainy blue window outside contrasting with warm golden indoor lamp comfort"
    }
}

# Combinatorial Matrix for 72,000+ unique non-repeating solo scenarios
SOLO_PILLARS = [
    "Anti-Social Cancel & Delay Loop (saying 'sounds good!' weeks ago and praying they cancel today)",
    "Micro-Finance & Bank Balance Reality Check (staring at pending charges after one iced coffee or delivery order)",
    "3 AM Brain & Sleep Sabotage (replaying a 4-second awkward moment from 2017 or calculating remaining sleep minutes)",
    "Remote Work & Tab-Closing Theater (jiggling mouse to stay green on Slack/Teams or closing 47 tabs at 4:59 PM)",
    "Day-Off & Rain Euphoria (waking up in panic before realizing it's Saturday and heavy rain is hitting the window)",
    "Sibling & Family Random Calls (sibling calling with zero purpose just to breathe on speakerphone)",
    "Errands, Grocery & Car Micro-Panics (check-engine light turning on or walking out of Target with $94 of random items)",
    "Decision Paralysis & Over-Preparation (rehearsing a 3-word drive-thru order 12 times in your head)"
]

SOLO_SETTINGS = [
    "cozy dark apartment bedroom with warm bedside lamp glow and rain streaking down the window",
    "modern living-room couch at night illuminated only by a soft TV glow",
    "minimalist home desk at 2:47 AM with a bright glowing laptop screen",
    "driver's seat of a parked car outside a grocery store at dusk",
    "dimly lit kitchen counter at midnight standing in front of an open refrigerator",
    "bathroom mirror at 7:05 AM under soft warm vanity lights",
    "quiet neighborhood laundromat at night with spinning dryers",
    "standing by the front apartment door holding keys and a backpack",
    "sitting on the edge of the bed staring at a glowing smartphone screen",
    "cozy armchair wrapped in a blanket with a steaming mug during a thunderstorm"
]

HUD_GAUGES = [
    "Social Battery", "Bank Balance", "Brain RAM", "Willpower",
    "Sleep Left", "Stress Level", "Patience", "Focus",
    "Caffeine Level", "Awkwardness", "Phone Battery", "Open Tabs"
]

SPECIFIC_ANCHORS = [
    "2:47 AM", "$14.82", "47 Chrome tabs", "4 hrs 11 mins", "98%",
    "3 missed calls", "$6.40 delivery fee", "4:58 PM", "1% battery",
    "$94.18 receipt", "2017 memory", "14 unread texts", "7:02 AM",
    "$38.50 burrito", "0 alarms set"
]

COMEDIC_ARCS = [
    "False Alarm Relief (starts in sheer panic, ends in pure horizontal blanket bliss)",
    "Slow-Motion Regret (starts confident and relaxed, slowly realizes a massive mistake)",
    "Instant Panic Spike (calm routine shattered by one tiny notification or sound)",
    "Deadpan Acceptance (chaotic problem arrives, character calmly stares into the void)",
    "Unhinged Over-Preparation (spending 40 minutes preparing for a 10-second interaction)"
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
        "layout_mode": "v5_solo_pov",
        "ig_user_id": os.environ.get("IG_USER_ID", "17841476835986162").strip(),
        "fb_page_id": "",
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "panic_color": [255, 75, 85],
        "domain": "Strictly SOLO millennial/Gen-Z internal chaos, day-off rain euphoria, sibling random calls, $14.82 bank checks, remote-work tab closing, and 2:47 AM overthinking",
        "art_style": "Clean vector-neat 2D webcomic illustration starring ONE solo white-headed minimalist character wearing a muted-olive baseball cap and dark charcoal hoodie, crisp uniform black ink outlines, cozy warm marker shading, atmospheric solo interior background, leave clean top space for a POV banner, strictly NO text or speech bubbles inside the drawing"
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
            "Sunday Scaries hitting at 6:14 PM",
            "Canceling weekend plans to stay home in the rain",
            "Checking pending bank transactions on Monday morning"
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


def sample_unique_combo(recent_history):
    used_combos = {h.get("combo_key", "") for h in recent_history}
    for _ in range(30):
        pillar = random.choice(SOLO_PILLARS)
        setting = random.choice(SOLO_SETTINGS)
        hud = random.choice(HUD_GAUGES)
        anchor = random.choice(SPECIFIC_ANCHORS)
        arc = random.choice(COMEDIC_ARCS)
        combo_key = f"{pillar[:22]}|{setting[:22]}|{hud}|{anchor}"
        if combo_key not in used_combos:
            return {
                "combo_key": combo_key,
                "pillar": pillar,
                "setting": setting,
                "hud": hud,
                "anchor": anchor,
                "arc": arc
            }
    return {
        "combo_key": f"fallback_{int(time.time())}",
        "pillar": random.choice(SOLO_PILLARS),
        "setting": random.choice(SOLO_SETTINGS),
        "hud": random.choice(HUD_GAUGES),
        "anchor": random.choice(SPECIFIC_ANCHORS),
        "arc": random.choice(COMEDIC_ARCS)
    }


def ask_gemini_script(prompt):
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview"]
    last_err = "Unknown error"

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json"
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(req_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(raw_text, strict=False)
                    if isinstance(parsed, dict) and isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 3:
                        print(f"Generated Page 1 V5 script with {model}")
                        return parsed
                    last_err = f"{model} returned incomplete JSON keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}"
                    print(last_err)
            except json.JSONDecodeError as e:
                last_err = f"{model} JSONDecodeError: {e}"
                print(last_err)
                time.sleep(1)
                continue
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:350]
                last_err = f"{model} HTTP {e.code}: {body}"
                print(last_err)
                if e.code in (400, 404):
                    break
                if e.code in (429, 500, 503):
                    time.sleep(3 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
                last_err = f"{model} Network/Timeout: {e}"
                print(last_err)
                time.sleep(2)
                continue
    raise RuntimeError(f"All Gemini models failed to produce valid JSON. Last error: {last_err}")


def generate_scene_illustration(visual_prompt, art_style, scene_mood, out_png_path):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["cozy_amber"])
    lighting_note = palette["prompt_light"]
    full_prompt = (
        f"{art_style}. Setting & Action: {visual_prompt}. Lighting & Mood: {lighting_note}. "
        "Character must strictly keep a minimalist white round head, muted-olive baseball cap, dark charcoal hoodie, "
        "and crisp black outlines. Vertical 9:16 portrait composition, keep the character centered in the middle-lower frame "
        "with clean unobstructed space in the top 25% for a POV banner, strictly NO text, NO letters, NO speech bubbles."
    )

    image_models = ["gemini-3.1-flash-image-preview", "gemini-3.8-flash-image"]
    for img_model in image_models:
        try:
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){img_model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "imageConfig": {"aspectRatio": "9:16"}
                }
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                res = json.loads(resp.read().decode())
                for part in res["candidates"][0]["content"]["parts"]:
                    if "inlineData" in part:
                        b64 = part["inlineData"]["data"]
                        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
                        img.save(out_png_path, format="PNG")
                        print(f"Generated V5 artwork via {img_model} ({scene_mood})")
                        return
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    # Neat vector-style fallback preserving exact character identity & mood palette
    is_panic = scene_mood == "panic_crimson"
    bg_map = {
        "cozy_amber": (46, 36, 30),
        "night_overthink": (20, 26, 48),
        "work_stress": (34, 42, 54),
        "money_anxiety": (26, 42, 35),
        "panic_crimson": (64, 20, 28),
        "rain_relief": (24, 38, 56)
    }
    bg = bg_map.get(scene_mood, (24, 30, 48))
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)
    for r in range(620, 120, -90):
        tint = tuple(min(255, c + 12) for c in bg)
        draw.ellipse([W // 2 - r, H // 2 - r + 120, W // 2 + r, H // 2 + r + 120], outline=tint, width=4)
    draw.rounded_rectangle([W // 2 - 95, 1020, W // 2 + 95, 1340], radius=45, fill=(45, 50, 62), outline=(12, 12, 16), width=10)
    draw.ellipse([W // 2 - 115, 790, W // 2 + 115, 1020], fill=(252, 252, 255), outline=(12, 12, 16), width=12)
    draw.pieslice([W // 2 - 118, 765, W // 2 + 118, 910], start=180, end=360, fill=(92, 112, 78), outline=(12, 12, 16), width=10)
    draw.rounded_rectangle([W // 2 - 10, 830, W // 2 + 155, 855], radius=10, fill=(92, 112, 78), outline=(12, 12, 16), width=8)
    eye_r = 16 if is_panic else 11
    draw.ellipse([W // 2 - 48 - eye_r, 905 - eye_r, W // 2 - 48 + eye_r, 905 + eye_r], fill=(12, 12, 16))
    draw.ellipse([W // 2 + 32 - eye_r, 905 - eye_r, W // 2 + 32 + eye_r, 905 + eye_r], fill=(12, 12, 16))
    img.save(out_png_path, format="PNG")


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
        "-af", f"volume=0.88,afade=t=in:st=0:d=0.3,afade=t=out:st={max(0.5, duration_sec - 0.8):.3f}:d=0.8",
        str(out_wav)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated Lyria score ({bpm} BPM)")


def build_v5_audio_with_sfx(music_prompt, bpm, sfx_style, duration_sec, final_wav):
    bed_wav = final_wav.parent / "lyria_bed.wav"
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, bed_wav, duration_sec))
    except Exception as e:
        print(f"Lyria skipped ({e}), generating cozy synth bed...")
        sr = 48000
        total_samples = int(sr * duration_sec)
        chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
        bar_len = int(sr * 2.25)
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

    sfx_wav = final_wav.parent / "micro_sfx.wav"
    sr = 48000
    total_samples = int(sr * duration_sec)
    with wave.open(str(sfx_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sr
            sig = 0.0
            if 3.0 <= t <= 3.22:
                dt = t - 3.0
                env = math.exp(-dt * 18.0)
                sig += math.sin(2 * math.pi * 880.0 * dt) * env * 0.28
            if 6.0 <= t <= 6.55:
                dt = t - 6.0
                env = math.exp(-dt * 7.5)
                if sfx_style == "heartbeat_drop":
                    freq = 68.0 - 20.0 * dt
                elif sfx_style == "alert_ding":
                    freq = 1046.5
                else:
                    freq = 420.0 * math.exp(-dt * 4.5)
                sig += math.sin(2 * math.pi * freq * dt) * env * 0.42
            s = int(max(-0.95, min(0.95, sig)) * 32767)
            frames.extend(struct.pack("<hh", s, s))
        wf.writeframes(frames)

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=1[out]",
        "-map", "[out]", "-ar", "48000", "-ac", "2", str(final_wav)
    ], check=True)


# ==============================================================================
# CINEMATIC GRADING, EASING & PARTICLE ATMOSPHERE ENGINE
# ==============================================================================
def _ease_out_cubic(p):
    return 1.0 - pow(1.0 - max(0.0, min(1.0, p)), 3)


def _ease_in_out_sine(p):
    return -(math.cos(math.pi * max(0.0, min(1.0, p))) - 1.0) / 2.0


def build_vignette_mask(strength=0.26):
    # Precompute smooth radial vignette once per reel for fast compositing
    small_w, small_h = 270, 480
    vig = Image.new("L", (small_w, small_h), 0)
    px = vig.load()
    cx, cy = small_w / 2.0, small_h * 0.52
    max_d = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_d
            val = int(max(0.0, min(255.0, (d ** 2.2) * 255.0 * strength)))
            px[x, y] = val
    return vig.resize((W, H), Image.Resampling.BILINEAR)


def generate_particle_seeds(count=28):
    rng = random.Random(42)
    return [
        {
            "x": rng.uniform(0.04, 0.96),
            "y": rng.uniform(0.05, 0.95),
            "speed": rng.uniform(0.6, 1.4),
            "size": rng.randint(2, 5),
            "phase": rng.uniform(0, math.pi * 2)
        }
        for _ in range(count)
    ]


def apply_atmosphere_grade(frame, scene_mood, t, local_p, vignette_mask, particle_seeds):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["cozy_amber"])

    # 1. Subtle mood color wash + gentle contrast polish
    tint_strength = VISUAL_TUNING["color_tint_strength"]
    if scene_mood == "panic_crimson":
        # Subtle pulse on panic rim tint
        tint_strength += 0.04 * math.sin(t * 14.0)
    tint_layer = Image.new("RGB", (W, H), palette["tint"])
    graded = Image.blend(frame, tint_layer, max(0.0, min(0.28, tint_strength)))
    graded = ImageEnhance.Contrast(graded).enhance(1.05)

    # 2. Soft radial vignette for depth & mobile readability
    dark_layer = Image.new("RGB", (W, H), (10, 12, 18))
    graded = Image.composite(dark_layer, graded, vignette_mask)

    # 3. Purposeful subtle environmental particles (rain, dust motes, or panic sparks)
    p_type = palette.get("particles", "none")
    if p_type != "none" and VISUAL_TUNING["particle_opacity"] > 0:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        alpha = int(255 * VISUAL_TUNING["particle_opacity"])
        glow_col = palette["glow"]

        for p in particle_seeds:
            if p_type == "rain":
                px = int(((p["x"] - t * 0.08 * p["speed"]) % 1.0) * W)
                py = int(((p["y"] + t * 0.55 * p["speed"]) % 1.0) * H)
                odraw.line([(px, py), (px - 6, py + 26)], fill=(195, 225, 255, int(alpha * 0.75)), width=2)
            elif p_type == "dust":
                px = int(((p["x"] + math.sin(t * 1.4 + p["phase"]) * 0.025) % 1.0) * W)
                py = int(((p["y"] - t * 0.04 * p["speed"]) % 1.0) * H)
                r = p["size"]
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(glow_col[0], glow_col[1], glow_col[2], int(alpha * 0.55)))
            elif p_type == "sparks":
                px = int(((p["x"] + math.sin(t * 6.0 + p["phase"]) * 0.04) % 1.0) * W)
                py = int(((p["y"] - t * 0.28 * p["speed"]) % 1.0) * H)
                r = p["size"] + 1
                odraw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 145, 95, int(alpha * 0.75)))

        graded = Image.alpha_composite(graded.convert("RGBA"), overlay).convert("RGB")

    return graded


def compute_camera_box(motion, local_p, t):
    max_z = VISUAL_TUNING["max_zoom_delta"]
    idle_breath = math.sin(t * 2.4) * 0.004

    if motion == "zoom_out":
        eased = _ease_out_cubic(local_p)
        zoom = (1.0 + max_z) - (max_z * eased) + idle_breath
    elif motion == "punch_zoom":
        # Quick 0.25s anticipation-and-punch, then smooth settle
        if local_p < 0.14:
            zoom = 1.0 + (max_z * 1.15) * _ease_out_cubic(local_p / 0.14)
        else:
            zoom = (1.0 + max_z * 1.15) - (max_z * 0.25 * _ease_in_out_sine((local_p - 0.14) / 0.86))
    elif motion == "deadpan_freeze":
        # Deliberate comedic stillness with near-zero micro drift
        zoom = 1.02 + (idle_breath * 0.4)
    else:
        # Smooth eased zoom_in or pan_right
        eased = _ease_in_out_sine(local_p)
        zoom = 1.0 + (max_z * eased) + idle_breath

    zoom = max(1.0, zoom)
    crop_w = int(W / zoom)
    crop_h = int(H / zoom)
    max_dx = W - crop_w
    max_dy = H - crop_h

    if motion == "pan_right":
        eased_pan = _ease_in_out_sine(local_p)
        x0 = int(max_dx * eased_pan)
        y0 = max_dy // 2
    elif motion == "shake_impact":
        # Crisp decaying impact shake during the first 0.42s of the scene, then steady reaction hold
        local_sec = local_p * 3.0
        if local_sec <= 0.42:
            decay = math.exp(-local_sec * 7.5)
            shake_x = int(math.sin(local_sec * 52.0) * min(20, max_dx // 2) * decay)
            shake_y = int(math.cos(local_sec * 44.0) * min(20, max_dy // 2) * decay)
        else:
            shake_x, shake_y = 0, 0
        x0 = max(0, min(max_dx, (max_dx // 2) + shake_x))
        y0 = max(0, min(max_dy, (max_dy // 2) + shake_y))
    else:
        x0 = max_dx // 2
        y0 = max_dy // 2

    return (x0, y0, x0 + crop_w, y0 + crop_h)


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


def draw_v5_overlays(frame, top_pov, hud_badge, thought_pop, scene_mood, t, local_p, handle):
    palette = MOOD_PALETTES.get(scene_mood, MOOD_PALETTES["cozy_amber"])
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 1. Top POV Card with smooth 0.35s entrance slide & accent bar
    if top_pov:
        ent = _ease_out_cubic(min(1.0, t / 0.35))
        slide_offset = int((1.0 - ent) * -28)
        card_alpha = int(255 * ent)
        pov_font = _load_font(42)
        wrapped = textwrap.fill(top_pov.strip(), width=30)
        lines = wrapped.split("\n")
        box_h = 46 + len(lines) * 52
        x0, y0 = 70, 185 + slide_offset
        x1, y1 = W - 70, y0 + box_h

        # Soft layered shadow + crisp card
        odraw.rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 10], radius=24, fill=(10, 12, 18, int(card_alpha * 0.55)))
        odraw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(252, 252, 254, card_alpha), outline=(22, 24, 30, card_alpha), width=3)
        # Subtle mood accent bar on left edge of POV card
        acc = palette["accent"]
        odraw.rounded_rectangle([x0 + 10, y0 + 18, x0 + 20, y1 - 18], radius=5, fill=(acc[0], acc[1], acc[2], card_alpha))
        odraw.multiline_text((W // 2 + 6, (y0 + y1) // 2), wrapped, font=pov_font, fill=(18, 20, 26, card_alpha), anchor="mm", align="center", spacing=10)

    # 2. Mood-Adaptive HUD Pill with subtle entrance pop
    if hud_badge:
        pop_p = min(1.0, local_p / 0.14)
        hud_scale = 1.0 + 0.08 * math.sin(pop_p * math.pi)
        hud_font = _load_font(int(43 * hud_scale))
        badge_text = hud_badge.strip()
        bbox = odraw.textbbox((0, 0), badge_text, font=hud_font)
        tw = (bbox[2] - bbox[0]) + 58
        th = 74
        bx0 = (W - tw) // 2
        by0 = 445
        h_bg = palette["hud_bg"]
        h_fg = palette["hud_fg"]
        odraw.rounded_rectangle([bx0 + 4, by0 + 6, bx0 + tw + 4, by0 + th + 6], radius=37, fill=(8, 10, 14, 130))
        odraw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + th], radius=37, fill=(h_bg[0], h_bg[1], h_bg[2], 242), outline=(h_fg[0], h_fg[1], h_fg[2], 210), width=3)
        odraw.text((W // 2, by0 + th // 2), badge_text, font=hud_font, fill=(h_fg[0], h_fg[1], h_fg[2], 255), anchor="mm")

    # 3. Punchline Thought-Pop with elastic scale-in bounce (holds cleanly, never blocks face)
    if thought_pop and local_p <= 0.76:
        bounce_p = min(1.0, local_p / 0.12)
        pop_scale = 1.24 - (0.24 * _ease_out_cubic(bounce_p))
        pop_alpha = int(255 * min(1.0, local_p / 0.06))
        pop_font = _load_font(int(74 * pop_scale))
        pop_col = palette["accent"] if scene_mood != "panic_crimson" else (255, 95, 100)
        odraw.text(
            (W // 2, 640),
            thought_pop.strip().upper(),
            font=pop_font,
            fill=(pop_col[0], pop_col[1], pop_col[2], pop_alpha),
            anchor="mm",
            stroke_width=9,
            stroke_fill=(12, 12, 16, pop_alpha)
        )

    # 4. Clean Handle Watermark above Reels bottom UI
    handle_font = _load_font(30)
    odraw.text((W // 2, 1625), handle, font=handle_font, fill=(255, 255, 255, 225), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 210))

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def render_page1_v5_reel(page_cfg, script_data, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:3]
    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        mood = sc.get("scene_mood") or ("panic_crimson" if sc.get("is_panic_scene") else "cozy_amber")
        if mood not in MOOD_PALETTES:
            mood = "panic_crimson" if sc.get("is_panic_scene") else "cozy_amber"
        sc["scene_mood"] = mood

        generate_scene_illustration(
            sc["visual_prompt"],
            page_cfg["art_style"],
            mood,
            art_path
        )
        scene_imgs.append(Image.open(art_path).convert("RGB"))

    sec_per_scene = 3.0
    total_dur = len(scenes) * sec_per_scene
    final_wav = tmp_dir / "final_v5.wav"
    build_v5_audio_with_sfx(
        script_data.get("music_prompt", "cozy lo-fi marimba rain beat dropping into comedic bass sting instrumental"),
        script_data.get("music_bpm", 106),
        script_data.get("sfx_style", "heartbeat_drop"),
        total_dur,
        final_wav
    )

    total_frames = int(total_dur * FPS)
    top_pov = script_data.get("top_pov_banner", "")
    vignette_mask = build_vignette_mask(VISUAL_TUNING["vignette_strength"])
    particle_seeds = generate_particle_seeds(26)

    for f_idx in range(total_frames):
        t = f_idx / FPS
        s_idx = min(len(scenes) - 1, int(t // sec_per_scene))
        sc = scenes[s_idx]
        scene_t = t - (s_idx * sec_per_scene)
        local_p = scene_t / sec_per_scene
        base_img = scene_imgs[s_idx]
        motion = sc.get("camera_motion", "zoom_in")
        mood = sc["scene_mood"]

        # 1. Directed Camera Motion with Easing & Safe Framing
        crop_box = compute_camera_box(motion, local_p, t)
        frame = base_img.crop(crop_box).resize((W, H), Image.Resampling.BILINEAR)

        # 2. Atmospheric Color Grading, Vignette & Subtle Environmental Particles
        frame = apply_atmosphere_grade(frame, mood, t, local_p, vignette_mask, particle_seeds)

        # 3. Tasteful Scene Transition Beat at Scene 2 & Scene 3 cuts
        trans_dur = VISUAL_TUNING["transition_sec"]
        if s_idx > 0 and scene_t < trans_dur:
            tr_p = scene_t / trans_dur
            if mood == "panic_crimson":
                # Quick warm flash cut into panic
                flash_alpha = (1.0 - tr_p) * 0.35
                flash_img = Image.new("RGB", (W, H), (255, 225, 220))
                frame = Image.blend(frame, flash_img, flash_alpha)
            else:
                # Smooth cross-blend from previous scene
                prev_img = scene_imgs[s_idx - 1]
                frame = Image.blend(prev_img, frame, _ease_out_cubic(tr_p))

        # 4. Top Animated Progress Bar
        draw = ImageDraw.Draw(frame)
        prog = min(1.0, (f_idx + 1) / max(1, total_frames))
        bar_col = MOOD_PALETTES[mood]["accent"]
        draw.rectangle([0, 0, W, 8], fill=(15, 18, 24))
        draw.rectangle([0, 0, int(W * prog), 8], fill=bar_col)

        # 5. Polished Mobile-Safe Overlays
        frame = draw_v5_overlays(
            frame=frame,
            top_pov=top_pov,
            hud_badge=sc.get("hud_badge", ""),
            thought_pop=sc.get("thought_pop", ""),
            scene_mood=mood,
            t=t,
            local_p=local_p,
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
    print(f"Rendered Page 1 V5 Studio Reel: {out_mp4}")


def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish V5 Reel {rel_path}"], check=True)
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
        time_slot_vibe = "MORNING SLOT (9 AM): Morning alarms, waking up late, or starting the workday."
    elif 12 <= hour < 18:
        time_slot_vibe = "AFTERNOON SLOT (2 PM): Midday bank balance checks, remote work tab closing, or errands."
    else:
        time_slot_vibe = "NIGHT SLOT (9 PM+): Late-night rain vibes, 2:47 AM overthinking, or canceling evening plans."

    trends = fetch_live_trends()
    active_pages = load_active_pages()

    for page in active_pages:
        slug = page["slug"]
        recent_history = load_history(slug, limit=25)
        recent_hooks = "\n".join(f"- {h.get('top_pov_banner', '')}" for h in recent_history if h.get("top_pov_banner")) or "None yet"
        combo = sample_unique_combo(recent_history)

        prompt = (
            f"You are the viral creative director for {page['handle']}.\n"
            f"CHANNEL DOMAIN: {page['domain']}\n"
            f"VISUAL STYLE: {page['art_style']}\n\n"
            "### MANDATORY COMBINATORIAL SEED (USE THIS EXACT SEED FOR ORIGINALITY)\n"
            f"- Content Pillar: {combo['pillar']}\n"
            f"- Solo Setting: {combo['setting']}\n"
            f"- Escalating HUD Gauge Metric: {combo['hud']}\n"
            f"- Hyper-Specific Anchor: {combo['anchor']}\n"
            f"- Comedic Arc: {combo['arc']}\n"
            f"- Time Slot Context: {time_slot_vibe}\n"
            f"- Optional US Google Trends (only weave in if natural): \n{trends}\n"
            f"- Previously Used POV Hooks (NEVER REPEAT):\n{recent_hooks}\n\n"
            "### OUTPUT REQUIREMENTS (RETURN ONLY VALID JSON WITH THESE EXACT KEYS)\n"
            "{\n"
            '  "top_pov_banner": "Punchy relatable solo POV hook (max 14 words, starts with POV: or When...). STRICTLY SOLO (no girlfriend, wife, or partner).",\n'
            '  "music_prompt": "Lyria RealTime instrumental prompt (max 16 words, ending with instrumental)",\n'
            '  "music_bpm": 106,\n'
            '  "sfx_style": "heartbeat_drop",\n'
            '  "scenes": [\n'
            '    {"hud_badge": "Social Battery: 85%", "thought_pop": "CHILL.", "visual_prompt": "Scene 1 calm solo character action in setting, NO text in drawing", "camera_motion": "zoom_in", "scene_mood": "cozy_amber", "is_panic_scene": false},\n'
            '    {"hud_badge": "Social Battery: 12%", "thought_pop": "WAIT.", "visual_prompt": "Scene 2 trigger hits solo character in setting, NO text in drawing", "camera_motion": "deadpan_freeze", "scene_mood": "night_overthink", "is_panic_scene": false},\n'
            '    {"hud_badge": "Social Battery: 0%", "thought_pop": "ABORT.", "visual_prompt": "Scene 3 unhinged panic or cozy relief reaction in setting, NO text in drawing", "camera_motion": "shake_impact", "scene_mood": "panic_crimson", "is_panic_scene": true}\n'
            "  ],\n"
            '  "ig_caption": "Short relatable caption + 4 niche hashtags",\n'
            '  "pinned_comment": "Engaging question to spark comment replies"\n'
            "}\n"
            "Allowed values for scene_mood: 'cozy_amber', 'night_overthink', 'work_stress', 'money_anxiety', 'panic_crimson', or 'rain_relief'.\n"
            "Allowed values for camera_motion: 'zoom_in', 'zoom_out', 'pan_right', 'punch_zoom', 'deadpan_freeze', or 'shake_impact'.\n"
            "Allowed values for sfx_style: 'heartbeat_drop', 'alert_ding', or 'record_scratch'.\n"
            "Direct each scene's mood and camera_motion deliberately to serve the joke (e.g., use 'deadpan_freeze' for awkward realization, 'rain_relief' + 'zoom_out' for cozy relief, 'punch_zoom' or 'shake_impact' + 'panic_crimson' for sudden panic)."
        )

        script_data = ask_gemini_script(prompt)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"

        render_page1_v5_reel(page, script_data, rel_mp4)
        pathlib.Path(f"posts/{slug}/reel_{stamp}.txt").write_text(
            f"{script_data['top_pov_banner']}\n\n{script_data['ig_caption']}\n\nPinned Comment: {script_data['pinned_comment']}",
            encoding="utf-8"
        )
        save_history(slug, {
            "timestamp": stamp,
            "combo_key": combo["combo_key"],
            "top_pov_banner": script_data["top_pov_banner"],
            "pinned_comment": script_data["pinned_comment"]
        })

        public_video_url = archive_and_get_pages_url(rel_mp4)
        token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()

        publish_to_instagram(page.get("ig_user_id", "").strip(), token, public_video_url, script_data["ig_caption"])
        publish_to_facebook_reels(page.get("fb_page_id", "").strip(), token, public_video_url, script_data["ig_caption"])
