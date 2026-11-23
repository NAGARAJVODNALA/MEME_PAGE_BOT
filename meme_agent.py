import os
import math
import json
import time
import wave
import struct
import random
import socket
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
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
PAGE_HANDLE = "@wearechillclub"
GRAPH_VERSION = "v21.0"
FPS = 24


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
            "Saying 'sounds good!' to plans you already know you're canceling",
            "Checking your bank account after one weekend out",
            "Your brain replaying an awkward moment from 2016 at 3 AM",
            "Boss scheduling a 'quick sync' at 4:55 PM on Friday",
            "Opening the fridge 4 times expecting new food to appear"
        ]
    return "\n".join(f"- {t}" for t in trends)


def ask_gemini(prompt):
    models = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]
    scene_schema = {
        "type": "OBJECT",
        "properties": {
            "setting": {"type": "STRING", "enum": ["day", "night_3am", "panic_red"]},
            "prop": {"type": "STRING", "enum": ["phone", "laptop", "bank_alert", "coffee", "bed", "none"]},
            "left_name": {"type": "STRING"},
            "left_pose": {"type": "STRING", "enum": ["blank_stare", "sweating", "smug", "panic", "table_flip"]},
            "left_line": {"type": "STRING"},
            "right_name": {"type": "STRING"},
            "right_pose": {"type": "STRING", "enum": ["blank_stare", "sweating", "smug", "panic", "table_flip"]},
            "right_line": {"type": "STRING"},
            "caption": {"type": "STRING"}
        },
        "required": ["setting", "prop", "left_name", "left_pose", "left_line", "right_name", "right_pose", "right_line", "caption"]
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "music_prompt": {"type": "STRING"},
                    "music_bpm": {"type": "INTEGER"},
                    "music_mood": {"type": "STRING", "enum": ["dramatic", "hype", "upbeat"]},
                    "hook": {"type": "STRING"},
                    "scenes": {"type": "ARRAY", "items": scene_schema},
                    "ig_caption": {"type": "STRING"}
                },
                "required": ["music_prompt", "music_bpm", "music_mood", "hook", "scenes", "ig_caption"]
            }
        }
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        for attempt in range(1, 3):
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(raw_text, strict=False)
                    print(f"Generated valid stickman script with {model}")
                    return parsed
            except json.JSONDecodeError as je:
                print(f"{model} returned malformed JSON on attempt {attempt}: {je}")
                time.sleep(1)
                continue
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                if e.code in (429, 500, 503):
                    time.sleep(3 * attempt)
                    continue
                raise
            except (TimeoutError, socket.timeout, urllib.error.URLError):
                time.sleep(2)
                continue
    raise RuntimeError("All Gemini models failed to produce valid JSON.")


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


async def _stream_lyria_wav(music_prompt, bpm, out_wav_path, duration_sec=9.0):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})
    target_bytes = int(48000 * 2 * 2 * (duration_sec + 1.5))
    pcm_buffer = bytearray()

    async with client.aio.live.music.connect(model="models/lyria-realtime-exp") as session:
        await session.set_weighted_prompts(
            prompts=[types.WeightedPrompt(text=music_prompt, weight=1.0)]
        )
        await session.set_music_generation_config(
            config=types.LiveMusicGenerationConfig(bpm=int(bpm), temperature=1.1)
        )
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
        raise RuntimeError(f"Lyria returned insufficient audio bytes: {len(pcm_buffer)}")

    raw_wav = pathlib.Path(str(out_wav_path) + ".raw.wav")
    with wave.open(str(raw_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(pcm_buffer)

    punch_time = round(duration_sec * 0.66, 2)
    af_filter = (
        f"volume='if(lt(t,{punch_time}),0.78,1.15)':eval=frame,"
        f"afade=t=in:st=0:d=0.25,afade=t=out:st={duration_sec - 0.8}:d=0.8"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav),
        "-t", str(duration_sec),
        "-af", af_filter,
        str(out_wav_path)
    ], check=True)
    raw_wav.unlink(missing_ok=True)
    print(f"Generated original Lyria AI music ({bpm} BPM): '{music_prompt}'")


