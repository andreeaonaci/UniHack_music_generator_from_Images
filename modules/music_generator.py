from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch
import scipy.io.wavfile
import os
import re

# ------------------- Smart Style Inference -------------------

HISTORICAL_KEYWORDS = {
    # Religious & Sacred
    "church": ["gregorian choir", "organ cathedral"],
    "cathedral": ["sacred chanting", "organ cathedral"],
    "basilica": ["sacred chanting", "church bells"],
    "monastery": ["monastic choir", "ancient religious music"],
    "biserica": ["sacred choir", "religious organ"],
    "orthodox": ["byzantine choir", "liturgical chants"],
    "catholic": ["gregorian choir", "classical chamber"],

    # Royal & Aristocratic
    "castle": ["epic orchestral", "noble horns"],
    "palace": ["baroque chamber strings", "classical orchestra"],
    "royal": ["regal brass", "orchestral march"],
    "queen": ["harpsichord", "baroque elegance"],
    "king": ["royal horns", "heroic march"],
    "court": ["renaissance ensemble", "lute strings"],
    "noble": ["romantic orchestra", "grand piano"],

    # Medieval & Fortified
    "fortress": ["war drums", "heroic brass"],
    "citadel": ["battle percussion", "deep brass"],
    "battlements": ["war horns", "marching drums"],
    "sword": ["battle percussion"],
    "knight": ["medieval horns", "epic battle score"],
    "gate tower": ["timpani", "marching brass"],
    "siege": ["dramatic percussion"],

    # Ancient Civilizations
    "ancient": ["tribal percussion", "flutes"],
    "roman": ["imperial horns", "ancient percussion"],
    "dacian": ["tribal drums", "ancestral flutes"],
    "temple": ["mystical flute", "ancient strings"],
    "ruins": ["dark ambient", "eerie strings"],

    # Architecture & Styles
    "gothic": ["church organ", "dark choir"],
    "baroque": ["harpsichord", "baroque strings"],
    "renaissance": ["lutes", "soft classical strings"],
    "neoclassical": ["chamber orchestra", "violin ensemble"],
    "eclectic": ["romantic orchestra"],
    "modernist": ["minimalist piano", "ambient electronics"],

    # War & Heroic
    "battle": ["war drums", "epic brass"],
    "memorial": ["emotional orchestra", "string elegy"],
    "victory": ["heroic fanfare", "triumphal brass"],
    "triumph": ["grand fanfare"],

    # Culture & Museums
    "museum": ["soft classical", "ambient modern classical"],
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

def generate_music(caption: str, style: str = "", output_path="generated.wav", duration_sec: int = 15):
    """
    Generate music from a text caption using MusicGen.
    """

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

    print("Prompt before fallback:", prompt)

    # Make sure prompt is not empty
    if len(prompt.strip()) == 0:
        prompt = "Cinematic music."
        print("Prompt was empty, using fallback:", prompt)

    # Tokenize (no manual padding)
    tokens = processor.tokenizer(prompt, return_tensors="pt")

    # Diagnostic prints
    print("Tokens input_ids shape:", tokens.input_ids.shape)
    print("Tokens input_ids:", tokens.input_ids)

    # Check if tokenizer returned 0 tokens
    if tokens.input_ids.shape[1] == 0:
        print("⚠️ Tokenizer returned 0 tokens, using minimal fallback.")
        tokens = processor.tokenizer("Cinematic music.", return_tensors="pt")
        print("Tokens input_ids after fallback shape:", tokens.input_ids.shape)
        print("Tokens input_ids after fallback:", tokens.input_ids)

    if tokens.input_ids.shape[1] == 0:
        raise ValueError("Tokenizer failed to produce any tokens. Please use a non-empty prompt.")

    # Move to device
    tokens = {k: v.to(device) for k, v in tokens.items()}

    # Compute max_length safely
    frame_rate = getattr(model.config.audio_encoder, "frame_rate", None)
    if frame_rate is None or frame_rate == 0:
        print("⚠️ frame_rate not set in config, using default 16000")
        frame_rate = 16000

    max_length = max(1, int(duration_sec * frame_rate / 1024))
    print("valori ", duration_sec, frame_rate)
    print("Max length for generation:", max_length)
    import numpy as np
    chunk_max_length = 100  # fiecare chunk ~10 secunde (poți ajusta)
    num_chunks = max(1, int(np.ceil(duration_sec / 5)))
    print("Num chunks:", num_chunks)

    all_audio = []

    for i in range(num_chunks):
        print(f"🎵 Generating chunk {i+1}/{num_chunks}...")
        audio_chunk = model.generate(**tokens, max_length=chunk_max_length)

        if hasattr(audio_chunk, "cpu"):
            audio_chunk = audio_chunk.cpu().numpy()

        all_audio.append(audio_chunk.reshape(-1))

    final_audio = np.concatenate(all_audio)

    target_len = int(16000 * duration_sec)
    final_audio = final_audio[:target_len]

    scipy.io.wavfile.write(output_path, 16000, final_audio.astype(np.float32))
    print(f"✅ Music generated: {output_path}")

    return output_path