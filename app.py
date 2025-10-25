import gradio as gr
from modules.captioner import generate_caption
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name

def process_monument(monument_name="Bran"):
    """
    1. Caută monumentul în dataset
    2. Obține descrierea → caption
    3. Folosește descrierea ca prompt pentru generare muzică
    """
    monument = match_monument_by_name(monument_name)
    
    # fallback
    caption = monument.get("descriere", "").strip()
    print("Caption is: ", caption)
    if not caption:
        caption = f"{monument_name} este un monument istoric important în România, cu o arhitectură remarcabilă."
    
    # eventual extindere prompt
    # caption_for_music = f"Generați o melodie inspirată de: {caption}"
    
    image_path = "datasets/" + monument.get("image")
    
    music_path = generate_music(caption ,output_path="assets/generated_music.wav")
    
    return caption, music_path, image_path



import gradio as gr
from modules.captioner import generate_caption
from modules.music_generator import generate_music
from datasets.monuments import load_monuments, match_monument_by_name

# ----------------- Funcție proces -----------------
def process_monument_ui(monument_name):
    monument = match_monument_by_name(monument_name)
    caption = monument.get("descriere", "").strip()
    if not caption:
        caption = f"{monument_name} este un monument istoric important în România."
    image_path = monument.get("image")
    music_path = generate_music(caption, output_path="assets/generated_music.wav")
    return caption, music_path, image_path

# ----------------- Lista monumente -----------------
monuments_list = [m["nume"] for m in load_monuments()]

# ----------------- Gradio Blocks -----------------
with gr.Blocks(css="""
    body {background: linear-gradient(to right, #f0f4ff, #d9e4ff);}
    .card {border-radius: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.25); padding: 15px; text-align:center; transition: transform 0.3s;}
    .card:hover {transform: scale(1.05);}
    .caption {font-weight:bold; font-size:16px; color:#333; margin-top:10px;}
""") as demo:

    gr.Markdown("<h1 style='text-align:center; color:#4B0082;'>🎵 Monument History AI 🎵</h1>")
    gr.Markdown("<p style='text-align:center; font-size:18px; color:#555;'>Selectează un monument și bucură-te de muzica inspirată de acesta.</p>")

    with gr.Row():
        with gr.Column(scale=1):
            monument_dropdown = gr.Dropdown(choices=monuments_list, label="Selectează monument")
            generate_btn = gr.Button("🎶 Generează muzică")
        with gr.Column(scale=2):
            image_card = gr.Image(label="Imagine monument", type="filepath")
            caption_out = gr.Textbox(label="Caption generat", interactive=False)
            music_out = gr.Audio(label="Muzică generată", autoplay=True)

    # Legăm butonul de funcția de generare
    generate_btn.click(
        fn=process_monument_ui,
        inputs=[monument_dropdown],
        outputs=[caption_out, music_out, image_card]
    )

demo.launch()
