"""
ui.py
Reusable Streamlit UI component functions.

PDF viewer
----------
pdf_viewer(entry, page_num, zoom) renders a single page via PyMuPDF.
Navigation is handled here.
"""

from pathlib import Path

import streamlit as st

from config import ALLOWED_TAGS, ZOOM_LEVELS
from pdf_utils import (
    PDFEntry, render_page, get_page_count, get_pdf_metadata
)
import database as db


# ══════════════════════════════════════════════════════════════════════════════
# PDF VIEWER
# ══════════════════════════════════════════════════════════════════════════════

def pdf_viewer(entry: PDFEntry, page_num: int, zoom: float) -> None:
    """
    Render the current page of *entry* at *zoom* and display it.
    Only the (path, page_num, zoom) triple triggers a re-render;
    any other session-state change is ignored by the cache.
    """
    if not entry.path.exists():
        st.error(f"File not found: `{entry.path}`")
        return

    path_str   = str(entry.path.resolve())
    total_pages = get_page_count(path_str)

    # ── Page navigation bar ──────────────────────────────────────────────────
    page_bar(page_num, total_pages, zoom, entry.key)

    # ── Render single page ───────────────────────────────────────────────────
    with st.spinner(""):
        png = render_page(path_str, page_num - 1, zoom)   # page_num is 1-indexed

    st.image(png, use_container_width=False)

    # ── Reading progress ─────────────────────────────────────────────────────
    pct = page_num / total_pages * 100
    st.progress(
        page_num / total_pages,
        text=f"Page {page_num} / {total_pages}  —  {pct:.1f}% of document",
    )


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION BARS
# ══════════════════════════════════════════════════════════════════════════════

def pdf_nav_bar(current_idx: int, total: int) -> int:
    """
    Renders ⬅ PDF  /  counter  /  PDF ➡.
    Returns the new pdf index (or current if unchanged).
    """
    cp, cc, cn = st.columns([1, 2, 1])
    new_idx = current_idx
    with cp:
        if st.button("⬅ Prev PDF", key="_nav_prev_pdf",
                     disabled=(current_idx == 0),
                     use_container_width=True):
            new_idx = current_idx - 1
    with cc:
        st.markdown(
            f"<div style='text-align:center;font-size:1rem;"
            f"padding:6px 0;font-weight:600;color:#c8d0e8'>"
            f"PDF {current_idx + 1} / {total}</div>",
            unsafe_allow_html=True,
        )
    with cn:
        if st.button("Next PDF ➡", key="_nav_next_pdf",
                     disabled=(current_idx >= total - 1),
                     use_container_width=True):
            new_idx = current_idx + 1
    return new_idx


