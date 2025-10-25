from modules.captioner import generate_caption
from modules.music_generator import generate_music
from modules.prompt_utils import build_music_prompt, PRESET_MONUMENTS
import gradio as gr

def process_monument(image, monument_type=None):
    """
    Proces complet: Caption + Muzică
    """
    caption = generate_caption(image.name)
    print("Caption generat:", caption)

    # Folosim preset dacă monument_type este dat
    preset = PRESET_MONUMENTS.get(monument_type, {})
    music_prompt = build_music_prompt(
        caption,
        monument_type=monument_type,
        period=preset.get("period"),
        mood=preset.get("mood")
    )

    music_path = generate_music(music_prompt, output_path="outputs/generated_music.wav", duration_sec=15)

    return caption, music_path

# 3️⃣ Gradio UI (asta e exact ce ai scris tu)
def gr_process(image, monument_type):
    caption, music_path = process_monument(image, monument_type)
    return caption, music_path

demo = gr.Interface(
    fn=gr_process,
    inputs=[
        gr.Image(type="filepath", label="Upload imagine monument"),
        gr.Dropdown(choices=list(PRESET_MONUMENTS.keys()), label="Tip monument (optional)")
    ],
    outputs=[gr.Textbox(label="Caption generat"), gr.Audio(label="Muzică generată")],
    title="Monument History AI",
    description="Upload o imagine cu un monument istoric și AI-ul generează caption și muzică specifică perioadei istorice."
)

# 4️⃣ Launch UI
if __name__ == "__main__":
    demo.launch()