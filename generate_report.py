"""
FTIR Transplant Fluid Report Generator
=======================================
Generates a single standalone HTML file — no server needed.
Publish freely on GitHub Pages, Netlify, or any static host.

Usage
-----
# Mode 1 — before (single consolidated xlsx)
  python generate_report.py --before "MASTER SHEET.xlsx"

# Mode 1 — before (folder of individual run files)
  python generate_report.py --before test_data/before/

# Mode 1 — after (single run file)
  python generate_report.py --after test_data/after/RUN_01.xlsx

# Mode 2 — before vs after comparison
  python generate_report.py --before "MASTER SHEET.xlsx" --after test_data/after/

# Custom output path
  python generate_report.py --before test_data/before/ --output my_report.html

Input format is auto-detected:
  • Single xlsx with RUN headers      → multi-run consolidated (Format C)
  • Single xlsx without RUN headers   → single run            (Format A)
  • Folder or multiple files          → one file per run      (Format B)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import datetime

import numpy as np
import pandas as pd

from ftir.loader     import load, load_from_folder
from ftir.analysis   import run_analysis
from ftir.difference import compare
import ftir.charts   as C


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate a standalone FTIR analysis HTML report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--before", metavar="PATH",
                   help="Before-transplant data: xlsx file OR folder of xlsx files")
    p.add_argument("--after",  metavar="PATH",
                   help="After-transplant data: xlsx file OR folder of xlsx files "
                        "(omit for Mode 1 single-side analysis)")
    p.add_argument("--output", metavar="FILE", default="index.html",
                   help="Output HTML file (default: index.html)")
    return p.parse_args()


def _load_path(path_str: str, label: str) -> dict:
    """Load from a file path or folder path."""
    p = Path(path_str)
    if p.is_dir():
        print(f"  Loading {label}: folder  '{p}'")
        runs = load_from_folder(p)
    elif p.suffix.lower() == ".xlsx":
        print(f"  Loading {label}: file    '{p}'")
        runs = load([p])
    else:
        sys.exit(f"ERROR: --{label.lower()} must be an .xlsx file or a folder.")
    print(f"    → {len(runs)} run(s): {list(runs.keys())}")
    return runs


# ─────────────────────────────────────────────────────────────
# HTML builder
# ─────────────────────────────────────────────────────────────

def build_html(before_res: dict, after_res: dict | None, diff: dict | None) -> str:
    mode2 = after_res is not None
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    label = before_res["label"]

    # ── serialise data for client-side export ──
    export_data = _build_export_data(before_res, after_res, diff)
    export_json = json.dumps(export_data, allow_nan=False)

    # ── plotly figures ──
    figs = _collect_figures(before_res, after_res, diff, mode2)
    fig_divs = {k: f.to_html(full_html=False, include_plotlyjs=False,
                              div_id=k, config={"responsive": True})
                for k, f in figs.items()}

    # ── section HTML ──
    if mode2:
        nav_html   = _nav(mode2)
        body_html  = _mode2_body(before_res, after_res, diff, fig_divs)
        header_html = _header_mode2(before_res, after_res, diff, now)
    else:
        nav_html   = _nav(mode2)
        body_html  = _mode1_body(before_res, fig_divs)
        header_html = _header_mode1(before_res, now)

    title = ("FTIR Before vs After Analysis"
             if mode2 else f"FTIR Analysis — {label}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
{_css()}
</head>
<body>
{header_html}
{nav_html}
<main>
{body_html}
</main>
{_footer()}
{_js(export_json, mode2, label)}
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# figures
# ─────────────────────────────────────────────────────────────

def _collect_figures(before, after, diff, mode2):
    figs = {}
    def _add(k, f):
        if f is not None:
            figs[k] = f
    _add("spectral_overlay",    C.spectral_overlay(before))
    _add("mean_band",           C.mean_band(before))
    _add("intensity_heatmap",   C.intensity_heatmap(before))
    _add("cv_chart",            C.cv_chart(before))
    _add("consistency_chart",   C.consistency_chart(before))
    _add("peak_count_bar",      C.peak_count_bar(before))
    _add("region_distribution", C.region_distribution(before))
    _add("top_peaks_bar",       C.top_peaks_bar(before))
    _add("region_boxplot",      C.region_boxplot(before))
    if mode2:
        _add("comparison_overlay",    C.comparison_overlay(before, after))
        _add("delta_spectrum",        C.delta_spectrum(diff))
        _add("volcano_plot",          C.volcano_plot(diff))
        _add("region_comparison_bar", C.region_comparison_bar(before, after))
        _add("toxicity_scorecard",    C.toxicity_scorecard(diff))
        _add("new_lost_peaks",        C.new_lost_peaks(diff))
        _add("spectral_overlay_after",   C.spectral_overlay(after))
        _add("mean_band_after",          C.mean_band(after))
        _add("region_distribution_after",C.region_distribution(after))
        _add("top_peaks_bar_after",      C.top_peaks_bar(after))
        _add("region_boxplot_after",     C.region_boxplot(after))
    return figs


# ─────────────────────────────────────────────────────────────
# export data (JSON embedded for client-side CSV/Excel)
# ─────────────────────────────────────────────────────────────

def _build_export_data(before, after, diff):
    def _df_to_records(df: pd.DataFrame) -> list:
        import math
        records = df.to_dict(orient="records")
        return [
            {k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
             for k, v in rec.items()}
            for rec in records
        ]

    data = {
        "before_peaks": _df_to_records(
            before["bin_stats"][[
                "bin","functional_group","bond","vibration_type","compound_class",
                "biological_relevance","mean_intensity","std_intensity","cv_pct",
                "present_in_n","consistency","region"
            ]]
        ),
        "before_runs": _df_to_records(before["run_summary"]),
        "before_all":  _df_to_records(
            before["all_df"][[
                "run","wavenumber","intensity","bin","region",
                "functional_group","bond","compound_class","biological_relevance"
            ]]
        ),
    }
    if after is not None:
        data["after_peaks"] = _df_to_records(
            after["bin_stats"][[
                "bin","functional_group","bond","vibration_type","compound_class",
                "biological_relevance","mean_intensity","std_intensity","cv_pct",
                "present_in_n","consistency","region"
            ]]
        )
        data["after_runs"] = _df_to_records(after["run_summary"])
    if diff is not None:
        data["delta"]    = _df_to_records(diff["delta_df"])
        data["toxicity"] = _df_to_records(diff["toxicity_df"])
        data["new_peaks"]  = _df_to_records(diff["new_peaks"])
        data["lost_peaks"] = _df_to_records(diff["lost_peaks"])
    return data


# ─────────────────────────────────────────────────────────────
# headers
# ─────────────────────────────────────────────────────────────

def _header_mode1(r, now):
    bs = r["bin_stats"]
    peak_at = bs.loc[bs["mean_intensity"].idxmax(), "bin"]
    return f"""
