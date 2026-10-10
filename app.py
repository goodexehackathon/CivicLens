"""CivicLens Streamlit app. All data lives in st.session_state (per browser session, in memory)."""
import streamlit as st
from datetime import datetime
import config
from document_processor import load_pdf, load_text, chunk_document
from retrieval import Index
from answer_generator import generate
from conflict_detection import extract, compare
from checklist import build_checklist

st.set_page_config(page_title="CivicLens", page_icon="🔎", layout="wide")
st.markdown("""<style>
.block-container{max-width:1100px;padding-top:1.5rem}
.brand{font-size:2rem;font-weight:700;color:#1f3a5f}.tag{color:#51606f;margin-bottom:1rem}
.card{border:1px solid #d8dee6;border-radius:10px;padding:.9rem 1rem;margin:.5rem 0;background:#fafbfd}
.warn{border-left:4px solid #c77d00;background:#fff7e6;padding:.6rem .9rem;border-radius:6px;margin:.5rem 0}
</style>""", unsafe_allow_html=True)

S = st.session_state
S.setdefault("docs", {})   # doc_id -> Document
S.setdefault("uploaded", set())

def docs(): return list(S.docs.values())
def usable(): return [d for d in docs() if d.status in ("ok",) or (d.status == "needs_ocr" and any(p.text.strip() for p in d.pages))]
def index():
    return Index([c for d in usable() for c in chunk_document(d)])

def ingest(files):
    for f in files:
        data = f.getvalue()
        d = load_text(data.decode("utf-8", "replace"), f.name) if f.name.lower().endswith(".txt") else load_pdf(data, f.name)
        if d.doc_id in S.docs:
            st.info(f"{f.name}: duplicate of an already uploaded document, skipped."); continue
        d.uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        S.docs[d.doc_id] = d

st.markdown('<div class="brand">🔎 CivicLens</div><div class="tag">Scholarship rules, explained with evidence — not guesswork.</div>', unsafe_allow_html=True)
home, ask, lib, conf, chk, about = st.tabs(["Home", "Ask CivicLens", "Document Library", "Conflict Review", "Checklist", "About & Evaluation"])

with home:
    st.write("Upload official scholarship PDFs, ask a question in English or Hindi, and see the exact passage and page behind every answer. "
             "If the documents don't answer, CivicLens says so.")
    files = st.file_uploader("Upload PDFs (or .txt for synthetic test notices)", type=["pdf", "txt"], accept_multiple_files=True)
    if files and st.button("Process documents", type="primary"):
        with st.spinner("Extracting text…"):
            ingest(files)
    ds = docs()
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents processed", sum(d.status != "failed" for d in ds))
    c2.metric("Searchable pages", sum(1 for d in usable() for p in d.pages if p.text.strip()))
    c3.metric("Passages", len(index().chunks) if usable() else 0)
    st.markdown('<div class="warn"><b>Privacy & limits.</b> Documents are kept in memory for this browser session only and are lost on refresh. '
                'If an AI key is configured, only the retrieved passages and your question are sent to Google Gemini; otherwise nothing leaves this app. '
                'Do not upload personal data (Aadhaar, bank details). CivicLens never decides eligibility — confirm with your institute or the official portal.</div>', unsafe_allow_html=True)
    if st.button("Clear all my documents and data"):
        S.docs.clear(); st.rerun()

with ask:
    lang = st.selectbox("Answer language", ["English", "Hindi"])
    q = st.text_input("Your question", placeholder="What is the last date to correct a defective application?")
    mode = "AI-generated answer (verified)" if config.GEMINI_API_KEY else "Evidence-only (no AI key configured)"
    st.caption(f"Mode: {mode}")
    if st.button("Ask Question", type="primary") and q:
        if not usable():
            st.warning("Upload and process at least one document first.")
        else:
            with st.spinner("Searching documents…"):
                results = index().search(q)
                out = generate(q, results, S.docs, lang)
            if not results:
                st.error(config.ABSTAIN_MSG)
                st.write("The uploaded documents have no sufficiently relevant passage. You may need the scheme guidelines or the latest notice for your state/institute.")
            else:
                if out["mode"] == "generated":
                    st.subheader("Answer (AI-drafted; each claim checked against its cited page)")
                    for n, c in enumerate([c for c in out["claims"] if c["status"] == "verified"], 1):
                        st.markdown(f"- {c['text']} **[{c['evidence_id']}]**")
                    bad = [c for c in out["claims"] if c["status"] != "verified"]
                    if bad: st.markdown(f'<div class="warn">{len(bad)} claim(s) failed verification and are hidden.</div>', unsafe_allow_html=True)
                else:
                    if out["mode"] == "abstain":
                        st.error(out["note"])
                    else:
                        st.info(out["note"])
                ev = extract([S.docs[c.doc_id] for _, c in results if c.doc_id in S.docs])
                if len({s.iso for s in ev if s.event}) > 1:
                    st.markdown('<div class="warn">Different dates appear in the retrieved passages — see <b>Conflict Review</b>. Confirm with your institute.</div>', unsafe_allow_html=True)
                st.caption("Relevance score = uncalibrated text-similarity for ranking only; it is not a probability that the answer is correct. A verified quote proves the text exists on that page, not that it applies to you.")
                st.subheader("Evidence")
                for i, (s, c) in enumerate(results, 1):
                    d = S.docs[c.doc_id]
                    with st.expander(f"[{i}] {c.filename} — page {c.page} (relevance {s:.2f})", expanded=i == 1):
                        st.write(c.text)
                        st.caption(f"Notice date: {d.notice_date or 'not provided'} · Scheme: {d.scheme or 'not provided'}")
                        if st.checkbox("Show full source page", key=f"pg{i}{c.doc_id}{c.page}"):
                            st.text(d.pages[c.page - 1].text)
                            if d.raw:
                                try:
                                    import fitz
                                    pix = fitz.open(stream=d.raw, filetype="pdf")[c.page - 1].get_pixmap(dpi=100)
                                    st.image(pix.tobytes("png"))
                                except Exception as e:
                                    st.caption(f"Page preview unavailable ({type(e).__name__}); open the original PDF at page {c.page}.")

