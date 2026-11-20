from subprocess import CompletedProcess
import unittest

from android_process_death import ProcessDeathCheck, run_check


class FakeAdb:
    def __init__(self):
        self.commands = []
        self.dumps = iter([
            '<hierarchy><node text="Draft 42" /></hierarchy>',
            '<hierarchy><node text="Draft 42" /></hierarchy>',
        ])

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        output = next(self.dumps) if command[-3:-1] == ["shell", "cat"] else ""
        if command[-3:] == ["shell", "pidof", "org.example.app"]:
            return CompletedProcess(command, 1, stdout="", stderr="")
        return CompletedProcess(command, 0, stdout=output, stderr="")


class ProcessDeathCheckTests(unittest.TestCase):
    def test_relaunches_after_force_stop_and_checks_before_and_after_state(self):
        fake = FakeAdb()
        result = run_check(ProcessDeathCheck(
            package="org.example.app",
            component="org.example.app/.MainActivity",
            expected_before=("Draft 42",),
            expected_after=("Draft 42",),
        ), runner=fake)
        self.assertTrue(result.passed)
        self.assertEqual("force-stop", result.mode)
        self.assertEqual(2, sum(command[1:4] == ["shell", "am", "start"] for command in fake.commands))
        self.assertTrue(any("force-stop" in command for command in fake.commands))

    def test_missing_restored_state_fails_the_check(self):
        class LostStateAdb(FakeAdb):
            def __init__(self):
                self.commands = []
                self.dumps = iter([
                    '<hierarchy><node text="Draft 42" /></hierarchy>',
                    '<hierarchy><node text="Empty" /></hierarchy>',
                ])
        result = run_check(ProcessDeathCheck(
            "org.example.app", "org.example.app/.MainActivity", ("Draft 42",), ("Draft 42",)
        ), runner=LostStateAdb())
        self.assertFalse(result.passed)
        self.assertEqual(("Draft 42",), result.after_missing)

    def test_rejects_invalid_component_before_invoking_adb(self):
        fake = FakeAdb()
        with self.assertRaises(ValueError):
            run_check(ProcessDeathCheck("org.example.app", "; rm -rf /", (), ()), runner=fake)
        self.assertEqual([], fake.commands)

    def test_background_kill_compares_a_captured_saved_state_marker(self):
        class MarkerAdb(FakeAdb):
            def __init__(self):
                self.commands = []
                self.dumps = iter([
                    '<hierarchy><node text="State: abc-123" /></hierarchy>',
                    '<hierarchy><node text="State: abc-123" /></hierarchy>',
                ])
        fake = MarkerAdb()
        result = run_check(ProcessDeathCheck(
            "org.example.app", "org.example.app/.MainActivity", (), (),
            mode="background-kill", persist_regex=r"State: ([A-Za-z0-9-]+)",
        ), runner=fake)
        self.assertTrue(result.passed)
        self.assertTrue(result.persisted_marker_preserved)
        self.assertTrue(any(command[1:4] == ["shell", "input", "keyevent"] for command in fake.commands))
        self.assertTrue(any(command[1:4] == ["shell", "am", "kill"] for command in fake.commands))

    def test_background_kill_fails_when_saved_state_marker_changes(self):
        class ChangedMarkerAdb(FakeAdb):
            def __init__(self):
                self.commands = []
                self.dumps = iter([
                    '<hierarchy><node text="State: before" /></hierarchy>',
                    '<hierarchy><node text="State: after" /></hierarchy>',
                ])
        result = run_check(ProcessDeathCheck(
            "org.example.app", "org.example.app/.MainActivity", (), (),
            mode="background-kill", persist_regex=r"State: ([A-Za-z0-9-]+)",
        ), runner=ChangedMarkerAdb())
        self.assertFalse(result.passed)
        self.assertFalse(result.persisted_marker_preserved)
        self.assertIn("captured state marker changed after process death", result.after_missing)


if __name__ == "__main__":
    unittest.main()
