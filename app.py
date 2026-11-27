"""Groww Review Pulse - Streamlit UI.

Run:  streamlit run app.py
Flow: reviews CSV -> themes + fee issue -> weekly pulse + fee explainer -> HUMAN APPROVAL -> MCP tools.
"""
from __future__ import annotations

import html
import json

import pandas as pd
import streamlit as st

from pulse import approval, config
from pulse.analyze import load_reviews
from pulse.generate import demote, word_count
from pulse.workflow import execute, request_approval, run_analysis

st.set_page_config(page_title="Groww Review Pulse", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap');
:root { --ink:#17252F; --muted:#5B6B73; --teal:#0B6E6E; --teal-soft:#E3F0EE; --amber:#A86B12; --amber-soft:#F7EEDF; --rule:#D5DDDA; }
html, body, [class*="css"] { font-family: 'Public Sans', system-ui, sans-serif; }
.block-container { max-width: 1180px; padding-top: 1.8rem; }
h1.t { font-family:'Source Serif 4',Georgia,serif; font-weight:600; font-size:2.2rem; margin:0 0 .3rem; color:var(--ink); }
p.lede { color:var(--muted); margin:0 0 1rem; max-width:75ch; }
.step { font-weight:700; color:var(--teal); font-size:.95rem; margin:1.4rem 0 .2rem; }
.quote { border-left:4px solid var(--teal); background:#fff; padding:.6rem .9rem; border-radius:6px; margin:.4rem 0; border:1px solid var(--rule); border-left-width:4px; }
.quote .m { color:var(--muted); font-size:.82rem; margin-top:.25rem; }
.fee { background:var(--amber-soft); border:1px solid #E7CFA4; border-radius:8px; padding:.8rem 1rem; }
.gate { background:#FFF8EC; border:2px solid var(--amber); border-radius:10px; padding:1rem 1.1rem; }
.ok { background:var(--teal-soft); border:1px solid var(--teal); border-radius:10px; padding:.9rem 1.1rem; }
.stats { display:grid; grid-template-columns:repeat(4, 1fr); gap:.6rem; margin:.3rem 0 .4rem; }
.stat { background:#fff; border:1px solid var(--rule); border-radius:8px; padding:.6rem .8rem; }
.stat .v { font-size:1.6rem; font-weight:700; color:var(--ink); line-height:1.2; }
.stat .l { font-size:.82rem; color:var(--muted); }
.themes { display:flex; flex-direction:column; gap:.45rem; margin:.3rem 0 .5rem; }
.th { background:#fff; border:1px solid var(--rule); border-radius:8px; padding:.6rem .8rem;
      display:grid; grid-template-columns:2rem minmax(0,1fr) minmax(0,1.1fr); gap:.2rem .8rem; align-items:center; }
.th.top { border-left:4px solid var(--teal); }
.th .rk { font-weight:700; color:var(--teal); font-size:1.05rem; }
.th .nm { font-weight:600; color:var(--ink); }
.th .meta { grid-column:2 / -1; font-size:.82rem; color:var(--muted); }
.th .bar { display:flex; align-items:center; gap:.5rem; }
.th .bar span.track { flex:1; height:8px; background:#E9EEEC; border-radius:99px; overflow:hidden; }
.th .bar span.fill { display:block; height:100%; background:var(--teal); border-radius:99px; }
.th .bar b { font-size:.9rem; min-width:2.2rem; text-align:right; }
.up { color:var(--amber); font-weight:600; }
.feelist { display:flex; flex-direction:column; gap:.35rem; margin-bottom:.5rem; }
.feerow { display:flex; justify-content:space-between; gap:.8rem; background:#fff; border:1px solid var(--rule); border-radius:6px; padding:.45rem .7rem; font-size:.9rem; }
.feerow .n { white-space:nowrap; color:var(--muted); }
.payload { background:#fff; border:1px solid var(--rule); border-radius:8px; padding:.7rem .9rem; font-size:.92rem; }
.payload dt { font-size:.78rem; color:var(--muted); margin-top:.5rem; }
.payload dt:first-child { margin-top:0; }
.payload dd { margin:0; color:var(--ink); overflow-wrap:anywhere; }
.payload ul { margin:.1rem 0 0 1.1rem; padding:0; }
@media (max-width: 640px) {
  .block-container { padding-left:.9rem; padding-right:.9rem; padding-top:3.2rem; }
  h1.t { font-size:1.7rem; }
  .stats { grid-template-columns:repeat(2, 1fr); }
  .stat .v { font-size:1.3rem; }
  .th { grid-template-columns:1.6rem minmax(0,1fr); }
  .th .bar { grid-column:2 / -1; }
  [data-testid="stVerticalBlockBorderWrapper"] h3 { font-size:1.25rem; }
  [data-testid="stVerticalBlockBorderWrapper"] h4 { font-size:1.08rem; }
  div.stButton > button, div.stDownloadButton > button { width:100%; }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="t">Groww Review Pulse</h1>', unsafe_allow_html=True)
st.markdown('<p class="lede">Turns raw Play Store reviews into a weekly product pulse and a ready-to-use explanation '
            'of the fee users misunderstand most, then logs both to the team\'s tools through MCP, '
            'but only after a person approves.</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Data")
    up = st.file_uploader("Use your own reviews CSV (optional)", type="csv",
                          help="Columns: date, rating, text (thumbs_up optional). Leave empty to use the bundled 12-week Groww sample.")
    st.caption(f"Default: `data/reviews.csv`, public Google Play reviews of the Groww app.")
    st.markdown("### How actions run")
    st.caption("The MCP server (`mcp_server.py`) exposes `append_to_notes` and `create_email_draft`. "
               "It refuses any call without an approved, unused approval id whose payload hash matches.")


@st.cache_data(show_spinner="Analysing reviews…")
def _analyse(raw: bytes | None):
    if raw is None:
        return run_analysis()
    import io
    df = pd.read_csv(io.BytesIO(raw))
    tmp = config.DATA / "_uploaded.csv"
    df.to_csv(tmp, index=False)
    return run_analysis(load_reviews(tmp))


res = _analyse(up.getvalue() if up else None)
ins = res.insights

# ---------------------------------------------------------------------------
st.markdown('<div class="step">STEP 1: Review intelligence</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="stats">'
    f'<div class="stat"><div class="v">{ins.total_reviews:,}</div><div class="l">Reviews analysed</div></div>'
    f'<div class="stat"><div class="v">{ins.substantive_reviews:,}</div><div class="l">Detailed enough to theme</div></div>'
    '<div class="stat"><div class="v">12 weeks</div><div class="l">Review window</div></div>'
    f'<div class="stat"><div class="v">{ins.avg_rating} ★</div><div class="l">Average rating</div></div>'
    '</div>', unsafe_allow_html=True)
st.caption(f"Reviews from {pd.Timestamp(ins.window_start):%-d %b %Y} to {pd.Timestamp(ins.window_end):%-d %b %Y}. "
           f"'This week' = {pd.Timestamp(ins.week_start):%-d %b} to {pd.Timestamp(ins.window_end):%-d %b}.")

st.markdown("**Themes (max 5), ranked by critical (1–3★) reviews**")
top_keys = {t.key for t in ins.top_themes}
peak = max(t.critical for t in ins.themes) or 1
cards = []
for i, t in enumerate(ins.themes, 1):
    rising = t.share_last_week > t.share_all
    trend = (f'<span class="up">↑ {t.share_last_week * 100:.1f}% this week</span>' if rising
             else f'{t.share_last_week * 100:.1f}% this week')
    cards.append(
        f'<div class="th{" top" if t.key in top_keys else ""}"><div class="rk">{i}</div>'
        f'<div class="nm">{html.escape(t.label)}</div>'
        f'<div class="bar"><span class="track"><span class="fill" style="width:{t.critical / peak * 100:.0f}%"></span></span>'
        f'<b>{t.critical}</b></div>'
        f'<div class="meta">{t.reviews} reviews · avg {t.avg_rating}★ · {trend} (12-week avg {t.share_all * 100:.1f}%)</div></div>')
st.markdown('<div class="themes">' + "".join(cards) + "</div>", unsafe_allow_html=True)
st.caption(f"Bar = critical (1–3★) reviews. Top 3 are marked in teal. {ins.unassigned:,} detailed reviews matched "
           "no theme (mostly general praise or unrelated text).")
with st.expander("Table view"):
    table = pd.DataFrame([{
        "Rank": i + 1, "Theme": t.label, "Critical reviews": t.critical, "All reviews": t.reviews,
        "Avg ★": t.avg_rating, "Share (12 wk)": t.share_all * 100, "Share (this week)": t.share_last_week * 100,
    } for i, t in enumerate(ins.themes)])
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "Share (12 wk)": st.column_config.NumberColumn(format="%.1f%%"),
        "Share (this week)": st.column_config.NumberColumn(format="%.1f%%"),
    })
st.markdown("**3 real user quotes (one per top theme)**")
labels = {t.key: t.label for t in ins.themes}
for col, q in zip(st.columns(3), ins.quotes):
    with col:
        st.markdown(f'<div class="quote">"{html.escape(q.text)}"<div class="m">{q.rating}★ · {q.date} · '
                    f'{html.escape(labels[q.theme])}</div></div>', unsafe_allow_html=True)

st.markdown("**Recurring fee confusion detected**")
fee = ins.fee
st.markdown(f'<div class="fee"><b>{html.escape(fee.label)}</b><br>{fee.mentions} reviews mention it '
            f'({fee.confused_mentions} explicitly say charges were unclear, hidden or unexpected); average rating '
            f'{fee.avg_rating}★.</div>', unsafe_allow_html=True)
with st.expander("How the fee was chosen: mentions per fee type"):
    st.markdown('<div class="feelist">' + "".join(
        f'<div class="feerow"><span>{html.escape(r["label"])}</span>'
        f'<span class="n">{r["mentions"]} mentions · {r["confused_mentions"]} confused</span></div>'
        for r in fee.table) + "</div>", unsafe_allow_html=True)
    for q in fee.evidence:
        st.markdown(f'<div class="quote">"{html.escape(q.text)}"<div class="m">{q.rating}★ · {q.date}</div></div>',
                    unsafe_allow_html=True)

# ---------------------------------------------------------------------------
p_col, e_col = st.columns(2)
with p_col:
    st.markdown(f'<div class="step">STEP 2: Weekly product pulse ({word_count(res.pulse_md)} / 250 words)</div>',
                unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(demote(res.pulse_md, 3))
    st.download_button("Download pulse (.md)", res.pulse_md, file_name="weekly_pulse.md")
with e_col:
    st.markdown(f'<div class="step">STEP 3: Fee explainer ({len(res.explainer.bullets)} bullets, 2 official links)</div>',
                unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(demote(res.explainer.markdown(), 2))
    st.download_button("Download explainer (.md)", res.explainer.markdown(), file_name="fee_explainer.md")

# ---------------------------------------------------------------------------
st.markdown('<div class="step">STEP 4: Approve MCP actions</div>', unsafe_allow_html=True)

key = json.dumps([res.notes_entry, res.email], sort_keys=True, ensure_ascii=False)
if st.session_state.get("payload_key") != key:      # new analysis -> new approval needed
    st.session_state.payload_key = key
    st.session_state.approval_id = request_approval(res)
    st.session_state.outcome = None
aid = st.session_state.approval_id
rec = approval.status(aid) or {}

if rec.get("status") == "pending":
    st.markdown('<div class="gate"><b>Nothing has been written or drafted yet.</b> Review the two actions below. '
                'They run only after you approve, and the server rejects them if the content changes.</div>',
                unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Action 1: `append_to_notes`** (shared notes doc)")
        e = res.notes_entry
        st.markdown(
            '<dl class="payload">'
            f'<dt>date</dt><dd>{e["date"]}</dd>'
            '<dt>top_themes</dt><dd><ul>' + "".join(f"<li>{html.escape(t)}</li>" for t in e["top_themes"]) + '</ul></dd>'
            f'<dt>identified_fee_issue</dt><dd>{html.escape(e["identified_fee_issue"])}</dd>'
            f'<dt>weekly_pulse</dt><dd>The full pulse shown in Step 2 ({word_count(e["weekly_pulse"])} words)</dd>'
            f'<dt>explanation_bullets</dt><dd>The {len(e["explanation_bullets"])} bullets shown in Step 3</dd>'
            '<dt>source_links</dt><dd><ul>' + "".join(f'<li><a href="{u}" target="_blank">{html.escape(u)}</a></li>'
                                                     for u in e["source_links"]) + '</ul></dd></dl>',
            unsafe_allow_html=True)
        with st.expander("Raw JSON sent to the tool"):
            st.json(e, expanded=True)
    with a2:
        st.markdown("**Action 2: `create_email_draft`** (draft only, never sent)")
        st.markdown(f'<div class="payload"><dt>Subject</dt><dd>{html.escape(res.email["subject"])}</dd></div>',
                    unsafe_allow_html=True)
        st.text_area("Body", res.email["body"], height=220, disabled=True)
    name = st.text_input("Your name (recorded with the approval)", placeholder="e.g. Vasim, Product Ops")
    checked = st.checkbox("I have reviewed both actions and the figures against the linked sources.")
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("Approve and run", type="primary", disabled=not (checked and name.strip())):
        approval.approve(aid, name.strip())
        with st.spinner("Calling MCP tools…"):
            st.session_state.outcome = execute(res, aid)
        st.rerun()
    if b2.button("Reject"):
        approval.reject(aid, name.strip() or "anonymous")
        st.rerun()
elif rec.get("status") == "rejected":
    st.warning(f"Rejected by {rec.get('approver')}. No actions were run.")
    if st.button("Start a new approval request"):
        st.session_state.payload_key = None
        st.rerun()
else:
    out = st.session_state.get("outcome") or {}
    st.markdown(f'<div class="ok"><b>Approved by {html.escape(rec.get("approver", ""))}</b> at {rec.get("approved_at", "")}. '
                f'MCP tools called: {", ".join(out.get("tools_available", []))}.</div>', unsafe_allow_html=True)
    n = out.get("append_to_notes", {})
    d = out.get("create_email_draft", {})
    r1, r2 = st.columns(2)
    with r1:
        st.markdown(f"**Notes doc:** {n.get('status')} → `{n.get('doc')}`  \nNotion: {n.get('notion')}")
        doc = config.OUT / "notes" / "product_pulse_log.md"
        if doc.exists():
            text = doc.read_text(encoding="utf-8")
            with st.container(border=True, height=420):
                st.markdown(demote(text[text.rfind("\n---\n"):], 3))
            st.download_button("Download notes doc", text, file_name="product_pulse_log.md")
    with r2:
        st.markdown(f"**Email draft:** {d.get('status')} → `{d.get('file')}`  \nGmail: {d.get('gmail')} · Sent: **{d.get('sent')}**")
        if d.get("file"):
            eml = config.ROOT / d["file"]
            md = eml.with_suffix(".md")
            if md.exists():
                with st.container(border=True, height=420):
                    st.text(md.read_text(encoding="utf-8"))
                st.download_button("Download draft (.eml)", eml.read_bytes(), file_name=eml.name)
    if st.button("Prepare another run"):
        st.session_state.payload_key = None
        st.rerun()

st.caption("Learning project. Reviews are public Google Play reviews with personal details scrubbed. "
           "Fee figures come from Groww's official pricing and help pages; check them before sending to customers.")
