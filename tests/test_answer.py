import json, config
from tests.test_core import A, DOCS, IDX
import answer_generator as ag

R = IDX.search("last date to correct defective application")
Q = "Defective applications must be corrected on or before 23-12-2024"

def _idx_for_A():
    return next(i for i, (_, c) in enumerate(R, 1) if c.doc_id == A.doc_id)

def test_missing_key(monkeypatch=None):
    old, config.GEMINI_API_KEY = config.GEMINI_API_KEY, None
    try: out = ag.generate("q", R, DOCS)
    finally: config.GEMINI_API_KEY = old
    assert out["mode"] == "evidence_only" and "unavailable" in out["note"]

def test_no_evidence_abstains():
    assert ag.generate("q", [], DOCS)["mode"] == "abstain"

def test_valid_generation():
    reply = json.dumps({"claims": [{"text": "Corrections close 23-12-2024", "evidence_id": _idx_for_A(), "quote": Q, "dates": ["2024-12-23"]}]})
    assert ag.generate("q", R, DOCS, call=lambda p: reply)["mode"] == "generated"

def test_fabricated_quote_rejected():
    reply = json.dumps({"claims": [{"text": "x", "evidence_id": _idx_for_A(), "quote": "Deadline is 5 Feb 2030", "dates": []}]})
    assert ag.generate("q", R, DOCS, call=lambda p: reply)["mode"] == "abstain"

def test_invalid_evidence_id_rejected():
    reply = json.dumps({"claims": [{"text": "x", "evidence_id": 99, "quote": Q, "dates": []}]})
    assert ag.generate("q", R, DOCS, call=lambda p: reply)["mode"] == "abstain"

def test_malformed_twice_falls_back():
    calls = []
    out = ag.generate("q", R, DOCS, call=lambda p: calls.append(1) or "not json")
    assert out["mode"] == "evidence_only" and len(calls) == 2
