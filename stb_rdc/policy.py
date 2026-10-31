"""Read-only onboarding: Core rules, RDC workflow and actionable commands."""
from typing import Any
import shlex

from .client import BridgeClient, BridgeError
from .config import ADAPTER_VERSION
from .workflow import rdc_workflow

INPUT_SELECTION = (
    "命令超过 200 个 Unicode 字符，或含单引号、双引号、反斜杠、反引号、$ 中任一字符时，使用 --base64；"
    "其余短且简单的单行文本使用 --text。字符数按原文计算，不含 CLI 外层引用。"
)

COMMAND_GUIDANCE = INPUT_SELECTION + (
    "执行命令使用 stb-rdc run 会话名，--text 与 --base64 PAYLOAD 二选一，都是 run 的参数。"
    "命令不超过 200 个 Unicode 字符，且不含单引号、双引号、反斜杠、反引号或 $ 时，"
    "使用 stb-rdc run 会话名 --text '命令正文'；其他情况用 --base64 PAYLOAD，即 stb-rdc run 会话名 --base64 PAYLOAD。"
    "使用会话代码执行工具按 UTF-8 编码为无折行标准 Base64，并解码逐字节回验；禁止模型手算或改写编码结果。工具不可用时报告，不改用 RDC 编码原文。仅单行、不添加首尾换行，Base64 不是加密。"
)
EXCLUSIVE_GUIDANCE = (
    "目标操作只通过 STB，不用独立 RDC Shell、文件工具或 tmux send-keys 旁路。"
    "缺少能力时停止并报告；旁路须取得一次性、限定范围的人工同意，不能绕过人工中断、ACL 或人工决定。"
)


def command_guide(name: str) -> dict[str, Any]:
    session = shlex.quote(name)
    commands = {
        "list": {"purpose": "未知会话名时列举；已知名称无需调用", "command": "stb-rdc list"},
        "info": {"purpose": "查看绑定 pane 状态并恢复当前 job_id", "command": f"stb-rdc info {session}"},
        "context": {"purpose": "刷新终端，不重复规则；默认 40 行", "command": f"stb-rdc context {session}"},
        "job": {"purpose": "查询原任务状态和结果", "command": "stb-rdc job JOB_ID"},
        "wait": {"purpose": "继续观察原任务；--seconds 可设 1–600 秒，默认 60，可能提前返回；超时不停止命令",
                 "command": "stb-rdc wait JOB_ID --seconds 60"},
        "run": {"purpose": "执行新任务，默认观察 60 秒",
                "input_selection": INPUT_SELECTION,
                "direct": f"stb-rdc run {session} --text '命令正文'",
                "base64": f"stb-rdc run {session} --base64 PAYLOAD"},
        "interrupt": {"purpose": "发送 Agent Ctrl+C 并等待提示符；termination_confirmed=false 时继续观察，不发新命令或重复中断",
                      "command": "stb-rdc interrupt JOB_ID"},
    }
    return commands


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


def bootstrap(client: BridgeClient, name: str, lines: int = 40, detailed: bool = False) -> dict[str, Any]:
    bridge = client.call("bridge_info")
    instructions = bridge.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise BridgeError("Bridge 未返回有效的通用执行说明，无法完成发现；请检查运行服务。",
                          code="BOOTSTRAP_INSTRUCTIONS_MISSING", detail={"field": "instructions"})
    session = client.session(name)
    pane = session["pane"]
    state = client.call("terminal_state", {"pane": pane})
    context = compact_terminal(client.call("terminal_read", {"pane": pane, "lines": lines}))
    # Onboarding is a fresh observation, not a report of the previous lease's
    # interruption history. Job results retain their authoritative status.
    context.pop("execution", None)
    jobs = client.call("terminal_job_list").get("jobs", [])
    fields = ("job_id", "state", "execution_phase", "elapsed_ms", "attention_reason")
    active = [{key: job[key] for key in fields if key in job}
              for job in jobs if job.get("pane") == pane and job.get("execution_phase") == "EXECUTING"]
    result = {
        "session": {key: session[key] for key in ("name", "pane") if key in session},
        "terminal_state": state,
        "context": context,
        "instructions": instructions,
        "transport": {"input_selection": COMMAND_GUIDANCE, "exclusive_mode": EXCLUSIVE_GUIDANCE},
        "commands": command_guide(name),
        "workflow": rdc_workflow(name),
    }
    if active:
        result["current_jobs"] = active
    if detailed:
        result["diagnostics"] = {
            "adapter_version": ADAPTER_VERSION,
            "bridge_version": bridge.get("version"),
            "error_provenance": {
                "adapter": "本地适配请求无效",
                "local_transport": "Adapter 与 Bridge 的 socket 或响应故障",
                "stb": "Bridge 返回的权威错误，不误判为目标命令失败",
                "upstream": "适配层启动前的 RDC 或上游拒绝，Adapter 无法观测",
                "target": "仅在任务证据确认后判断目标命令失败",
            },
        }
    return result
