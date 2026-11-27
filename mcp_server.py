"""MCP server exposing the two approval-gated actions.

Tools
  append_to_notes(entry, approval_id)       -> appends the entry to the shared notes doc
  create_email_draft(subject, body, to, approval_id) -> creates an email DRAFT (never sends)

Backends (local by default, real services when credentials are set):
  Notes:  outputs/notes/product_pulse_log.md (+ .jsonl). Also a Notion page when
          NOTION_TOKEN and NOTION_PAGE_ID are set.
  Email:  outputs/email_drafts/*.eml (+ .md). Also a Gmail draft via IMAP when
          GMAIL_ADDRESS and GMAIL_APP_PASSWORD are set. There is no send code anywhere.

Run standalone:  python mcp_server.py   (stdio transport; the app starts it automatically)
"""
from __future__ import annotations

import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from pulse import approval, config  # noqa: E402

NOTES_DIR = config.OUT / "notes"
DRAFTS_DIR = config.OUT / "email_drafts"
REQUIRED_ENTRY_KEYS = {"date", "top_themes", "weekly_pulse", "identified_fee_issue", "explanation_bullets", "source_links"}

mcp = FastMCP("groww-pulse-actions")


# ---------------------------------------------------------------------------
def _entry_markdown(entry: dict) -> str:
    lines = [f"\n---\n\n## Weekly Product Pulse: {entry['date']}", "", "**Top themes:** " + "; ".join(entry["top_themes"]),
             "", "**Identified fee issue:** " + entry["identified_fee_issue"], "", "### Weekly pulse", "",
             re.sub(r"^(#+) ", lambda m: "#" * min(6, len(m.group(1)) + 3) + " ", entry["weekly_pulse"], flags=re.M), "", "### Fee explanation", ""]
    lines += [f"- {b}" for b in entry["explanation_bullets"]]
    lines += ["", "**Sources:** " + " | ".join(entry["source_links"]), ""]
    return "\n".join(lines)


def _notion_append(entry: dict) -> str:
    token, page = os.getenv("NOTION_TOKEN"), os.getenv("NOTION_PAGE_ID")
    if not (token and page):
        return "skipped (NOTION_TOKEN / NOTION_PAGE_ID not set)"

    def para(text, kind="paragraph"):
        return {"object": "block", "type": kind, kind: {"rich_text": [{"type": "text", "text": {"content": text[:1990]}}]}}

    blocks = [para(f"Weekly Product Pulse: {entry['date']}", "heading_2"),
              para("Top themes: " + "; ".join(entry["top_themes"])),
              para("Identified fee issue: " + entry["identified_fee_issue"]),
              para(entry["weekly_pulse"]),
              *[para(b, "bulleted_list_item") for b in entry["explanation_bullets"]],
              para("Sources: " + " | ".join(entry["source_links"]))]
    r = requests.patch(f"https://api.notion.com/v1/blocks/{page}/children",
                       headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
                       json={"children": blocks}, timeout=30)
    return "appended to Notion page" if r.ok else f"Notion error {r.status_code}: {r.text[:200]}"


def _gmail_draft(msg: EmailMessage) -> str:
    user, pw = os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD")
    if not (user and pw):
        return "skipped (GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set)"
    try:
        with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
            imap.login(user, pw)
            if not msg["From"]:
                msg["From"] = user
            typ, _ = imap.append('"[Gmail]/Drafts"', r"(\Draft)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        return "saved to Gmail Drafts" if typ == "OK" else f"Gmail returned {typ}"
    except Exception as e:  # report, never crash the tool
        return f"Gmail error: {e}"


# ---------------------------------------------------------------------------
@mcp.tool()
def append_to_notes(entry: dict, approval_id: str) -> str:
    """Append a weekly pulse entry to the shared product notes doc. Requires a human approval id.

    entry keys: date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links
    """
    ok, why = approval.consume(approval_id, "append_to_notes", entry)
    if not ok:
        return json.dumps({"status": "blocked", "reason": why})
    missing = REQUIRED_ENTRY_KEYS - entry.keys()
    if missing:
        return json.dumps({"status": "error", "reason": f"missing keys: {sorted(missing)}"})
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    doc = NOTES_DIR / "product_pulse_log.md"
    if not doc.exists():
        doc.write_text("# Groww Product Pulse Log\n\nShared notes doc. Entries are appended by the MCP "
                       "`append_to_notes` tool after human approval.\n", encoding="utf-8")
    with open(doc, "a", encoding="utf-8") as fh:
        fh.write(_entry_markdown(entry))
    with open(NOTES_DIR / "product_pulse_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**entry, "approval_id": approval_id,
                             "appended_at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
    return json.dumps({"status": "appended", "doc": str(doc.relative_to(config.ROOT)), "notion": _notion_append(entry)})


@mcp.tool()
def create_email_draft(subject: str, body: str, approval_id: str, to: str = "") -> str:
    """Create an email DRAFT for review. Never sends. Requires a human approval id."""
    payload = {"subject": subject, "body": body, "to": to}
    ok, why = approval.consume(approval_id, "create_email_draft", payload)
    if not ok:
        return json.dumps({"status": "blocked", "reason": why})
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to
    msg["X-Unsent"] = "1"  # opens as an editable draft in Outlook / Apple Mail
    msg.set_content(body)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    (DRAFTS_DIR / f"{stem}.eml").write_bytes(msg.as_bytes())
    (DRAFTS_DIR / f"{stem}.md").write_text(f"To: {to or '(add recipients)'}\nSubject: {subject}\n\n{body}\n",
                                           encoding="utf-8")
    return json.dumps({"status": "draft_created", "file": f"outputs/email_drafts/{stem}.eml",
                       "gmail": _gmail_draft(msg), "sent": False})


if __name__ == "__main__":
    mcp.run()  # stdio