def build_audio_track(out_audio_path, music_prompt, bpm=115, music_mood="upbeat", duration_sec=9.0):
    try:
        asyncio.run(_stream_lyria_wav(music_prompt, bpm, out_audio_path, duration_sec=duration_sec))
        return
    except Exception as e:
        print(f"Lyria AI music skipped ({e}), using backup audio track...")

    audio_dir = pathlib.Path("assets/audio")
    mp3s = list(audio_dir.glob("*.mp3")) if audio_dir.exists() else []
    if mp3s:
        mood_keywords = {
            "dramatic": ["action", "trailer", "cinematic", "epic", "dark"],
            "hype": ["phonk", "run", "energy", "gym", "fast"],
            "upbeat": ["synth", "pop", "promo", "inspiring", "chill", "lofi"],
        }
        keywords = mood_keywords.get(music_mood, [])
        matched = [p for p in mp3s if any(k in p.name.lower() for k in keywords)]
        chosen = random.choice(matched if matched else mp3s)
        print(f"Using backup music track ({music_mood}): {chosen}")
        punch_time = round(duration_sec * 0.66, 2)
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(chosen),
            "-t", str(duration_sec),
            "-af", f"volume='if(lt(t,{punch_time}),0.75,1.12)':eval=frame,afade=t=in:st=0:d=0.25,afade=t=out:st={duration_sec - 0.8}:d=0.8",
            str(out_audio_path)
        ], check=True)
        return

    sample_rate = 44100
    total_samples = int(sample_rate * duration_sec)
    chords = [
        [261.63, 311.13, 392.00, 466.16],
        [207.65, 261.63, 311.13, 392.00],
        [174.61, 207.65, 261.63, 311.13],
        [196.00, 246.94, 293.66, 349.23],
    ]
    bar_len = int(sample_rate * 2.0)
    beat_len = int(sample_rate * 0.5)

    with wave.open(str(out_audio_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            chord = chords[(i // bar_len) % len(chords)]
            beat_idx = (i // beat_len) % 4
            beat_pos = (i % beat_len) / beat_len

            pad = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.065
            bass = 0.22 * math.exp(-3.0 * beat_pos) * math.sin(2 * math.pi * (chord[0] / 2) * t)
            kick = 0.0
            if beat_idx in (0, 2) and beat_pos < 0.22:
                kf = 115 * math.exp(-20 * beat_pos) + 45
                kick = 0.34 * math.exp(-11 * beat_pos) * math.sin(2 * math.pi * kf * t)
            snare = 0.0
            if beat_idx in (1, 3) and beat_pos < 0.14:
                snare = 0.16 * math.exp(-28 * beat_pos) * random.uniform(-1, 1)

            val = max(-0.95, min(0.95, pad + bass + kick + snare))
            frames.extend(struct.pack("<h", int(val * 32767)))

        wf.writeframes(frames)


def sketch_line(draw, p1, p2, fill, width, rng, segments=5):
    x1, y1 = p1
    x2, y2 = p2
    pts = [(x1, y1)]
    for s in range(1, segments):
        t = s / segments
        jx = rng.uniform(-2.6, 2.6)
        jy = rng.uniform(-2.6, 2.6)
        pts.append((x1 + (x2 - x1) * t + jx, y1 + (y2 - y1) * t + jy))
    pts.append((x2, y2))
    draw.line(pts, fill=fill, width=width, joint="curve")


def sketch_circle(draw, cx, cy, r, fill_color, outline_color, width, rng, steps=28):
    pts = []
    for i in range(steps):
        ang = (2 * math.pi * i) / steps
        jitter = rng.uniform(-3.0, 3.0)
        px = cx + (r + jitter) * math.cos(ang)
        py = cy + (r + jitter) * math.sin(ang)
        pts.append((px, py))
    if fill_color is not None:
        draw.polygon(pts, fill=fill_color)
    pts.append(pts[0])
    draw.line(pts, fill=outline_color, width=width, joint="curve")


def draw_prop(draw, prop, cx, cy, is_dark, rng):
    ink = (240, 240, 245) if is_dark else (20, 20, 25)
    if prop == "phone":
        px, py = cx + 88, cy - 35
        draw.rounded_rectangle([px - 24, py - 42, px + 24, py + 42], radius=8, fill=(30, 35, 50), outline=ink, width=5)
        draw.rounded_rectangle([px - 18, py - 32, px + 18, py + 28], radius=4, fill=(120, 200, 255))
        draw.ellipse([px + 10, py - 50, px + 34, py - 26], fill=(235, 50, 60))
    elif prop == "laptop":
        dx, dy = cx + 115, cy + 25
        sketch_line(draw, (dx - 65, dy), (dx + 85, dy), ink, 9, rng)
        draw.polygon([(dx - 20, dy), (dx + 55, dy), (dx + 75, dy - 65), (dx, dy - 65)], fill=(190, 215, 240), outline=ink)
    elif prop == "bank_alert":
        bx, by = cx, cy - 335
        draw.rounded_rectangle([bx - 135, by - 36, bx + 135, by + 36], radius=16, fill=(225, 45, 55), outline=(255, 255, 255), width=4)
        draw.text((bx, by), "BALANCE: $3.42", fill=(255, 255, 255), font=_load_font(28), anchor="mm")
    elif prop == "coffee":
        mx, my = cx + 82, cy - 15
        draw.rectangle([mx - 18, my - 22, mx + 18, my + 22], fill=(255, 255, 255), outline=ink, width=5)
        draw.arc([mx + 12, my - 14, mx + 28, my + 12], start=270, end=90, fill=ink, width=5)
    elif prop == "bed":
        draw.rounded_rectangle([cx - 165, cy + 40, cx + 165, cy + 165], radius=18, fill=(75, 95, 145), outline=ink, width=6)
        draw.rounded_rectangle([cx - 150, cy + 10, cx - 55, cy + 50], radius=12, fill=(245, 245, 250), outline=ink, width=5)


def draw_speech_bubble(draw, x, y, text, speaker_label, align="left"):
    font = _load_font(35)
    label_font = _load_font(23)
    wrapped = textwrap.fill(text, width=20)
    lines = wrapped.split("\n")
    box_w = 420
    box_h = 54 + len(lines) * 42

    x0 = max(45, min(1080 - 45 - box_w, x - box_w // 2))
    y0 = y - box_h // 2
    x1 = x0 + box_w
    y1 = y0 + box_h

    draw.rounded_rectangle([x0 + 7, y0 + 7, x1 + 7, y1 + 7], radius=22, fill=(18, 18, 22))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=22, fill=(255, 255, 255), outline=(18, 18, 22), width=6)

    tail_x = x0 + 85 if align == "left" else x1 - 85
    draw.polygon([(tail_x - 16, y1 - 2), (tail_x + 16, y1 - 2), (tail_x, y1 + 26)], fill=(255, 255, 255))
    draw.line([(tail_x - 16, y1), (tail_x, y1 + 26), (tail_x + 16, y1)], fill=(18, 18, 22), width=6)

    if speaker_label:
        draw.text((x0 + 22, y0 + 13), speaker_label.upper(), fill=(220, 50, 60), font=label_font)
    draw.multiline_text((x0 + 22, y0 + 44), wrapped, fill=(15, 15, 20), font=font, spacing=7)


def draw_character(draw, cx, cy, pose, frame_idx, is_dark_bg=False, scale=1.0):
    rng = random.Random((frame_idx // 2) * 997 + int(cx))
    ink = (245, 245, 248) if is_dark_bg else (18, 18, 22)
    face_fill = (34, 37, 48) if is_dark_bg else (255, 255, 255)
    stroke = max(8, int(12 * scale))
    r = int(80 * scale)
    head_y = cy - int(195 * scale)

    sketch_circle(draw, cx, head_y, r, face_fill, ink, stroke, rng)

    if pose == "blank_stare":
        draw.ellipse([cx - 32, head_y - 12, cx - 18, head_y + 2], fill=ink)
        draw.ellipse([cx + 18, head_y - 12, cx + 32, head_y + 2], fill=ink)
        sketch_line(draw, (cx - 24, head_y + 28), (cx + 24, head_y + 28), ink, 7, rng, segments=3)
    elif pose in ("sweating", "panic"):
        draw.ellipse([cx - 38, head_y - 22, cx - 12, head_y + 4], outline=ink, width=5)
        draw.ellipse([cx + 12, head_y - 22, cx + 38, head_y + 4], outline=ink, width=5)
        draw.ellipse([cx - 28, head_y - 12, cx - 22, head_y - 6], fill=ink)
        draw.ellipse([cx + 22, head_y - 12, cx + 28, head_y - 6], fill=ink)
        sketch_line(draw, (cx - 42, head_y - 32), (cx - 16, head_y - 24), ink, 6, rng, segments=2)
        sketch_line(draw, (cx + 42, head_y - 32), (cx + 16, head_y - 24), ink, 6, rng, segments=2)
        draw.ellipse([cx - 20, head_y + 16, cx + 20, head_y + 42], outline=ink, width=6)
        drop_y = head_y - 28 + int((frame_idx * 12) % 62)
        draw.ellipse([cx + 92, drop_y, cx + 110, drop_y + 24], fill=(65, 175, 255))
    elif pose == "smug":
        sketch_line(draw, (cx - 38, head_y - 14), (cx - 14, head_y - 8), ink, 7, rng, segments=2)
        sketch_line(draw, (cx + 14, head_y - 8), (cx + 38, head_y - 14), ink, 7, rng, segments=2)
        draw.arc([cx - 28, head_y + 6, cx + 28, head_y + 38], start=10, end=170, fill=ink, width=8)
    else:
        sketch_line(draw, (cx - 40, head_y - 22), (cx - 14, head_y - 8), ink, 7, rng, segments=2)
        sketch_line(draw, (cx - 14, head_y - 8), (cx - 40, head_y + 6), ink, 7, rng, segments=2)
        sketch_line(draw, (cx + 40, head_y - 22), (cx + 14, head_y - 8), ink, 7, rng, segments=2)
        sketch_line(draw, (cx + 14, head_y - 8), (cx + 40, head_y + 6), ink, 7, rng, segments=2)
        draw.ellipse([cx - 24, head_y + 12, cx + 24, head_y + 48], fill=ink)

    neck_y = head_y + r
    hip_y = cy + int(85 * scale)
    leg_end = cy + int(260 * scale)
    sketch_line(draw, (cx, neck_y), (cx, hip_y), ink, stroke, rng)
    sketch_line(draw, (cx, hip_y), (cx - int(62 * scale), leg_end), ink, stroke, rng)
    sketch_line(draw, (cx, hip_y), (cx + int(62 * scale), leg_end), ink, stroke, rng)

    sh_y = neck_y + int(36 * scale)
    if pose in ("panic", "table_flip"):
        wave = int(math.sin(frame_idx * 0.85) * 22)
        sketch_line(draw, (cx, sh_y), (cx - 92, sh_y - 92 + wave), ink, stroke, rng)
        sketch_line(draw, (cx, sh_y), (cx + 92, sh_y - 92 - wave), ink, stroke, rng)
    elif pose == "smug":
        sketch_line(draw, (cx, sh_y), (cx - 72, sh_y + 62), ink, stroke, rng)
        sketch_line(draw, (cx - 72, sh_y + 62), (cx - 15, sh_y + 102), ink, stroke, rng)
        sketch_line(draw, (cx, sh_y), (cx + 72, sh_y + 62), ink, stroke, rng)
        sketch_line(draw, (cx + 72, sh_y + 62), (cx + 15, sh_y + 102), ink, stroke, rng)
    else:
        sketch_line(draw, (cx, sh_y), (cx - 60, sh_y + 120), ink, stroke, rng)
        sketch_line(draw, (cx, sh_y), (cx + 68, sh_y + 95), ink, stroke, rng)


def render_paper_base(W, H, setting):
    if setting == "night_3am":
        bg = (22, 26, 40)
    elif setting == "panic_red":
        bg = (52, 16, 22)
    else:
        bg = (246, 243, 235)

    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    if setting == "day":
        for y in range(420, 1340, 56):
            draw.line([(60, y), (W - 60, y)], fill=(232, 229, 220), width=2)
        draw.line([(125, 405), (125, 1350)], fill=(235, 195, 195), width=3)

    return img


def draw_immersive_frame(frame_idx, scene_frames, scene_idx, hook_text, scene, out_png):
    W, H = 1080, 1920
    setting = scene.get("setting", "day")
    is_dark = setting in ("night_3am", "panic_red")
    accent_line = (85, 95, 135) if setting == "night_3am" else ((225, 65, 75) if setting == "panic_red" else (25, 25, 30))

    img = render_paper_base(W, H, setting)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([55, 85, W - 55, 355], radius=30, fill=(255, 255, 255), outline=(18, 18, 22), width=6)
    hook_font = _load_font(48)
    wrapped_hook = textwrap.fill(hook_text, width=26)
    draw.multiline_text((W // 2, 220), wrapped_hook, fill=(15, 15, 20), font=hook_font, anchor="mm", align="center", spacing=12)

    total_progress = scene.get("progress", 0.5)
    draw.rectangle([55, 375, W - 55, 387], fill=(185, 185, 190))
    draw.rectangle([55, 375, 55 + int((W - 110) * total_progress), 387], fill=(235, 60, 70))

    if setting == "night_3am":
        draw.ellipse([820, 430, 925, 535], fill=(250, 235, 150))
        draw.ellipse([850, 420, 950, 520], fill=(22, 26, 40))
        draw.text((140, 455), "3:14 AM", fill=(145, 165, 225), font=_load_font(42))
    elif setting == "panic_red":
        for angle in range(0, 360, 18):
            rad = math.radians(angle + (frame_idx * 5))
            x1 = W // 2 + int(math.cos(rad) * 350)
            y1 = 1040 + int(math.sin(rad) * 350)
            x2 = W // 2 + int(math.cos(rad) * 580)
            y2 = 1040 + int(math.sin(rad) * 580)
            draw.line([(x1, y1), (x2, y2)], fill=(135, 35, 45), width=6)

    draw.line([(80, 1335), (W - 80, 1335)], fill=accent_line, width=6)

    t = frame_idx / max(1, FPS)
    bob = int(math.sin(t * 11) * 7)
    shake = int(math.sin(t * 38) * 13) if (setting == "panic_red" or scene_idx == 2) else 0

    left_line = scene.get("left_line", "")
    right_line = scene.get("right_line", "")
    prop = scene.get("prop", "none")

    if right_line:
        draw_character(draw, 305 + shake, 1065 + bob, scene.get("left_pose", "blank_stare"), frame_idx, is_dark, scale=0.92)
        draw_character(draw, 775 - shake, 1065 - bob, scene.get("right_pose", "smug"), frame_idx, is_dark, scale=0.92)
        draw_prop(draw, prop, 305 + shake, 1065 + bob, is_dark, random.Random(frame_idx // 2))
        if left_line:
            draw_speech_bubble(draw, 285, 640, left_line, scene.get("left_name", "ME"), align="left")
        if frame_idx >= int(scene_frames * 0.22):
            draw_speech_bubble(draw, 775, 735, right_line, scene.get("right_name", "MY BRAIN"), align="right")
    else:
        draw_character(draw, W // 2 + shake, 1065 + bob, scene.get("left_pose", "sweating"), frame_idx, is_dark, scale=1.06)
        draw_prop(draw, prop, W // 2 + shake, 1065 + bob, is_dark, random.Random(frame_idx // 2))
        if left_line:
            draw_speech_bubble(draw, W // 2, 640, left_line, scene.get("left_name", ""), align="left")

    bottom_caption = scene.get("caption", "")
    if bottom_caption:
        sub_font = _load_font(44)
        wrapped_sub = textwrap.fill(bottom_caption, width=26)
        draw.rounded_rectangle([75, 1410, W - 75, 1675], radius=28, fill=(15, 17, 24), outline=(255, 255, 255), width=4)
        draw.multiline_text((W // 2, 1542), wrapped_sub, fill=(255, 255, 255), font=sub_font, anchor="mm", align="center", spacing=12)

    draw.text((W // 2, 1810), PAGE_HANDLE, fill=(160, 160, 170) if is_dark else (105, 105, 115), font=_load_font(32), anchor="mm")

    if scene_idx == 2:
        zoom = 1.0 + min(0.14, (frame_idx / max(1, scene_frames)) * 0.18)
        crop_w = int(W / zoom)
        crop_h = int(H / zoom)
        x0 = (W - crop_w) // 2
        y0 = int((H - crop_h) * 0.45)
        img = img.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((W, H), Image.Resampling.BILINEAR)

    img.save(out_png, format="PNG")


def render_stickman_reel_mp4(script_data, out_mp4):
    tmp_dir = pathlib.Path("tmp_frames")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    hook = script_data["hook"]
    scenes = script_data["scenes"]
    sec_per_scene = 3.0
    scene_frames = int(FPS * sec_per_scene)
    total_frames = scene_frames * len(scenes)
    frame_counter = 0

    for idx, scene in enumerate(scenes):
        for f in range(scene_frames):
            scene_copy = dict(scene)
            scene_copy["progress"] = (frame_counter + 1) / max(1, total_frames)
            frame_path = tmp_dir / f"frame_{frame_counter:04d}.png"
            draw_immersive_frame(f, scene_frames, idx, hook, scene_copy, frame_path)
            frame_counter += 1

    audio_path = tmp_dir / "track.wav"
    build_audio_track(
        audio_path,
        music_prompt=script_data.get("music_prompt", "quirky playful pizzicato comedy loop, marimba and bass, instrumental"),
        bpm=script_data.get("music_bpm", 118),
        music_mood=script_data.get("music_mood", "upbeat"),
        duration_sec=len(scenes) * sec_per_scene
    )

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(tmp_dir / "frame_%04d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp_dir)
    print(f"Rendered realistic hand-drawn stickman Reel: {out_mp4}")


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


def get_ig_account_id():
    return os.environ.get("IG_USER_ID", "17841476835986162").strip() or "17841476835986162"


def publish_reel_to_instagram(video_url, caption):
    if not IG_ACCESS_TOKEN:
        print("IG_ACCESS_TOKEN not set yet — generated Reel saved in repo only.")
        return

    ig_id = get_ig_account_id()
    base = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{ig_id}"

    container = post_request(f"{base}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": IG_ACCESS_TOKEN
    })
    creation_id = container["id"]
    print(f"Created IG Reel container: {creation_id}")

    for attempt in range(1, 20):
        time.sleep(5)
        status_url = f"[https://graph.facebook.com/](https://graph.facebook.com/){GRAPH_VERSION}/{creation_id}?fields=status_code,status&access_token={IG_ACCESS_TOKEN}"
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"Reel processing status ({attempt}/20): {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram Reel processing failed: {status_data}")

    published = post_request(f"{base}/media_publish", {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    })
    print(f"LIVE REEL ON INSTAGRAM! Media ID: {published['id']}")


if __name__ == "__main__":
    trends = fetch_live_trends()
    prompt = (
        "You run a viral, 1M-follower stickman comedy Instagram Reels page modeled after @enemy.stickman, @sketchy.stickman, and @dailystickman. "
        "Write 1 ultra-snappy, relatable 3-scene skit (9 seconds total) with two characters (e.g., ME vs MY BRAIN, ME vs BANK ACCOUNT, ME vs BOSS). "
        "Keep every line short and punchy so viewers read it effortlessly in 2 seconds.\n"
        "Also write a custom instrumental 'music_prompt' for Google Lyria AI music generation matching the skit's comedy arc.\n"
        "Return valid JSON with:\n"
        "- 'music_prompt': descriptive instrumental prompt for Lyria (max 18 words, always end with 'instrumental')\n"
        "- 'music_bpm': integer between 95 and 138\n"
        "- 'music_mood': strictly one of ['dramatic', 'hype', 'upbeat']\n"
        "- 'hook': punchy top hook (max 8 words, e.g., 'POV: Checking your bank balance on Monday')\n"
        "- 'scenes': array of exactly 3 objects (Scene 1 = normal setup, Scene 2 = awkward escalation, Scene 3 = chaotic punchline), each with:\n"
        "   - 'setting': strictly one of ['day', 'night_3am', 'panic_red']\n"
        "   - 'prop': strictly one of ['phone', 'laptop', 'bank_alert', 'coffee', 'bed', 'none']\n"
        "   - 'left_name': short character label (e.g., 'ME')\n"
        "   - 'left_pose': strictly one of ['blank_stare', 'sweating', 'smug', 'panic', 'table_flip']\n"
        "   - 'left_line': ultra-short speech bubble (max 6 words)\n"
        "   - 'right_name': second character label (e.g., 'MY BRAIN')\n"
        "   - 'right_pose': strictly one of ['blank_stare', 'sweating', 'smug', 'panic', 'table_flip']\n"
        "   - 'right_line': snappy comeback speech bubble (max 6 words, or '' for solo reaction)\n"
        "   - 'caption': punchy bottom narrator line (max 8 words)\n"
        "- 'ig_caption': short relatable caption + 'Send this to someone who does this' + 8 viral comedy/reels hashtags\n\n"
        f"Trends:\n{trends}"
    )

    script_data = ask_gemini(prompt)

    est = timezone(timedelta(hours=-5))
    stamp = datetime.now(est).strftime("%Y-%m-%d_%H%M")
    posts_dir = pathlib.Path("posts")
    posts_dir.mkdir(exist_ok=True)
    rel_mp4 = f"posts/reel_{stamp}.mp4"

    render_stickman_reel_mp4(script_data, rel_mp4)
    pathlib.Path(f"posts/reel_{stamp}.txt").write_text(script_data["ig_caption"], encoding="utf-8")

    public_video_url = archive_and_get_pages_url(rel_mp4)
    publish_reel_to_instagram(public_video_url, script_data["ig_caption"])
