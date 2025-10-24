from transformers import pipeline

story_model = pipeline("text-generation", model="gpt2", max_length=200)

def generate_story(caption: str) -> str:
    """
    Generează o poveste scurtă pe baza caption-ului (doar pentru afișare).
    """
    prompt = f"Write a short story (4-6 sentences) based on this image description: {caption}"
    result = story_model(prompt)[0]["generated_text"]
    return result.strip()
