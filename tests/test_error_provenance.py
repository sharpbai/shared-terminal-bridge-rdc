"""Contract tests for error provenance without live STB."""
import io
import json
import socket
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr

from stb_rdc.client import BridgeClient, BridgeError
from stb_rdc.errors import bridge_failure
from stb_rdc.cli import main
from stb_rdc.policy import interaction_policy


class ProvenanceTests(unittest.TestCase):
    def test_stb_error_preserves_code_and_layer(self):
        e = bridge_failure({"code": "EXECUTION_LEASE_INVALID", "pane": "%1"})
        self.assertEqual(e.as_dict()["error"]["layer"], "stb")
        self.assertEqual(e.as_dict()["error"]["code"], "EXECUTION_LEASE_INVALID")

    def test_missing_managed_session_is_adapter_layer(self):
        from tests.fakes import FakeBridgeClient
        e = None
        try:
            BridgeClient.session(FakeBridgeClient(), "missing")
        except BridgeError as error:
            e = error
        self.assertIsNotNone(e)
        self.assertEqual(e.code, "MANAGED_SESSION_NOT_FOUND")

    def test_transport_error_is_not_stb_denial(self):
        class DownSocket:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def connect(self, *args): raise ConnectionRefusedError("offline")
        with patch("stb_rdc.client.socket.socket", return_value=DownSocket()):
            with self.assertRaises(BridgeError) as captured:
                BridgeClient().call("bridge_info")
        self.assertEqual(captured.exception.layer, "local_transport")

    def test_cli_prints_machine_readable_error(self):
        class Denied:
            def call(self, *args, **kwargs):
                raise bridge_failure({"code": "PANE_ACCESS_DENIED"})
        stderr = io.StringIO()
        with patch("stb_rdc.cli.BridgeClient", return_value=Denied()):
            with redirect_stderr(stderr), self.assertRaises(SystemExit):
                main(["status"])
        self.assertEqual(json.loads(stderr.getvalue())["error"]["code"],
                         "PANE_ACCESS_DENIED")

    def test_policy_does_not_claim_upstream_observability(self):
        p = interaction_policy()
        self.assertIn("before adapter starts", p["error_provenance"]["upstream"])
        self.assertEqual(p["authorization_granularity"],
                         "task_or_risk_boundary_not_each_command")


if __name__ == "__main__":
    unittest.main()
