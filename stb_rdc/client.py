"""Small newline-delimited JSON client for the local STB Unix socket."""

import json
import socket
from pathlib import Path
from typing import Any

from .config import DEFAULT_SOCKET


class BridgeError(RuntimeError):
    """Raised when the local Bridge cannot complete an API request."""


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
            raise BridgeError(f"STB unavailable: {error}") from error

        if not line:
            raise BridgeError("STB returned empty response")

        response = json.loads(line)
        if not response.get("ok"):
            detail = json.dumps(response.get("error"), ensure_ascii=False)
            raise BridgeError(detail)
        return response["result"]

    def session(self, name: str) -> dict[str, Any]:
        sessions = self.call("terminal_session_list").get("sessions", [])
        for managed_session in sessions:
            if managed_session["name"] == name:
                return managed_session
        raise BridgeError(f"managed session not found: {name}")
