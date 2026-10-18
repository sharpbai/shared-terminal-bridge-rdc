"""One discovery response supplies context and the next JSON requests, read-only."""
import io
import json
import unittest
from unittest import mock
import contextlib

from stb_rdc.stdio import serve
from stb_rdc.policy import PROTOCOL_REVISION, bootstrap
from tests.fakes import FakeBridgeClient
from stb_rdc.cli import build_parser, dispatch, main


class BootstrapStdinTest(unittest.TestCase):
    def test_default_output_guides_without_help_or_bridge(self):
        for argv in ([], None):
            output = io.StringIO()
            with mock.patch("sys.argv", ["stb-rdc"]), \
                    mock.patch("stb_rdc.cli.BridgeClient") as bridge, \
                    contextlib.redirect_stdout(output):
                main(argv)
            bridge.assert_not_called()
            self.assertIn("Agent 首次使用：stb-rdc bootstrap SESSION", output.getvalue())
            self.assertIn("{status,serve-stdio,bootstrap,context,wait,job,interrupt}", output.getvalue())
            self.assertNotIn("timeout_ms=1", output.getvalue())
            with mock.patch("sys.argv", ["stb-rdc"]):
                self.assertEqual(output.getvalue(), build_parser().format_help())

    def test_cli_guides_direct_discovery_and_matches_stdin(self):
        parser = build_parser()
        self.assertIn("Agent 首次使用：stb-rdc bootstrap", parser.format_help())
        for options in ([], ["--detailed"]):
            args = parser.parse_args(["bootstrap", "verify33", *options])
            result = dispatch(args, FakeBridgeClient())
            self.assertEqual(result, bootstrap(FakeBridgeClient(), "verify33", detailed=bool(options)))

    def test_compact_default_and_explicit_details(self):
        compact = bootstrap(FakeBridgeClient(), "verify33")
        full = bootstrap(FakeBridgeClient(), "verify33", detailed=True)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(full)))
        self.assertLess(len(json.dumps(compact["interaction_policy"])), 2000)
        self.assertIn("never repeat", compact["bootstrap_result"]["repeat_bootstrap"])
        policy = json.dumps(compact["interaction_policy"])
        for rule in ("Ctrl+C", "approval", "ACL", "same", "job", "one-shot"):
            if rule == "same":
                rule = "identical"
            self.assertIn(rule, policy)
        response = self.request(dict(id="d", op="bootstrap", session="verify33",
                                     params={"detailed": True}), FakeBridgeClient())
        self.assertEqual(response["result"], full)
        self.assertFalse(self.request(dict(id="bad", op="bootstrap", session="verify33",
                                          params={"detailed": "yes"}), FakeBridgeClient())["ok"])

    def request(self, frame, client):
        output = io.StringIO()
        serve(io.StringIO(json.dumps(frame) + "\n"), output, client)
        return json.loads(output.getvalue())

    def test_bootstrap_restores_discovery_without_lease_or_execution(self):
        client = FakeBridgeClient()
        response = self.request(dict(id="discover", op="bootstrap", session="verify33"), client)
        self.assertTrue(response["ok"], response)
        result = response["result"]
        self.assertEqual(result["protocol_revision"], PROTOCOL_REVISION)
        self.assertTrue(result["bootstrap_result"]["discovery_only"])
        self.assertFalse(result["bootstrap_result"]["task_executed"])
        self.assertEqual([m for m, _ in client.calls], ["bridge_info",
            "terminal_session_list", "terminal_state", "terminal_read"])
        self.assertEqual(client.calls[-1][1]["lines"], 20)
        self.assertNotIn("submit", result["request_templates"])
        self.assertNotIn("lease", result["request_templates"])
        self.assertEqual(result["request_templates"]["wait"]["params"]["wait_ms"], 600000)
        self.assertIn("no routine README", result["bootstrap_result"]["next_step"])

    def test_cli_and_stdin_share_existing_bootstrap(self):
        frame = dict(id="discover", op="bootstrap", session="verify33", params={"lines": 12})
        self.assertEqual(self.request(frame, FakeBridgeClient())["result"],
                         bootstrap(FakeBridgeClient(), "verify33", 12))

    def test_invalid_parameters_never_call_bridge(self):
        frames = [dict(id="x", op="bootstrap"), dict(id="x", op="bootstrap", session=""),
            *[dict(id="x", op="bootstrap", session="verify33", params={"lines": n})
              for n in [0, 101, True, "20"]],
            dict(id="x", op="bootstrap", session="verify33", params={"text": "echo x"}),
            dict(id="x", op="bootstrap", session="verify33", params={"pane": "%5"})]
        for frame in frames:
            client = FakeBridgeClient()
            self.assertFalse(self.request(frame, client)["ok"])
            self.assertEqual(client.calls, [])

    def test_missing_session_has_structured_error_without_execution(self):
        client = FakeBridgeClient()
        self.assertFalse(self.request(dict(id="x", op="bootstrap", session="missing"), client)["ok"])
        self.assertEqual([m for m, _ in client.calls], ["bridge_info", "terminal_session_list"])
