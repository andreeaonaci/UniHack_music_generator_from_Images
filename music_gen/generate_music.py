from transformers import MusicgenForConditionalGeneration, MusicgenProcessor
import torch

# Încarcă modelul
pipe = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-medium")
processor = MusicgenProcessor.from_pretrained("facebook/musicgen-medium")
pipe.to("cuda")  # sau "cpu" dacă nu ai GPU

# Generează muzică
prompt = "O muzică inspirată de un tablou impresionist"
audio_array = pipe(prompt, max_length_seconds=20).audios[0]

# Salvează audio
import soundfile as sf
sf.write("generated_music.wav", audio_array, 32000)
