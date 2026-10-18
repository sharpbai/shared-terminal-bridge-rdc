"""The default adapter contract never delegates authority bookkeeping."""
import io
import json
import unittest
from stb_rdc.stdio import serve
from stb_rdc.model_view import model_view
from stb_rdc.policy import request_templates
from tests.test_stdio_run import RunClient


class ModelContractTest(unittest.TestCase):
    def test_old_operations_and_authority_injection_are_rejected(self):
        for op, params in [("lease", {}), ("submit", {"text": "echo x"}),
                           ("run", {"text": "echo x", "generation": 7}),
                           ("run", {"text": "echo x", "_authorization": {}})]:
            client, output = RunClient(), io.StringIO()
            serve(io.StringIO(json.dumps(dict(id="x", op=op, params=params)) + "\n"), output, client)
            self.assertFalse(json.loads(output.getvalue())["ok"])
            self.assertEqual(client.calls, [])

    def test_interrupt_uses_job_only_and_input_maps_id(self):
        client, output = RunClient(), io.StringIO()
        client.call = lambda method, params=None: (client.calls.append((method, params)) or {"generation": 8, "ok": True})
        for op, params in [("interrupt", {"job_id": "one"})]:
            serve(io.StringIO(json.dumps(dict(id="x", op=op, params=params)) + "\n"), output, client)
        self.assertEqual(client.calls, [("terminal_interrupt_job", {"job_id": "one"})])
        self.assertNotIn("generation", json.loads(output.getvalue())["result"])

    def test_templates_and_views_hide_counters_not_terminal_strings(self):
        templates = request_templates("test", True)
        self.assertNotIn("lease", templates)
        self.assertNotIn("submit", templates)
        self.assertEqual(templates["interrupt"]["params"], {"job_id": "FROM_RUN"})
        value = {"generation": 9, "lease": {}, "output": "generation=9 \\u0003",
                 "error": {"code": "EXECUTION_LEASE_INVALID", "generation": 9}}
        filtered = model_view(value)
        self.assertEqual(filtered["output"], value["output"])
        self.assertEqual(filtered["error"], {"code": "JOB_NOT_CURRENT"})
