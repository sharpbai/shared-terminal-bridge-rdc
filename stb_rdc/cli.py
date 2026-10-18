"""Command-line interface and direct mappings to STB API methods."""

import argparse
import json
import sys
from typing import Any, Sequence

from .client import BridgeClient, BridgeError
from .config import ADAPTER_VERSION
from .policy import bootstrap, compact_terminal, interaction_policy
from .model_view import model_view


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Thin ChatGPT/RDC adapter for Shared Terminal Bridge.\n"
                     "Agent 首次使用：stb-rdc bootstrap SESSION\n"
                     "由 bootstrap 获取上下文、规则及调用模板；已有当前契约时无需重复发现。"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("serve-stdio", help="Read one JSONL stdin request, return one response and exit")

    bootstrap_parser = commands.add_parser("bootstrap", help="Discover once; return context, rules and run template")
    bootstrap_parser.add_argument("session")
    bootstrap_parser.add_argument("--lines", type=int, choices=range(1, 101), metavar="1-100", default=20)
    bootstrap_parser.add_argument("--detailed", action="store_true", help="Include extended policy explanations (normally unnecessary)")

    context_parser = commands.add_parser("context")
    context_parser.add_argument("session")
    context_parser.add_argument("--lines", type=int, default=40)

    wait_parser = commands.add_parser("wait")
    wait_parser.add_argument("job_id")
    wait_parser.add_argument("--seconds", type=int, default=60)

    job_parser = commands.add_parser("job")
    job_parser.add_argument("job_id")

    interrupt_parser = commands.add_parser("interrupt")
    interrupt_parser.add_argument("job_id")
    return parser


def dispatch(args: argparse.Namespace, client: BridgeClient) -> dict[str, Any]:
    if args.command == "status":
        return {
            "adapter_version": ADAPTER_VERSION,
            "bridge": {k: v for k, v in client.call("bridge_info").items() if k != "methods"},
            "sessions": client.call("terminal_session_list").get("sessions", []),
            "interaction_policy": interaction_policy(),
        }
    if args.command == "bootstrap":
        return bootstrap(client, args.session, args.lines, args.detailed)
    if args.command == "context":
        managed_session = client.session(args.session)
        pane = managed_session["pane"]
        return {
            "session": managed_session,
            "state": client.call("terminal_state", {"pane": pane}),
            "terminal": compact_terminal(
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

    return client.call("terminal_interrupt_job", {"job_id": args.job_id})


def run(
    argv: Sequence[str] | None = None,
    client: BridgeClient | None = None,
) -> dict[str, Any] | None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        build_parser().print_help()
        return None
    args = build_parser().parse_args(arguments)
    if args.command == "serve-stdio":
        from .stdio import serve
        serve(sys.stdin, sys.stdout, client or BridgeClient())
        return None
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
