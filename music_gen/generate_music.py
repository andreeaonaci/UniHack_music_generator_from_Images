import torch
from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import scipy.io.wavfile as wav
import os

MODEL_ID = "facebook/musicgen-small"  # trebuie să fie disponibil pe HuggingFace

device = "cuda" if torch.cuda.is_available() else "cpu"

processor = MusicgenProcessor.from_pretrained(MODEL_ID)
model = MusicgenForConditionalGeneration.from_pretrained(MODEL_ID).to(device)

def generate_music(prompt: str, output_path="assets/generated_music.wav"):
    """
    Generează melodie pe baza prompt-ului.
    - prompt: mood / instrumente / gen
    - output_path: unde se salvează WAV
    """
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    print(f"🎵 Generating music for prompt: {prompt}")

    # Encode prompt
    inputs = processor(
        text=prompt,
        padding=True,
        return_tensors="pt"
    ).to(device)

    # Generate audio
    audio_values = model.generate(
        **inputs,
        max_new_tokens=750,   # 50 tokens/sec
        do_sample=True,        # sampling activ
        top_k=50,
        top_p=0.95,
        temperature=1.2
    )

    # Salvează WAV
    sampling_rate = model.config.audio_encoder.sampling_rate
    wav.write(output_path, sampling_rate, audio_values[0, 0].cpu().numpy())

    print(f"✅ Music saved at: {output_path}")
    return output_path
