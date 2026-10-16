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
        "human_override_recovery": {
            "reacquire_without_new_authorization": False,
            "guidance": (
                "After a human Ctrl+C revokes the lease, stop the current execution "
                "chain. Explain that Ctrl+C canceled the pending command and revoked "
                "AI execution authority. If the shell was at a continuation prompt "
                "(for example > from unmatched quoting), confirm recovery to a normal "
                "prompt using read-only observation; do not resend the canceled command. "
                "Ask for explicit renewed authorization scoped to the specific next "
                "operation/session. Avoid vague requests to reply continue or approve. "
                "Do not silently treat an ambiguous continue as renewal; once the "
                "user clearly authorizes that scope, obtain a fresh lease."
            ),
            "example_request_zh": (
                "刚才 Ctrl+C 取消了未完成的命令，也撤销了 AI 的执行授权。"
                "终端恢复正常后，如果要继续，请明确授权我在指定会话执行下一步操作；"
                "不会自动重放刚才取消的命令。"
            ),
        },
        "revoked_generation_policy": "DENY",
        "authorization_granularity": "task_or_risk_boundary_not_each_command",
        "authorization_guidance": (
            "Use ChatGPT's normal contextual judgment to scope operations and ask "
            "for human confirmation at meaningful risk boundaries. Routine observations "
            "and low-risk steps within the approved task need no extra conversational "
            "approval. Destructive actions, privilege escalation, and material service "
            "or network changes merit explicit human confirmation. Always honor STB "
            "lease, pane ACL, long-run approvals and Human Override; these are separate "
            "local enforcement rules, not substitutes for user consent."
        ),
        "error_provenance": {
            "adapter": "invalid local session or adapter request",
            "local_transport": "Unix socket/response failure between adapter and STB",
            "stb": "authoritative STB error code including lease and ACL",
            "upstream": "OpenAI safety or RDC rejection happens before adapter starts; classify in ChatGPT, never claim STB/Windows/API failed",
            "target": "command/API failure only when STB job evidence establishes it",
        },
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