<header class="hdr">
  <div class="hdr-inner">
    <h1>FTIR Spectroscopic Analysis</h1>
    <p class="sub">Transplant Fluid &mdash; <b>{r['label']}</b> transplant
       &nbsp;|&nbsp; Generated {now}</p>
    <div class="kpi-row">
      {_kpi("Total Peaks",       len(r['all_df']))}
      {_kpi("Runs",              r['n_runs'])}
      {_kpi("Consistent Peaks",  len(r['highly_consistent']), "≥80% runs")}
      {_kpi("Wavenumber Range",  f"{r['all_df']['wavenumber'].min():.0f}–{r['all_df']['wavenumber'].max():.0f}", "cm⁻¹")}
      {_kpi("Max Mean Intensity", f"{bs['mean_intensity'].max():.3f}", f"at {peak_at:.0f} cm⁻¹")}
      {_kpi("Mode", "1 — Single-side")}
    </div>
  </div>
</header>"""


def _header_mode2(before, after, diff, now):
    vc = diff["verdict_color"]
    return f"""
<header class="hdr">
  <div class="hdr-inner">
    <h1>FTIR Before vs After Comparison</h1>
    <p class="sub">Transplant Fluid &mdash; Toxicity &amp; Biochemical Change Analysis
       &nbsp;|&nbsp; Generated {now}</p>
    <div class="kpi-row">
      {_kpi("Before Peaks",     len(before['all_df']))}
      {_kpi("Before Runs",      before['n_runs'])}
      {_kpi("After Peaks",      len(after['all_df']))}
      {_kpi("After Runs",       after['n_runs'])}
      {_kpi("New Peaks",        len(diff['new_peaks']))}
      {_kpi("Lost Peaks",       len(diff['lost_peaks']))}
      {_kpi("Significant Δ",    len(diff['significant_changes']))}
      <div class="kpi-card" style="border-top:4px solid {vc}">
        <div class="kpi-label">Toxicity Verdict</div>
        <div class="kpi-val" style="color:{vc}">{diff['verdict']}</div>
        <div class="kpi-sub">{diff['toxicity_score']}/{diff['toxicity_max']} &nbsp; {diff['toxicity_pct']:.1f}%</div>
      </div>
    </div>
  </div>
</header>"""


def _kpi(label, val, sub=""):
    return (f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-val">{val}</div>'
            f'<div class="kpi-sub">{sub}&nbsp;</div>'
            f'</div>')


# ─────────────────────────────────────────────────────────────
# navigation
# ─────────────────────────────────────────────────────────────

def _nav(mode2):
    links_m1 = [
        ("#overview",        "Overview"),
        ("#spectra",         "Spectra"),
        ("#assignments",     "Assignments"),
        ("#statistics",      "Statistics"),
        ("#regions",         "Regions"),
        ("#reproducibility", "Reproducibility"),
        ("#full-table",      "Full Table"),
    ]
    links_m2 = [
        ("#overview",    "Overview"),
        ("#comparison",  "Comparison"),
        ("#delta",       "Delta"),
        ("#toxicity",    "Toxicity"),
        ("#new-lost",    "New / Lost"),
        ("#before",      "Before Analysis"),
        ("#after",       "After Analysis"),
        ("#full-table",  "Full Tables"),
    ]
    links = links_m2 if mode2 else links_m1
    items = "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in links)
    return f"""
