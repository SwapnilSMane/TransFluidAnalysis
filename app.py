"""
FTIR Transplant Fluid Analyser — Streamlit App
Deploy free: streamlit.io/cloud  (no server required)
"""
import streamlit as st
import traceback

from ftir.loader   import load, detect_format
from ftir.analysis import run_analysis
from ftir.difference import compare
import ftir.charts   as C
import ftir.exporter as E

st.set_page_config(
    page_title="FTIR Transplant Fluid Analyser",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────
# helper functions (defined before any st.* calls)
# ─────────────────────────────────────────────────────────────

def _show_format_guide():
    with st.expander("📋 Input format guide"):
        st.markdown("""
| Format | Description | Example |
|--------|-------------|---------|
| **Single file, single run** | Two columns: Wavenumber \| Intensity. Header optional. | `RUN_01.xlsx` |
| **Single file, multi-run** | Multiple runs side-by-side with `RUN X` headers in row 1 | `MASTER SHEET.xlsx` |
| **Multiple files** | One file per run, each in single-run format | `RUN_01.xlsx`, `RUN_03.xlsx`, … |
        """)


def _searchable_dataframe(df):
    query = st.text_input("Filter table…", key=f"filter_{id(df)}")
    if query:
        mask = df.apply(lambda col: col.astype(str).str.lower().str.contains(
            query.lower(), na=False)).any(axis=1)
        df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_mode1(result: dict):
    label  = result["label"]
    single = result["is_single"]

    cols = st.columns(5)
    cols[0].metric("Total Peaks",      len(result["all_df"]))
    cols[1].metric("Runs",             result["n_runs"])
    cols[2].metric("Consistent Peaks", len(result["highly_consistent"]),
                   help="Peaks present in ≥80% of runs")
    cols[3].metric("Wavenumber Range",
                   f"{result['all_df']['wavenumber'].min():.0f}–"
                   f"{result['all_df']['wavenumber'].max():.0f} cm⁻¹")
    bs = result["bin_stats"]
    cols[4].metric("Max Mean Intensity",
                   f"{bs['mean_intensity'].max():.4f}",
                   f"at {bs.loc[bs['mean_intensity'].idxmax(),'bin']:.0f} cm⁻¹")

    tabs = st.tabs(["Spectra", "Assignments", "Statistics", "Regions",
                    "Reproducibility", "Full Peak Table"])

    with tabs[0]:
        st.plotly_chart(C.spectral_overlay(result), use_container_width=True)
        if not single:
            fig_mb = C.mean_band(result)
            if fig_mb:
                st.plotly_chart(fig_mb, use_container_width=True)

    with tabs[1]:
        hc = result["highly_consistent"].sort_values("bin")
        if hc.empty:
            st.warning("No peaks consistent across ≥80% of runs.")
        else:
            st.caption(f"{len(hc)} peaks present in ≥80% of {result['n_runs']} run(s)")
            st.dataframe(
                hc[["bin","functional_group","bond","vibration_type",
                    "compound_class","biological_relevance",
                    "mean_intensity","cv_pct","present_in_n","consistency"]].rename(columns={
                    "bin":"Bin cm⁻¹","functional_group":"Functional Group","bond":"Bond",
                    "vibration_type":"Vibration","compound_class":"Compound Class",
                    "biological_relevance":"Biological Relevance",
                    "mean_intensity":"Mean Int.","cv_pct":"CV%",
                    "present_in_n":"# Runs","consistency":"Consistency",
                }),
                use_container_width=True, hide_index=True,
            )

    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(C.top_peaks_bar(result), use_container_width=True)
        with col2:
            st.plotly_chart(C.region_boxplot(result), use_container_width=True)
        if not single:
            fig_pc = C.peak_count_bar(result)
            if fig_pc:
                st.plotly_chart(fig_pc, use_container_width=True)
            fig_hm = C.intensity_heatmap(result)
            if fig_hm:
                st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Run-level statistics (heatmap, per-run bar) require ≥2 runs.")

    with tabs[3]:
        st.plotly_chart(C.region_distribution(result), use_container_width=True)

    with tabs[4]:
        if single:
            st.info("Reproducibility analysis requires ≥2 runs. "
                    "Upload multiple files or a multi-run Excel to enable this section.")
        else:
            fig_cv = C.cv_chart(result)
            if fig_cv:
                st.plotly_chart(fig_cv, use_container_width=True)
            fig_cs = C.consistency_chart(result)
            if fig_cs:
                st.plotly_chart(fig_cs, use_container_width=True)

    with tabs[5]:
        bs = result["bin_stats"].sort_values("bin")
        st.caption(f"{len(bs)} unique 10 cm⁻¹ bins")
        _searchable_dataframe(bs[[
            "bin","functional_group","bond","vibration_type","compound_class",
            "biological_relevance","mean_intensity","cv_pct","present_in_n","consistency","region"
        ]].rename(columns={
            "bin":"Bin cm⁻¹","functional_group":"Functional Group","bond":"Bond",
            "vibration_type":"Vibration","compound_class":"Compound Class",
            "biological_relevance":"Biological Relevance",
            "mean_intensity":"Mean Int.","cv_pct":"CV%","present_in_n":"# Runs",
            "consistency":"Consistency","region":"Region",
        }))


def _render_mode2(before: dict, after: dict, diff: dict):
    verdict = diff["verdict"]
    vcolor  = {"Low": "green", "Moderate": "orange", "High": "red"}.get(verdict, "gray")
    st.markdown(
        f"### Toxicity Verdict: "
        f"<span style='color:{vcolor};font-size:1.3em'><b>{verdict}</b></span> &nbsp;"
        f"<small>(score {diff['toxicity_score']}/{diff['toxicity_max']}, "
        f"{diff['toxicity_pct']:.1f}%)</small>",
        unsafe_allow_html=True,
    )
    st.caption(diff["verdict_detail"])
    st.divider()

    col_b, col_a = st.columns(2)
    with col_b:
        st.subheader(f"Before — {before['n_runs']} run(s)")
        st.caption(f"Total peaks: {len(before['all_df'])}  |  Consistent: {len(before['highly_consistent'])}")
    with col_a:
        st.subheader(f"After — {after['n_runs']} run(s)")
        st.caption(f"Total peaks: {len(after['all_df'])}  |  Consistent: {len(after['highly_consistent'])}")

    tabs = st.tabs([
        "Comparison", "Delta", "New / Lost Peaks",
        "Before Analysis", "After Analysis", "Toxicity", "Full Tables"
    ])

    with tabs[0]:
        st.plotly_chart(C.comparison_overlay(before, after), use_container_width=True)
        st.plotly_chart(C.region_comparison_bar(before, after), use_container_width=True)

    with tabs[1]:
        st.plotly_chart(C.delta_spectrum(diff), use_container_width=True)
        st.plotly_chart(C.volcano_plot(diff), use_container_width=True)

    with tabs[2]:
        st.plotly_chart(C.new_lost_peaks(diff), use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"New peaks ({len(diff['new_peaks'])})")
            if diff["new_peaks"].empty:
                st.success("No new peaks detected.")
            else:
                st.dataframe(diff["new_peaks"][["bin","functional_group","mean_after","biological_relevance"]],
                             use_container_width=True, hide_index=True)
        with col2:
            st.subheader(f"Lost peaks ({len(diff['lost_peaks'])})")
            if diff["lost_peaks"].empty:
                st.success("No lost peaks detected.")
            else:
                st.dataframe(diff["lost_peaks"][["bin","functional_group","mean_before","biological_relevance"]],
                             use_container_width=True, hide_index=True)

    with tabs[3]:
        st.caption("Before transplant — detailed analysis")
        _render_mode1(before)

    with tabs[4]:
        st.caption("After transplant — detailed analysis")
        _render_mode1(after)

    with tabs[5]:
        st.plotly_chart(C.toxicity_scorecard(diff), use_container_width=True)
        st.dataframe(
            diff["toxicity_df"][[
                "marker","band_label","before_value","after_value",
                "delta_pct","concern","description"
            ]].rename(columns={
                "marker":"Marker","band_label":"Band","before_value":"Before",
                "after_value":"After","delta_pct":"Δ%","concern":"Concern",
                "description":"Interpretation",
            }),
            use_container_width=True, hide_index=True,
        )

    with tabs[6]:
        st.subheader("Delta Table")
        _searchable_dataframe(diff["delta_df"][[
            "bin","functional_group","region",
            "mean_before","mean_after","delta","delta_pct","significant","status",
            "biological_relevance"
        ]].rename(columns={
            "bin":"Bin cm⁻¹","functional_group":"Functional Group","region":"Region",
            "mean_before":"Before","mean_after":"After","delta":"Δ",
            "delta_pct":"Δ%","significant":"Significant","status":"Status",
            "biological_relevance":"Relevance",
        }))


def _build_figures(before: dict, after: dict | None, diff: dict | None) -> dict:
    figures = {}
    def _add(key, fig):
        if fig is not None:
            figures[key] = fig
    _add("spectral_overlay",    C.spectral_overlay(before))
    _add("mean_band",           C.mean_band(before))
    _add("intensity_heatmap",   C.intensity_heatmap(before))
    _add("cv_chart",            C.cv_chart(before))
    _add("consistency_chart",   C.consistency_chart(before))
    _add("peak_count_bar",      C.peak_count_bar(before))
    _add("region_distribution", C.region_distribution(before))
    _add("top_peaks_bar",       C.top_peaks_bar(before))
    _add("region_boxplot",      C.region_boxplot(before))
    if after and diff:
        _add("comparison_overlay",    C.comparison_overlay(before, after))
        _add("delta_spectrum",        C.delta_spectrum(diff))
        _add("volcano_plot",          C.volcano_plot(diff))
        _add("region_comparison_bar", C.region_comparison_bar(before, after))
        _add("toxicity_scorecard",    C.toxicity_scorecard(diff))
        _add("new_lost_peaks",        C.new_lost_peaks(diff))
    return figures


def _render_downloads(before: dict, after: dict | None, diff: dict | None):
    st.divider()
    st.subheader("📥 Download Report")
    figures = _build_figures(before, after, diff)
    label   = before["label"]
    stem    = "ftir_before_vs_after" if after else f"ftir_{label.lower()}"

    cols = st.columns(6)
    with cols[0]:
        html = E.to_html(before, after, diff, figures)
        st.download_button("🌐 HTML", html, f"{stem}.html",
                           "text/html", use_container_width=True)
    with cols[1]:
        with st.spinner("PDF…"):
            pdf = E.to_pdf(before, after, diff, figures)
        st.download_button("📄 PDF", pdf, f"{stem}.pdf",
                           "application/pdf", use_container_width=True)
    with cols[2]:
        xlsx = E.to_excel(before, after, diff)
        st.download_button("📊 Excel", xlsx, f"{stem}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with cols[3]:
        csv_bytes = E.to_csv(before, after, diff)
        st.download_button("📋 CSV", csv_bytes, f"{stem}.csv",
                           "text/csv", use_container_width=True)
    with cols[4]:
        with st.spinner("PPTX…"):
            pptx = E.to_pptx(before, after, diff, figures)
        st.download_button("📑 PowerPoint", pptx, f"{stem}.pptx",
                           "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                           use_container_width=True)
    with cols[5]:
        with st.spinner("DOCX…"):
            docx = E.to_docx(before, after, diff, figures)
        st.download_button("📝 Word", docx, f"{stem}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)


# ─────────────────────────────────────────────────────────────
# sidebar — input
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔬 FTIR Analyser")
    st.caption("Transplant Fluid Spectroscopic Analysis")
    st.divider()

    mode = st.radio(
        "Analysis Mode",
        ["Mode 1 — Single-side Analysis", "Mode 2 — Before vs After Comparison"],
        help=(
            "**Mode 1**: Analyse one fluid state (before OR after transplant).\n\n"
            "**Mode 2**: Compare before and after — detect toxicity and biochemical changes."
        ),
    )
    mode2 = mode.startswith("Mode 2")

    st.divider()
    st.markdown("**Input formats accepted**")
    st.caption("• **Single file** — one or multiple runs in one `.xlsx`\n"
               "• **Multiple files** — one `.xlsx` per run\n\n"
               "Format is auto-detected from file structure.")

    st.divider()
    st.markdown("**Export formats**")
    st.caption("HTML · PDF · Excel · CSV · PowerPoint · Word\n\n"
               "Download buttons appear after analysis.")


# ─────────────────────────────────────────────────────────────
# main — upload
# ─────────────────────────────────────────────────────────────
st.title("🔬 FTIR Transplant Fluid Analyser")

if not mode2:
    # ── Mode 1 ──
    col_label, col_upload = st.columns([1, 3])
    with col_label:
        fluid_label = st.radio("Fluid state", ["Before", "After"], horizontal=True)
    with col_upload:
        files = st.file_uploader(
            f"Upload {fluid_label} data (.xlsx) — single file or multiple files",
            type=["xlsx"], accept_multiple_files=True, key="mode1_files",
        )

    if not files:
        st.info("Upload one or more `.xlsx` files to begin analysis.")
        _show_format_guide()
        st.stop()

    with st.spinner("Loading and analysing…"):
        try:
            runs   = load(files)
            result = run_analysis(runs, label=fluid_label)
        except Exception as e:
            st.error(f"Error loading files: {e}")
            st.code(traceback.format_exc())
            st.stop()

    _render_mode1(result)
    _render_downloads(result, None, None)

else:
    # ── Mode 2 ──
    col_b, col_a = st.columns(2)
    with col_b:
        st.subheader("Before transplant")
        before_files = st.file_uploader(
            "Upload Before data (.xlsx)",
            type=["xlsx"], accept_multiple_files=True, key="before_files",
        )
    with col_a:
        st.subheader("After transplant")
        after_files = st.file_uploader(
            "Upload After data (.xlsx)",
            type=["xlsx"], accept_multiple_files=True, key="after_files",
        )

    if not before_files or not after_files:
        st.info("Upload both Before and After files to begin comparison analysis.")
        _show_format_guide()
        st.stop()

    with st.spinner("Loading and analysing both datasets…"):
        try:
            before_runs = load(before_files)
            after_runs  = load(after_files)
            before_res  = run_analysis(before_runs, label="Before")
            after_res   = run_analysis(after_runs,  label="After")
            diff        = compare(before_res, after_res)
        except Exception as e:
            st.error(f"Error during analysis: {e}")
            st.code(traceback.format_exc())
            st.stop()

    _render_mode2(before_res, after_res, diff)
    _render_downloads(before_res, after_res, diff)

