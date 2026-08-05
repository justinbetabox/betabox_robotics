from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from betabox_robotics.robots.health import (
    HealthCheck,
    RobotHealth,
)


class HealthCheckTests(unittest.TestCase):
    def test_create(self) -> None:
        check = HealthCheck(
            name="drive",
            ok=True,
            message="ready",
        )

        self.assertEqual(
            check.name,
            "drive",
        )
        self.assertTrue(check.ok)
        self.assertEqual(
            check.message,
            "ready",
        )

    def test_normalizes_strings(self) -> None:
        check = HealthCheck(
            name=" drive ",
            ok=False,
            message=" motor unavailable ",
        )

        self.assertEqual(
            check.name,
            "drive",
        )
        self.assertEqual(
            check.message,
            "motor unavailable",
        )

    def test_empty_message_is_allowed(self) -> None:
        check = HealthCheck(
            name="drive",
            ok=True,
        )

        self.assertEqual(
            check.message,
            "",
        )

    def test_whitespace_message_becomes_empty(
        self,
    ) -> None:
        check = HealthCheck(
            name="drive",
            ok=True,
            message="   ",
        )

        self.assertEqual(
            check.message,
            "",
        )

    def test_rejects_invalid_name_type(
        self,
    ) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "name must be a string",
                ),
            ):
                HealthCheck(
                    name=value,  # type: ignore[arg-type]
                    ok=True,
                )

    def test_rejects_empty_name(self) -> None:
        for value in (
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "name cannot be empty",
                ),
            ):
                HealthCheck(
                    name=value,
                    ok=True,
                )

    def test_rejects_non_boolean_ok(self) -> None:
        for value in (
            1,
            0,
            "true",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "ok must be a boolean",
                ),
            ):
                HealthCheck(
                    name="drive",
                    ok=value,  # type: ignore[arg-type]
                )

    def test_rejects_invalid_message_type(
        self,
    ) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "message must be a string",
                ),
            ):
                HealthCheck(
                    name="drive",
                    ok=False,
                    message=value,  # type: ignore[arg-type]
                )

    def test_to_dict(self) -> None:
        check = HealthCheck(
            name="drive",
            ok=False,
            message="motor unavailable",
        )

        self.assertEqual(
            check.to_dict(),
            {
                "name": "drive",
                "ok": False,
                "message": "motor unavailable",
            },
        )

    def test_is_frozen(self) -> None:
        check = HealthCheck(
            name="drive",
            ok=True,
        )

        with self.assertRaises(FrozenInstanceError):
            check.ok = False  # type: ignore[misc]


class RobotHealthTests(unittest.TestCase):
    def test_defaults(self) -> None:
        health = RobotHealth(ok=True)

        self.assertTrue(health.ok)
        self.assertEqual(
            health.checks,
            (),
        )
        self.assertEqual(
            health.messages,
            (),
        )
        self.assertEqual(
            health.failed_checks,
            (),
        )

    def test_accepts_checks(self) -> None:
        first = HealthCheck(
            name="drive",
            ok=True,
        )
        second = HealthCheck(
            name="vision",
            ok=False,
            message="camera unavailable",
        )

        health = RobotHealth(
            ok=False,
            checks=(
                first,
                second,
            ),
        )

        self.assertEqual(
            health.checks,
            (
                first,
                second,
            ),
        )

    def test_rejects_non_boolean_ok(self) -> None:
        for value in (
            1,
            0,
            "true",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "ok must be a boolean",
                ),
            ):
                RobotHealth(
                    ok=value,  # type: ignore[arg-type]
                )

    def test_rejects_list_checks(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "checks must be a tuple",
        ):
            RobotHealth(
                ok=True,
                checks=[  # type: ignore[arg-type]
                    HealthCheck(
                        name="drive",
                        ok=True,
                    )
                ],
            )

    def test_rejects_invalid_check_entry(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "checks must contain only HealthCheck instances",
        ):
            RobotHealth(
                ok=False,
                checks=(
                    object(),  # type: ignore[arg-type]
                ),
            )

    def test_failed_checks(self) -> None:
        passing = HealthCheck(
            name="drive",
            ok=True,
        )
        failed = HealthCheck(
            name="vision",
            ok=False,
            message="camera unavailable",
        )

        health = RobotHealth(
            ok=False,
            checks=(
                passing,
                failed,
            ),
        )

        self.assertEqual(
            health.failed_checks,
            (failed,),
        )

    def test_messages_include_only_failed_checks_with_messages(
        self,
    ) -> None:
        health = RobotHealth(
            ok=False,
            checks=(
                HealthCheck(
                    name="drive",
                    ok=True,
                    message="ignored",
                ),
                HealthCheck(
                    name="vision",
                    ok=False,
                    message="camera unavailable",
                ),
                HealthCheck(
                    name="audio",
                    ok=False,
                ),
                HealthCheck(
                    name="system",
                    ok=False,
                    message="media missing",
                ),
            ),
        )

        self.assertEqual(
            health.messages,
            (
                "camera unavailable",
                "media missing",
            ),
        )

    def test_to_dict(self) -> None:
        health = RobotHealth(
            ok=False,
            checks=(
                HealthCheck(
                    name="drive",
                    ok=True,
                ),
                HealthCheck(
                    name="vision",
                    ok=False,
                    message="camera unavailable",
                ),
            ),
        )

        self.assertEqual(
            health.to_dict(),
            {
                "ok": False,
                "checks": [
                    {
                        "name": "drive",
                        "ok": True,
                        "message": "",
                    },
                    {
                        "name": "vision",
                        "ok": False,
                        "message": ("camera unavailable"),
                    },
                ],
            },
        )

    def test_checks_are_immutable(self) -> None:
        check = HealthCheck(
            name="drive",
            ok=True,
        )
        health = RobotHealth(
            ok=True,
            checks=(check,),
        )

        with self.assertRaises(TypeError):
            health.checks[0] = check  # type: ignore[index]

    def test_is_frozen(self) -> None:
        health = RobotHealth(ok=True)

        with self.assertRaises(FrozenInstanceError):
            health.ok = False  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
