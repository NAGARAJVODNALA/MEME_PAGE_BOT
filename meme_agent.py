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
            "Monday morning 9 AM meetings",
            "Checking your bank account after the weekend",
            "Boss saying 'quick 5 minute call' at 4:58 PM",
            "Overthinking a text you sent 3 hours ago",
            "Setting 7 alarms and snoozing all of them"
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


def generate_lo_fi_beat_wav(wav_path, duration_sec=9.0):
    """Generates a clean lo-fi synth bass + snare groove so Reels always have crisp audio."""
    sample_rate = 44100
    total_samples = int(sample_rate * duration_sec)
    notes = [130.81, 155.56, 174.61, 196.00]  # C3, Eb3, F3, G3 chill minor loop
    beat_len = int(sample_rate * 0.5)

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            beat_idx = (i // beat_len) % len(notes)
            beat_pos = (i % beat_len) / beat_len

            # Warm bass pluck
            freq = notes[beat_idx]
            env = math.exp(-3.5 * beat_pos)
            bass = 0.25 * env * math.sin(2 * math.pi * freq * t)

            # Soft kick on beats 0 & 2, crisp hi-hat tick every beat
            kick = 0.0
            if beat_idx in (0, 2) and beat_pos < 0.25:
                kick_freq = 110 * math.exp(-18 * beat_pos) + 42
                kick = 0.35 * math.exp(-12 * beat_pos) * math.sin(2 * math.pi * kick_freq * t)

            hat = 0.0
            if beat_pos < 0.04:
                hat = 0.06 * math.exp(-80 * beat_pos) * random.uniform(-1, 1)

            val = max(-0.95, min(0.95, bass + kick + hat))
            frames.extend(struct.pack("<h", int(val * 32767)))

        wf.writeframes(frames)


def draw_stickman_frame(frame_idx, total_frames, hook_text, scene_caption, pose, out_png):
    """Draws a 1080x1920 enemy.stickman-style animated frame."""
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), color=(248, 248, 246))
    draw = ImageDraw.Draw(img)

    # Subtle notebook/sketch border
    draw.rectangle([36, 36, W - 36, H - 36], outline=(225, 225, 220), width=4)

    # Top Hook Banner (stays pinned across all scenes like viral Reels)
    hook_font = _load_font(54)
    wrapped_hook = textwrap.fill(hook_text, width=26)
    draw.multiline_text((W // 2, 230), wrapped_hook, fill=(18, 18, 22), font=hook_font, anchor="mm", align="center", spacing=14)
    draw.line([(140, 390), (W - 140, 390)], fill=(20, 20, 24), width=5)

    # Animation oscillation
    t = frame_idx / max(1, FPS)
    bob = int(math.sin(t * 10) * 8)
    fast_shake = int(math.sin(t * 32) * 10) if pose in ("typing_fast", "sweating", "table_flip") else 0

    cx = W // 2 + fast_shake
    cy = 980 + bob
    stroke = 14
    ink = (15, 15, 18)

    # Ground shadow
    draw.ellipse([cx - 170, 1290, cx + 170, 1330], fill=(225, 225, 222))

    # Head
    head_r = 92
    head_cy = cy - 230
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=ink, width=stroke)

    # Expressive Stickman Face by Pose
    if pose == "blank_stare":
        draw.ellipse([cx - 38, head_cy - 18, cx - 22, head_cy - 2], fill=ink)
        draw.ellipse([cx + 22, head_cy - 18, cx + 38, head_cy - 2], fill=ink)
        draw.line([(cx - 32, head_cy + 34), (cx + 32, head_cy + 34)], fill=ink, width=9)
    elif pose in ("sweating", "typing_fast"):
        # Stressed wide eyes + wavy mouth
        draw.ellipse([cx - 44, head_cy - 24, cx - 16, head_cy + 4], outline=ink, width=6)
        draw.ellipse([cx + 16, head_cy - 24, cx + 44, head_cy + 4], outline=ink, width=6)
        draw.ellipse([cx - 33, head_cy - 13, cx - 27, head_cy - 7], fill=ink)
        draw.ellipse([cx + 27, head_cy - 13, cx + 33, head_cy - 7], fill=ink)
        draw.arc([cx - 32, head_cy + 20, cx + 32, head_cy + 48], start=180, end=360, fill=ink, width=8)
        # Animated flying sweat drops
        drop_y = head_cy - 40 + int((frame_idx * 9) % 70)
        draw.ellipse([cx + 115, drop_y, cx + 135, drop_y + 28], fill=(65, 165, 245))
        draw.ellipse([cx - 135, drop_y + 15, cx - 115, drop_y + 43], fill=(65, 165, 245))
    elif pose == "table_flip":
        # Angry > < eyes + shouting mouth
        draw.line([(cx - 45, head_cy - 24), (cx - 18, head_cy - 10), (cx - 45, head_cy + 4)], fill=ink, width=8)
        draw.line([(cx + 45, head_cy - 24), (cx + 18, head_cy - 10), (cx + 45, head_cy + 4)], fill=ink, width=8)
        draw.ellipse([cx - 26, head_cy + 14, cx + 26, head_cy + 54], fill=ink)
    else:  # celebrating / smug
        draw.arc([cx - 45, head_cy - 22, cx - 15, head_cy + 2], start=180, end=360, fill=ink, width=8)
        draw.arc([cx + 15, head_cy - 22, cx + 45, head_cy + 2], start=180, end=360, fill=ink, width=8)
        draw.arc([cx - 36, head_cy + 8, cx + 36, head_cy + 48], start=0, end=180, fill=ink, width=9)

    # Torso & Legs
    neck_y = head_cy + head_r
    hip_y = cy + 95
    draw.line([(cx, neck_y), (cx, hip_y)], fill=ink, width=stroke)
    draw.line([(cx, hip_y), (cx - 75, 1300)], fill=ink, width=stroke)
    draw.line([(cx, hip_y), (cx + 75, 1300)], fill=ink, width=stroke)

    # Arms & Props by Pose
    shoulder_y = neck_y + 45
    if pose == "typing_fast":
        arm_flutter = int(math.sin(t * 40) * 18)
        draw.line([(cx, shoulder_y), (cx + 110, shoulder_y + 65 + arm_flutter)], fill=ink, width=stroke)
        draw.line([(cx, shoulder_y), (cx + 110, shoulder_y + 95 - arm_flutter)], fill=ink, width=stroke)
        # Desk + Laptop
        draw.line([(cx + 80, shoulder_y + 120), (cx + 280, shoulder_y + 120)], fill=ink, width=12)
        draw.line([(cx + 150, shoulder_y + 120), (cx + 195, shoulder_y + 35)], fill=ink, width=12)
    elif pose == "table_flip":
        # Arms thrown up + flipped table flying in air
        draw.line([(cx, shoulder_y), (cx - 110, shoulder_y - 110)], fill=ink, width=stroke)
        draw.line([(cx, shoulder_y), (cx + 110, shoulder_y - 110)], fill=ink, width=stroke)
        flip_y = shoulder_y - 210 - int(abs(math.sin(t * 6)) * 40)
        draw.line([(cx - 140, flip_y), (cx + 140, flip_y - 45)], fill=ink, width=14)
        draw.line([(cx - 110, flip_y), (cx - 125, flip_y - 75)], fill=ink, width=12)
        draw.line([(cx + 110, flip_y - 40), (cx + 95, flip_y - 115)], fill=ink, width=12)
    elif pose == "celebrating":
        wave_y = int(math.sin(t * 14) * 30)
        draw.line([(cx, shoulder_y), (cx - 125, shoulder_y - 110 + wave_y)], fill=ink, width=stroke)
        draw.line([(cx, shoulder_y), (cx + 125, shoulder_y - 110 - wave_y)], fill=ink, width=stroke)
    else:
        # Hands on hips / defeated slump
        draw.line([(cx, shoulder_y), (cx - 85, shoulder_y + 85), (cx - 15, shoulder_y + 135)], fill=ink, width=stroke)
        draw.line([(cx, shoulder_y), (cx + 85, shoulder_y + 85), (cx + 15, shoulder_y + 135)], fill=ink, width=stroke)

    # Bottom Dialogue / Punchline Subtitle Box
    sub_font = _load_font(48)
    wrapped_sub = textwrap.fill(scene_caption, width=28)
    draw.rounded_rectangle([90, 1410, W - 90, 1690], radius=28, fill=(18, 20, 26))
    draw.multiline_text((W // 2, 1550), wrapped_sub, fill=(255, 255, 255), font=sub_font, anchor="mm", align="center", spacing=14)

    # Watermark
    draw.text((W // 2, 1810), PAGE_HANDLE, fill=(120, 120, 128), font=_load_font(32), anchor="mm")
    img.save(out_png, format="PNG")


def render_stickman_reel_mp4(script_data, out_mp4):
    tmp_dir = pathlib.Path("tmp_frames")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    hook = script_data["hook"]
    scenes = script_data["scenes"]  # 3 scenes, 3 seconds each = 9-second viral Reel
    frame_counter = 0

    for scene in scenes:
        scene_frames = FPS * 3
        pose = scene.get("pose", "blank_stare")
        caption = scene.get("caption", "")
        for f in range(scene_frames):
            frame_path = tmp_dir / f"frame_{frame_counter:04d}.png"
            draw_stickman_frame(f, scene_frames, hook, caption, pose, frame_path)
            frame_counter += 1

    wav_path = tmp_dir / "beat.wav"
    generate_lo_fi_beat_wav(wav_path, duration_sec=len(scenes) * 3.0)

    # Encode 1080x1920 H.264 + AAC MP4 optimized for Instagram Reels
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(tmp_dir / "frame_%04d.png"),
        "-i", str(wav_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp_dir)
    print(f"Rendered animated stickman Reel: {out_mp4}")


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
    manual_id = os.environ.get("IG_USER_ID", "").strip()
    if manual_id:
        return manual_id
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/me/assigned_instagram_accounts?access_token={IG_ACCESS_TOKEN}"
    data = json.loads(urllib.request.urlopen(url, timeout=15).read().decode())
    accounts = data.get("data", [])
    if not accounts:
        raise RuntimeError(f"No assigned Instagram accounts found: {data}")
    ig_id = accounts[0]["id"]
    print(f"Resolved Instagram Account ID: {ig_id}")
    return ig_id


def publish_reel_to_instagram(video_url, caption):
    if not IG_ACCESS_TOKEN:
        print("IG_ACCESS_TOKEN not set yet — generated Reel saved in repo only.")
        return

    ig_id = get_ig_account_id()
    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_id}"

    # Step 1: Create REELS container
    container = post_request(f"{base}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": IG_ACCESS_TOKEN
    })
    creation_id = container["id"]
    print(f"Created IG Reel container: {creation_id}")

    # Step 2: Poll until Meta finishes processing the video
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

    # Step 3: Publish Reel to feed & Reels tab
    published = post_request(f"{base}/media_publish", {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    })
    print(f"LIVE REEL ON INSTAGRAM! Media ID: {published['id']}")


if __name__ == "__main__":
    trends = fetch_live_trends()
    prompt = (
        "You run a viral stickman comedy Instagram Reels page like 'enemy.stickman'. "
        "Write 1 hilarious, hyper-relatable 3-scene real-world scenario inspired by everyday life or today's trends.\n"
        "Return valid JSON with:\n"
        "- 'hook': punchy top hook (max 11 words, e.g., 'POV: Your boss says quick 5-minute call at 4:58 PM')\n"
        "- 'scenes': array of exactly 3 objects, each with:\n"
        "   - 'pose': strictly one of ['typing_fast', 'sweating', 'blank_stare', 'table_flip', 'celebrating']\n"
        "   - 'caption': funny beat/dialogue line for that 3-second scene (max 12 words)\n"
        "- 'ig_caption': engaging caption + 'Tag someone who relates' + 8 viral comedy/reels hashtags\n\n"
        f"Trends for inspiration:\n{trends}"
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
