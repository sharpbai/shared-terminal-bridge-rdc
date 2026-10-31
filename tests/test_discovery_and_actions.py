"""Current CLI discovery and job actions, without legacy JSONL choreography."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from stb_rdc.cli import build_parser, dispatch, main, run
from stb_rdc.policy import bootstrap
from stb_rdc.model_view import model_view
from tests.fakes import FakeBridgeClient, RunClient


class CurrentContractTest(unittest.TestCase):
    def test_base64_selection_visible_in_command_help_and_bootstrap(self):
        from stb_rdc.policy import INPUT_SELECTION
        for command, target in (("run", "verify33"),):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                build_parser().parse_args([command, target, "--help"])
            for term in ("200", "Unicode", "--base64", "--text", "反斜杠", "$"):
                self.assertIn(term, output.getvalue())
        result = bootstrap(RunClient(), "verify33")
        for command in ("run",):
            self.assertEqual(result["commands"][command]["input_selection"], INPUT_SELECTION)

    def test_default_help_is_read_only_and_has_no_legacy_entry(self):
        output = io.StringIO()
        with patch('stb_rdc.cli.BridgeClient') as client, contextlib.redirect_stdout(output):
            main([])
        client.assert_not_called()
        self.assertIn('bootstrap SESSION', output.getvalue())
        self.assertNotIn('serve-stdio', output.getvalue())
        self.assertNotIn('approve', output.getvalue())
        self.assertNotIn('reject', output.getvalue())
        self.assertNotIn('input', output.getvalue())

    def test_removed_commands_fail_before_core(self):
        for name in ('serve-stdio', 'lease', 'release', 'send', 'approve', 'reject', 'input'):
            client = RunClient()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                run([name], client)
            self.assertEqual(client.calls, [])

    def test_bootstrap_is_complete_and_does_not_write(self):
        client = RunClient()
        result = bootstrap(client, 'verify33')
        self.assertNotIn('bootstrap_result', result)
        self.assertNotIn('terminal_run', [m for m, _ in client.calls])
        self.assertEqual([m for m, p in client.calls],
                         ['bridge_info', 'terminal_session_resolve', 'terminal_state', 'terminal_read', 'terminal_job_list'])
        templates = json.dumps(result['commands'])
        for removed in ('NEW_UNIQUE', 'serve-stdio', 'generation', '"op"'):
            self.assertNotIn(removed, templates)
        self.assertNotIn('input', result['commands'])
        self.assertNotIn('approve', result['commands'])
        self.assertLess(len(json.dumps(result['transport'], ensure_ascii=False)), 2000)

    def test_core_error_is_preserved_without_probe_or_retry(self):
        from stb_rdc.errors import bridge_failure, BridgeError
        class Denied(RunClient):
            def call(self, method, params=None):
                if method == "terminal_run":
                    self.calls.append((method, params))
                    raise bridge_failure({"code": "PANE_ACCESS_DENIED"})
                return super().call(method, params)
        client = Denied()
        with self.assertRaises(BridgeError) as captured:
            run(["run", "verify33", "--text", "pwd"], client)
        self.assertEqual(captured.exception.code, "PANE_ACCESS_DENIED")
        self.assertEqual([m for m, _ in client.calls], ["terminal_session_resolve", "terminal_run"])

    def test_interrupt_keeps_confirmation_and_wait_budget(self):
        client = RunClient()
        client.call = lambda m, p=None: (client.calls.append((m, p)) or {
            'termination_confirmed': False, 'generation': 7})
        result = run(['interrupt', 'job-real', '--seconds', '4'], client)
        self.assertFalse(result['termination_confirmed'])
        self.assertNotIn('generation', result)
        self.assertEqual(client.calls, [('terminal_interrupt_job', {'job_id': 'job-real', 'wait_ms': 4000})])

    def test_views_do_not_rewrite_terminal_strings(self):
        value = {'generation': 7, 'output': 'generation=7 \\u0003',
                 'error': {'code': 'EXECUTION_LEASE_INVALID', 'generation': 7}}
        self.assertEqual(model_view(value), {'output': value['output'], 'error': {'code': 'JOB_NOT_CURRENT'}})
