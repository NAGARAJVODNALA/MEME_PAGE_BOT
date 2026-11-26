import os
import math
import json
import time
import wave
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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "NAGARAJVODNALA/MEME_PAGE_BOT").strip()
DEFAULT_IG_USER_ID = "17841476835986162"
GRAPH_VERSION = "v21.0"
FPS = 24
W, H = 1080, 1920
SS = 2  # 2x supersampling for crisp ink lines

# ==============================================================================
# CHARACTER BIBLE & VOICES (TWO TALKING ANIMATED CHARACTERS)
# ==============================================================================
CHAR_A = {
    "name": "Chill Guy",
    "voice": "en-US-AndrewNeural",
    "cap_color": (132, 92, 68),      # Warm brown/olive cap
    "shirt_color": (244, 242, 238),  # White tee/hoodie
    "head_fill": (246, 243, 238),
    "head_shadow": (218, 212, 204),
    "ink_color": (18, 18, 22),
}

CHAR_B = {
    "name": "Friend",
    "voice": "en-US-AvaNeural",
    "hair_color": (28, 30, 36),
    "dress_color": (32, 34, 42),
    "head_fill": (246, 243, 238),
    "head_shadow": (218, 212, 204),
    "ink_color": (18, 18, 22),
}

EXPRESSIONS = [
    "chill_smirk",
    "deadpan",
    "excited_wide",
    "skeptical",
    "shocked",
    "smug_eyes_closed",
]

GESTURES = [
    "relaxed_idle",
    "hand_point",
    "shrug_palms",
    "lean_in_talk",
    "mic_hold",
    "nod_agree",
]


def build_https_url(host, path, query_params=None):
    query = urllib.parse.urlencode(query_params) if query_params else ""
    return urllib.parse.urlunparse(("https", host, path, "", query, ""))


def verify_runtime_environment():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY secret in GitHub Actions.")
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
            print(f"pages.json skipped ({e}), using default @wearechillclub config.")
    return [{
        "slug": "wearechillclub",
        "handle": "@wearechillclub",
        "enabled": True,
        "ig_user_id": os.environ.get("IG_USER_ID", DEFAULT_IG_USER_ID).strip() or DEFAULT_IG_USER_ID,
        "token_secret": "IG_ACCESS_TOKEN",
        "accent_color": [255, 225, 45],
        "domain": (
            "Relatable millennial/Gen-Z everyday chill comedy, lazy day-off logic, "
            "$14.82 bank account negotiations, overthinking texts, and witty deadpan banter"
        ),
    }]


def fetch_world_context():
    headlines = []
    try:
        rss_url = build_https_url("trends.google.com", "/trending/rss", {"geo": "US"})
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
            for el in root.findall(".//item/title")[:5]:
                if el.text:
                    headlines.append(el.text.strip())
    except Exception:
        pass
    return "\n".join(f"- {h}" for h in headlines) if headlines else "- Everyday relatable chill life"


# ==============================================================================
# PERSISTENT DIALOGUE HISTORY (PREVENTING REPEATS)
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
    hist_path.write_text(json.dumps(items[-5000:], indent=2), encoding="utf-8")


# ==============================================================================
# NATURAL CONVERSATIONAL DIALOGUE GENERATOR (GEMINI)
# ==============================================================================
def _extract_json_object(raw_text):
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned, strict=False)


