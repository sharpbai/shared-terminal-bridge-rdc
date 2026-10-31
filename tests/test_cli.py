import unittest

from stb_rdc.cli import run, build_parser
from stb_rdc.config import ADAPTER_VERSION
from tests.fakes import FakeBridgeClient


class CliTests(unittest.TestCase):
    def test_list_returns_sessions(self) -> None:
        client = FakeBridgeClient()
        result = run(["list"], client)
        self.assertEqual(result["sessions"][0]["name"], "verify33")

    def test_default_observation_budgets(self):
        parser = build_parser()
        for command in ("bootstrap", "context"):
            self.assertEqual(parser.parse_args([command, "verify33"]).lines, 40)
        self.assertEqual(parser.parse_args(["run", "verify33", "--text", "pwd"]).wait_ms, 60000)
        for command in ("wait", "interrupt"):
            self.assertEqual(parser.parse_args([command, "job-1"]).seconds, 60)

    def test_info_only_returns_executing_job_in_selected_pane(self):
        class Jobs(FakeBridgeClient):
            def call(self, method, params=None):
                if method == "terminal_job_list":
                    return {"jobs": [
                        {"job_id": "active", "pane": "%5", "execution_phase": "EXECUTING"},
                        {"job_id": "other", "pane": "%6", "execution_phase": "EXECUTING"},
                        {"job_id": "done", "pane": "%5", "execution_phase": "FINISHED"}]}
                return super().call(method, params)
        client = Jobs()
        result = run(["info", "verify33"], client)
        self.assertEqual([job["job_id"] for job in result["current_jobs"]], ["active"])
        self.assertEqual(client.calls[0], ("terminal_session_resolve", {"name": "verify33"}))
        self.assertNotIn("terminal_run", [method for method, _ in client.calls])

    def test_context_maps_session_to_bounded_read(self) -> None:
        client = FakeBridgeClient()
        result = run(["context", "verify33", "--lines", "9"], client)
        self.assertEqual(result["context"]["content"], "ready")
        self.assertIn(("terminal_read", {"pane": "%5", "lines": 9}), client.calls)

    def test_old_send_is_removed(self) -> None:
        client = FakeBridgeClient()
        with self.assertRaises(SystemExit):
            run(["send", "verify33", "8", "df -h /"], client)
        self.assertEqual(client.calls, [])

    def test_lease_uses_resolved_managed_pane(self) -> None:
        client = FakeBridgeClient()
        with self.assertRaises(SystemExit):
            run(["lease", "verify33"], client)
        self.assertEqual(client.calls, [])

    def test_wait_converts_seconds_to_milliseconds(self) -> None:
        client = FakeBridgeClient()
        run(["wait", "job-1", "--seconds", "17"], client)
        self.assertEqual(
            client.calls[-1],
            ("terminal_wait_job", {"job_id": "job-1", "wait_ms": 17000}),
        )

    def test_interrupt_uses_authoritative_job_scope(self) -> None:
        client = FakeBridgeClient()
        run(["interrupt", "job-1"], client)
        self.assertEqual(
            client.calls[-1],
            ("terminal_interrupt_job", {"job_id": "job-1", "wait_ms": 60000}),
        )

    def test_job_reads_status_without_session_or_lease(self) -> None:
        client = FakeBridgeClient()
        result = run(["job", "job-1"], client)
        self.assertEqual(result["state"], "RUNNING")
        self.assertEqual(
            client.calls,
            [("terminal_job_status", {"job_id": "job-1"})],
        )


if __name__ == "__main__":
    unittest.main()
