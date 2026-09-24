"""Discovery response and interaction guidance exposed to ChatGPT."""

from typing import Any

from .client import BridgeClient
from .config import ADAPTER_VERSION


def interaction_policy() -> dict[str, Any]:
    return {
        "human_primary": True,
        "bootstrap_first": True,
        "bootstrap_is_discovery_only": True,
        "execution_path_required": "RDC -> stb-rdc -> STB -> tmux",
        "direct_rdc_shell_execution_forbidden": True,
        "direct_tmux_send_keys_forbidden": True,
        "execution_requires_lease": True,
        "human_interrupt_action": "STOP_CURRENT_TURN",
        "revoked_generation_policy": "DENY",
        "wait_timeout_is_job_failure": False,
        "wait_timeout_guidance": (
            "A wait timeout only ends this observation window. Re-check the job; "
            "do not interrupt a still-running job solely because wait timed out."
        ),
    }


def compact_terminal(raw: dict[str, Any]) -> dict[str, Any]:
    lines = [line.rstrip() for line in raw.get("content", "").splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return {
        "content": "\n".join(lines),
        "execution": raw.get("execution", {}),
        "truncated": raw.get("truncated", False),
    }


def bootstrap(client: BridgeClient, name: str, lines: int = 40) -> dict[str, Any]:
    bridge = client.call("bridge_info")
    managed_session = client.session(name)
    pane = managed_session["pane"]
    terminal_state = client.call("terminal_state", {"pane": pane})
    context = compact_terminal(
        client.call("terminal_read", {"pane": pane, "lines": lines})
    )
    return {
        "adapter": {"name": "stb-rdc", "version": ADAPTER_VERSION},
        "bridge": {
            "name": bridge.get("name"),
            "version": bridge.get("version"),
            "api_version": bridge.get("api_version"),
        },
        "session": managed_session,
        "terminal_state": terminal_state,
        "context": context,
        "interaction_policy": interaction_policy(),
        "bootstrap_result": {
            "ready": True,
            "task_executed": False,
            "discovery_only": True,
            "next_step": (
                "For terminal work, continue only through stb-rdc commands. Do not "
                "run the user's terminal task directly with Remote Desktop Commander "
                "shell/process tools and do not call tmux send-keys directly."
            ),
        },
        "workflow": {
            "cold_start": "bootstrap discovery only -> plan",
            "execute": "lease -> send -> job/wait",
            "on_human_interrupt": (
                "stop current turn; do not reacquire or continue without new human "
                "authorization"
            ),
        },
    }
