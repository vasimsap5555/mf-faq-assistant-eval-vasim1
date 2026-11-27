"""Step 1 - Review intelligence layer.

* Seeded clustering of reviews into at most 5 themes (TF-IDF + seeded k-means).
* Top 3 themes ranked by number of critical (1-3 star) reviews.
* 3 real user quotes, one per top theme.
* The most frequently misunderstood fee/charge.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from . import config

_THEME_KEYS = list(config.THEMES)
_SEEDS = {k: [re.compile(p, re.I) for p in v["seeds"]] for k, v in config.THEMES.items()}
# Tie-break when two themes have equal seed hits: specific issues before generic ones.
_PRIORITY = ["charges", "funds", "support", "performance", "ease"]


@dataclass
class Theme:
    key: str
    label: str
    reviews: int
    critical: int
    avg_rating: float
    share_all: float
    share_last_week: float
    top_terms: list[str]
    weekly: dict[str, int]


@dataclass
class Quote:
    theme: str
    text: str
    rating: int
    date: str
    thumbs_up: int


@dataclass
class FeeIssue:
    key: str
    label: str
    mentions: int
    confused_mentions: int
    avg_rating: float
    table: list[dict]
    evidence: list[Quote] = field(default_factory=list)


@dataclass
class Insights:
    window_start: str
    window_end: str
    week_start: str
    total_reviews: int
    substantive_reviews: int
    avg_rating: float
    themes: list[Theme]           # all clustered themes, ranked
    top_themes: list[Theme]       # top 3
    quotes: list[Quote]           # 3 quotes, one per top theme
    fee: FeeIssue
    unassigned: int


# ---------------------------------------------------------------------------
def load_reviews(path=config.REVIEWS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"review_id": str})
    df["text"] = df["text"].fillna("").astype(str)
    df["date"] = pd.to_datetime(df["date"])
    df["rating"] = df["rating"].astype(int)
    df["thumbs_up"] = df.get("thumbs_up", 0)
    df["n_words"] = df["text"].str.split().str.len()
    return df


def _is_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) > 0.9


def _seed_hits(text: str) -> np.ndarray:
    return np.array([sum(bool(p.search(text)) for p in _SEEDS[k]) for k in _THEME_KEYS], dtype=float)


def cluster(df: pd.DataFrame, iterations: int = 4, alpha: float = 0.12, tau: float = 0.22) -> pd.DataFrame:
    """Seeded k-means on TF-IDF vectors. Returns df with a `theme` column (None = unassigned).

    A review joins a theme if it contains one of the theme's seed phrases, or if its
    TF-IDF vector is close enough (cosine >= tau) to the theme centroid. Centroids are
    re-estimated from members on each iteration."""
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=0.5, sublinear_tf=True, stop_words="english")
    X = normalize(vec.fit_transform(df["text"]))
    hits = np.vstack([_seed_hits(t) for t in df["text"]])
    hit_bonus = alpha * np.minimum(hits, 3)

    # Initial labels: reviews with seed hits.
    prio = np.array([_PRIORITY.index(k) for k in _THEME_KEYS])
    labels = np.full(len(df), -1)
    has = hits.sum(1) > 0
    labels[has] = [int(np.lexsort((prio, -row))[0]) for row in hits[has]]

    for _ in range(iterations):
        centroids = []
        for j in range(len(_THEME_KEYS)):
            members = X[labels == j]
            c = np.asarray(members.mean(0)).ravel() if members.shape[0] else np.zeros(X.shape[1])
            centroids.append(c / (np.linalg.norm(c) or 1))
        C = np.vstack(centroids)
        sim = np.asarray(X @ C.T)
        best = (sim + hit_bonus).argmax(1)
        keep = (hits.sum(1) > 0) | (sim.max(1) >= tau)
        labels = np.where(keep, best, -1)

    out = df.copy()
    out["theme"] = [(_THEME_KEYS[i] if i >= 0 else None) for i in labels]
    out["seed_hit"] = [bool(hits[i, labels[i]]) if labels[i] >= 0 else False for i in range(len(df))]
    terms = np.array(vec.get_feature_names_out())
    out.attrs["top_terms"] = {}
    for j, k in enumerate(_THEME_KEYS):
        m = X[labels == j]
        if m.shape[0]:
            weights = np.asarray(m.mean(0)).ravel()
            out.attrs["top_terms"][k] = [t for t in terms[weights.argsort()[::-1]] if len(t) > 2][:8]
    return out


# ---------------------------------------------------------------------------
_SENT = re.compile(r"(?<=[.!?])\s+")


def _quote_text(text: str, max_words: int = 45) -> str:
    """Verbatim quote: whole sentences up to ~max_words, '…' if cut."""
    out, n = [], 0
    for s in _SENT.split(text.strip()):
        w = len(s.split())
        if out and n + w > max_words:
            break
        out.append(s)
        n += w
    q = " ".join(out)
    words = q.split()
    if len(words) > max_words:
        q = " ".join(words[:max_words]).rstrip(",;:") + "…"
    elif len(q) < len(text.strip()):
        q = q.rstrip() + " …"
    return q


def _pick_quote(rows: pd.DataFrame, theme_key: str, max_words: int = 25) -> Quote | None:
    """Most-upvoted review whose opening sentences (<= max_words) state the theme on their own."""
    if rows.empty:
        return None
    seeds = _SEEDS[theme_key]
    best = None
    for _, r in rows[rows["text"].map(_is_english)].sort_values("thumbs_up", ascending=False).iterrows():
        q = _quote_text(r["text"], max_words)
        complete = not q.endswith("…")
        if any(p.search(q) for p in seeds) and len(q.split()) >= 8:
            cand = Quote(theme_key, q, int(r["rating"]), r["date"].strftime("%Y-%m-%d"), int(r["thumbs_up"]))
            if complete:
                return cand
            best = best or cand
    return best


# ---------------------------------------------------------------------------
def detect_fee_issue(sub: pd.DataFrame) -> FeeIssue:
    fee_rows = sub[sub["text"].str.contains(config.FEE_CONTEXT, case=False, regex=True)]
    confused = fee_rows["text"].str.contains(config.CONFUSION_CUES, case=False, regex=True)
    table = []
    for key, meta in config.FEE_TYPES.items():
        pat = "|".join(meta["patterns"])
        m = fee_rows["text"].str.contains(pat, case=False, regex=True)
        table.append({
            "key": key, "label": meta["label"], "mentions": int(m.sum()),
            "confused_mentions": int((m & confused).sum()),
            "avg_rating": round(float(fee_rows.loc[m, "rating"].mean()), 2) if m.any() else None,
        })
    table.sort(key=lambda r: (r["confused_mentions"], r["mentions"]), reverse=True)
    top = table[0]
    pat = "|".join(config.FEE_TYPES[top["key"]]["patterns"])
    strict = r"brokerage|\bdp\b|per[- ]order|deduction|contract note"
    ev = fee_rows[fee_rows["text"].str.contains(pat, case=False, regex=True) & confused & (fee_rows["rating"] <= 3)
                  & fee_rows["text"].str.contains(strict, case=False, regex=True)]
    ev = ev[ev["text"].map(_is_english) & ev["n_words"].between(14, 90)].sort_values("thumbs_up", ascending=False)
    strict_re = re.compile(strict, re.I)
    evidence = []
    for _, r in ev.iterrows():
        q = _quote_text(r["text"])
        if strict_re.search(q):  # the fee term must be visible in the quoted part itself
            evidence.append(Quote("charges", q, int(r["rating"]), r["date"].strftime("%Y-%m-%d"), int(r["thumbs_up"])))
        if len(evidence) == 3:
            break
    return FeeIssue(top["key"], top["label"], top["mentions"], top["confused_mentions"],
                    top["avg_rating"] or 0.0, table, evidence)


# ---------------------------------------------------------------------------
def analyze(df: pd.DataFrame | None = None) -> Insights:
    df = load_reviews() if df is None else df
    end = df["date"].max()
    week_start = end - timedelta(days=6)
    sub = df[(df["n_words"] >= config.MIN_WORDS)].reset_index(drop=True)
    sub = cluster(sub)

    df_week_index = sub["date"] >= week_start
    themes = []
    for k in _THEME_KEYS:
        rows = sub[sub["theme"] == k]
        if rows.empty:
            continue
        weekly = rows.groupby(rows["date"].dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")).size()
        themes.append(Theme(
            key=k, label=config.THEMES[k]["label"], reviews=len(rows),
            critical=int((rows["rating"] <= 3).sum()), avg_rating=round(float(rows["rating"].mean()), 2),
            share_all=round(len(rows) / len(sub), 4),
            share_last_week=round(float((sub.loc[df_week_index, "theme"] == k).mean()), 4),
            top_terms=sub.attrs["top_terms"].get(k, []), weekly=weekly.to_dict(),
        ))
    themes.sort(key=lambda t: (t.critical, t.reviews), reverse=True)
    themes = themes[: config.MAX_THEMES]
    top = themes[:3]
    quotes = [q for t in top if (q := _pick_quote(sub[(sub["theme"] == t.key) & (sub["rating"] <= 3)], t.key))]

    return Insights(
        window_start=df["date"].min().strftime("%Y-%m-%d"), window_end=end.strftime("%Y-%m-%d"),
        week_start=week_start.strftime("%Y-%m-%d"), total_reviews=len(df), substantive_reviews=len(sub),
        avg_rating=round(float(df["rating"].mean()), 2), themes=themes, top_themes=top, quotes=quotes,
        fee=detect_fee_issue(sub), unassigned=int(sub["theme"].isna().sum()),
    )
