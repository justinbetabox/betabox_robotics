from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
    BETABOX_HARDWARE_GROUPS,
    BETABOX_SHARED_GROUP,
    ProvisionedAccount,
    _validate_account_name,
    _validate_bool,
    _validate_name,
    _validate_optional_password,
    _validate_password_max_days,
    _validate_path,
    account_by_username,
)


def make_account(
    **overrides: object,
) -> ProvisionedAccount:
    values: dict[str, object] = {
        "username": "student4",
        "display_name": "Student 4",
        "group": "student4",
        "home": Path("/home/student4"),
        "shell": Path("/bin/bash"),
        "password": None,
        "password_max_days": None,
        "supplemental_groups": (BETABOX_HARDWARE_GROUPS),
        "persistent": True,
        "install_media": True,
    }

    values.update(overrides)

    return ProvisionedAccount(
        **values  # type: ignore[arg-type]
    )


class ValidateNameTests(unittest.TestCase):
    def test_accepts_and_normalizes_name(self) -> None:
        self.assertEqual(
            _validate_name(
                " Student ",
                field_name="display_name",
            ),
            "Student",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "display_name must be a string",
                ),
            ):
                _validate_name(
                    value,
                    field_name="display_name",
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
                    "display_name cannot be empty",
                ),
            ):
                _validate_name(
                    value,
                    field_name="display_name",
                )


class ValidateAccountNameTests(unittest.TestCase):
    def test_accepts_valid_names(self) -> None:
        for value in (
            "student",
            "student1",
            "robot_user",
            "_service",
            "robot-user",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    _validate_account_name(
                        value,
                        field_name="username",
                    ),
                    value,
                )

    def test_normalizes_whitespace(self) -> None:
        self.assertEqual(
            _validate_account_name(
                " student1 ",
                field_name="username",
            ),
            "student1",
        )

    def test_rejects_invalid_names(self) -> None:
        for value in (
            "Student",
            "1student",
            "student.name",
            "student name",
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValueError),
            ):
                _validate_account_name(
                    value,
                    field_name="username",
                )


class ValidatePathTests(unittest.TestCase):
    def test_accepts_absolute_path(self) -> None:
        path = Path("/home/student")

        self.assertEqual(
            _validate_path(
                path,
                field_name="home",
            ),
            path,
        )

    def test_accepts_absolute_string(self) -> None:
        self.assertEqual(
            _validate_path(
                "/bin/bash",
                field_name="shell",
            ),
            Path("/bin/bash"),
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "home must be a string or Path",
                ),
            ):
                _validate_path(
                    value,
                    field_name="home",
                )

    def test_rejects_relative_path(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "home must be an absolute path",
        ):
            _validate_path(
                "home/student",
                field_name="home",
            )


class OptionalPasswordTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(_validate_optional_password(None))

    def test_accepts_password(self) -> None:
        self.assertEqual(
            _validate_optional_password("classroom-password"),
            "classroom-password",
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            123,
            True,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "password must be a string or None",
                ),
            ):
                _validate_optional_password(value)

    def test_rejects_empty_password(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "password cannot be empty",
        ):
            _validate_optional_password("")


class PasswordMaxDaysTests(unittest.TestCase):
    def test_accepts_none(self) -> None:
        self.assertIsNone(_validate_password_max_days(None))

    def test_accepts_positive_integer(self) -> None:
        self.assertEqual(
            _validate_password_max_days(90),
            90,
        )

    def test_rejects_invalid_type(self) -> None:
        for value in (
            True,
            90.0,
            "90",
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "password_max_days must be an integer or None",
                ),
            ):
                _validate_password_max_days(value)

    def test_rejects_non_positive_value(self) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "password_max_days must be at least 1",
                ),
            ):
                _validate_password_max_days(value)


class ValidateBoolTests(unittest.TestCase):
    def test_accepts_booleans(self) -> None:
        self.assertTrue(
            _validate_bool(
                True,
                field_name="persistent",
            )
        )
        self.assertFalse(
            _validate_bool(
                False,
                field_name="persistent",
            )
        )

    def test_rejects_non_boolean(self) -> None:
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
                    "persistent must be a boolean",
                ),
            ):
                _validate_bool(
                    value,
                    field_name="persistent",
                )


