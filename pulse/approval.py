"""Approval gate shared by the UI/CLI (which grant approvals) and the MCP server (which checks them).

Flow:
  1. The workflow builds the exact tool payloads and calls `request()` -> status "pending".
  2. A human reviews the payloads and calls `approve()` (Streamlit button or CLI y/N).
  3. Each MCP tool call must carry the approval id. The server calls `consume()`, which
     rejects the call unless the approval is "approved", the payload hash matches what the
     human saw, and that tool has not already used it.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from . import config

STORE = config.OUT / "approvals.json"


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _load() -> dict:
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else {}


def _save(data: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def request(actions: dict[str, dict]) -> str:
    """actions: {tool_name: payload}. Returns a pending approval id."""
    data = _load()
    aid = uuid.uuid4().hex[:12]
    data[aid] = {
        "status": "pending",
        "requested_at": datetime.now().isoformat(timespec="seconds"),
        "actions": {tool: {"hash": payload_hash(p), "used": False} for tool, p in actions.items()},
    }
    _save(data)
    return aid


def approve(aid: str, approver: str) -> None:
    data = _load()
    if aid not in data or data[aid]["status"] != "pending":
        raise ValueError("Approval not found or not pending")
    data[aid].update(status="approved", approver=approver, approved_at=datetime.now().isoformat(timespec="seconds"))
    _save(data)


def reject(aid: str, approver: str) -> None:
    data = _load()
    if aid in data:
        data[aid].update(status="rejected", approver=approver, decided_at=datetime.now().isoformat(timespec="seconds"))
        _save(data)


def consume(aid: str, tool: str, payload: dict) -> tuple[bool, str]:
    data = _load()
    rec = data.get(aid)
    if rec is None:
        return False, "No such approval id. A human must approve this action first."
    if rec["status"] != "approved":
        return False, f"Approval is '{rec['status']}', not 'approved'."
    act = rec["actions"].get(tool)
    if act is None:
        return False, f"Tool '{tool}' was not part of the approved actions."
    if act["used"]:
        return False, "This approval was already used for this tool."
    if act["hash"] != payload_hash(payload):
        return False, "Payload differs from what was approved."
    act["used"] = True
    act["used_at"] = datetime.now().isoformat(timespec="seconds")
    _save(data)
    return True, "ok"


def status(aid: str) -> dict | None:
    return _load().get(aid)