<nav class="topnav" id="topnav">
  <ul>{items}</ul>
  <div class="export-bar">
    <button onclick="exportCSV()" title="Download CSV">⬇ CSV</button>
    <button onclick="exportExcel()" title="Download Excel">⬇ Excel</button>
    <button onclick="window.print()" title="Print / Save as PDF">🖨 PDF</button>
  </div>
</nav>"""


# ─────────────────────────────────────────────────────────────
# MODE 1 body
# ─────────────────────────────────────────────────────────────

def _mode1_body(r, fd):
    single = r["is_single"]
    label  = r["label"]
    hc     = r["highly_consistent"].sort_values("bin")
    bs     = r["bin_stats"].sort_values("bin")

    repro_section = (
        f"""
<section id="reproducibility">
  <h2>Reproducibility</h2>
  <p class="lead">CV% per wavenumber bin and peak consistency across runs.
     Low CV% (green) = highly reproducible — reliable for pre/post comparison.</p>
  {'<div class="chart-card">' + fd.get("cv_chart","") + '</div>' if "cv_chart" in fd else ""}
  {'<div class="chart-card mt">' + fd.get("consistency_chart","") + '</div>' if "consistency_chart" in fd else ""}
</section>"""
        if not single else
        f"""
<section id="reproducibility">
  <h2>Reproducibility</h2>
  <div class="callout info">Reproducibility analysis (CV%, consistency) requires
  at least 2 runs. Upload a folder of run files or a multi-run Excel to enable
  this section.</div>
</section>"""
    )

    return f"""
<section id="overview">
  <h2>Overview</h2>
  <p class="lead">
    This report analyses the FTIR spectroscopic profile of transplant fluid
    <strong>({label} transplant)</strong>. Peaks are mapped to functional groups
    and biological compounds. Consistent peaks form the chemical fingerprint of
    this fluid state.
  </p>
  {_run_cards(r)}
</section>

<section id="spectra">
  <h2>Spectra</h2>
  <p class="lead">{'Spectrum of the single run.' if single else f'Overlay of all {r["n_runs"]} runs. Regions are colour-coded by spectral zone.'}</p>
  <div class="chart-card">{fd.get("spectral_overlay","")}</div>
  {'<div class="chart-card mt">' + fd["mean_band"] + '</div>' if "mean_band" in fd else ""}
</section>

<section id="assignments">
  <h2>Peak Assignments — Consistent Peaks (≥80% of runs)</h2>
  <p class="lead">{len(hc)} peaks present in ≥80% of {r["n_runs"]} run(s).
     Each bin is mapped to its functional group and biological relevance.</p>
  {_callout_single(single)}
  <div class="tbl-wrap" id="assign-tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search assignments…"
           oninput="filterTable(this,'assign-tbl')">
    {_assignment_table(hc, r['n_runs'], 'assign-tbl')}
  </div>
</section>

<section id="statistics">
  <h2>Statistics</h2>
  <p class="lead">Top 20 most intense peaks, intensity distributions, and
  per-run peak counts.</p>
  <div class="grid2">
    <div class="chart-card">{fd.get("top_peaks_bar","")}</div>
    <div class="chart-card">{fd.get("region_boxplot","")}</div>
  </div>
  {'<div class="chart-card mt">' + fd["peak_count_bar"] + '</div>' if "peak_count_bar" in fd else ""}
  {'<div class="chart-card mt">' + fd["intensity_heatmap"] + '</div>' if "intensity_heatmap" in fd else ""}
</section>

<section id="regions">
  <h2>Spectral Regions</h2>
  <p class="lead">Mid-IR divided into 9 functional zones. Each region reflects
     distinct chemical components of the preservation fluid.</p>
  <div class="chart-card">{fd.get("region_distribution","")}</div>
  {_region_reference_table()}
</section>

{repro_section}

<section id="full-table">
  <h2>Full Peak Table</h2>
  <p class="lead">{len(bs)} unique 10 cm⁻¹ bins across all runs with
  complete IR assignments.</p>
  <div class="tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search peaks, groups, compounds…"
           oninput="filterTable(this,'full-tbl')">
    {_full_peak_table(bs, r['n_runs'], 'full-tbl')}
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────
# MODE 2 body
# ─────────────────────────────────────────────────────────────

