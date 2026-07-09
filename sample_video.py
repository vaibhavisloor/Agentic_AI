#!/usr/bin/env python3
"""
Legends of Bharat — v1 single-video generator (local)
=====================================================
LLM picks an Indian history/monument topic -> Hindi script -> AI images ->
Hindi neural voice (word-timed) -> animated captions -> Ken Burns assembly.

Usage:
    export GEMINI_API_KEY=...          (Windows: set GEMINI_API_KEY=...)
    python make_video.py               # full run
    python make_video.py --dry-run     # no API key needed: placeholder visuals,
                                       # real TTS if online (else synthetic audio)
    python make_video.py --veo         # replace scene 1 visual with a Veo clip
                                       # (PAID: needs billing on your key, ~Rs.100/clip)
    python make_video.py --voice hi-IN-SwaraNeural   # female voice

Deps: pip install -r requirements.txt   +   ffmpeg on PATH
Output: out/<topic>.mp4 + out/<topic>.json (title/caption/hashtags for upload later)
"""

try:
    from dotenv import load_dotenv   # reads GEMINI_API_KEY from a local .env
    load_dotenv()
except ImportError:
    pass                             # dotenv optional; env var works either way

import argparse, asyncio, json, math, os, re, shutil, subprocess, sys, time
import urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

# ----------------------------- config ---------------------------------------

TEXT_MODEL  = "gemini-2.5-flash"        # swap to a gemini-3 model if your key has it
IMAGE_MODEL = "gemini-2.5-flash-image"  # "nano banana"
VEO_MODEL   = "veo-3.1-fast-generate-preview"  # check ai.google.dev/models for current id
VOICE       = "hi-IN-MadhurNeural"      # male; hi-IN-SwaraNeural = female
TTS_RATE    = "+6%"                     # slightly faster pacing for shorts

W, H, FPS   = 1080, 1920, 30
FONT_URL    = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
               "notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf")
FONT_FILE   = "NotoSansDevanagari.ttf"
FONT_NAME   = "Noto Sans Devanagari"

ROOT     = Path(__file__).resolve().parent
OUT_DIR  = ROOT / "out"
HISTORY  = ROOT / "topics_history.json"

PLAN_PROMPT = """आप एक वायरल यूट्यूब शॉर्ट्स स्क्रिप्ट राइटर हैं। चैनल: "Legends of Bharat" — भारत का इतिहास।

काम: भारत के इतिहास से एक कम-प्रसिद्ध लेकिन रोमांचक विषय चुनिए — कोई ऐतिहासिक घटना, पुराना स्मारक, खोया हुआ शहर, या किसी राजवंश की कहानी। इन विषयों से बचें (पहले बन चुके हैं): {avoid}

फिर 35-45 सेकंड की हिंदी स्क्रिप्ट लिखिए:
- 5 से 6 सीन, हर सीन में 12-22 शब्द, कुल 90-110 शब्द
- पहला सीन एक ज़बरदस्त हुक हो — चौंकाने वाला सवाल या तथ्य
- आखिरी सीन में हल्का सा सस्पेंस या सोचने वाली बात छोड़िए
- भाषा: सरल, बोलचाल की हिंदी, कहानी सुनाने वाला अंदाज़। अंक देवनागरी में नहीं, साधारण (1526) लिखें।
- केवल प्रमाणित ऐतिहासिक तथ्य। कोई मनगढ़ंत बात नहीं।

हर सीन के लिए एक image_prompt भी दीजिए (अंग्रेज़ी में): cinematic, photorealistic, vertical 9:16 composition, ancient/medieval India aesthetic, dramatic lighting, no text, no watermark, no maps with borders.

सिर्फ़ यह JSON लौटाइए (कोई और टेक्स्ट नहीं):
{{
  "topic_en": "short-english-slug",
  "title_hi": "यूट्यूब शीर्षक (हुक वाला, 60 अक्षर तक)",
  "scenes": [
    {{"narration_hi": "...", "image_prompt": "..."}}
  ],
  "caption_hi": "2 लाइन का description",
  "hashtags": ["#इतिहास", "..."]
}}"""

