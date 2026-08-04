BRAND_PRONUNCIATIONS = {
    "Betabox": "Baytabox",
    "betabox": "baytabox",
    "BETABOX": "BAYTABOX",
}


def prepare_speech_text(text: str) -> str:
    """
    Replace words with speech-friendly pronunciations before sending text
    to a text-to-speech engine.
    """
    prepared = text

    for original, spoken in BRAND_PRONUNCIATIONS.items():
        prepared = prepared.replace(original, spoken)

    return prepared
