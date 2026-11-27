"""Orchestration: reviews -> insights -> pulse + explainer -> payloads -> (approval) -> MCP tools."""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import date

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import approval, config
from .analyze import Insights, analyze
from .generate import Explainer, build_explainer, build_pulse, to_plain

SERVER = config.ROOT / "mcp_server.py"


@dataclass
class Result:
    insights: Insights
    pulse_md: str
    explainer: Explainer
    notes_entry: dict
    email: dict


def run_analysis(df=None) -> Result:
    ins = analyze(df)
    pulse_md = build_pulse(ins)
    exp = build_explainer(ins)
    today = date.today().isoformat()
    notes_entry = {
        "date": today,
        "top_themes": [t.label for t in ins.top_themes],
        "weekly_pulse": pulse_md,
        "identified_fee_issue": f"{ins.fee.label}: {ins.fee.mentions} reviews mention it, "
                                f"{ins.fee.confused_mentions} explicitly say the charges were unclear or unexpected.",
        "explanation_bullets": exp.bullets,
        "source_links": [s["url"] for s in exp.links],
    }
    body = (
        "Hi team,\n\nHere is this week's product pulse and a reusable support snippet for the most "
        "frequently misunderstood charge in user reviews.\n\n"
        "=== WEEKLY PRODUCT PULSE ===\n\n" + to_plain(pulse_md) +
        "\n\n=== SUPPORT SNIPPET (copy into replies / help article) ===\n\n" + exp.plain() +
        "\n\nThis is a draft for review. Please check the figures against the linked sources before sending.\n"
    )
    email = {"subject": f"Weekly Product Pulse + Customer Clarification — {date.today().strftime('%d %b %Y')}",
             "body": body, "to": ""}
    return Result(ins, pulse_md, exp, notes_entry, email)


def request_approval(res: Result) -> str:
    return approval.request({"append_to_notes": res.notes_entry, "create_email_draft": res.email})


async def _call_tools(res: Result, approval_id: str) -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], cwd=str(config.ROOT))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            notes = await session.call_tool("append_to_notes", {"entry": res.notes_entry, "approval_id": approval_id})
            draft = await session.call_tool("create_email_draft", {**res.email, "approval_id": approval_id})
    return {"tools_available": tools,
            "append_to_notes": json.loads(notes.content[0].text),
            "create_email_draft": json.loads(draft.content[0].text)}


def execute(res: Result, approval_id: str) -> dict:
    """Call the MCP tools. The server itself re-checks the approval."""
    return asyncio.run(_call_tools(res, approval_id))
