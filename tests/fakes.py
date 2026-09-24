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
        responses = {
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
        }
        return responses[method]

    def session(self, name: str) -> dict[str, Any]:
        self.call("terminal_session_list")
        for managed_session in self.sessions:
            if managed_session["name"] == name:
                return managed_session
        raise BridgeError(f"managed session not found: {name}")
