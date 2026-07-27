from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from betabox_robotics.services.accounts import (
    BETABOX_ACCOUNTS,
    ProvisionedAccount,
    account_by_username,
)
from betabox_robotics.services.workspace import (
    workspace_directories,
)

from deployment.provision.accounts import (
    create_account,
    ensure_account_group,
    ensure_account_password,
    ensure_group_member,
    ensure_password_policy,
    ensure_service_user_access,
    reconcile_account,
    user_is_group_member,
)


class ManagedAccountDefinitionTests(
    unittest.TestCase,
):
    """Tests for managed Betabox account definitions."""

    def test_expected_accounts_are_defined(
        self,
    ) -> None:
        usernames = {account.username for account in BETABOX_ACCOUNTS}

        self.assertEqual(
            usernames,
            {
                "guest",
                "student",
                "student1",
                "student2",
                "student3",
            },
        )

    def test_guest_is_non_interactive(
        self,
    ) -> None:
        guest = account_by_username("guest")

        self.assertEqual(
            guest.shell,
            Path("/usr/sbin/nologin"),
        )
        self.assertFalse(guest.persistent)

    def test_students_use_bash(
        self,
    ) -> None:
        for username in (
            "student",
            "student1",
            "student2",
            "student3",
        ):
            with self.subTest(username=username):
                account = account_by_username(username)

                self.assertEqual(
                    account.shell,
                    Path("/bin/bash"),
                )
                self.assertTrue(account.persistent)

    def test_account_lookup_rejects_unknown_user(
        self,
    ) -> None:
        with self.assertRaises(LookupError):
            account_by_username("not-a-betabox-account")

    def test_workspace_directories_exclude_home(
        self,
    ) -> None:
        account = account_by_username("student")

        self.assertNotIn(
            account.home,
            workspace_directories(account),
        )

    def test_students_have_classroom_password_policy(
        self,
    ) -> None:
        for username in (
            "student",
            "student1",
            "student2",
            "student3",
        ):
            with self.subTest(username=username):
                account = account_by_username(username)

                self.assertEqual(
                    account.password,
                    "learnbydoing",
                )
                self.assertIsNone(
                    account.password_max_days,
                )

    def test_guest_has_no_password(
        self,
    ) -> None:
        guest = account_by_username("guest")

        self.assertIsNone(guest.password)

    def test_account_definitions_have_no_machine_specific_groups(
        self,
    ) -> None:
        for account in BETABOX_ACCOUNTS:
            with self.subTest(username=account.username):
                self.assertEqual(
                    account.supplemental_groups,
                    (),
                )


class AccountCreationTests(
    unittest.TestCase,
):
    """Tests for Linux account creation commands."""

    @patch("deployment.provision.accounts.run_command")
    def test_create_account_uses_expected_options(
        self,
        run_command,
    ) -> None:
        account = ProvisionedAccount(
            username="student-test",
            display_name="Test Student",
            group="student-test",
            home=Path("/home/student-test"),
            shell=Path("/bin/bash"),
        )

        create_account(account)

        run_command.assert_called_once_with(
            "useradd",
            "--create-home",
            "--home-dir",
            "/home/student-test",
            "--shell",
            "/bin/bash",
            "--gid",
            "student-test",
            "student-test",
        )


class AccountGroupTests(
    unittest.TestCase,
):
    """Tests for managed Linux groups."""

    @patch("deployment.provision.accounts.run_command")
    @patch(
        "deployment.provision.accounts.group_exists",
        return_value=False,
    )
    def test_missing_group_is_created(
        self,
        group_exists,
        run_command,
    ) -> None:
        account = ProvisionedAccount(
            username="student-test",
            display_name="Test Student",
            group="student-test",
            home=Path("/home/student-test"),
            shell=Path("/bin/bash"),
        )

        ensure_account_group(account)

        run_command.assert_called_once_with(
            "groupadd",
            "student-test",
        )

    @patch("deployment.provision.accounts.run_command")
    @patch(
        "deployment.provision.accounts.group_exists",
        return_value=True,
    )
    def test_existing_group_is_unchanged(
        self,
        group_exists,
        run_command,
    ) -> None:
        account = account_by_username("student")

        ensure_account_group(account)

        run_command.assert_not_called()


