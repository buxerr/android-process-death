"""CLI for black-box Android process-death checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from .runner import ProcessDeathCheck, run_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="android-process-death-check",
        description="Force-stop and relaunch an Android app, then check visible state through adb.",
    )
    parser.add_argument("--package", required=True, help="application package ID")
    parser.add_argument("--component", required=True, help="launcher component, e.g. org.example/.MainActivity")
    parser.add_argument("--expect-before", action="append", default=[], help="text expected in the UI before process death")
    parser.add_argument("--expect-after", action="append", default=[], help="persisted UI text expected after relaunch")
    parser.add_argument("--device", help="adb device serial when more than one device is connected")
    parser.add_argument("--adb", default="adb", help="path to adb executable")
    parser.add_argument("--timeout", type=int, default=30, help="seconds allowed for each adb command")
    parser.add_argument("--mode", choices=["force-stop", "background-kill"], default="force-stop",
                        help="force-stop for durable cold-start checks; background-kill to exercise saved activity state")
    parser.add_argument("--persist-regex", help="one capture group matched before and after process death")
    parser.add_argument("--background-settle", type=float, default=1.0,
                        help="seconds to wait after pressing Home before asking Android to kill the app")
    args = parser.parse_args(argv)
    try:
        result = run_check(ProcessDeathCheck(
            package=args.package,
            component=args.component,
            expected_before=tuple(args.expect_before),
            expected_after=tuple(args.expect_after),
            device=args.device,
            adb=args.adb,
            timeout_seconds=args.timeout,
            mode=args.mode,
            persist_regex=args.persist_regex,
            background_settle_seconds=args.background_settle,
        ))
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"Process-death check failed to run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
