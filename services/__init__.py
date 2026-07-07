"""
Betabox platform services.
"""

from .install_check import main as install_check_main
from .verify import CheckResult, collect_checks, main as verify_main

__all__ = [
    "CheckResult",
    "collect_checks",
    "install_check_main",
    "verify_main",
]
