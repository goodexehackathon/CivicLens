"""Checklist built only from document text. Absence from uploads is never treated as 'missing from the student's application'."""
import re
from conflict_detection import extract, compare

REQ = re.compile(r"\b(required|must|shall|should|mandatory)\b", re.I)
DOCW = re.compile(r"\b(documents?|certificates?|marksheets?|photograph|proof|passbook|declaration|receipt)\b", re.I)

def build_checklist(docs):
    items, seen = [], set()
    for d in docs:
        for p in d.pages:
            for s in re.split(r"(?<=[.;])\s+|\n\n", p.text):
                s = s.strip()
                if REQ.search(s) and DOCW.search(s) and s not in seen:
                    seen.add(s)
                    items.append({"status": "supported", "item": s, "source": (d.filename, p.number)})
    stmts = extract(docs)
    flagged = {r["event"] for r in compare(stmts) if r["kind"] in ("potential_conflict", "explicit_revision")}
    for st in stmts:
        status = "conflicting" if st.event in flagged else "supported"
        items.append({"status": status, "item": f"{st.event.title()} date mentioned: {st.raw}", "source": (st.filename, st.page)})
    if not any(i["item"] and DOCW.search(i["item"]) for i in items):
        items.append({"status": "missing", "item": "No required-document list found in the uploaded documents (this does not mean none is required).", "source": None})
    for t in ("Whether your own application is marked defective (check the official portal)",
              "Which notice applies to your institute and category (confirm with your institute)"):
        items.append({"status": "confirm", "item": t, "source": None})
    return items
