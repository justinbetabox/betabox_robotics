from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from betabox_robotics.launchpad.status_cache import StatusCache

MODULE = "betabox_robotics.launchpad.status_cache"


class StatusCacheConstructionTests(unittest.TestCase):
    def test_defaults(
        self,
    ) -> None:
        cache = StatusCache()

        self.assertEqual(
            cache.ttl_seconds,
            3.0,
        )
        self.assertIsNone(
            cache.payload,
        )
        self.assertEqual(
            cache.collected_at,
            0.0,
        )
        self.assertIsInstance(
            cache.lock,
            asyncio.Lock,
        )

    def test_normalizes_numeric_values(
        self,
    ) -> None:
        cache = StatusCache(
            ttl_seconds=3,
            collected_at=2,
        )

        self.assertEqual(
            cache.ttl_seconds,
            3.0,
        )
        self.assertEqual(
            cache.collected_at,
            2.0,
        )

    def test_copies_initial_payload(
        self,
    ) -> None:
        payload = {
            "status": "ok",
        }

        cache = StatusCache(
            payload=payload,
        )

        self.assertEqual(
            cache.payload,
            payload,
        )
        self.assertIsNot(
            cache.payload,
            payload,
        )

    def test_rejects_invalid_ttl(
        self,
    ) -> None:
        for value in (
            True,
            "3",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "ttl_seconds must be a number",
                ),
            ):
                StatusCache(
                    ttl_seconds=value,  # type: ignore[arg-type]
                )

    def test_rejects_nonpositive_ttl(
        self,
    ) -> None:
        for value in (
            0,
            -1,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "ttl_seconds must be greater than 0",
                ),
            ):
                StatusCache(
                    ttl_seconds=value,
                )

    def test_rejects_invalid_payload(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "payload must be a dictionary",
        ):
            StatusCache(
                payload="invalid",  # type: ignore[arg-type]
            )

    def test_rejects_invalid_collected_at(
        self,
    ) -> None:
        for value in (
            True,
            "1",
            None,
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    TypeError,
                    "collected_at must be a number",
                ),
            ):
                StatusCache(
                    collected_at=value,  # type: ignore[arg-type]
                )

    def test_rejects_negative_collected_at(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "collected_at cannot be negative",
        ):
            StatusCache(
                collected_at=-1,
            )

    def test_rejects_invalid_lock(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "lock must be an asyncio.Lock",
        ):
            StatusCache(
                lock=object(),  # type: ignore[arg-type]
            )

    def test_is_slotted(
        self,
    ) -> None:
        cache = StatusCache()

        self.assertFalse(
            hasattr(
                cache,
                "__dict__",
            )
        )


class IsFreshTests(unittest.TestCase):
    def test_without_payload_is_not_fresh(
        self,
    ) -> None:
        cache = StatusCache(
            collected_at=10.0,
        )

        self.assertFalse(cache.is_fresh())

    def test_recent_payload_is_fresh(
        self,
    ) -> None:
        cache = StatusCache(
            ttl_seconds=3.0,
            payload={
                "status": "ok",
            },
            collected_at=10.0,
        )

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=12.0,
        ):
            self.assertTrue(cache.is_fresh())

    def test_expired_payload_is_not_fresh(
        self,
    ) -> None:
        cache = StatusCache(
            ttl_seconds=3.0,
            payload={
                "status": "ok",
            },
            collected_at=10.0,
        )

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=13.0,
        ):
            self.assertFalse(cache.is_fresh())

    def test_future_timestamp_is_not_fresh(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "ok",
            },
            collected_at=20.0,
        )

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=10.0,
        ):
            self.assertFalse(cache.is_fresh())


class GetTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_fresh_cached_payload_without_collection(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "cached",
            },
            collected_at=10.0,
        )
        collector = Mock(
            return_value={
                "status": "new",
            },
        )

        with (
            patch(
                f"{MODULE}.time.monotonic",
                return_value=11.0,
            ),
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(),
            ) as to_thread,
        ):
            result = await cache.get(collector)

        self.assertEqual(
            result,
            {
                "status": "cached",
            },
        )
        collector.assert_not_called()
        to_thread.assert_not_awaited()

    async def test_collects_stale_payload_in_thread(
        self,
    ) -> None:
        cache = StatusCache()
        collector = Mock(
            return_value={
                "status": "new",
            },
        )

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(
                    return_value={
                        "status": "new",
                    }
                ),
            ) as to_thread,
            patch(
                f"{MODULE}.time.monotonic",
                return_value=25.0,
            ),
        ):
            result = await cache.get(collector)

        to_thread.assert_awaited_once_with(collector)
        self.assertEqual(
            result,
            {
                "status": "new",
            },
        )
        self.assertEqual(
            cache.payload,
            {
                "status": "new",
            },
        )
        self.assertEqual(
            cache.collected_at,
            25.0,
        )

    async def test_returns_copy_of_cached_payload(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "ok",
            },
            collected_at=10.0,
        )

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=11.0,
        ):
            first = await cache.get(
                lambda: {
                    "status": "new",
                }
            )
            second = await cache.get(
                lambda: {
                    "status": "new",
                }
            )

        self.assertEqual(
            first,
            second,
        )
        self.assertIsNot(
            first,
            cache.payload,
        )
        self.assertIsNot(
            second,
            cache.payload,
        )

    async def test_returned_payload_cannot_mutate_cache_top_level(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "ok",
            },
            collected_at=10.0,
        )

        with patch(
            f"{MODULE}.time.monotonic",
            return_value=11.0,
        ):
            result = await cache.get(
                lambda: {
                    "status": "new",
                }
            )

        result["status"] = "changed"

        self.assertEqual(
            cache.payload,
            {
                "status": "ok",
            },
        )

    async def test_rejects_noncallable_collector(
        self,
    ) -> None:
        cache = StatusCache()

        with self.assertRaisesRegex(
            TypeError,
            "collector must be callable",
        ):
            await cache.get(
                1  # type: ignore[arg-type]
            )

    async def test_rejects_invalid_collector_payload(
        self,
    ) -> None:
        cache = StatusCache()

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(return_value="invalid"),
            ),
            self.assertRaisesRegex(
                TypeError,
                "payload must be a dictionary",
            ),
        ):
            await cache.get(
                dict  # type: ignore[return-value]
            )

        self.assertIsNone(cache.payload)
        self.assertEqual(
            cache.collected_at,
            0.0,
        )

    async def test_collector_error_propagates_without_updating_cache(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "stale",
            },
            collected_at=1.0,
        )
        error = RuntimeError(
            "collection failed",
        )

        with (
            patch(
                f"{MODULE}.time.monotonic",
                return_value=10.0,
            ),
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(side_effect=error),
            ),
            self.assertRaises(RuntimeError) as context,
        ):
            await cache.get(dict)

        self.assertIs(
            context.exception,
            error,
        )
        self.assertEqual(
            cache.payload,
            {
                "status": "stale",
            },
        )
        self.assertEqual(
            cache.collected_at,
            1.0,
        )

    async def test_second_waiter_uses_payload_collected_by_first(
        self,
    ) -> None:
        cache = StatusCache()
        collector = Mock(
            return_value={
                "status": "new",
            },
        )
        collection_started = asyncio.Event()
        allow_collection = asyncio.Event()
        calls = 0

        async def to_thread_side_effect(
            function: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            collection_started.set()
            await allow_collection.wait()
            return {
                "status": "new",
            }

        with (
            patch(
                f"{MODULE}.asyncio.to_thread",
                new=AsyncMock(
                    side_effect=to_thread_side_effect,
                ),
            ),
            patch(
                f"{MODULE}.time.monotonic",
                return_value=10.0,
            ),
        ):
            first = asyncio.create_task(cache.get(collector))
            await collection_started.wait()

            second = asyncio.create_task(cache.get(collector))

            await asyncio.sleep(0)
            allow_collection.set()

            first_result, second_result = await asyncio.gather(
                first,
                second,
            )

        self.assertEqual(
            calls,
            1,
        )
        self.assertEqual(
            first_result,
            {
                "status": "new",
            },
        )
        self.assertEqual(
            second_result,
            {
                "status": "new",
            },
        )


class ClearTests(unittest.TestCase):
    def test_clear_resets_payload_and_timestamp(
        self,
    ) -> None:
        cache = StatusCache(
            payload={
                "status": "ok",
            },
            collected_at=10.0,
        )
        lock = cache.lock

        cache.clear()

        self.assertIsNone(
            cache.payload,
        )
        self.assertEqual(
            cache.collected_at,
            0.0,
        )
        self.assertIs(
            cache.lock,
            lock,
        )


if __name__ == "__main__":
    unittest.main()
