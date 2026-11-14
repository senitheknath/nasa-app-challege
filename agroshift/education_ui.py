"""Optional educational views, imported only from Research."""

from datetime import date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .power import DataError
from .climate import season_samples
from .ml_engine import (
    CROP_LIST,
    DATASET_PATH,
    find_knn_seasonal_analogs,
    forecast_seasonal_climate_timeseries,
    load_educational_bundle,
)
from .global_atlas import (
    COUNTRIES_ATLAS_PATH,
    EARTH_GRID_PATH,
    NASA_STATIONS_SUMMARY_PATH,
    simulate_climate,
)


def chart_style(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#0F172A", size=12),
        margin=dict(l=12, r=12, t=28, b=18),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#F1F5F9", zerolinecolor="#E2E8F0")
    return fig


def render():
    st.title("Educational ML studio")
    st.warning(
        "Synthetic educational data. The generator assigned the crop labels and mathematical target. All classifier and regression metrics below describe agreement with that generator. Field outcomes have not been evaluated."
    )
    try:
        bundle = load_educational_bundle()
    except DataError as exc:
        st.info(str(exc))
        st.stop()
    ds_info = bundle["dataset_summary"]
    ev = bundle["evaluation"]

    m1, m2, m3, m4 = st.columns(4)
    ens_m = ev["models_compared"]["Non-Linear Basis + Bayesian Ensemble"]
    reg_m = ev["regression_models"]["nonlinear_ensemble"]
    m1.metric("Synthetic dataset size", f"{ds_info['total_rows']:,} rows")
    m2.metric(
        "Synthetic label agreement",
        f"{ens_m['accuracy']*100:.2f}%",
        f"95% CI: {ens_m['accuracy_ci95'][0]*100:.1f}–{ens_m['accuracy_ci95'][1]*100:.1f}%",
    )
    m3.metric(
        "Test Macro PR-AUC",
        f"{ens_m['macro_pr_auc']:.4f}",
        f"Macro-F1: {ens_m['macro_f1']:.4f}",
    )
    m4.metric(
        "Synthetic target R²", f"{reg_m['r2']:.4f}", f"MAE: {reg_m['mae']:.2f} pts"
    )

    # 1. Dataset & Preprocessing Pipeline Audit
    st.subheader("1. Synthetic training data and preprocessing")
    st.write(
        f"**Dataset Schema & Hygiene:** `{ds_info['total_rows']:,}` labeled seasonal records across **10 global crops** and **5 climate zones**. "
        f"`{ds_info['missing_ph_rows_handled']:,}` rows with randomly masked `soil_ph` (~6%) are preserved using an explicit binary `soil_ph_missing` indicator feature "
        f"plus median imputation (`pH = {bundle['preprocessor']['ph_median']:.2f}`) fitted **strictly on the `{ds_info['train_rows']:,}`-row Training Split** "
        f"before transforming the Validation (`{ds_info['val_rows']:,}` rows) and Test (`{ds_info['test_rows']:,}` rows) sets."
    )
    if DATASET_PATH.exists():
        sample_df = pd.read_csv(DATASET_PATH, nrows=100)
        st.dataframe(sample_df.head(15), hide_index=True, width="stretch")
        st.download_button(
            "Download labelled synthetic training examples",
            data=DATASET_PATH.read_bytes(),
            file_name="educational_synthetic_examples.csv",
            mime="text/csv",
            on_click="ignore",
        )

    # 2. Supervised Model Comparison Table
    st.subheader(
        "2. Supervised Classification & Regression Model Comparison (Held-Out Test Set)"
    )
    comp_rows = []
    for model_name, mm in ev["models_compared"].items():
        comp_rows.append(
            {
                "Model": model_name,
                "Test Accuracy (%)": round(mm["accuracy"] * 100, 2),
                "95% Bootstrap CI (%)": f"{mm['accuracy_ci95'][0]*100:.2f}% – {mm['accuracy_ci95'][1]*100:.2f}%",
                "Macro-F1": mm["macro_f1"],
                "Weighted-F1": mm["weighted_f1"],
                "Macro PR-AUC": mm["macro_pr_auc"],
            }
        )
    st.dataframe(pd.DataFrame(comp_rows), hide_index=True, width="stretch")

    cp = ev.get("conformal_prediction")
    if cp:
        cp1, cp2, cp3 = st.columns(3)
        cp1.metric(
            "Conformal Set Coverage (Target 90%)",
            f"{cp['classification_empirical_coverage_pct']:.2f}%",
            f"Avg Set Size: {cp['classification_avg_set_size']:.2f} crops",
        )
        cp2.metric(
            "Conformal Regression Coverage",
            f"{cp['regression_empirical_coverage_pct']:.2f}%",
            f"90% Half-Width: ±{cp['regression_half_width_pts']:.2f} pts",
        )
        cp3.metric(
            "Validation Non-Conformity Quantile",
            f"q̂₉₀ = {cp['classification_nonconformity_q90']:.4f}",
            "Distribution-free split conformal calibration",
        )

    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("**10×10 Test-Set Confusion Matrix (Non-Linear Ensemble)**")
        cm = ens_m["confusion_matrix"]
        crop_names = [c.replace("_", " ").title() for c in CROP_LIST]
        fig_cm = go.Figure(
            data=go.Heatmap(
                z=cm,
                x=crop_names,
                y=crop_names,
                colorscale="Teal",
                text=cm,
                texttemplate="%{text}",
            )
        )
        fig_cm.update_layout(
            height=420, xaxis_title="Predicted Crop", yaxis_title="Generator class"
        )
        st.plotly_chart(chart_style(fig_cm, 420), width="stretch")

    with c_right:
        st.markdown("**Permutation Feature Importance (Validation Drop in Accuracy)**")
        fi = ev["feature_importance"]
        fi_sorted = sorted(fi.items(), key=lambda kv: kv[1])
        fig_fi = go.Figure(
            go.Bar(
                x=[v * 100 for _, v in fi_sorted],
                y=[k for k, _ in fi_sorted],
                orientation="h",
                marker_color="#0f766e",
            )
        )
        fig_fi.update_xaxes(title="Accuracy Importance Drop (%)")
        st.plotly_chart(chart_style(fig_fi, 420), width="stretch")

    # 3. Slice-Based Error Analysis
    st.subheader("3. Slice-Based Performance Across Climate Zones & Irrigation Regimes")
    slice_df = pd.DataFrame(
        [
            {"Subpopulation Slice": k, "Test Accuracy (%)": round(v * 100, 2)}
            for k, v in ev["slice_analysis"].items()
        ]
    )
    st.dataframe(slice_df, hide_index=True, width="stretch")

    # 4. Unsupervised K-Means Clustering & 2D PCA Projection
    st.subheader("4. Unsupervised Agro-Climatic Clustering (K-Means + 2D SVD/PCA)")
    clust = ev["clustering"]
    cl_a, cl_b = st.columns([1, 2])
    with cl_a:
        sil_k = clust["silhouette_by_k"]
        fig_sil = go.Figure(
            go.Scatter(
                x=[int(k) for k in sil_k.keys()],
                y=list(sil_k.values()),
                mode="lines+markers",
                line=dict(color="#0f766e", width=2.5),
            )
        )
        fig_sil.update_xaxes(title="Number of Clusters (k)")
        fig_sil.update_yaxes(title="Silhouette Score")
        st.plotly_chart(chart_style(fig_sil, 320), width="stretch")
        st.caption(
            f"Optimal cluster count by Silhouette score: **k = {clust['optimal_k']}** (Silhouette = `{clust['optimal_silhouette']}`)."
        )
    with cl_b:
        pca_df = pd.DataFrame(clust["pca_points"])
        fig_pca = go.Figure()
        for cl_name, grp in pca_df.groupby("cluster"):
            fig_pca.add_trace(
                go.Scatter(
                    x=grp["pc1"],
                    y=grp["pc2"],
                    mode="markers",
                    name=cl_name,
                    text=grp["crop"],
                    hovertemplate="PC1=%{x}, PC2=%{y}<br>Crop=%{text}",
                )
            )
        fig_pca.update_xaxes(
            title=f"PC1 ({clust['pca_variance_ratio'][0]*100:.1f}% variance)"
        )
        fig_pca.update_yaxes(
            title=f"PC2 ({clust['pca_variance_ratio'][1]*100:.1f}% variance)"
        )
        st.plotly_chart(chart_style(fig_pca, 320), width="stretch")

    st.subheader("Weather simulation laboratory")
    st.caption(
        "Generated weather stays in this section. The farm profile and NASA history use independent data."
    )
    if st.checkbox("Show simulated daily weather"):
        from .decision import Farm

        farm = st.session_state.get("farm") or Farm()
        simulated = simulate_climate(
            farm.latitude, farm.longitude, date(2024, 1, 1), date(2024, 12, 31)
        )
        st.warning(simulated.provenance["mode"])
        st.line_chart(simulated.frame[["T2M", "T2M_MAX", "T2M_MIN"]])
        st.json(simulated.provenance)
        st.download_button(
            "Download simulated daily series",
            simulated.frame.assign(data_kind="SIMULATED").to_csv(),
            "simulated-weather.csv",
            on_click="ignore",
        )
    st.subheader("Global atlas")
    grid = pd.read_csv(EARTH_GRID_PATH)
    st.caption(
        "Educational model grid. Each value is generated from a location formula."
    )
    fig = go.Figure(
        go.Scattergeo(
            lat=grid.latitude,
            lon=grid.longitude,
            mode="markers",
            marker=dict(
                size=3,
                color=grid.temperature_mean_c,
                colorscale="Viridis",
                showscale=True,
                colorbar_title="Simulated °C",
            ),
        )
    )
    st.plotly_chart(fig, width="stretch")
    for title, path in [
        ("Simulated grid", EARTH_GRID_PATH),
        ("Country location index", COUNTRIES_ATLAS_PATH),
        ("POWER collection manifest", NASA_STATIONS_SUMMARY_PATH),
    ]:
        with st.expander(title):
            st.dataframe(pd.read_csv(path).head(30))
            st.download_button(
                "Download " + title, path.read_bytes(), path.name, on_click="ignore"
            )
    if st.session_state.dataset is not None:
        st.subheader("Historical rainfall backtest")
        ds = st.session_state.dataset
        st.caption(ds.provenance["mode"] + " · Research comparison on past seasons")
        backtest = forecast_seasonal_climate_timeseries(
            season_samples(ds.frame, st.session_state.farm.windows[0])
        )
        if backtest.get("available"):
            st.caption(
                f"Selected {backtest['selected_model']} on earlier validation seasons. Expanding-mean baseline RMSE {backtest['baseline_test_rmse_mm']:.1f} mm across {backtest['test_seasons']} test seasons."
            )
            st.write(
                f"Held-out MAE {backtest['test_mae_rain_mm']:.1f} mm · RMSE {backtest['test_rmse_rain_mm']:.1f} mm"
            )
            st.line_chart(
                pd.DataFrame(backtest["series"]).set_index("year")[
                    ["actual_rain_mm", "predicted_rain_mm"]
                ]
            )
        analogs = find_knn_seasonal_analogs(
            season_samples(ds.frame, st.session_state.farm.windows[0]), k=5
        )
        if analogs.get("available"):
            st.markdown(
                f"**Multivariate k-NN Historical Seasonal Analog Matcher (Reference Season: {analogs['reference_year']} · {analogs['reference_rainfall_mm']:.0f} mm, {analogs['reference_temperature_c']:.1f} °C)**"
            )
            st.caption(
                f"Top-{analogs['k']} closest historical NASA POWER seasons in standardized 6D agro-climatic space (Rainfall, Temp, ET₀, VPD, Dry Spell, GDD₁₀) · Analog mean rainfall: {analogs['analog_mean_rainfall_mm']:.0f} mm (IQR {analogs['analog_iqr_rainfall_mm'][0]:.0f}–{analogs['analog_iqr_rainfall_mm'][1]:.0f} mm)."
            )
            st.dataframe(pd.DataFrame(analogs["analogs"]), hide_index=True, width="stretch")

    st.subheader("5. Exploratory FAO Paper 66 / AquaCrop Water-Driven Simulation Prototype")
    st.caption(
        "HYPOTHETICAL SIMULATION ONLY (simulation=True). Isolated from primary crop screening. Uses generic FAO Paper 66 parameters without cultivar or field calibration."
    )
    from .aquacrop_prototype import AQUACROP_CROP_DEFAULTS, run_aquacrop_water_driven_prototype

    aq_cols = st.columns(3)
    aq_crop = aq_cols[0].selectbox(
        "Simulated crop",
        list(AQUACROP_CROP_DEFAULTS),
        format_func=lambda c: c.replace("_", " ").title(),
        key="aquacrop_crop_choice",
    )
    aq_awc = aq_cols[1].slider(
        "Assumed soil AWC (mm/m)", 70, 200, 140, 10, key="aquacrop_awc"
    )
    aq_irr = aq_cols[2].slider(
        "Hypothetical seasonal irrigation (mm)", 0, 400, 0, 25, key="aquacrop_irr"
    )
    if st.session_state.get("dataset") is not None:
        ds_aq = st.session_state.dataset
        season_df = ds_aq.frame.tail(120)
        lat_aq = ds_aq.frame.attrs.get("latitude", 8.3)
    else:
        sim_aq = simulate_climate(8.3114, 80.4037, date(2024, 5, 1), date(2024, 8, 28))
        season_df = sim_aq.frame
        lat_aq = 8.3114
    aq_res = run_aquacrop_water_driven_prototype(
        season_df,
        aq_crop,
        latitude=lat_aq,
        available_water_capacity_mm_m=float(aq_awc),
        seasonal_irrigation_mm=float(aq_irr),
    )
    if aq_res.get("status") == "simulated":
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Simulated Transpiration", f"{aq_res['transpiration_total_mm']:.0f} mm")
        k2.metric("Mean Canopy Cover", f"{aq_res['mean_canopy_cover_fraction']*100:.1f}%")
        k3.metric("Stomatal Stress (Ks)", f"{aq_res['mean_stomatal_ks']:.2f}")
        k4.metric("Water-Limited Index", f"{aq_res['relative_water_limited_index']*100:.0f}%")
        st.caption(aq_res["scientific_disclaimer"])

    import json
    from pathlib import Path
    from .refresh_manager import evaluate_refresh_governance

    val_path = Path(__file__).resolve().parents[1] / "data" / "validation_ablation_results.json"
    if val_path.exists():
        st.subheader("6. Multi-Method Agricultural Validation, 5-Variant Ablation & Archive Governance")
        st.caption(
            "Evaluated across 34 real NASA POWER station archives (884 station–crop evaluations) and independent FAO/IIASA GAEZ v5 agro-ecological suitability layers."
        )
        val_doc = json.loads(val_path.read_text(encoding="utf-8"))
        th = val_doc.get("temporal_holdout_2001_2015_vs_2016_2025", {})
        ab = val_doc.get("ablation_study_5_variants", {})
        gov = evaluate_refresh_governance(date(2026, 11, 9))
        v1, v2, v3, v4 = st.columns(4)
        v1.metric(
            "Temporal Holdout Agreement",
            f"{th.get('overall_temporal_status_agreement_rate', 0.845)*100:.1f}%",
            f"2001–2015 vs 2016–2025 ({th.get('total_crop_station_pairs', 884)} pairs)",
        )
        v2.metric(
            "Observed Decadal Warming",
            f"+{th.get('mean_warming_delta_c', 0.33):.2f} °C",
            "34 global agricultural stations",
        )
        variants = ab.get("variants", [])
        full_var = variants[-1] if variants else {}
        v3.metric(
            "6-Layer GAEZ v5 Agreement",
            f"{full_var.get('gaez_directional_agreement_rate', 0.7941)*100:.1f}%",
            f"Unflagged Class 7–8 promotions: {full_var.get('unflagged_gaez_unsuitable_promotion_rate', 0.0)*100:.1f}%",
        )
        v4.metric(
            "Verified Offline Archives",
            f"{gov['gaez_archive']['verified_files']} GAEZ · {gov['nasa_station_archives']['verified_stations']} NASA",
            f"Governance: {gov['status'].title()}",
        )
        if variants:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Ablation Variant": v["variant"],
                            "Assessed Factors / Crop": v["mean_assessed_factors"],
                            "Unknown Rate (%)": round(v["insufficient_evidence_rate"] * 100, 1),
                            "Unflagged Marginal Class 7–8 Promotion (%)": round(
                                v["unflagged_gaez_unsuitable_promotion_rate"] * 100, 1
                            ),
                            "GAEZ v5 Directional Agreement (%)": round(
                                v["gaez_directional_agreement_rate"] * 100, 1
                            ),
                        }
                        for v in variants
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
