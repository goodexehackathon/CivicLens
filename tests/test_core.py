import pathlib, pytest
from document_processor import load_text, load_pdf, chunk_document
from retrieval import Index
from verification import validate_citation, verify_answer
from conflict_detection import extract, compare, find_dates
from config import ABSTAIN_MSG

F = pathlib.Path(__file__).parent / "fixtures"
def load(n): return load_text((F / n).read_text(), n)
A, B, U = load("synthetic_notice_a.txt"), load("synthetic_notice_b.txt"), load("unrelated_notice.txt")
DOCS = {d.doc_id: d for d in (A, B, U)}
IDX = Index([c for d in (A, B, U) for c in chunk_document(d)])

def test_page_metadata_preserved():
    d = load_text("Page one text here is long enough.\fPage two text here is long enough.", "x")
    cs = chunk_document(d)
    assert [c.page for c in cs] == [1, 2] and all(c.filename == "x" for c in cs)

def test_bad_pdf_handled():
    assert load_pdf(b"not a pdf", "bad.pdf").status == "failed"

def test_retrieval_relevant():
    r = IDX.search("last date to correct defective application")
    assert r and r[0][1].doc_id in (A.doc_id, B.doc_id)

def test_irrelevant_rejected_english_and_hindi():
    assert IDX.search("What is the scholarship amount for PhD students abroad?") == [] or \
           all(c.doc_id != U.doc_id for _, c in IDX.search("scholarship amount"))
    assert IDX.search("छात्रवृत्ति की राशि कितनी है") == []

def good_cit(): return {"doc_id": A.doc_id, "page": 1, "quote": "Defective applications must be corrected on or before 23-12-2024"}
SUP = {(A.doc_id, 1), (B.doc_id, 1)}

def test_citation_valid():
    assert validate_citation(good_cit(), DOCS, SUP)[0]

@pytest.mark.parametrize("patch", [{"doc_id": "nope"}, {"page": 9}, {"quote": "Deadline is 1 Jan 2030"}])
def test_citation_rejected(patch):
    assert not validate_citation({**good_cit(), **patch}, DOCS, SUP)[0]

def test_citation_not_in_supplied_evidence():
    assert not validate_citation(good_cit(), DOCS, {(B.doc_id, 1)})[0]

def test_date_claim_checked():
    ok = verify_answer({"claims": [{"text": "x", "dates": ["2024-12-23"], "citation": good_cit()}]}, DOCS, SUP)
    bad = verify_answer({"claims": [{"text": "x", "dates": ["2025-01-27"], "citation": good_cit()}]}, DOCS, SUP)
    assert ok["mode"] == "generated" and bad["mode"] == "abstain" and bad["note"] == ABSTAIN_MSG

def test_malformed_model_output():
    assert verify_answer("garbage", DOCS, SUP)["mode"] == "evidence_only"
    assert verify_answer({"claims": "x"}, DOCS, SUP)["mode"] == "evidence_only"

def test_explicit_extension_detected():
    res = [r for r in compare(extract([A, B])) if r["event"] == "correction"]
    assert any(r["kind"] == "explicit_revision" for r in res)

def test_different_events_not_compared():
    kinds = {(r["a"].event, r["b"].event) for r in compare(extract([A, B]))}
    assert all(a == b for a, b in kinds)

def test_unrevised_difference_flagged_not_resolved():
    X = load_text("Scheme Alpha 2024-25. Defective applications must be corrected by 01-02-2025.", "x")
    r = compare(extract([A, X]))
    assert any(i["kind"] == "potential_conflict" for i in r)

def test_date_parsing():
    assert {d.iso for d in find_dates("by 5 March 2025 or 27-01-2025")} == {"2025-03-05", "2025-01-27"}

def test_hindi_retrieval():
    H = load("hindi_notice.txt")
    idx = Index([c for d in (A, U, H) for c in chunk_document(d)])
    r = idx.search("सुधार की अंतिम तिथि क्या है")
    assert r and r[0][1].doc_id == H.doc_id
