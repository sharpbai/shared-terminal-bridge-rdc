"""In-memory Bridge test double; no daemon, RDC, or tmux required."""

from typing import Any

from stb_rdc.client import BridgeError


class FakeBridgeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.sessions = [{"name": "verify33", "pane": "%5"}]

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_params = params or {}
        self.calls.append((method, request_params))
        if method == "terminal_session_resolve":
            for session in self.sessions:
                if session["name"] == request_params["name"]:
                    return session
            raise BridgeError("会话不存在", layer="stb", code="SESSION_NOT_MANAGED")
        responses = {
            "terminal_job_list": {"jobs": []},
            "bridge_info": {"name": "STB", "version": "0.15.0", "api_version": 1},
            "terminal_session_list": {"sessions": self.sessions},
            "terminal_state": {"foreground": "zsh"},
            "terminal_read": {
                "content": "\nready\n\n",
                "execution": {"state": "IDLE"},
                "truncated": False,
            },
            "acquire_execution": {"generation": 8, "state": "ACTIVE"},
            "terminal_submit": {"job_id": "job-1"},
            "terminal_wait_job": {"job_id": "job-1", "state": "COMPLETED"},
            "terminal_job_status": {
                "job_id": "job-1",
                "pane": "%5",
                "generation": 8,
                "state": "RUNNING",
            },
            "terminal_interrupt": {"job_id": "job-1", "state": "INTERRUPTING"},
            "terminal_interrupt_job": {"job_id": "job-1", "state": "INTERRUPTING"},
        }
        return responses[method]

    def session(self, name: str) -> dict[str, Any]:
        return self.call("terminal_session_resolve", {"name": name})


class RunClient(FakeBridgeClient):
    def call(self, method, params=None):
        if method == "bridge_info":
            self.calls.append((method, params or {}))
            return {"run_auto_request_id": True, "input_auto_request_id": True,
                    "instructions": "Core 通用规则：执行期间人工 Ctrl+C 停止旧链，高风险通过对话确认。",
                    "terminal_run": "receipt-scoped-run-v1",
                    "model_tasks": "job-authority-v2", "command_request_dedup": "durable-submit-v1"}
        if method in {"terminal_run", "terminal_input_job"}:
            self.calls.append((method, params))
            return {"job_id": "job-one", "state": "COMPLETED", "generation": 8}
        return super().call(method, params)