def _fallback_dialogue_script(history_items):
    past_titles = {h.get("topic", "") for h in history_items}
    scripts = [
        {
            "topic": "Doing Nothing Productively",
            "setting": "couch_hangout",
            "dialogue": [
                {"speaker": "B", "line": "What are you doing today?", "expr_a": "smug_eyes_closed", "expr_b": "skeptical", "gesture": "hand_point", "camera": "two_shot"},
                {"speaker": "A", "line": "Nothing.", "expr_a": "chill_smirk", "expr_b": "skeptical", "gesture": "relaxed_idle", "camera": "two_shot"},
                {"speaker": "B", "line": "Oh, let's plan something!", "expr_a": "deadpan", "expr_b": "excited_wide", "gesture": "lean_in_talk", "camera": "two_shot"},
                {"speaker": "A", "line": "No thank you.", "expr_a": "chill_smirk", "expr_b": "shocked", "gesture": "shrug_palms", "camera": "two_shot"},
                {"speaker": "B", "line": "You're gonna waste the whole day?", "expr_a": "chill_smirk", "expr_b": "skeptical", "gesture": "hand_point", "camera": "two_shot"},
                {"speaker": "A", "line": "Not at all. I'm doing nothing. Nailing it.", "expr_a": "smug_eyes_closed", "expr_b": "deadpan", "gesture": "relaxed_idle", "camera": "punchline_a"},
            ],
            "ig_caption": "Doing nothing is a full-time commitment. #wearechillclub #animatedcomedy #relatable #reels",
            "pinned_comment": "Who else has a full schedule of doing nothing this weekend?",
        },
        {
            "topic": "Checking the Bank Balance",
            "setting": "street_interview",
            "dialogue": [
                {"speaker": "B", "line": "Quick question. What's your budget this weekend?", "expr_a": "deadpan", "expr_b": "excited_wide", "gesture": "mic_hold", "camera": "two_shot"},
                {"speaker": "A", "line": "Fourteen dollars and eighty-two cents.", "expr_a": "deadpan", "expr_b": "skeptical", "gesture": "shrug_palms", "camera": "two_shot"},
                {"speaker": "B", "line": "So you're staying home and cooking?", "expr_a": "skeptical", "expr_b": "chill_smirk", "gesture": "mic_hold", "camera": "two_shot"},
                {"speaker": "A", "line": "No, I'm ordering iced coffee to think about it.", "expr_a": "chill_smirk", "expr_b": "shocked", "gesture": "hand_point", "camera": "punchline_a"},
            ],
            "ig_caption": "Financial planning at its finest. #wearechillclub #comedy #relatable #animation",
            "pinned_comment": "What is your go-to comfort order when the bank app hurts?",
        },
    ]
    for s in scripts:
        if s["topic"] not in past_titles:
            return s
    chosen = random.choice(scripts).copy()
    chosen["topic"] = f"{chosen['topic']} #{int(time.time()) % 100}"
    return chosen


def normalize_script(raw, history_items):
    if not isinstance(raw, dict) or not isinstance(raw.get("dialogue"), list) or len(raw["dialogue"]) < 4:
        return _fallback_dialogue_script(history_items)

    setting = raw.get("setting") if raw.get("setting") in ("couch_hangout", "street_interview") else "couch_hangout"
    clean_lines = []
    for idx, item in enumerate(raw["dialogue"][:8]):
        if not isinstance(item, dict):
            continue
        sp = "A" if str(item.get("speaker", "A")).strip().upper().startswith("A") else "B"
        line = " ".join(str(item.get("line") or "").strip().split())
        if not line:
            continue
        # Keep lines crisp so single-overlay subtitles stay easy to read
        words = line.split()
        if len(words) > 13:
            line = " ".join(words[:13])
        clean_lines.append({
            "speaker": sp,
            "line": line,
            "expr_a": item.get("expr_a") if item.get("expr_a") in EXPRESSIONS else "chill_smirk",
            "expr_b": item.get("expr_b") if item.get("expr_b") in EXPRESSIONS else "skeptical",
            "gesture": item.get("gesture") if item.get("gesture") in GESTURES else ("mic_hold" if setting == "street_interview" else "hand_point"),
            "camera": "punchline_a" if idx == len(raw["dialogue"][:8]) - 1 else (
                item.get("camera") if item.get("camera") in ("two_shot", "focus_a", "focus_b", "punchline_a") else "two_shot"
            ),
        })

    if len(clean_lines) < 4:
        return _fallback_dialogue_script(history_items)

    topic = str(raw.get("topic") or "Chill Banter").strip()
    return {
        "topic": topic,
        "setting": setting,
        "dialogue": clean_lines,
        "ig_caption": str(raw.get("ig_caption") or f"{topic} #wearechillclub #animatedcomedy #reels").strip(),
        "pinned_comment": str(raw.get("pinned_comment") or "Tag someone who talks just like this!").strip(),
    }


