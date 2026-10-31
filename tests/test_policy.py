"""Bootstrap is complete, bounded, read-only and transport-specific."""
import unittest
from stb_rdc.policy import bootstrap, compact_terminal, rdc_workflow, COMMAND_GUIDANCE
from tests.fakes import FakeBridgeClient, RunClient
from stb_rdc.client import BridgeError


class PolicyTests(unittest.TestCase):
    def test_tool_calls_use_documented_rdc_arguments(self):
        import shlex
        from stb_rdc.cli import build_parser
        workflow = rdc_workflow("verify33")
        calls = []

        def visit(value):
            if isinstance(value, dict):
                if "tool" in value:
                    calls.append(value)
                for child in value.values():
                    visit(child)

        visit(workflow)
        self.assertGreaterEqual(len(calls), 8)
        self.assertIn("不是命令", workflow["usage"])
        self.assertIn("deviceId", workflow["device"])
        for call in calls:
            args = call["arguments"]
            if call["tool"] == "start_process":
                self.assertEqual(set(args), {"command", "timeout_ms"})
                self.assertEqual(args["timeout_ms"], 1)
                build_parser().parse_args(shlex.split(args["command"])[1:])
            else:
                self.assertEqual(call["tool"], "read_process_output")
                self.assertEqual(set(args), {"pid", "offset", "timeout_ms"})
                self.assertIs(type(args["pid"]), int)
                self.assertEqual(args["offset"], 0)
                self.assertLessEqual(args["timeout_ms"], 3000)

    def test_bootstrap_omits_previous_interrupt_metadata_only(self):
        from stb_rdc.cli import run

        class PreviousInterrupt(RunClient):
            def call(self, method, params=None):
                result = super().call(method, params)
                if method == "terminal_read":
                    result["execution"] = {
                        "human_override": True,
                        "interrupt_source": {"source": "human"},
                        "lease": {"state": "REVOKED"},
                    }
                if method == "terminal_job_status":
                    result.update(state="INTERRUPTED_BY_HUMAN",
                                  recommended_action="STOP_CURRENT_EXECUTION_CHAIN")
                return result

        for detailed in (False, True):
            result = bootstrap(PreviousInterrupt(), "verify33", detailed=detailed)
            self.assertNotIn("execution", result["context"])
            self.assertNotIn("human_override", result["context"])
            self.assertEqual(result["context"]["content"], "ready")
        context = run(["context", "verify33"], PreviousInterrupt())
        self.assertTrue(context["context"]["execution"]["human_override"])
        job = run(["job", "job-1"], PreviousInterrupt())
        self.assertEqual(job["state"], "INTERRUPTED_BY_HUMAN")
        self.assertEqual(job["recommended_action"], "STOP_CURRENT_EXECUTION_CHAIN")

    def test_workflow_guides_complete_task_path(self):
        import base64
        import shlex
        from stb_rdc.cli import run
        workflow = rdc_workflow("verify33")
        self.assertNotIn("existing_job", workflow["observe"])
        self.assertIn("实际遇到任务占用", workflow["handle_result"]["error"])
        self.assertIn("代码执行工具", workflow["run_base64"]["encode"])
        text = "printf '%s' '中文'"
        for mode in ("run_text", "run_base64"):
            self.assertEqual(workflow[mode]["call"]["tool"], "start_process")
            start = workflow[mode]["call"]["arguments"]
            self.assertEqual(start["timeout_ms"], 1)
            self.assertNotIn("interact_with_process", workflow[mode])
            argv = shlex.split(start["command"].replace("PAYLOAD", base64.b64encode(text.encode()).decode()))[1:]
            client = RunClient()
            run(argv, client)
            self.assertEqual([m for m, _ in client.calls], ["terminal_session_resolve", "terminal_run"])
            if mode == "run_base64":
                self.assertEqual(client.calls[-1][1]["text"], text)

    def test_workflow_quotes_session_name(self):
        import shlex
        workflow = rdc_workflow("ops space'quote")
        for mode in ("run_text", "run_base64"):
            self.assertEqual(shlex.split(workflow[mode]["call"]["arguments"]["command"])[2],
                             "ops space'quote")

    def test_input_selection_is_explicit_without_mcp_mixing(self):
        for term in ("200 个 Unicode 字符", "单引号", "双引号", "反斜杠",
                     "反引号", "$", "其他情况用 --base64", "都是 run 的参数"):
            self.assertIn(term, COMMAND_GUIDANCE)
        self.assertNotIn("MCP", COMMAND_GUIDANCE)

    def test_read_only_bootstrap_has_one_source_of_core_rules(self):
        client = RunClient()
        result = bootstrap(client, "verify33")
        self.assertNotIn("bootstrap_result", result)
        self.assertNotIn("protocol_revision", result)
        self.assertNotIn("adapter", result)
        self.assertNotIn("bridge", result)
        self.assertEqual([m for m, _ in client.calls], [
            "bridge_info", "terminal_session_resolve", "terminal_state",
            "terminal_read", "terminal_job_list"])
        for key in ("interaction_policy", "request_templates", "current_jobs"):
            self.assertNotIn(key, result)
        self.assertEqual(set(result["transport"]), {"input_selection", "exclusive_mode"})
        self.assertIn("Ctrl+C", result["instructions"])
        self.assertNotIn("legacy", str(result))
        self.assertIn("context", result["commands"])
        self.assertIn("info", result["commands"])
        self.assertEqual(result["commands"]["wait"]["command"], "stb-rdc wait JOB_ID --seconds 60")
        self.assertIn("1–600", result["commands"]["wait"]["purpose"])
        self.assertIn("--seconds 60", result["workflow"]["follow_up"]["wait"]["arguments"]["command"])

    def test_missing_instructions_prevents_ready_and_write_templates(self):
        class Missing(RunClient):
            def call(self, method, params=None):
                result = super().call(method, params)
                if method == "bridge_info":
                    result.pop("instructions", None)
                return result
        client = Missing()
        with self.assertRaises(BridgeError) as captured:
            bootstrap(client, "verify33")
        self.assertEqual(captured.exception.code, "BOOTSTRAP_INSTRUCTIONS_MISSING")
        self.assertEqual(captured.exception.detail, {"field": "instructions"})
        self.assertEqual([m for m, _ in client.calls], ["bridge_info"])

    def test_bootstrap_does_not_require_compatibility_flags(self):
        class NoFlags(RunClient):
            def call(self, method, params=None):
                result = super().call(method, params)
                if method == "bridge_info":
                    return {"instructions": result["instructions"]}
                return result
        result = bootstrap(NoFlags(), "verify33")
        self.assertIn("run", result["commands"])
        self.assertNotIn("input", result["commands"])
        self.assertIn("interrupt", result["commands"])

    def test_active_jobs_are_scoped_summarized_and_optional(self):
        class Jobs(RunClient):
            def call(self, method, params=None):
                if method == "terminal_job_list":
                    self.calls.append((method, params or {}))
                    return {"jobs": [
                        {"pane": "%5", "job_id": "active", "execution_phase": "EXECUTING", "output": "large"},
                        {"pane": "%6", "job_id": "other", "execution_phase": "EXECUTING"},
                        {"pane": "%5", "job_id": "done", "execution_phase": "FINISHED"}]}
                return super().call(method, params)
        result = bootstrap(Jobs(), "verify33")
        self.assertEqual(result["current_jobs"], [{"job_id": "active", "execution_phase": "EXECUTING"}])

    def test_detailed_adds_only_diagnostics_not_another_policy(self):
        compact = bootstrap(RunClient(), "verify33")
        detailed = bootstrap(RunClient(), "verify33", detailed=True)
        diagnostics = detailed.pop("diagnostics")
        self.assertEqual(compact, detailed)
        self.assertEqual(set(diagnostics), {"adapter_version", "bridge_version", "error_provenance"})
        self.assertIn("适配层启动前", diagnostics["error_provenance"]["upstream"])

    def test_compact_terminal_preserves_existing_bounding(self):
        result = compact_terminal({"content": "\n first  \nsecond\n\n", "truncated": True})
        self.assertEqual(result["content"], " first\nsecond")
        self.assertTrue(result["truncated"])
