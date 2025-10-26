
def build_music_prompt(caption: str, monument_type: str = None, period: str = None, mood: str = None) -> str:
    """
    Construiește un prompt detaliat pentru MusicGen
    bazat pe caption + tip de monument + perioadă + mood.
    """
    prompt = f"Muzică inspirată de monumentul descris: '{caption}'"
    
    if monument_type:
        prompt += f", tip: {monument_type}"
    if period:
        prompt += f", perioada: {period}"
    if mood:
        prompt += f", atmosferă: {mood}"
    
    prompt += ", instrumente tradiționale specifice, coerentă și autentică"
    return prompt


# Exemple de preseturi
PRESET_MONUMENTS = {
    "castel": {"period": "Evul Mediu", "mood": "solemn", "instrumente": "vioară, cor"},
    "biserică": {"period": "Secol XVII", "mood": "linistit", "instrumente": "orgă, cor"},
    "palat": {"period": "Secol XIX", "mood": "grandios", "instrumente": "pian, orchestră"},
    "turn de apărare": {"period": "Evul Mediu", "mood": "misterios", "instrumente": "fluier, cor"},
}
