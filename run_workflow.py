"""Command-line version of the workflow with a terminal approval prompt.

Usage:  python run_workflow.py            (asks y/N before any MCP action)
        python run_workflow.py --save     (also writes the pulse and explainer to outputs/)
"""
from __future__ import annotations

import json
import sys

from pulse import approval, config
from pulse.generate import word_count
from pulse.workflow import execute, request_approval, run_analysis


def main() -> None:
    res = run_analysis()
    ins = res.insights
    print(f"\nTop themes: {', '.join(t.label for t in ins.top_themes)}")
    print(f"Fee issue:  {ins.fee.label} ({ins.fee.mentions} mentions)\n")
    print(res.pulse_md, f"\n\n[{word_count(res.pulse_md)} words]\n")
    print(res.explainer.markdown(), "\n")
    if "--save" in sys.argv:
        config.OUT.mkdir(exist_ok=True)
        (config.OUT / "weekly_pulse.md").write_text(res.pulse_md + "\n", encoding="utf-8")
        (config.OUT / "fee_explainer.md").write_text(res.explainer.markdown() + "\n", encoding="utf-8")

    aid = request_approval(res)
    print("=" * 70)
    print("APPROVAL REQUIRED. Proposed MCP actions:")
    print("  1. append_to_notes     ->", json.dumps({k: (v if k != "weekly_pulse" else "<pulse above>")
                                                       for k, v in res.notes_entry.items()}, ensure_ascii=False)[:300], "…")
    print("  2. create_email_draft  -> subject:", res.email["subject"], "(draft only, not sent)")
    answer = input("\nApprove both actions? [y/N] ").strip().lower()
    if answer != "y":
        approval.reject(aid, "cli-user")
        print("Rejected. Nothing was written.")
        return
    approval.approve(aid, input("Your name: ").strip() or "cli-user")
    print(json.dumps(execute(res, aid), indent=2))


if __name__ == "__main__":
    main()
