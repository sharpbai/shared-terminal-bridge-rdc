"""Discovery response and interaction guidance exposed to ChatGPT."""

from typing import Any

from .client import BridgeClient
from .config import ADAPTER_VERSION

PROTOCOL_REVISION = "model-tasks-v2"

PAGER_GUIDANCE = (
    "Disable pagers for command output: use git --no-pager ... or GIT_PAGER=cat, "
    "and systemctl --no-pager ... to avoid getting stuck at (END). "
    "Bound output where practical; do not change global target configuration."
)


def request_templates(name, supports_run=False):
    """Small actionable contract; placeholders must come from actual responses."""
    templates = {
        "wait": {"id": "NEW_UNIQUE_ID", "op": "wait",
                 "params": {"job_id": "FROM_RUN", "wait_ms": 600000}},
        "job": {"id": "NEW_UNIQUE_ID", "op": "job",
                "params": {"job_id": "FROM_RUN"}},
        "interrupt": {"id": "NEW_UNIQUE_ID", "op": "interrupt",
                      "params": {"job_id": "FROM_RUN"}},
        "input": {"id": "NEW_UNIQUE_INPUT_ID", "op": "input",
                  "params": {"job_id": "FROM_RUN", "text": "REPLY_TO_RUNNING_PROGRAM"}},
        "approve": {"id": "NEW_UNIQUE_ID", "op": "approve",
                    "params": {"request_id": "FROM_APPROVAL_REQUEST"}},
    }
    if supports_run:
        templates = {"run": {"id": "NEW_UNIQUE_COMMAND_ID", "op": "run", "session": name,
            "params": {"text": "YOUR_SINGLE_LINE_COMMAND", "expected_duration_ms": 10000,
                       "resource_class": "normal", "wait_ms": 600000}}, **templates}
    return templates


