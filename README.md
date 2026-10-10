# CivicLens — Scholarship rules, explained with evidence
Team Good.exe · Commit for Good · Manipal University Jaipur (Round 2 prototype)

Upload scholarship PDFs, ask in English/Hindi, see the exact page behind each answer, review conflicting dates, get a source-linked checklist.
CivicLens never decides eligibility. Fictional fixtures in `tests/fixtures/` are **synthetic**, not official notices.

## Status (honest)
| Feature | Status |
|---|---|
| PDF extraction with page numbers, text/PDF upload, dedupe, remove/reprocess | Implemented; PDF path **not yet run** by the author's tooling (PyMuPDF unavailable there) — test on your laptop |
| OCR for scanned PDFs | Implemented, optional (needs Tesseract); untested |
| TF-IDF retrieval with relevance + coverage thresholds, Hindi tokens | Implemented, tested on synthetic data |
| Multilingual embedding retrieval | **Not implemented** |
| Gemini grounded answers + citation/date verification | Implemented; verification tested with fake model output; real Gemini call **untested** |
| LLM entailment check of claims | **Not implemented** (only deterministic date-in-quote check) |
| Conflict detection, checklist | Implemented (rule-based), tested on synthetic data |
| Streamlit UI | Written, compiles; **not yet launched** |
| In-PDF text highlighting | Not implemented (page preview only) |

## Windows (PowerShell, VS Code)
```powershell
python --version                     # 3.10-3.12 recommended
python -m venv .venv
.\.venv\Scripts\Activate.ps1         # if blocked: Set-ExecutionPolicy -Scope Process Bypass
python -m pip install -r requirements.txt
copy .env.example .env               # optional: add GEMINI_API_KEY
python -m streamlit run app.py
python -m pytest -q                  # run tests
python evaluation.py                 # synthetic evaluation
```
Env vars are read from the environment; to use `.env`, run `$env:GEMINI_API_KEY="..."` in PowerShell (or add `load_dotenv()` to `config.py`).
Troubleshooting: if `pip` installs to another Python, always use `python -m pip`. OCR needs the Tesseract installer (UB Mannheim build) plus the Hindi language data, and `tesseract` on PATH; without it, scanned PDFs are flagged "needs_ocr".

## Publish to GitHub (manual)
```powershell
git init; git add .; git commit -m "CivicLens prototype"
git branch -M main
git remote add origin https://github.com/<your-account>/<your-repo>.git
git push -u origin main
```
## Deploy (Streamlit Community Cloud) — **live URL pending**
Push to GitHub → share.streamlit.io → New app → select repo, `app.py` → Advanced settings → Secrets: `GEMINI_API_KEY = "..."`. Works without the secret. Note: free-tier apps are public; don't upload sensitive files. Remove `pytesseract` from requirements if the build fails (OCR then disabled).

## Real documents for the demo
Download current notices from official sources (e.g. scholarships.gov.in, your state education department sites, as cited in the Round 1 brief), and record each notice's date and URL in the Document Library tab. Confirm the dates yourself before presenting.

## Limitations
Session-only memory; lexical (not semantic) retrieval; Hindi quality limited; a verified quote shows the text exists on a page, not that it applies to a given student; synthetic test results do not show real-world reliability.
