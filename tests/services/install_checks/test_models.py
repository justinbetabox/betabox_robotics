from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.services.install_checks.models import (
    CheckResult,
)


class CheckResultTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        result = CheckResult(
            name="command:python",
            ok=True,
            message="/usr/bin/python",
        )

        self.assertEqual(
            result.name,
            "command:python",
        )
        self.assertTrue(result.ok)
        self.assertEqual(
            result.message,
            "/usr/bin/python",
        )

    def test_default_message(self) -> None:
        result = CheckResult(
            name="check:test",
            ok=False,
        )

        self.assertEqual(
            result.message,
            "",
        )

    def test_strips_name_and_message(self) -> None:
        result = CheckResult(
            name=" check:test ",
            ok=True,
            message=" passed ",
        )

        self.assertEqual(
            result.name,
            "check:test",
        )
        self.assertEqual(
            result.message,
            "passed",
        )

    def test_allows_empty_message(self) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with self.subTest(value=value):
                result = CheckResult(
                    name="check:test",
                    ok=True,
                    message=value,
                )

                self.assertEqual(
                    result.message,
                    "",
                )

    def test_rejects_invalid_name_type(self) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "name must be a string",
                ),
            ):
                CheckResult(
                    name=value,  # type: ignore[arg-type]
                    ok=True,
                )

    def test_rejects_empty_name(self) -> None:
        for value in (
            "",
            " ",
            "\t",
            "\n",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "name cannot be empty",
                ),
            ):
                CheckResult(
                    name=value,
                    ok=True,
                )

    def test_rejects_non_boolean_ok(self) -> None:
        for value in (
            None,
            0,
            1,
            "yes",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "ok must be a boolean",
                ),
            ):
                CheckResult(
                    name="check:test",
                    ok=value,  # type: ignore[arg-type]
                )

    def test_rejects_invalid_message_type(self) -> None:
        for value in (
            None,
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "message must be a string",
                ),
            ):
                CheckResult(
                    name="check:test",
                    ok=True,
                    message=value,  # type: ignore[arg-type]
                )

    def test_to_dict(self) -> None:
        result = CheckResult(
            name="service-enabled:jupyterhub.service",
            ok=False,
            message="disabled",
        )

        self.assertEqual(
            result.to_dict(),
            {
                "name": ("service-enabled:jupyterhub.service"),
                "ok": False,
                "message": "disabled",
            },
        )

    def test_is_frozen(self) -> None:
        result = CheckResult(
            name="check:test",
            ok=True,
        )

        with self.assertRaises(FrozenInstanceError):
            result.ok = False  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        result = CheckResult(
            name="check:test",
            ok=True,
        )

        self.assertFalse(
            hasattr(
                result,
                "__dict__",
            )
        )


if __name__ == "__main__":
    unittest.main()
