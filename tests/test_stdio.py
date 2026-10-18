"""RDC stdin JSONL is data, not another shell command string."""

import io
import json
from pathlib import Path
import select
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from stb_rdc.stdio import serve
from stb_rdc.cli import main

COMMANDS = [
    "awk '{n[$1]++;s[$1]+=$2}'",
    '''printf '%s' "double ' single"''',
    r"printf '%s' 'C:\Users\name\file'",
    r"printf '%s' '\n\u0003'",
    "printf '%s' '中文 😀 $(not-executed) `not-executed`'",
    r"grep -E 'a\.[0-9]+$' file",
    "echo one\necho two", "\x03",
]


class Client:
    def __init__(self):
        self.calls = []

    def session(self, name):
        return {"pane": "%0"}

    def call(self, method, params=None):
        if method == "bridge_info":
            return {"command_request_dedup": "durable-submit-v1", "terminal_run": "receipt-scoped-run-v1", "model_tasks": "job-authority-v2"}
        self.calls.append((method, json.loads(json.dumps(params))))
        return {"accepted": True}


class StdioTest(unittest.TestCase):
    def test_complex_text_roundtrip_one_process_per_frame(self):
        client = Client()
        frames = [dict(id=f"command-{i}", op="run", session="test", params=dict(
            text=text)) for i, text in enumerate(COMMANDS)]
        output = io.StringIO()
        for frame in frames:
            serve(io.StringIO(json.dumps(frame) + "\n"), output, client)
        self.assertEqual([p["text"] for _, p in client.calls], COMMANDS)
        self.assertEqual([p["request_id"] for _, p in client.calls],
                         [f["id"] for f in frames])
        self.assertTrue(all(json.loads(line)["ok"] for line in output.getvalue().splitlines()))

    def test_malformed_frame_returns_error_and_ignores_following_frame(self):
        output = io.StringIO()
        client = Client()
        serve(io.StringIO('not json\n{"id":"next","op":"info"}\n'), output, client)
        results = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertFalse(results[0]["ok"])
        self.assertEqual(len(results), 1)
        self.assertEqual(client.calls, [])

    def test_old_core_fails_closed(self):
        client = Client()
        client.call = lambda *args: {}
        output = io.StringIO()
        serve(io.StringIO('{"id":"x","op":"submit","params":{"text":"echo x"}}\n'),
              output, client)
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_cli_stdout_contains_only_one_response(self):
        output = io.StringIO()
        with patch("stb_rdc.cli.BridgeClient", return_value=Client()), \
             patch("sys.stdin", io.StringIO('{"id":"x","op":"info"}\n')), \
             patch("sys.stdout", output):
            main(["serve-stdio"])
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertEqual(json.loads(output.getvalue())["id"], "x")

    def test_oversized_frame_exits_without_processing_another(self):
        output = io.StringIO()
        with patch("stb_rdc.stdio.MAX_FRAME", 40):
            serve(io.StringIO("x" * 100 + '\n{"id":"x","op":"info"}\n'), output, Client())
        frames = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertFalse(frames[0]["ok"])
        self.assertEqual(len(frames), 1)

    def test_no_read_past_first_request_even_when_stdin_stays_open(self):
        class Reader:
            def __init__(self):
                self.reads = 0
            def readline(self, limit):
                self.reads += 1
                if self.reads > 1:
                    raise AssertionError("must not wait for another line or EOF")
                return '{"id":"x","op":"info"}\n'
        reader = Reader()
        output = io.StringIO()
        serve(reader, output, Client())
        self.assertEqual(reader.reads, 1)
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_empty_stdin_has_no_response_and_incomplete_frame_is_rejected(self):
        output = io.StringIO()
        serve(io.StringIO(""), output, Client())
        self.assertEqual(output.getvalue(), "")
        serve(io.StringIO('{"id":"x","op":"info"}'), output, Client())
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_queued_second_submit_is_not_executed(self):
        frame = json.dumps(dict(id="one", op="run", params=dict(
            pane="%0", text="echo x"))) + "\n"
        client = Client()
        output = io.StringIO()
        serve(io.StringIO(frame + frame.replace('"one"', '"two"')), output, client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_real_process_exits_with_stdin_open_after_fragmented_request(self):
        # Fake the socket client, not the entrypoint or process lifecycle.
        code = ("from unittest.mock import patch; "
                "from tests.test_stdio import Client; from stb_rdc.cli import main; "
                "patch('stb_rdc.cli.BridgeClient',return_value=Client()).start(); "
                "main(['serve-stdio'])")
        process = subprocess.Popen([sys.executable, "-u", "-c", code],
            cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            process.stdin.write('{"id":"pipe-1",')
            process.stdin.flush()
            self.assertEqual(select.select([process.stdout], [], [], .05)[0], [])
            process.stdin.write('"op":"info"}\n')
            process.stdin.flush()
            self.assertTrue(select.select([process.stdout], [], [], 3)[0])
            self.assertTrue(json.loads(process.stdout.readline())["ok"])
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertFalse(process.stdin.closed)  # exit did not depend on EOF
            self.assertEqual(process.stdout.read(), "")
            self.assertEqual(process.stderr.read(), "")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

    def test_wait_response_is_not_returned_before_bridge_result(self):
        entered, release = threading.Event(), threading.Event()
        class WaitingClient(Client):
            def call(self, method, params=None):
                self.assert_method = method
                entered.set()
                release.wait(2)
                return {"state": "WAIT_CANCELLED"}
        output = io.StringIO()
        client = WaitingClient()
        task = threading.Thread(target=serve, args=(io.StringIO(
            '{"id":"wait-1","op":"wait","params":{"job_id":"one","wait_ms":600000}}\n'),
            output, client))
        task.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertEqual(output.getvalue(), "")
        finally:
            release.set()
            task.join(3)
        self.assertFalse(task.is_alive())
        self.assertEqual(client.assert_method, "terminal_wait_job")
        self.assertEqual(json.loads(output.getvalue())["result"]["state"], "WAIT_CANCELLED")