def page_bar(page_num: int, total_pages: int, zoom: float,
             pdf_key: str) -> None:
    """
    Full page-navigation + zoom bar rendered above the page image.
    Uses st.session_state.page_num as the sole source of truth to prevent rerun loops.
    """
    # ── Row 1: page navigation buttons ───────────────────────────────────────
    c_first, c_prev, c_info, c_next, c_last = st.columns([1, 1, 2, 1, 1])

    page_changed = False

    with c_first:
        if st.button("⏮", key="_pg_first", disabled=(page_num == 1),
                     help="First page", use_container_width=True):
            st.session_state.page_num = 1
            page_changed = True

    with c_prev:
        if st.button("◀", key="_pg_prev", disabled=(page_num == 1),
                     help="Previous page  [A]", use_container_width=True):
            st.session_state.page_num = page_num - 1
            page_changed = True

    with c_info:
        st.markdown(
            f"<div style='text-align:center;font-weight:600;"
            f"color:#c8d0e8;padding:6px 0;font-size:0.95rem'>"
            f"Page {page_num} / {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with c_next:
        if st.button("▶", key="_pg_next", disabled=(page_num >= total_pages),
                     help="Next page  [D]", use_container_width=True):
            st.session_state.page_num = page_num + 1
            page_changed = True

    with c_last:
        if st.button("⏭", key="_pg_last", disabled=(page_num >= total_pages),
                     help="Last page", use_container_width=True):
            st.session_state.page_num = total_pages
            page_changed = True

    # ── Row 2: Select Slider for precise jumping ─────────────────────────────
    def on_slider_change():
        # Triggered when user manually drags the slider
        db.save_page_pos(pdf_key, st.session_state.page_num)

    st.select_slider(
        "Page",
        options=list(range(1, total_pages + 1)),
        key="page_num", 
        label_visibility="collapsed",
        on_change=on_slider_change
    )

    # ── Execute state changes ────────────────────────────────────────────────
    if page_changed:
        db.save_page_pos(pdf_key, st.session_state.page_num)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SIDE-PANEL COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def pdf_info_panel(entry: PDFEntry) -> None:
    """File info + metadata block."""
    st.markdown("### 📄 Current PDF")
    st.markdown(f"**Subject:** `{entry.subject}`")
    st.markdown(f"**File:** `{entry.filename}`")
    st.markdown(f"**Month:** {entry.month_display}")
    st.markdown(f"**Date:** {entry.day}")
    st.markdown(f"**Topic:** {entry.topic}")
    st.divider()

    meta = get_pdf_metadata(str(entry.path.resolve()))
    if meta["pages"]:
        st.markdown(f"📑 **Pages:** {meta['pages']}")
    st.markdown(f"💾 **Size:** {meta['size_kb']} KB")
    st.markdown(f"🕒 **Modified:** {meta['modified']}")


def read_fav_controls(entry: PDFEntry) -> None:
    meta = db.get_meta(entry.key)
    col1, col2 = st.columns(2)
    with col1:
        new_read = st.checkbox("✅ Mark as Read", value=meta["is_read"],
                               key=f"read_{entry.key}")
        if new_read != meta["is_read"]:
            db.set_read(entry.key, new_read)
            st.rerun()
    with col2:
        star = "⭐ Starred" if meta["is_fav"] else "☆ Star"
        if st.button(star, key=f"fav_{entry.key}", use_container_width=True):
            db.set_fav(entry.key, not meta["is_fav"])
            st.rerun()


def tags_panel(entry: PDFEntry) -> None:
    meta     = db.get_meta(entry.key)
    selected = st.multiselect(
        "🏷 Tags",
        options=ALLOWED_TAGS,
        default=[t for t in meta["tags"] if t in ALLOWED_TAGS],
        key=f"tags_{entry.key}",
    )
    if selected != meta["tags"]:
        db.set_tags(entry.key, selected)


def comments_panel(entry: PDFEntry) -> None:
    existing = db.get_comment(entry.key)
    body = st.text_area(
        "📝 Notes",
        value=existing,
        height=180,
        placeholder="Add your study notes here…",
        key=f"comment_{entry.key}",
    )
    if body != existing:
        db.save_comment(entry.key, body)
        st.toast("Notes saved ✓", icon="💾")


def resume_banner(entry: PDFEntry, saved_page: int, total_pages: int) -> bool:
    """
    Show a 'Resume from page N?' banner when the saved page > 1.
    Returns True if the user clicked Resume (caller should apply the page).
    """
    if saved_page <= 1:
        return False
    col_msg, col_yes, col_no = st.columns([4, 1, 1])
    with col_msg:
        pct = saved_page / total_pages * 100
        st.info(
            f"📖 You left off at **page {saved_page} / {total_pages}** "
            f"({pct:.0f}%) — resume?",
            icon=None,
        )
    with col_yes:
        if st.button("Resume", key=f"resume_{entry.key}",
                     use_container_width=True):
            return True
    with col_no:
        if st.button("Start over", key=f"restart_{entry.key}",
                     use_container_width=True):
            db.save_page_pos(entry.key, 1)
            st.session_state._show_resume = False
            st.session_state._saved_page = 1
            st.rerun()
    return False


# ══════════════════════════════════════════════════════════════════════════════
# MISC HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def subject_progress(subject: str, entries: list[PDFEntry],
                     meta_all: dict) -> tuple[int, int]:
    total = len(entries)
    read  = sum(1 for e in entries
                if meta_all.get(e.key, {}).get("is_read", False))
    return read, total


def build_markdown_export(subjects: list[str],
                           pdfs_by_subject: dict[str, list[PDFEntry]],
                           comments: dict[str, str]) -> str:
    lines = ["# Semester Study Notes\n"]
    for subj in subjects:
        lines.append(f"\n## {subj}\n")
        for entry in pdfs_by_subject.get(subj, []):
            note = comments.get(entry.key, "").strip()
            if note:
                lines.append(f"### {entry.label}\n")
                lines.append(note + "\n")
    return "\n".join(lines)
