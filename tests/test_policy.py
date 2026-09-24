import unittest

from stb_rdc.policy import bootstrap, compact_terminal, interaction_policy
from tests.fakes import FakeBridgeClient


class PolicyTests(unittest.TestCase):
    def test_compact_terminal_only_trims_blank_edges(self) -> None:
        result = compact_terminal(
            {"content": "\n first  \nsecond\n\n", "truncated": True}
        )
        self.assertEqual(result["content"], " first\nsecond")
        self.assertTrue(result["truncated"])

    def test_bootstrap_is_discovery_only(self) -> None:
        client = FakeBridgeClient()
        result = bootstrap(client, "verify33", 12)

        self.assertTrue(result["bootstrap_result"]["discovery_only"])
        self.assertFalse(result["bootstrap_result"]["task_executed"])
        self.assertEqual(result["context"]["content"], "ready")
        methods = [method for method, _ in client.calls]
        self.assertEqual(
            methods,
            ["bridge_info", "terminal_session_list", "terminal_state", "terminal_read"],
        )
        self.assertNotIn("acquire_execution", methods)
        self.assertNotIn("terminal_submit", methods)

    def test_policy_preserves_exclusive_execution_path(self) -> None:
        result = interaction_policy()
        self.assertEqual(
            result["execution_path_required"], "RDC -> stb-rdc -> STB -> tmux"
        )
        self.assertTrue(result["direct_rdc_shell_execution_forbidden"])
        self.assertFalse(result["wait_timeout_is_job_failure"])
        self.assertEqual(result["human_interrupt_action"], "STOP_CURRENT_TURN")


if __name__ == "__main__":
    unittest.main()
