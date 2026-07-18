"""
Text extraction for supported document types.

Each loader returns a list of (page_number, text) tuples so downstream
chunking can retain page-level provenance for citations. `page_number`
is None for formats without a native page concept (txt, md, csv).
"""
from pathlib import Path


class UnsupportedFileTypeError(Exception):
    pass


def load_pdf(path: str) -> list[tuple[int | None, str]]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def load_docx(path: str) -> list[tuple[int | None, str]]:
    import docx

    document = docx.Document(path)
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return [(None, text)]


def load_txt(path: str) -> list[tuple[int | None, str]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [(None, f.read())]


def load_markdown(path: str) -> list[tuple[int | None, str]]:
    # Kept as raw markdown text -- the markdown-aware chunker splits on headers.
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [(None, f.read())]


LOADERS = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".txt": load_txt,
    ".md": load_markdown,
}


def load_document(path: str) -> list[tuple[int | None, str]]:
    ext = Path(path).suffix.lower()
    loader = LOADERS.get(ext)
    if loader is None:
        raise UnsupportedFileTypeError(
            f"'{ext}' is not yet supported. Supported: {list(LOADERS.keys())} "
            "(CSV/PPTX/XLSX/OCR loaders are extension points -- see docs/ROADMAP.md)"
        )
    return loader(path)