def _mode2_body(before, after, diff, fd):
    vc = diff["verdict_color"]
    return f"""
<section id="overview">
  <h2>Overview</h2>
  <div class="callout" style="border-color:{vc}">
    <strong>Toxicity Verdict: <span style="color:{vc};font-size:1.15em">
    {diff['verdict']}</span></strong>
    &nbsp;(score {diff['toxicity_score']}/{diff['toxicity_max']},
    {diff['toxicity_pct']:.1f}%)
    <br><span style="color:#555">{diff['verdict_detail']}</span>
  </div>
  <div class="grid2 mt">
    <div>
      <h3>Before transplant — {before['n_runs']} run(s)</h3>
      {_run_cards(before)}
    </div>
    <div>
      <h3>After transplant — {after['n_runs']} run(s)</h3>
      {_run_cards(after)}
    </div>
  </div>
</section>

<section id="comparison">
  <h2>Spectral Comparison</h2>
  <p class="lead">Mean spectra (±1 SD) of Before and After overlaid, and
  mean intensity per spectral region side by side.</p>
  <div class="chart-card">{fd.get("comparison_overlay","")}</div>
  <div class="chart-card mt">{fd.get("region_comparison_bar","")}</div>
</section>

<section id="delta">
  <h2>Delta Analysis (After − Before)</h2>
  <p class="lead">Red bars = intensity increase after transplant.
  Blue bars = intensity decrease. The volcano plot shows both magnitude
  and direction of change per bin.</p>
  <div class="chart-card">{fd.get("delta_spectrum","")}</div>
  <div class="chart-card mt">{fd.get("volcano_plot","")}</div>
  <h3 style="margin:24px 0 12px">Significant Changes</h3>
  <div class="tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'delta-tbl')">
    {_delta_table(diff['significant_changes'], 'delta-tbl')}
  </div>
</section>

<section id="toxicity">
  <h2>Toxicity Marker Analysis</h2>
  <p class="lead">10 key spectroscopic markers for organ stress, cell damage,
  and biochemical toxicity. Each is scored None → Low → Moderate → High.</p>
  <div class="chart-card">{fd.get("toxicity_scorecard","")}</div>
  <div class="tbl-wrap mt">
    {_toxicity_table(diff['toxicity_df'])}
  </div>
</section>

<section id="new-lost">
  <h2>New and Lost Peaks</h2>
  <p class="lead">Peaks present only in After (new) or only in Before (lost)
  indicate biochemical species that appeared or disappeared post-transplant.</p>
  <div class="chart-card">{fd.get("new_lost_peaks","")}</div>
  <div class="grid2 mt">
    <div>
      <h3>New Peaks — {len(diff['new_peaks'])} detected</h3>
      {_new_lost_table(diff['new_peaks'], "after", "new-tbl")}
    </div>
    <div>
      <h3>Lost Peaks — {len(diff['lost_peaks'])} detected</h3>
      {_new_lost_table(diff['lost_peaks'], "before", "lost-tbl")}
    </div>
  </div>
</section>

<section id="before">
  <h2>Before Transplant — Full Analysis</h2>
  <div class="chart-card">{fd.get("spectral_overlay","")}</div>
  {'<div class="chart-card mt">' + fd["mean_band"] + '</div>' if "mean_band" in fd else ""}
  <div class="chart-card mt">{fd.get("top_peaks_bar","")}</div>
  <div class="chart-card mt">{fd.get("region_distribution","")}</div>
  {'<div class="chart-card mt">' + fd["intensity_heatmap"] + '</div>' if "intensity_heatmap" in fd else ""}
  {'<div class="chart-card mt">' + fd["cv_chart"] + '</div>' if "cv_chart" in fd else ""}
  <h3 style="margin:24px 0 12px">Consistent Peaks (Before)</h3>
  <div class="tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'before-assign-tbl')">
    {_assignment_table(before["highly_consistent"].sort_values("bin"),
                       before["n_runs"], 'before-assign-tbl')}
  </div>
</section>

<section id="after">
  <h2>After Transplant — Full Analysis</h2>
  <div class="chart-card">{fd.get("spectral_overlay_after","")}</div>
  {'<div class="chart-card mt">' + fd["mean_band_after"] + '</div>' if "mean_band_after" in fd else ""}
  <div class="chart-card mt">{fd.get("top_peaks_bar_after","")}</div>
  <div class="chart-card mt">{fd.get("region_distribution_after","")}</div>
  <h3 style="margin:24px 0 12px">Consistent Peaks (After)</h3>
  <div class="tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'after-assign-tbl')">
    {_assignment_table(after["highly_consistent"].sort_values("bin"),
                       after["n_runs"], 'after-assign-tbl')}
  </div>
</section>

<section id="full-table">
  <h2>Full Peak Tables</h2>
  <div class="tabs" id="full-tabs">
    <button class="tab-btn active" onclick="switchTab('ft-before','full-tabs',this)">Before</button>
    <button class="tab-btn"        onclick="switchTab('ft-after', 'full-tabs',this)">After</button>
    <button class="tab-btn"        onclick="switchTab('ft-delta', 'full-tabs',this)">Delta</button>
  </div>
  <div id="ft-before" class="tab-panel active tbl-wrap">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'ft-before-tbl')">
    {_full_peak_table(before["bin_stats"].sort_values("bin"), before["n_runs"], 'ft-before-tbl')}
  </div>
  <div id="ft-after" class="tab-panel tbl-wrap" style="display:none">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'ft-after-tbl')">
    {_full_peak_table(after["bin_stats"].sort_values("bin"), after["n_runs"], 'ft-after-tbl')}
  </div>
  <div id="ft-delta" class="tab-panel tbl-wrap" style="display:none">
    <input class="tbl-search" type="text" placeholder="Search…"
           oninput="filterTable(this,'ft-delta-tbl')">
    {_delta_table(diff["delta_df"].sort_values("bin"), 'ft-delta-tbl')}
  </div>
</section>"""


