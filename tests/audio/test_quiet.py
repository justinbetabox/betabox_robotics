import io
import sys
import unittest
from contextlib import redirect_stderr

from betabox_robotics.audio.quiet import suppress_stderr


class SuppressStderrTests(unittest.TestCase):
    def test_context_enters_and_exits(self) -> None:
        with suppress_stderr():
            pass

    def test_nested_contexts(self) -> None:
        with suppress_stderr(), suppress_stderr():
            pass

    def test_python_stderr_is_restored(self) -> None:
        original = io.StringIO()

        with redirect_stderr(original):
            print("before", file=original)

            with suppress_stderr():
                # Writes to Python stderr object still work.
                # Native fd 2 is what is redirected.
                print("inside", file=original)

            print("after", file=original)

        self.assertEqual(
            original.getvalue(),
            "before\ninside\nafter\n",
        )

    def test_exception_inside_context_restores_stderr(self) -> None:
        with self.assertRaises(RuntimeError), suppress_stderr():
            raise RuntimeError("boom")

        # If stderr wasn't restored correctly,
        # later code may fail.
        print("still works", file=sys.stderr)
