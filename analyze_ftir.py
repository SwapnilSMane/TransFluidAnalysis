"""
FTIR Analysis of Transplant Fluid (Before Transplant)
Generates a standalone interactive HTML report.
"""

import pandas as pd
import numpy as np
import openpyxl
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from collections import defaultdict

# ─────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────
EXCEL_PATH = "/Users/swapnilmane/Documents/Projects/Transplant-Fluid/MASTER SHEET.xlsx"
OUTPUT_HTML = "/Users/swapnilmane/Documents/Projects/Transplant-Fluid/ftir_report.html"

RUN_DEFS = [
    (1,  "RUN 1"),  (7,  "RUN 3"),  (10, "RUN 4"),
    (13, "RUN 5"),  (16, "RUN 6"),  (19, "RUN 7"),
    (22, "RUN 8"),  (25, "RUN 9"),  (28, "RUN 10"),
]

def load_runs(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    runs = {}
    for col, name in RUN_DEFS:
        peaks = []
        for row in ws.iter_rows(min_row=3, min_col=col, max_col=col + 1, values_only=True):
            if row[0] is not None and isinstance(row[0], (int, float)):
                peaks.append({
                    "wavenumber": float(row[0]),
                    "intensity": float(row[1]) if row[1] is not None else 0.0,
                })
        runs[name] = pd.DataFrame(peaks)
    return runs

runs = load_runs(EXCEL_PATH)

# ─────────────────────────────────────────────
# 2. IR PEAK ASSIGNMENT TABLE
# Based on:
#   - UCSC IR table (IR-Table-1.pdf)
#   - Colthup, Daly & Wiberley "Introduction to IR and Raman Spectroscopy"
#   - Movasaghi et al. (2008) Appl. Spectrosc. Rev. 43:134-179 (biofluid FTIR)
#   - Stuart "Biological Applications of Infrared Spectroscopy" (1997)
# ─────────────────────────────────────────────
IR_TABLE = [
    # (low, high, functional_group, bond, vibration_type, compound_class, biological_relevance)
    (3600, 3700, "Alcohol / Water",          "O–H",    "stretch (free)",           "Alcohols, water",                    "Free hydroxyl groups, trace water"),
    (3400, 3600, "Alcohol / Carbohydrate",   "O–H",    "stretch (H-bonded)",       "Alcohols, sugars, water",            "Glucose, raffinose, HES (preservation solutes)"),
    (3300, 3500, "Amine / Amide",            "N–H",    "stretch",                  "Primary/secondary amines, amides",   "Proteins, amino acids (glutathione, adenosine)"),
    (3200, 3400, "Water / Carbohydrate",     "O–H",    "stretch (broad, H-bonded)","Water, polysaccharides",             "Aqueous matrix, HES backbone"),
    (2950, 2970, "Alkyl (lipid)",            "C–H",    "asym. stretch –CH₃",       "Lipids, fatty acids, proteins",      "Lipid membrane fragments"),
    (2910, 2935, "Alkyl (lipid)",            "C–H",    "asym. stretch –CH₂–",      "Lipids, fatty acids",                "Phospholipid acyl chains"),
    (2855, 2875, "Alkyl (lipid)",            "C–H",    "sym. stretch –CH₂–",       "Lipids, fatty acids",                "Phospholipid acyl chains (toxicity marker if elevated)"),
    (2830, 2860, "Alkyl",                    "C–H",    "sym. stretch –CH₃",        "Methyl-bearing molecules",           "Various metabolites"),
    (2500, 2700, "Carboxylic acid",          "O–H",    "stretch (very broad)",     "Carboxylic acids",                   "Organic acids, metabolic byproducts"),
    (2100, 2280, "Nitrile / Isocyanate",     "C≡N / C=N=O", "stretch",             "Nitriles, isocyanates",              "Rare in normal fluid; toxicity indicator if present"),
    (1870, 1900, "Anhydride / Overtone",     "C=O",    "asym. stretch",            "Anhydrides, overtones",              "Artefact or degradation product"),
    (1735, 1755, "Ester / Lipid",            "C=O",    "stretch",                  "Esters, triglycerides, phospholipids","Lipid esters — membrane integrity marker"),
    (1710, 1730, "Carboxylic acid / Aldehyde","C=O",   "stretch",                  "Carboxylic acids, aldehydes",        "Free fatty acids, aldehyde metabolites (oxidative stress)"),
    (1680, 1700, "Amide I (unordered)",      "C=O",    "stretch (unordered protein)","Proteins",                         "Denatured/unordered protein — ↑ in stressed fluid"),
    (1650, 1680, "Amide I (α-helix)",        "C=O",    "stretch (α-helix)",         "Proteins (albumin, enzymes)",        "Major protein secondary structure band"),
    (1620, 1650, "Amide I (β-sheet) / Water","C=O / H–O–H","stretch / bend",       "Proteins, water",                   "β-sheet proteins; water bending at ~1640 cm⁻¹"),
    (1590, 1620, "Aromatic / C=C",          "C=C",    "stretch",                   "Aromatics, purines",                 "Adenosine ring vibration, aromatic amino acids"),
    (1535, 1570, "Amide II",                 "N–H / C–N","bend + stretch",          "Proteins, peptides",                 "Coupled N-H bend/C-N stretch — protein content"),
    (1480, 1510, "Amide II / Aromatic",      "N–H / C=C","bend",                   "Proteins, aromatic rings",           "Secondary protein band"),
    (1445, 1480, "Lipid / Protein",          "C–H",    "scissoring –CH₂–",         "Lipids, aliphatic proteins",         "Fatty acid chain length indicator"),
    (1395, 1445, "Carboxylate",              "COO⁻",   "sym. stretch",              "Amino acids, fatty acid salts",      "Ionised carboxylate (amino acids, glutathione)"),
    (1365, 1395, "Alkyl / Nitrate",          "C–H / N–O","bending / stretch",       "tert-butyl, nitrates",              "Hydroxyethyl groups, inorganic nitrate"),
    (1300, 1365, "Amide III / CH",           "C–N / N–H","bend + stretch",          "Proteins",                          "Tertiary protein structure marker"),
    (1215, 1265, "Phospholipid / Amide III", "P=O / C–N","asym. stretch",           "Phospholipids, nucleic acids",       "Membrane phospholipids — integrity indicator"),
    (1140, 1215, "Carbohydrate",             "C–O",    "stretch",                   "Sugars, glycogen",                   "Glucose, raffinose, HES (C-O of C-OH groups)"),
    (1070, 1140, "Phosphate / Carbohydrate", "P–O / C–O–C","sym. stretch",          "Phosphate, sugars",                  "Phosphate buffer, glucose ring C-O-C"),
    (1020, 1070, "Carbohydrate",             "C–O–C",  "glycosidic stretch",        "Polysaccharides, monosaccharides",   "Raffinose, glucose, HES backbone — key preservation markers"),
    (970,  1020, "Phosphodiester / Sugar",   "C–O–P / C–OH","stretch",              "Nucleotides, sugars",               "Adenosine phosphate bonds"),
    (890,  970,  "Anomeric C–H / Phosphate", "=C–H / P–O","bend / stretch",         "Sugars (β-anomers), phosphate",     "Carbohydrate anomeric configuration"),
    (800,  890,  "Aromatic C–H / Silicone",  "=C–H",   "out-of-plane bend",         "Aromatics, Si–O (contaminant)",     "Adenine ring C-H; silicone contamination if very strong"),
    (700,  800,  "Aromatic / Alkene",        "=C–H",   "out-of-plane bend",         "Mono-subst. aromatics, alkenes",    "Aromatic amino acids (phenylalanine, tyrosine)"),
    (710,  730,  "Lipid (long chain)",       "(CH₂)ₙ", "rocking",                   "Long-chain fatty acids (n > 4)",    "Saturated fatty acid chains — membrane-derived lipids"),
    (600,  700,  "C–Cl / C–Br / Aromatic",  "C–X / C–H","stretch / bend",           "Halogenated compounds, aromatics",  "Possible chlorinated metabolites or contaminants"),
    (500,  600,  "Inorganic / Skeletal",     "M–O / P–O","bend",                    "Metal oxides, phosphate",           "Inorganic phosphate, metal salts (preservation buffer)"),
    (400,  500,  "Inorganic / Skeletal",     "M–L",    "stretch/bend",              "Mineral salts, metal-ligand",       "KH₂PO₄, MgSO₄ salts in preservation solution"),
]

IR_DF = pd.DataFrame(IR_TABLE, columns=[
    "wn_low", "wn_high", "functional_group", "bond",
    "vibration_type", "compound_class", "biological_relevance"
])

def assign_peak(wn):
    """Return the best matching IR assignment for a given wavenumber."""
    match = IR_DF[(IR_DF.wn_low <= wn) & (IR_DF.wn_high >= wn)]
    if match.empty:
        return ("Unassigned", "–", "–", "–", "–")
    row = match.iloc[0]
    return (row.functional_group, row.bond, row.vibration_type,
            row.compound_class, row.biological_relevance)

# Annotate each run
for name, df in runs.items():
    cols = df["wavenumber"].apply(lambda w: pd.Series(
        assign_peak(w),
        index=["functional_group", "bond", "vibration_type", "compound_class", "biological_relevance"]
    ))
    runs[name] = pd.concat([df, cols], axis=1)

# ─────────────────────────────────────────────
# 3. STATISTICS
# ─────────────────────────────────────────────
# Bin peaks into 10 cm⁻¹ windows for cross-run comparison
BIN_WIDTH = 10.0

def bin_wavenumber(wn):
    return round(wn / BIN_WIDTH) * BIN_WIDTH

all_peaks = []
for name, df in runs.items():
    for _, row in df.iterrows():
        all_peaks.append({
            "run": name,
            "wavenumber": row.wavenumber,
            "intensity": row.intensity,
            "bin": bin_wavenumber(row.wavenumber),
            "functional_group": row.functional_group,
            "bond": row.bond,
            "vibration_type": row.vibration_type,
            "compound_class": row.compound_class,
            "biological_relevance": row.biological_relevance,
        })

all_df = pd.DataFrame(all_peaks)

# Per-bin statistics
bin_stats = all_df.groupby("bin").agg(
    count=("intensity", "count"),
    mean_intensity=("intensity", "mean"),
    std_intensity=("intensity", "std"),
    min_intensity=("intensity", "min"),
    max_intensity=("intensity", "max"),
    functional_group=("functional_group", lambda x: x.mode()[0]),
    bond=("bond", lambda x: x.mode()[0]),
    vibration_type=("vibration_type", lambda x: x.mode()[0]),
    compound_class=("compound_class", lambda x: x.mode()[0]),
    biological_relevance=("biological_relevance", lambda x: x.mode()[0]),
).reset_index()

bin_stats["cv_pct"] = (bin_stats["std_intensity"] / bin_stats["mean_intensity"].replace(0, np.nan) * 100).round(1)
bin_stats["consistency"] = pd.cut(
    bin_stats["count"],
    bins=[0, 2, 5, 7, 9],
    labels=["Rare (1-2 runs)", "Moderate (3-5 runs)", "Common (6-7 runs)", "Highly Consistent (8-9 runs)"]
)
n_runs = len(runs)
bin_stats["present_in_pct"] = (bin_stats["count"] / n_runs * 100).round(0)

# Region summary
REGIONS = [
    (400,  700,  "Fingerprint / Inorganic"),
    (700,  900,  "Aromatic & Long-chain CH"),
    (900,  1300, "Carbohydrate / Phosphate"),
    (1300, 1500, "Protein CH / Carboxylate"),
    (1500, 1800, "Amide (Protein) / Lipid C=O"),
    (1800, 2800, "Overtone / Combination"),
    (2800, 3050, "C–H Stretch (Lipids)"),
    (3050, 3700, "O–H / N–H Stretch"),
]

def get_region(wn):
    for lo, hi, name in REGIONS:
        if lo <= wn < hi:
            return name
    return "Other"

all_df["region"] = all_df["wavenumber"].apply(get_region)
bin_stats["region"] = bin_stats["bin"].apply(get_region)

region_summary = all_df.groupby(["run", "region"]).agg(
    peak_count=("wavenumber", "count"),
    mean_intensity=("intensity", "mean"),
    total_intensity=("intensity", "sum"),
).reset_index()

# Per-run summary
run_summary = all_df.groupby("run").agg(
    n_peaks=("wavenumber", "count"),
    mean_intensity=("intensity", "mean"),
    max_intensity=("intensity", "max"),
    total_intensity=("intensity", "sum"),
).reset_index()

# Top peaks by mean intensity across runs
top_peaks = bin_stats.nlargest(20, "mean_intensity").copy()

# Consistency overview: bins present in all / most runs
highly_consistent = bin_stats[bin_stats["count"] >= 8].copy()

print(f"Total peaks across all runs: {len(all_df)}")
print(f"Unique 10cm⁻¹ bins occupied: {len(bin_stats)}")
print(f"Bins present in ≥8/9 runs: {len(highly_consistent)}")

# ─────────────────────────────────────────────
# 4. COLOUR PALETTE
# ─────────────────────────────────────────────
RUN_COLORS = px.colors.qualitative.Set2
RUN_NAMES = list(runs.keys())
COLOR_MAP = {name: RUN_COLORS[i % len(RUN_COLORS)] for i, name in enumerate(RUN_NAMES)}

REGION_COLORS = {
    "Fingerprint / Inorganic":    "#e74c3c",
    "Aromatic & Long-chain CH":   "#e67e22",
    "Carbohydrate / Phosphate":   "#f1c40f",
    "Protein CH / Carboxylate":   "#2ecc71",
    "Amide (Protein) / Lipid C=O":"#1abc9c",
    "Overtone / Combination":     "#3498db",
    "C–H Stretch (Lipids)":       "#9b59b6",
    "O–H / N–H Stretch":          "#e91e8c",
}

# ─────────────────────────────────────────────
# 5. FIGURES
# ─────────────────────────────────────────────

# Fig 1: Overlay spectral plot (all runs, wavenumber vs intensity)
def fig_spectral_overlay():
    fig = go.Figure()
    for name, df in runs.items():
        df_sorted = df.sort_values("wavenumber")
        fig.add_trace(go.Scatter(
            x=df_sorted["wavenumber"], y=df_sorted["intensity"],
            mode="lines+markers",
            name=name,
            line=dict(color=COLOR_MAP[name], width=1.2),
            marker=dict(size=4),
            hovertemplate=(
                "<b>" + name + "</b><br>"
                "Wavenumber: %{x:.1f} cm⁻¹<br>"
                "Intensity: %{y:.4f}<br>"
                "<extra></extra>"
            ),
        ))
    fig.update_layout(
        title="FTIR Spectral Overlay — All Runs (Before Transplant)",
        xaxis=dict(title="Wavenumber (cm⁻¹)", autorange="reversed"),
        yaxis_title="Absorbance / Intensity",
        legend_title="Run",
        hovermode="closest",
        template="plotly_white",
        height=500,
    )
    # Add region shading
    for lo, hi, label in REGIONS:
        fig.add_vrect(
            x0=lo, x1=hi,
            fillcolor=REGION_COLORS.get(label, "#aaa"),
            opacity=0.07, line_width=0,
            annotation_text=label if (hi - lo) > 200 else "",
            annotation_position="top left",
            annotation=dict(font_size=9, font_color="#555"),
        )
    return fig

# Fig 2: Mean ± std band plot
def fig_mean_band():
    bs = bin_stats.sort_values("bin")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.concat([bs["bin"], bs["bin"][::-1]]),
        y=pd.concat([bs["mean_intensity"] + bs["std_intensity"].fillna(0),
                     (bs["mean_intensity"] - bs["std_intensity"].fillna(0))[::-1]]),
        fill="toself", fillcolor="rgba(52,152,219,0.2)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=True, name="±1 SD",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=bs["bin"], y=bs["mean_intensity"],
        mode="lines", name="Mean Intensity",
        line=dict(color="#2980b9", width=2),
        hovertemplate=(
            "Bin: %{x:.0f} cm⁻¹<br>"
            "Mean: %{y:.4f}<br>"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Mean FTIR Spectrum ± 1 SD (Across All Runs)",
        xaxis=dict(title="Wavenumber (cm⁻¹)", autorange="reversed"),
        yaxis_title="Mean Absorbance",
        template="plotly_white",
        height=450,
    )
    return fig

# Fig 3: Heatmap — runs × wavenumber bins (intensity)
def fig_heatmap():
    pivot = all_df.pivot_table(
        index="run", columns="bin", values="intensity", aggfunc="mean"
    ).reindex(RUN_NAMES)
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Viridis",
        colorbar_title="Intensity",
        hovertemplate="Run: %{y}<br>Wavenumber bin: %{x} cm⁻¹<br>Intensity: %{z:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title="Intensity Heatmap: Runs × Wavenumber (10 cm⁻¹ bins)",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="Run",
        template="plotly_white",
        height=420,
    )
    return fig

