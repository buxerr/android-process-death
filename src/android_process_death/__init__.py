"""Black-box Android process-death checks driven by adb."""

from .runner import CheckResult, ProcessDeathCheck, run_check

__all__ = ["CheckResult", "ProcessDeathCheck", "run_check"]
