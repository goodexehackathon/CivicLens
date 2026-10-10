Ingest (document_processor) → chunks (page-bound) → Index (retrieval) → generate (answer_generator, optional Gemini) → verify (verification) → UI (app.py)
Parallel: conflict_detection (dates by event type) → Conflict tab; checklist from document sentences + conflicts.
Data stays in st.session_state; only retrieved passages + question go to Gemini when a key is set.
