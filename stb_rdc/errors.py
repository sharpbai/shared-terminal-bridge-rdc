"""Error provenance for calls which reached the local adapter.

Upstream OpenAI/RDC refusals happen before this process starts and cannot be
observed or classified here.
"""
import json


class BridgeError(RuntimeError):
    def __init__(self, message, *, layer="adapter", code="ADAPTER_ERROR", detail=None):
        super().__init__(message)
        self.layer = layer
        self.code = code
        self.detail = detail

    def as_dict(self):
        return {"ok": False, "error": {"layer": self.layer, "code": self.code,
                "message": str(self), "detail": self.detail}}


def bridge_failure(payload):
    """Preserve authoritative STB codes; never infer command/API failures."""
    detail = payload if isinstance(payload, dict) else {"message": str(payload)}
    code = str(detail.get("code") or "BRIDGE_ERROR")
    return BridgeError(json.dumps(detail, ensure_ascii=False), layer="stb",
                       code=code, detail=detail)
