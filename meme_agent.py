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
from PIL import Image, ImageDraw, ImageFont

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920

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
        "art_style": "Clean vector-neat 2D webcomic illustration starring ONE solo white-headed stickman character wearing a muted-olive baseball cap and dark charcoal hoodie, crisp uniform black ink outlines, cozy warm marker shading, atmospheric solo interior background, no text overlays"
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
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-2.0-flash"]
    scene_schema = {
        "type": "OBJECT",
        "properties": {
            "hud_badge": {"type": "STRING"},
            "thought_pop": {"type": "STRING"},
            "visual_prompt": {"type": "STRING"},
            "camera_motion": {"type": "STRING", "enum": ["zoom_in", "zoom_out", "pan_right", "shake_impact"]},
            "is_panic_scene": {"type": "BOOLEAN"}
        },
        "required": ["hud_badge", "thought_pop", "visual_prompt", "camera_motion", "is_panic_scene"]
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 2048,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "top_pov_banner": {"type": "STRING"},
                    "music_prompt": {"type": "STRING"},
                    "music_bpm": {"type": "INTEGER"},
                    "sfx_style": {"type": "STRING", "enum": ["heartbeat_drop", "alert_ding", "record_scratch"]},
                    "scenes": {"type": "ARRAY", "items": scene_schema},
                    "ig_caption": {"type": "STRING"},
                    "pinned_comment": {"type": "STRING"}
                },
                "required": ["top_pov_banner", "music_prompt", "music_bpm", "sfx_style", "scenes", "ig_caption", "pinned_comment"]
            }
        }
    }

    last_err = "Unknown error"
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req_payload = json.loads(json.dumps(payload))
            if model == "gemini-2.0-flash":
                req_payload["generationConfig"].pop("thinkingConfig", None)

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
                    print(f"Generated Page 1 V5 script with {model}")
                    return parsed
            except json.JSONDecodeError as e:
                last_err = f"{model} JSONDecodeError: {e}"
                print(last_err)
                time.sleep(1)
                continue
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
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


