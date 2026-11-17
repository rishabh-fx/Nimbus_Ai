"""Owner: Harsh + Kishlay. Charter retrieval with citations and an injection filter.

Pipeline: split each charter into sections -> drop sections containing injected instructions ->
score sections against the query -> keep those above THRESHOLD -> return top-k with file + section.

Default scoring is TF-IDF cosine similarity: deterministic, free, explainable, works offline.
Set RAG_MODE=embed in .env to use Gemini embeddings instead (falls back to TF-IDF on any error).
"""
import math
import os
import re
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CHARTERS = ROOT / "data" / "charters"
THRESHOLD = 0.08          # TF-IDF cosine below this = not relevant
EMBED_THRESHOLD = 0.55    # cosine threshold when RAG_MODE=embed
TOP_K = 3

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"note to (the )?ai",
    r"disregard (the )?(rules|instructions)",
    r"system prompt",
    r"you are now",
    r"report every initiative as",
]
STOPWORDS = set("""a an the is are was were be been of to in on for and or with by at as it its this that
what which who why how does do did has have had i we you our your me my from about tell show give please
initiative initiatives""".split())
# query expansion so plain-English questions reach the right charter section
EXPANSIONS = {
    "why": ["risks"], "red": ["risks"], "amber": ["risks"], "underperform": ["risks"],
    "problem": ["risks"], "issue": ["risks"], "concern": ["risks"], "risk": ["risks"],
    "low": ["risks"], "negative": ["risks"], "loss": ["risks"],
    "goal": ["objective"], "aim": ["objective"], "purpose": ["objective"],
    "target": ["success", "metrics"], "kpi": ["success", "metrics"], "measure": ["success", "metrics"],
    "owner": ["sponsor"], "responsible": ["sponsor"], "covers": ["scope"], "include": ["scope"],
}


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOPWORDS:
            continue
        if len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        out.append(w)
    return out


def is_injection(text):
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)


def load_chunks():
    """One chunk per '## Section'. The section heading is part of the searchable text."""
    chunks, blocked = [], []
    for f in sorted(CHARTERS.glob("*.md")):
        iid = f.stem.upper()
        title = ""
        for part in re.split(r"^## ", f.read_text(encoding="utf-8"), flags=re.M):
            part = part.strip()
            if part.startswith("# "):
                title = part[2:].strip()
                continue
            if not part:
                continue
            section, _, body = part.partition("\n")
            chunk = {"file": f"data/charters/{f.name}", "initiative_id": iid, "title": title,
                     "section": section.strip(), "text": body.strip()}
            if is_injection(body):
                # keep the clean sentences, drop the injected one
                clean = [s for s in re.split(r"(?<=[.!?])\s+", body.strip()) if not is_injection(s)]
                blocked.append({"file": chunk["file"], "section": chunk["section"]})
                chunk["text"] = " ".join(clean)
                chunk["sanitised"] = True
            if chunk["text"]:
                chunks.append(chunk)
    return chunks, blocked


def _tfidf_scores(query, chunks):
    docs = [tokens(f"{c['section']} {c['section']} {c['title']} {c['text']}") for c in chunks]
    q = tokens(query)
    q += tokens(" ".join(e for w in list(q) for e in EXPANSIONS.get(w, [])))
    n = len(docs)
    df = Counter(w for d in docs for w in set(d))
    idf = {w: math.log((n + 1) / (df[w] + 1)) + 1 for w in df}

    def vec(ws):
        tf = Counter(ws)
        return {w: tf[w] * idf.get(w, 0.0) for w in tf}

    qv = vec(q)
    qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    scores = []
    for d in docs:
        dv = vec(d)
        dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        scores.append(sum(qv[w] * dv.get(w, 0.0) for w in qv) / (qn * dn))
    return scores


def _embed_scores(query, chunks):
    from backend.agent import get_client  # lazy import, shares the same client
    model = os.getenv("EMBED_MODEL", "gemini-embedding-001")
    texts = [query] + [f"{c['section']}: {c['text']}" for c in chunks]
    data = get_client().embeddings.create(model=model, input=texts).data
    m = np.array([d.embedding for d in data], dtype=float)
    m = m / np.linalg.norm(m, axis=1, keepdims=True)
    return list(m[1:] @ m[0])


def search_charters(query, initiative=None, k=TOP_K):
    chunks, blocked = load_chunks()
    if initiative:
        chunks = [c for c in chunks
                  if c["initiative_id"] == initiative.strip().upper()
                  or c["title"].lower().endswith(initiative.strip().lower())]
    if not chunks:
        return {"found": False, "results": [], "blocked": blocked}
    threshold = THRESHOLD
    try:
        if os.getenv("RAG_MODE", "tfidf") == "embed":
            scores, threshold = _embed_scores(query, chunks), EMBED_THRESHOLD
        else:
            scores = _tfidf_scores(query, chunks)
    except Exception:
        scores = _tfidf_scores(query, chunks)
    ranked = sorted(zip(scores, chunks), key=lambda x: -x[0])
    top = ranked[0][0] if ranked else 0
    # keep sections above the absolute threshold AND at least half as relevant as the best one
    results = [{**c, "score": round(float(s), 3)} for s, c in ranked[:k]
               if s >= threshold and s >= 0.5 * top]
    return {"found": bool(results), "results": results, "blocked": blocked}


if __name__ == "__main__":
    import json
    print(json.dumps(search_charters("why is it red", "PM-01"), indent=2))
