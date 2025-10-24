from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch
import scipy.io.wavfile

model_id = "facebook/musicgen-medium"

processor = MusicgenProcessor.from_pretrained(model_id)
model = MusicgenForConditionalGeneration.from_pretrained(model_id)

def generate_music(prompt: str, output_path="generated.wav"):
    print("Generating music for prompt:", prompt)

    inputs = processor(
        text=prompt,
        padding=True,
        return_tensors="pt"
    )

    audio_values = model.generate(
        **inputs,
        max_new_tokens=256  # ~10 sec de audio
    )

    sampling_rate = model.config.audio_encoder.sampling_rate
    scipy.io.wavfile.write(output_path, sampling_rate, audio_values[0, 0].cpu().numpy())

    print(f"Music saved at: {output_path}")
    return output_path
