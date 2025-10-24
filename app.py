import os
from image_analysis.caption import generate_caption
from image_analysis.story import generate_story
from music_gen.mood import extract_music_mood
from music_gen.generate_music import generate_music

IMAGE_PATH = "assets/folclor.jpg"
OUTPUT_MUSIC = "assets/generated_music.wav"

if __name__ == "__main__":
    print("📌 Processing image...")
    caption = generate_caption(IMAGE_PATH)
    print("📝 Caption:", caption)

    print("📌 Generating story...")
    story = generate_story(caption)
    print("📖 Story:", story)

    print("📌 Extracting music mood...")
    music_prompt = extract_music_mood(caption)
    print("🎶 Music Prompt:", music_prompt)

    print("📌 Generating music...")
    music_path = generate_music(music_prompt, OUTPUT_MUSIC)
    print("✅ Music generated at:", music_path)
