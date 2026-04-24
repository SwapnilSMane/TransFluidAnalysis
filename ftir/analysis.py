"""
Core FTIR analysis: binning, statistics, consistency.
Handles both single-run and multi-run inputs gracefully.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px

from .assignments import assign_peak, get_region, REGIONS

BIN_WIDTH = 10.0


def _bin(wn: float) -> float:
    return round(wn / BIN_WIDTH) * BIN_WIDTH


def run_analysis(runs: dict[str, pd.DataFrame], label: str) -> dict:
    """
    Parameters
    ----------
    runs  : {run_name: DataFrame(wavenumber, intensity)}
    label : "Before" or "After"

    Returns
    -------
    result dict with all analysis outputs (see keys below)
    """
    n_runs = len(runs)
    is_single = n_runs == 1

    run_colors = px.colors.qualitative.Set2
    color_map = {name: run_colors[i % len(run_colors)] for i, name in enumerate(runs)}

    # ── annotate each run ──
    annotated: dict[str, pd.DataFrame] = {}
    for name, df in runs.items():
        rows = []
        for _, r in df.iterrows():
            a = assign_peak(r.wavenumber)
            rows.append({
                "run":               name,
                "wavenumber":        r.wavenumber,
                "intensity":         r.intensity,
                "bin":               _bin(r.wavenumber),
                "region":            get_region(r.wavenumber),
                "functional_group":  a["functional_group"],
                "bond":              a["bond"],
                "vibration_type":    a["vibration_type"],
                "compound_class":    a["compound_class"],
                "biological_relevance": a["biological_relevance"],
            })
        annotated[name] = pd.DataFrame(rows)

    all_df = pd.concat(annotated.values(), ignore_index=True)

    # ── bin statistics ──
    bin_stats = all_df.groupby("bin").agg(
        count            =("intensity", "count"),
        mean_intensity   =("intensity", "mean"),
        std_intensity    =("intensity", "std"),
        min_intensity    =("intensity", "min"),
        max_intensity    =("intensity", "max"),
        functional_group =("functional_group", lambda x: x.mode()[0]),
        bond             =("bond",             lambda x: x.mode()[0]),
        vibration_type   =("vibration_type",   lambda x: x.mode()[0]),
        compound_class   =("compound_class",   lambda x: x.mode()[0]),
        biological_relevance=("biological_relevance", lambda x: x.mode()[0]),
        region           =("region",           lambda x: x.mode()[0]),
    ).reset_index()

    bin_stats["cv_pct"] = (
        bin_stats["std_intensity"] /
        bin_stats["mean_intensity"].replace(0, np.nan) * 100
    ).round(1)
    bin_stats["present_in_n"] = bin_stats["count"]
    bin_stats["present_in_pct"] = (bin_stats["count"] / n_runs * 100).round(0)

    # consistency label
    def _consistency(n):
        frac = n / n_runs
        if frac == 1.0:           return "All runs"
        if frac >= 0.8:           return "Highly consistent (≥80%)"
        if frac >= 0.5:           return "Moderate (50–79%)"
        return                            "Rare (<50%)"
    bin_stats["consistency"] = bin_stats["count"].apply(_consistency)

    highly_consistent = bin_stats[bin_stats["present_in_pct"] >= 80].copy()

    # ── per-run summary ──
    run_summary = all_df.groupby("run").agg(
        n_peaks        =("wavenumber", "count"),
        mean_intensity =("intensity",  "mean"),
        max_intensity  =("intensity",  "max"),
        total_intensity=("intensity",  "sum"),
    ).reset_index()

    # ── region summary ──
    region_summary = all_df.groupby(["run", "region"]).agg(
        peak_count     =("wavenumber", "count"),
        mean_intensity =("intensity",  "mean"),
        total_intensity=("intensity",  "sum"),
    ).reset_index()

    # ── top peaks by mean intensity ──
    top_peaks = bin_stats.nlargest(20, "mean_intensity").copy()

    return {
        "label":             label,
        "n_runs":            n_runs,
        "is_single":         is_single,
        "runs":              runs,
        "annotated":         annotated,
        "all_df":            all_df,
        "bin_stats":         bin_stats,
        "run_summary":       run_summary,
        "region_summary":    region_summary,
        "highly_consistent": highly_consistent,
        "top_peaks":         top_peaks,
        "color_map":         color_map,
        "run_names":         list(runs.keys()),
    }
