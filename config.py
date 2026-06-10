"""
config.py
Central configuration for the Semester PDF Navigator.
"""

from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
# Change SEM_ROOT to point at your actual "Sem 5" folder.
SEM_ROOT: Path = Path("Sem 5")

# SQLite database file lives next to app.py
DB_PATH: Path = Path("navigator.db")

# ─── Month ordering ───────────────────────────────────────────────────────────
MONTH_ORDER: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

MONTH_DISPLAY: dict[str, str] = {
    "jan": "January", "feb": "February", "mar": "March",
    "apr": "April",   "may": "May",      "jun": "June",
    "jul": "July",    "aug": "August",   "sep": "September",
    "oct": "October", "nov": "November", "dec": "December",
}

# ─── UI constants ─────────────────────────────────────────────────────────────
APP_TITLE    = "Semester PDF Navigator"
APP_ICON     = "📚"
RECENT_LIMIT = 20        # max entries in recent-activity list

# ─── PDF rendering ────────────────────────────────────────────────────────────
# Supported zoom levels shown in the zoom control
ZOOM_LEVELS: list[float] = [0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
DEFAULT_ZOOM: float       = 1.5   # index into ZOOM_LEVELS

# ─── Allowed custom tags ──────────────────────────────────────────────────────
ALLOWED_TAGS: list[str] = ["Exam", "Revision", "Important", "Assignment", "Reading"]