# ─────────────────────────────────────────────────────────────
# table builders
# ─────────────────────────────────────────────────────────────

def _cv_color(cv):
    if pd.isna(cv): return "#888"
    return "#27ae60" if cv < 20 else ("#f39c12" if cv < 50 else "#e74c3c")

def _cv_str(cv):
    return "–" if pd.isna(cv) else f"{cv:.1f}%"

def _concern_badge(c):
    cls = {"None":"badge-none","Low":"badge-low","Moderate":"badge-mod","High":"badge-high"}.get(c,"badge-none")
    return f'<span class="badge {cls}">{c}</span>'

def _assignment_table(hc, n_runs, tid):
    rows = "".join(
        f"<tr>"
        f"<td class='wn'>{r['bin']:.0f}</td>"
        f"<td><b>{r['functional_group']}</b></td>"
        f"<td><code>{r['bond']}</code></td>"
        f"<td>{r['vibration_type']}</td>"
        f"<td>{r['compound_class']}</td>"
        f"<td class='bio'>{r['biological_relevance']}</td>"
        f"<td>{r['mean_intensity']:.4f}</td>"
        f"<td style='color:{_cv_color(r['cv_pct'])}'>{_cv_str(r['cv_pct'])}</td>"
        f"<td>{int(r['count'])}/{n_runs}</td>"
        f"</tr>"
        for _, r in hc.iterrows()
    ) or "<tr><td colspan='9' class='muted'>No consistent peaks found.</td></tr>"
    return (f'<table id="{tid}"><thead><tr>'
            '<th>Bin cm⁻¹</th><th>Functional Group</th><th>Bond</th>'
            '<th>Vibration</th><th>Compound Class</th><th>Biological Relevance</th>'
            '<th>Mean Int.</th><th>CV%</th><th>Runs</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _full_peak_table(bs, n_runs, tid):
    rows = "".join(
        f"<tr>"
        f"<td class='wn'>{r['bin']:.0f}</td>"
        f"<td>{r['functional_group']}</td>"
        f"<td><code>{r['bond']}</code></td>"
        f"<td>{r['compound_class']}</td>"
        f"<td class='bio'>{r['biological_relevance']}</td>"
        f"<td>{r['mean_intensity']:.4f}</td>"
        f"<td style='color:{_cv_color(r['cv_pct'])}'>{_cv_str(r['cv_pct'])}</td>"
        f"<td>{int(r['count'])}/{n_runs}</td>"
        f"<td>{r['region']}</td>"
        f"</tr>"
        for _, r in bs.iterrows()
    )
    return (f'<table id="{tid}"><thead><tr>'
            '<th>Bin cm⁻¹</th><th>Functional Group</th><th>Bond</th>'
            '<th>Compound Class</th><th>Biological Relevance</th>'
            '<th>Mean Int.</th><th>CV%</th><th>Runs</th><th>Region</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _delta_table(df, tid):
    status_color = {
        "new":"#9b59b6","lost":"#e67e22",
        "increased":"#e74c3c","decreased":"#2980b9","unchanged":"#95a5a6"
    }
    rows_html = []
    for _, r in df.iterrows():
        dc  = "#e74c3c" if r["delta"]     > 0 else "#2980b9"
        dpc = "#e74c3c" if r["delta_pct"] > 0 else "#2980b9"
        sc  = status_color.get(r["status"], "#888")
        rows_html.append(
            f"<tr>"
            f"<td class='wn'>{r['bin']:.0f}</td>"
            f"<td>{r['functional_group']}</td>"
            f"<td>{r['region']}</td>"
            f"<td>{r['mean_before']:.4f}</td>"
            f"<td>{r['mean_after']:.4f}</td>"
            f"<td style='color:{dc}'>{r['delta']:+.4f}</td>"
            f"<td style='color:{dpc}'>{r['delta_pct']:+.1f}%</td>"
            f"<td style='color:{sc}'><b>{r['status']}</b></td>"
            f"<td class='bio'>{r['biological_relevance']}</td>"
            f"</tr>"
        )
    rows = "".join(rows_html) or "<tr><td colspan='9' class='muted'>No changes found.</td></tr>"
    return (f'<table id="{tid}"><thead><tr>'
            '<th>Bin cm⁻¹</th><th>Functional Group</th><th>Region</th>'
            '<th>Before</th><th>After</th><th>Δ</th><th>Δ%</th>'
            '<th>Status</th><th>Biological Relevance</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _toxicity_table(df):
    rows_html = []
    for _, r in df.iterrows():
        dpc = "#e74c3c" if r["delta_pct"] > 0 else "#2980b9"
        rows_html.append(
            f"<tr>"
            f"<td><b>{r['marker']}</b></td>"
            f"<td>{r['band_label']}</td>"
            f"<td>{r['before_value']:.5f}</td>"
            f"<td>{r['after_value']:.5f}</td>"
            f"<td style='color:{dpc}'>{r['delta_pct']:+.1f}%</td>"
            f"<td>{_concern_badge(r['concern'])}</td>"
            f"<td class='bio'>{r['description']}</td>"
            f"</tr>"
        )
    rows = "".join(rows_html)
    return ('<table><thead><tr>'
            '<th>Marker</th><th>Band</th><th>Before</th><th>After</th>'
            '<th>Δ%</th><th>Concern</th><th>Interpretation</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _new_lost_table(df, intensity_col, tid):
    if df.empty:
        return f'<p class="callout ok">None detected.</p>'
    rows = "".join(
        f"<tr><td class='wn'>{r['bin']:.0f}</td>"
        f"<td>{r['functional_group']}</td>"
        f"<td>{r['mean_'+intensity_col]:.4f}</td>"
        f"<td class='bio'>{r['biological_relevance']}</td></tr>"
        for _, r in df.sort_values("mean_"+intensity_col, ascending=False).iterrows()
    )
    return (f'<table id="{tid}"><thead><tr>'
            f'<th>Bin cm⁻¹</th><th>Functional Group</th>'
            f'<th>Intensity</th><th>Biological Relevance</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _run_cards(r):
    cards = "".join(
        f'<div class="run-card">'
        f'<div class="rc-title">{row["run"]}</div>'
        f'<div class="rc-row"><span>Peaks</span><b>{row["n_peaks"]}</b></div>'
        f'<div class="rc-row"><span>Mean int.</span><b>{row["mean_intensity"]:.4f}</b></div>'
        f'<div class="rc-row"><span>Max int.</span><b>{row["max_intensity"]:.4f}</b></div>'
        f'</div>'
        for _, row in r["run_summary"].iterrows()
    )
    return f'<div class="run-cards">{cards}</div>'


def _callout_single(single):
    if not single:
        return ""
    return ('<div class="callout info">Single-run dataset: CV% and run-count columns '
            'are not applicable.</div>')


def _region_reference_table():
    rows = [
        ("400–700",   "Fingerprint / Inorganic",      "Metal salts, phosphate bends",                  "Preservation buffer inorganic salts (KH₂PO₄, MgSO₄)"),
        ("700–900",   "Aromatic & Long-chain C–H",     "(CH₂)ₙ rocking, aromatic C–H bend",             "Long-chain fatty acids from cell membranes; adenine ring"),
        ("900–1300",  "Carbohydrate / Phosphate",      "C–O–C glycosidic, P–O, C–O stretch",            "Primary preservation solutes: glucose, raffinose, HES, phosphate"),
        ("1300–1500", "Protein C–H / Carboxylate",     "Amide III, CH₂ scissoring, COO⁻ sym.",          "Protein side chains, amino acid carboxylates (glutathione)"),
        ("1500–1800", "Amide / Lipid C=O",             "Amide I (~1650), Amide II (~1550), ester C=O",  "<b>Critical toxicity zone:</b> protein structure + membrane lipids"),
        ("1800–2800", "Overtone / CO₂",                "Overtones, CO₂ (~2349), aldehyde C–H (~2720)",  "Weak region; CO₂ artefact; aldehyde = oxidative stress marker"),
        ("2800–3050", "C–H Stretch (Lipids)",          "CH₂/CH₃ symmetric + asymmetric stretch",        "Lipid content; elevated post-transplant = cell lysis"),
        ("3050–3700", "O–H / N–H Stretch",             "O–H broad (water, sugars), N–H (proteins)",     "Dominant aqueous peak; carbohydrate OH; protein N–H"),
        ("3700–3900", "O–H Overtone / Atmospheric",    "Water vapour overtones",                         "Atmospheric water vapour; instrument noise"),
    ]
    header = ("<thead><tr><th>Range cm⁻¹</th><th>Zone</th>"
              "<th>Key Assignments</th><th>Biological Meaning</th></tr></thead>")
    body = "".join(
        f"<tr><td><b>{lo}</b></td><td>{z}</td><td>{k}</td><td>{b}</td></tr>"
        for lo, z, k, b in rows
    )
    return f'<div class="tbl-wrap mt"><table>{header}<tbody>{body}</tbody></table></div>'


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────

def _css():
    return """<style>
:root{--bg:#f4f6f9;--card:#fff;--text:#2c3e50;--accent:#2980b9;
      --border:#dde1e7;--muted:#7f8c8d;--radius:10px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px}

/* header */
.hdr{background:linear-gradient(135deg,#1a2a4a 0%,#2980b9 100%);color:#fff;padding:36px 48px 28px}
.hdr h1{font-size:1.85rem;font-weight:700;letter-spacing:-.3px}
.hdr .sub{font-size:.92rem;opacity:.82;margin-top:5px}
.kpi-row{display:flex;flex-wrap:wrap;gap:14px;margin-top:20px}
.kpi-card{background:rgba(255,255,255,.12);border-radius:8px;padding:12px 18px;min-width:130px}
.kpi-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.5px;opacity:.75}
.kpi-val{font-size:1.55rem;font-weight:700;margin-top:2px}
.kpi-sub{font-size:.72rem;opacity:.72;margin-top:1px}

/* nav */
.topnav{background:#fff;border-bottom:1px solid var(--border);
        position:sticky;top:0;z-index:100;display:flex;align-items:center;
        padding:0 48px;gap:0}
.topnav ul{display:flex;list-style:none;flex:1;overflow-x:auto}
.topnav a{display:block;padding:13px 14px;font-size:.83rem;font-weight:500;
          color:var(--muted);text-decoration:none;white-space:nowrap;
          border-bottom:3px solid transparent;transition:.18s}
.topnav a:hover,.topnav a.active{color:var(--accent);border-bottom-color:var(--accent)}
.export-bar{display:flex;gap:8px;padding:8px 0;flex-shrink:0}
.export-bar button{padding:6px 14px;border:1px solid var(--border);background:#fff;
                   border-radius:6px;font-size:.8rem;cursor:pointer;white-space:nowrap;
                   transition:.15s;color:var(--text)}
.export-bar button:hover{background:var(--accent);color:#fff;border-color:var(--accent)}

/* main */
main{max-width:1400px;margin:0 auto;padding:28px 48px 72px}
section{margin-bottom:52px}
section h2{font-size:1.25rem;font-weight:700;border-left:4px solid var(--accent);
           padding-left:10px;margin-bottom:14px}
section h3{font-size:1rem;font-weight:600;margin-bottom:10px;color:var(--text)}
.lead{font-size:.88rem;color:var(--muted);margin-bottom:16px;line-height:1.65}
.mt{margin-top:18px}

/* chart card */
.chart-card{background:var(--card);border:1px solid var(--border);
            border-radius:var(--radius);overflow:hidden}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}

/* run cards */
.run-cards{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}
.run-card{background:var(--card);border:1px solid var(--border);border-radius:8px;
          border-top:4px solid var(--accent);padding:12px 16px;min-width:150px}
.rc-title{font-weight:700;font-size:.92rem;margin-bottom:8px}
.rc-row{display:flex;justify-content:space-between;font-size:.78rem;
        padding:2px 0;border-bottom:1px solid #f0f0f0;color:var(--muted)}
.rc-row b{color:var(--text)}

/* tables */
.tbl-wrap{overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border);
          background:var(--card)}
table{width:100%;border-collapse:collapse;font-size:.78rem}
thead tr{background:#f0f4f8}
th{padding:9px 11px;text-align:left;font-weight:600;font-size:.72rem;
   text-transform:uppercase;letter-spacing:.3px;color:var(--muted);
   border-bottom:2px solid var(--border);white-space:nowrap}
td{padding:7px 11px;border-bottom:1px solid #f0f0f0;vertical-align:top}
tr:hover td{background:#f7faff}
td.wn{font-weight:700;color:var(--accent)}
td.bio{font-size:.72rem;color:var(--muted);max-width:240px}
td.muted{color:var(--muted);font-style:italic}
code{background:#f0f4f8;padding:2px 5px;border-radius:3px;font-size:.75rem;color:#c0392b}
.tbl-search{width:100%;padding:8px 12px;border:none;border-bottom:1px solid var(--border);
            font-size:.83rem;outline:none;background:#fafbfc}

/* badges */
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.7rem;font-weight:700;color:#fff}
.badge-none{background:#95a5a6}.badge-low{background:#27ae60}
.badge-mod{background:#e67e22}.badge-high{background:#e74c3c}

/* callouts */
.callout{border-left:4px solid #f39c12;background:#fff8f0;padding:13px 17px;
         border-radius:0 8px 8px 0;margin:12px 0;font-size:.87rem;line-height:1.65}
.callout.info{border-color:var(--accent);background:#f0f7ff}
.callout.ok{border-color:#27ae60;background:#f0fff4}

/* tabs */
.tabs{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:0}
.tab-btn{padding:9px 18px;background:none;border:none;cursor:pointer;
         font-size:.85rem;font-weight:500;color:var(--muted);
         border-bottom:3px solid transparent;margin-bottom:-2px;transition:.15s}
.tab-btn.active,.tab-btn:hover{color:var(--accent);border-bottom-color:var(--accent)}

/* footer */
footer{background:#fff;border-top:1px solid var(--border);
       padding:18px 48px;font-size:.75rem;color:var(--muted);line-height:1.6}

/* print */
@media print{
  .topnav,.export-bar{display:none!important}
  main{padding:0}
  .chart-card,.tbl-wrap{break-inside:avoid;page-break-inside:avoid}
  section{break-inside:avoid}
  .hdr{background:#fff!important;color:#000!important;-webkit-print-color-adjust:exact}
}
</style>"""


# ─────────────────────────────────────────────────────────────
# footer + JS
# ─────────────────────────────────────────────────────────────

def _footer():
    return """<footer>
  <b>FTIR Transplant Fluid Analyser</b> &mdash;
  IR assignments: Colthup, Daly &amp; Wiberley (1990);
  Movasaghi et al. <em>Appl.Spectrosc.Rev.</em> 43 (2008) 134–179;
  Stuart <em>Biological Applications of Infrared Spectroscopy</em> (1997). &nbsp;|&nbsp;
  Charts: <a href="https://plotly.com" target="_blank">Plotly</a> &nbsp;|&nbsp;
  Excel export: <a href="https://sheetjs.com" target="_blank">SheetJS</a>
</footer>"""


def _js(export_json, mode2, label):
    stem = "ftir_before_vs_after" if mode2 else f"ftir_{label.lower()}"
    return f"""<script>
// ── embedded data ──
const FTIR_DATA = {export_json};

// ── table filter ──
function filterTable(inp, tblId) {{
  const q = inp.value.toLowerCase();
  document.getElementById(tblId).querySelectorAll('tbody tr').forEach(r => {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}

// ── tab switcher ──
function switchTab(panelId, groupId, btn) {{
  document.getElementById(groupId).querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#' + groupId + ' + .tab-panel, #' + groupId).forEach(() => {{}});
  // hide all panels that are siblings of the tabs div
  const tabs = document.getElementById(groupId);
  let el = tabs.nextElementSibling;
  while (el && el.classList.contains('tab-panel')) {{
    el.style.display = 'none'; el = el.nextElementSibling;
  }}
  document.getElementById(panelId).style.display = '';
}}

// ── CSV export ──
function exportCSV() {{
  const rows = FTIR_DATA.before_peaks;
  if (!rows || !rows.length) return;
  const keys = Object.keys(rows[0]);
  const csv  = [keys.join(','), ...rows.map(r =>
    keys.map(k => JSON.stringify(r[k] ?? '')).join(',')
  )].join('\\n');
  _download(new Blob([csv], {{type:'text/csv'}}), '{stem}_peaks.csv');
}}

// ── Excel export (SheetJS) ──
function exportExcel() {{
  if (typeof XLSX === 'undefined') {{ alert('SheetJS not loaded'); return; }}
  const wb = XLSX.utils.book_new();
  const sheets = [
    ['Before Peaks',  FTIR_DATA.before_peaks],
    ['Before Runs',   FTIR_DATA.before_runs],
  ];
  {'sheets.push(["After Peaks", FTIR_DATA.after_peaks], ["After Runs", FTIR_DATA.after_runs], ["Delta", FTIR_DATA.delta], ["Toxicity", FTIR_DATA.toxicity]);' if mode2 else ''}
  sheets.forEach(([name, data]) => {{
    if (data && data.length) XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(data), name);
  }});
  XLSX.writeFile(wb, '{stem}.xlsx');
}}

function _download(blob, name) {{
  const a = Object.assign(document.createElement('a'), {{
    href: URL.createObjectURL(blob), download: name
  }});
  a.click(); URL.revokeObjectURL(a.href);
}}

// ── nav active on scroll ──
const _sections = document.querySelectorAll('section[id]');
const _links    = document.querySelectorAll('.topnav a');
const _obs = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (e.isIntersecting)
      _links.forEach(l => l.classList.toggle('active',
        l.getAttribute('href') === '#' + e.target.id));
  }});
}}, {{rootMargin: '-20% 0px -70% 0px'}});
_sections.forEach(s => _obs.observe(s));
</script>"""


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    if not args.before and not args.after:
        sys.exit("ERROR: provide at least --before or --after.\n"
                 "Run with --help for usage examples.")

    print("FTIR Report Generator")
    print("─" * 40)

    before_res = after_res = diff = None

    if args.before:
        runs = _load_path(args.before, "Before")
        before_res = run_analysis(runs, label="Before")
        print(f"  Before: {len(before_res['all_df'])} peaks, "
              f"{len(before_res['highly_consistent'])} consistent")

    if args.after:
        runs = _load_path(args.after, "After")
        after_res = run_analysis(runs, label="After")
        print(f"  After:  {len(after_res['all_df'])} peaks, "
              f"{len(after_res['highly_consistent'])} consistent")

    if after_res and not before_res:
        # After-only Mode 1: treat it as the primary result
        before_res = after_res
        after_res  = None

    if before_res and after_res:
        diff = compare(before_res, after_res)
        print(f"  Verdict: {diff['verdict']}  "
              f"(score {diff['toxicity_score']}/{diff['toxicity_max']})")

    print(f"\nBuilding HTML report…")
    html = build_html(before_res, after_res, diff)

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    size_kb = out.stat().st_size // 1024
    print(f"✅  Written: {out}  ({size_kb} KB)")
    print(f"\nPublish freely (no server needed):")
    print(f"  GitHub Pages : push {out.name} → enable Pages → public URL")
    print(f"  Netlify Drop : drag & drop at app.netlify.com/drop")


if __name__ == "__main__":
    main()
