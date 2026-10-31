"""Direct and encoded input converge into one Core call."""
import base64
import contextlib
import io
import unittest
from stb_rdc.cli import run
from tests.fakes import RunClient

class CliRunTest(unittest.TestCase):
    def test_direct_and_base64_are_identical(self):
        for text in [r"""printf '%s\n' "$HOME" '中文'""", "echo " + "x" * 40000]:
            for options in (["--text", text], ["--base64", base64.b64encode(text.encode()).decode()]):
                client = RunClient()
                self.assertEqual(run(["run", "verify33", *options, "--wait-ms", "1"], client)["job_id"], "job-one")
                self.assertEqual([m for m, _ in client.calls], ["terminal_session_resolve", "terminal_run"])
                self.assertEqual(client.calls[-1][1]["text"], text)
                self.assertNotIn("request_id", client.calls[-1][1])

    def test_invalid_encoding_never_contacts_core(self):
        client = RunClient()
        with self.assertRaises(RuntimeError):
            run(["run", "verify33", "--base64", "!!"], client)
        self.assertEqual(client.calls, [])

    def test_removed_stdio_and_exclusive_inputs(self):
        for command, target in (("run", "verify33"),):
            for options in (["--stdio"], ["--stdin"], ["--text", "pwd", "--base64", "cHdk"]):
                client = RunClient()
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    run([command, target, *options], client)
                self.assertEqual(client.calls, [])