DRY_PLAN = {
    "topic_en": "taj-mahal-black-legend",
    "title_hi": "ताज महल का काला जुड़वां — सच या झूठ?",
    "scenes": [
        {"narration_hi": "क्या आप जानते हैं ताज महल के सामने एक काला ताज महल भी बनने वाला था?",
         "image_prompt": "Taj Mahal at dawn, river view, cinematic"},
        {"narration_hi": "कहा जाता है शाहजहाँ यमुना के उस पार अपने लिए काले संगमरमर का मकबरा चाहता था।",
         "image_prompt": "black marble palace concept across river, night"},
        {"narration_hi": "महताब बाग़ में मिली काली दीवारों को लोग उसी अधूरे सपने का सबूत मानते थे।",
         "image_prompt": "ruins in Mehtab Bagh garden, archaeology"},
        {"narration_hi": "लेकिन खुदाई में पता चला वे दीवारें काई से काली पड़ी थीं, पत्थर सफ़ेद ही था।",
         "image_prompt": "excavation site, moss covered white stones"},
        {"narration_hi": "तो क्या यह सिर्फ़ एक किंवदंती थी, या इतिहास ने कुछ छुपा लिया? आप क्या मानते हैं?",
         "image_prompt": "mysterious silhouette of Taj Mahal at dusk"},
    ],
    "caption_hi": "काले ताज महल की कहानी — मिथक या अधूरा सपना?",
    "hashtags": ["#इतिहास", "#TajMahal", "#LegendsOfBharat"],
}

# ----------------------------- helpers --------------------------------------

