"""
All Plotly figures for Mode 1 (single-side) and Mode 2 (comparison).
Each function returns a go.Figure.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .assignments import REGIONS, REGION_COLORS


# ════════════════════════════════════════════
#  MODE 1 — Single-side charts
# ════════════════════════════════════════════

def spectral_overlay(result: dict) -> go.Figure:
    """All runs overlaid. Single run: simple line plot."""
    fig = go.Figure()
    for name, df in result["annotated"].items():
        df_s = df.sort_values("wavenumber")
        fig.add_trace(go.Scatter(
            x=df_s["wavenumber"], y=df_s["intensity"],
            mode="lines+markers", name=name,
            line=dict(color=result["color_map"].get(name, "#333"), width=1.5),
            marker=dict(size=3),
            hovertemplate=(
                f"<b>{name}</b><br>"
                "Wavenumber: %{x:.1f} cm⁻¹<br>"
                "Intensity: %{y:.4f}<br>"
                "<extra></extra>"
            ),
        ))
    _add_region_shading(fig)
    title = (
        f"FTIR Spectrum — {result['label']}"
        if result["is_single"]
        else f"FTIR Spectral Overlay — {result['label']} ({result['n_runs']} runs)"
    )
    fig.update_layout(
        title=title,
        xaxis=dict(title="Wavenumber (cm⁻¹)", autorange="reversed"),
        yaxis_title="Absorbance / Intensity",
        template="plotly_white", height=480,
        legend_title="Run",
    )
    return fig


def mean_band(result: dict) -> go.Figure | None:
    """Mean ± SD band. Skipped for single run."""
    if result["is_single"]:
        return None
    bs = result["bin_stats"].sort_values("bin")
    upper = bs["mean_intensity"] + bs["std_intensity"].fillna(0)
    lower = (bs["mean_intensity"] - bs["std_intensity"].fillna(0)).clip(lower=0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.concat([bs["bin"], bs["bin"][::-1]]),
        y=pd.concat([upper, lower[::-1]]),
        fill="toself", fillcolor="rgba(52,152,219,0.15)",
        line=dict(color="rgba(0,0,0,0)"),
        name="±1 SD", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=bs["bin"], y=bs["mean_intensity"],
        mode="lines", name="Mean",
        line=dict(color="#2980b9", width=2),
        hovertemplate="Bin: %{x:.0f} cm⁻¹<br>Mean: %{y:.4f}<extra></extra>",
    ))
    _add_region_shading(fig)
    fig.update_layout(
        title=f"Mean Spectrum ± 1 SD — {result['label']}",
        xaxis=dict(title="Wavenumber (cm⁻¹)", autorange="reversed"),
        yaxis_title="Mean Absorbance",
        template="plotly_white", height=430,
    )
    return fig


def intensity_heatmap(result: dict) -> go.Figure | None:
    """Runs × wavenumber heatmap. Skipped for single run."""
    if result["is_single"]:
        return None
    pivot = result["all_df"].pivot_table(
        index="run", columns="bin", values="intensity", aggfunc="mean"
    ).reindex(result["run_names"])
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="Viridis", colorbar_title="Intensity",
        hovertemplate="Run: %{y}<br>Bin: %{x} cm⁻¹<br>Intensity: %{z:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Intensity Heatmap — {result['label']}",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="Run", template="plotly_white", height=400,
    )
    return fig


def cv_chart(result: dict) -> go.Figure | None:
    """CV% by bin. Skipped for single run."""
    if result["is_single"]:
        return None
    bs = result["bin_stats"][result["bin_stats"]["count"] >= 2].copy()
    fig = go.Figure(go.Bar(
        x=bs["bin"], y=bs["cv_pct"],
        marker=dict(color=bs["cv_pct"], colorscale="RdYlGn_r", colorbar_title="CV (%)"),
        hovertemplate="Bin: %{x:.0f} cm⁻¹<br>CV: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=f"Reproducibility — CV% per Wavenumber Bin ({result['label']})",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="CV (%)", template="plotly_white", height=380,
    )
    return fig


def consistency_chart(result: dict) -> go.Figure | None:
    """Scatter: how many runs each bin appears in. Skipped for single run."""
    if result["is_single"]:
        return None
    bs = result["bin_stats"].copy()
    fig = go.Figure()
    for region in [r[2] for r in REGIONS]:
        sub = bs[bs["region"] == region]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["bin"], y=sub["present_in_n"],
            mode="markers", name=region,
            marker=dict(
                color=REGION_COLORS.get(region, "#aaa"),
                size=sub["mean_intensity"] * 80 + 5,
                opacity=0.75, sizemode="area",
            ),
            hovertemplate=(
                "Bin: %{x:.0f} cm⁻¹<br>"
                "Present in %{y} / " + str(result["n_runs"]) + " runs<br>"
                "<extra></extra>"
            ),
        ))
    fig.add_hline(
        y=result["n_runs"] * 0.8, line_dash="dash", line_color="green",
        annotation_text="≥80% runs", annotation_position="right",
    )
    fig.update_layout(
        title=f"Peak Consistency — {result['label']}",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis=dict(title=f"# Runs (out of {result['n_runs']})", range=[0, result["n_runs"] + 1]),
        template="plotly_white", legend_title="Region", height=460,
    )
    return fig


def peak_count_bar(result: dict) -> go.Figure | None:
    """Bar: peak count per run. Skipped for single run."""
    if result["is_single"]:
        return None
    rs = result["run_summary"]
    fig = go.Figure(go.Bar(
        x=rs["run"], y=rs["n_peaks"],
        marker_color=[result["color_map"].get(r, "#3498db") for r in rs["run"]],
        text=rs["n_peaks"], textposition="outside",
        hovertemplate="Run: %{x}<br>Peaks: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Peaks Detected per Run — {result['label']}",
        xaxis_title="Run", yaxis_title="Peak Count",
        template="plotly_white", height=360,
    )
    return fig


def region_distribution(result: dict) -> go.Figure:
    """Stacked bar: peak distribution across spectral regions per run."""
    pivot = result["region_summary"].pivot_table(
        index="run", columns="region", values="peak_count", fill_value=0
    ).reindex(result["run_names"])
    fig = go.Figure()
    for region in pivot.columns:
        fig.add_trace(go.Bar(
            name=region, x=pivot.index.tolist(), y=pivot[region].tolist(),
            marker_color=REGION_COLORS.get(region, "#aaa"),
            hovertemplate=f"Run: %{{x}}<br>{region}: %{{y}} peaks<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        title=f"Peak Distribution by Spectral Region — {result['label']}",
        xaxis_title="Run", yaxis_title="Peak Count",
        template="plotly_white", legend_title="Region", height=430,
    )
    return fig


def top_peaks_bar(result: dict) -> go.Figure:
    """Top 20 most intense peaks with error bars."""
    tp = result["top_peaks"].sort_values("bin")
    fig = go.Figure(go.Bar(
        x=tp["bin"].astype(str) + " cm⁻¹",
        y=tp["mean_intensity"],
        error_y=dict(type="data", array=tp["std_intensity"].fillna(0).tolist()),
        marker_color=tp["region"].map(REGION_COLORS).fillna("#aaa"),
        text=tp["functional_group"],
        textposition="outside",
        customdata=tp[["functional_group", "bond", "compound_class", "biological_relevance"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>Mean intensity: %{y:.4f}<br>"
            "Group: %{customdata[0]}<br>Bond: %{customdata[1]}<br>"
            "Compound: %{customdata[2]}<br>%{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=f"Top 20 Most Intense Peaks — {result['label']}",
        xaxis_title="Wavenumber Bin", yaxis_title="Mean Intensity",
        template="plotly_white", xaxis_tickangle=-45, height=460,
    )
    return fig


def region_boxplot(result: dict) -> go.Figure:
    """Box plot of intensity distribution per region."""
    fig = go.Figure()
    for region in [r[2] for r in REGIONS]:
        sub = result["all_df"][result["all_df"]["region"] == region]
        if sub.empty:
            continue
        fig.add_trace(go.Box(
            y=sub["intensity"], name=region,
            marker_color=REGION_COLORS.get(region, "#aaa"),
            boxmean=True,
            hovertemplate=f"{region}<br>Intensity: %{{y:.4f}}<extra></extra>",
        ))
    fig.update_layout(
        title=f"Intensity Distribution by Region — {result['label']}",
        yaxis_title="Absorbance", template="plotly_white",
        xaxis_tickangle=-30, height=460, showlegend=False,
    )
    return fig


# ════════════════════════════════════════════
#  MODE 2 — Comparison charts
# ════════════════════════════════════════════

def comparison_overlay(before: dict, after: dict) -> go.Figure:
    """Mean spectra of before and after overlaid."""
    bs_b = before["bin_stats"].sort_values("bin")
    bs_a = after["bin_stats"].sort_values("bin")

    fig = go.Figure()
    # Before band
    upper_b = bs_b["mean_intensity"] + bs_b["std_intensity"].fillna(0)
    lower_b = (bs_b["mean_intensity"] - bs_b["std_intensity"].fillna(0)).clip(lower=0)
    fig.add_trace(go.Scatter(
        x=pd.concat([bs_b["bin"], bs_b["bin"][::-1]]),
        y=pd.concat([upper_b, lower_b[::-1]]),
        fill="toself", fillcolor="rgba(52,152,219,0.12)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=bs_b["bin"], y=bs_b["mean_intensity"],
        mode="lines", name="Before (mean)",
        line=dict(color="#2980b9", width=2),
        hovertemplate="Before — Bin: %{x:.0f} cm⁻¹<br>Mean: %{y:.4f}<extra></extra>",
    ))
    # After band
    upper_a = bs_a["mean_intensity"] + bs_a["std_intensity"].fillna(0)
    lower_a = (bs_a["mean_intensity"] - bs_a["std_intensity"].fillna(0)).clip(lower=0)
    fig.add_trace(go.Scatter(
        x=pd.concat([bs_a["bin"], bs_a["bin"][::-1]]),
        y=pd.concat([upper_a, lower_a[::-1]]),
        fill="toself", fillcolor="rgba(231,76,60,0.12)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=bs_a["bin"], y=bs_a["mean_intensity"],
        mode="lines", name="After (mean)",
        line=dict(color="#e74c3c", width=2),
        hovertemplate="After — Bin: %{x:.0f} cm⁻¹<br>Mean: %{y:.4f}<extra></extra>",
    ))
    _add_region_shading(fig)
    fig.update_layout(
        title="Before vs After — Mean Spectrum Comparison (±1 SD)",
        xaxis=dict(title="Wavenumber (cm⁻¹)", autorange="reversed"),
        yaxis_title="Mean Absorbance", template="plotly_white", height=500,
    )
    return fig


def delta_spectrum(diff: dict) -> go.Figure:
    """Delta intensity (After − Before) per bin."""
    df = diff["delta_df"].sort_values("bin")
    colors = df["delta"].apply(
        lambda d: "#e74c3c" if d > 0 else "#2980b9"
    )
    fig = go.Figure(go.Bar(
        x=df["bin"], y=df["delta"],
        marker_color=colors,
        customdata=df[["functional_group", "status", "delta_pct"]].values,
        hovertemplate=(
            "Bin: %{x:.0f} cm⁻¹<br>Δ Intensity: %{y:.4f}<br>"
            "Group: %{customdata[0]}<br>Status: %{customdata[1]}<br>"
            "Change: %{customdata[2]:.1f}%<extra></extra>"
        ),
    ))
    fig.add_hline(y=0, line_color="#333", line_width=1)
    fig.update_layout(
        title="Delta Spectrum — After minus Before (Δ Intensity)",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="Δ Intensity (After − Before)",
        template="plotly_white", height=420,
    )
    return fig


def volcano_plot(diff: dict) -> go.Figure:
    """Volcano-style: delta% vs wavenumber, coloured by significance."""
    df = diff["delta_df"].copy()
    color_map = {
        "new":       "#9b59b6",
        "lost":      "#e67e22",
        "increased": "#e74c3c",
        "decreased": "#2980b9",
        "unchanged": "#95a5a6",
    }
    fig = go.Figure()
    for status, group in df.groupby("status"):
        fig.add_trace(go.Scatter(
            x=group["bin"], y=group["delta_pct"],
            mode="markers", name=status.capitalize(),
            marker=dict(color=color_map.get(status, "#aaa"), size=7, opacity=0.8),
            customdata=group[["functional_group", "delta"]].values,
            hovertemplate=(
                "Bin: %{x:.0f} cm⁻¹<br>Change: %{y:.1f}%<br>"
                "Group: %{customdata[0]}<br>Δ: %{customdata[1]:.4f}<extra></extra>"
            ),
        ))
    fig.add_hline(y=0, line_color="#333", line_dash="dot")
    fig.update_layout(
        title="Change Profile — Δ% per Bin (coloured by status)",
        xaxis=dict(title="Wavenumber bin (cm⁻¹)", autorange="reversed"),
        yaxis_title="% Change (After vs Before)",
        template="plotly_white", height=450, legend_title="Status",
    )
    return fig


def toxicity_scorecard(diff: dict) -> go.Figure:
    """Horizontal bar chart of toxicity marker concern levels."""
    df = diff["toxicity_df"].copy()
    concern_val = {"None": 0, "Low": 1, "Moderate": 2, "High": 3}
    concern_color = {"None": "#27ae60", "Low": "#f1c40f", "Moderate": "#e67e22", "High": "#e74c3c"}
    df["score"] = df["concern"].map(concern_val)
    df["color"] = df["concern"].map(concern_color)
    df = df.sort_values("score", ascending=True)

    fig = go.Figure(go.Bar(
        x=df["score"], y=df["marker"],
        orientation="h",
        marker_color=df["color"].tolist(),
        text=df["concern"],
        textposition="inside",
        customdata=df[["band_label", "before_value", "after_value", "delta_pct", "description"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>Band: %{customdata[0]}<br>"
            "Before: %{customdata[1]:.4f}  After: %{customdata[2]:.4f}<br>"
            "Change: %{customdata[3]:.1f}%<br>%{customdata[4]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Toxicity Marker Scorecard",
        xaxis=dict(title="Concern Level", tickvals=[0,1,2,3],
                   ticktext=["None","Low","Moderate","High"]),
        yaxis_title="", template="plotly_white", height=460,
        xaxis_range=[0, 3.5],
    )
    return fig


def new_lost_peaks(diff: dict) -> go.Figure:
    """Side-by-side bars for new vs lost peaks."""
    new_df  = diff["new_peaks"]
    lost_df = diff["lost_peaks"]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("New Peaks (After only)", "Lost Peaks (Before only)"))
    if not new_df.empty:
        fig.add_trace(go.Bar(
            x=new_df["bin"], y=new_df["mean_after"],
            marker_color="#9b59b6", name="New",
            hovertemplate="Bin: %{x:.0f} cm⁻¹<br>Intensity: %{y:.4f}<extra></extra>",
        ), row=1, col=1)
    if not lost_df.empty:
        fig.add_trace(go.Bar(
            x=lost_df["bin"], y=lost_df["mean_before"],
            marker_color="#e67e22", name="Lost",
            hovertemplate="Bin: %{x:.0f} cm⁻¹<br>Intensity: %{y:.4f}<extra></extra>",
        ), row=1, col=2)

    fig.update_xaxes(title_text="Wavenumber (cm⁻¹)", autorange="reversed")
    fig.update_yaxes(title_text="Intensity")
    fig.update_layout(
        title="New and Lost Peaks (Before vs After)",
        template="plotly_white", height=400, showlegend=False,
    )
    return fig


def region_comparison_bar(before: dict, after: dict) -> go.Figure:
    """Grouped bar: mean intensity per region, Before vs After."""
    def _region_mean(result):
        return result["all_df"].groupby("region")["intensity"].mean().rename(result["label"])

    b_series = _region_mean(before)
    a_series = _region_mean(after)
    combined = pd.concat([b_series, a_series], axis=1).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Before", x=combined.index.tolist(), y=combined["Before"].tolist(),
        marker_color="#2980b9",
        hovertemplate="Before — %{x}<br>Mean intensity: %{y:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="After", x=combined.index.tolist(), y=combined["After"].tolist(),
        marker_color="#e74c3c",
        hovertemplate="After — %{x}<br>Mean intensity: %{y:.4f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="group",
        title="Mean Intensity per Spectral Region — Before vs After",
        xaxis_title="Region", yaxis_title="Mean Intensity",
        template="plotly_white", xaxis_tickangle=-30, height=430,
    )
    return fig


# ════════════════════════════════════════════
#  helpers
# ════════════════════════════════════════════

def _add_region_shading(fig: go.Figure) -> None:
    for lo, hi, label in REGIONS:
        color = REGION_COLORS.get(label, "#aaa")
        fig.add_vrect(
            x0=lo, x1=hi,
            fillcolor=color, opacity=0.05, line_width=0,
            annotation_text=label if (hi - lo) > 200 else "",
            annotation_position="top left",
            annotation=dict(font_size=8, font_color="#666"),
        )