# Fig 4: CV% heatmap (reproducibility)
def fig_cv_heatmap():
    bs_filtered = bin_stats[bin_stats["count"] >= 3].copy()
    fig = go.Figure(go.Bar(
        x=bs_filtered["bin"],
        y=bs_filtered["cv_pct"],
        marker=dict(
            color=bs_filtered["cv_pct"],
            colorscale="RdYlGn_r",
            colorbar_title="CV (%)",
        ),
        hovertemplate=(
            "Bin: %{x:.0f} cm⁻¹<br>"
            "CV: %{y:.1f}%<br>"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Coefficient of Variation (%) by Wavenumber Bin (runs present ≥ 3)",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="CV (%)",
        template="plotly_white",
        height=400,
    )
    return fig

# Fig 5: Peak count per run (bar)
def fig_peak_count():
    fig = go.Figure(go.Bar(
        x=run_summary["run"],
        y=run_summary["n_peaks"],
        marker_color=[COLOR_MAP[r] for r in run_summary["run"]],
        text=run_summary["n_peaks"],
        textposition="outside",
        hovertemplate="Run: %{x}<br>Peaks: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title="Number of Detected Peaks per Run",
        xaxis_title="Run",
        yaxis_title="Peak Count",
        template="plotly_white",
        height=380,
    )
    return fig

# Fig 6: Region distribution stacked bar
def fig_region_distribution():
    pivot = region_summary.pivot_table(
        index="run", columns="region", values="peak_count", fill_value=0
    ).reindex(RUN_NAMES)
    fig = go.Figure()
    for region in pivot.columns:
        fig.add_trace(go.Bar(
            name=region,
            x=pivot.index.tolist(),
            y=pivot[region].tolist(),
            marker_color=REGION_COLORS.get(region, "#aaa"),
            hovertemplate="Run: %{x}<br>Region: " + region + "<br>Peaks: %{y}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title="Peak Distribution Across Spectral Regions per Run",
        xaxis_title="Run",
        yaxis_title="Number of Peaks",
        template="plotly_white",
        legend_title="Spectral Region",
        height=450,
    )
    return fig

# Fig 7: Consistency scatter (how many runs each bin appears in)
def fig_consistency():
    bs = bin_stats.copy()
    bs["region"] = bs["bin"].apply(get_region)
    fig = go.Figure()
    for region in [r[2] for r in REGIONS]:
        sub = bs[bs["region"] == region]
        fig.add_trace(go.Scatter(
            x=sub["bin"], y=sub["count"],
            mode="markers",
            name=region,
            marker=dict(
                color=REGION_COLORS.get(region, "#aaa"),
                size=sub["mean_intensity"] * 80 + 5,
                opacity=0.7,
                sizemode="area",
            ),
            hovertemplate=(
                "Bin: %{x:.0f} cm⁻¹<br>"
                "Present in %{y} runs<br>"
                "<extra></extra>"
            ),
        ))
    fig.add_hline(y=8, line_dash="dash", line_color="green",
                  annotation_text="≥8/9 runs", annotation_position="right")
    fig.update_layout(
        title="Peak Consistency: Number of Runs Each Wavenumber Bin Appears In",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis=dict(title="# Runs (out of 9)", range=[0, 10]),
        template="plotly_white",
        legend_title="Spectral Region",
        height=480,
    )
    return fig

# Fig 8: Top 20 high-intensity peaks — annotated
def fig_top_peaks():
    tp = top_peaks.sort_values("bin")
    fig = go.Figure(go.Bar(
        x=tp["bin"].astype(str) + " cm⁻¹",
        y=tp["mean_intensity"],
        error_y=dict(type="data", array=tp["std_intensity"].fillna(0).tolist()),
        marker_color=tp["region"].map(REGION_COLORS).fillna("#aaa"),
        text=tp["functional_group"],
        textposition="outside",
        customdata=tp[["functional_group", "bond", "compound_class", "biological_relevance"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Mean intensity: %{y:.4f}<br>"
            "Group: %{customdata[0]}<br>"
            "Bond: %{customdata[1]}<br>"
            "Compound: %{customdata[2]}<br>"
            "Relevance: %{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Top 20 Most Intense Peaks (Mean ± SD across runs)",
        xaxis_title="Wavenumber Bin",
        yaxis_title="Mean Intensity",
        template="plotly_white",
        xaxis_tickangle=-45,
        height=480,
    )
    return fig

# Fig 9: Per-region mean intensity box plots
def fig_region_boxplot():
    fig = go.Figure()
    for region in [r[2] for r in REGIONS]:
        sub = all_df[all_df["region"] == region]
        if sub.empty:
            continue
        fig.add_trace(go.Box(
            y=sub["intensity"],
            name=region,
            marker_color=REGION_COLORS.get(region, "#aaa"),
            boxmean=True,
            hovertemplate="Region: " + region + "<br>Intensity: %{y:.4f}<extra></extra>",
        ))
    fig.update_layout(
        title="Intensity Distribution by Spectral Region",
        xaxis_title="Spectral Region",
        yaxis_title="Absorbance",
        template="plotly_white",
        xaxis_tickangle=-30,
        height=480,
        showlegend=False,
    )
    return fig

# ─────────────────────────────────────────────
# 6. BUILD HTML REPORT
# ─────────────────────────────────────────────
print("Building figures…")
f1 = fig_spectral_overlay()
f2 = fig_mean_band()
f3 = fig_heatmap()
f4 = fig_cv_heatmap()
f5 = fig_peak_count()
f6 = fig_region_distribution()
f7 = fig_consistency()
f8 = fig_top_peaks()
f9 = fig_region_boxplot()

def fig_to_div(fig, div_id):
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)

# Build the highlighted assignments table (consistent peaks)
def build_assignment_table():
    rows_html = ""
    for _, row in highly_consistent.sort_values("bin").iterrows():
        intensity_bar = min(int(row["mean_intensity"] * 500), 100)
        cv_color = "#27ae60" if row["cv_pct"] < 20 else ("#f39c12" if row["cv_pct"] < 50 else "#e74c3c")
        rows_html += f"""
        <tr>
          <td class="wn-cell">{row['bin']:.0f}</td>
          <td>{row['functional_group']}</td>
          <td><code>{row['bond']}</code></td>
          <td>{row['vibration_type']}</td>
          <td>{row['compound_class']}</td>
          <td class="bio-cell">{row['biological_relevance']}</td>
          <td>
            <div class="bar-wrap">
              <div class="bar-fill" style="width:{intensity_bar}%"></div>
              <span>{row['mean_intensity']:.4f}</span>
            </div>
          </td>
          <td style="color:{cv_color};font-weight:600">{row['cv_pct']:.1f}%</td>
          <td>{row['count']:.0f}/9</td>
        </tr>"""
    return rows_html

def build_full_table():
    rows_html = ""
    for _, row in bin_stats.sort_values("bin").iterrows():
        rows_html += f"""
        <tr>
          <td>{row['bin']:.0f}</td>
          <td>{row['functional_group']}</td>
          <td><code>{row['bond']}</code></td>
          <td>{row['vibration_type']}</td>
          <td>{row['compound_class']}</td>
          <td class="bio-cell">{row['biological_relevance']}</td>
          <td>{row['mean_intensity']:.4f}</td>
          <td>{row['cv_pct'] if pd.notna(row['cv_pct']) else '–'}</td>
          <td>{row['count']:.0f}/9</td>
        </tr>"""
    return rows_html

def build_run_cards():
    cards = ""
    for _, row in run_summary.iterrows():
        color = COLOR_MAP[row["run"]]
        cards += f"""
        <div class="run-card" style="border-top: 4px solid {color}">
          <div class="run-title">{row['run']}</div>
          <div class="run-stat"><span>Peaks</span><b>{row['n_peaks']}</b></div>
          <div class="run-stat"><span>Mean intensity</span><b>{row['mean_intensity']:.4f}</b></div>
          <div class="run-stat"><span>Max intensity</span><b>{row['max_intensity']:.4f}</b></div>
          <div class="run-stat"><span>Total intensity</span><b>{row['total_intensity']:.3f}</b></div>
        </div>"""
    return cards

print("Assembling HTML…")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FTIR Analysis — Transplant Fluid (Before Transplant)</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root {{
    --bg: #f5f7fa; --card: #ffffff; --text: #2c3e50;
    --accent: #2980b9; --accent2: #27ae60; --muted: #7f8c8d;
    --border: #dde1e7; --warn: #e67e22; --danger: #e74c3c;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); }}

  /* ── HEADER ── */
  .header {{
    background: linear-gradient(135deg, #1a2a4a 0%, #2980b9 100%);
    color: #fff; padding: 40px 48px 32px;
  }}
  .header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }}
  .header .subtitle {{ font-size: 1rem; opacity: .8; margin-top: 6px; }}
  .header .meta {{ display: flex; gap: 32px; margin-top: 20px; flex-wrap: wrap; }}
  .header .meta-item {{ display: flex; flex-direction: column; }}
  .header .meta-item span {{ font-size: .75rem; opacity: .7; text-transform: uppercase; letter-spacing: .5px; }}
  .header .meta-item b {{ font-size: 1.3rem; }}

  /* ── NAV ── */
  .nav {{ background: #fff; border-bottom: 1px solid var(--border);
         position: sticky; top: 0; z-index: 100; }}
  .nav ul {{ display: flex; list-style: none; padding: 0 48px; overflow-x: auto; }}
  .nav li a {{ display: block; padding: 14px 16px; font-size: .88rem; font-weight: 500;
               color: var(--muted); text-decoration: none; white-space: nowrap;
               border-bottom: 3px solid transparent; transition: .2s; }}
  .nav li a:hover, .nav li a.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  /* ── MAIN ── */
  main {{ max-width: 1400px; margin: 0 auto; padding: 32px 48px 64px; }}
  section {{ margin-bottom: 56px; }}
  section h2 {{ font-size: 1.35rem; font-weight: 700; color: var(--text);
                border-left: 4px solid var(--accent); padding-left: 12px; margin-bottom: 20px; }}
  section p.lead {{ font-size: .95rem; color: var(--muted); margin-bottom: 18px; line-height: 1.7; }}

  /* ── CARDS ── */
  .card {{ background: var(--card); border: 1px solid var(--border);
          border-radius: 10px; padding: 20px 24px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
               padding: 18px 20px; }}
  .kpi-card .kpi-label {{ font-size: .75rem; color: var(--muted); text-transform: uppercase;
                          letter-spacing: .5px; margin-bottom: 6px; }}
  .kpi-card .kpi-value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
  .kpi-card .kpi-sub {{ font-size: .8rem; color: var(--muted); margin-top: 2px; }}

  /* ── RUN CARDS ── */
  .run-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }}
  .run-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }}
  .run-title {{ font-weight: 700; font-size: 1rem; margin-bottom: 10px; }}
  .run-stat {{ display: flex; justify-content: space-between; font-size: .8rem;
               padding: 3px 0; border-bottom: 1px solid #f0f0f0; }}
  .run-stat span {{ color: var(--muted); }}

  /* ── TABLES ── */
  .table-wrap {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); }}
  table {{ width: 100%; border-collapse: collapse; font-size: .82rem; }}
  thead tr {{ background: #f0f4f8; }}
  th {{ padding: 10px 12px; text-align: left; font-weight: 600;
       font-size: .78rem; text-transform: uppercase; letter-spacing: .3px;
       color: var(--muted); border-bottom: 2px solid var(--border); white-space: nowrap; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
  tr:hover td {{ background: #f7faff; }}
  .wn-cell {{ font-weight: 700; color: var(--accent); }}
  .bio-cell {{ font-size: .78rem; color: var(--muted); max-width: 260px; }}
  code {{ background: #f0f4f8; padding: 2px 5px; border-radius: 3px;
         font-size: .8rem; color: #c0392b; }}
  .bar-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .bar-fill {{ height: 8px; border-radius: 4px; background: var(--accent); flex-shrink: 0; }}

  /* ── CALLOUT ── */
  .callout {{ border-left: 4px solid var(--warn); background: #fff8f0;
             padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 16px 0;
             font-size: .9rem; line-height: 1.6; }}
  .callout.info {{ border-color: var(--accent); background: #f0f7ff; }}
  .callout.success {{ border-color: var(--accent2); background: #f0fff4; }}

  /* ── PLOT GRID ── */
  .plot-2col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 900px) {{ .plot-2col {{ grid-template-columns: 1fr; }} }}
  .plot-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}

  /* ── FOOTER ── */
  footer {{ background: #fff; border-top: 1px solid var(--border);
           padding: 24px 48px; font-size: .82rem; color: var(--muted); }}
  footer a {{ color: var(--accent); }}
  .badge {{ display: inline-block; background: var(--accent); color: #fff;
           padding: 2px 8px; border-radius: 4px; font-size: .72rem; font-weight: 600;
           margin-left: 6px; }}
  .badge.warn {{ background: var(--warn); }}
  .badge.ok {{ background: var(--accent2); }}

  /* ── SEARCH/FILTER ── */
  .filter-row {{ display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }}
  .filter-row input, .filter-row select {{
    padding: 7px 12px; border: 1px solid var(--border); border-radius: 6px;
    font-size: .85rem; outline: none;
  }}
  .filter-row input:focus, .filter-row select:focus {{ border-color: var(--accent); }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <h1>FTIR Spectroscopic Analysis — Transplant Fluid</h1>
  <p class="subtitle">Before-transplant fluid characterisation &nbsp;|&nbsp; 9 runs &nbsp;|&nbsp; ~400–3900 cm⁻¹</p>
  <div class="meta">
    <div class="meta-item"><span>Total Peaks Detected</span><b>{len(all_df)}</b></div>
    <div class="meta-item"><span>Runs Analysed</span><b>{len(runs)}</b></div>
    <div class="meta-item"><span>Wavenumber Range</span><b>400 – 3900 cm⁻¹</b></div>
    <div class="meta-item"><span>Highly Consistent Peaks</span><b>{len(highly_consistent)}</b></div>
    <div class="meta-item"><span>Status</span><b>Before Transplant ✔</b></div>
  </div>
</div>

<!-- NAV -->
<nav class="nav">
  <ul>
    <li><a href="#overview">Overview</a></li>
    <li><a href="#spectra">Spectra</a></li>
    <li><a href="#assignments">Peak Assignments</a></li>
    <li><a href="#statistics">Statistics</a></li>
    <li><a href="#consistency">Reproducibility</a></li>
    <li><a href="#regions">Spectral Regions</a></li>
    <li><a href="#toxicity">Toxicity Markers</a></li>
    <li><a href="#full-table">Full Peak Table</a></li>
  </ul>
</nav>

<main>

<!-- ── OVERVIEW ── -->
<section id="overview">
  <h2>Overview</h2>
  <p class="lead">
    This report analyses the FTIR (Fourier-Transform Infrared) spectroscopic profiles of
    transplant preservation fluid <em>before</em> organ transplantation across 9 measurement runs.
    Each run captures detected peaks as (wavenumber, intensity) pairs spanning the mid-IR
    range (~400–3900 cm⁻¹). Peaks are mapped to functional groups, bond types, and biological
    compounds using established IR spectroscopy reference tables. The goal is to establish a
    comprehensive baseline that will be compared against post-transplant fluid measurements
    to detect changes indicative of toxicity, organ stress, or biochemical deterioration.
  </p>

  <div class="callout info">
    <strong>Objective:</strong> Characterise the pre-transplant fluid composition in detail.
    When post-transplant FTIR data becomes available, differences in amide bands (protein
    denaturation), lipid bands (membrane damage), and carbohydrate bands (metabolic changes)
    will serve as toxicity/viability indicators.
  </div>

  <div class="kpi-row" style="margin-top:24px">
    <div class="kpi-card">
      <div class="kpi-label">Total Peaks</div>
      <div class="kpi-value">{len(all_df)}</div>
      <div class="kpi-sub">across 9 runs</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Avg peaks / run</div>
      <div class="kpi-value">{len(all_df)//len(runs)}</div>
      <div class="kpi-sub">range {run_summary.n_peaks.min()}–{run_summary.n_peaks.max()}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Consistent peaks</div>
      <div class="kpi-value">{len(highly_consistent)}</div>
      <div class="kpi-sub">present in ≥8/9 runs</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Wavenumber range</div>
      <div class="kpi-value">~3500</div>
      <div class="kpi-sub">cm⁻¹ span</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Max mean intensity</div>
      <div class="kpi-value">{bin_stats.mean_intensity.max():.3f}</div>
      <div class="kpi-sub">at ~{bin_stats.loc[bin_stats.mean_intensity.idxmax(), 'bin']:.0f} cm⁻¹</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Spectral regions</div>
      <div class="kpi-value">8</div>
      <div class="kpi-sub">defined zones</div>
    </div>
  </div>

  <h3 style="font-size:1rem;font-weight:600;margin:24px 0 14px">Per-Run Summary</h3>
  <div class="run-cards">
    {build_run_cards()}
  </div>
</section>

<!-- ── SPECTRA ── -->
<section id="spectra">
  <h2>FTIR Spectra</h2>
  <p class="lead">
    All 9 runs overlaid on the same axes. Background regions are colour-coded by spectral zone.
    Hover over any data point to see its exact wavenumber and intensity. The x-axis is reversed
    (high → low wavenumber) following FTIR convention.
  </p>
  <div class="card">{fig_to_div(f1, "fig1")}</div>
  <div style="margin-top:20px" class="card">{fig_to_div(f2, "fig2")}</div>
</section>

<!-- ── PEAK ASSIGNMENTS ── -->
<section id="assignments">
  <h2>Peak Assignments — Highly Consistent Peaks (≥ 8/9 runs)</h2>
  <p class="lead">
    Peaks appearing in at least 8 of the 9 runs represent the most reproducible spectral
    features of the pre-transplant fluid. Each 10 cm⁻¹ bin is mapped to its functional group,
    bond type, and biological relevance using standard mid-IR reference tables (Colthup et al.;
    Movasaghi et al. 2008 <em>Appl. Spectrosc. Rev.</em>).
  </p>

  <div class="callout success">
    <strong>{len(highly_consistent)} highly consistent peaks</strong> identified.
    These form the chemical fingerprint of the baseline (pre-transplant) preservation fluid.
    Changes to these peaks post-transplant will be the primary indicators of organ-induced
    biochemical alterations or toxicity.
  </div>

  <div class="table-wrap">
    <table id="assignments-table">
      <thead>
        <tr>
          <th>Wavenumber (cm⁻¹)</th>
          <th>Functional Group</th>
          <th>Bond</th>
          <th>Vibration Type</th>
          <th>Compound Class</th>
          <th>Biological Relevance</th>
          <th>Mean Intensity</th>
          <th>CV%</th>
          <th>Runs</th>
        </tr>
      </thead>
      <tbody>
        {build_assignment_table()}
      </tbody>
    </table>
  </div>
</section>

<!-- ── STATISTICS ── -->
<section id="statistics">
  <h2>Statistical Analysis</h2>
  <p class="lead">
    Intensity distributions, per-run peak counts, and the top 20 most intense peaks
    (mean ± standard deviation across runs).
  </p>
  <div class="plot-2col">
    <div class="plot-card">{fig_to_div(f5, "fig5")}</div>
    <div class="plot-card">{fig_to_div(f9, "fig9")}</div>
  </div>
  <div style="margin-top:20px" class="card">{fig_to_div(f8, "fig8")}</div>

  <div class="callout" style="margin-top:20px">
    <strong>Highest-intensity region:</strong> The O–H / N–H stretch region (3200–3600 cm⁻¹)
    typically dominates due to the aqueous matrix. The carbohydrate / phosphate region
    (900–1300 cm⁻¹) is next highest, reflecting glucose, raffinose, and phosphate buffers
    in preservation solutions. Amide bands (1500–1800 cm⁻¹) indicate protein content.
  </div>
</section>

<!-- ── CONSISTENCY / REPRODUCIBILITY ── -->
<section id="consistency">
  <h2>Reproducibility &amp; Consistency</h2>
  <p class="lead">
    The heatmap shows intensity across all runs and wavenumber bins. The CV% chart highlights
    which spectral regions are reproducible (low CV) versus variable (high CV) — a key
    consideration when comparing pre- and post-transplant spectra.
  </p>
  <div class="card">{fig_to_div(f3, "fig3")}</div>
  <div style="margin-top:20px" class="card">{fig_to_div(f7, "fig7")}</div>
  <div style="margin-top:20px" class="card">{fig_to_div(f4, "fig4")}</div>

  <div class="callout">
    <strong>Interpretation of CV%:</strong>
    CV &lt; 20% (green) = highly reproducible peak &rarr; reliable for comparison.
    CV 20–50% (amber) = moderately variable &rarr; use cautiously.
    CV &gt; 50% (red) = high variability &rarr; may reflect real biological variation
    or instrument noise; flag for further investigation.
  </div>
</section>

<!-- ── SPECTRAL REGIONS ── -->
<section id="regions">
  <h2>Spectral Regions</h2>
  <p class="lead">
    The mid-IR spectrum is divided into 8 functional regions. Below is the peak-count
    distribution per run across these regions, followed by a reference guide to what
    each region represents in the context of transplant fluid.
  </p>
  <div class="card">{fig_to_div(f6, "fig6")}</div>

  <div style="margin-top:24px" class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Region</th>
          <th>Wavenumber (cm⁻¹)</th>
          <th>Key Assignments</th>
          <th>Biological Meaning in Transplant Fluid</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><b style="color:#e74c3c">Fingerprint / Inorganic</b></td><td>400–700</td>
          <td>Metal-ligand, P–O bend, C–Cl</td>
          <td>Inorganic salts (KH₂PO₄, MgSO₄) in preservation buffer; skeletal vibrations</td></tr>
        <tr><td><b style="color:#e67e22">Aromatic &amp; Long-chain CH</b></td><td>700–900</td>
          <td>(CH₂)ₙ rocking, aromatic C–H bend</td>
          <td>Long-chain fatty acids from cell membranes; adenine ring vibrations</td></tr>
        <tr><td><b style="color:#f1c40f">Carbohydrate / Phosphate</b></td><td>900–1300</td>
          <td>C–O–C glycosidic, P–O stretch, C–O</td>
          <td><strong>Primary preservation solute region</strong>: glucose, raffinose, HES, phosphate; largest functional zone</td></tr>
        <tr><td><b style="color:#2ecc71">Protein CH / Carboxylate</b></td><td>1300–1500</td>
          <td>Amide III, CH₂ scissor, COO⁻</td>
          <td>Protein side chains, amino acid carboxylates (glutathione); lipid chain bending</td></tr>
        <tr><td><b style="color:#1abc9c">Amide (Protein) / Lipid C=O</b></td><td>1500–1800</td>
          <td>Amide I (1650), Amide II (1550), ester C=O (1740)</td>
          <td><strong>Critical toxicity zone</strong>: protein secondary structure (amide I/II shifts indicate denaturation); ester C=O from lipid oxidation</td></tr>
        <tr><td><b style="color:#3498db">Overtone / Combination</b></td><td>1800–2800</td>
          <td>Overtones, CO₂, nitriles</td>
          <td>Usually weak; nitrile presence would indicate contamination or atypical chemistry</td></tr>
        <tr><td><b style="color:#9b59b6">C–H Stretch (Lipids)</b></td><td>2800–3050</td>
          <td>CH₂/CH₃ symmetric &amp; asymmetric stretch</td>
          <td>Lipid content from cell membrane fragments; elevated post-transplant may indicate cell lysis</td></tr>
        <tr><td><b style="color:#e91e8c">O–H / N–H Stretch</b></td><td>3050–3700</td>
          <td>O–H (water, alcohols), N–H (amines)</td>
          <td>Dominant aqueous peak; carbohydrate OH; protein N–H</td></tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ── TOXICITY MARKERS ── -->
<section id="toxicity">
  <h2>Toxicity &amp; Viability Marker Framework</h2>
  <p class="lead">
    This section defines the spectroscopic markers that will be monitored when
    post-transplant fluid data becomes available. Each marker is tied to specific
    wavenumber bands identified in the current baseline.
  </p>

  <div class="callout info">
    <strong>How to use this baseline:</strong> For each marker below, the <em>before</em>
    values from this report establish the reference. A statistically significant shift
    (ΔI or Δν) in the same band in the after-transplant spectra will indicate biochemical
    change. Recommended threshold: |ΔI| &gt; 2×SD of the baseline, or wavenumber shift &gt; 5 cm⁻¹.
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Marker</th>
          <th>Band (cm⁻¹)</th>
          <th>Baseline Assignment</th>
          <th>What a Change Means</th>
          <th>Toxicity Direction</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><b>Protein denaturation</b></td>
          <td>1650 (Amide I)</td>
          <td>α-helix C=O stretch</td>
          <td>Peak shift to ~1620–1630 cm⁻¹ → β-sheet / aggregation; loss of secondary structure</td>
          <td><span class="badge warn">↓ shift</span></td>
        </tr>
        <tr>
          <td><b>Protein content change</b></td>
          <td>1540–1560 (Amide II)</td>
          <td>N–H bend + C–N stretch</td>
          <td>Intensity ↑ = protein leakage from cells; ↓ = protein degradation</td>
          <td><span class="badge warn">↑ intensity</span></td>
        </tr>
        <tr>
          <td><b>Lipid oxidation / peroxidation</b></td>
          <td>1740 (ester C=O)</td>
          <td>Lipid ester carbonyl</td>
          <td>Intensity ↑ = oxidised lipids from membrane damage; new band ~1720 suggests aldehydes (oxidative stress)</td>
          <td><span class="badge warn">↑ intensity</span></td>
        </tr>
        <tr>
          <td><b>Cell membrane lysis</b></td>
          <td>2850 + 2920 (C–H)</td>
          <td>CH₂ sym./asym. stretch (lipids)</td>
          <td>Intensity ↑ post-transplant = cell lysis releasing membrane lipids into fluid</td>
          <td><span class="badge warn">↑ intensity</span></td>
        </tr>
        <tr>
          <td><b>Lipid:protein ratio</b></td>
          <td>2920 / 1650</td>
          <td>CH₂ / Amide I</td>
          <td>Ratio ↑ = relative lipid increase (membrane damage); ratio ↓ = protein increase (leakage)</td>
          <td><span class="badge warn">ratio change</span></td>
        </tr>
        <tr>
          <td><b>Preservation solute depletion</b></td>
          <td>1020–1080 (C–O–C)</td>
          <td>Glucose / raffinose / HES</td>
          <td>Intensity ↓ = consumption of sugars by metabolic activity or degradation of HES</td>
          <td><span class="badge ok">↓ intensity</span></td>
        </tr>
        <tr>
          <td><b>Phosphate changes</b></td>
          <td>1080–1100 (P–O)</td>
          <td>Phosphate symmetric stretch</td>
          <td>Shift or broadening → ionic strength change; ATP release from stressed cells</td>
          <td><span class="badge warn">shift</span></td>
        </tr>
        <tr>
          <td><b>Free fatty acid accumulation</b></td>
          <td>1710–1730 (C=O acid)</td>
          <td>Carboxylic acid C=O</td>
          <td>Intensity ↑ = free fatty acid release from membrane phospholipid hydrolysis (ischaemia marker)</td>
          <td><span class="badge warn">↑ intensity</span></td>
        </tr>
        <tr>
          <td><b>Nucleic acid / adenosine loss</b></td>
          <td>970 + 1080</td>
          <td>C–O–P / phosphodiester</td>
          <td>Intensity change → adenosine consumption or DNA/RNA release from necrotic cells</td>
          <td><span class="badge warn">↓ intensity</span></td>
        </tr>
        <tr>
          <td><b>Oxidative stress (aldehyde)</b></td>
          <td>~2720 (C–H of CHO)</td>
          <td>Aldehyde C–H stretch</td>
          <td>New peak appearance = lipid peroxidation aldehyde products (malondialdehyde, 4-HNE)</td>
          <td><span class="badge danger">new peak</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ── FULL PEAK TABLE ── -->
<section id="full-table">
  <h2>Full Peak Assignment Table (All Detected Bins)</h2>
  <p class="lead">
    Complete list of all {len(bin_stats)} wavenumber bins detected across runs, with IR assignments,
    mean intensity, CV%, and run count. Use the search and filter to explore.
  </p>
  <div class="filter-row">
    <input id="search-input" type="text" placeholder="Search wavenumber, functional group, compound…" style="flex:1;min-width:200px">
    <select id="cv-filter">
      <option value="">All CV%</option>
      <option value="low">Low CV (&lt; 20%)</option>
      <option value="med">Medium CV (20–50%)</option>
      <option value="high">High CV (&gt; 50%)</option>
    </select>
    <select id="runs-filter">
      <option value="">All run counts</option>
      <option value="8">Present in ≥ 8 runs</option>
      <option value="5">Present in ≥ 5 runs</option>
      <option value="1">Present in 1–2 runs (rare)</option>
    </select>
  </div>
  <div class="table-wrap">
    <table id="full-table-el">
      <thead>
        <tr>
          <th>Bin (cm⁻¹)</th>
          <th>Functional Group</th>
          <th>Bond</th>
          <th>Vibration Type</th>
          <th>Compound Class</th>
          <th>Biological Relevance</th>
          <th>Mean Intensity</th>
          <th>CV%</th>
          <th>Runs</th>
        </tr>
      </thead>
      <tbody id="full-table-body">
        {build_full_table()}
      </tbody>
    </table>
  </div>
</section>

</main>

<footer>
  <strong>FTIR Transplant Fluid Analysis Report</strong> &mdash;
  Generated with Python · Plotly · OpenPyXL &nbsp;|&nbsp;
  IR assignments based on Colthup, Daly &amp; Wiberley (1990);
  Movasaghi et al. <em>Appl. Spectrosc. Rev.</em> 43 (2008) 134–179;
  Stuart <em>Biological Applications of Infrared Spectroscopy</em> (1997). &nbsp;|&nbsp;
  <span style="color:#e74c3c">Before-transplant baseline only</span> — post-transplant comparison pending.
</footer>

<script>
// ── TABLE SEARCH/FILTER ──
const searchInput  = document.getElementById('search-input');
const cvFilter     = document.getElementById('cv-filter');
const runsFilter   = document.getElementById('runs-filter');
const tableBody    = document.getElementById('full-table-body');

function filterTable() {{
  const q   = searchInput.value.toLowerCase();
  const cv  = cvFilter.value;
  const rc  = runsFilter.value;
  const rows = tableBody.querySelectorAll('tr');
  rows.forEach(row => {{
    const cells = Array.from(row.querySelectorAll('td')).map(c => c.textContent.toLowerCase());
    const text  = cells.join(' ');
    const cvVal = parseFloat(cells[7]) || 0;
    const runs  = parseInt(cells[8]) || 0;

    let show = true;
    if (q && !text.includes(q)) show = false;
    if (cv === 'low'  && cvVal >= 20) show = false;
    if (cv === 'med'  && (cvVal < 20 || cvVal >= 50)) show = false;
    if (cv === 'high' && cvVal < 50)  show = false;
    if (rc === '8' && runs < 8) show = false;
    if (rc === '5' && runs < 5) show = false;
    if (rc === '1' && runs > 2) show = false;
    row.style.display = show ? '' : 'none';
  }});
}}

searchInput.addEventListener('input', filterTable);
cvFilter.addEventListener('change', filterTable);
runsFilter.addEventListener('change', filterTable);

// ── NAV ACTIVE STATE ──
const sections = document.querySelectorAll('section[id]');
const navLinks  = document.querySelectorAll('.nav a');
const observer  = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      navLinks.forEach(l => {{
        l.classList.toggle('active', l.getAttribute('href') === '#' + e.target.id);
      }});
    }}
  }});
}}, {{ rootMargin: '-20% 0px -70% 0px' }});
sections.forEach(s => observer.observe(s));
</script>
</body>
</html>"""

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅  Report written to: {OUTPUT_HTML}")
print(f"   Size: {len(html) / 1024:.0f} KB")
print("\nTo publish freely (no server needed):")
print("  1. GitHub Pages: push HTML to a repo → enable Pages → share URL")
print("  2. Netlify Drop: drag & drop at app.netlify.com/drop")
print("  3. Vercel: 'vercel --prod' on the folder")
