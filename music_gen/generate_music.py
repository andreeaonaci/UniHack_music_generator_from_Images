# modules/music_gen.py

from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch
import scipy.io.wavfile

model_id = "facebook/musicgen-medium"
processor = MusicgenProcessor.from_pretrained(model_id)
model = MusicgenForConditionalGeneration.from_pretrained(model_id)

def generate_music(prompt: str, output_path="outputs/generated_music.wav", duration_sec=15):
    """
    Generează muzică pe baza unui prompt text
    """
    inputs = processor(
        text=prompt,
        padding=True,
        return_tensors="pt"
    )

    audio_values = model.generate(
        **inputs,
        max_new_tokens=duration_sec * 16_000
    )

    sampling_rate = model.config.audio_encoder.sampling_rate
    scipy.io.wavfile.write(output_path, sampling_rate, audio_values[0, 0].cpu().numpy())

    return output_path