def interaction_policy() -> dict[str, Any]:
    return {
        "human_primary": True,
        "bootstrap_first": True,
        "command_output": PAGER_GUIDANCE,
        "bootstrap_is_discovery_only": True,
        "execution_path_required": "RDC -> stb-rdc -> STB -> tmux",
        "command_transport": {
            "preferred": "serve-stdio-jsonl-once-v1",
            "startup": "stb-rdc serve-stdio",
            "startup_timeout_ms": 1,
            "startup_request": {"command": "stb-rdc serve-stdio", "timeout_ms": 1},
            "startup_timeout_rule": "REQUIRED: timeout_ms=1 millisecond, not 1000; do not use defaults",
            "lifecycle": "one request, one response, exit; never reuse PID",
            "input": "RDC interact_with_process input: JSONL, not shell text",
            "submit_id": "Unique logical request ID; retain unchanged across retries",
            "multiline_execution": False,
            "guidance": "Never embed target commands in RDC start_process arguments. "
                        "Start the fixed receiver with timeout_ms=1 to get its PID promptly, "
                        "then immediately send exactly one newline-terminated JSON request "
                        "using interact_with_process. Do not sleep or wait for readiness output. "
                        "Startup timeout_ms MUST be 1 (one millisecond), never 1000 or 3000. "
                        "Only the following input/output collection may use timeout_ms=3000. "
                        "The receiver flushes its response and exits; use a new process per request. "
                        "Use interrupt op for Ctrl+C, not escaped control bytes. accepted only "
                        "means requested; interrupt waits for prompt return by default (600000ms; "
                        "optional wait_ms). Check termination_confirmed. If false, observe the job "
                        "and do not submit another command or claim it stopped. "
                        "A running wait does not prevent a separate request for control/status. "
                        "A timeout does not authorize a new submit ID.",
        },
        "direct_rdc_shell_execution_forbidden": True,
        "direct_tmux_send_keys_forbidden": True,
        "authority_handled_by_core": True,
        "human_interrupt_action": "STOP_CURRENT_EXECUTION_CHAIN",
        "human_override_recovery": {
            "reacquire_without_new_authorization": True,
            "guidance": (
                "After a human Ctrl+C interrupts the job, stop the current execution "
                "chain, not the whole model turn. New run calls received by Bridge after "
                "the interrupt are automatically authorized internally; "
                "no routine conversational reauthorization is needed. "
                "At a continuation prompt, observe recovery before a new command. "
                "Do not replay the canceled call's queued steps. High-risk operations "
                "still require explicit human approval; do not bypass STB decisions."
            ),
            "example_request_zh": (
                "刚才 Ctrl+C 已取消当前执行链；不会自动重放该调用的后续步骤。"
                "终端恢复后，新调用可自动续授权；高风险操作仍单独请你批准。"
            ),
        },
        "interrupted_job_policy": "NEVER_RESUME_OLD_CHAIN_ALLOW_NEW_RUN",
        "authorization_granularity": "task_or_risk_boundary_not_each_command",
        "authorization_guidance": (
            "Use ChatGPT's normal contextual judgment to scope operations and ask "
            "for human confirmation at meaningful risk boundaries. Routine observations "
            "and low-risk steps within the approved task need no extra conversational "
            "approval. Destructive actions, privilege escalation, and material service "
            "or network changes merit explicit human confirmation. Always honor STB "
            "pane ACL, risk approvals and Human Override; these are separate "
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


def compact_policy():
    """Minimum complete runtime rules; detailed explanations remain opt-in."""
    return {
        "command_output": PAGER_GUIDANCE,
        "startup_request": {"command": "stb-rdc serve-stdio", "timeout_ms": 1},
        "transport": "Immediately send one newline-terminated JSON via interact_with_process; collect with timeout_ms=3000. One response then exit; never reuse PID. Never put target commands in startup arguments. Single-line commands only; use interrupt for Ctrl+C.",
        "authority": "Core handles authorization. Human Ctrl+C during execution stops the old chain: never replay canceled steps. New calls may renew internally. High-risk/destructive/privileged/service/network changes require explicit approval; honor Core ACL and risk decisions.",
        "retry_wait": "Retry identical logical request ID and command parameters, never submit a new ID on transport timeout. wait timeout or canceled observation does not stop the job; use job/wait to observe, input/interrupt only with its job ID. Interrupt waits for prompt by default (600000ms, optional wait_ms); if termination_confirmed=false, observe the job, do not submit another command. Read the existing PID after RDC collection timeout; never repeat the interrupt input.",
        "exclusive_mode": "Target operations only through STB. No independent RDC shell/filesystem or tmux send-keys bypass. Missing capability: fail closed; bypass requires explicit one-shot scoped human approval and cannot evade Human Override, ACL or risk approval.",
    }


def bootstrap(client: BridgeClient, name: str, lines: int = 20, detailed: bool = False) -> dict[str, Any]:
    bridge = client.call("bridge_info")
    supports_model = (bridge.get("terminal_run") == "receipt-scoped-run-v1"
                      and bridge.get("model_tasks") == "job-authority-v2")
    managed_session = client.session(name)
    pane = managed_session["pane"]
    terminal_state = client.call("terminal_state", {"pane": pane})
    context = compact_terminal(
        client.call("terminal_read", {"pane": pane, "lines": lines})
    )
    return {
        "protocol_revision": PROTOCOL_REVISION,
        "adapter": {"name": "stb-rdc", "version": ADAPTER_VERSION},
        "bridge": {
            "name": bridge.get("name"),
            "version": bridge.get("version"),
            "api_version": bridge.get("api_version"),
            "execution_policy": bridge.get("execution_policy", "legacy-explicit-renewal"),
            "command_request_dedup": bridge.get("command_request_dedup"),
            "terminal_run": bridge.get("terminal_run"),
            "model_tasks": bridge.get("model_tasks"),
        },
        "session": managed_session,
            "terminal_state": terminal_state,
        "context": context,
        "interaction_policy": interaction_policy() if detailed else compact_policy(),
        "request_templates": request_templates(name, supports_model),
        "bootstrap_result": {
            "ready": supports_model,
            "task_executed": False,
            "discovery_only": True,
            "discovery_complete": supports_model,
            "repeat_bootstrap": "Only after environment changes or compatibility errors; never repeat to reduce lines. Use context for fresh terminal observations.",
            "preferred_operation": ("run" if supports_model
                                    else "restart_required"),
            "next_step": (
                "Discovery complete when ready=true: use run; no routine README or second bootstrap. "
                "Reuse this revision's contract; use context for fresh observations. "
                "Replace template placeholders with actual IDs/commands. ready=false: upgrade/restart Core, no execution fallback."
            ),
        },
        "workflow": {
            "cold_start": "bootstrap discovery only -> plan",
            "execute": ("run; retry same ID only to observe original job"
                        if supports_model
                        else "restart Core; no legacy execution fallback"),
            "on_human_interrupt": (
                "stop canceled execution chain; a new local call may renew automatically; "
                "retain high-risk approval; job IDs identify old work"
            ),
        },
    }