with lib:
    name = st.text_input("Search documents by name")
    for d in [d for d in docs() if name.lower() in d.filename.lower()]:
        with st.container(border=True):
            st.markdown(f"**{d.filename}** · id `{d.doc_id}` · status **{d.status}**")
            st.caption(f"Uploaded {getattr(d, 'uploaded_at', '?')} · {len(d.pages)} pages · {sum(len(p.text.strip()) >= 20 for p in d.pages)} with text")
            for e in d.errors: st.warning(e)
            a, b, c = st.columns(3)
            d.notice_date = a.text_input("Notice date (if known)", d.notice_date or "", key=f"nd{d.doc_id}") or None
            d.scheme = b.text_input("Scheme / cycle (if known)", d.scheme or "", key=f"sc{d.doc_id}") or None
            d.source_url = c.text_input("Source URL (if known)", d.source_url or "", key=f"su{d.doc_id}") or None
            r1, r2 = st.columns(2)
            if r1.button("Remove", key=f"rm{d.doc_id}"): S.docs.pop(d.doc_id); st.rerun()
            if r2.button("Reprocess", key=f"rp{d.doc_id}") and d.raw:
                new = load_pdf(d.raw, d.filename); new.notice_date, new.scheme, new.source_url = d.notice_date, d.scheme, d.source_url
                S.docs[d.doc_id] = new; st.rerun()
    if not docs(): st.info("No documents yet. Upload on the Home tab.")

with conf:
    st.write("Statements are compared only when they describe the same type of event (and the same cycle, if stated). "
             "CivicLens never decides which notice overrides another.")
    res = [r for r in compare(extract(usable())) if r["kind"] != "repeated"]
    label = {"explicit_revision": "A later passage explicitly revises/extends a date", "potential_conflict": "Potential conflict — needs human review"}
    for r in res:
        with st.container(border=True):
            st.markdown(f"**{r['event'].title()} deadline — {label[r['kind']]}**")
            x, y = st.columns(2)
            for col, s in ((x, r["a"]), (y, r["b"])):
                d = S.docs[s.doc_id]
                col.markdown(f"*{s.filename}, p.{s.page}* (notice date: {d.notice_date or 'not provided'}; cycle: {s.cycle or 'not stated'})")
                col.write(s.text); col.caption(f"Parsed date: {s.iso} (original: {s.raw})")
            st.warning(r["advice"])
            st.selectbox("Manual review status", ["Unreviewed", "Confirmed with institute", "Resolved"], key=f"mr{id(r)}{r['a'].doc_id}{r['b'].doc_id}{r['a'].page}{r['b'].page}{r['event']}")
    if not res: st.info("No conflicting or revised dates detected in the uploaded documents.")

with chk:
    order = {"conflicting": 0, "supported": 1, "confirm": 2, "missing": 3}
    names = {"supported": "Supported by uploaded documents", "confirm": "Requires your confirmation", "missing": "Not found in uploaded documents", "conflicting": "Conflicting information found"}
    for it in sorted(build_checklist(usable()) if usable() else [], key=lambda i: order[i["status"]]):
        src = f"{it['source'][0]}, p.{it['source'][1]}" if it["source"] else "—"
        st.markdown(f"**{names[it['status']]}** — {it['item']}  \n<small>Source: {src}</small>", unsafe_allow_html=True)
    if not usable(): st.info("Upload documents to generate a checklist.")

with about:
    st.markdown("""**Pipeline:** PyMuPDF extraction (page-bound) → optional Tesseract OCR → page-bound chunks → TF-IDF retrieval with relevance and query-coverage thresholds → optional Gemini answer (JSON, evidence-id based) → deterministic citation/date verification → conflict detection → checklist.
**Not implemented:** multilingual embedding retrieval, LLM-based entailment check, text highlighting in PDF pages.
**Limits:** Hindi support is lexical only; session data is in-memory; rule-based date parsing covers dd-mm-yyyy and "d Month yyyy".
Run `python evaluation.py` for the synthetic evaluation (a sanity check, not real-world accuracy).""")
