from PIL import Image
from transformers import pipeline
from datasets.monuments import match_monument_by_name

captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")

def generate_caption(image_path: str):
    base_caption = captioner(Image.open(image_path))[0]["generated_text"]
    matched = match_monument_by_name(base_caption)

    if matched:
        final_caption = f"{matched['nume']} din {matched['localitate']}. {matched['descriere']}"
    else:
        final_caption = base_caption  # fallback

    return final_caption
