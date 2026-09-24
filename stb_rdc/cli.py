"""Command-line interface and direct mappings to STB API methods."""

import argparse
import json
import sys
from typing import Any, Sequence

from .client import BridgeClient, BridgeError
from .config import ADAPTER_VERSION
from .policy import bootstrap, compact_terminal, interaction_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Thin ChatGPT/RDC adapter for Shared Terminal Bridge."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")

    bootstrap_parser = commands.add_parser("bootstrap")
    bootstrap_parser.add_argument("session")
    bootstrap_parser.add_argument("--lines", type=int, default=40)

    context_parser = commands.add_parser("context")
    context_parser.add_argument("session")
    context_parser.add_argument("--lines", type=int, default=40)

    lease_parser = commands.add_parser("lease")
    lease_parser.add_argument("session")

    send_parser = commands.add_parser("send")
    send_parser.add_argument("session")
    send_parser.add_argument("generation", type=int)
    send_parser.add_argument("text")

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
            "bridge": client.call("bridge_info"),
            "sessions": client.call("terminal_session_list").get("sessions", []),
            "interaction_policy": interaction_policy(),
        }
    if args.command == "bootstrap":
        return bootstrap(client, args.session, args.lines)
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
    if args.command == "lease":
        pane = client.session(args.session)["pane"]
        return client.call("acquire_execution", {"pane": pane})
    if args.command == "send":
        pane = client.session(args.session)["pane"]
        return client.call(
            "terminal_submit",
            {"pane": pane, "generation": args.generation, "text": args.text},
        )
    if args.command == "wait":
        return client.call(
            "terminal_wait_job",
            {"job_id": args.job_id, "wait_ms": args.seconds * 1000},
        )
    if args.command == "job":
        return client.call("terminal_job_status", {"job_id": args.job_id})

    job = client.call("terminal_job_status", {"job_id": args.job_id})
    return client.call(
        "terminal_interrupt",
        {"pane": job["pane"], "generation": job["generation"]},
    )


def run(
    argv: Sequence[str] | None = None,
    client: BridgeClient | None = None,
) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    return dispatch(args, client or BridgeClient())


def main(argv: Sequence[str] | None = None) -> None:
    try:
        result = run(argv)
    except (BridgeError, RuntimeError) as error:
        print(
            json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        raise SystemExit(1) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
