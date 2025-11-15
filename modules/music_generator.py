from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch
import scipy.io.wavfile
import os
import re
import requests
import tempfile
import time
import numpy as np
from music_gen.mood import extract_music_mood

HISTORICAL_KEYWORDS = {
    "art": ["piano minimal", "orchestral textures"],
    "concert": ["grand orchestra", "acoustic strings"],
    "theatre": ["dramatic score"],

    # Natural Monuments
    "lake": ["ambient pads", "soft winds", "gentle piano", "water textures"],
    "mountain": ["pan flutes", "epic cinematic", "wind strings"],
    "valley": ["serene orchestral", "acoustic guitars", "soft pads"],
    "cave": ["echoing ambient", "mystical drones", "reverberant textures"],
    "waterfall": ["flowing textures", "nature percussion", "soft chimes"],
    "cliff": ["dramatic ambient", "windy textures"],
    "Delta": ["calm nature soundscape", "soft flutes", "water birds", "ambient pads"],

    # Maritime & Ports
    "port": ["accordion folk", "strings with sea ambience", "harbor sounds"],
    "sea": ["ambient waves", "soft cinematic pads", "oceanic textures"],

    # Transportation / Industrial Heritage
    "railway": ["nostalgic violin", "folk acoustic", "train rhythm"],
    "train": ["mechanical rhythm", "orchestral travel suite", "ambient locomotion"],

    # Tourism & Landmarks
    "plaza": ["festive orchestra", "street ensemble"],
    "square": ["historical waltz", "soft piano"],
    "market": ["folk ensemble", "traditional instruments", "village ambiance"],
    "tower": ["dramatic brass", "cinematic rise", "epic pads"],
    "bridge": ["calm orchestral", "nostalgic violins", "flowing textures"],

    # Generic/Extra
    "historical": ["cinematic strings", "piano minimal", "orchestral textures"],
    "cultural": ["soft piano", "ambient strings", "light choir"],
}

def extract_style_from_caption(caption: str, min_words: int = 2):
    """
    Extracts a style from the caption based on HISTORICAL_KEYWORDS.
    Returns a string with at least min_words.
    """
    caption_norm = normalize_ro(caption.lower())  # lowercase + diacritics
    matched_styles = []

    for keyword, styles in HISTORICAL_KEYWORDS.items():
        if keyword in caption_norm:
            matched_styles.extend(styles)

    # Ensure we have at least min_words in the style
    if len(matched_styles) < min_words:
        # fallback: pick a few generic styles
        matched_styles.extend(HISTORICAL_KEYWORDS.get("historical", []))

    # Remove duplicates
    matched_styles = list(dict.fromkeys(matched_styles))

    return ", ".join(matched_styles[:min_words])


def infer_monument_style(description: str) -> str:
    desc = description.lower()
    detected = []

    for key, styles in HISTORICAL_KEYWORDS.items():
        if key in desc:
            detected.extend(styles)

    if not detected:
        return "cinematic orchestra, atmospheric strings"

    # return max 3 unique
    detected = list(dict.fromkeys(detected))[:3]
    return ", ".join(detected)


# ------------------- Model & Processor -------------------
model_id = "facebook/musicgen-medium"
processor = MusicgenProcessor.from_pretrained(model_id)
model = MusicgenForConditionalGeneration.from_pretrained(model_id)

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Optional: translator fallback using deep-translator
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_AVAILABLE = True
except ImportError:
    print("⚠️ deep-translator not installed, prompts will remain in original language.")
    TRANSLATE_AVAILABLE = False

# ------------------- Normalizare diacritice -------------------
def normalize_ro(text: str) -> str:
    """
    Replace Romanian diacritics with ASCII letters.
    """
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T'
    }
    # Folosim regex pentru a înlocui toate aparițiile
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))
    return pattern.sub(lambda m: replacements[m.group(0)], text)

