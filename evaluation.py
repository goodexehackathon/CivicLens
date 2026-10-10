"""Small synthetic evaluation. Results are a sanity check on fixtures, NOT real-world accuracy."""
import pathlib, json
from document_processor import load_text, chunk_document
from retrieval import Index
from verification import validate_citation
from conflict_detection import extract, compare

F = pathlib.Path(__file__).parent / "tests" / "fixtures"
def L(n): return load_text((F / n).read_text(encoding="utf-8"), n)

ANSWERABLE = [  # (question, acceptable (filename,page) set)
    ("What is the last date to correct a defective application?", {("synthetic_notice_a.txt", 1), ("synthetic_notice_b.txt", 1)}),
    ("Has the correction deadline been extended?", {("synthetic_notice_b.txt", 1)}),
    ("When must institute verification be completed?", {("synthetic_notice_a.txt", 1)}),
    ("त्रुटिपूर्ण आवेदन में सुधार की अंतिम तिथि क्या है", {("hindi_notice.txt", 1)}),
]
UNANSWERABLE = ["What is the monthly stipend amount?", "Which bank issues the scholarship cheque?", "छात्रवृत्ति की राशि कितनी है"]
# (doc_a, doc_b, event) -> expected set of non-"repeated" kinds
CONFLICT_LABELS = {("synthetic_notice_a.txt", "synthetic_notice_b.txt", "correction"): "explicit_revision"}

def run(k=3):
    docs = [L(n) for n in ("synthetic_notice_a.txt", "synthetic_notice_b.txt", "unrelated_notice.txt", "hindi_notice.txt")]
    dmap = {d.doc_id: d for d in docs}
    idx = Index([c for d in docs for c in chunk_document(d)])
    hits = sum(any((c.filename, c.page) in exp for _, c in idx.search(q, k=k)) for q, exp in ANSWERABLE)
    abst = sum(idx.search(q) == [] for q in UNANSWERABLE)
    valid = tot = 0  # citation self-consistency: first sentence of each top hit must validate
    for q, _ in ANSWERABLE:
        for _, c in idx.search(q, k=k):
            tot += 1
            quote = c.text.split(".")[0]
            valid += validate_citation({"doc_id": c.doc_id, "page": c.page, "quote": quote}, dmap, {(c.doc_id, c.page)})[0]
    found = {(r["a"].filename, r["b"].filename, r["event"]): r["kind"] for r in compare(extract(docs)) if r["kind"] != "repeated"}
    tp = sum(found.get(key) == v for key, v in CONFLICT_LABELS.items())
    return {"retrieval_success@%d" % k: f"{hits}/{len(ANSWERABLE)}", "citation_validity (self-consistency)": f"{valid}/{tot}",
            "abstention_on_unanswerable": f"{abst}/{len(UNANSWERABLE)}",
            "conflict_precision": f"{tp}/{len(found)}", "conflict_recall": f"{tp}/{len(CONFLICT_LABELS)}",
            "claim_support_rate": "n/a (needs LLM run)", "note": "Tiny synthetic set; not evidence of real-world reliability."}

if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
