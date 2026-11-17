"""Owner: Kunal. Streamlit UI: ask questions, see the scorecard, the report and the audit trail.

Run from repo root (after the API is up): streamlit run frontend/ui.py
Falls back to calling the agent directly if the API is not running.
"""
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import agent, report, tools  # noqa: E402

API = "http://127.0.0.1:8000"
BADGE = {"Green": "🟢", "Amber": "🟡", "Red": "🔴", "Unknown": "⚪"}
TYPE_LABEL = {"scorecard": "numbers from the governed scorecard",
              "charter": "evidence from initiative charters",
              "mixed": "scorecard numbers + charter evidence",
              "not_found": "not in the data provided",
              "refused": "refused by policy"}
EXAMPLES = ["Why is PM-01 Red?", "Which initiatives are Red?",
            "What are the success metrics for BOT-02?", "What is the 2027 budget for CP-01?"]

st.set_page_config(page_title="Nimbus Value Intelligence", page_icon="📊", layout="wide")


def call_api(question):
    try:
        r = requests.post(f"{API}/ask", json={"question": question}, timeout=60)
        r.raise_for_status()
        return r.json(), "API"
    except Exception:
        return agent.ask(question), "direct"


st.title("📊 Nimbus AI — Value Intelligence Assistant")
st.caption(f"Code for numbers, retrieval for charter evidence, the LLM only for grounded explanation. "
           f"All figures as of {tools.AS_OF}.")

ask_tab, score_tab, report_tab, audit_tab = st.tabs(["Ask", "Scorecard", "Weekly report", "Audit trail"])

with ask_tab:
    if "question" not in st.session_state:
        st.session_state.question = EXAMPLES[0]
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        if col.button(ex, use_container_width=True):
            st.session_state.question = ex
    question = st.text_input("Ask about adoption, ROI, payback, status, risks or objectives",
                             key="question")
    if st.button("Ask", type="primary") or question:
        with st.spinner("Thinking..."):
            result, path = call_api(question)
        st.markdown(f"### {result['answer']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Answer type", result["answer_type"])
        c2.metric("Number check", "passed" if result["verifier"]["passed"] else "blocked")
        c3.metric("Latency", f"{result.get('latency_ms', 0):.0f} ms" if result.get("latency_ms") else "—")
        st.caption(f"{TYPE_LABEL.get(result['answer_type'], '')} · trace `{result['trace_id']}` · "
                   f"mode `{result['mode']}` · via {path}")
        if result["sources"]:
            st.markdown("**Sources**")
            for s in result["sources"]:
                st.markdown(f"- `{s}`")
        if not result["verifier"]["passed"]:
            st.error(f"Blocked unverified numbers: {result['verifier']['unsupported_numbers']}")
        with st.expander("Tools invoked"):
            st.json(result["tools_invoked"])

with score_tab:
    rows = tools.build_scorecard()
    counts = pd.Series([r["status"] for r in rows]).value_counts()
    cols = st.columns(3)
    for col, status in zip(cols, ("Green", "Amber", "Red")):
        col.metric(f"{BADGE[status]} {status}", int(counts.get(status, 0)))
    df = pd.DataFrame([{
        "ID": r["initiative_id"], "Name": r["name"], "Status": f"{BADGE[r['status']]} {r['status']}",
        "Adoption": r["adoption"], "WAU change": r["wau_change"], "ROI": r["roi"],
        "Payback (months)": r["payback_months"], "Run-rate vs plan": r["run_rate_vs_plan"],
        "Months live": r["months_live"], "Notes": "; ".join(r["notes"]),
    } for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"Adoption": st.column_config.NumberColumn(format="percent"),
                                "WAU change": st.column_config.NumberColumn(format="percent"),
                                "ROI": st.column_config.NumberColumn(format="percent"),
                                "Run-rate vs plan": st.column_config.NumberColumn(format="percent")})
    st.bar_chart(df.set_index("ID")[["Adoption", "ROI"]])
    st.caption(f"Source: {tools.SOURCE}")

with report_tab:
    if st.button("Generate weekly report"):
        path = report.weekly_report()
        st.success(f"Written to {path.relative_to(ROOT)}")
    path = ROOT / "outputs" / "weekly_report.md"
    if path.exists():
        st.markdown(path.read_text(encoding="utf-8"))
    changelog = ROOT / "outputs" / "changelog.md"
    if changelog.exists():
        with st.expander("Data change log"):
            st.markdown(changelog.read_text(encoding="utf-8"))

with audit_tab:
    log = ROOT / "logs" / "audit.jsonl"
    if not log.exists():
        st.info("No questions logged yet. Ask something with the API running.")
    else:
        entries = [pd.read_json(log, lines=True)]
        st.dataframe(entries[0][["ts", "trace_id", "question", "answer_type", "mode", "latency_ms"]]
                     .tail(25).iloc[::-1], use_container_width=True, hide_index=True)
        st.caption("Every answer is logged to logs/audit.jsonl with its trace id and latency.")
