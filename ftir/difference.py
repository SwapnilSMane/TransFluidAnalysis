"""
Before vs After comparison:
  - Delta intensity per bin
  - Peak shifts
  - New / lost peaks
  - Toxicity scoring per marker band
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .assignments import TOXICITY_MARKERS

BIN_WIDTH = 10.0
THRESHOLD_SD = 2.0   # delta > 2×SD of baseline = significant


def compare(before: dict, after: dict) -> dict:
    """
    Parameters
    ----------
    before, after : result dicts from analysis.run_analysis()

    Returns
    -------
    diff dict
    """
    bs_b = before["bin_stats"].set_index("bin")
    bs_a = after["bin_stats"].set_index("bin")

    all_bins = sorted(set(bs_b.index) | set(bs_a.index))

    rows = []
    for b in all_bins:
        in_b = b in bs_b.index
        in_a = b in bs_a.index
        mi_b = bs_b.loc[b, "mean_intensity"] if in_b else 0.0
        mi_a = bs_a.loc[b, "mean_intensity"] if in_a else 0.0
        std_b = bs_b.loc[b, "std_intensity"]  if in_b else 0.0
        fg   = bs_b.loc[b, "functional_group"] if in_b else (
               bs_a.loc[b, "functional_group"] if in_a else "–")
        bond = bs_b.loc[b, "bond"] if in_b else (
               bs_a.loc[b, "bond"] if in_a else "–")
        region = bs_b.loc[b, "region"] if in_b else (
                 bs_a.loc[b, "region"] if in_a else "–")
        bio  = bs_b.loc[b, "biological_relevance"] if in_b else (
               bs_a.loc[b, "biological_relevance"] if in_a else "–")

        delta = mi_a - mi_b
        delta_pct = (delta / mi_b * 100) if mi_b != 0 else (100.0 if mi_a > 0 else 0.0)
        significant = abs(delta) > THRESHOLD_SD * (std_b if std_b > 0 else 0.001)

        status = "unchanged"
        if in_b and not in_a:
            status = "lost"
        elif not in_b and in_a:
            status = "new"
        elif significant:
            status = "increased" if delta > 0 else "decreased"

        rows.append({
            "bin":            b,
            "mean_before":    mi_b,
            "mean_after":     mi_a,
            "delta":          delta,
            "delta_pct":      round(delta_pct, 1),
            "significant":    significant,
            "status":         status,
            "functional_group": fg,
            "bond":           bond,
            "region":         region,
            "biological_relevance": bio,
        })

    delta_df = pd.DataFrame(rows)

    new_peaks  = delta_df[delta_df["status"] == "new"].copy()
    lost_peaks = delta_df[delta_df["status"] == "lost"].copy()
    increased  = delta_df[delta_df["status"] == "increased"].copy()
    decreased  = delta_df[delta_df["status"] == "decreased"].copy()
    significant_changes = delta_df[delta_df["significant"]].copy()

    # ── toxicity scoring ──
    scores = []
    for marker in TOXICITY_MARKERS:
        b_vals = [bs_b.loc[bn, "mean_intensity"] for bn in marker["bins"] if bn in bs_b.index]
        a_vals = [bs_a.loc[bn, "mean_intensity"] for bn in marker["bins"] if bn in bs_a.index]
        b_mean = float(np.mean(b_vals)) if b_vals else 0.0
        a_mean = float(np.mean(a_vals)) if a_vals else 0.0
        delta  = a_mean - b_mean
        delta_pct = (delta / b_mean * 100) if b_mean != 0 else (100 if a_mean > 0 else 0)

        direction = marker["direction"]
        concern = _score_marker(direction, delta, delta_pct, b_mean, a_mean)

        scores.append({
            "marker":       marker["name"],
            "band_label":   marker["band_label"],
            "before_value": round(b_mean, 5),
            "after_value":  round(a_mean, 5),
            "delta":        round(delta, 5),
            "delta_pct":    round(delta_pct, 1),
            "direction":    direction,
            "concern":      concern,
            "description":  marker["description"],
        })

    toxicity_df = pd.DataFrame(scores)

    # Overall verdict
    concern_map = {"None": 0, "Low": 1, "Moderate": 2, "High": 3}
    total = sum(concern_map.get(r, 0) for r in toxicity_df["concern"])
    max_possible = 3 * len(scores)
    pct = total / max_possible * 100

    if pct < 20:
        verdict = "Low"
        verdict_color = "#27ae60"
        verdict_detail = "No significant biochemical changes detected."
    elif pct < 50:
        verdict = "Moderate"
        verdict_color = "#f39c12"
        verdict_detail = "Some biochemical changes detected. Further investigation recommended."
    else:
        verdict = "High"
        verdict_color = "#e74c3c"
        verdict_detail = "Significant biochemical changes detected. Possible toxicity / organ stress."

    return {
        "delta_df":           delta_df,
        "new_peaks":          new_peaks,
        "lost_peaks":         lost_peaks,
        "increased":          increased,
        "decreased":          decreased,
        "significant_changes":significant_changes,
        "toxicity_df":        toxicity_df,
        "toxicity_score":     total,
        "toxicity_max":       max_possible,
        "toxicity_pct":       round(pct, 1),
        "verdict":            verdict,
        "verdict_color":      verdict_color,
        "verdict_detail":     verdict_detail,
    }


def _score_marker(direction: str, delta: float, delta_pct: float,
                  b_mean: float, a_mean: float) -> str:
    abs_pct = abs(delta_pct)

    if direction == "new_peak":
        if a_mean > 0.005:
            return "High"
        if a_mean > 0.001:
            return "Moderate"
        return "None"

    if direction == "increase":
        if delta_pct > 50:  return "High"
        if delta_pct > 20:  return "Moderate"
        if delta_pct > 5:   return "Low"
        return "None"

    if direction == "decrease":
        if delta_pct < -50: return "High"
        if delta_pct < -20: return "Moderate"
        if delta_pct < -5:  return "Low"
        return "None"

    if direction == "shift":
        if abs_pct > 50:    return "High"
        if abs_pct > 20:    return "Moderate"
        if abs_pct > 5:     return "Low"
        return "None"

    # "change"
    if abs_pct > 50:    return "High"
    if abs_pct > 20:    return "Moderate"
    if abs_pct > 5:     return "Low"
    return "None"