def generate_dialogue_with_gemini(page_cfg, history_items, world_context):
    past_topics = [f"- {h.get('topic', '')}" for h in history_items[-30:] if h.get("topic")]
    past_block = "\n".join(past_topics) if past_topics else "- None yet"

    prompt = (
        f"Write a hilarious, natural 15-to-24-second animated comedy conversation for {page_cfg['handle']}.\n"
        f"CHANNEL VIBE: {page_cfg['domain']}\n\n"
        "CHARACTERS:\n"
        "- Speaker A (Chill Guy): laid-back, deadpan, witty guy in a cap.\n"
        "- Speaker B (Friend): expressive, energetic friend or street interviewer.\n\n"
        "ALREADY USED TOPICS (DO NOT REPEAT):\n"
        f"{past_block}\n\n"
        "OPTIONAL TRENDING SPARK:\n"
        f"{world_context}\n\n"
        "RULES:\n"
        "1. Write 5 to 7 short, natural spoken lines (like real people talking—contractions, comedic timing, deadpan punchline).\n"
        "2. Each line MUST be 3 to 11 words so ONLY ONE clean subtitle line is needed at a time.\n"
        "3. Pick setting: either 'couch_hangout' or 'street_interview'.\n\n"
        "Return ONLY valid JSON with keys:\n"
        "- topic (short string)\n"
        "- setting ('couch_hangout' or 'street_interview')\n"
        "- dialogue (list of objects with: speaker ('A' or 'B'), line, expr_a, expr_b, gesture, camera)\n"
        "  Valid expr_a/expr_b: chill_smirk, deadpan, excited_wide, skeptical, shocked, smug_eyes_closed\n"
        "  Valid gesture: relaxed_idle, hand_point, shrug_palms, lean_in_talk, mic_hold, nod_agree\n"
        "  Valid camera: two_shot, focus_a, focus_b, punchline_a\n"
        "- ig_caption (engaging Instagram caption with 4 hashtags)\n"
        "- pinned_comment (short question to spark comments)"
    )

    for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        url = build_https_url(
            "generativelanguage.googleapis.com",
            f"/v1beta/models/{model}:generateContent",
            {"key": GEMINI_API_KEY},
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 1.0,
                "maxOutputTokens": 1800,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode())
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _extract_json_object(raw_text)
                script = normalize_script(parsed, history_items)
                print(f"Generated talking script via {model}: {script['topic']}")
                return script
        except Exception as e:
            print(f"Gemini ({model}) skipped: {e}")

    print("Using fallback conversational script.")
    return _fallback_dialogue_script(history_items)