class ExistingAccountTests(
    unittest.TestCase,
):
    """Tests for existing managed accounts."""

    @patch("deployment.provision.accounts.run_command")
    @patch("deployment.provision.accounts.grp.getgrnam")
    @patch("deployment.provision.accounts.pwd.getpwnam")
    def test_current_account_is_unchanged(
        self,
        getpwnam,
        getgrnam,
        run_command,
    ) -> None:
        account = account_by_username("student")

        getpwnam.return_value = SimpleNamespace(
            pw_dir="/home/student",
            pw_shell="/bin/bash",
            pw_gid=1001,
        )

        getgrnam.return_value = SimpleNamespace(
            gr_gid=1001,
        )

        reconcile_account(account)

        run_command.assert_not_called()

    @patch("deployment.provision.accounts.run_command")
    @patch("deployment.provision.accounts.grp.getgrnam")
    @patch("deployment.provision.accounts.pwd.getpwnam")
    def test_incorrect_shell_is_repaired(
        self,
        getpwnam,
        getgrnam,
        run_command,
    ) -> None:
        account = account_by_username("student")

        getpwnam.return_value = SimpleNamespace(
            pw_dir="/home/student",
            pw_shell="/usr/sbin/nologin",
            pw_gid=1001,
        )

        getgrnam.return_value = SimpleNamespace(
            gr_gid=1001,
        )

        reconcile_account(account)

        run_command.assert_called_once_with(
            "usermod",
            "--shell",
            "/bin/bash",
            "student",
        )

    @patch("deployment.provision.accounts.run_command")
    @patch("deployment.provision.accounts.grp.getgrnam")
    @patch("deployment.provision.accounts.pwd.getpwnam")
    def test_incorrect_primary_group_is_repaired(
        self,
        getpwnam,
        getgrnam,
        run_command,
    ) -> None:
        account = account_by_username("student")

        getpwnam.return_value = SimpleNamespace(
            pw_dir="/home/student",
            pw_shell="/bin/bash",
            pw_gid=1000,
        )

        getgrnam.return_value = SimpleNamespace(
            gr_gid=1001,
        )

        reconcile_account(account)

        run_command.assert_called_once_with(
            "usermod",
            "--gid",
            "student",
            "student",
        )


class AccountPasswordTests(
    unittest.TestCase,
):
    """Tests for managed account password policy."""

    @patch("deployment.provision.accounts.subprocess.run")
    def test_student_password_is_set(
        self,
        subprocess_run,
    ) -> None:
        account = account_by_username("student")

        ensure_account_password(account)

        subprocess_run.assert_called_once_with(
            ["chpasswd"],
            input="student:learnbydoing\n",
            text=True,
            check=True,
        )

    @patch("deployment.provision.accounts.subprocess.run")
    def test_guest_password_is_not_set(
        self,
        subprocess_run,
    ) -> None:
        account = account_by_username("guest")

        ensure_account_password(account)

        subprocess_run.assert_not_called()

    @patch("deployment.provision.accounts.run_command")
    def test_student_password_never_expires(
        self,
        run_command,
    ) -> None:
        account = account_by_username("student")

        ensure_password_policy(account)

        run_command.assert_called_once_with(
            "chage",
            "--maxdays",
            "-1",
            "student",
        )

    @patch("deployment.provision.accounts.run_command")
    def test_guest_has_no_password_policy(
        self,
        run_command,
    ) -> None:
        account = account_by_username("guest")

        ensure_password_policy(account)

        run_command.assert_not_called()

    @patch("deployment.provision.accounts.run_command")
    def test_finite_password_expiration_is_applied(
        self,
        run_command,
    ) -> None:
        account = ProvisionedAccount(
            username="student-test",
            display_name="Test Student",
            group="student-test",
            home=Path("/home/student-test"),
            shell=Path("/bin/bash"),
            password="learnbydoing",
            password_max_days=90,
        )

        ensure_password_policy(account)

        run_command.assert_called_once_with(
            "chage",
            "--maxdays",
            "90",
            "student-test",
        )


