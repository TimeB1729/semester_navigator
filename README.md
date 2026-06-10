# 📚 Semester PDF Navigator

A polished Streamlit app for navigating, annotating, and tracking your semester lecture PDFs.

---

## Directory Layout

```
semester_navigator/
├── app.py           ← entry point
├── config.py        ← all tuneable constants
├── database.py      ← SQLite persistence
├── pdf_utils.py     ← file scanning & filename parsing
├── ui.py            ← reusable UI components
├── requirements.txt
├── navigator.db     ← auto-created on first run
└── Sem 5/           ← your PDF folder (create this)
    ├── LSM_25/
    │   ├── Jul_22_LSM.pdf
    │   ├── Jul_24_LSM.pdf
    │   └── ...
    ├── ParaInf_25/
    │   ├── Jul_23_ParaInf.pdf
    │   ├── Jan_25_ParaInf.pdf
	│   └── ...
    └── ...
```

---

## Quick Start

```bash
# 1. Clone / copy this folder
cd semester_navigator

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your PDF folder structure
mkdir -p "Sem 5/LSM_25"
# copy your PDFs in, named  Mon_DD_Topic.pdf

# 5. Run
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

---

## PDF Naming Convention

```
<Mon>_<DD>_<Topic>.pdf
```

| Part      | Format          | Examples            |
|-----------|-----------------|---------------------|
| `Mon`     | 3-letter month  | `Jan`, `Feb`, `Mar` |
| `DD`      | 1–2 digit day   | `3`, `12`, `25`     |
| `Topic`   | Words joined by `_` | `EM_Algorithm`  |

Full examples:
```
Jan_03_Introduction.pdf
Feb_10_BayesianNetworks.pdf
Mar_25_EMAlgorithm.pdf
```

---

## Features at a Glance

| Feature | Where |
|---|---|
| Folder navigation | Left sidebar |
| PDF viewer (embedded) | Reader view, main column |
| Prev / Next + keyboard ← → | Below file header |
| Mark as Read / Star | Right panel |
| Custom tags | Right panel |
| Per-PDF notes (auto-saved) | Right panel |
| Global search (names + notes) | Search view |
| Progress tracking | Bottom of reader + Dashboard |
| Dashboard charts | Dashboard view |
| Recent activity | Sidebar expander |
| Export all notes as Markdown | Dashboard → Export |

---

## Configuration (`config.py`)

| Constant | Default | Description |
|---|---|---|
| `SEM_ROOT` | `Path("Sem 5")` | Root folder to scan |
| `DB_PATH` | `Path("navigator.db")` | SQLite file location |
| `DEFAULT_PDF_HEIGHT` | `720` | Viewer height in px |
| `RECENT_LIMIT` | `20` | Max recent-activity entries |
| `ALLOWED_TAGS` | see file | Customisable tag list |

---

## Extending for Future Semesters

### Option A – Point at a new root

Change `SEM_ROOT` in `config.py`:

```python
SEM_ROOT = Path("Sem 6")
```

The app will scan the new directory; the SQLite DB is keyed by `Subject/filename`, so Sem 5 and Sem 6 notes never collide if you keep separate DB files:

```python
DB_PATH = Path("sem6.db")
```

### Option B – Multi-semester mode

1. Add a `SEMESTER` selector widget in `app.py`.
2. Pass the chosen root to `get_subjects()` and `get_pdfs_for_subject()`.
3. Store the chosen semester in `st.session_state.semester` and prefix DB keys with it.

### Adding new subjects

Just drop a new folder inside `Sem 5/` and refresh the browser. No code changes needed.

---

## Architecture Notes

- **`config.py`** is the single source of truth for all magic strings and paths. Changing semester root, DB location, or tag list requires editing one file.
- **`database.py`** wraps every SQLite interaction in a context manager, keeping connection lifetimes short and thread-safe for Streamlit's multi-threading model.
- **`pdf_utils.py`** is pure Python with no Streamlit imports — it can be imported by tests or scripts independently.
- **`ui.py`** contains only rendering logic and thin DB calls; no business logic.
- **`app.py`** wires the views together via `st.session_state`, acting as a minimal router.
