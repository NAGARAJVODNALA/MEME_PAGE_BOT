import os
import json
import time
import socket
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

def fetch_live_trends():
    trends = []
    try:
        req = urllib.request.Request(
            "https://trends.google.com/trending/rss?geo=US",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item/title")[:12]:
                if item.text:
                    trends.append(item.text.strip())
    except Exception as e:
        print(f"Google Trends RSS skipped: {e}")

    if not trends:
        trends = [
            "Monday morning meetings",
            "Checking bank account after the weekend",
            "AI taking over every job",
            "Procrastinating until 11:59 PM",
            "Saying 'let's catch up soon' and never texting back"
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
                    print(f"Generated meme copy with {model}")
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

def render_meme_jpeg(top_caption, punchline, out_path):
    img = Image.new("RGB", (1080, 1080), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    header_font = _load_font(44)
    wrapped_top = textwrap.fill(top_caption, width=34)
    draw.multiline_text((70, 70), wrapped_top, fill=(15, 15, 15), font=header_font, spacing=14)

    draw.rounded_rectangle([60, 350, 1020, 960], radius=32, fill=(18, 20, 28))
    body_font = _load_font(54)
    wrapped_body = textwrap.fill(punchline, width=25)
    draw.multiline_text((110, 460), wrapped_body, fill=(255, 255, 255), font=body_font, spacing=18)

    draw.text((70, 995), PAGE_HANDLE, fill=(110, 110, 125), font=_load_font(28))
    img.save(out_path, format="JPEG", quality=95)
    print(f"Saved JPEG meme: {out_path}")

def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish meme {rel_path}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push"], check=True)

    owner, repo = REPO_NAME.split("/", 1)
    pages_url = f"https://{owner.lower()}.github.io/{repo}/{rel_path}"

    # Wait until GitHub Pages deployment serves the live JPEG with image/jpeg Content-Type
    for attempt in range(1, 13):
        time.sleep(5)
        try:
            req = urllib.request.Request(pages_url, headers={"User-Agent": "facebookexternalhit/1.1"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and "image/jpeg" in ctype:
                    print(f"Verified live GitHub Pages JPEG ({ctype}): {pages_url}")
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages deploy ({attempt}/12): {e}")

    raise RuntimeError(f"GitHub Pages did not serve JPEG in time: {pages_url}")

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

def publish_to_instagram(image_url, caption):
    if not IG_ACCESS_TOKEN:
        print("IG_ACCESS_TOKEN not set yet — generated meme saved in repo only.")
        return

    ig_id = get_ig_account_id()
    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_id}"

    container = post_request(f"{base}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN
    })
    creation_id = container["id"]
    print(f"Created IG container: {creation_id}")

    for _ in range(10):
        status_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}?fields=status_code&access_token={IG_ACCESS_TOKEN}"
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram container failed: {status_data}")
        time.sleep(3)

    published = post_request(f"{base}/media_publish", {
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN
    })
    print(f"LIVE ON INSTAGRAM! Media ID: {published['id']}")

if __name__ == "__main__":
    trends = fetch_live_trends()
    prompt = (
        "You run a viral, funny Instagram meme page. Looking at today's trending topics below, "
        "write 1 original, relatable meme with:\n"
        "- 'top_caption': relatable setup line (max 14 words, like 'Me pretending to work while...')\n"
        "- 'punchline': funny twist or reaction (max 16 words)\n"
        "- 'ig_caption': short engaging caption + call-to-action ('Tag someone who does this') + 8 viral hashtags\n"
        "Return valid JSON with keys: top_caption, punchline, ig_caption.\n\n"
        f"Trends:\n{trends}"
    )

    raw = ask_gemini(prompt).strip()
    meme = json.loads(raw, strict=False)

    est = timezone(timedelta(hours=-5))
    stamp = datetime.now(est).strftime("%Y-%m-%d_%H%M")
    posts_dir = pathlib.Path("posts")
    posts_dir.mkdir(exist_ok=True)
    rel_img = f"posts/meme_{stamp}.jpg"

    render_meme_jpeg(meme["top_caption"], meme["punchline"], rel_img)
    pathlib.Path(f"posts/meme_{stamp}.txt").write_text(meme["ig_caption"], encoding="utf-8")

    public_image_url = archive_and_get_pages_url(rel_img)
    publish_to_instagram(public_image_url, meme["ig_caption"])
