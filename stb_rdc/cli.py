"""Command-line interface and direct mappings to STB API methods."""

import argparse
import json
import sys
from typing import Any, Sequence

from .client import BridgeClient, BridgeError
from .policy import bootstrap, compact_terminal, INPUT_SELECTION
from .model_view import model_view
from .command_input import decode_chunks, validate_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("通过 RDC 使用共享终端的轻量适配层。\n"
                     "Agent 首次使用：stb-rdc bootstrap SESSION\n"
                     "由 bootstrap 获取上下文、规则及调用模板；已有当前契约时无需重复发现。"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="列出托管会话")
    info_parser = commands.add_parser("info", help="查看指定会话状态和当前任务")
    info_parser.add_argument("session")
    run_parser = commands.add_parser("run", allow_abbrev=False, help="执行任务并观察结果",
        description=INPUT_SELECTION + " 默认观察 60 秒，超时不停止任务；工具编码步骤见 bootstrap。")
    run_parser.add_argument("session")
    source = run_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="单行命令；需要启动 Shell 正确引用")
    source.add_argument("--base64-chunks", nargs="+", metavar="CHUNK_OR_DIGEST",
                        help="空格分隔的 Base64 短段，最后一个参数为 16 位摘要")
    run_parser.add_argument("--wait-ms", type=int, default=60000)
    run_parser.add_argument("--expected-duration-ms", type=int, default=10000)
    run_parser.add_argument("--resource-class", choices=("normal", "high_io", "full_scan"), default="normal")

    bootstrap_parser = commands.add_parser("bootstrap", help="首次接入：返回上下文、规则和调用模板")
    bootstrap_parser.add_argument("session")
    bootstrap_parser.add_argument("--lines", type=int, choices=range(1, 101), metavar="1-100", default=40)
    bootstrap_parser.add_argument("--detailed", action="store_true", help="附带版本和错误来源诊断；不改变执行规则")

    context_parser = commands.add_parser("context", help="刷新终端上下文，默认 40 行")
    context_parser.add_argument("session")
    context_parser.add_argument("--lines", type=int, choices=range(1, 101), metavar="1-100", default=40)

    wait_parser = commands.add_parser("wait", help="继续观察原任务，默认 60 秒，不停止任务")
    wait_parser.add_argument("job_id")
    wait_parser.add_argument("--seconds", type=int, default=60, metavar="秒",
                             help="本次最多观察秒数（1–600，默认 60）；可能提前返回，超时不停止任务")

    job_parser = commands.add_parser("job", help="查询任务状态和结果")
    job_parser.add_argument("job_id")

    interrupt_parser = commands.add_parser("interrupt", help="中断任务并等待提示符返回")
    interrupt_parser.add_argument("job_id")
    interrupt_parser.add_argument("--seconds", type=int, default=60,
                                  help="等待提示符返回，1–600 秒，默认 60 秒")
    return parser


def dispatch(args: argparse.Namespace, client: BridgeClient) -> dict[str, Any]:
    if args.command == "run":
        if args.base64_chunks is not None:
            text = decode_chunks(args.base64_chunks)
        else:
            text = validate_command(args.text)
        pane = client.session(args.session)["pane"]
        params = dict(pane=pane, text=text, wait_ms=args.wait_ms,
                      expected_duration_ms=args.expected_duration_ms, resource_class=args.resource_class)
        return client.call("terminal_run", params)
    if args.command == "list":
        return client.call("terminal_session_list")
    if args.command == "info":
        session = client.session(args.session)
        state = client.call("terminal_state", {"pane": session["pane"]})
        jobs = client.call("terminal_job_list").get("jobs", [])
        return {"session": session, "terminal_state": state,
                "current_jobs": [{key: job[key] for key in ("job_id", "pane", "state", "execution_phase",
                                                          "elapsed_ms", "resource_class", "attention_reason")
                                  if key in job} for job in jobs if job.get("pane") == session["pane"]
                                 and job.get("execution_phase") == "EXECUTING"]}
    if args.command == "bootstrap":
        return bootstrap(client, args.session, args.lines, args.detailed)
    if args.command == "context":
        managed_session = client.session(args.session)
        pane = managed_session["pane"]
        return {
            "session": managed_session,
            "terminal_state": client.call("terminal_state", {"pane": pane}),
            "context": compact_terminal(
                client.call("terminal_read", {"pane": pane, "lines": args.lines})
            ),
        }
    if args.command == "wait":
        return client.call(
            "terminal_wait_job",
            {"job_id": args.job_id, "wait_ms": args.seconds * 1000},
        )
    if args.command == "job":
        return client.call("terminal_job_status", {"job_id": args.job_id})

    return client.call("terminal_interrupt_job", {"job_id": args.job_id,
                                                  "wait_ms": args.seconds * 1000})


def run(
    argv: Sequence[str] | None = None,
    client: BridgeClient | None = None,
) -> dict[str, Any] | None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        build_parser().print_help()
        return None
    args = build_parser().parse_args(arguments)
    return model_view(dispatch(args, client or BridgeClient()))


def main(argv: Sequence[str] | None = None) -> None:
    try:
        result = run(argv)
    except BridgeError as error:
        print(json.dumps(model_view(error.as_dict()), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from error
    except RuntimeError as error:
        print(json.dumps({"ok": False, "error": {
            "layer": "adapter", "code": "ADAPTER_ERROR",
            "message": str(error), "detail": None
        }}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from error
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
