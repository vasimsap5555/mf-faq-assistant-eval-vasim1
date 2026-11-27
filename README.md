# Groww Review Pulse

An AI workflow that turns raw Groww Play Store reviews into a **weekly internal product pulse** and a **ready-to-use customer explanation** of the fee users misunderstand most. It then logs both to internal tools through **MCP**, but only after a person approves.

This is the same product as Milestone 4 (Groww, with the HDFC Mutual Fund FAQ assistant). It simulates a Product + Support workflow: product tracks sentiment, and support gets a clear explanation for recurring confusion.

**Live demo:** https://mf-faq-assistant-eval-vasim1-4nfpdrq2cyhbekid8bsizq.streamlit.app/

## What fee issue was identified from the reviews

**Brokerage and per-order charges on stock trades, including the DP charge on selling.**

| Fee type | Reviews mentioning it | Say it was unclear / hidden / unexpected |
|---|---|---|
| **Brokerage & per-order charges (incl. DP on selling)** | **89** | **10** |
| MTF interest & pledge charges | 21 | 4 |
| Account opening / AMC / modification charges | 13 | 2 |
| F&O charges | 12 | 2 |
| Mutual fund exit load / expense ratio | 3 | 2 |

Users don't object to a single number. They object to the **total deduction** they only see after selling. Typical reviews:

> "Whenever I sell stocks, the per-order charges and other deductions are not clearly displayed." (3★)
>
> "DEMONIC BROKERAGE OF RS.110.45 DEDUCTED OUT OF RS.230 PROFIT IN GROWW BYST TRADE.. UNREASONABLE" (3★)

**Why not exit load?** The assignment example uses exit load, and Milestone 4 covered mutual funds. In 11,088 real Groww reviews, though, exit load appears **0 times** and mutual fund costs only 3 times. The brief says the fee must come from what users are actually confused about, so the system picks the fee from the data and does not hard-code one.

## Results (12 weeks of real reviews)

- **Data:** 11,088 public Google Play reviews of Groww, 3 Sep to 25 Nov 2026. 2,734 are detailed enough (5+ words) to theme.
- **Themes (max 5), ranked by critical 1–3★ reviews:**
  1. App performance & trading reliability (175)
  2. Customer support responsiveness (163)
  3. Charges & fee transparency (139). Also the fastest-rising theme: 9.7% of reviews this week vs 7.6% over 12 weeks.
  4. Withdrawals, payments & fund delays (82)
  5. Ease of use & app UI (43; mostly praise, avg 4.68★)
- **Outputs:** see the `deliverables/` folder.

| Deliverable | File |
|---|---|
| Weekly product pulse (234 words) | `deliverables/weekly_pulse.md` |
| Fee explainer (6 bullets, 2 official links, "Last checked") | `deliverables/fee_explainer.md` |
| Notes doc with the appended entry | `deliverables/notes_doc_appended_entry.md` |
| Email draft (text and .eml) | `deliverables/email_draft.md`, `deliverables/email_draft.eml` |
| Approval record (who approved, when, payload hashes) | `deliverables/approval_record.json` |
| Screenshots | `deliverables/screenshots/` |
| Reviews CSV (full and 300-row sample) | `data/reviews.csv`, `data/reviews_sample.csv` |
| Source list (5 URLs) | `SOURCES.md` |

## How to run

```bash
pip install -r requirements.txt

streamlit run app.py          # web app (recommended)
python run_workflow.py --save # command-line version, asks y/N before any action

python scripts/fetch_reviews.py --weeks 12   # optional: re-download the latest reviews
```

**Deploy on Streamlit Community Cloud:** push this folder to GitHub (with `app.py` at the top level of the repo), then create an app with main file `app.py`. No API keys are needed.

## Where the MCP approval happens

```
reviews.csv → [1] themes + fee detection → [2] weekly pulse → [3] fee explainer
            → [4] APPROVAL GATE → MCP client → mcp_server.py → notes doc + email draft
```

1. **In the app, Step 4 "Approve MCP actions".** The app shows the exact payloads of both actions: the notes entry as JSON, and the email subject and body. **Approve and run** stays disabled until you type your name and tick "I have reviewed both actions". Reject records the decision and runs nothing. In the CLI, the same gate is a `y/N` prompt.
2. **In the MCP server itself** (`mcp_server.py`, via `pulse/approval.py`). Each tool call must carry an approval id, and the server blocks the call unless:
   - the approval status is `approved` by a named person;
   - the SHA-256 hash of the payload matches what the person saw, so the content can't change after approval;
   - that tool hasn't already used the approval, so it can't be replayed.

   This is tested: unapproved, unknown-id, tampered and replayed calls all return `"status": "blocked"`.

### MCP tools

| Tool | Does | Default target | Real service (optional) |
|---|---|---|---|
| `append_to_notes(entry, approval_id)` | Appends `{date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links}` | `outputs/notes/product_pulse_log.md` (+ `.jsonl`) | **Notion page:** set `NOTION_TOKEN` and `NOTION_PAGE_ID` |
| `create_email_draft(subject, body, to, approval_id)` | Creates a draft. **There is no send code anywhere.** | `outputs/email_drafts/*.eml` (opens as a draft in Outlook / Apple Mail) | **Gmail Drafts:** set `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` (Google app password) |

The email subject is `Weekly Product Pulse + Customer Clarification — <date>`. The body holds the weekly pulse plus the fee explanation as a reusable support snippet. On Streamlit Cloud, put the optional keys in **App settings → Secrets** as top-level entries; Streamlit exposes them as environment variables.

## How it works

- **Review intelligence** (`pulse/analyze.py`)
  - Reviews under 5 words ("good app") are skipped.
  - The rest are vectorised with TF-IDF and grouped by **seeded k-means**: each theme's centroid starts from seed phrases and is re-estimated from its members over 4 iterations.
  - A review joins a theme if it uses one of the theme's phrases, or if its text is very close (cosine ≥ 0.22) to the theme centroid. Reviews that are neither stay unassigned rather than being forced into a theme.
- **Ranking:** themes are ranked by the number of critical (1–3★) reviews, which reflects product pain better than raw volume, since 5-star "nice app" reviews dominate.
- **Quotes:** the most-upvoted review per top theme whose opening sentences state the issue on their own, quoted verbatim. Personal details (phone, email, PAN) are scrubbed when the reviews are downloaded.
- **Fee detection:** charge-related reviews are tagged by fee type, and the system picks the type with the most explicit confusion cues ("not clearly displayed", "hidden", "deducted", "less than"), breaking ties by mention count.
- **Generation** (`pulse/generate.py`) is deterministic, so every number traces back to the CSV. Hard limits are enforced in code: the pulse is ≤250 words (an error is raised if not), and the explainer has ≤6 bullets, exactly 2 official groww.in links, and "Last checked".

## Known limits

- **Seeded clustering:** themes start from a curated seed list, not purely unsupervised clustering. This keeps labels readable, but a brand-new topic would land in "unassigned" until a seed is added. 1,386 detailed reviews are unassigned, mostly general praise.
- **English only:** Hindi and Hinglish reviews are counted, but rarely match theme seeds.
- **Fee explainer coverage:** the explainer text is verified by hand for the detected fee (trading charges). If the data ever surfaces a different fee, the code stops and asks for a verified explainer rather than generating unverified figures.
- **Fee figures** come from Groww's pricing and help pages as of 26 Nov 2026; re-check them before each send.
- **No live connectors by default:** Notion and Gmail work only with your credentials. Otherwise the notes doc and draft are local files, which the app shows and lets you download.
