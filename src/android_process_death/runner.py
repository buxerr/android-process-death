"""Launch, force-stop, and relaunch an Android app while checking visible state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import subprocess
import time
from typing import Callable, Sequence


PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
COMPONENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*/(?:\.[A-Za-z0-9_.$]+|[A-Za-z][A-Za-z0-9_.$]*)$")


@dataclass(frozen=True)
class ProcessDeathCheck:
    package: str
    component: str
    expected_before: tuple[str, ...]
    expected_after: tuple[str, ...]
    device: str | None = None
    adb: str = "adb"
    timeout_seconds: int = 30
    mode: str = "force-stop"
    persist_regex: str | None = None
    background_settle_seconds: float = 1.0


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    mode: str
    before_missing: tuple[str, ...]
    after_missing: tuple[str, ...]
    persisted_marker_preserved: bool | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _base(check: ProcessDeathCheck) -> list[str]:
    command = [check.adb]
    if check.device:
        command.extend(["-s", check.device])
    return command


def _run(command: Sequence[str], timeout: int, runner: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    result = runner(list(command), check=False, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "adb command failed").strip()
        raise RuntimeError(message)
    return result.stdout


def _visible_xml(check: ProcessDeathCheck, runner: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    base = _base(check)
    _run([*base, "shell", "uiautomator", "dump", "/sdcard/window.xml"], check.timeout_seconds, runner)
    return _run([*base, "shell", "cat", "/sdcard/window.xml"], check.timeout_seconds, runner)


def _wait_for_process_exit(
    check: ProcessDeathCheck,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    command = [*_base(check), "shell", "pidof", check.package]
    for _ in range(40):
        result = runner(command, check=False, capture_output=True, text=True, timeout=check.timeout_seconds)
        if result.returncode != 0 or not result.stdout.strip():
            return
        time.sleep(0.25)
    raise RuntimeError("Android app process remained alive after the background kill")


def _wait_until_background(
    check: ProcessDeathCheck,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    command = [*_base(check), "shell", "dumpsys", "activity", "activities"]
    resumed_activity = re.compile(
        rf"(?im)^\s*(?:topResumedActivity|mResumedActivity|ResumedActivity)\s*[:=]\s*[^\n]*"
        rf"\b{re.escape(check.package)}/"
    )
    deadline = time.monotonic() + check.timeout_seconds
    while True:
        activities = _run(command, check.timeout_seconds, runner)
        if not resumed_activity.search(activities):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Android app remained in the foreground after HOME")
        time.sleep(0.25)


def _missing(xml: str, expected: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(text for text in expected if text not in xml)


def run_check(
    check: ProcessDeathCheck,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> CheckResult:
    if (
        not PACKAGE_RE.match(check.package)
        or not COMPONENT_RE.match(check.component)
        or check.component.split("/", 1)[0] != check.package
    ):
        raise ValueError("package and component must be valid; component format is package/.Activity")
    if check.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if check.background_settle_seconds < 0:
        raise ValueError("background_settle_seconds must not be negative")
    if check.mode not in {"force-stop", "background-kill"}:
        raise ValueError("mode must be force-stop or background-kill")
    persist_pattern = None
    if check.persist_regex:
        try:
            persist_pattern = re.compile(check.persist_regex)
        except re.error as exc:
            raise ValueError(f"persist_regex is invalid: {exc}") from exc
        if persist_pattern.groups != 1:
            raise ValueError("persist_regex must contain exactly one capture group")

    base = _base(check)
    _run([*base, "shell", "am", "start", "-W", "-n", check.component], check.timeout_seconds, runner)
    before_xml = _visible_xml(check, runner)
    before_missing = list(_missing(before_xml, check.expected_before))
    if check.mode == "force-stop":
        _run([*base, "shell", "am", "force-stop", check.package], check.timeout_seconds, runner)
    else:
        _run([*base, "shell", "input", "keyevent", "HOME"], check.timeout_seconds, runner)
        _wait_until_background(check, runner)
        if check.background_settle_seconds:
            time.sleep(check.background_settle_seconds)
        _run([*base, "shell", "am", "kill", check.package], check.timeout_seconds, runner)
        _wait_for_process_exit(check, runner)
    _run([*base, "shell", "am", "start", "-W", "-n", check.component], check.timeout_seconds, runner)
    after_xml = _visible_xml(check, runner)
    after_missing = list(_missing(after_xml, check.expected_after))
    persisted_marker_preserved: bool | None = None
    if persist_pattern is not None:
        before_match = persist_pattern.search(before_xml)
        after_match = persist_pattern.search(after_xml)
        persisted_marker_preserved = bool(before_match and after_match and before_match.group(1) == after_match.group(1))
        if not before_match:
            before_missing.append("persist-regex did not match before process death")
        if not after_match:
            after_missing.append("persist-regex did not match after relaunch")
        elif before_match and before_match.group(1) != after_match.group(1):
            after_missing.append("captured state marker changed after process death")
    passed = not before_missing and not after_missing and persisted_marker_preserved is not False
    return CheckResult(passed, check.mode, tuple(before_missing), tuple(after_missing), persisted_marker_preserved)
