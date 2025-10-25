from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch
import scipy.io.wavfile

model_id = "facebook/musicgen-medium"
processor = MusicgenProcessor.from_pretrained(model_id)
model = MusicgenForConditionalGeneration.from_pretrained(model_id)

def generate_music(caption: str, style: str = "", output_path="generated.wav"):
    prompt = f"{caption}. Instrumentation: {style}. Cinematic, historical atmosphere."

    inputs = processor(text=prompt, padding=True, return_tensors="pt")

    audio_values = model.generate(
        **inputs,
        max_length=int(15 * model.config.audio_encoder.frame_rate / 1024)
    )

    sr = model.config.audio_encoder.sampling_rate
    scipy.io.wavfile.write(output_path, sr, audio_values[0, 0].cpu().numpy())
    return output_path
