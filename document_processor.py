"""Ingestion: PDF/text -> pages -> page-bound chunks. Original text is preserved."""
import re, hashlib
from dataclasses import dataclass, field
from config import MAX_FILE_MB

@dataclass
class Page:
    number: int          # 1-based, original page number
    text: str

@dataclass
class Document:
    doc_id: str
    filename: str
    pages: list
    status: str = "ok"
    errors: list = field(default_factory=list)
    notice_date: str = None   # only if user supplies it
    source_url: str = None
    scheme: str = None
    raw: bytes = field(default=None, repr=False)

@dataclass
class Chunk:
    doc_id: str
    filename: str
    page: int
    text: str
    heading: str = None

def _id(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]

def norm_ws(t: str) -> str:
    return re.sub(r"[ \t]+", " ", t).strip()

def load_pdf(data: bytes, filename: str) -> Document:
    doc_id = _id(data)
    if not data.startswith(b"%PDF"):
        return Document(doc_id, filename, [], "failed", ["Not a valid PDF file"])
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        return Document(doc_id, filename, [], "failed", [f"Larger than {MAX_FILE_MB} MB"])
    try:
        import fitz
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        return Document(doc_id, filename, [], "failed", [f"Unreadable PDF: {e}"])
    pages, errors = [], []
    for i, p in enumerate(pdf):
        txt = p.get_text("text")
        if len(txt.strip()) < 20:
            txt, err = _ocr(p)
            if err: errors.append(f"Page {i+1}: {err}")
        pages.append(Page(i + 1, txt))
    doc = Document(doc_id, filename, pages, errors=errors, raw=data)
    return _finish(doc)

def _ocr(page):
    """Optional OCR (needs pytesseract + Tesseract binary). Returns (text, error_or_None)."""
    try:
        import pytesseract, io
        import os                                   
        exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  
        if os.path.exists(exe):                     
            pytesseract.pytesseract.tesseract_cmd = exe   
        from PIL import Image
        img = Image.open(io.BytesIO(page.get_pixmap(dpi=200).tobytes("png")))
        return pytesseract.image_to_string(img, lang="eng"), None
    except Exception as e:
        return "", f"OCR unavailable or failed ({type(e).__name__})"

def load_text(text: str, filename: str, page_break="\f") -> Document:
    """For synthetic fixtures: form feed separates pages."""
    pages = [Page(i + 1, t) for i, t in enumerate(text.split(page_break))]
    return _finish(Document(_id(text.encode()), filename, pages))

def _finish(doc: Document) -> Document:
    empty = [p.number for p in doc.pages if len(p.text.strip()) < 20]
    if not doc.pages:
        doc.status, doc.errors = "failed", ["No pages"]
    elif len(empty) == len(doc.pages):
        doc.status = "needs_ocr"
        doc.errors.append("No extractable text (scanned?). OCR not run or unavailable.")
    elif empty:
        doc.errors.append(f"Pages with little/no text: {empty}")
    return doc

def chunk_document(doc: Document, max_chars=700) -> list:
    """Chunks never cross page boundaries, so a citation page is always truthful."""
    out = []
    for p in doc.pages:
        heading, buf = None, ""
        for para in re.split(r"\n\s*\n", p.text):
            para = para.strip()
            if not para:
                continue
            first = para.split("\n")[0]
            if len(first) < 80 and (first.isupper() or re.match(r"^\d+[.)]\s", first)):
                heading = first
            if buf and len(buf) + len(para) > max_chars:
                out.append(Chunk(doc.doc_id, doc.filename, p.number, buf, heading)); buf = ""
            buf = (buf + "\n" + para).strip()
        if buf:
            out.append(Chunk(doc.doc_id, doc.filename, p.number, buf, heading))
    return out
