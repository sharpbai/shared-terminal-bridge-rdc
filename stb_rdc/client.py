"""Small newline-delimited JSON client for the local STB Unix socket."""
import json
import socket
from pathlib import Path
from typing import Any

from .config import DEFAULT_SOCKET
from .errors import BridgeError, bridge_failure


class BridgeClient:
    """Call the local STB API without owning execution policy or state."""

    def __init__(self, socket_path: Path = DEFAULT_SOCKET) -> None:
        self.socket_path = socket_path

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"method": method, "params": params or {}}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.connect(str(self.socket_path))
                with connection.makefile("w", encoding="utf-8") as writer:
                    writer.write(json.dumps(request) + "\n")
                    writer.flush()
                with connection.makefile("r", encoding="utf-8") as reader:
                    line = reader.readline()
        except OSError as error:
            raise BridgeError(
                f"STB transport unavailable: {error}", layer="local_transport",
                code="STB_TRANSPORT_ERROR"
            ) from error

        if not line:
            raise BridgeError(
                "STB returned empty response", layer="local_transport",
                code="STB_EMPTY_RESPONSE"
            )
        try:
            response = json.loads(line)
        except (ValueError, TypeError) as error:
            raise BridgeError(
                "STB returned invalid JSON", layer="local_transport",
                code="STB_INVALID_RESPONSE"
            ) from error
        if not isinstance(response, dict):
            raise BridgeError(
                "STB returned non-object response", layer="local_transport",
                code="STB_INVALID_RESPONSE"
            )
        if not response.get("ok"):
            raise bridge_failure(response.get("error"))
        return response["result"]

    def session(self, name: str) -> dict[str, Any]:
        sessions = self.call("terminal_session_list").get("sessions", [])
        for managed_session in sessions:
            if managed_session["name"] == name:
                return managed_session
        raise BridgeError(
            f"managed session not found: {name}", layer="adapter",
            code="MANAGED_SESSION_NOT_FOUND"
        )
