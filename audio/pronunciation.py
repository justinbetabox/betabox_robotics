BRAND_PRONUNCIATIONS = {
    "Betabox": "Baytabox",
    "betabox": "baytabox",
    "BETABOX": "BAYTABOX",
}


def prepare_speech_text(text: str) -> str:
    prepared = text

    for original, spoken in BRAND_PRONUNCIATIONS.items():
        prepared = prepared.replace(original, spoken)

    return prepared
