# Android Process-Death State Restoration Check

Exercise an Android app through a real `adb force-stop` and cold relaunch, then verify that important visible state survives. Use it for Android and Jetpack Compose state-restoration regression checks that should go beyond a saved-state unit test.

The runner uses Android's UI hierarchy dump to verify text before and after process death. Your app must display a test marker for the state being checked. It supports a durable cold-start check and a background-process kill mode that can exercise activity saved-state restoration.

## Install

```sh
python -m pip install android-process-death-check
```

Install Android platform-tools, enable USB debugging or start an emulator, and confirm the device is visible with `adb devices`.

## Run a check

```sh
android-process-death-check \
  --package com.example.notes \
  --component com.example.notes/.MainActivity \
  --expect-before "Draft 42" \
  --expect-after "Draft 42" \
  --mode background-kill \
  --persist-regex 'Draft marker: ([A-Za-z0-9-]+)'
```

The `force-stop` mode launches, checks, force-stops, and cold-starts the activity. The `background-kill` mode sends the app home, asks Android to kill its background process, verifies the process exited, and relaunches the existing task. With `--persist-regex`, the runner compares one captured marker before and after without printing the UI hierarchy. Use `--device SERIAL` when multiple devices are connected. Exit code `0` means assertions passed, `1` means state was missing or changed, and `2` means the adb check could not run.

## Compose and Android state testing

Keep transient UI state that must survive process death in `SavedStateHandle` or `rememberSaveable`, and durable application data in storage. Expose an accessibility marker from that state and compare it with `--persist-regex`. The background-kill mode approximates OS process reclamation; device/OS behavior varies, so pair it with instrumentation tests and test the Android versions you support. Avoid asserting transient animation or time-dependent labels.

The `example/` directory contains a small Compose app whose UUID is stored only through `rememberSaveable`. Build it with Android Studio or Gradle, install `dev.buxerr.processdeathfixture`, then run:

```sh
android-process-death-check \
  --package dev.buxerr.processdeathfixture \
  --component dev.buxerr.processdeathfixture/.MainActivity \
  --mode background-kill \
  --persist-regex 'Saved marker: ([a-f0-9-]+)'
```

The expected result is the same captured UUID after Android kills and recreates the background activity process.

## Development

```sh
python -m unittest discover -s tests -v
```

Keywords: Android process death test, Compose state restoration, adb force stop relaunch test, Android saved state CI, process recreation UI test.

## License

MIT
