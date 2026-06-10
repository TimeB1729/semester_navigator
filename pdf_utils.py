"""
pdf_utils.py
File scanning, filename parsing, and PDF rendering.

Rendering contract
------------------
render_page(path_str, page_num, zoom) -> bytes  (PNG)

  Decorated with @st.cache_data so Streamlit only re-renders when the
  (path, page, zoom) triple changes.  Notes, tags, read-status, and
  favourites do NOT appear in the cache key and therefore never force
  a re-render.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz                  # PyMuPDF
import streamlit as st

from config import MONTH_ORDER, MONTH_DISPLAY, SEM_ROOT


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass(order=True)
class PDFEntry:
    """One PDF file with parsed metadata."""
    month_num:  int   = field(compare=True)
    day:        int   = field(compare=True)

    subject:    str   = field(compare=False)
    filename:   str   = field(compare=False)
    topic:      str   = field(compare=False)
    month_abbr: str   = field(compare=False)
    path:       Path  = field(compare=False)

    @property
    def key(self) -> str:
        return f"{self.subject}/{self.filename}"

    @property
    def month_display(self) -> str:
        return MONTH_DISPLAY.get(self.month_abbr.lower(), self.month_abbr)

    @property
    def label(self) -> str:
        return f"{self.month_display} {self.day} – {self.topic}"


# ─── Filename parser ──────────────────────────────────────────────────────────

_PATTERN = re.compile(
    r"^(?P<month>[A-Za-z]{3})_(?P<day>\d{1,2})_(?P<topic>.+)\.pdf$",
    re.IGNORECASE,
)


def parse_filename(filename: str) -> Optional[tuple[int, int, str, str]]:
    """Return (month_num, day, topic, month_abbr) or None."""
    m = _PATTERN.match(filename)
    if not m:
        return None
    abbr = m.group("month").lower()
    num  = MONTH_ORDER.get(abbr)
    if num is None:
        return None
    return num, int(m.group("day")), m.group("topic").replace("_", " "), abbr


# ─── Folder / file scanning ───────────────────────────────────────────────────

def get_subjects(root: Path = SEM_ROOT) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def get_pdfs_for_subject(subject: str, root: Path = SEM_ROOT) -> list[PDFEntry]:
    folder  = root / subject
    entries: list[PDFEntry] = []
    for p in folder.glob("*.pdf"):
        parsed = parse_filename(p.name)
        if parsed is None:
            continue
        month_num, day, topic, abbr = parsed
        entries.append(PDFEntry(
            month_num  = month_num,
            day        = day,
            subject    = subject,
            filename   = p.name,
            topic      = topic,
            month_abbr = abbr,
            path       = p,
        ))
    return sorted(entries)


def all_pdfs(root: Path = SEM_ROOT) -> list[PDFEntry]:
    result: list[PDFEntry] = []
    for s in get_subjects(root):
        result.extend(get_pdfs_for_subject(s, root))
    return result


# ─── Cached page renderer ─────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def render_page(path_str: str, page_num: int, zoom: float = 1.5) -> bytes:
    """
    Render a single PDF page to PNG bytes.

    Parameters
    ----------
    path_str : str
        Absolute path to the PDF (string so it's hashable by st.cache_data).
    page_num : int
        0-indexed page number.
    zoom : float
        Rendering scale factor.  2.0 ≈ 144 dpi (crisp on retina screens).

    Returns
    -------
    bytes
        PNG image data.
    """
    doc = fitz.open(path_str)
    try:
        page = doc[page_num]
        mat  = fitz.Matrix(zoom, zoom)
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


@st.cache_data(show_spinner=False)
def get_page_count(path_str: str) -> int:
    """Return total pages in the PDF (cached)."""
    doc = fitz.open(path_str)
    n   = doc.page_count
    doc.close()
    return n


# ─── File metadata ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def get_pdf_metadata(path_str: str) -> dict:
    """
    Return pages, size_kb, and last-modified timestamp.
    Uses PyMuPDF for page count; pathlib for file stats.
    """
    p    = Path(path_str)
    stat = p.stat()
    pages = get_page_count(path_str)
    from datetime import datetime
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y, %H:%M")
    return {
        "pages":    pages,
        "size_kb":  round(stat.st_size / 1024, 1),
        "modified": modified,
    }
