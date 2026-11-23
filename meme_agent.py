import os
import math
import json
import time
import wave
import struct
import random
import socket
import shutil
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
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
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
                    print(f"Generated stickman script with {model}")
                    return data["candidates"][0]["content"]["parts"][0]["text"]
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
    raise RuntimeError("All Gemini models failed.")


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


def build_audio_track(out_audio_path, duration_sec=10.5):
    """Uses any real .mp3 in assets/audio/ if available, otherwise generates a rich chord+beat groove."""
    audio_dir = pathlib.Path("assets/audio")
    mp3s = list(audio_dir.glob("*.mp3")) if audio_dir.exists() else []
    if mp3s:
        chosen = random.choice(mp3s)
        print(f"Using real music track: {chosen}")
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(chosen),
            "-t", str(duration_sec), "-af", "afade=t=out:st=" + str(duration_sec - 1.0) + ":d=1.0",
            str(out_audio_path)
        ], check=True)
        return

    # Richer warm Rhodes-style chord progression + crisp percussion fallback
    sample_rate = 44100
    total_samples = int(sample_rate * duration_sec)
    chords = [
        [261.63, 311.13, 392.00, 466.16],  # Cm7
        [207.65, 261.63, 311.13, 392.00],  # Abmaj7
        [174.61, 207.65, 261.63, 311.13],  # Fm7
        [196.00, 246.94, 293.66, 349.23],  # G7
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

            # Warm electric-piano chord pad
            pad = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.065
            # Sub bass
            bass = 0.22 * math.exp(-3.0 * beat_pos) * math.sin(2 * math.pi * (chord[0] / 2) * t)
            # Kick & snare groove
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


def draw_speech_bubble(draw, x, y, text, speaker_label, align="left"):
    font = _load_font(34)
    label_font = _load_font(24)
    wrapped = textwrap.fill(text, width=22)
    lines = wrapped.split("\n")
    box_w = 430
    box_h = 56 + len(lines) * 42

    x0 = x - box_w // 2
    y0 = y - box_h // 2
    x1 = x0 + box_w
    y1 = y0 + box_h

    # Drop shadow + crisp comic speech bubble
    draw.rounded_rectangle([x0 + 8, y0 + 8, x1 + 8, y1 + 8], radius=24, fill=(20, 20, 25))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(255, 255, 255), outline=(18, 18, 22), width=6)

    # Pointer triangle toward character
    tail_x = x0 + 90 if align == "left" else x1 - 90
    draw.polygon([(tail_x - 18, y1 - 2), (tail_x + 18, y1 - 2), (tail_x, y1 + 28)], fill=(255, 255, 255))
    draw.line([(tail_x - 18, y1), (tail_x, y1 + 28), (tail_x + 18, y1)], fill=(18, 18, 22), width=6)

    if speaker_label:
        draw.text((x0 + 24, y0 + 14), speaker_label.upper(), fill=(220, 55, 65), font=label_font)
    draw.multiline_text((x0 + 24, y0 + 46), wrapped, fill=(18, 18, 22), font=font, spacing=8)


