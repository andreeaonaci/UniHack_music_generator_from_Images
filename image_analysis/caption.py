from transformers import pipeline
from PIL import Image
import os

def generate_caption(image_path: str) -> str:
    """
    Generează o descriere scurtă a imaginii.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-large")
    result = captioner(image)[0]["generated_text"]
    return result
