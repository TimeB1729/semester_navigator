"""
app.py
Semester PDF Navigator – main entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st
from pathlib import Path

import database as db
from config import (
    APP_TITLE, APP_ICON, SEM_ROOT, RECENT_LIMIT,
    ZOOM_LEVELS, DEFAULT_ZOOM,
)
from pdf_utils import (
    get_subjects, get_pdfs_for_subject, all_pdfs,
    get_page_count, PDFEntry,
)
from ui import (
    pdf_viewer, pdf_nav_bar, pdf_info_panel,
    read_fav_controls, tags_panel, comments_panel,
    subject_progress, resume_banner,
    build_markdown_export,
)


# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Bootstrap ───────────────────────────────────────────────────────────────

db.init_db()

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#0f1117; color:#e8eaf0; }
[data-testid="stSidebar"]          { background:#161b27 !important;
                                      border-right:1px solid #252d3e; }

/* Cards */
.card {
    background:#1a2035; border:1px solid #252d3e;
    border-radius:10px; padding:16px 20px; margin-bottom:12px;
}
.card-title { font-size:.78rem; text-transform:uppercase;
               letter-spacing:.08em; color:#7c8db5; margin-bottom:4px; }
.card-sub   { font-size:.82rem; color:#7c8db5; margin-top:2px; }

/* Metric tiles */
[data-testid="metric-container"] {
    background:#1a2035; border:1px solid #252d3e;
    border-radius:10px; padding:12px 16px;
}
[data-testid="metric-container"] label {
    color:#7c8db5 !important; font-size:.78rem !important;
    text-transform:uppercase; letter-spacing:.07em;
}

/* Page image – slight shadow for "paper" feel */
[data-testid="stImage"] img {
    border-radius:4px;
    box-shadow: 0 4px 24px rgba(0,0,0,.55);
    background: #fff;
}
</style>
""", unsafe_allow_html=True)


# ─── Session-state init ───────────────────────────────────────────────────────