def draw_character(draw, cx, cy, pose, frame_idx, is_dark_bg=False, scale=1.0):
    ink = (245, 245, 248) if is_dark_bg else (18, 18, 22)
    face_fill = (32, 34, 44) if is_dark_bg else (255, 255, 255)
    stroke = max(8, int(13 * scale))
    r = int(82 * scale)
    head_y = cy - int(200 * scale)

    # Head
    draw.ellipse([cx - r, head_y - r, cx + r, head_y + r], fill=face_fill, outline=ink, width=stroke)

    # Face expression
    if pose == "blank_stare":
        draw.ellipse([cx - 32, head_y - 14, cx - 18, head_y], fill=ink)
        draw.ellipse([cx + 18, head_y - 14, cx + 32, head_y], fill=ink)
        draw.line([(cx - 26, head_y + 28), (cx + 26, head_y + 28)], fill=ink, width=8)
    elif pose in ("sweating", "panic"):
        draw.ellipse([cx - 38, head_y - 20, cx - 12, head_y + 6], outline=ink, width=5)
        draw.ellipse([cx + 12, head_y - 20, cx + 38, head_y + 6], outline=ink, width=5)
        draw.ellipse([cx - 28, head_y - 10, cx - 22, head_y - 4], fill=ink)
        draw.ellipse([cx + 22, head_y - 10, cx + 28, head_y - 4], fill=ink)
        draw.ellipse([cx - 22, head_y + 16, cx + 22, head_y + 44], outline=ink, width=6)
        drop_y = head_y - 30 + int((frame_idx * 11) % 65)
        draw.ellipse([cx + 95, drop_y, cx + 113, drop_y + 24], fill=(70, 175, 255))
    elif pose == "smug":
        draw.line([(cx - 38, head_y - 14), (cx - 14, head_y - 8)], fill=ink, width=7)
        draw.line([(cx + 14, head_y - 8), (cx + 38, head_y - 14)], fill=ink, width=7)
        draw.arc([cx - 28, head_y + 6, cx + 28, head_y + 38], start=10, end=170, fill=ink, width=8)
    else:  # shocked / table_flip
        draw.line([(cx - 40, head_y - 22), (cx - 14, head_y - 8), (cx - 40, head_y + 6)], fill=ink, width=7)
        draw.line([(cx + 40, head_y - 22), (cx + 14, head_y - 8), (cx + 40, head_y + 6)], fill=ink, width=7)
        draw.ellipse([cx - 24, head_y + 12, cx + 24, head_y + 48], fill=ink)

    # Torso & Legs
    neck_y = head_y + r
    hip_y = cy + int(85 * scale)
    leg_end = cy + int(265 * scale)
    draw.line([(cx, neck_y), (cx, hip_y)], fill=ink, width=stroke)
    draw.line([(cx, hip_y), (cx - int(65 * scale), leg_end)], fill=ink, width=stroke)
    draw.line([(cx, hip_y), (cx + int(65 * scale), leg_end)], fill=ink, width=stroke)

    # Arms
    sh_y = neck_y + int(38 * scale)
    if pose in ("panic", "table_flip"):
        wave = int(math.sin(frame_idx * 0.8) * 20)
        draw.line([(cx, sh_y), (cx - 95, sh_y - 95 + wave)], fill=ink, width=stroke)
        draw.line([(cx, sh_y), (cx + 95, sh_y - 95 - wave)], fill=ink, width=stroke)
    elif pose == "smug":
        draw.line([(cx, sh_y), (cx - 75, sh_y + 65), (cx - 15, sh_y + 105)], fill=ink, width=stroke)
        draw.line([(cx, sh_y), (cx + 75, sh_y + 65), (cx + 15, sh_y + 105)], fill=ink, width=stroke)
    else:
        draw.line([(cx, sh_y), (cx - 65, sh_y + 125)], fill=ink, width=stroke)
        draw.line([(cx, sh_y), (cx + 65, sh_y + 125)], fill=ink, width=stroke)