def generate_scene_illustration(visual_prompt, art_style, is_panic, out_png_path):
    lighting_note = (
        "dramatic crimson-red panic rim lighting and high-contrast wide-eyed shock expression"
        if is_panic else
        "cozy warm ambient lamp glow with moody midnight-blue shadows"
    )
    full_prompt = (
        f"{art_style}. Setting & Action: {visual_prompt}. Lighting: {lighting_note}. "
        "Vertical 9:16 portrait composition, keep the character centered in the middle-lower frame "
        "with clean unobstructed space in the top 25% for a POV banner, strictly NO text, NO letters, NO speech bubbles."
    )

    image_models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"]
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
                        print(f"Generated V5 artwork via {img_model}")
                        return
        except Exception as e:
            print(f"{img_model} skipped ({e})")

    # Neat vector-style fallback if image quota is temporarily reached
    bg = (64, 18, 26) if is_panic else (22, 28, 46)
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)
    for r in range(620, 120, -90):
        tint = tuple(min(255, c + 12) for c in bg)
        draw.ellipse([W // 2 - r, H // 2 - r + 120, W // 2 + r, H // 2 + r + 120], outline=tint, width=4)
    # Character torso (charcoal hoodie)
    draw.rounded_rectangle([W // 2 - 95, 1020, W // 2 + 95, 1340], radius=45, fill=(45, 50, 62), outline=(12, 12, 16), width=10)
    # Round white head + muted olive cap
    draw.ellipse([W // 2 - 115, 790, W // 2 + 115, 1020], fill=(252, 252, 255), outline=(12, 12, 16), width=12)
    draw.pieslice([W // 2 - 118, 765, W // 2 + 118, 910], start=180, end=360, fill=(92, 112, 78), outline=(12, 12, 16), width=10)
    draw.rounded_rectangle([W // 2 - 10, 830, W // 2 + 155, 855], radius=10, fill=(92, 112, 78), outline=(12, 12, 16), width=8)
    # Eyes
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

    # Synthesize crisp micro-SFX sting at t=3.0s (Scene 2) and t=6.0s (Scene 3 panic drop)
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


def draw_v5_overlays(draw, top_pov, hud_badge, thought_pop, is_panic, local_p, accent_rgb, panic_rgb, handle):
    # 1. Persistent Top POV Pill Banner (Safe Zone Y: 185px)
    if top_pov:
        pov_font = _load_font(42)
        wrapped = textwrap.fill(top_pov.strip(), width=31)
        lines = wrapped.split("\n")
        box_h = 44 + len(lines) * 52
        x0, y0 = 70, 185
        x1, y1 = W - 70, y0 + box_h
        draw.rounded_rectangle([x0 + 6, y0 + 8, x1 + 6, y1 + 8], radius=24, fill=(10, 10, 14))
        draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(255, 255, 255), outline=(18, 18, 22), width=4)
        draw.multiline_text((W // 2, (y0 + y1) // 2), wrapped, font=pov_font, fill=(15, 15, 20), anchor="mm", align="center", spacing=10)

    # 2. Floating Escalating HUD Gauge Pill (Y: 445px)
    if hud_badge:
        hud_font = _load_font(44)
        badge_text = hud_badge.strip()
        bbox = draw.textbbox((0, 0), badge_text, font=hud_font)
        tw = (bbox[2] - bbox[0]) + 56
        th = 74
        bx0 = (W - tw) // 2
        by0 = 445
        fill_col = tuple(panic_rgb) if is_panic else (22, 26, 36)
        txt_col = (255, 255, 255) if is_panic else tuple(accent_rgb)
        draw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + th], radius=37, fill=fill_col, outline=(255, 255, 255), width=3)
        draw.text((W // 2, by0 + th // 2), badge_text, font=hud_font, fill=txt_col, anchor="mm")

    # 3. Beat-Synced Inner-Thought Pop Word
    if thought_pop and local_p <= 0.72:
        pop_font = _load_font(76)
        pop_col = tuple(panic_rgb) if is_panic else tuple(accent_rgb)
        draw.text(
            (W // 2, 645),
            thought_pop.strip().upper(),
            font=pop_font,
            fill=pop_col,
            anchor="mm",
            stroke_width=9,
            stroke_fill=(12, 12, 16)
        )

    # 4. Subtle Handle Watermark above Reels bottom UI
    handle_font = _load_font(30)
    draw.text((W // 2, 1625), handle, font=handle_font, fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))


def render_page1_v5_reel(page_cfg, script_data, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    scenes = script_data["scenes"][:3]
    scene_imgs = []
    for idx, sc in enumerate(scenes):
        art_path = tmp_dir / f"art_{idx}.png"
        generate_scene_illustration(
            sc["visual_prompt"],
            page_cfg["art_style"],
            sc.get("is_panic_scene", idx == 2),
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
    accent_rgb = page_cfg.get("accent_color", [255, 225, 45])
    panic_rgb = page_cfg.get("panic_color", [255, 75, 85])
    top_pov = script_data.get("top_pov_banner", "")

    for f_idx in range(total_frames):
        t = f_idx / FPS
        s_idx = min(len(scenes) - 1, int(t // sec_per_scene))
        sc = scenes[s_idx]
        local_p = (t - (s_idx * sec_per_scene)) / sec_per_scene
        base_img = scene_imgs[s_idx]
        motion = sc.get("camera_motion", "zoom_in")

        if motion == "zoom_out":
            zoom = 1.13 - (0.13 * local_p)
        else:
            zoom = 1.0 + (0.13 * local_p)

        crop_w = int(W / zoom)
        crop_h = int(H / zoom)
        max_dx = W - crop_w
        max_dy = H - crop_h

        if motion == "pan_right":
            x0 = int(max_dx * local_p)
            y0 = max_dy // 2
        elif motion == "shake_impact":
            shake_x = int(math.sin(t * 44) * min(18, max_dx // 2))
            shake_y = int(math.cos(t * 38) * min(18, max_dy // 2))
            x0 = max(0, min(max_dx, (max_dx // 2) + shake_x))
            y0 = max(0, min(max_dy, (max_dy // 2) + shake_y))
        else:
            x0 = max_dx // 2
            y0 = max_dy // 2

        frame = base_img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(frame)

        prog = min(1.0, (f_idx + 1) / max(1, total_frames))
        bar_col = tuple(panic_rgb) if sc.get("is_panic_scene") else tuple(accent_rgb)
        draw.rectangle([0, 0, int(W * prog), 10], fill=bar_col)

        draw_v5_overlays(
            draw=draw,
            top_pov=top_pov,
            hud_badge=sc.get("hud_badge", ""),
            thought_pop=sc.get("thought_pop", ""),
            is_panic=sc.get("is_panic_scene", False),
            local_p=local_p,
            accent_rgb=accent_rgb,
            panic_rgb=panic_rgb,
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
            "### OUTPUT REQUIREMENTS (3-SCENE 9-SECOND SOLO REEL)\n"
            "1. 'top_pov_banner': Punchy relatable solo POV hook (max 14 words, starts with 'POV:' or 'When...'). STRICTLY SOLO (no girlfriend, wife, or partner).\n"
            "2. 'scenes' (EXACTLY 3 SCENES):\n"
            "   - Scene 1 (0-3s Setup): Calm solo setup. 'hud_badge' starts high/normal (e.g., 'Social Battery: 85%'), 'thought_pop' is '' or 1 word ('CHILL.'), 'is_panic_scene': false.\n"
            "   - Scene 2 (3-6s Reality Check): Trigger hits. 'hud_badge' drops/spikes (e.g., 'Social Battery: 12%'), 'thought_pop' is 1-2 punchy words ('WAIT.', 'HOLD ON.'), 'is_panic_scene': false.\n"
            "   - Scene 3 (6-9s Unhinged Reaction): Peak panic or relief. 'hud_badge' hits extreme (e.g., 'Social Battery: 0%'), 'thought_pop' is 1-2 punchy words ('ABORT.', 'BLISS.', 'WHY.'), 'camera_motion': 'shake_impact' or 'zoom_in', 'is_panic_scene': true for panic or false for cozy relief.\n"
            "   - 'visual_prompt' for each scene: Describe the solo stickman character (muted-olive cap, dark hoodie) in the setting with clear facial expression and posture. NO text inside the illustration.\n"
            "3. 'music_prompt': Lyria RealTime prompt (max 16 words, ending with 'instrumental').\n"
            "4. 'ig_caption': Short relatable caption + 4 niche hashtags.\n"
            "5. 'pinned_comment': Engaging question to spark comment replies.\n\n"
            "Return valid JSON matching the exact schema."
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
