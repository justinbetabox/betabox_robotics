"""
Betabox platform services.
"""

from .verify import CheckResult, collect_checks, main

__all__ = [
    "CheckResult",
    "collect_checks",
    "main",
]
