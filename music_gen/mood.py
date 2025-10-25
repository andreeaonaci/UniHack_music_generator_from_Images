from transformers import pipeline

mood_model = pipeline("text2text-generation", model="google/flan-t5-base")

def extract_music_mood(caption: str) -> str:
    """
    Extrage keywords culturale, mood, instrumente și gen muzical din caption.
    Ignoră obiecte irelevante și face prompt specific culturii.
    """
    prompt = (
        "Analyze the following image description and generate a detailed music prompt "
        "including: mood, musical style/genre, traditional instruments, tempo, "
        "and cultural context. Do NOT include irrelevant objects like food or props. "
        "Output in 15 words or less.\n\n"
        f"Image description: {caption}\n\nMusic prompt:"
    )
    result = mood_model(prompt)[0]["generated_text"]
    return result.strip()
