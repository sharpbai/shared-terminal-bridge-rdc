import base64
import hashlib
import unittest

from stb_rdc.command_input import decode_chunks, decode_command
import contextlib
import io
import json
import shlex

from stb_rdc.workflow import rdc_workflow
from stb_rdc.cli import run
from tests.fakes import RunClient

class SegmentedBase64Test(unittest.TestCase):
    def test_valid_and_corrupted_chunks(self):
        raw = ("echo " + "x" * 66 + "中文").encode()
        parts = [base64.b64encode(raw[i:i+72]).decode() for i in range(0, len(raw), 72)]
        digest = hashlib.sha256(raw).hexdigest()[:16]
        self.assertEqual(decode_chunks([*parts, digest]), raw.decode())
        self.assertEqual(decode_command(base64.b64encode(raw).decode()), raw.decode())
        for values in ([parts[0], digest], [*parts, "0" * 16],
                       [parts[0], parts[1] + " ", digest], [digest]):
            with self.subTest(values=values), self.assertRaises(RuntimeError):
                decode_chunks(values)

    def test_bootstrap_script_produces_one_run(self):
        output = io.StringIO()
        workflow = rdc_workflow("verify33")["run_base64"]
        with contextlib.redirect_stdout(output):
            exec(workflow["python_example"], {})
        parts = json.loads(output.getvalue())
        self.assertGreater(len(parts), 2)
        args = workflow["call"]["arguments"]
        self.assertEqual(args["timeout_ms"], 1)
        argv = shlex.split(args["command"].split(" CHUNK1", 1)[0]) + parts
        client = RunClient()
        run(argv[1:], client)
        self.assertEqual([method for method, _ in client.calls],
                         ["terminal_session_resolve", "terminal_run"])
        self.assertEqual(client.calls[-1][1]["text"],
                         r"printf '%s\n' 'A read-only example for demonstrating short Base64 segments'")
        rejected = RunClient()
        with self.assertRaisesRegex(RuntimeError, "摘要不匹配"):
            run([*argv[1:-2], argv[-1]], rejected)
        self.assertEqual(rejected.calls, [])