def _generate_music_local(caption: str, style: str = "", output_path="generated.wav", duration_sec: int = 10, loop: bool = True):
    """Legacy local MusicGen-based generator (kept as a fallback).

    Produces a WAV file at `output_path`. Ensures duration_sec <= 10.
    If `loop` is True and the generated audio is shorter than requested, it will tile it to reach the target length.
    """
    duration_sec = min(int(duration_sec), 10)

    # Normalize Romanian diacritics
    caption_norm = normalize_ro(caption)

    # Translate caption to English if possible
    if TRANSLATE_AVAILABLE:
        try:
            caption_en = GoogleTranslator(source='ro', target='en').translate(caption_norm)
        except Exception as e:
            print(f"⚠️ Translation failed: {e}, using normalized caption.")
            caption_en = caption_norm
    else:
        caption_en = caption_norm

    # Auto infer style if user didn't provide one
    auto_style = infer_monument_style(caption_en)
    final_style = style if style else auto_style
    if not final_style:
        final_style = extract_style_from_caption(caption_en)

    print("🎼 Selected style:", final_style)

    prompt = f"Music for a historical monument: {caption_en}. Style: {final_style}. Cinematic atmosphere, cultural heritage."
    # show the final prompt that will be used by the local MusicGen generator
    print("➡️ Local generator prompt:\n" + prompt)

    # Tokenize (no manual padding)
    tokens = processor.tokenizer(prompt, return_tensors="pt")

    # Move to device
    tokens = {k: v.to(device) for k, v in tokens.items()}

    # Number of chunks: conservative (each chunk ~5s)
    num_chunks = max(1, int(np.ceil(duration_sec / 5)))
    chunk_max_length = 100

    all_audio = []
    for i in range(num_chunks):
        print(f"🎵 Generating chunk {i+1}/{num_chunks} (local)...")
        audio_chunk = model.generate(**tokens, max_length=chunk_max_length)
        if hasattr(audio_chunk, "cpu"):
            audio_chunk = audio_chunk.cpu().numpy()
        all_audio.append(audio_chunk.reshape(-1))

    final_audio = np.concatenate(all_audio)
    target_len = int(16000 * duration_sec)
    if final_audio.shape[0] < target_len and loop and final_audio.shape[0] > 0:
        # tile audio to reach target length
        repeats = int(np.ceil(target_len / final_audio.shape[0]))
        final_audio = np.tile(final_audio, repeats)[:target_len]
    else:
        final_audio = final_audio[:target_len]

    scipy.io.wavfile.write(output_path, 16000, final_audio.astype(np.float32))
    print(f"✅ Local Music generated: {output_path}")
    return output_path


def _generate_music_suno(caption: str, output_path: str, duration_sec: int = 15, loop: bool = True):
    """Send prompt to Suno and return a path to the generated audio file.

    Handles three common Suno response styles:
    - Direct binary audio (wav/mp3) in the HTTP response body.
    - JSON with an audio URL (key: "audio_url" or "url").
    - JSON with an async job id (key: "jobId"/"taskId"/"id") which requires polling a record-info endpoint.

    The function will download and, if necessary, convert audio to WAV (16k mono) and return the file path.
    """
    duration_sec = min(int(duration_sec), 15)
    api_key = os.getenv("SUNO_API_KEY")
    api_url = os.getenv("SUNO_API_URL", "https://api.sunoapi.org/api/v1/generate")
    if not api_key:
        raise RuntimeError("SUNO_API_KEY not set")

    enriched = build_enriched_prompt(caption)
    print("➡️ Suno prompt:\n" + enriched)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {"prompt": enriched[0:499], 
                "duration_seconds": duration_sec, 
                "customMode": True,
                "instrumental": True,
                "personaId": "persona_123",
                "model": "V3_5",
                "negativeTags": "Heavy Metal, Upbeat Drums",
                "vocalGender": "m",
                "styleWeight": 0.65,
                "weirdnessConstraint": 0.65,
                "audioWeight": 0.65,
                "format": "wav", 
                "loop": bool(loop)}

    # Allow callers to specify a public callback URL via env var SUNO_CALLBACK_URL
    callback_url = os.getenv("SUNO_CALLBACK_URL")
    print("Suno callback URL:", callback_url)
    if callback_url:
        payload["callBackUrl"] = callback_url
    else:
        print("⚠️ SUNO_CALLBACK_URL not set; proceeding without callback URL.")
    resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Suno API error: {resp.status_code} {resp.text}")

    # After sending the request we prefer to receive Suno's callback (saved under assets/suno_callback).
    # Wait up to `wait_secs` seconds for a callback file to appear; if none arrives, fall back to local generation.
    wait_secs = int(os.getenv("SUNO_CALLBACK_WAIT", "5"))
    cb_dir = os.path.join("assets", "suno_callback")
    os.makedirs(cb_dir, exist_ok=True)

    # snapshot before files so we can detect new ones
    before_files = set(os.listdir(cb_dir))

    # helper: check immediate response for audio URL or binary
    try:
        j = resp.json()
    except Exception:
        j = None

    # if Suno returned an immediate audio URL in the response JSON, download it and return
    if isinstance(j, dict):
        audio_url = j.get("audio_url") or j.get("url") or None
        task_id = j.get("taskId") or j.get("jobId") or j.get("id") or None
        if audio_url:
            try:
                from modules.audio_utils import download_and_convert
                return download_and_convert(audio_url, output_path)
            except Exception as e:
                print("Failed to download audio_url from Suno response:", e)

    else:
        # If binary audio returned directly in HTTP body, save and return
        if resp.content:
            try:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ Suno-generated music saved to {output_path} (direct response)")
                return output_path
            except Exception as e:
                print("Failed to write direct Suno response to disk:", e)

    # If we have a task_id, prefer to look for files containing that id; otherwise watch for any new file
    search_for = None
    if isinstance(j, dict):
        search_for = j.get("taskId") or j.get("jobId") or j.get("id")

    print(f"Waiting up to {wait_secs}s for Suno callback files in {cb_dir}...")
    start = time.time()
    found_path = None
    while time.time() - start < wait_secs:
        try:
            files = os.listdir(cb_dir)
        except Exception:
            files = []

        # if we have a task id, match files containing it
        if search_for:
            matches = [f for f in files if search_for in f]
            if matches:
                # pick the most recent match
                matches.sort(key=lambda p: os.path.getmtime(os.path.join(cb_dir, p)))
                found_path = os.path.join(cb_dir, matches[-1])
                break

        # otherwise detect any new file created after our snapshot
        new = [f for f in files if f not in before_files]
        if new:
            new.sort(key=lambda p: os.path.getmtime(os.path.join(cb_dir, p)))
            found_path = os.path.join(cb_dir, new[-1])
            break

        time.sleep(1)

    if found_path:
        print(f"➡️ Found callback-generated file: {found_path}")
        return found_path

    # No callback arrived in time -> fall back to local generator
    print(f"⚠️ No Suno callback received within {wait_secs}s; falling back to local generation.")
    return _generate_music_local(caption, style="", output_path=output_path, duration_sec=duration_sec, loop=loop)