# ==============================================================================
# REAL SPOKEN TTS + FRAME-BY-FRAME LIP-SYNC ENVELOPE
# ==============================================================================
async def _synthesize_edge_tts(text, voice, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+4%")
    await comm.save(str(out_mp3))


def _fallback_voice_wav(text, speaker, out_wav):
    sr = 48000
    dur = max(1.1, min(3.2, len(text.split()) * 0.32))
    base_f = 145.0 if speaker == "A" else 225.0
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(int(sr * dur)):
            t = i / sr
            syllable = abs(math.sin(2 * math.pi * 3.4 * t))
            tone = math.sin(2 * math.pi * (base_f + 18 * math.sin(t * 7.0)) * t)
            s = int(max(-0.85, min(0.85, tone * syllable * 0.35)) * 32767)
            buf.extend(struct.pack("<h", s))
        wf.writeframes(buf)


def build_dialogue_audio_and_lipsync(script, tmp_dir):
    sr = 48000
    timeline = []
    padded_wavs = []
    cursor = 0.25  # brief 0.25s lead-in

    # Initial silence
    lead_wav = tmp_dir / "lead.wav"
    _write_silence_wav(lead_wav, sr, cursor)
    padded_wavs.append(lead_wav)

    for idx, turn in enumerate(script["dialogue"]):
        speaker = turn["speaker"]
        voice = CHAR_A["voice"] if speaker == "A" else CHAR_B["voice"]
        mp3_path = tmp_dir / f"line_{idx}.mp3"
        raw_wav = tmp_dir / f"line_{idx}_raw.wav"
        padded_wav = tmp_dir / f"line_{idx}_pad.wav"

        try:
            asyncio.run(_synthesize_edge_tts(turn["line"], voice, mp3_path))
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", str(sr), "-ac", "1", str(raw_wav)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"TTS fallback on line {idx} ({e})")
            _fallback_voice_wav(turn["line"], speaker, raw_wav)

        with wave.open(str(raw_wav), "r") as wf:
            frames_bytes = wf.readframes(wf.getnframes())
            samples = struct.unpack(f"<{len(frames_bytes) // 2}h", frames_bytes)

        speech_dur = len(samples) / sr
        pause_after = 0.65 if idx == len(script["dialogue"]) - 1 else 0.24
        total_turn_dur = speech_dur + pause_after

        # Compute 24fps RMS mouth openness envelope
        spf = int(sr / FPS)
        mouth_env = []
        peak_rms = 1.0
        raw_rms = []
        for f in range(max(1, int(total_turn_dur * FPS))):
            s0 = f * spf
            s1 = min(len(samples), s0 + spf)
            if s1 > s0:
                chunk = samples[s0:s1]
                rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
            else:
                rms = 0.0
            raw_rms.append(rms)
            if rms > peak_rms:
                peak_rms = rms

        for rms in raw_rms:
            norm = min(1.0, (rms / max(900.0, peak_rms * 0.72)))
            mouth_env.append(0.0 if norm < 0.14 else norm)

        # Pad WAV with trailing pause so audio stays in exact lockstep
        with wave.open(str(padded_wav), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(frames_bytes + (b"\x00\x00" * int(sr * pause_after)))

        padded_wavs.append(padded_wav)
        timeline.append({
            **turn,
            "start": cursor,
            "speech_end": cursor + speech_dur,
            "end": cursor + total_turn_dur,
            "mouth_env": mouth_env,
        })
        cursor += total_turn_dur

    # Concatenate voice track
    concat_txt = tmp_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.name}'" for p in padded_wavs), encoding="utf-8")
    voice_wav = tmp_dir / "voice_all.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-ar", str(sr), "-ac", "2", str(voice_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Subtle warm chill ambient bed underneath speech
    bed_wav = tmp_dir / "bed.wav"
    chords = [[261.63, 329.63, 392.00], [220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [196.00, 246.94, 293.66]]
    bar_len = int(sr * 2.0)
    with wave.open(str(bed_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(int(sr * cursor)):
            t = i / sr
            chord = chords[(i // bar_len) % len(chords)]
            val = sum(math.sin(2 * math.pi * f * t) for f in chord) * 0.035
            s = int(max(-0.8, min(0.8, val)) * 32767)
            buf.extend(struct.pack("<hh", s, s))
        wf.writeframes(buf)

    final_wav = tmp_dir / "final_audio.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_wav),
            "-i", str(bed_wav),
            "-filter_complex", "[0:a]volume=1.18[v];[1:a]volume=0.35[b];[v][b]amix=inputs=2:duration=first[out]",
            "-map", "[out]", "-ar", str(sr), "-ac", "2", str(final_wav),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return timeline, cursor, final_wav


def _write_silence_wav(path, sr, dur):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * int(sr * dur))


# ==============================================================================
# EXPRESSIVE 2-CHARACTER ANIMATION & SINGLE-OVERLAY SUBTITLE RENDERER
# ==============================================================================
def _render_background(setting, out_bg_path):
    bw, bh = W * SS, H * SS
    ink = (18, 18, 22)

    if setting == "street_interview":
        img = Image.new("RGB", (bw, bh), (174, 218, 238))
        draw = ImageDraw.Draw(img)
        # Soft cartoon clouds
        for cx, cy, r in [(260, 320, 70), (330, 310, 85), (410, 325, 65), (780, 420, 65), (845, 412, 78)]:
            draw.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=(246, 250, 255))
        # Distant park greenery & sidewalk
        draw.rectangle([0, 1180 * SS, bw, 1340 * SS], fill=(92, 168, 94), outline=ink, width=6 * SS)
        draw.rectangle([0, 1340 * SS, bw, bh], fill=(198, 202, 208), outline=ink, width=6 * SS)
        # Curb stripes
        for idx, x in enumerate(range(0, W, 180)):
            col = (34, 36, 40) if idx % 2 == 0 else (245, 245, 245)
            draw.rectangle([x * SS, 1340 * SS, (x + 180) * SS, 1378 * SS], fill=col, outline=ink, width=4 * SS)
    else:
        # Cozy living room couch setup (inspired by video_4.mp4)
        img = Image.new("RGB", (bw, bh), (218, 204, 184))
        draw = ImageDraw.Draw(img)
        # Framed wall art
        draw.rectangle([90 * SS, 330 * SS, 360 * SS, 650 * SS], fill=(154, 178, 152), outline=ink, width=7 * SS)
        # Bookshelf on right
        draw.rectangle([820 * SS, 440 * SS, bw, 1180 * SS], fill=(156, 114, 78), outline=ink, width=7 * SS)
        for sy in (620, 800, 980):
            draw.line([(820 * SS, sy * SS), (bw, sy * SS)], fill=ink, width=7 * SS)
        # Floor & rug
        draw.rectangle([0, 1160 * SS, bw, bh], fill=(176, 138, 102), outline=ink, width=7 * SS)
        draw.polygon(
            [(80 * SS, 1320 * SS), (960 * SS, 1320 * SS), (1040 * SS, 1560 * SS), (20 * SS, 1560 * SS)],
            fill=(232, 224, 210),
            outline=ink,
        )
        # Cozy green sofa
        draw.rounded_rectangle([110 * SS, 740 * SS, 920 * SS, 1260 * SS], radius=45 * SS, fill=(134, 154, 108), outline=ink, width=8 * SS)
        draw.rounded_rectangle([160 * SS, 1010 * SS, 870 * SS, 1180 * SS], radius=30 * SS, fill=(148, 168, 120), outline=ink, width=7 * SS)

    img.resize((W, H), Image.Resampling.LANCZOS).save(out_bg_path, format="PNG")


def _draw_mouth(draw, hx, hy, scale, expr, mouth_open):
    ink = (18, 18, 22)
    mw = int(26 * scale * SS)
    if mouth_open > 0.12:
        mh = int((8 + 26 * mouth_open) * scale * SS)
        draw.ellipse(
            [hx - mw, hy + int(22 * scale * SS), hx + mw, hy + int(22 * scale * SS) + mh],
            fill=(165, 52, 58),
            outline=ink,
            width=max(4 * SS, int(5 * scale * SS)),
        )
        # Tongue/teeth hint when wide open
        if mouth_open > 0.45:
            draw.chord(
                [hx - mw + 4 * SS, hy + int(24 * scale * SS), hx + mw - 4 * SS, hy + int(22 * scale * SS) + mh],
                start=15,
                end=165,
                fill=(235, 115, 120),
            )
    else:
        if expr in ("chill_smirk", "smug_eyes_closed", "excited_wide"):
            draw.arc(
                [hx - int(24 * scale * SS), hy + int(18 * scale * SS), hx + int(26 * scale * SS), hy + int(44 * scale * SS)],
                start=10,
                end=170,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        elif expr == "shocked":
            draw.ellipse(
                [hx - int(12 * scale * SS), hy + int(24 * scale * SS), hx + int(12 * scale * SS), hy + int(46 * scale * SS)],
                fill=(165, 52, 58),
                outline=ink,
                width=max(4 * SS, int(5 * scale * SS)),
            )
        else:
            draw.line(
                [(hx - int(20 * scale * SS), hy + int(34 * scale * SS)), (hx + int(20 * scale * SS), hy + int(32 * scale * SS))],
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )


def _draw_eyes(draw, hx, hy, scale, expr, t, look_dir=1):
    ink = (18, 18, 22)
    eye_dx = int(32 * scale * SS)
    eye_y = hy - int(10 * scale * SS)
    er = int(20 * scale * SS)
    blinking = ((t + (0.9 if look_dir < 0 else 0.0)) % 3.1) < 0.11
    px_off = int(5 * look_dir * scale * SS)

    if expr == "smug_eyes_closed" or blinking:
        for side in (-1, 1):
            ex = hx + side * eye_dx
            draw.arc(
                [ex - er, eye_y - int(8 * scale * SS), ex + er, eye_y + int(12 * scale * SS)],
                start=10,
                end=170,
                fill=ink,
                width=max(4 * SS, int(6 * scale * SS)),
            )
        return

    for side in (-1, 1):
        ex = hx + side * eye_dx
        draw.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(254, 254, 255), outline=ink, width=max(4 * SS, int(5 * scale * SS)))
        draw.ellipse([ex - 6 * SS + px_off, eye_y - 6 * SS, ex + 6 * SS + px_off, eye_y + 6 * SS], fill=ink)
        if expr in ("deadpan", "skeptical"):
            draw.pieslice(
                [ex - er, eye_y - er, ex + er, eye_y + er],
                start=180,
                end=360,
                fill=(246, 243, 238),
                outline=ink,
                width=max(4 * SS, int(5 * scale * SS)),
            )
        # Expressive eyebrows
        brow_tilt = -6 * side * SS if expr == "skeptical" else (5 * side * SS if expr == "excited_wide" else 0)
        draw.line(
            [(ex - er, eye_y - er - 10 * SS - brow_tilt), (ex + er, eye_y - er - 10 * SS + brow_tilt)],
            fill=ink,
            width=max(4 * SS, int(6 * scale * SS)),
        )


def _draw_character_pair(draw, setting, expr_a, expr_b, gesture, active_speaker, mouth_open, t):
    ink = (18, 18, 22)
    limb_w = 8 * SS

    # Character A (Left - Chill Guy in cap)
    bob_a = int(math.sin(t * (7.5 if active_speaker == "A" and mouth_open > 0.1 else 2.2)) * 5)
    ax, ay = 340, (860 if setting == "couch_hangout" else 840) + bob_a
    scale_a = 0.96

    # Body A
    ahx, ahy = ax * SS, ay * SS
    arx, ary = int(96 * scale_a * SS), int(96 * scale_a * SS)
    aneck_y = ahy + ary - 4 * SS
    ahip_y = aneck_y + int(190 * scale_a * SS)
    draw.rounded_rectangle(
        [ahx - 58 * SS, aneck_y, ahx + 58 * SS, ahip_y],
        radius=28 * SS,
        fill=CHAR_A["shirt_color"],
        outline=ink,
        width=7 * SS,
    )
    # Legs A
    for side in (-1, 1):
        draw.line([(ahx + side * 26 * SS, ahip_y), (ahx + side * 30 * SS, ahip_y + 190 * SS)], fill=ink, width=limb_w)
    # Arms A
    gest_a = int(math.sin(t * 8.0) * 18 * SS) if (active_speaker == "A" and gesture in ("hand_point", "shrug_palms")) else 0
    draw.line([(ahx - 54 * SS, aneck_y + 30 * SS), (ahx - 86 * SS, aneck_y + 110 * SS), (ahx - 66 * SS, aneck_y + 165 * SS)], fill=ink, width=limb_w)
    draw.line([(ahx + 54 * SS, aneck_y + 30 * SS), (ahx + 98 * SS, aneck_y + 85 * SS - gest_a), (ahx + 132 * SS, aneck_y + 55 * SS - gest_a)], fill=ink, width=limb_w)

    # Head A + Cap
    draw.ellipse([ahx - arx, ahy - ary, ahx + arx, ahy + ary], fill=CHAR_A["head_fill"], outline=ink, width=8 * SS)
    draw.pieslice([ahx - arx, ahy - ary - 10 * SS, ahx + arx, ahy - int(ary * 0.12)], start=180, end=360, fill=CHAR_A["cap_color"], outline=ink, width=7 * SS)
    draw.rounded_rectangle([ahx - 8 * SS, ahy - int(ary * 0.56), ahx + int(arx * 1.32), ahy - int(ary * 0.34)], radius=8 * SS, fill=CHAR_A["cap_color"], outline=ink, width=6 * SS)
    _draw_eyes(draw, ahx, ahy, scale_a, expr_a, t, look_dir=1)
    _draw_mouth(draw, ahx, ahy, scale_a, expr_a, mouth_open if active_speaker == "A" else 0.0)

    # Character B (Right - Friend / Interviewer)
    bob_b = int(math.sin(t * (7.5 if active_speaker == "B" and mouth_open > 0.1 else 2.4) + 1.0) * 5)
    bx, by = 735, (855 if setting == "couch_hangout" else 840) + bob_b
    scale_b = 0.96
    bhx, bhy = bx * SS, by * SS
    brx, bry = int(94 * scale_b * SS), int(94 * scale_b * SS)
    bneck_y = bhy + bry - 4 * SS
    bhip_y = bneck_y + int(190 * scale_b * SS)

    # Hair bun + head B
    draw.ellipse([bhx + brx - 24 * SS, bhy - bry + 4 * SS, bhx + brx + 36 * SS, bhy - bry + 64 * SS], fill=CHAR_B["hair_color"], outline=ink, width=6 * SS)
    draw.rounded_rectangle(
        [bhx - 54 * SS, bneck_y, bhx + 54 * SS, bhip_y],
        radius=28 * SS,
        fill=CHAR_B["dress_color"],
        outline=ink,
        width=7 * SS,
    )
    for side in (-1, 1):
        draw.line([(bhx + side * 24 * SS, bhip_y), (bhx + side * 28 * SS, bhip_y + 190 * SS)], fill=ink, width=limb_w)

    # Arms B (holds microphone toward A in street_interview mode!)
    if setting == "street_interview":
        mic_tip = (ahx + 150 * SS, ahy + 45 * SS)
        draw.line([(bhx - 50 * SS, bneck_y + 30 * SS), (bhx - 130 * SS, bneck_y + 50 * SS), mic_tip], fill=ink, width=limb_w)
        # Handheld microphone
        draw.line([mic_tip, (mic_tip[0] - 28 * SS, mic_tip[1] - 24 * SS)], fill=(50, 54, 62), width=14 * SS)
        draw.ellipse([mic_tip[0] - 46 * SS, mic_tip[1] - 42 * SS, mic_tip[0] - 14 * SS, mic_tip[1] - 10 * SS], fill=(80, 84, 92), outline=ink, width=4 * SS)
    else:
        gest_b = int(math.sin(t * 8.0) * 18 * SS) if active_speaker == "B" else 0
        draw.line([(bhx - 50 * SS, bneck_y + 30 * SS), (bhx - 105 * SS, bneck_y + 75 * SS - gest_b), (bhx - 138 * SS, bneck_y + 45 * SS - gest_b)], fill=ink, width=limb_w)
    draw.line([(bhx + 50 * SS, bneck_y + 30 * SS), (bhx + 82 * SS, bneck_y + 115 * SS), (bhx + 62 * SS, bneck_y + 165 * SS)], fill=ink, width=limb_w)

    draw.ellipse([bhx - brx, bhy - bry, bhx + brx, bhy + bry], fill=CHAR_B["head_fill"], outline=ink, width=8 * SS)
    draw.pieslice([bhx - brx, bhy - bry - 6 * SS, bhx + brx, bhy - int(bry * 0.15)], start=180, end=360, fill=CHAR_B["hair_color"], outline=ink, width=7 * SS)
    _draw_eyes(draw, bhx, bhy, scale_b, expr_b, t, look_dir=-1)
    _draw_mouth(draw, bhx, bhy, scale_b, expr_b, mouth_open if active_speaker == "B" else 0.0)


def _load_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_single_synchronized_caption(frame, turn, t, page_cfg):
    """Renders ONLY ONE clean synchronized text overlay (zero top banner or beat badges)."""
    rgba = frame.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Subtle watermark handle
    odraw.text(
        (W // 2, 1655),
        page_cfg["handle"],
        font=_load_font(26),
        fill=(255, 255, 255, 195),
        anchor="mm",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 180),
    )

    if not turn or t > turn["speech_end"] + 0.12:
        return Image.alpha_composite(rgba, overlay).convert("RGB")

    line = turn["line"]
    words = line.split()
    speech_dur = max(0.25, turn["speech_end"] - turn["start"])
    progress = max(0.0, min(0.999, (t - turn["start"]) / speech_dur))
    active_word_idx = int(progress * len(words))

    acc = tuple(page_cfg.get("accent_color", (255, 225, 45)))
    font = _load_font(52)

    # Wrap into at most 2 clean lines centered in lower-middle safe zone
    wrapped_lines = textwrap.wrap(line, width=24)[:2]
    word_counter = 0
    base_y = 1430 if len(wrapped_lines) == 1 else 1395

    for row_i, row_text in enumerate(wrapped_lines):
        row_words = row_text.split()
        space_w = odraw.textbbox((0, 0), " ", font=font)[2]
        word_boxes = [odraw.textbbox((0, 0), w, font=font) for w in row_words]
        total_w = sum((b[2] - b[0]) for b in word_boxes) + space_w * max(0, len(row_words) - 1)
        cur_x = (W - total_w) // 2
        cur_y = base_y + row_i * 68

        for w_i, w in enumerate(row_words):
            is_active = (word_counter == active_word_idx)
            fill_col = (acc[0], acc[1], acc[2], 255) if is_active else (255, 255, 255, 255)
            odraw.text(
                (cur_x, cur_y),
                w,
                font=font,
                fill=fill_col,
                anchor="la",
                stroke_width=7,
                stroke_fill=(14, 16, 20, 250),
            )
            cur_x += (word_boxes[w_i][2] - word_boxes[w_i][0]) + space_w
            word_counter += 1

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def apply_camera_framing(img, camera_mode, turn_p):
    eased = 1.0 - pow(1.0 - max(0.0, min(1.0, turn_p)), 3)
    if camera_mode == "punchline_a":
        zoom = 1.04 + 0.24 * eased
        cx, cy = int(W * 0.36), int(H * 0.50)
    elif camera_mode == "focus_a":
        zoom = 1.12
        cx, cy = int(W * 0.40), int(H * 0.50)
    elif camera_mode == "focus_b":
        zoom = 1.12
        cx, cy = int(W * 0.60), int(H * 0.50)
    else:
        zoom = 1.02 + 0.03 * eased
        cx, cy = W // 2, H // 2

    cw, ch = int(W / zoom), int(H / zoom)
    x0 = max(0, min(W - cw, cx - cw // 2))
    y0 = max(0, min(H - ch, cy - ch // 2))
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)


def render_talking_reel(page_cfg, script, out_mp4):
    tmp_dir = pathlib.Path(f"tmp_{page_cfg['slug']}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        timeline, total_dur, final_wav = build_dialogue_audio_and_lipsync(script, tmp_dir)
        bg_path = tmp_dir / "bg.png"
        _render_background(script["setting"], bg_path)
        bg_img = Image.open(bg_path).convert("RGB")

        total_frames = int(total_dur * FPS)
        for f_idx in range(total_frames):
            t = f_idx / FPS
            active_turn = None
            for turn in timeline:
                if turn["start"] <= t < turn["end"]:
                    active_turn = turn
                    break

            if active_turn:
                local_f = min(len(active_turn["mouth_env"]) - 1, max(0, int((t - active_turn["start"]) * FPS)))
                mouth_open = active_turn["mouth_env"][local_f]
                speaker = active_turn["speaker"]
                expr_a = active_turn["expr_a"]
                expr_b = active_turn["expr_b"]
                gesture = active_turn["gesture"]
                camera = active_turn["camera"]
                turn_p = (t - active_turn["start"]) / max(0.1, active_turn["end"] - active_turn["start"])
            else:
                mouth_open = 0.0
                speaker = "A"
                expr_a = "chill_smirk"
                expr_b = "chill_smirk"
                gesture = "relaxed_idle"
                camera = "two_shot"
                turn_p = 0.0

            stage_hi = bg_img.resize((W * SS, H * SS), Image.Resampling.BILINEAR)
            draw = ImageDraw.Draw(stage_hi)
            _draw_character_pair(draw, script["setting"], expr_a, expr_b, gesture, speaker, mouth_open, t)
            frame = stage_hi.resize((W, H), Image.Resampling.LANCZOS)
            frame = apply_camera_framing(frame, camera, turn_p)
            frame = ImageEnhance.Contrast(frame).enhance(1.03)
            frame = draw_single_synchronized_caption(frame, active_turn, t, page_cfg)
            frame.save(tmp_dir / f"frame_{f_idx:04d}.png", format="PNG")

        subprocess.run(
            [
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
            ],
            check=True,
        )
        print(f"Rendered {total_dur:.1f}s talking Reel -> {out_mp4}")
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


# ==============================================================================
# GITHUB PAGES ARCHIVE + INSTAGRAM REELS PUBLISHING
# ==============================================================================
def archive_and_get_pages_url(rel_path):
    subprocess.run(["git", "config", "user.name", "Meme-Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "posts/"], check=True)
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Publish Reel {rel_path}"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)

    owner, repo = REPO_NAME.split("/", 1)
    pages_url = build_https_url(f"{owner.lower()}.github.io", f"/{repo}/{rel_path}")
    for attempt in range(1, 25):
        time.sleep(5)
        try:
            req = urllib.request.Request(pages_url, headers={"User-Agent": "facebookexternalhit/1.1"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200 and ("video/" in ctype or "octet-stream" in ctype):
                    print(f"GitHub Pages video live: {pages_url}")
                    return pages_url
        except Exception as e:
            print(f"Waiting for GitHub Pages ({attempt}/24): {e}")
    raise RuntimeError(f"GitHub Pages did not serve MP4 in time: {pages_url}")


def post_request(url, params):
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Meta API {e.code} on {url}: {e.read().decode('utf-8', errors='replace')}") from e


def publish_to_instagram(ig_id, token, video_url, caption, pinned_comment=""):
    if not token:
        raise RuntimeError("Missing IG_ACCESS_TOKEN secret in GitHub Actions.")
    if not ig_id:
        raise RuntimeError("Missing IG_USER_ID.")

    media_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{ig_id}/media")
    container = post_request(
        media_url,
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
    )
    creation_id = container["id"]
    print(f"Created IG media container: {creation_id}")

    for attempt in range(1, 31):
        time.sleep(5)
        status_url = build_https_url(
            "graph.facebook.com",
            f"/{GRAPH_VERSION}/{creation_id}",
            {"fields": "status_code,status", "access_token": token},
        )
        status_data = json.loads(urllib.request.urlopen(status_url, timeout=15).read().decode())
        code = status_data.get("status_code")
        print(f"IG Reel status ({attempt}/30): {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram Reel container failed: {status_data}")
    else:
        raise RuntimeError(f"Instagram Reel container timed out: {creation_id}")

    publish_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{ig_id}/media_publish")
    published = post_request(publish_url, {"creation_id": creation_id, "access_token": token})
    media_id = published["id"]
    print(f"LIVE ON INSTAGRAM ({ig_id})! Media ID: {media_id}")

    if pinned_comment:
        try:
            comment_url = build_https_url("graph.facebook.com", f"/{GRAPH_VERSION}/{media_id}/comments")
            post_request(comment_url, {"message": pinned_comment, "access_token": token})
        except Exception as e:
            print(f"Comment skipped ({e}); Reel is already live.")


if __name__ == "__main__":
    verify_runtime_environment()
    est = timezone(timedelta(hours=-5))
    now_est = datetime.now(est)
    world_context = fetch_world_context()
    publish_enabled = os.environ.get("PUBLISH_TO_IG", "true").strip().lower() not in ("0", "false", "no")

    for page in load_active_pages():
        slug = page["slug"]
        history_items = load_story_history(slug, limit=80)
        script = generate_dialogue_with_gemini(page, history_items, world_context)

        stamp = now_est.strftime("%Y-%m-%d_%H%M")
        out_dir = pathlib.Path("posts") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        rel_mp4 = f"posts/{slug}/reel_{stamp}.mp4"
        out_dir.joinpath(f"story_{stamp}.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

        save_story_record(slug, {
            "timestamp": stamp,
            "topic": script["topic"],
            "setting": script["setting"],
            "lines": [d["line"] for d in script["dialogue"]],
        })

        render_talking_reel(page, script, rel_mp4)

        if publish_enabled:
            token = os.environ.get(page.get("token_secret", "IG_ACCESS_TOKEN"), "").strip()
            ig_id = (page.get("ig_user_id") or os.environ.get("IG_USER_ID") or DEFAULT_IG_USER_ID).strip()
            public_url = archive_and_get_pages_url(rel_mp4)
            publish_to_instagram(ig_id, token, public_url, script["ig_caption"], script.get("pinned_comment", ""))
