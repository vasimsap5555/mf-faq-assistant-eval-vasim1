"""Configuration: paths, theme seeds, fee taxonomy and official sources."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
REVIEWS_CSV = DATA / "reviews.csv"

PRODUCT = "Groww"
APP_ID = "com.nextbillion.groww"
MIN_WORDS = 5          # reviews shorter than this ("good", "nice app") carry no theme signal
MAX_THEMES = 5
PULSE_WORD_LIMIT = 250
EXPLAINER_MAX_BULLETS = 6

# ---------------------------------------------------------------------------
# Themes. Seed phrases initialise the cluster centroids; the clustering step then
# re-estimates each centroid from the reviews assigned to it (seeded k-means).
# ---------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "performance": {
        "label": "App performance & trading reliability",
        "seeds": [
            r"\blag", r"\bslow\b", r"freez", r"\bstuck\b", r"crash", r"hang(?:s|ing)?\b", r"buffer",
            r"glitch", r"\bbug", r"not (?:loading|working|opening)", r"server", r"chart(?:s)? (?:not|lag|slow|delay|stuck)",
            r"order (?:not|stuck|reject|fail|delay)", r"\bexecution", r"\bdelay(?:ed)? (?:in )?(?:order|price|chart)",
            r"\bupdate\b.*\b(?:worst|issue|problem|bug|reset)", r"refresh", r"technical (?:issue|glitch)",
        ],
    },
    "funds": {
        "label": "Withdrawals, payments & fund delays",
        "seeds": [
            r"withdraw", r"\bredeem", r"redemption", r"refund", r"not (?:yet )?credited", r"\bcredited",
            r"add(?:ed|ing)? (?:money|funds?)", r"deposit", r"\bpayout", r"\bus stock", r"money (?:is |was )?(?:stuck|deducted)",
            r"\bmandate", r"autopay", r"bank account", r"\bblocked fund",
        ],
    },
    "support": {
        "label": "Customer support responsiveness",
        "seeds": [
            r"customer (?:care|support|service)", r"\bsupport team", r"no (?:reply|response)", r"not (?:responding|replying)",
            r"\bticket", r"raised (?:a |the )?(?:query|complaint|issue)", r"\bhelp ?(?:line|desk|center|centre)",
            r"\bchat support", r"\bagent\b", r"unresolved", r"no resolution", r"complain",
        ],
    },
    "charges": {
        "label": "Charges & fee transparency",
        "seeds": [
            r"brokerage", r"\bcharg", r"hidden", r"\bfees?\b", r"\bdp\b", r"\bstt\b", r"\bgst\b",
            r"deduct", r"\bamc\b", r"\bper order", r"contract note", r"\btaxes\b", r"costly", r"expensive",
        ],
    },
    "ease": {
        "label": "Ease of use & app UI",
        "seeds": [
            r"easy to (?:use|understand|invest|navigate)", r"user[- ]friendly", r"\bbeginner", r"\bsimple\b",
            r"\bclean (?:ui|interface)", r"\binterface", r"\bsmooth", r"\bconvenient", r"\bbest app",
            r"\bui\b", r"hassle[- ]free",
        ],
    },
}

# ---------------------------------------------------------------------------
# Fee taxonomy used to find the most frequently misunderstood charge.
# ---------------------------------------------------------------------------
FEE_TYPES: dict[str, dict] = {
    "trading_charges": {
        "label": "Brokerage & per-order charges on stock trades (incl. DP charges on selling)",
        "patterns": [r"brokerage", r"\bdp\b", r"depository", r"\bstt\b", r"per order", r"sell order",
                     r"\btransaction charge", r"contract note", r"20 ?rs", r"₹ ?20\b", r"rs\.? ?20\b"],
    },
    "account_charges": {
        "label": "Account opening / maintenance (AMC) / modification charges",
        "patterns": [r"\bamc\b", r"maintenance charge", r"account opening", r"opening charge",
                     r"changing (?:the )?details", r"modification"],
    },
    "mtf_interest": {
        "label": "MTF interest and pledge charges",
        "patterns": [r"\bmtf\b", r"interest", r"pledg"],
    },
    "fund_costs": {
        "label": "Mutual fund exit load / expense ratio",
        "patterns": [r"exit load", r"expense ratio", r"\bter\b"],
    },
    "fno_charges": {
        "label": "F&O charges",
        "patterns": [r"\bf&o\b", r"\bfno\b", r"\boption(?:s)? trading"],
    },
}
FEE_CONTEXT = r"brokerage|charg|\bfees?\b|deduct|\bdp\b|\bstt\b|\bgst\b|\bamc\b|hidden|interest|exit load|expense ratio"
CONFUSION_CUES = (
    r"hidden|not (?:clearly )?(?:shown|showing|displayed|visible|mentioned|explained)|never display|"
    r"without (?:any )?(?:reason|info|information|telling)|didn'?t know|confus|unexpected|surpris|why (?:is|are|did|do)|"
    r"\bless than\b|only (?:around |about )?(?:₹|rs)|\bdeducted\b|\bshould (?:be able to )?(?:see|show)|clear(?:ly)?|transparen"
)

# ---------------------------------------------------------------------------
# Official sources (also listed in SOURCES.md).
# ---------------------------------------------------------------------------
SOURCES = [
    {"id": "SRC1", "title": "Groww - Brokerage Charges & Pricing", "url": "https://groww.in/pricing",
     "use": "Equity brokerage, DP charge and statutory charges table"},
    {"id": "SRC2", "title": "Groww Help - How much does Groww charge for stocks?",
     "url": "https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1",
     "use": "Brokerage formula, minimum charge, DP charge split and GST"},
    {"id": "SRC3", "title": "Groww Help - Are DP charges per stock or per order?",
     "url": "https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/are-dp-charges-per-stock-or-per-order",
     "use": "DP charge applies once per sell order"},
    {"id": "SRC4", "title": "Groww Help - Why is my brokerage more than 20 rupees?",
     "url": "https://groww.in/help/payments-&-withdrawals/payments-charges/why-is-my-brokerage-more-than-20-rupees--71",
     "use": "Brokerage is per order, so several orders can exceed ₹20 a day"},
    {"id": "SRC5", "title": "Google Play - Groww reviews (data source)",
     "url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN",
     "use": "Public user reviews analysed for the pulse"},
]
EXPLAINER_LINKS = ["SRC1", "SRC2"]   # the two official links shown in the fee explainer
LAST_CHECKED = "2026-11-26"
