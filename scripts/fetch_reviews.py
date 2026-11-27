"""Fetch public Google Play reviews for the Groww app (last N weeks) into data/reviews.csv.

Usage:  python scripts/fetch_reviews.py --weeks 12
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews

APP_ID = "com.nextbillion.groww"
OUT = Path(__file__).resolve().parent.parent / "data" / "reviews.csv"

# Scrub anything that looks like personal data before saving.
_PII = [
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I), "[PAN]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"), "[PHONE]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[NUMBER]"),
]


def scrub(text: str) -> str:
    for pat, repl in _PII:
        text = pat.sub(repl, text)
    return " ".join(text.split())


def main(weeks: int, max_pages: int) -> None:
    cutoff = datetime.now() - timedelta(weeks=weeks)
    rows, token = [], None
    for _ in range(max_pages):
        batch, token = reviews(APP_ID, lang="en", country="in", sort=Sort.NEWEST,
                               count=200, continuation_token=token)
        if not batch:
            break
        for r in batch:
            if r["at"] < cutoff:
                continue
            rows.append({
                "review_id": r["reviewId"],
                "date": r["at"].strftime("%Y-%m-%d"),
                "rating": r["score"],
                "thumbs_up": r["thumbsUpCount"],
                "app_version": r.get("reviewCreatedVersion") or "",
                "text": scrub(r["content"] or ""),
            })
        if batch[-1]["at"] < cutoff or token is None:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} reviews from {rows[-1]['date']} to {rows[0]['date']} -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=12)
    ap.add_argument("--max-pages", type=int, default=400)
    a = ap.parse_args()
    main(a.weeks, a.max_pages)
