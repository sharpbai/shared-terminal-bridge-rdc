import unittest

from stb_rdc.cli import run
from stb_rdc.config import ADAPTER_VERSION
from tests.fakes import FakeBridgeClient


class CliTests(unittest.TestCase):
    def test_status_returns_adapter_and_bridge_metadata(self) -> None:
        client = FakeBridgeClient()
        result = run(["status"], client)
        self.assertEqual(result["adapter_version"], ADAPTER_VERSION)
        self.assertEqual(result["bridge"]["name"], "STB")
        self.assertEqual(result["sessions"][0]["name"], "verify33")

    def test_context_maps_session_to_bounded_read(self) -> None:
        client = FakeBridgeClient()
        result = run(["context", "verify33", "--lines", "9"], client)
        self.assertEqual(result["terminal"]["content"], "ready")
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
            ("terminal_interrupt_job", {"job_id": "job-1"}),
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
