"""Owner: Harsh + Kishlay. Evaluation harness: scores retrieval and routing against evals/eval_set.json.

Metrics
  retrieval hit@1 / hit@3  did the expected (initiative, section) come back, and was it ranked first
  routing accuracy         did answer_type match the label (scorecard | charter | mixed | not_found | refused)
  fallback correctness     every not_found case answered with the exact fallback sentence
  refusal recall           every adversarial case refused
  groundedness             no answer contained a number the tools did not produce
  content checks           required words present, injected text absent

Run from repo root:
  python -m backend.evaluate              # full agent (uses the LLM if GEMINI_API_KEY is set)
  python -m backend.evaluate --retrieval  # retrieval only, no agent, no API calls
"""
import argparse
import json
import time
from pathlib import Path

from backend import agent, rag

ROOT = Path(__file__).resolve().parent.parent
EVAL_SET = ROOT / "evals" / "eval_set.json"
OUT = ROOT / "outputs"


def load_cases():
    return json.loads(EVAL_SET.read_text(encoding="utf-8"))["cases"]


def retrieval_scores(cases):
    """Score rag.search_charters on the cases that expect a charter section."""
    rows = []
    for c in cases:
        if not c["expect_sections"]:
            continue
        expected = {(i.upper(), s.lower()) for i, s in c["expect_sections"]}
        iid = next((i for i, _ in c["expect_sections"]), None)
        # the agent passes an initiative when the question names one; mimic that
        asked_id = iid if iid and iid.lower() in c["question"].lower() else None
        res = rag.search_charters(c["question"], asked_id)
        got = [(r["initiative_id"].upper(), r["section"].lower()) for r in res["results"]]
        rows.append({
            "id": c["id"], "question": c["question"],
            "expected": sorted(expected), "retrieved": got,
            "hit@1": bool(got) and got[0] in expected,
            "hit@3": any(g in expected for g in got[:3]),
        })
    return rows


def agent_scores(cases):
    rows = []
    for c in cases:
        start = time.perf_counter()
        r = agent.ask(c["question"])
        latency = (time.perf_counter() - start) * 1000
        answer = r["answer"].lower()
        missing = [w for w in c.get("must_contain", []) if w.lower() not in answer]
        leaked = [w for w in c.get("must_not_contain", []) if w.lower() in answer]
        sections = {(s.split("/")[-1].split(".")[0].upper(), s.split("§")[-1].strip().lower())
                    for s in r["sources"] if "§" in s}
        expected = {(i.upper(), s.lower()) for i, s in c["expect_sections"]}
        rows.append({
            "id": c["id"], "question": c["question"],
            "expect_type": c["expect_type"], "got_type": r["answer_type"],
            "type_ok": r["answer_type"] == c["expect_type"],
            "sections_ok": expected.issubset(sections) if expected else True,
            "content_ok": not missing and not leaked,
            "missing": missing, "leaked": leaked,
            "grounded": r["verifier"]["passed"],
            "fallback_ok": (r["answer"] == agent.FALLBACK) if c["expect_type"] == "not_found" else True,
            "answer": r["answer"], "mode": r["mode"], "latency_ms": round(latency, 1),
        })
    return rows


def pct(n, d):
    return "n/a" if not d else f"{100 * n / d:.0f}% ({n}/{d})"


def summarise(agent_rows, retr_rows):
    nf = [r for r in agent_rows if r["expect_type"] == "not_found"]
    ref = [r for r in agent_rows if r["expect_type"] == "refused"]
    charter = [r for r in agent_rows if r["expect_type"] in ("charter", "mixed")]
    return [
        ("Routing accuracy (answer_type)", pct(sum(r["type_ok"] for r in agent_rows), len(agent_rows))),
        ("Retrieval hit@1", pct(sum(r["hit@1"] for r in retr_rows), len(retr_rows))),
        ("Retrieval hit@3", pct(sum(r["hit@3"] for r in retr_rows), len(retr_rows))),
        ("Correct section cited", pct(sum(r["sections_ok"] for r in charter), len(charter))),
        ("Fallback used on unanswerable", pct(sum(r["fallback_ok"] for r in nf), len(nf))),
        ("Refusal recall (adversarial)", pct(sum(r["type_ok"] for r in ref), len(ref))),
        ("Groundedness (no invented numbers)", pct(sum(r["grounded"] for r in agent_rows), len(agent_rows))),
        ("Content checks", pct(sum(r["content_ok"] for r in agent_rows), len(agent_rows))),
    ]


