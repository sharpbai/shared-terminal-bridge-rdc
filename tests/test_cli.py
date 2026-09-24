import unittest

from stb_rdc.cli import run
from tests.fakes import FakeBridgeClient


class CliTests(unittest.TestCase):
    def test_status_returns_adapter_and_bridge_metadata(self) -> None:
        client = FakeBridgeClient()
        result = run(["status"], client)
        self.assertEqual(result["adapter_version"], "0.2.3")
        self.assertEqual(result["bridge"]["name"], "STB")
        self.assertEqual(result["sessions"][0]["name"], "verify33")

    def test_context_maps_session_to_bounded_read(self) -> None:
        client = FakeBridgeClient()
        result = run(["context", "verify33", "--lines", "9"], client)
        self.assertEqual(result["terminal"]["content"], "ready")
        self.assertIn(("terminal_read", {"pane": "%5", "lines": 9}), client.calls)

    def test_send_preserves_text_and_generation(self) -> None:
        client = FakeBridgeClient()
        result = run(["send", "verify33", "8", "df -h /"], client)
        self.assertEqual(result["job_id"], "job-1")
        self.assertIn(
            (
                "terminal_submit",
                {"pane": "%5", "generation": 8, "text": "df -h /"},
            ),
            client.calls,
        )

    def test_lease_uses_resolved_managed_pane(self) -> None:
        client = FakeBridgeClient()
        result = run(["lease", "verify33"], client)
        self.assertEqual(result["generation"], 8)
        self.assertEqual(client.calls[-1], ("acquire_execution", {"pane": "%5"}))

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
            ("terminal_interrupt", {"pane": "%5", "generation": 8}),
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
