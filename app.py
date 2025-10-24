import streamlit as st
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel, pipeline
from music_gen.generate_music import generate_music

# --- SETUP CLIP ---
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# --- SETUP GPT (text generation) ---
text_generator = pipeline("text-generation", model="gpt2")  # Rapid MVP

# --- STREAMLIT UI ---
st.set_page_config(page_title="AI Cultural Companion", layout="wide")
st.title("🎨 AI Cultural Companion")
st.write("Transformă o imagine culturală în muzică și poveste generată de AI!")

# Sidebar
st.sidebar.header("Instrucțiuni")
st.sidebar.write("""
1. Încarcă o imagine culturală (tablou, poster, obiect)  
2. AI-ul va genera o poveste + muzică inspirată  
3. Ascultă și citește rezultatul!
""")

uploaded_file = st.file_uploader("Alege o imagine", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imaginea ta", use_column_width=True)

    # --- 1. Extract embedding ---
    inputs = clip_processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_embedding = clip_model.get_image_features(**inputs)

    st.write("✅ Embedding extras cu CLIP")

    # --- 2. Generate Text ---
    prompt_text = f"Scrie o poveste culturală scurtă inspirată de această imagine: {uploaded_file.name}"
    generated_text = text_generator(prompt_text, max_length=100, do_sample=True, temperature=0.7)
    story = generated_text[0]['generated_text']
    st.subheader("📖 Poveste generată de AI")
    st.write(story)

    # --- 3. Generate Music ---
    st.subheader("🎵 Muzică generată de AI")
    music_path = generate_music(prompt_text, output_path="assets/generated_music.wav")
    st.audio(music_path)