def sh(cmd, cwd=None):
    """Run a command, raise with stderr on failure."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(map(str, cmd))}\n{p.stderr[-2000:]}")
    return p.stdout

def ffprobe_duration(path):
    out = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())

def ensure_font(dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / FONT_FILE
    cached = ROOT / "fonts" / FONT_FILE
    if not cached.exists():
        cached.parent.mkdir(exist_ok=True)
        print("  downloading Devanagari font (one-time)...")
        urllib.request.urlretrieve(FONT_URL, cached)
    shutil.copy(cached, target)

def load_history():
    if HISTORY.exists():
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    return []

def save_history(topic):
    hist = load_history()
    hist.append({"topic": topic, "at": datetime.now().isoformat(timespec="seconds")})
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_json_loose(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)

def preflight(dry_run):
    """Verify local dependencies BEFORE any API call — nothing gets spent."""
    problems = []
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        problems.append(
            "ffmpeg/ffprobe not found on PATH.\n"
            "      Windows : winget install Gyan.FFmpeg   "
            "(then CLOSE and REOPEN the terminal)\n"
            "      verify  : ffmpeg -version")
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        msg = ("edge-tts not installed in this Python environment.\n"
               "      uv  : uv pip install edge-tts\n"
               "      pip : python -m pip install edge-tts")
        if dry_run:
            print("  note: edge-tts missing -> dry-run will use synthetic audio")
        else:
            problems.append(msg)
    if problems:
        sys.exit("\nPreflight failed — fix these first (no API calls were made):\n"
                 + "\n".join(f"  - {p}" for p in problems))

# ----------------------------- step 1: plan ---------------------------------

_NARR_KEYS = ["narration_hi", "narration", "narration_hindi", "voiceover_hi",
              "voiceover", "script_hi", "script", "text"]
_IMG_KEYS  = ["image_prompt", "imagePrompt", "visual_prompt", "image", "prompt",
              "visual"]

def _pick(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _normalize_plan(plan):
    """Canonicalize scene keys even if the model drifted, then validate hard."""
    scenes = []
    for i, s in enumerate(plan.get("scenes") or []):
        narr, img = _pick(s, _NARR_KEYS), _pick(s, _IMG_KEYS)
        if not narr or not img:
            raise ValueError(f"scene {i+1} missing narration/image_prompt: {s}")
        scenes.append({"narration_hi": narr, "image_prompt": img})
    if not (3 <= len(scenes) <= 8):
        raise ValueError(f"expected 3-8 scenes, got {len(scenes)}")
    plan["scenes"] = scenes
    for k in ("topic_en", "title_hi", "caption_hi"):
        if not isinstance(plan.get(k), str) or not plan[k].strip():
            raise ValueError(f"plan missing '{k}'")
    plan.setdefault("hashtags", ["#इतिहास", "#LegendsOfBharat"])
    return plan

def make_plan(client):
    avoid = ", ".join(h["topic"] for h in load_history()[-15:]) or "—"
    from google.genai import types
    from pydantic import BaseModel

    class Scene(BaseModel):
        narration_hi: str
        image_prompt: str

    class Plan(BaseModel):
        topic_en: str
        title_hi: str
        scenes: list[Scene]
        caption_hi: str
        hashtags: list[str]

    resp = client.models.generate_content(
        model=TEXT_MODEL,
        contents=PLAN_PROMPT.format(avoid=avoid),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Plan,           # enforced: exact keys, guaranteed
            temperature=1.0),
    )
    plan = None
    parsed = getattr(resp, "parsed", None)
    if parsed is not None:                  # SDK returns a Pydantic instance
        plan = parsed.model_dump()
    if plan is None:                        # older SDK fallback
        plan = parse_json_loose(resp.text)
    return _normalize_plan(plan)            # validate BEFORE spending on images

# ----------------------------- step 2: images -------------------------------

def cover_crop(img_path):
    """Normalize any image to exactly 1080x1920 (cover-crop)."""
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    scale = max(W / im.width, H / im.height)
    im = im.resize((math.ceil(im.width * scale), math.ceil(im.height * scale)),
                   Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im.crop((x, y, x + W, y + H)).save(img_path, quality=92)

def gen_image_gemini(client, prompt, path):
    from google.genai import types
    cfg = None
    try:
        cfg = types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio="9:16"))
    except Exception:
        pass  # older SDK: fall back to prompt-only aspect hint
    resp = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=f"{prompt}. Vertical 9:16 portrait composition.",
        config=cfg)
    for part in resp.candidates[0].content.parts:
        data = getattr(part, "inline_data", None)
        if data and data.data:
            Path(path).write_bytes(data.data)
            return True
    return False

def gen_image_pollinations(prompt, path):
    import requests
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt) + f"?width={W}&height={H}&nologo=true")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    Path(path).write_bytes(r.content)
    return True

def make_images(client, plan, build):
    paths = []
    for i, sc in enumerate(plan["scenes"]):
        p = build / f"img_{i}.jpg"
        print(f"  image {i+1}/{len(plan['scenes'])}...")
        ok = False
        try:
            ok = gen_image_gemini(client, sc["image_prompt"], p)
        except Exception as e:
            print(f"    gemini image failed ({e}); trying pollinations fallback")
        if not ok:
            gen_image_pollinations(sc["image_prompt"], p)
        cover_crop(p)
        paths.append(p)
    return paths

def make_placeholder_images(plan, build):
    """--dry-run visuals: gradient cards so the assembly path is identical."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(ROOT / "fonts" / FONT_FILE), 54)
    colors = [(30,34,68),(72,38,38),(28,60,48),(70,52,22),(50,30,66),(24,50,70)]
    paths = []
    for i, sc in enumerate(plan["scenes"]):
        c = colors[i % len(colors)]
        im = Image.new("RGB", (W, H))
        for y in range(H):  # vertical gradient
            k = y / H
            im.paste(tuple(int(v * (0.45 + 0.9 * k)) for v in c), (0, y, W, y + 1))
        d = ImageDraw.Draw(im)
        d.text((W//2, H//2 - 260), f"SCENE {i+1}", anchor="mm",
               font=ImageFont.truetype(str(ROOT/"fonts"/FONT_FILE), 90), fill=(255,255,255))
        d.text((W//2, H//2 - 120), "(placeholder — real run uses AI images)",
               anchor="mm", font=font, fill=(220,220,220))
        p = build / f"img_{i}.jpg"
        im.save(p, quality=90)
        paths.append(p)
    return paths

# ----------------------------- step 3: voice + timings ----------------------

async def _edge_tts(text, voice, mp3_path):
    import edge_tts
    words, sents = [], []
    comm = edge_tts.Communicate(text, voice, rate=TTS_RATE)
    with open(mp3_path, "wb") as f:
        async for ch in comm.stream():
            t = ch.get("type")
            if t == "audio" and ch.get("data"):
                f.write(ch["data"])
            elif t in ("WordBoundary", "SentenceBoundary"):
                item = {"t": ch["offset"] / 1e7,
                        "d": ch["duration"] / 1e7,
                        "w": ch.get("text", "")}
                (words if t == "WordBoundary" else sents).append(item)
    return words, sents

def estimate_word_timings(full_text, sents, total_dur):
    """Service sent no word metadata: interpolate from sentence boundaries,
    or spread words evenly across the measured audio duration."""
    if sents:
        out = []
        for s in sents:
            ws = s["w"].split()
            if not ws:
                continue
            step = (s["d"] / len(ws)) if s["d"] > 0 else 0.3
            out += [{"t": s["t"] + i * step, "d": step * 0.9, "w": w}
                    for i, w in enumerate(ws)]
        if out:
            return out
    ws = full_text.split()
    step = max(total_dur - 0.4, 1.0) / max(len(ws), 1)
    return [{"t": i * step, "d": step * 0.9, "w": w} for i, w in enumerate(ws)]

def synth_fallback_audio(plan, build):
    """Offline fallback: gentle tone + evenly spaced word timings."""
    all_words = " ".join(s["narration_hi"] for s in plan["scenes"]).split()
    dur = max(18.0, len(all_words) * 0.42)
    mp3 = build / "voice.mp3"
    sh(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=520:duration={dur:.2f}",
        "-af", "volume=0.15", str(mp3)])
    step = dur / len(all_words)
    words = [{"t": i * step, "d": step * 0.9, "w": w} for i, w in enumerate(all_words)]
    return mp3, words, dur

def make_voice(plan, build, voice, dry_run=False):
    text = " ".join(s["narration_hi"].strip() for s in plan["scenes"])
    mp3 = build / "voice.mp3"
    last_err = None
    for attempt in (1, 2):
        try:
            words, sents = asyncio.run(_edge_tts(text, voice, mp3))
            if not mp3.exists() or mp3.stat().st_size < 1024:
                raise RuntimeError("empty audio returned by edge-tts")
            dur = ffprobe_duration(mp3)
            if words:
                print(f"  voice ok: {dur:.1f}s, {len(words)} word timings")
                return mp3, words, dur
            # audio is real, metadata is missing -> degrade, don't die
            words = estimate_word_timings(text, sents, dur)
            src = ("interpolated from sentence boundaries" if sents
                   else "estimated by even spread")
            print(f"  voice ok: {dur:.1f}s — service sent no word metadata; "
                  f"caption timings {src}")
            return mp3, words, dur
        except Exception as e:
            last_err = e
            if attempt == 1:
                print(f"  attempt 1 failed ({e}); retrying in 3s...")
                time.sleep(3)
    if dry_run:   # synthetic audio exists ONLY to test assembly offline
        print(f"  edge-tts unavailable ({last_err}) -> synthetic audio fallback")
        return synth_fallback_audio(plan, build)
    raise RuntimeError(
        f"voice generation failed after 2 attempts: {last_err}\n"
        f"  Diagnose in 15s:\n"
        f'    edge-tts --voice {voice} --text "नमस्ते दुनिया" '
        f"--write-media t.mp3 --write-subtitles t.srt\n"
        f"  (t.mp3 plays but t.srt is empty = service metadata issue, rerun later)\n"
        f"  Also worth: uv pip install -U edge-tts"
    ) from last_err

def scene_boundaries(plan, words, total_dur):
    """Start time of each scene, from word timings (proportional fallback)."""
    counts = [len(s["narration_hi"].split()) for s in plan["scenes"]]
    total_words = sum(counts)
    starts, cum = [], 0
    for c in counts:
        if cum == 0:
            starts.append(0.0)
        elif len(words) == total_words:            # exact mapping
            starts.append(words[cum]["t"])
        else:                                       # proportional mapping
            starts.append(total_dur * (cum / total_words))
        cum += c
    ends = starts[1:] + [total_dur + 0.35]          # tiny tail pad
    return list(zip(starts, ends))

# ----------------------------- step 4: captions -----------------------------

def fmt_ass_time(t):
    cs = int(round(t * 100))
    return f"{cs//360000}:{(cs//6000)%60:02d}:{(cs//100)%60:02d}.{cs%100:02d}"

def build_ass(words, total_dur, path):
    """2-3 word chunks, pop-in style, Devanagari-safe."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT_NAME},80,&H00FFFFFF,&H0000FFFF,&H00101010,&H96000000,1,0,0,0,100,100,0,0,1,6,2,2,60,60,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines, i, CH = [], 0, 3
    while i < len(words):
        chunk = words[i:i + CH]
        start = chunk[0]["t"]
        end = words[i + CH]["t"] if i + CH < len(words) else min(
            chunk[-1]["t"] + chunk[-1]["d"] + 0.30, total_dur)
        end = max(end, start + 0.35)
        txt = " ".join(w["w"] for w in chunk)
        lines.append(f"Dialogue: 0,{fmt_ass_time(start)},{fmt_ass_time(end)},"
                     f"Cap,,0,0,0,,{{\\fad(60,40)}}{txt}")
        i += CH
    Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

# ----------------------------- step 5: assembly -----------------------------

def ken_burns_clip(img, dur, idx, out_path, frames):
    """Zoom-in on even scenes, slow lateral pan on odd — variety, low risk."""
    if idx % 2 == 0:
        zexpr = "min(zoom+0.0011,1.15)"
        xexpr, yexpr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        zexpr = "1.09"
        xexpr = f"(iw-iw/zoom)*(on/{max(frames-1,1)})"
        yexpr = "ih/2-(ih/zoom/2)"
    vf = (f"scale={W*2}:{H*2},"
          f"zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}'"
          f":d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
    sh(["ffmpeg", "-y", "-i", str(img), "-vf", vf, "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out_path)])

def assemble(image_paths, bounds, voice_mp3, ass_file, build, final_path,
             veo_clip=None):
    clips = []
    for i, ((start, end), img) in enumerate(zip(bounds, image_paths)):
        frames = int(round(end * FPS)) - int(round(start * FPS))
        frames = max(frames, FPS)  # at least 1s
        clip = build / f"scene_{i}.mp4"
        if i == 0 and veo_clip:
            # trim/pad the veo shot to scene-1 duration, mute, normalize size
            sh(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(veo_clip),
                "-frames:v", str(frames), "-an",
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                       f"crop={W}:{H},fps={FPS},format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(clip)])
        else:
            ken_burns_clip(img, end - start, i, clip, frames)
        clips.append(clip)

    concat_txt = build / "concat.txt"
    concat_txt.write_text("".join(f"file '{c.name}'\n" for c in clips),
                          encoding="utf-8")
    silent = build / "video_nosub.mp4"
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
        "-c", "copy", silent.name], cwd=build)

    bgm = ROOT / "assets" / "bgm.mp3"
    cmd = ["ffmpeg", "-y", "-i", silent.name, "-i", str(voice_mp3)]
    if bgm.exists():
        cmd += ["-stream_loop", "-1", "-i", str(bgm),
                "-filter_complex",
                "[2:a]volume=0.12[m];[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-vf", f"ass={ass_file.name}:fontsdir=fonts",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "final.mp4"]
    sh(cmd, cwd=build)  # relative paths (cwd=build) keep Windows filter args safe
    shutil.copy(build / "final.mp4", final_path)

# ----------------------------- optional: Veo --------------------------------

def make_veo_clip(client, prompt, build):
    from google.genai import types
    print(f"  Veo: generating 8s hero shot (PAID — roughly Rs.100 at current "
          f"Veo Fast rates; check ai.google.dev/pricing)...")
    op = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=f"{prompt}. Slow cinematic camera movement, no text.",
        config=types.GenerateVideosConfig(aspect_ratio="9:16"))
    while not op.done:
        time.sleep(10)
        op = client.operations.get(op)
    vid = op.response.generated_videos[0]
    path = build / "veo_hero.mp4"
    client.files.download(file=vid.video)
    vid.video.save(str(path))
    return path

# ----------------------------- main ------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="no API key needed; placeholder visuals")
    ap.add_argument("--veo", action="store_true",
                    help="use a Veo clip for scene 1 (paid)")
    ap.add_argument("--voice", default=VOICE)
    args = ap.parse_args()

    preflight(args.dry_run)   # fail here, before font/plan/images — zero spend

    build = ROOT / "build" / datetime.now().strftime("%Y%m%d_%H%M%S")
    build.mkdir(parents=True)
    OUT_DIR.mkdir(exist_ok=True)
    ensure_font(build / "fonts")

    client = None
    if not args.dry_run:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY not set (or use --dry-run).")
        from google import genai
        client = genai.Client(api_key=key)

    print("[1/5] plan + script (Hindi)")
    plan = DRY_PLAN if args.dry_run else make_plan(client)
    print(f"  topic: {plan['topic_en']} — {plan['title_hi']}")

    print("[2/5] voice (edge-tts, word-timed)")
    voice_mp3, words, dur = make_voice(plan, build, args.voice, args.dry_run)
    bounds = scene_boundaries(plan, words, dur)

    print("[3/5] visuals")
    images = (make_placeholder_images(plan, build) if args.dry_run
              else make_images(client, plan, build))
    veo_clip = None
    if args.veo and client:
        try:
            veo_clip = make_veo_clip(client, plan["scenes"][0]["image_prompt"], build)
        except Exception as e:
            print(f"  Veo failed ({e}) -> falling back to image for scene 1")

    print("[4/5] captions")
    ass_file = build / "subs.ass"
    build_ass(words, dur, ass_file)

    print("[5/5] assembly (Ken Burns + captions + audio)")
    slug = re.sub(r"[^a-z0-9-]", "", plan["topic_en"].lower())[:50] or "video"
    final = OUT_DIR / f"{slug}.mp4"
    assemble(images, bounds, voice_mp3, ass_file, build, final, veo_clip)

    meta = {k: plan[k] for k in ("topic_en", "title_hi", "caption_hi", "hashtags")}
    (OUT_DIR / f"{slug}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.dry_run:
        save_history(plan["topic_en"])

    print(f"\nDone: {final}  ({ffprobe_duration(final):.1f}s)")
    print(f"Metadata for upload step: {OUT_DIR / (slug + '.json')}")

if __name__ == "__main__":
    main()