_DEFAULTS: dict = {
    "active_subject": None,
    "pdf_index":      0,
    "page_num":       1,
    "zoom":           DEFAULT_ZOOM,
    "view":           "reader",
    "search_query":   "",
    "filter_mode":    "All PDFs",
    # internal: tracks which pdf_key is currently loaded so we can
    # detect PDF changes and reset page / show resume banner
    "_loaded_key":    "",
    "_show_resume":   False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─── Helpers ─────────────────────────────────────────────────────────────────

def set_pdf(subject: str, idx: int) -> None:
    st.session_state.active_subject = subject
    st.session_state.pdf_index      = idx
    st.session_state.view           = "reader"
    # page / resume reset handled in the reader section on key change


def jump_to_key(key: str) -> None:
    parts = key.split("/", 1)
    if len(parts) != 2:
        return
    subj, fname = parts
    entries = get_pdfs_for_subject(subj)
    for i, e in enumerate(entries):
        if e.filename == fname:
            set_pdf(subj, i)
            return


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"## {APP_ICON} {APP_TITLE}")
    st.divider()

    view_choice = st.radio(
        "View",
        ["📖 Reader", "📊 Dashboard", "🔍 Search"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if   "Reader"    in view_choice: st.session_state.view = "reader"
    elif "Dashboard" in view_choice: st.session_state.view = "dashboard"
    else:                            st.session_state.view = "search"

    st.divider()

    st.session_state.filter_mode = st.selectbox(
        "Filter",
        ["All PDFs", "Unread", "Read", "Favorites"],
        index=["All PDFs", "Unread", "Read", "Favorites"].index(
            st.session_state.filter_mode
        ),
    )
    st.divider()

    subjects = get_subjects()
    if not subjects:
        st.warning(f"No subject folders found in `{SEM_ROOT}`.")
    else:
        st.markdown("**Subjects**")
        meta_all = db.all_meta()
        for subj in subjects:
            entries  = get_pdfs_for_subject(subj)
            read, total = subject_progress(subj, entries, meta_all)
            label    = f"{subj}  `{read}/{total}`"
            active   = st.session_state.active_subject == subj
            if st.button(label, key=f"subj_{subj}",
                         use_container_width=True,
                         type="primary" if active else "secondary"):
                set_pdf(subj, 0)
                st.rerun()

    st.divider()

    recent = db.get_recent(10)
    if recent:
        with st.expander("🕒 Recently Opened", expanded=False):
            for key in recent:
                parts   = key.split("/", 1)
                display = parts[1] if len(parts) == 2 else key
                if st.button(display, key=f"rec_{key}",
                             use_container_width=True):
                    jump_to_key(key)
                    st.rerun()

    # Keyboard shortcut legend
    with st.expander("⌨ Keyboard Shortcuts", expanded=False):
        st.markdown("""
| Key | Action |
|-----|--------|
| `A` `K` `PageUp` | Previous Page |
| `D` `J` `PageDown` | Next Page |
| `Home` | First Page |
| `End` | Last Page |
| `←` `H` | Previous PDF |
| `→` `L` | Next PDF |
| `+` | Zoom In |
| `-` | Zoom Out |
| `R` | Toggle Read |
| `F` | Toggle Favourite |
| `N` | Focus Notes |
        """)


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.view == "dashboard":
    st.markdown("## 📊 Dashboard")
    st.divider()

    subjects    = get_subjects()
    meta_all    = db.all_meta()
    all_entries = all_pdfs()

    total_pdfs = len(all_entries)
    total_read = sum(1 for e in all_entries
                     if meta_all.get(e.key, {}).get("is_read"))
    total_fav  = sum(1 for e in all_entries
                     if meta_all.get(e.key, {}).get("is_fav"))
    pct        = round(total_read / total_pdfs * 100, 1) if total_pdfs else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📚 Subjects",   len(subjects))
    c2.metric("📄 Total PDFs", total_pdfs)
    c3.metric("✅ Read",        total_read)
    c4.metric("⭐ Favourites", total_fav)
    c5.metric("📈 Complete",   f"{pct}%")
    st.progress(total_read / total_pdfs if total_pdfs else 0)
    st.divider()

    st.markdown("### Per-Subject Progress")
    import pandas as pd
    rows = []
    for subj in subjects:
        entries = get_pdfs_for_subject(subj)
        read, total = subject_progress(subj, entries, meta_all)
        rows.append({"Subject": subj, "Read": read,
                     "Total": total, "Remaining": total - read})
    df = pd.DataFrame(rows)
    if not df.empty:
        st.dataframe(
            df.style
              .bar(subset=["Read"],      color="#3d7ebf")
              .bar(subset=["Remaining"], color="#3a2035")
              .format({"Read": "{}", "Total": "{}", "Remaining": "{}"}),
            use_container_width=True, hide_index=True,
        )
        st.bar_chart(df.set_index("Subject")[["Read", "Remaining"]])

    st.divider()
    st.markdown("### 📤 Export Notes")
    comments  = db.all_comments()
    pdfs_by_s = {s: get_pdfs_for_subject(s) for s in subjects}
    md_export = build_markdown_export(subjects, pdfs_by_s, comments)
    st.download_button(
        "⬇ Download Notes as Markdown",
        data=md_export,
        file_name="semester_notes.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: SEARCH
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.view == "search":
    st.markdown("## 🔍 Global Search")
    query = st.text_input(
        "Search across filenames, topics, and notes…",
        value=st.session_state.search_query,
        placeholder="e.g. Bayes, EM Algorithm, revision…",
    )
    st.session_state.search_query = query

    if query.strip():
        q           = query.strip().lower()
        all_entries = all_pdfs()
        comments    = db.all_comments()
        meta_all    = db.all_meta()

        results = [
            e for e in all_entries
            if any(q in f for f in [
                e.filename.lower(), e.topic.lower(), e.subject.lower(),
                comments.get(e.key, "").lower(),
                " ".join(meta_all.get(e.key, {}).get("tags", [])).lower(),
            ])
        ]

        st.markdown(f"**{len(results)} result(s)** for `{query}`")
        for e in results:
            col_info, col_jump = st.columns([5, 1])
            with col_info:
                tags_str  = ", ".join(meta_all.get(e.key, {}).get("tags", []))
                note_snip = comments.get(e.key, "")[:80]
                st.markdown(
                    f"<div class='card'>"
                    f"<span class='card-title'>{e.subject}</span>"
                    f"<div style='font-weight:600;color:#c8d0e8;margin:4px 0'>"
                    f"{e.label}</div>"
                    + (f"<div class='card-sub'>🏷 {tags_str}</div>" if tags_str else "")
                    + (f"<div class='card-sub'>📝 {note_snip}…</div>" if note_snip else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with col_jump:
                if st.button("Open", key=f"srch_{e.key}",
                             use_container_width=True):
                    jump_to_key(e.key)
                    st.rerun()
        if not results:
            st.info("No matches found.")
    else:
        st.info("Type a search term above.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW: READER
# ══════════════════════════════════════════════════════════════════════════════

subjects = get_subjects()
if not subjects:
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.warning(
        f"No subject folders found under `{SEM_ROOT.resolve()}`.\n\n"
        "1. Create `Sem 5/` beside `app.py`.\n"
        "2. Add subject sub-folders (e.g. `LSM_25/`).\n"
        "3. Add PDFs named `Jan_12_Topic.pdf`.\n"
        "4. Reload."
    )
    st.stop()

if st.session_state.active_subject is None or \
   st.session_state.active_subject not in subjects:
    st.session_state.active_subject = subjects[0]
    st.session_state.pdf_index      = 0

active_subject = st.session_state.active_subject
all_entries    = get_pdfs_for_subject(active_subject)

# Apply filter
meta_all    = db.all_meta()
filter_mode = st.session_state.filter_mode
if   filter_mode == "Read":
    filtered = [e for e in all_entries if  meta_all.get(e.key, {}).get("is_read")]
elif filter_mode == "Unread":
    filtered = [e for e in all_entries if not meta_all.get(e.key, {}).get("is_read")]
elif filter_mode == "Favorites":
    filtered = [e for e in all_entries if  meta_all.get(e.key, {}).get("is_fav")]
else:
    filtered = all_entries

if not filtered:
    st.info(f"No PDFs match the **{filter_mode}** filter for **{active_subject}**.")
    st.stop()

idx   = min(st.session_state.pdf_index, len(filtered) - 1)
st.session_state.pdf_index = idx
entry: PDFEntry = filtered[idx]

# ── Detect PDF change → reset page, offer resume ──────────────────────────────
if st.session_state._loaded_key != entry.key:
    # Clear existing widget state to prevent out-of-bounds carryover
    if "page_num" in st.session_state:
        del st.session_state["page_num"]
        
    saved_page = db.get_page_pos(entry.key)
    st.session_state.page_num    = 1
    st.session_state._loaded_key = entry.key
    st.session_state._show_resume = (saved_page > 1)
    st.session_state._saved_page  = saved_page

# ── Log to recent activity ────────────────────────────────────────────────────
db.log_recent(entry.key, RECENT_LIMIT)

# ── Page header ──────────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='margin-bottom:2px'>{active_subject} — {entry.topic}</h2>"
    f"<div style='color:#7c8db5;font-size:.9rem'>"
    f"{entry.month_display} {entry.day}  •  "
    f"<code>{entry.filename}</code></div>",
    unsafe_allow_html=True,
)
st.divider()

# ── PDF-level navigation ───────────────────────────────────────────────────────
new_pdf_idx = pdf_nav_bar(idx, len(filtered))
if new_pdf_idx != idx:
    st.session_state.pdf_index = new_pdf_idx
    st.rerun()

st.divider()

# ── Resume banner ─────────────────────────────────────────────────────────────
if st.session_state.get("_show_resume", False):
    path_str    = str(entry.path.resolve())
    total_pages = get_page_count(path_str)
    if resume_banner(entry, st.session_state._saved_page, total_pages):
        st.session_state.page_num   = st.session_state._saved_page
        st.session_state._show_resume = False
        st.rerun()

# ── Main layout: viewer + side panel ──────────────────────────────────────────
viewer_col, panel_col = st.columns([3, 1])

with viewer_col:
    path_str    = str(entry.path.resolve())
    total_pages = get_page_count(path_str)

    # Clamp page_num in case the PDF changed
    page_num = max(1, min(st.session_state.page_num, total_pages))
    if page_num != st.session_state.page_num:
        st.session_state.page_num = page_num

    pdf_viewer(entry, page_num, st.session_state.zoom)



with panel_col:
    pdf_info_panel(entry)
    st.divider()
    read_fav_controls(entry)
    st.divider()
    tags_panel(entry)
    st.divider()
    comments_panel(entry)


# ── Subject-level progress bar ────────────────────────────────────────────────
st.divider()
read_subj, _ = subject_progress(active_subject, all_entries, db.all_meta())
pct_subj     = read_subj / len(all_entries) if all_entries else 0
c1, c2 = st.columns([3, 1])
with c1:
    st.progress(
        pct_subj,
        text=f"{active_subject}: {read_subj} / {len(all_entries)} read "
             f"({pct_subj*100:.1f}%)",
    )
with c2:
    st.caption(f"Showing {len(filtered)} / {len(all_entries)} PDFs "
               f"(filter: {filter_mode})")