def write_report(agent_rows, retr_rows, path=None):
    path = path or OUT / "eval_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = agent_rows[0]["mode"] if agent_rows else "n/a"
    avg = sum(r["latency_ms"] for r in agent_rows) / len(agent_rows) if agent_rows else 0
    lines = ["# Evaluation report", "",
             f"Cases: {len(agent_rows)} · mode: `{mode}` · average latency {avg:.0f} ms",
             f"Set: `evals/eval_set.json`", "",
             "## Summary", "", "| Metric | Score |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in summarise(agent_rows, retr_rows)]

    lines += ["", "## Routing and guardrails", "",
              "| ID | Question | Expected | Got | Section | Grounded | Content |",
              "|---|---|---|---|---|---|---|"]
    for r in agent_rows:
        tick = lambda b: "✅" if b else "❌"  # noqa: E731
        lines.append(f"| {r['id']} | {r['question']} | {r['expect_type']} | "
                     f"{r['got_type']} {tick(r['type_ok'])} | {tick(r['sections_ok'])} | "
                     f"{tick(r['grounded'])} | {tick(r['content_ok'])} |")

    lines += ["", "## Retrieval", "", "| ID | Expected section | Top 3 retrieved | hit@1 | hit@3 |",
              "|---|---|---|---|---|"]
    for r in retr_rows:
        exp = ", ".join(f"{i} § {s}" for i, s in r["expected"])
        got = ", ".join(f"{i} § {s}" for i, s in r["retrieved"]) or "none"
        lines.append(f"| {r['id']} | {exp} | {got} | {'✅' if r['hit@1'] else '❌'} | "
                     f"{'✅' if r['hit@3'] else '❌'} |")

    failures = [r for r in agent_rows
                if not (r["type_ok"] and r["sections_ok"] and r["content_ok"] and r["grounded"])]
    lines += ["", "## Failures", ""]
    if failures:
        for r in failures:
            detail = []
            if not r["type_ok"]:
                detail.append(f"expected {r['expect_type']}, got {r['got_type']}")
            if not r["sections_ok"]:
                detail.append("expected charter section not cited")
            if r["missing"]:
                detail.append(f"missing: {r['missing']}")
            if r["leaked"]:
                detail.append(f"leaked: {r['leaked']}")
            if not r["grounded"]:
                detail.append("unverified number blocked")
            lines.append(f"- **{r['id']}** ({r['question']}): {'; '.join(detail)}")
            lines.append(f"  - answer: {r['answer']}")
    else:
        lines.append("None.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--retrieval", action="store_true", help="score retrieval only, no agent calls")
    args = p.parse_args()
    cases = load_cases()
    retr = retrieval_scores(cases)
    if args.retrieval:
        for r in retr:
            print(f"{r['id']:>4}  hit@1 {'Y' if r['hit@1'] else 'N'}  hit@3 "
                  f"{'Y' if r['hit@3'] else 'N'}  {r['question']}")
        print(f"\nhit@1 {pct(sum(r['hit@1'] for r in retr), len(retr))}   "
              f"hit@3 {pct(sum(r['hit@3'] for r in retr), len(retr))}")
        return
    rows = agent_scores(cases)
    for k, v in summarise(rows, retr):
        print(f"{k:<38} {v}")
    print(f"\nReport: {write_report(rows, retr).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
