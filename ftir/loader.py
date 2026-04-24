"""
Loads FTIR peak data from three input formats:

  Format A — Single Excel file, ONE run
             Columns: Wavenumber | Intensity  (header optional)
             Returns: {"Run 1": DataFrame}

  Format B — Multiple Excel files (one per run)
             Each file is Format A
             Returns: {"RUN_01": df, "RUN_03": df, ...}

  Format C — Single Excel file, MULTIPLE runs side-by-side
             Row 1: RUN headers  |  Row 2: column headers  |  Row 3+: data
             Returns: {"RUN 1": df, "RUN 3": df, ...}

Auto-detection logic:
  - Multiple files uploaded         → Format B
  - Single file, row-1 has "RUN"   → Format C
  - Single file, otherwise          → Format A
"""

from __future__ import annotations
import io
import re
from pathlib import Path
import openpyxl
import pandas as pd


# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────

def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows where both columns are numeric; rename cols."""
    df = df.copy()
    df.columns = ["wavenumber", "intensity"]
    df = df[pd.to_numeric(df["wavenumber"], errors="coerce").notna()]
    df = df[pd.to_numeric(df["intensity"],  errors="coerce").notna()]
    df["wavenumber"] = df["wavenumber"].astype(float)
    df["intensity"]  = df["intensity"].astype(float)
    df = df[(df["wavenumber"] > 0) & (df["intensity"] >= 0)]
    return df.reset_index(drop=True)


def _run_name_from_path(path: str | Path) -> str:
    stem = Path(path).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip().upper()
    return stem


def _is_run_header(value) -> bool:
    if value is None:
        return False
    return bool(re.search(r"\bRUN\b", str(value).upper()))


def _wb_from_source(source) -> openpyxl.Workbook:
    """Accept file path, BytesIO, or Streamlit UploadedFile."""
    if isinstance(source, (str, Path)):
        return openpyxl.load_workbook(source)
    # BytesIO or Streamlit UploadedFile
    data = source.read() if hasattr(source, "read") else source
    return openpyxl.load_workbook(io.BytesIO(data))


# ─────────────────────────────────────────────────────────────
# format-specific loaders
# ─────────────────────────────────────────────────────────────

def _load_format_a(source, run_name: str = "Run 1") -> dict[str, pd.DataFrame]:
    """Single file, single run."""
    wb = _wb_from_source(source)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {run_name: pd.DataFrame(columns=["wavenumber", "intensity"])}

    # Detect if first row is a header
    first_numeric = None
    start = 0
    for i, row in enumerate(rows):
        try:
            float(row[0]); float(row[1])
            first_numeric = i
            break
        except (TypeError, ValueError, IndexError):
            continue

    start = first_numeric if first_numeric is not None else 0
    data = [r[:2] for r in rows[start:] if len(r) >= 2]
    df = pd.DataFrame(data, columns=["wavenumber", "intensity"])
    return {run_name: _clean_df(df)}


def _load_format_b(sources, names: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Multiple files, one run each."""
    result = {}
    for i, src in enumerate(sources):
        name = names[i] if names else _run_name_from_path(
            getattr(src, "name", f"Run {i+1}")
        )
        single = _load_format_a(src, run_name=name)
        result.update(single)
    return result


def _load_format_c(source) -> dict[str, pd.DataFrame]:
    """Single file, multiple runs side-by-side."""
    wb = _wb_from_source(source)
    ws = wb.active

    # Find run columns from row 1
    run_cols: list[tuple[int, str]] = []
    for cell in ws[1]:
        if _is_run_header(cell.value):
            run_cols.append((cell.column, str(cell.value).strip()))

    if not run_cols:
        # Fallback to Format A if no RUN headers found
        return _load_format_a(source, run_name="Run 1")

    result = {}
    for col, run_name in run_cols:
        peaks = []
        for row in ws.iter_rows(min_row=3, min_col=col, max_col=col + 1, values_only=True):
            if row[0] is not None and isinstance(row[0], (int, float)):
                peaks.append([float(row[0]), float(row[1]) if row[1] is not None else 0.0])
        if peaks:
            df = pd.DataFrame(peaks, columns=["wavenumber", "intensity"])
            result[run_name] = _clean_df(df)

    return result


# ─────────────────────────────────────────────────────────────
# public API
# ─────────────────────────────────────────────────────────────

def detect_format(source_or_sources) -> str:
    """
    Returns 'A', 'B', or 'C'.
    source_or_sources: single source or list of sources.
    """
    if isinstance(source_or_sources, list):
        return "B" if len(source_or_sources) > 1 else detect_format(source_or_sources[0])

    try:
        wb = _wb_from_source(source_or_sources)
    except Exception:
        return "A"

    ws = wb.active
    row1 = [cell.value for cell in ws[1]]
    if any(_is_run_header(v) for v in row1):
        return "C"
    return "A"


def load(source_or_sources, names: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """
    Main entry point.
    Returns {run_name: DataFrame(wavenumber, intensity)} for all runs.
    """
    sources = source_or_sources if isinstance(source_or_sources, list) else [source_or_sources]

    if len(sources) > 1:
        fmt = "B"
    else:
        fmt = detect_format(sources[0])

    if fmt == "B":
        return _load_format_b(sources, names)
    elif fmt == "C":
        return _load_format_c(sources[0])
    else:
        name = names[0] if names else _run_name_from_path(
            getattr(sources[0], "name", "Run 1")
        )
        return _load_format_a(sources[0], run_name=name)


def load_from_folder(folder: str | Path) -> dict[str, pd.DataFrame]:
    """Load all .xlsx files from a directory (Format B)."""
    folder = Path(folder)
    files = sorted(folder.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx files found in {folder}")
    return _load_format_b(files, names=[_run_name_from_path(f) for f in files])
