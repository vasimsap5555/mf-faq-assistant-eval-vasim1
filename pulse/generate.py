"""Steps 2 and 3 - weekly product pulse (internal) and fee explainer (customer-facing).

Both are generated deterministically from the insights, so every number and quote
traces back to the reviews CSV. Hard limits are enforced in code:
pulse <= 250 words; explainer <= 6 bullets, exactly 2 official links, "Last checked".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from . import config
from .analyze import Insights

# One action idea per theme; the pulse uses the ideas for its top 3 themes.
ACTIONS = {
    "performance": "Set latency budgets for charts and order placement in live markets; show an in-app incident banner.",
    "support": "Route money-stuck and failed-order tickets to a priority queue with a published first-response time.",
    "charges": "Show brokerage, DP charge, taxes and net amount on the sell confirmation screen, not only in the contract note.",
    "funds": "Add a withdrawal and US-funding tracker with a committed date, and alert users when it slips.",
    "ease": "Run UI changes past a beginner usability check, and keep chart setups across app updates.",
}

FEE_EXPLAINERS = {
    "trading_charges": {
        "title": "Brokerage and other charges on stock trades",
        "question": "Why did I receive less than expected after selling shares?",
        "bullets": [
            "Brokerage is charged on every executed order, both buy and sell: ₹20 or 0.1% of the trade value, whichever is lower. If that is below ₹5, the minimum is the lower of ₹5 or 2.5% of the trade value.",
            "Because brokerage is per order, buying and selling a stock are two separate charges, and several orders in one day can add up to more than ₹20. F&O orders are a flat ₹20 each.",
            "Selling shares from your demat account adds a DP charge of ₹20 per sell order (₹3.50 depository + ₹16.50 Groww; ₹19.75 for women investors), plus GST. Groww's ₹16.50 part is waived when the sale value is below ₹100.",
            "The DP charge applies per sell order, not per share: selling the same stock in two separate orders means two DP charges.",
            "Government and exchange charges are added on top. For delivery trades: STT of 0.1% on buy and sell, stamp duty of 0.015% on buy, exchange transaction charges (0.00297% on NSE), SEBI turnover fee (0.0001%), and 18% GST on brokerage and charges.",
            "Your contract note lists the exact charges for each trade, and the Brokerage Calculator on Groww's pricing page estimates them before you place an order.",
        ],
    },
}


@dataclass
class Explainer:
    fee_key: str
    title: str
    question: str
    bullets: list[str]
    links: list[dict]
    last_checked: str

    def markdown(self) -> str:
        lines = [f"### {self.title}", f"*{self.question}*", ""]
        lines += [f"- {b}" for b in self.bullets]
        lines += ["", "**Official sources:**"]
        lines += [f"- [{s['title']}]({s['url']})" for s in self.links]
        lines += ["", f"Last checked: {_fmt(self.last_checked)}"]
        return "\n".join(lines)

    def plain(self) -> str:
        lines = [f"{self.title}", f"{self.question}", ""]
        lines += [f"• {b}" for b in self.bullets]
        lines += ["", "Official sources:"] + [f"- {s['title']}: {s['url']}" for s in self.links]
        lines += ["", f"Last checked: {_fmt(self.last_checked)}"]
        return "\n".join(lines)


def _fmt(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")


def word_count(md: str) -> int:
    text = re.sub(r"[#>*_`\-|]", " ", md)
    return len(re.findall(r"[\w₹%.,'’/&+-]+", text))


def _short(text: str, max_words: int = 26) -> str:
    """Trim a verbatim quote at a sentence or word boundary for the word-limited pulse."""
    words = text.rstrip(" …").split()
    if len(words) <= max_words:
        return text
    cut = " ".join(words[:max_words])
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] + " …" if end > len(cut) * 0.5 else cut.rstrip(",;:") + "…"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def build_pulse(ins: Insights) -> str:
    top = ins.top_themes
    by_key = {t.key: t for t in ins.themes}
    lines = [
        f"# {config.PRODUCT} Weekly Product Pulse: {_fmt(ins.week_start)} to {_fmt(ins.window_end)}",
        f"Source: {ins.total_reviews:,} Play Store reviews, {_fmt(ins.window_start)} to {_fmt(ins.window_end)} "
        f"({ins.substantive_reviews:,} detailed enough to theme).",
        "",
        "## Top themes",
    ]
    for i, t in enumerate(top, 1):
        trend = "up" if t.share_last_week > t.share_all else "down"
        lines.append(f"{i}. **{t.label}**: {t.critical} critical reviews, avg {t.avg_rating}★; "
                     f"{_pct(t.share_last_week)} this week ({trend} from {_pct(t.share_all)}).")
    lines += ["", "## What users say"]
    for q in ins.quotes:
        lines += [f"> \"{_short(q.text)}\" ({q.rating}★)", ""]
    # Key observation: fastest-rising theme this week + the fee confusion.
    rising = max(ins.themes, key=lambda t: t.share_last_week - t.share_all)
    fee = ins.fee
    charges = by_key.get("charges")
    obs = (f"**{rising.label}** is rising fastest ({_pct(rising.share_last_week)} this week vs "
           f"{_pct(rising.share_all)} over 12 weeks). ")
    if charges:
        obs += (f"Most-confused fee: **brokerage and per-order charges on stock trades** ({fee.mentions} reviews). "
                f"Users see the total deduction only after selling and call it hidden charges.")
    lines += ["## Key observation", obs, "", "## Action ideas"]
    keys = [t.key for t in top]
    if "charges" not in keys:  # the fee issue always gets an action, replacing the third theme's
        keys = keys[:2] + ["charges"]
    for i, k in enumerate(keys, 1):
        lines.append(f"{i}. {ACTIONS[k]}")
    md = "\n".join(lines)
    n = word_count(md)
    if n > config.PULSE_WORD_LIMIT:
        raise ValueError(f"Pulse is {n} words; limit is {config.PULSE_WORD_LIMIT}")
    return md


def to_plain(md: str) -> str:
    """Markdown -> plain text for email bodies."""
    out = []
    for line in md.splitlines():
        if line.startswith("#"):
            line = line.lstrip("# ").upper()
        line = re.sub(r"^> ", "  ", line)
        line = line.replace("**", "")
        out.append(line)
    return "\n".join(out)


def demote(md: str, levels: int = 3) -> str:
    """Shrink headings for display inside the app."""
    return re.sub(r"^(#+) ", lambda m: "#" * min(6, len(m.group(1)) + levels) + " ", md, flags=re.M)


def build_explainer(ins: Insights) -> Explainer:
    spec = FEE_EXPLAINERS.get(ins.fee.key)
    if spec is None:
        raise KeyError(f"No verified explainer for fee type '{ins.fee.key}'. Add one to FEE_EXPLAINERS with official sources.")
    bullets = spec["bullets"][: config.EXPLAINER_MAX_BULLETS]
    links = [s for s in config.SOURCES if s["id"] in config.EXPLAINER_LINKS]
    assert len(links) == 2 and all(s["url"].startswith("https://groww.in") for s in links)
    return Explainer(ins.fee.key, spec["title"], spec["question"], bullets, links, config.LAST_CHECKED)
