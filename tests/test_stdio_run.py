"""run maps to one Core request, never a local sequence of execution calls."""
import io
import json
import unittest

from stb_rdc.policy import bootstrap, interaction_policy
from stb_rdc.stdio import serve
from tests.fakes import FakeBridgeClient


class RunClient(FakeBridgeClient):
    def call(self, method, params=None):
        if method == "bridge_info":
            self.calls.append((method, params or {}))
            return {"terminal_run": "receipt-scoped-run-v1",
                    "model_tasks": "job-authority-v2",
                    "command_request_dedup": "durable-submit-v1"}
        if method == "terminal_run":
            self.calls.append((method, params))
            return {"job_id": "job-one", "state": "COMPLETED", "generation": 8}
        return super().call(method, params)


class StdinRunTest(unittest.TestCase):
    def test_one_core_call_preserves_text_id_and_wait(self):
        client = RunClient()
        frame = dict(id="run-unique", op="run", session="verify33", params=dict(
            text="awk '{n[$1]++;s[$1]+=$2}'", expected_duration_ms=1000,
            resource_class="normal", wait_ms=600000))
        output = io.StringIO()
        serve(io.StringIO(json.dumps(frame) + "\n"), output, client)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        self.assertEqual([m for m, _ in client.calls],
                         ["terminal_session_list", "bridge_info", "terminal_run"])
        self.assertEqual(client.calls[-1][1], dict(frame["params"], pane="%5", request_id=frame["id"]))

    def test_old_core_has_no_unsafe_split_fallback(self):
        client = FakeBridgeClient()
        output = io.StringIO()
        serve(io.StringIO('{"id":"x","op":"run","session":"verify33","params":{"text":"echo x"}}\n'), output, client)
        self.assertFalse(json.loads(output.getvalue())["ok"])
        self.assertNotIn("acquire_execution", [m for m, _ in client.calls])
        self.assertNotIn("terminal_submit", [m for m, _ in client.calls])

    def test_bootstrap_advertises_run_only_when_core_supports_it(self):
        modern = bootstrap(RunClient(), "verify33")
        legacy = bootstrap(FakeBridgeClient(), "verify33")
        self.assertIn("run", modern["request_templates"])
        self.assertNotIn("generation", modern["request_templates"]["run"]["params"])
        self.assertNotIn("run", legacy["request_templates"])
        transport = interaction_policy()["command_transport"]
        self.assertEqual(transport["startup_request"],
                         {"command": "stb-rdc serve-stdio", "timeout_ms": 1})
        self.assertIn("not 1000", transport["startup_timeout_rule"])
