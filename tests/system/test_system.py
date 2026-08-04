from __future__ import annotations

import subprocess
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from betabox_robotics.system import (
    MediaPaths,
    System,
    SystemError,
    SystemHealth,
    SystemStatus,
)
from betabox_robotics.version import __version__


class MediaPathsTests(unittest.TestCase):
    def test_create(self) -> None:
        paths = MediaPaths(
            pictures=Path("/media/pictures"),
            videos=Path("/media/videos"),
            sounds=Path("/media/sounds"),
        )

        self.assertEqual(
            paths.all,
            (
                Path("/media/pictures"),
                Path("/media/videos"),
                Path("/media/sounds"),
            ),
        )

    def test_accepts_string_paths(self) -> None:
        paths = MediaPaths(
            pictures="/media/pictures",  # type: ignore[arg-type]
            videos="/media/videos",  # type: ignore[arg-type]
            sounds="/media/sounds",  # type: ignore[arg-type]
        )

        self.assertEqual(
            paths.pictures,
            Path("/media/pictures"),
        )
        self.assertEqual(
            paths.videos,
            Path("/media/videos"),
        )
        self.assertEqual(
            paths.sounds,
            Path("/media/sounds"),
        )

    def test_rejects_invalid_path_values(self) -> None:
        for field_name in (
            "pictures",
            "videos",
            "sounds",
        ):
            for value in (
                True,
                123,
                object(),
            ):
                with (
                    self.subTest(
                        field=field_name,
                        value=value,
                    ),
                    self.assertRaises(TypeError),
                ):
                    kwargs: dict[str, object] = {
                        "pictures": Path("/pictures"),
                        "videos": Path("/videos"),
                        "sounds": Path("/sounds"),
                    }

                    kwargs[field_name] = value

                    MediaPaths(**kwargs)  # type: ignore[arg-type]

    def test_exists_returns_true_when_all_exist(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            paths = MediaPaths(
                pictures=root / "pictures",
                videos=root / "videos",
                sounds=root / "sounds",
            )

            for path in paths.all:
                path.mkdir()

            self.assertTrue(paths.exists())

    def test_exists_returns_false_when_any_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            paths = MediaPaths(
                pictures=root / "pictures",
                videos=root / "videos",
                sounds=root / "sounds",
            )

            paths.pictures.mkdir()
            paths.videos.mkdir()

            self.assertFalse(paths.exists())

    def test_to_dict(self) -> None:
        paths = MediaPaths(
            pictures=Path("/media/pictures"),
            videos=Path("/media/videos"),
            sounds=Path("/media/sounds"),
        )

        self.assertEqual(
            paths.to_dict(),
            {
                "pictures": "/media/pictures",
                "videos": "/media/videos",
                "sounds": "/media/sounds",
            },
        )

    def test_is_frozen(self) -> None:
        paths = MediaPaths(
            pictures=Path("/pictures"),
            videos=Path("/videos"),
            sounds=Path("/sounds"),
        )

        with self.assertRaises(FrozenInstanceError):
            paths.pictures = Path("/other")  # type: ignore[misc]


class SystemStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.media = MediaPaths(
            pictures=Path("/media/pictures"),
            videos=Path("/media/videos"),
            sounds=Path("/media/sounds"),
        )

    def test_create(self) -> None:
        status = SystemStatus(
            version="1.0.0",
            hostname="Betabox-1234",
            ip_addresses=(
                "192.168.1.10",
                "10.0.0.1",
            ),
            media=self.media,
        )

        self.assertEqual(
            status.version,
            "1.0.0",
        )
        self.assertEqual(
            status.hostname,
            "Betabox-1234",
        )
        self.assertEqual(
            status.ip_addresses,
            (
                "192.168.1.10",
                "10.0.0.1",
            ),
        )

    def test_normalizes_strings(self) -> None:
        status = SystemStatus(
            version=" 1.0.0 ",
            hostname=" Betabox-1234 ",
            ip_addresses=(" 192.168.1.10 ",),
            media=self.media,
        )

        self.assertEqual(
            status.version,
            "1.0.0",
        )
        self.assertEqual(
            status.hostname,
            "Betabox-1234",
        )
        self.assertEqual(
            status.ip_addresses,
            ("192.168.1.10",),
        )

    def test_rejects_invalid_version(self) -> None:
        for value in (
            123,
            None,
            " ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ),
            ):
                SystemStatus(
                    version=value,  # type: ignore[arg-type]
                    hostname="Betabox",
                    ip_addresses=(),
                    media=self.media,
                )

    def test_rejects_invalid_hostname(self) -> None:
        for value in (
            123,
            None,
            " ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ),
            ):
                SystemStatus(
                    version="1.0.0",
                    hostname=value,  # type: ignore[arg-type]
                    ip_addresses=(),
                    media=self.media,
                )

    def test_rejects_non_tuple_addresses(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "ip_addresses must be a tuple",
        ):
            SystemStatus(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=[  # type: ignore[arg-type]
                    "192.168.1.10",
                ],
                media=self.media,
            )

    def test_rejects_invalid_address(self) -> None:
        for value in (
            123,
            " ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ),
            ):
                SystemStatus(
                    version="1.0.0",
                    hostname="Betabox",
                    ip_addresses=(
                        value,  # type: ignore[arg-type]
                    ),
                    media=self.media,
                )

    def test_rejects_invalid_media(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "media must be a MediaPaths",
        ):
            SystemStatus(
                version="1.0.0",
                hostname="Betabox",
                ip_addresses=(),
                media=object(),  # type: ignore[arg-type]
            )

    def test_to_dict(self) -> None:
        status = SystemStatus(
            version="1.0.0",
            hostname="Betabox",
            ip_addresses=("192.168.1.10",),
            media=self.media,
        )

        self.assertEqual(
            status.to_dict(),
            {
                "version": "1.0.0",
                "hostname": "Betabox",
                "ip_addresses": [
                    "192.168.1.10",
                ],
                "media": self.media.to_dict(),
            },
        )


class SystemHealthTests(unittest.TestCase):
    def test_create(self) -> None:
        health = SystemHealth(
            ok=False,
            messages=("missing directory",),
        )

        self.assertFalse(health.ok)
        self.assertEqual(
            health.messages,
            ("missing directory",),
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
                SystemHealth(
                    ok=value,  # type: ignore[arg-type]
                    messages=(),
                )

    def test_rejects_non_tuple_messages(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "messages must be a tuple",
        ):
            SystemHealth(
                ok=True,
                messages=[],  # type: ignore[arg-type]
            )

    def test_rejects_invalid_message(self) -> None:
        for value in (
            123,
            " ",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(
                    (
                        TypeError,
                        ValueError,
                    )
                ),
            ):
                SystemHealth(
                    ok=False,
                    messages=(
                        value,  # type: ignore[arg-type]
                    ),
                )

    def test_to_dict(self) -> None:
        health = SystemHealth(
            ok=False,
            messages=(
                "first",
                "second",
            ),
        )

        self.assertEqual(
            health.to_dict(),
            {
                "ok": False,
                "messages": [
                    "first",
                    "second",
                ],
            },
        )


class SystemConstructionTests(unittest.TestCase):
    def test_default_media_root(self) -> None:
        with patch(
            "betabox_robotics.system.system.Path.home",
            return_value=Path("/home/picar"),
        ):
            system = System()

        self.assertEqual(
            system.media_paths(),
            MediaPaths(
                pictures=Path("/home/picar/media/pictures"),
                videos=Path("/home/picar/media/videos"),
                sounds=Path("/home/picar/media/sounds"),
            ),
        )

    def test_custom_media_root(self) -> None:
        system = System(media_root="~/robot-media")

        self.assertEqual(
            system.media_paths().pictures,
            Path("~/robot-media").expanduser() / "pictures",
        )

    def test_rejects_invalid_media_root(
        self,
    ) -> None:
        for value in (
            True,
            123,
            object(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "media_root must be a string or Path",
                ),
            ):
                System(
                    media_root=value  # type: ignore[arg-type]
                )

    def test_default_factory(self) -> None:
        config = SimpleNamespace(media_root=Path("/custom/media"))

        system = System.default(
            config  # type: ignore[arg-type]
        )

        self.assertEqual(
            system.media_paths().pictures,
            Path("/custom/media/pictures"),
        )

    def test_default_rejects_missing_media_root(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "config must provide media_root",
        ):
            System.default(
                object()  # type: ignore[arg-type]
            )


class SystemOperationTests(unittest.TestCase):
    def test_hostname(self) -> None:
        system = System()

        with patch(
            "betabox_robotics.system.system.socket.gethostname",
            return_value="Betabox-1234",
        ):
            self.assertEqual(
                system.hostname(),
                "Betabox-1234",
            )

    def test_hostname_normalizes_value(
        self,
    ) -> None:
        system = System()

        with patch(
            "betabox_robotics.system.system.socket.gethostname",
            return_value=" Betabox-1234 ",
        ):
            self.assertEqual(
                system.hostname(),
                "Betabox-1234",
            )

    def test_hostname_wraps_os_error(
        self,
    ) -> None:
        system = System()

        with (
            patch(
                "betabox_robotics.system.system.socket.gethostname",
                side_effect=OSError("failed"),
            ),
            self.assertRaisesRegex(
                SystemError,
                "failed to read hostname",
            ),
        ):
            system.hostname()

    def test_hostname_rejects_invalid_result(
        self,
    ) -> None:
        system = System()

        for value in (
            "",
            " ",
            123,
        ):
            with (
                self.subTest(value=value),
                patch(
                    "betabox_robotics.system.system.socket.gethostname",
                    return_value=value,
                ),
                self.assertRaisesRegex(
                    SystemError,
                    "invalid hostname",
                ),
            ):
                system.hostname()

    def test_ip_addresses(self) -> None:
        system = System()

        result = subprocess.CompletedProcess(
            args=[
                "hostname",
                "-I",
            ],
            returncode=0,
            stdout=("127.0.0.1 192.168.1.20 10.0.0.5 192.168.1.20\n"),
            stderr="",
        )

        with patch(
            "betabox_robotics.system.system.subprocess.run",
            return_value=result,
        ) as run:
            addresses = system.ip_addresses()

        self.assertEqual(
            addresses,
            (
                "192.168.1.20",
                "10.0.0.5",
            ),
        )
        run.assert_called_once_with(
            [
                "hostname",
                "-I",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

    def test_ip_addresses_returns_empty_on_failure_code(
        self,
    ) -> None:
        system = System()

        result = subprocess.CompletedProcess(
            args=[
                "hostname",
                "-I",
            ],
            returncode=1,
            stdout="",
            stderr="failed",
        )

        with patch(
            "betabox_robotics.system.system.subprocess.run",
            return_value=result,
        ):
            self.assertEqual(
                system.ip_addresses(),
                (),
            )

    def test_ip_addresses_returns_empty_on_os_error(
        self,
    ) -> None:
        system = System()

        with patch(
            "betabox_robotics.system.system.subprocess.run",
            side_effect=OSError("missing"),
        ):
            self.assertEqual(
                system.ip_addresses(),
                (),
            )

    def test_ip_addresses_returns_empty_on_timeout(
        self,
    ) -> None:
        system = System()

        with patch(
            "betabox_robotics.system.system.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=[
                    "hostname",
                    "-I",
                ],
                timeout=3,
            ),
        ):
            self.assertEqual(
                system.ip_addresses(),
                (),
            )

    def test_media_paths(self) -> None:
        system = System(media_root=Path("/media"))

        self.assertEqual(
            system.media_paths(),
            MediaPaths(
                pictures=Path("/media/pictures"),
                videos=Path("/media/videos"),
                sounds=Path("/media/sounds"),
            ),
        )

    def test_ensure_media_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            system = System(media_root=Path(temp_dir))

            paths = system.ensure_media_paths()

            self.assertTrue(paths.pictures.is_dir())
            self.assertTrue(paths.videos.is_dir())
            self.assertTrue(paths.sounds.is_dir())
            self.assertTrue(paths.exists())

    def test_ensure_media_paths_wraps_error(
        self,
    ) -> None:
        system = System(media_root=Path("/media"))

        with (
            patch(
                "betabox_robotics.system.system.Path.mkdir",
                side_effect=OSError("permission denied"),
            ),
            self.assertRaisesRegex(
                SystemError,
                "failed to create media directories",
            ),
        ):
            system.ensure_media_paths()

    def test_status(self) -> None:
        system = System(media_root=Path("/media"))

        with (
            patch.object(
                system,
                "hostname",
                return_value="Betabox-1234",
            ),
            patch.object(
                system,
                "ip_addresses",
                return_value=("192.168.1.20",),
            ),
        ):
            status = system.status()

        self.assertEqual(
            status,
            SystemStatus(
                version=__version__,
                hostname="Betabox-1234",
                ip_addresses=("192.168.1.20",),
                media=MediaPaths(
                    pictures=Path("/media/pictures"),
                    videos=Path("/media/videos"),
                    sounds=Path("/media/sounds"),
                ),
            ),
        )

    def test_health_when_paths_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            system = System(media_root=Path(temp_dir))
            system.ensure_media_paths()

            health = system.health()

        self.assertTrue(health.ok)
        self.assertEqual(
            health.messages,
            (),
        )

    def test_health_when_paths_are_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            system = System(media_root=root)

            health = system.health()

        self.assertFalse(health.ok)
        self.assertEqual(
            health.messages,
            (
                f"missing media directory: {root / 'pictures'}",
                f"missing media directory: {root / 'videos'}",
                f"missing media directory: {root / 'sounds'}",
            ),
        )

    def test_stop_all_is_no_op_while_open(
        self,
    ) -> None:
        system = System()

        self.assertIsNone(system.stop_all())


class SystemLifecycleTests(unittest.TestCase):
    def test_initially_open(self) -> None:
        self.assertFalse(System().closed)

    def test_close(self) -> None:
        system = System()

        system.close()

        self.assertTrue(system.closed)

    def test_close_is_idempotent(self) -> None:
        system = System()

        system.close()
        system.close()

        self.assertTrue(system.closed)

    def test_deinit_closes_system(self) -> None:
        system = System()

        system.deinit()

        self.assertTrue(system.closed)

    def test_context_manager(self) -> None:
        system = System()

        with system as active:
            self.assertIs(
                active,
                system,
            )
            self.assertFalse(system.closed)

        self.assertTrue(system.closed)

    def test_closed_system_rejects_operations(
        self,
    ) -> None:
        operations = (
            lambda system: system.hostname(),
            lambda system: system.ip_addresses(),
            lambda system: system.media_paths(),
            lambda system: system.ensure_media_paths(),
            lambda system: system.status(),
            lambda system: system.stop_all(),
            lambda system: system.health(),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                system = System()
                system.close()

                with self.assertRaisesRegex(
                    SystemError,
                    "system subsystem is closed",
                ):
                    operation(system)

    def test_closed_system_rejects_context_entry(
        self,
    ) -> None:
        system = System()
        system.close()

        with (
            self.assertRaisesRegex(
                SystemError,
                "system subsystem is closed",
            ),
            system,
        ):
            pass


if __name__ == "__main__":
    unittest.main()