def _generate_music_via_copilot(caption: str, output_path: str, duration_sec: int = 15, loop: bool = True):
    """Optionally send the caption to a Copilot bridge which handles forwarding to Suno.

    The bridge endpoint URL can be configured via COPILOT_BRIDGE_URL. The bridge is
    expected to accept JSON {"text": <str>, "duration": <int>} and return WAV bytes.
    This allows integration with Copilot workflows that orchestrate Suno on your behalf.
    """
    bridge_url = os.getenv("COPILOT_BRIDGE_URL")
    if not bridge_url:
        raise RuntimeError("COPILOT_BRIDGE_URL not set")

    # send both raw text and enriched prompt to the bridge so it can orchestrate
    enriched = build_enriched_prompt(caption)
    # show the final prompt that will be sent to the Copilot bridge
    print("➡️ Copilot bridge prompt:\n" + enriched)
    payload = {"text": caption, "prompt": enriched, "duration": int(min(duration_sec, 15)), "loop": bool(loop)}
    print("➡️ Sending prompt to Copilot bridge:", bridge_url)
    resp = requests.post(bridge_url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Copilot bridge error: {resp.status_code} {resp.text}")
    if resp.content:
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"✅ Copilot-bridged music saved to {output_path}")
        return output_path
    raise RuntimeError("Copilot bridge did not return audio data")


def generate_music(caption: str, style: str = "", output_path="generated.wav", duration_sec: int = 15, loop: bool = True, use_local: bool = False):
    """Wrapper generator.

    If `use_local` is True, force the local MusicGen fallback. Otherwise prefer Copilot bridge -> Suno -> local fallback
    depending on environment configuration. The `loop` flag is passed to downstream generators.
    """
    duration_sec = min(int(duration_sec), 15)

    # If the user explicitly requested the local model, call it directly
    if use_local:
        return _generate_music_local(caption, style=style, output_path=output_path, duration_sec=duration_sec, loop=loop)

    # try Copilot bridge first (if configured), then Suno, then local fallback
    try:
        if os.getenv("COPILOT_BRIDGE_URL"):
            aux = _generate_music_via_copilot(caption, output_path=output_path, duration_sec=duration_sec, loop=loop)
            print ("Using Copilot bridge for music generation")
            return aux
    except Exception as e:
        print(f"⚠️ Copilot bridge failed: {e}. Trying Suno directly...")

    try:
        if os.getenv("SUNO_API_KEY"):
            aux = _generate_music_suno(caption, output_path=output_path, duration_sec=duration_sec, loop=loop)
            print("Using Suno for music generation")
            return aux
    except Exception as e:
        print(f"⚠️ Suno generation failed: {e}. Falling back to local generator.")

    # local fallback
    print("➡️ Using local MusicGen generator as fallback.")
    return _generate_music_local(caption, style=style, output_path=output_path, duration_sec=duration_sec, loop=loop)


def build_enriched_prompt(caption: str, style: str = "") -> str:
    """Create an English, enriched prompt suitable for ambient music generation.

    Steps:
    - normalize Romanian diacritics
    - translate to English when possible
    - ask a lightweight mood model to extract musical mood/instrument suggestions
    - combine with inferred style keywords to form a descriptive prompt
    """
    # normalize
    caption_norm = normalize_ro(caption or "")

    # translate to English if available
    if TRANSLATE_AVAILABLE:
        try:
            caption_en = GoogleTranslator(source='ro', target='en').translate(caption_norm)
        except Exception:
            caption_en = caption_norm
    else:
        caption_en = caption_norm

    # ask the mood model for a short music prompt (may be <15 words)
    try:
        mood = extract_music_mood(caption_en)
    except Exception:
        mood = infer_monument_style(caption_en)

    extra_style = style if style else infer_monument_style(caption_en)

    final_prompt = (
        f"{caption_en}. Create a short ambient piece (max 15 seconds) for this monument. "
        f"Mood: {mood}. Instruments/Style: {extra_style}. Characteristics: gentle evolving pads, soft reverb, low-pass textures, slow tempo (~40-70 BPM), subtle field ambience, minimal or no percussion, no vocals. Emphasize the architectural and cultural atmosphere of the site."
    )
    return final_prompt