from __future__ import annotations

import unittest
from unittest.mock import call, patch

from betabox_robotics.config import (
    DEFAULT_PLATFORM_CONFIG,
)
from betabox_robotics.services.verify import (
    main,
    print_results,
)
from betabox_robotics.services.verify_checks.models import (
    CheckResult,
)

MODULE = "betabox_robotics.services.verify"


def make_check(
    name: str,
    *,
    ok: bool = True,
    message: str = "",
) -> CheckResult:
    return CheckResult(
        name=name,
        ok=ok,
        message=message,
    )


class PrintResultsTests(unittest.TestCase):
    def test_prints_all_passing_results(self) -> None:
        checks = (
            make_check(
                "camera:picamera2",
                message="import ok",
            ),
            make_check(
                "hardware:battery",
                message="8.20 V — ok",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertTrue(result)
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Verification"),
                call("===================="),
                call(),
                call("[OK] camera:picamera2"),
                call("     import ok"),
                call("[OK] hardware:battery"),
                call("     8.20 V — ok"),
                call(),
                call("Betabox verification passed."),
            ],
        )

    def test_prints_failed_results(self) -> None:
        checks = (
            make_check(
                "camera:picamera2",
                message="import ok",
            ),
            make_check(
                "vision:service",
                ok=False,
                message="Vision service degraded",
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertFalse(result)
        self.assertEqual(
            print_message.call_args_list,
            [
                call(),
                call("Betabox Verification"),
                call("===================="),
                call(),
                call("[OK] camera:picamera2"),
                call("     import ok"),
                call("[FAIL] vision:service"),
                call("     Vision service degraded"),
                call(),
                call("Betabox verification failed."),
            ],
        )

    def test_empty_checks_passes(self) -> None:
        with patch("builtins.print"):
            result = print_results(())

        self.assertTrue(result)

    def test_does_not_print_empty_message(
        self,
    ) -> None:
        checks = (make_check("check:test"),)

        with patch("builtins.print") as print_message:
            print_results(checks)

        self.assertNotIn(
            call("     "),
            print_message.call_args_list,
        )

    def test_reports_each_failed_check(
        self,
    ) -> None:
        checks = (
            make_check(
                "check:one",
                ok=False,
            ),
            make_check(
                "check:two",
                ok=False,
            ),
        )

        with patch("builtins.print") as print_message:
            result = print_results(checks)

        self.assertFalse(result)
        self.assertIn(
            call("[FAIL] check:one"),
            print_message.call_args_list,
        )
        self.assertIn(
            call("[FAIL] check:two"),
            print_message.call_args_list,
        )

    def test_rejects_non_tuple_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                "checks must be a tuple",
            ),
        ):
            print_results(
                []  # type: ignore[arg-type]
            )

        print_message.assert_not_called()

    def test_rejects_invalid_check_before_printing(
        self,
    ) -> None:
        with (
            patch("builtins.print") as print_message,
            self.assertRaisesRegex(
                TypeError,
                ("checks must contain only CheckResult values"),
            ),
        ):
            print_results(
                (
                    object(),  # type: ignore[arg-type]
                )
            )

        print_message.assert_not_called()

    def test_validation_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.validate_checks",
                side_effect=error,
            ),
            patch("builtins.print") as print_message,
            self.assertRaises(RuntimeError) as context,
        ):
            print_results(())

        self.assertIs(
            context.exception,
            error,
        )
        print_message.assert_not_called()


class MainTests(unittest.TestCase):
    def test_returns_zero_when_checks_pass(
        self,
    ) -> None:
        checks = (make_check("check:test"),)

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ) as collect,
            patch(
                f"{MODULE}.print_results",
                return_value=True,
            ) as print_results_call,
        ):
            result = main()

        self.assertEqual(result, 0)
        collect.assert_called_once_with(
            config=DEFAULT_PLATFORM_CONFIG,
        )
        print_results_call.assert_called_once_with(checks)

    def test_returns_one_when_checks_fail(
        self,
    ) -> None:
        checks = (
            make_check(
                "check:test",
                ok=False,
            ),
        )

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(
                f"{MODULE}.print_results",
                return_value=False,
            ),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_returns_one_for_type_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.collect_checks",
                side_effect=TypeError("invalid configuration"),
            ),
            patch(f"{MODULE}.print_results") as print_results_call,
            patch("builtins.print") as print_message,
        ):
            result = main()

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid configuration")
        print_results_call.assert_not_called()

    def test_returns_one_for_value_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.collect_checks",
                side_effect=ValueError("invalid timeout"),
            ),
            patch(f"{MODULE}.print_results") as print_results_call,
            patch("builtins.print") as print_message,
        ):
            result = main()

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("invalid timeout")
        print_results_call.assert_not_called()

    def test_returns_one_for_os_error(
        self,
    ) -> None:
        with (
            patch(
                f"{MODULE}.collect_checks",
                side_effect=OSError("device unavailable"),
            ),
            patch(f"{MODULE}.print_results") as print_results_call,
            patch("builtins.print") as print_message,
        ):
            result = main()

        self.assertEqual(result, 1)
        print_message.assert_called_once_with("device unavailable")
        print_results_call.assert_not_called()

    def test_unexpected_collection_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("programming error")

        with (
            patch(
                f"{MODULE}.collect_checks",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main()

        self.assertIs(
            context.exception,
            error,
        )

    def test_print_results_error_propagates(
        self,
    ) -> None:
        error = RuntimeError("printing failed")
        checks = (make_check("check:test"),)

        with (
            patch(
                f"{MODULE}.collect_checks",
                return_value=checks,
            ),
            patch(
                f"{MODULE}.print_results",
                side_effect=error,
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            main()

        self.assertIs(
            context.exception,
            error,
        )


if __name__ == "__main__":
    unittest.main()
