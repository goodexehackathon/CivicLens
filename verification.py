"""Deterministic verification. A passing citation check proves the quote EXISTS on the page,
not that it supports the claim -- support is checked separately for dates."""
import re
from config import ABSTAIN_MSG
from conflict_detection import find_dates

def _n(t): return re.sub(r"\s+", " ", t).strip().lower()

def validate_citation(cit, docs, supplied):
    """cit: {doc_id, page, quote}. docs: {doc_id: Document}. supplied: set of (doc_id, page) given to generator."""
    d = docs.get(cit.get("doc_id"))
    if d is None: return False, "unknown document"
    page = next((p for p in d.pages if p.number == cit.get("page")), None)
    if page is None: return False, "invalid page"
    if (d.doc_id, page.number) not in supplied: return False, "not in supplied evidence"
    if not cit.get("quote") or _n(cit["quote"]) not in _n(page.text): return False, "quote not on cited page"
    return True, "ok"

def check_date_claim(claim_dates, quote):
    """Deterministic support check: every date in the claim must appear in the cited quote."""
    have = {d.iso for d in find_dates(quote)}
    return bool(claim_dates) and all(d in have for d in claim_dates)

def verify_answer(raw, docs, supplied):
    """raw: model output dict {claims:[{text, dates:[iso], citation:{...}}]}. Malformed -> abstain/evidence-only."""
    try:
        claims = raw["claims"]
        assert isinstance(claims, list)
    except Exception:
        return {"mode": "evidence_only", "claims": [], "note": "Model output failed validation."}
    out = []
    for c in claims:
        ok, why = validate_citation(c.get("citation") or {}, docs, supplied)
        sup = ok and (check_date_claim(c["dates"], c["citation"]["quote"]) if c.get("dates") else None)
        status = "verified" if ok and sup in (True, None) else "unverified"
        out.append({**c, "status": status, "reason": why if not ok else ("date mismatch" if sup is False else "ok")})
    shown = [c for c in out if c["status"] == "verified"]
    if not shown:
        return {"mode": "abstain", "claims": out, "note": ABSTAIN_MSG}
    return {"mode": "generated", "claims": out, "note": None}