class SupplementalGroupTests(
    unittest.TestCase,
):
    """Tests for supplemental group membership."""

    @patch("deployment.provision.accounts.grp.getgrnam")
    @patch("deployment.provision.accounts.pwd.getpwnam")
    def test_primary_group_counts_as_membership(
        self,
        getpwnam,
        getgrnam,
    ) -> None:
        getpwnam.return_value = SimpleNamespace(
            pw_gid=1001,
        )
        getgrnam.return_value = SimpleNamespace(
            gr_gid=1001,
            gr_mem=[],
        )

        self.assertTrue(
            user_is_group_member(
                "student",
                "student",
            )
        )

    @patch("deployment.provision.accounts.grp.getgrnam")
    @patch("deployment.provision.accounts.pwd.getpwnam")
    def test_supplemental_membership_is_detected(
        self,
        getpwnam,
        getgrnam,
    ) -> None:
        getpwnam.return_value = SimpleNamespace(
            pw_gid=1000,
        )
        getgrnam.return_value = SimpleNamespace(
            gr_gid=1001,
            gr_mem=["pi"],
        )

        self.assertTrue(
            user_is_group_member(
                "pi",
                "student",
            )
        )

    @patch("deployment.provision.accounts.run_command")
    @patch(
        "deployment.provision.accounts.user_is_group_member",
        return_value=False,
    )
    def test_missing_membership_is_added(
        self,
        user_is_member,
        run_command,
    ) -> None:
        ensure_group_member(
            "pi",
            "student",
        )

        run_command.assert_called_once_with(
            "usermod",
            "--append",
            "--groups",
            "student",
            "pi",
        )

    @patch("deployment.provision.accounts.run_command")
    @patch(
        "deployment.provision.accounts.user_is_group_member",
        return_value=True,
    )
    def test_existing_membership_is_unchanged(
        self,
        user_is_member,
        run_command,
    ) -> None:
        ensure_group_member(
            "pi",
            "student",
        )

        run_command.assert_not_called()


class ServiceUserAccessTests(
    unittest.TestCase,
):
    """Tests for service-user workspace access."""

    @patch("deployment.provision.accounts.ensure_group_member")
    def test_service_user_is_added_to_student_group(
        self,
        ensure_member,
    ) -> None:
        account = account_by_username("student")

        ensure_service_user_access(
            account,
            "pi",
        )

        ensure_member.assert_called_once_with(
            "pi",
            "student",
        )

    @patch("deployment.provision.accounts.ensure_group_member")
    def test_service_user_is_not_added_to_guest_group(
        self,
        ensure_member,
    ) -> None:
        account = account_by_username("guest")

        ensure_service_user_access(
            account,
            "pi",
        )

        ensure_member.assert_not_called()

    @patch("deployment.provision.accounts.ensure_group_member")
    def test_missing_service_user_is_ignored(
        self,
        ensure_member,
    ) -> None:
        account = account_by_username("student")

        ensure_service_user_access(
            account,
            None,
        )

        ensure_member.assert_not_called()

    @patch("deployment.provision.accounts.ensure_group_member")
    def test_account_is_not_added_to_its_own_group(
        self,
        ensure_member,
    ) -> None:
        account = account_by_username("student")

        ensure_service_user_access(
            account,
            "student",
        )

        ensure_member.assert_not_called()


if __name__ == "__main__":
    unittest.main()
