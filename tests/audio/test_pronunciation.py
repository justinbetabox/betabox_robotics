#!/usr/bin/env python3

import unittest

from betabox_robotics.audio.pronunciation import (
    BRAND_PRONUNCIATIONS,
    prepare_speech_text,
)


class PrepareSpeechTextTests(unittest.TestCase):
    def test_replaces_brand_name(self) -> None:
        self.assertEqual(
            prepare_speech_text("Welcome to Betabox."),
            "Welcome to Baytabox.",
        )

    def test_replaces_lowercase_brand_name(self) -> None:
        self.assertEqual(
            prepare_speech_text("betabox is ready."),
            "baytabox is ready.",
        )

    def test_replaces_uppercase_brand_name(self) -> None:
        self.assertEqual(
            prepare_speech_text("BETABOX ONLINE"),
            "BAYTABOX ONLINE",
        )

    def test_multiple_occurrences_are_replaced(self) -> None:
        self.assertEqual(
            prepare_speech_text("Betabox and betabox and BETABOX"),
            "Baytabox and baytabox and BAYTABOX",
        )

    def test_unrelated_text_is_unchanged(self) -> None:
        text = "Robot ready."
        self.assertEqual(
            prepare_speech_text(text),
            text,
        )

    def test_empty_string(self) -> None:
        self.assertEqual(
            prepare_speech_text(""),
            "",
        )

    def test_dictionary_contains_expected_entries(self) -> None:
        self.assertEqual(
            BRAND_PRONUNCIATIONS["Betabox"],
            "Baytabox",
        )
        self.assertEqual(
            BRAND_PRONUNCIATIONS["betabox"],
            "baytabox",
        )
        self.assertEqual(
            BRAND_PRONUNCIATIONS["BETABOX"],
            "BAYTABOX",
        )


if __name__ == "__main__":
    unittest.main()
