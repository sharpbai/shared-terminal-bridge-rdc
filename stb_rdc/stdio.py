"""One stdin request, one JSON response, then exit; never invoke a shell."""

import json

from .client import BridgeError
from .policy import bootstrap
from .model_view import model_view

MAX_FRAME = 1024 * 1024
OPERATIONS = {
    "run": "terminal_run",
    "wait": "terminal_wait_job", "job": "terminal_job_status",
    "interrupt": "terminal_interrupt_job", "input": "terminal_input_job",
    "context": "terminal_read",
    "state": "terminal_state", "sessions": "terminal_session_list",
    "info": "bridge_info", "approve": "terminal_approve_request",
}


def dispatch_frame(frame, client):
    if not isinstance(frame, dict) or set(frame) - {"id", "op", "session", "params"}:
        raise ValueError("Expected {id, op, session?, params?}")
    request_id = frame.get("id")
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
        raise ValueError("id must be a nonempty string of at most 128 characters")
    params = frame.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    params = dict(params)
    if any(key in params for key in ("generation", "lease", "authorization", "_authorization")):
        raise ValueError("Authority metadata is internal; use run or a job ID")
    if frame.get("op") == "bootstrap":
        session = frame.get("session")
        if not isinstance(session, str) or not session.strip():
            raise ValueError("bootstrap requires a named session")
        if set(params) - {"lines", "detailed"}:
            raise ValueError("bootstrap only accepts params.lines and params.detailed")
        detailed = params.get("detailed", False)
        if type(detailed) is not bool:
            raise ValueError("bootstrap detailed must be boolean")
        lines = params.get("lines", 20)
        if type(lines) is not int or not 1 <= lines <= 100:
            raise ValueError("bootstrap lines must be an integer from 1 to 100")
        return model_view(bootstrap(client, session, lines, detailed))
    if frame.get("op") == "interrupt":
        if "session" in frame or set(params) != {"job_id"}:
            raise ValueError("Job interrupt accepts only params.job_id")
        return model_view(client.call("terminal_interrupt_job", params))
    method = OPERATIONS.get(frame.get("op"))
    if method is None:
        raise ValueError("Unsupported op")
    if "session" in frame:
        if "pane" in params:
            raise ValueError("Use session or pane, not both")
        params["pane"] = client.session(frame["session"])["pane"]
    if method in {"terminal_run", "terminal_input_job"}:
        if "request_id" in params:
            raise ValueError("Submit request_id is derived from envelope id")
        info = client.call("bridge_info")
        if not info.get("command_request_dedup"):
            raise ValueError("Core requires command_request_dedup support; no unsafe fallback")
        if info.get("model_tasks") != "job-authority-v2":
            raise ValueError("Core model task interface unavailable; restart/upgrade Bridge, no legacy fallback")
        if method == "terminal_run" and info.get("terminal_run") != "receipt-scoped-run-v1":
            raise ValueError("Core requires terminal_run support; restart Bridge, no fallback to split lease/submit")
        params["request_id"] = request_id
    result = client.call(method, params)
    if frame.get("op") == "info":
        result = {key: value for key, value in result.items() if key != "methods"}
    return model_view(result)


def serve(reader, writer, client):
    line = reader.readline(MAX_FRAME + 1)
    if not line:
        return
    request_id = None
    try:
        if len(line) > MAX_FRAME:
            # No drain: the process exits, even if the sender keeps stdin open.
            raise ValueError("JSONL frame too large")
        if not line.endswith("\n"):
            raise ValueError("JSONL request must end with a newline")
        frame = json.loads(line)
        if isinstance(frame, dict):
            request_id = frame.get("id")
        result = dispatch_frame(frame, client)
        response = {"id": request_id, "ok": True, "result": result}
    except BridgeError as error:
        response = dict(model_view(error.as_dict()), id=request_id)
    except (ValueError, TypeError, KeyError) as error:
        response = {"id": request_id, "ok": False, "error": {
            "layer": "adapter", "code": "INVALID_STDIO_REQUEST", "message": str(error)}}
    writer.write(json.dumps(response, ensure_ascii=False) + "\n")
    writer.flush()
