"""
Multi-format report export.
Returns bytes (or str for CSV/HTML) ready for st.download_button.
"""
from __future__ import annotations
import io
import datetime
import textwrap

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────────

def to_html(before: dict, after: dict | None, diff: dict | None,
            figures: dict) -> str:
    """Standalone interactive HTML (all Plotly charts + tables)."""
    import plotly.io as pio

    def fig_div(key):
        fig = figures.get(key)
        if fig is None:
            return ""
        return fig.to_html(full_html=False, include_plotlyjs=False,
                           div_id=key, config={"responsive": True})

    label = before["label"]
    mode2 = after is not None

    sections = _html_mode1_sections(before, figures, fig_div)
    if mode2:
        sections += _html_mode2_sections(before, after, diff, figures, fig_div)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    title = ("FTIR Before vs After Analysis" if mode2
             else f"FTIR Analysis — {label}")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root{{--bg:#f5f7fa;--card:#fff;--text:#2c3e50;--accent:#2980b9;--border:#dde1e7;--muted:#7f8c8d}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}}
.header{{background:linear-gradient(135deg,#1a2a4a,#2980b9);color:#fff;padding:36px 48px 28px}}
.header h1{{font-size:1.9rem;font-weight:700}}
.header .sub{{font-size:.95rem;opacity:.8;margin-top:6px}}
.header .meta{{display:flex;gap:28px;margin-top:18px;flex-wrap:wrap}}
.header .mi span{{font-size:.72rem;opacity:.7;text-transform:uppercase;letter-spacing:.5px}}
.header .mi b{{font-size:1.3rem;display:block}}
nav{{background:#fff;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}}
nav ul{{display:flex;list-style:none;padding:0 48px;overflow-x:auto}}
nav a{{display:block;padding:12px 14px;font-size:.85rem;font-weight:500;color:var(--muted);
       text-decoration:none;white-space:nowrap;border-bottom:3px solid transparent}}
nav a:hover{{color:var(--accent);border-bottom-color:var(--accent)}}
main{{max-width:1380px;margin:0 auto;padding:28px 48px 64px}}
section{{margin-bottom:52px}}
section h2{{font-size:1.3rem;font-weight:700;border-left:4px solid var(--accent);
            padding-left:10px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}}}
.tbl-wrap{{overflow-x:auto;border-radius:8px;border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
thead tr{{background:#f0f4f8}}
th{{padding:9px 11px;text-align:left;font-weight:600;font-size:.75rem;
    text-transform:uppercase;letter-spacing:.3px;color:var(--muted);
    border-bottom:2px solid var(--border);white-space:nowrap}}
td{{padding:7px 11px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
tr:hover td{{background:#f7faff}}
code{{background:#f0f4f8;padding:2px 5px;border-radius:3px;font-size:.78rem;color:#c0392b}}
.callout{{border-left:4px solid #f39c12;background:#fff8f0;padding:12px 16px;
          border-radius:0 8px 8px 0;margin:14px 0;font-size:.88rem;line-height:1.6}}
.callout.info{{border-color:var(--accent);background:#f0f7ff}}
.callout.ok{{border-color:#27ae60;background:#f0fff4}}
.badge{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.72rem;
        font-weight:600;color:#fff}}
.badge-low{{background:#27ae60}}.badge-mod{{background:#e67e22}}
.badge-high{{background:#e74c3c}}.badge-none{{background:#95a5a6}}
footer{{background:#fff;border-top:1px solid var(--border);padding:20px 48px;
        font-size:.8rem;color:var(--muted)}}
.fi{{display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
.fi input,.fi select{{padding:6px 10px;border:1px solid var(--border);
                       border-radius:6px;font-size:.82rem}}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <p class="sub">Generated {now} &nbsp;|&nbsp; FTIR Transplant Fluid Analyser</p>
  <div class="meta">
    <div class="mi"><span>Mode</span><b>{"Before vs After" if mode2 else "Single-side"}</b></div>
    <div class="mi"><span>Label</span><b>{label}</b></div>
    <div class="mi"><span>Runs ({label})</span><b>{before["n_runs"]}</b></div>
    {"<div class='mi'><span>Runs (After)</span><b>" + str(after["n_runs"]) + "</b></div>" if mode2 else ""}
    <div class="mi"><span>Total peaks ({label})</span><b>{len(before["all_df"])}</b></div>
    {"<div class='mi'><span>Verdict</span><b style='color:" + diff["verdict_color"] + "'>" + diff["verdict"] + "</b></div>" if mode2 else ""}
  </div>
</div>
<nav><ul>
  {_nav_links(mode2)}
</ul></nav>
<main>
{sections}
</main>
<footer>FTIR Transplant Fluid Analyser &nbsp;|&nbsp;
IR assignments: Colthup et al. (1990); Movasaghi et al. Appl.Spectrosc.Rev. 43 (2008)
</footer>
<script>
// table search
document.querySelectorAll('[data-search]').forEach(inp=>{{
  inp.addEventListener('input',()=>{{
    const q=inp.value.toLowerCase();
    const tb=document.getElementById(inp.dataset.search);
    tb.querySelectorAll('tr').forEach(r=>{{
      r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';
    }});
  }});
}});
</script>
</body></html>"""
    return html


def _nav_links(mode2: bool) -> str:
    links = [
        ("overview","Overview"),("spectra","Spectra"),
        ("assignments","Assignments"),("statistics","Statistics"),
        ("regions","Regions"),
    ]
    if mode2:
        links += [("comparison","Comparison"),("toxicity","Toxicity")]
    return "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in links)


def _html_mode1_sections(result: dict, figures: dict, fig_div) -> str:
    label = result["label"]
    bs = result["bin_stats"]
    rs = result["run_summary"]
    hc = result["highly_consistent"]

    kpis = f"""
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;margin-bottom:24px">
  {_kpi("Total peaks", len(result["all_df"]), "")}
  {_kpi("Runs", result["n_runs"], "")}
  {_kpi("Consistent peaks", len(hc), "≥80% runs")}
  {_kpi("Peak range", f"{result['all_df']['wavenumber'].min():.0f}–{result['all_df']['wavenumber'].max():.0f}", "cm⁻¹")}
  {_kpi("Max mean intensity", f"{bs['mean_intensity'].max():.3f}", f"at {bs.loc[bs['mean_intensity'].idxmax(),'bin']:.0f} cm⁻¹")}
</div>"""

    run_cards = "".join(
        f'<div class="card" style="padding:14px;border-top:4px solid #2980b9">'
        f'<b>{r.run}</b><br>'
        f'<small style="color:#888">{r.n_peaks} peaks &nbsp;|&nbsp; '
        f'mean {r.mean_intensity:.4f} &nbsp;|&nbsp; '
        f'max {r.max_intensity:.4f}</small></div>'
        for _, r in rs.iterrows()
    ) if not result["is_single"] else ""

    def _cv_color(cv):
        if pd.isna(cv): return "#888"
        return "#27ae60" if cv < 20 else ("#e67e22" if cv < 50 else "#e74c3c")

    def _cv_str(cv):
        return "–" if pd.isna(cv) else f"{cv:.1f}%"

    assignment_rows = "".join(
        "<tr>"
        f"<td><b style='color:#2980b9'>{r['bin']:.0f}</b></td>"
        f"<td>{r['functional_group']}</td><td><code>{r['bond']}</code></td>"
        f"<td>{r['vibration_type']}</td><td>{r['compound_class']}</td>"
        f"<td style='font-size:.75rem;color:#888;max-width:240px'>{r['biological_relevance']}</td>"
        f"<td>{r['mean_intensity']:.4f}</td>"
        f"<td style='color:{_cv_color(r['cv_pct'])}'>{_cv_str(r['cv_pct'])}</td>"
        f"<td>{r['count']:.0f}/{result['n_runs']}</td>"
        "</tr>"
        for _, r in hc.sort_values("bin").iterrows()
    )

    no_cv_note = ('<div class="callout info">CV% and consistency analyses are not applicable '
                  'for a single-run dataset.</div>') if result["is_single"] else ""

    return f"""
<section id="overview">
  <h2>Overview — {label}</h2>
  {kpis}
  {'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px">' + run_cards + '</div>' if run_cards else ''}
</section>

<section id="spectra">
  <h2>Spectra — {label}</h2>
  <div class="card">{fig_div("spectral_overlay")}</div>
  {"<div class='card' style='margin-top:18px'>" + fig_div("mean_band") + "</div>" if not result["is_single"] else ""}
</section>

<section id="assignments">
  <h2>Peak Assignments — Highly Consistent Peaks (≥80% runs)</h2>
  {no_cv_note if result["is_single"] else ""}
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Bin (cm⁻¹)</th><th>Functional Group</th><th>Bond</th>
        <th>Vibration</th><th>Compound Class</th><th>Biological Relevance</th>
        <th>Mean Int.</th><th>CV%</th><th>Runs</th>
      </tr></thead>
      <tbody>{assignment_rows}</tbody>
    </table>
  </div>
</section>

<section id="statistics">
  <h2>Statistics — {label}</h2>
  <div class="grid2">
    <div class="card">{fig_div("top_peaks_bar")}</div>
    <div class="card">{fig_div("region_boxplot")}</div>
  </div>
  {"<div class='card' style='margin-top:18px'>" + fig_div("peak_count_bar") + "</div>" if not result["is_single"] else ""}
  {"<div class='card' style='margin-top:18px'>" + fig_div("intensity_heatmap") + "</div>" if not result["is_single"] else ""}
  {"<div class='card' style='margin-top:18px'>" + fig_div("cv_chart") + "</div>" if not result["is_single"] else ""}
</section>

<section id="regions">
  <h2>Spectral Regions — {label}</h2>
  <div class="card">{fig_div("region_distribution")}</div>
  {"<div class='card' style='margin-top:18px'>" + fig_div("consistency_chart") + "</div>" if not result["is_single"] else ""}
</section>"""


def _html_mode2_sections(before: dict, after: dict, diff: dict,
                          figures: dict, fig_div) -> str:
    verdict = diff["verdict"]
    vcolor  = diff["verdict_color"]

    tox_rows = "".join(
        f"<tr><td><b>{r['marker']}</b></td><td>{r['band_label']}</td>"
        f"<td>{r['before_value']:.5f}</td><td>{r['after_value']:.5f}</td>"
        f"<td style='color:{'#e74c3c' if r['delta']>0 else '#2980b9'}'>{r['delta_pct']:+.1f}%</td>"
        f"<td><span class='badge badge-{r['concern'].lower()}'>{r['concern']}</span></td>"
        f"<td style='font-size:.75rem;color:#888'>{r['description']}</td></tr>"
        for _, r in diff["toxicity_df"].iterrows()
    )

    new_rows = "".join(
        f"<tr><td>{r['bin']:.0f}</td><td>{r['functional_group']}</td>"
        f"<td>{r['mean_after']:.4f}</td>"
        f"<td style='font-size:.75rem;color:#888'>{r['biological_relevance']}</td></tr>"
        for _, r in diff["new_peaks"].sort_values("mean_after", ascending=False).iterrows()
    ) or "<tr><td colspan='4' style='color:#888'>No new peaks detected</td></tr>"

    lost_rows = "".join(
        f"<tr><td>{r['bin']:.0f}</td><td>{r['functional_group']}</td>"
        f"<td>{r['mean_before']:.4f}</td>"
        f"<td style='font-size:.75rem;color:#888'>{r['biological_relevance']}</td></tr>"
        for _, r in diff["lost_peaks"].sort_values("mean_before", ascending=False).iterrows()
    ) or "<tr><td colspan='4' style='color:#888'>No lost peaks detected</td></tr>"

    return f"""
<section id="comparison">
  <h2>Before vs After — Spectral Comparison</h2>
  <div class="card">{fig_div("comparison_overlay")}</div>
  <div class="card" style="margin-top:18px">{fig_div("delta_spectrum")}</div>
  <div class="card" style="margin-top:18px">{fig_div("volcano_plot")}</div>
  <div class="card" style="margin-top:18px">{fig_div("region_comparison_bar")}</div>
  <div class="grid2" style="margin-top:18px">
    <div class="card">
      <div style="padding:14px 16px"><b>New Peaks (in After, absent in Before)</b></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Bin (cm⁻¹)</th><th>Group</th><th>Intensity (After)</th><th>Relevance</th></tr></thead>
        <tbody>{new_rows}</tbody>
      </table></div>
    </div>
    <div class="card">
      <div style="padding:14px 16px"><b>Lost Peaks (in Before, absent in After)</b></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Bin (cm⁻¹)</th><th>Group</th><th>Intensity (Before)</th><th>Relevance</th></tr></thead>
        <tbody>{lost_rows}</tbody>
      </table></div>
    </div>
  </div>
</section>

<section id="toxicity">
  <h2>Toxicity Analysis</h2>
  <div class="callout {'ok' if verdict=='Low' else ''}" style="border-color:{vcolor}">
    <strong>Overall Verdict: <span style="color:{vcolor};font-size:1.1em">{verdict}</span></strong>
    &nbsp;(score {diff['toxicity_score']}/{diff['toxicity_max']}, {diff['toxicity_pct']:.1f}%)
    <br>{diff['verdict_detail']}
  </div>
  <div class="card" style="margin-top:16px">{fig_div("toxicity_scorecard")}</div>
  <div class="tbl-wrap" style="margin-top:18px">
    <table>
      <thead><tr><th>Marker</th><th>Band</th><th>Before</th><th>After</th>
                 <th>Change</th><th>Concern</th><th>Interpretation</th></tr></thead>
      <tbody>{tox_rows}</tbody>
    </table>
  </div>
  <div class="card" style="margin-top:18px">{fig_div("new_lost_peaks")}</div>
</section>"""


def _kpi(label, value, sub):
    return (f'<div class="card" style="padding:16px">'
            f'<div style="font-size:.72rem;color:#888;text-transform:uppercase">{label}</div>'
            f'<div style="font-size:1.7rem;font-weight:700;color:#2980b9">{value}</div>'
            f'<div style="font-size:.78rem;color:#888">{sub}</div></div>')


# ─────────────────────────────────────────────────────────────
# PDF  (reportlab)
# ─────────────────────────────────────────────────────────────

def to_pdf(before: dict, after: dict | None, diff: dict | None,
           figures: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, Image, HRFlowable,
                                        PageBreak, KeepTogether)
        from reportlab.lib.units import cm
    except ImportError:
        return b"reportlab not installed. Run: pip install reportlab"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    h1  = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    h2  = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceAfter=6,
                         textColor=colors.HexColor("#2980b9"))
    h3  = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11, spaceAfter=4)
    body= ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=14)
    note= ParagraphStyle("Note", parent=styles["Normal"], fontSize=8,
                         textColor=colors.HexColor("#666666"), leading=12)

    label = before["label"]
    mode2 = after is not None
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    story = []
    story.append(Paragraph(
        f"FTIR Transplant Fluid Analysis — {'Before vs After' if mode2 else label}", h1))
    story.append(Paragraph(
        f"Generated: {now} &nbsp;|&nbsp; Runs ({label}): {before['n_runs']}", note))
    if mode2:
        vcolor = diff["verdict_color"].lstrip("#")
        story.append(Paragraph(
            f"<b>Verdict: <font color='#{vcolor}'>{diff['verdict']}</font></b> — "
            f"{diff['verdict_detail']}", body))
    story.append(HRFlowable(width="100%", spaceAfter=10))

    # --- figures as images ---
    fig_keys_mode1 = ["spectral_overlay", "mean_band", "top_peaks_bar",
                      "region_distribution", "region_boxplot",
                      "intensity_heatmap", "cv_chart", "consistency_chart"]
    fig_keys_mode2 = ["comparison_overlay", "delta_spectrum", "volcano_plot",
                      "region_comparison_bar", "toxicity_scorecard", "new_lost_peaks"]

    all_fig_keys = fig_keys_mode1 + (fig_keys_mode2 if mode2 else [])

    for key in all_fig_keys:
        fig = figures.get(key)
        if fig is None:
            continue
        try:
            img_bytes = fig.to_image(format="png", width=700, height=350, scale=1.5)
            img = Image(io.BytesIO(img_bytes), width=17*cm, height=8.5*cm)
            story.append(KeepTogether([img, Spacer(1, 0.3*cm)]))
        except Exception:
            story.append(Paragraph(f"[Chart: {key} — export unavailable]", note))

    # --- peak assignment table ---
    story.append(PageBreak())
    story.append(Paragraph("Peak Assignments (Consistent Peaks ≥80%)", h2))
    hc = before["highly_consistent"].sort_values("bin")
    tdata = [["Bin cm⁻¹","Functional Group","Bond","Compound Class","Mean Int.","CV%","Runs"]]
    for _, r in hc.iterrows():
        tdata.append([
            f"{r['bin']:.0f}",
            textwrap.shorten(str(r["functional_group"]), 30),
            str(r["bond"]),
            textwrap.shorten(str(r["compound_class"]), 28),
            f"{r['mean_intensity']:.4f}",
            f"{r['cv_pct']:.1f}%" if pd.notna(r["cv_pct"]) else "–",
            f"{r['count']:.0f}/{before['n_runs']}",
        ])
    t = Table(tdata, repeatRows=1, hAlign="LEFT",
              colWidths=[2*cm, 4.5*cm, 2.8*cm, 4.2*cm, 2*cm, 1.5*cm, 1.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2980b9")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTSIZE",   (0,0), (-1,-1), 7.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f7fa")]),
        ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#dde1e7")),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(t)

    if mode2:
        story.append(PageBreak())
        story.append(Paragraph("Toxicity Scorecard", h2))
        tox = diff["toxicity_df"]
        tdata2 = [["Marker","Band","Before","After","Δ%","Concern"]]
        for _, r in tox.iterrows():
            tdata2.append([
                textwrap.shorten(str(r["marker"]), 35),
                str(r["band_label"]),
                f"{r['before_value']:.5f}",
                f"{r['after_value']:.5f}",
                f"{r['delta_pct']:+.1f}%",
                str(r["concern"]),
            ])
        t2 = Table(tdata2, repeatRows=1, hAlign="LEFT",
                   colWidths=[5*cm, 3*cm, 2.2*cm, 2.2*cm, 1.5*cm, 2*cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2980b9")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f7fa")]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#dde1e7")),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))
        story.append(t2)

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# Excel (.xlsx)
# ─────────────────────────────────────────────────────────────

def to_excel(before: dict, after: dict | None, diff: dict | None) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book
        hdr_fmt = wb.add_format({"bold": True, "bg_color": "#2980b9",
                                  "font_color": "white", "border": 1})
        num_fmt = wb.add_format({"num_format": "0.00000"})
        pct_fmt = wb.add_format({"num_format": "0.0%"})

        def _write_sheet(df: pd.DataFrame, name: str):
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            for i, col in enumerate(df.columns):
                ws.write(0, i, col, hdr_fmt)
                ws.set_column(i, i, max(len(str(col)) + 2, 12))

        # Sheet 1: Run Summary
        _write_sheet(before["run_summary"], f"Run Summary ({before['label']})")

        # Sheet 2: Bin Statistics
        _write_sheet(before["bin_stats"][[
            "bin","functional_group","bond","vibration_type","compound_class",
            "biological_relevance","mean_intensity","std_intensity","cv_pct",
            "present_in_n","present_in_pct","consistency","region"
        ]], f"Peak Stats ({before['label']})")

        # Sheet 3: All raw peaks annotated
        _write_sheet(before["all_df"][[
            "run","wavenumber","intensity","bin","region",
            "functional_group","bond","vibration_type","compound_class","biological_relevance"
        ]], f"All Peaks ({before['label']})")

        if after is not None:
            _write_sheet(after["run_summary"], f"Run Summary ({after['label']})")
            _write_sheet(after["bin_stats"][[
                "bin","functional_group","bond","vibration_type","compound_class",
                "biological_relevance","mean_intensity","std_intensity","cv_pct",
                "present_in_n","present_in_pct","consistency","region"
            ]], f"Peak Stats ({after['label']})")
            _write_sheet(after["all_df"][[
                "run","wavenumber","intensity","bin","region",
                "functional_group","bond","vibration_type","compound_class","biological_relevance"
            ]], f"All Peaks ({after['label']})")

        if diff is not None:
            _write_sheet(diff["delta_df"][[
                "bin","functional_group","bond","region",
                "mean_before","mean_after","delta","delta_pct","significant","status",
                "biological_relevance"
            ]], "Delta Analysis")
            _write_sheet(diff["toxicity_df"][[
                "marker","band_label","before_value","after_value",
                "delta","delta_pct","concern","description"
            ]], "Toxicity Scorecard")
            if not diff["new_peaks"].empty:
                _write_sheet(diff["new_peaks"][["bin","functional_group","mean_after","biological_relevance"]],
                             "New Peaks")
            if not diff["lost_peaks"].empty:
                _write_sheet(diff["lost_peaks"][["bin","functional_group","mean_before","biological_relevance"]],
                             "Lost Peaks")

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────

def to_csv(before: dict, after: dict | None, diff: dict | None) -> bytes:
    parts = []
    parts.append("# FTIR Peak Assignment Table — " + before["label"])
    parts.append(before["bin_stats"][[
        "bin","functional_group","bond","vibration_type","compound_class",
        "biological_relevance","mean_intensity","std_intensity","cv_pct",
        "present_in_n","consistency","region"
    ]].to_csv(index=False))

    if diff is not None:
        parts.append("\n# Delta Analysis (After - Before)")
        parts.append(diff["delta_df"].to_csv(index=False))
        parts.append("\n# Toxicity Scorecard")
        parts.append(diff["toxicity_df"].to_csv(index=False))

    return "\n".join(parts).encode()


# ─────────────────────────────────────────────────────────────
# PowerPoint (.pptx)
# ─────────────────────────────────────────────────────────────

def to_pptx(before: dict, after: dict | None, diff: dict | None,
            figures: dict) -> bytes:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
    except ImportError:
        return b"python-pptx not installed. Run: pip install python-pptx"

    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)

    blank = prs.slide_layouts[6]
    title_layout = prs.slide_layouts[0]

    def _add_title_slide():
        sl = prs.slides.add_slide(title_layout)
        sl.shapes.title.text = ("FTIR Before vs After Analysis"
                                 if after else f"FTIR Analysis — {before['label']}")
        sl.placeholders[1].text = (
            f"Generated: {datetime.datetime.now():%Y-%m-%d}\n"
            f"Runs ({before['label']}): {before['n_runs']}"
            + (f"\nVerdict: {diff['verdict']}" if diff else "")
        )

    def _add_chart_slide(key: str, title_text: str):
        fig = figures.get(key)
        if fig is None:
            return
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=600, scale=1.5)
        except Exception:
            return
        sl = prs.slides.add_slide(blank)
        txb = sl.shapes.add_textbox(Inches(0.3), Inches(0.1), Inches(12), Inches(0.5))
        tf  = txb.text_frame
        tf.text = title_text
        tf.paragraphs[0].runs[0].font.size = Pt(14)
        tf.paragraphs[0].runs[0].font.bold = True
        tf.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x29, 0x80, 0xB9)
        sl.shapes.add_picture(io.BytesIO(img_bytes),
                               Inches(0.3), Inches(0.7), Inches(12.7), Inches(6.5))

    _add_title_slide()

    chart_plan = [
        ("spectral_overlay",    f"Spectral {'Overlay' if not before['is_single'] else 'Plot'} — {before['label']}"),
        ("mean_band",           f"Mean ± SD Spectrum — {before['label']}"),
        ("top_peaks_bar",       f"Top 20 Most Intense Peaks — {before['label']}"),
        ("region_distribution", f"Peak Distribution by Region — {before['label']}"),
        ("region_boxplot",      f"Intensity Distribution by Region — {before['label']}"),
        ("intensity_heatmap",   "Intensity Heatmap — All Runs"),
        ("cv_chart",            "Reproducibility — CV% per Bin"),
        ("consistency_chart",   "Peak Consistency across Runs"),
    ]
    if after:
        chart_plan += [
            ("comparison_overlay",    "Before vs After — Mean Spectrum Comparison"),
            ("delta_spectrum",        "Delta Spectrum — After minus Before"),
            ("volcano_plot",          "Change Profile — Δ% per Bin"),
            ("region_comparison_bar", "Mean Intensity per Region — Before vs After"),
            ("toxicity_scorecard",    "Toxicity Marker Scorecard"),
            ("new_lost_peaks",        "New and Lost Peaks"),
        ]

    for key, title_text in chart_plan:
        _add_chart_slide(key, title_text)

    if diff:
        sl = prs.slides.add_slide(blank)
        txb = sl.shapes.add_textbox(Inches(0.3), Inches(0.1), Inches(12), Inches(0.5))
        tf  = txb.text_frame
        tf.text = f"Overall Toxicity Verdict: {diff['verdict']}"
        tf.paragraphs[0].runs[0].font.size = Pt(20)
        tf.paragraphs[0].runs[0].font.bold = True
        col = diff["verdict_color"].lstrip("#")
        tf.paragraphs[0].runs[0].font.color.rgb = RGBColor(
            int(col[0:2],16), int(col[2:4],16), int(col[4:6],16))
        txb2 = sl.shapes.add_textbox(Inches(0.3), Inches(0.8), Inches(12), Inches(5))
        tf2  = txb2.text_frame
        tf2.word_wrap = True
        tf2.text = (f"Score: {diff['toxicity_score']}/{diff['toxicity_max']} "
                    f"({diff['toxicity_pct']:.1f}%)\n\n"
                    + diff["verdict_detail"] + "\n\nMarker Summary:\n"
                    + "\n".join(f"  • {r['marker']}: {r['concern']}"
                                for _, r in diff["toxicity_df"].iterrows()))
        tf2.paragraphs[0].runs[0].font.size = Pt(12)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# Word (.docx)
# ─────────────────────────────────────────────────────────────

def to_docx(before: dict, after: dict | None, diff: dict | None,
            figures: dict) -> bytes:
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        return b"python-docx not installed. Run: pip install python-docx"

    doc = Document()
    label = before["label"]
    mode2 = after is not None
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Title
    t = doc.add_heading(
        "FTIR Before vs After Analysis" if mode2 else f"FTIR Analysis — {label}", 0)
    doc.add_paragraph(f"Generated: {now}  |  Runs ({label}): {before['n_runs']}")
    if mode2:
        p = doc.add_paragraph()
        run = p.add_run(f"Overall Verdict: {diff['verdict']}")
        run.bold = True
        col = diff["verdict_color"].lstrip("#")
        run.font.color.rgb = RGBColor(int(col[0:2],16), int(col[2:4],16), int(col[4:6],16))
        doc.add_paragraph(diff["verdict_detail"])
    doc.add_page_break()

    def _add_fig(doc, key, caption):
        fig = figures.get(key)
        if fig is None:
            return
        try:
            img_bytes = fig.to_image(format="png", width=900, height=450, scale=1.5)
            doc.add_picture(io.BytesIO(img_bytes), width=Inches(6.2))
            doc.add_paragraph(caption).alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            doc.add_paragraph(f"[Chart: {key} — export unavailable]")

    # Mode 1 sections
    doc.add_heading(f"1. Spectral Analysis — {label}", 1)
    _add_fig(doc, "spectral_overlay", f"Figure 1 — Spectral {'Overlay' if not before['is_single'] else 'Plot'}")
    if not before["is_single"]:
        _add_fig(doc, "mean_band", f"Figure 2 — Mean ± SD Spectrum")

    doc.add_heading("2. Peak Assignments (≥80% runs)", 1)
    hc = before["highly_consistent"].sort_values("bin")
    tbl = doc.add_table(rows=1, cols=6)
    tbl.style = "Light Shading Accent 1"
    hdr = tbl.rows[0].cells
    for i, h in enumerate(["Bin cm⁻¹","Functional Group","Bond","Compound Class","Mean Int.","Concern"]):
        hdr[i].text = h
    for _, r in hc.iterrows():
        row = tbl.add_row().cells
        row[0].text = f"{r['bin']:.0f}"
        row[1].text = str(r["functional_group"])[:30]
        row[2].text = str(r["bond"])
        row[3].text = str(r["compound_class"])[:28]
        row[4].text = f"{r['mean_intensity']:.4f}"
        row[5].text = f"CV {r['cv_pct']:.1f}%" if pd.notna(r["cv_pct"]) else "–"

    doc.add_heading("3. Statistics", 1)
    _add_fig(doc, "top_peaks_bar", "Figure — Top 20 Most Intense Peaks")
    _add_fig(doc, "region_distribution", "Figure — Peak Distribution by Region")
    _add_fig(doc, "region_boxplot", "Figure — Intensity Distribution by Region")
    if not before["is_single"]:
        _add_fig(doc, "intensity_heatmap", "Figure — Intensity Heatmap")
        _add_fig(doc, "cv_chart", "Figure — Reproducibility CV%")
        _add_fig(doc, "consistency_chart", "Figure — Peak Consistency")

    if mode2:
        doc.add_page_break()
        doc.add_heading("4. Before vs After Comparison", 1)
        _add_fig(doc, "comparison_overlay",    "Figure — Mean Spectrum Comparison")
        _add_fig(doc, "delta_spectrum",        "Figure — Delta Spectrum")
        _add_fig(doc, "volcano_plot",          "Figure — Change Profile")
        _add_fig(doc, "region_comparison_bar", "Figure — Region Comparison")

        doc.add_heading("5. Toxicity Analysis", 1)
        _add_fig(doc, "toxicity_scorecard", "Figure — Toxicity Scorecard")

        tbl2 = doc.add_table(rows=1, cols=6)
        tbl2.style = "Light Shading Accent 1"
        hdr2 = tbl2.rows[0].cells
        for i, h in enumerate(["Marker","Band","Before","After","Δ%","Concern"]):
            hdr2[i].text = h
        for _, r in diff["toxicity_df"].iterrows():
            row = tbl2.add_row().cells
            row[0].text = str(r["marker"])[:35]
            row[1].text = str(r["band_label"])
            row[2].text = f"{r['before_value']:.5f}"
            row[3].text = f"{r['after_value']:.5f}"
            row[4].text = f"{r['delta_pct']:+.1f}%"
            row[5].text = str(r["concern"])

        _add_fig(doc, "new_lost_peaks", "Figure — New and Lost Peaks")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
