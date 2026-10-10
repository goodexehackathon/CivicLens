"""Cross-document date comparison. Does NOT assume newest wins; flags for human review."""
import re
from dataclasses import dataclass
from datetime import date

MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
NUM = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
WORD = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b", re.I)
CYCLE = re.compile(r"\b(20\d{2})\s*[-–]\s*(\d{2}|20\d{2})\b")
REVISE = re.compile(r"\b(extend\w*|revis\w*|one more opportunity|supersed\w*|in partial modification)\b", re.I)

@dataclass
class Dt:
    iso: str; raw: str

@dataclass
class Stmt:
    doc_id: str; filename: str; page: int; text: str; event: str; iso: str; raw: str; cycle: str; revises: bool

def find_dates(t):
    out = []
    for m in NUM.finditer(t):
        try: out.append(Dt(date(int(m[3]), int(m[2]), int(m[1])).isoformat(), m[0]))
        except ValueError: pass
    for m in WORD.finditer(t):
        out.append(Dt(date(int(m[3]), MONTHS[m[2].lower()], int(m[1])).isoformat(), m[0]))
    return out

def event_type(s):
    s = s.lower()
    if re.search(r"correct|defective|re-?submit", s): return "correction"
    if re.search(r"verif", s): return "verification"
    if re.search(r"last date|submi|apply|application", s): return "submission"
    return None

def extract(docs):
    out = []
    for d in docs:
        for p in d.pages:
            for sent in re.split(r"(?<=[.;])\s+|\n\n", p.text):
                ev, dts = event_type(sent), find_dates(sent)
                cyc = CYCLE.search(sent)
                for dt in dts:
                    if ev:
                        out.append(Stmt(d.doc_id, d.filename, p.number, sent.strip(), ev, dt.iso, dt.raw,
                                        cyc[0] if cyc else None, bool(REVISE.search(sent))))
    return out

def compare(stmts):
    """Only same-event statements from different documents are compared; cycle must not differ if both known."""
    res = []
    for i, a in enumerate(stmts):
        for b in stmts[i + 1:]:
            if a.doc_id == b.doc_id or a.event != b.event: continue
            if a.cycle and b.cycle and a.cycle != b.cycle: continue
            if a.iso == b.iso: kind = "repeated"
            else:
                later = b if b.iso > a.iso else a
                kind = "explicit_revision" if later.revises else "potential_conflict"
            res.append({"kind": kind, "event": a.event, "a": a, "b": b,
                        "advice": "" if kind == "repeated" else "Confirm with the issuing authority or your institute."})
    return res