def draw_immersive_frame(frame_idx, scene_frames, hook_text, scene, out_png):
    W, H = 1080, 1920
    setting = scene.get("setting", "day")
    is_dark = setting in ("night_3am", "panic_red")

    if setting == "night_3am":
        bg_color = (22, 25, 38)
        accent_line = (75, 85, 120)
    elif setting == "panic_red":
        bg_color = (45, 16, 22)
        accent_line = (220, 65, 75)
    else:
        bg_color = (247, 246, 242)
        accent_line = (25, 25, 30)

    img = Image.new("RGB", (W, H), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Top Hook Header Card (high-contrast pill banner)
    draw.rounded_rectangle([55, 85, W - 55, 365], radius=32, fill=(255, 255, 255), outline=(18, 18, 22), width=6)
    hook_font = _load_font(48)
    wrapped_hook = textwrap.fill(hook_text, width=28)
    draw.multiline_text((W // 2, 225), wrapped_hook, fill=(15, 15, 20), font=hook_font, anchor="mm", align="center", spacing=12)

    # Progress bar across top showing Reel pacing
    total_progress = scene.get("progress", 0.5)
    draw.rectangle([55, 385, W - 55, 397], fill=(180, 180, 185))
    draw.rectangle([55, 385, 55 + int((W - 110) * total_progress), 397], fill=(235, 65, 75))

    # Setting details (3 AM Moon/Clock or Panic Speed Lines)
    if setting == "night_3am":
        draw.ellipse([820, 440, 930, 550], fill=(250, 235, 150))
        draw.ellipse([850, 430, 955, 535], fill=bg_color)
        draw.text((150, 470), "3:14 AM", fill=(140, 160, 220), font=_load_font(42))
    elif setting == "panic_red":
        for angle in range(0, 360, 20):
            rad = math.radians(angle + (frame_idx * 4))
            x1 = W // 2 + int(math.cos(rad) * 380)
            y1 = 1040 + int(math.sin(rad) * 380)
            x2 = W // 2 + int(math.cos(rad) * 560)
            y2 = 1040 + int(math.sin(rad) * 560)
            draw.line([(x1, y1), (x2, y2)], fill=(120, 35, 45), width=6)

    # Floor horizon line
    draw.line([(80, 1335), (W - 80, 1335)], fill=accent_line, width=6)

    # Two-character interaction or solo dramatic center
    t = frame_idx / max(1, FPS)
    bob = int(math.sin(t * 11) * 8)
    shake = int(math.sin(t * 36) * 12) if setting == "panic_red" else 0

    left_line = scene.get("left_line", "")
    right_line = scene.get("right_line", "")

    if right_line:
        # Two stickmen facing off with comic speech bubbles
        draw_character(draw, 300 + shake, 1065 + bob, scene.get("left_pose", "blank_stare"), frame_idx, is_dark, scale=0.92)
        draw_character(draw, 780 - shake, 1065 - bob, scene.get("right_pose", "smug"), frame_idx, is_dark, scale=0.92)
        if left_line:
            draw_speech_bubble(draw, 290, 650, left_line, scene.get("left_name", "ME"), align="left")
        if frame_idx >= int(scene_frames * 0.25):
            draw_speech_bubble(draw, 770, 740, right_line, scene.get("right_name", "MY BRAIN"), align="right")
    else:
        draw_character(draw, W // 2 + shake, 1065 + bob, scene.get("left_pose", "sweating"), frame_idx, is_dark, scale=1.05)
        if left_line:
            draw_speech_bubble(draw, W // 2, 650, left_line, scene.get("left_name", ""), align="left")

    # Bottom Punchline Subtitle Pill
    bottom_caption = scene.get("caption", "")
    if bottom_caption:
        sub_font = _load_font(44)
        wrapped_sub = textwrap.fill(bottom_caption, width=28)
        draw.rounded_rectangle([75, 1410, W - 75, 1680], radius=28, fill=(15, 17, 24), outline=(255, 255, 255), width=4)
        draw.multiline_text((W // 2, 1545), wrapped_sub, fill=(255, 255, 255), font=sub_font, anchor="mm", align="center", spacing=12)

    draw.text((W // 2, 1810), PAGE_HANDLE, fill=(155, 155, 165) if is_dark else (110, 110, 120), font=_load_font(32), anchor="mm")
    img.save(out_png, format="PNG")


def render_stickman_reel_mp4(script_data, out_mp4):
    tmp_dir = pathlib.Path("tmp_frames")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    hook = script_data["hook"]
    scenes = script_data["scenes"]
    sec_per_scene = 3.5
    scene_frames = int(FPS * sec_per_scene)
    total_frames = scene_frames * len(scenes)
    frame_counter = 0

    for idx, scene in enumerate(scenes):
        for f in range(scene_frames):
            scene_copy = dict(scene)
            scene_copy["progress"] = (frame_counter + 1) / max(1, total_frames)
            frame_path = tmp_dir / f"frame_{frame_counter:04d}.png"
            draw_immersive_frame(f, scene_frames, hook, scene_copy, frame_path)
            frame_counter += 1

    audio_path = tmp_dir / "track.wav"
    build_audio_track(audio_path, duration_sec=len(scenes) * sec_per_scene)

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
    print(f"Rendered immersive stickman Reel: {out_mp4}")


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
    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_id}"

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
        status_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}?fields=status_code,status&access_token={IG_ACCESS_TOKEN}"
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
        "You run a viral, funny stickman comedy Instagram Reels page like 'enemy.stickman'. "
        "Write 1 hilarious, hyper-relatable 3-scene skit with two characters (e.g., ME vs MY BRAIN, ME vs BANK ACCOUNT, ME vs BOSS) "
        "based on real-world everyday comedy or today's trends.\n"
        "Return valid JSON with:\n"
        "- 'hook': punchy top hook (max 11 words, e.g., 'POV: Checking your bank account on Monday morning')\n"
        "- 'scenes': array of exactly 3 objects (Scene 1 = normal setup, Scene 2 = escalation, Scene 3 = chaotic punchline), each with:\n"
        "   - 'setting': strictly one of ['day', 'night_3am', 'panic_red']\n"
        "   - 'left_name': short character label (e.g., 'ME')\n"
        "   - 'left_pose': strictly one of ['blank_stare', 'sweating', 'smug', 'panic', 'table_flip']\n"
        "   - 'left_line': short speech bubble line (max 9 words)\n"
        "   - 'right_name': second character label (e.g., 'MY BRAIN' or 'BANK APP')\n"
        "   - 'right_pose': strictly one of ['blank_stare', 'sweating', 'smug', 'panic', 'table_flip']\n"
        "   - 'right_line': funny comeback speech bubble (max 9 words, or empty string '' if solo scene)\n"
        "   - 'caption': punchy narrator subtitle at bottom (max 11 words)\n"
        "- 'ig_caption': funny relatable caption + 'Tag someone who does this' + 8 viral comedy/reels hashtags\n\n"
        f"Trends:\n{trends}"
    )

    raw = ask_gemini(prompt).strip()
    script_data = json.loads(raw, strict=False)

    est = timezone(timedelta(hours=-5))
    stamp = datetime.now(est).strftime("%Y-%m-%d_%H%M")
    posts_dir = pathlib.Path("posts")
    posts_dir.mkdir(exist_ok=True)
    rel_mp4 = f"posts/reel_{stamp}.mp4"

    render_stickman_reel_mp4(script_data, rel_mp4)
    pathlib.Path(f"posts/reel_{stamp}.txt").write_text(script_data["ig_caption"], encoding="utf-8")

    public_video_url = archive_and_get_pages_url(rel_mp4)
    publish_reel_to_instagram(public_video_url, script_data["ig_caption"])