class ProvisionedAccountTests(unittest.TestCase):
    def test_create(self) -> None:
        account = make_account()

        self.assertEqual(
            account.username,
            "student4",
        )
        self.assertEqual(
            account.display_name,
            "Student 4",
        )
        self.assertEqual(
            account.group,
            "student4",
        )
        self.assertEqual(
            account.home,
            Path("/home/student4"),
        )
        self.assertEqual(
            account.shell,
            Path("/bin/bash"),
        )
        self.assertEqual(
            account.supplemental_groups,
            BETABOX_HARDWARE_GROUPS,
        )
        self.assertTrue(account.persistent)
        self.assertTrue(account.install_media)

    def test_normalizes_fields(self) -> None:
        account = make_account(
            username=" student4 ",
            display_name=" Student 4 ",
            group=" student4 ",
            home="/home/student4",
            shell="/bin/bash",
        )

        self.assertEqual(
            account.username,
            "student4",
        )
        self.assertEqual(
            account.display_name,
            "Student 4",
        )
        self.assertEqual(
            account.group,
            "student4",
        )
        self.assertEqual(
            account.home,
            Path("/home/student4"),
        )
        self.assertEqual(
            account.shell,
            Path("/bin/bash"),
        )

    def test_rejects_non_tuple_groups(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "supplemental_groups must be a tuple",
        ):
            make_account(
                supplemental_groups=[
                    "gpio",
                ],
            )

    def test_rejects_duplicate_groups(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "supplemental_groups cannot contain duplicates",
        ):
            make_account(
                supplemental_groups=(
                    "gpio",
                    "gpio",
                ),
            )

    def test_rejects_invalid_group_name(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "supplemental group contains invalid characters",
        ):
            make_account(
                supplemental_groups=("Bad Group",),
            )

    def test_rejects_invalid_flags(self) -> None:
        for field_name in (
            "persistent",
            "install_media",
        ):
            with (
                self.subTest(field=field_name),
                self.assertRaisesRegex(
                    TypeError,
                    f"{field_name} must be a boolean",
                ),
            ):
                make_account(
                    **{
                        field_name: 1,
                    }
                )

    def test_is_frozen(self) -> None:
        account = make_account()

        with self.assertRaises(FrozenInstanceError):
            account.username = "changed"  # type: ignore[misc]


class AccountTableTests(unittest.TestCase):
    def test_expected_accounts_exist(self) -> None:
        self.assertEqual(
            tuple(account.username for account in BETABOX_ACCOUNTS),
            (
                "guest",
                "admin",
                "student",
                "student1",
                "student2",
                "student3",
            ),
        )

    def test_usernames_are_unique(self) -> None:
        usernames = [account.username for account in BETABOX_ACCOUNTS]

        self.assertEqual(
            len(usernames),
            len(set(usernames)),
        )

    def test_all_accounts_have_hardware_groups(self) -> None:
        for account in BETABOX_ACCOUNTS:
            with self.subTest(username=account.username):
                self.assertEqual(
                    account.supplemental_groups,
                    BETABOX_HARDWARE_GROUPS,
                )

    def test_shared_group_is_in_hardware_groups(self) -> None:
        self.assertIn(
            BETABOX_SHARED_GROUP,
            BETABOX_HARDWARE_GROUPS,
        )

    def test_guest_is_non_persistent(self) -> None:
        guest = account_by_username("guest")

        self.assertFalse(guest.persistent)
        self.assertEqual(
            guest.shell,
            Path("/usr/sbin/nologin"),
        )

    def test_non_guest_accounts_are_persistent(self) -> None:
        for account in BETABOX_ACCOUNTS:
            if account.username == "guest":
                continue

            with self.subTest(username=account.username):
                self.assertTrue(account.persistent)

    def test_runtime_accounts_do_not_store_passwords(self) -> None:
        for account in BETABOX_ACCOUNTS:
            with self.subTest(username=account.username):
                self.assertIsNone(account.password)


class AccountLookupTests(unittest.TestCase):
    def test_returns_account_by_username(self) -> None:
        account = account_by_username("student1")

        self.assertEqual(
            account.username,
            "student1",
        )
        self.assertEqual(
            account.display_name,
            "Student 1",
        )

    def test_normalizes_whitespace(self) -> None:
        account = account_by_username(" student1 ")

        self.assertEqual(
            account.username,
            "student1",
        )

    def test_rejects_unknown_username(self) -> None:
        with self.assertRaisesRegex(
            LookupError,
            "Unknown managed Betabox account: unknown",
        ):
            account_by_username("unknown")

    def test_preserves_lookup_error_cause(self) -> None:
        with self.assertRaises(LookupError) as context:
            account_by_username("unknown")

        self.assertIsInstance(
            context.exception.__cause__,
            KeyError,
        )

    def test_rejects_invalid_username(self) -> None:
        for value in (
            "Student1",
            "student one",
            "",
            "   ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ValueError),
            ):
                account_by_username(value)

    def test_rejects_invalid_username_type(self) -> None:
        for value in (
            123,
            None,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "username must be a string",
                ),
            ):
                account_by_username(
                    value  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()
