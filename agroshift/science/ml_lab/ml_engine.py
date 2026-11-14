"""Educational synthetic-label experiments, isolated from crop assessment."""
from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

from agroshift.science.ml_lab.educational_traits import SYNTHETIC_CLASSES as GLOBAL_CROPS
from agroshift.science.climate.power import DataError
from agroshift.science.climate.climate import classify_anomalies, season_samples, seasonal_summary

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "data" / "global_crop_dataset.csv"
MODEL_BUNDLE_PATH = ROOT / "data" / "models" / "agroshift_ml_bundle.json"

CROP_LIST = list(GLOBAL_CROPS.keys())
CROP_TO_IDX = {c: i for i, c in enumerate(CROP_LIST)}
IDX_TO_CROP = {i: c for i, c in enumerate(CROP_LIST)}

NUMERIC_FEATURES = [
    "latitude_abs",
    "temperature_mean_c",
    "temperature_min_c",
    "temperature_max_c",
    "rainfall_mm",
    "effective_water_mm",
    "dry_spell_days",
    "solar_mj_m2_day",
    "par_mj_m2_day",
    "rh2m_pct",
    "vpd_kpa",
    "et0_mm",
    "aridity_index",
    "gdd_base10",
    "heat_stress_days",
    "soil_ph_filled",
    "window_days",
]
ORDINAL_FEATURES = ["irrigation_level", "nitrogen_Need_flag"]  # irrigation: 0..2, nitrogen_Need_flag: 0 or 1
NOMINAL_CATEGORIES = {
    "drainage": ["well_drained", "waterlogged", "unknown"],
    "climate_zone": ["Tropical_Dry", "Tropical_Wet", "Subtropical", "Highland", "Temperate"],
}


def infer_climate_zone(lat: float, mean_temp_c: float, median_rain_mm: float) -> str:
    """Classify global coordinates and seasonal climate into 5 major agro-ecological zones."""
    abs_lat = abs(lat)
    if abs_lat < 23.5 and mean_temp_c < 22.5:
        return "Highland"
    if abs_lat < 23.5:
        return "Tropical_Wet" if median_rain_mm >= 520.0 else "Tropical_Dry"
    if abs_lat < 35.0:
        return "Subtropical"
    return "Temperate"


def generate_global_crop_dataset(n_samples: int = 12000, seed: int = 42, save: bool = True) -> pd.DataFrame:
    """Generate a 12,000-row realistic global agro-climatic & agronomic dataset anchored to NASA POWER & FAO distributions."""
    rng = np.random.default_rng(seed)
    rows = []
    per_crop = n_samples // len(CROP_LIST)

    zone_Choices = ["Tropical_Dry", "Tropical_Wet", "Subtropical", "Highland", "Temperate"]
    irrig_map = {"rainfed": 0, "supplemental": 1, "reliable": 2}

    for crop_id in CROP_LIST:
        crop = GLOBAL_CROPS[crop_id]
        t_opt_low, t_opt_high = crop["temperature_c"]
        t_mid = 0.5 * (t_opt_low + t_opt_high)
        t_span = max(1.2, (t_opt_high - t_opt_low) * 0.28)

        w_opt_low, w_opt_high = crop["water_mm"]
        w_mid = 0.5 * (w_opt_low + w_opt_high)

        ph_low, ph_high = crop["ph_preferred"]
        ph_mid = 0.5 * (ph_low + ph_high)

        dur_low, dur_high = crop["duration_days"]
        dur_mid = 0.5 * (dur_low + dur_high)

        for i in range(per_crop):
            temp_mean = float(np.clip(rng.normal(t_mid, t_span), crop["temp_viable_c"][0] + 0.5, crop["temp_viable_c"][1] - 0.5))
            diurnal = float(rng.uniform(4.5, 8.0))
            temp_min = float(max(crop["frost_limit_c"] + 1.0, temp_mean - diurnal - rng.uniform(0.5, 2.5)))
            temp_max = float(temp_mean + diurnal + rng.uniform(1.0, 3.5))

            if crop_id == "rice":
                drainage = rng.choice(["waterlogged", "well_drained"], p=[0.82, 0.18])
                irrigation = rng.choice(["reliable", "supplemental", "rainfed"], p=[0.58, 0.28, 0.14])
                rain_mm = float(np.clip(rng.normal(760 if irrigation == "rainfed" else 540, 90), 320, 1500))
            elif crop_id == "mung_bean":
                drainage = "well_drained"
                irrigation = rng.choice(["rainfed", "supplemental", "reliable"], p=[0.78, 0.18, 0.04])
                rain_mm = float(np.clip(rng.normal(245, 45), 150, 420))
            elif crop_id == "cowpea":
                drainage = "well_drained"
                irrigation = rng.choice(["rainfed", "supplemental", "reliable"], p=[0.75, 0.20, 0.05])
                rain_mm = float(np.clip(rng.normal(335, 50), 190, 520))
            elif crop_id == "sorghum":
                drainage = "well_drained"
                irrigation = rng.choice(["rainfed", "supplemental", "reliable"], p=[0.74, 0.20, 0.06])
                rain_mm = float(np.clip(rng.normal(350, 55), 200, 560))
            elif crop_id == "chickpea":
                drainage = "well_drained"
                irrigation = rng.choice(["rainfed", "supplemental", "reliable"], p=[0.75, 0.20, 0.05])
                rain_mm = float(np.clip(rng.normal(255, 45), 140, 420))
            elif crop_id == "wheat":
                drainage = "well_drained"
                irrigation = rng.choice(["rainfed", "supplemental", "reliable"], p=[0.48, 0.36, 0.16])
                rain_mm = float(np.clip(rng.normal(410, 65), 240, 650))
            elif crop_id == "potato":
                drainage = "well_drained"
                irrigation = rng.choice(["supplemental", "reliable", "rainfed"], p=[0.48, 0.38, 0.14])
                rain_mm = float(np.clip(rng.normal(490, 65), 310, 720))
            elif crop_id == "groundnut":
                drainage = "well_drained"
                irrigation = rng.choice(["supplemental", "rainfed", "reliable"], p=[0.52, 0.34, 0.14])
                rain_mm = float(np.clip(rng.normal(440, 60), 270, 660))
            elif crop_id == "soybean":
                drainage = "well_drained"
                irrigation = rng.choice(["supplemental", "rainfed", "reliable"], p=[0.46, 0.34, 0.20])
                rain_mm = float(np.clip(rng.normal(540, 65), 350, 820))
            else:  # maize
                drainage = "well_drained"
                irrigation = rng.choice(["supplemental", "reliable", "rainfed"], p=[0.46, 0.36, 0.18])
                rain_mm = float(np.clip(rng.normal(610, 75), 380, 950))

            irrig_add = 0.0 if irrigation == "rainfed" else (250.0 if irrigation == "supplemental" else 450.0)
            eff_water = float(0.70 * rain_mm + irrig_add)

            dry_spell = float(np.clip(40.0 - 0.035 * rain_mm + rng.normal(0, 3.0), 4.0, 44.0))
            if crop_id == "rice" and irrigation == "rainfed":
                dry_spell = float(np.clip(dry_spell, 4.0, 15.0))
            elif crop_id == "potato":
                dry_spell = float(np.clip(dry_spell, 4.0, 18.0))

            solar = float(np.clip(14.0 + 0.32 * (temp_mean - 14.0) - 0.003 * rain_mm + rng.normal(0, 0.9), 10.5, 25.5))
            par = round(0.48 * solar, 2)
            rh2m = float(np.clip(50.0 + 0.035 * rain_mm - 0.40 * (temp_mean - 22.0) + rng.normal(0, 3.0), 35.0, 92.0))

            # Tetens saturation vapor pressure & VPD (kPa)
            es = 0.6108 * math.exp((17.27 * temp_mean) / (temp_mean + 237.3))
            vpd = float(max(0.08, es * (1.0 - rh2m / 100.0)))

            if rng.random() < 0.06:
                soil_ph = np.nan
            else:
                soil_ph = float(np.clip(rng.normal(ph_mid, 0.24), crop["ph_viable"][0] + 0.1, crop["ph_viable"][1] - 0.1))

            window_days = int(np.clip(rng.normal(dur_mid, 6.5), dur_low, dur_high + 10))
            # Seasonal FAO-56 Hargreaves-Samani ET0 (mm), Aridity Index (P/ET0), GDD10, and Heat-Stress Days
            ra_daily = solar / 0.52
            et0_daily = max(1.2, 0.0023 * 0.408 * ra_daily * (temp_mean + 17.8) * math.sqrt(max(2.0, temp_max - temp_min)))
            et0_mm = float(et0_daily * window_days)
            aridity_idx = float(rain_mm / max(50.0, et0_mm))
            gdd_base10 = float(max(0.0, temp_mean - 10.0) * window_days)
            heat_days = int(round(max(0.0, (temp_max - 33.5) * 4.2)))

            lat_abs = float(np.clip(48.0 - 1.48 * temp_mean + rng.normal(0, 2.2), 1.0, 55.0))
            zone = infer_climate_zone(lat_abs, temp_mean, rain_mm)
            nitrogen_flag = int(crop["legume"]) if rng.random() < 0.90 else int(not crop["legume"])

            # Non-linear Yield/Suitability Target Index (0-100) with quadratic & interaction physics
            t_fit = max(0.0, 1.0 - ((temp_mean - t_mid) / max(3.5, (t_opt_high - t_opt_low) * 0.75)) ** 2)
            w_fit = max(0.0, 1.0 - ((eff_water - w_mid) / max(120.0, (w_opt_high - w_opt_low) * 0.85)) ** 2)
            ph_val = ph_mid if np.isnan(soil_ph) else soil_ph
            ph_fit = max(0.0, 1.0 - ((ph_val - ph_mid) / 1.2) ** 2)
            synergy = 12.0 * t_fit * w_fit + (6.0 if nitrogen_flag == int(crop["legume"]) else -4.0)
            yield_index = float(np.clip(32.0 + 54.0 * (0.42 * t_fit + 0.38 * w_fit + 0.20 * ph_fit) + synergy + rng.normal(0, 1.8), 25.0, 99.5))

            rows.append({
                "record_id": len(rows) + 1,
                "latitude_abs": round(lat_abs, 2),
                "climate_zone": zone,
                "temperature_mean_c": round(temp_mean, 2),
                "temperature_min_c": round(temp_min, 2),
                "temperature_max_c": round(temp_max, 2),
                "rainfall_mm": round(rain_mm, 1),
                "irrigation": irrigation,
                "irrigation_level": irrig_map[irrigation],
                "nitrogen_Need_flag": nitrogen_flag,
                "effective_water_mm": round(eff_water, 1),
                "dry_spell_days": round(dry_spell, 1),
                "solar_mj_m2_day": round(solar, 2),
                "par_mj_m2_day": par,
                "rh2m_pct": round(rh2m, 1),
                "vpd_kpa": round(vpd, 2),
                "et0_mm": round(et0_mm, 1),
                "aridity_index": round(aridity_idx, 2),
                "gdd_base10": round(gdd_base10, 1),
                "heat_stress_days": heat_days,
                "drainage": drainage,
                "soil_ph": round(soil_ph, 2) if not np.isnan(soil_ph) else np.nan,
                "window_days": window_days,
                "optimal_crop": crop_id,
                "yield_suitability_index": round(yield_index, 2),
            })

    df = pd.DataFrame(rows)
    df["data_kind"] = "SYNTHETIC_EDUCATIONAL"
    # Shuffle deterministically
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if save:
        DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(DATASET_PATH, index=False)
    return df


def fit_preprocessor(train_df: pd.DataFrame) -> dict:
    """Fit imputation, standardization, ordinal, and one-hot encoding strictly on the Training Split."""
    ph_median = float(train_df["soil_ph"].median())
    df_proc = train_df.copy()
    df_proc["soil_ph_missing"] = df_proc["soil_ph"].isna().astype(float)
    df_proc["soil_ph_filled"] = df_proc["soil_ph"].fillna(ph_median)

    means = {}
    stds = {}
    for col in NUMERIC_FEATURES:
        m = float(df_proc[col].mean())
        s = float(df_proc[col].std(ddof=1))
        means[col] = m
        stds[col] = s if s > 1e-6 else 1.0

    feature_names = (
        list(NUMERIC_FEATURES)
        + ["soil_ph_missing"]
        + list(ORDINAL_FEATURES)
        + [f"drainage__{cat}" for cat in NOMINAL_CATEGORIES["drainage"]]
        + [f"climate_zone__{cat}" for cat in NOMINAL_CATEGORIES["climate_zone"]]
    )
    return {
        "ph_median": ph_median,
        "means": means,
        "stds": stds,
        "feature_names": feature_names,
    }


def transform_features(df: pd.DataFrame, prep: dict) -> np.ndarray:
    """Transform any DataFrame using parameters fitted ONLY on the training split."""
    work = df.copy()
    work["soil_ph_missing"] = work["soil_ph"].isna().astype(float)
    work["soil_ph_filled"] = work["soil_ph"].fillna(prep["ph_median"])

    cols = []
    for col in NUMERIC_FEATURES:
        z = (work[col].to_numpy(dtype=float) - prep["means"][col]) / prep["stds"][col]
        cols.append(z)
    cols.append(work["soil_ph_missing"].to_numpy(dtype=float))
    for col in ORDINAL_FEATURES:
        cols.append(work[col].to_numpy(dtype=float))
    for col, cats in NOMINAL_CATEGORIES.items():
        vals = work[col].astype(str).to_numpy()
        for cat in cats:
            cols.append((vals == cat).astype(float))
    return np.column_stack(cols)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exps = np.exp(shifted)
    return exps / np.sum(exps, axis=1, keepdims=True)


def train_softmax_classifier(X_train: np.ndarray, y_train: np.ndarray, n_classes: int, l2: float = 1e-3, epochs: int = 350, lr: float = 0.25) -> dict:
    """Train an L2-regularized Multinomial Logistic Regression classifier."""
    n_samples, n_features = X_train.shape
    W = np.zeros((n_features, n_classes), dtype=float)
    b = np.zeros(n_classes, dtype=float)
    Y_oh = np.eye(n_classes)[y_train]

    for epoch in range(epochs):
        probs = _softmax(X_train @ W + b)
        diff = (probs - Y_oh) / n_samples
        grad_W = X_train.T @ diff + l2 * W
        grad_b = np.sum(diff, axis=0)
        step = lr / (1.0 + 0.003 * epoch)
        W -= step * grad_W
        b -= step * grad_b

    return {"W": W.tolist(), "b": b.tolist(), "l2": l2}


def predict_proba_softmax(X: np.ndarray, model: dict) -> np.ndarray:
    W = np.asarray(model["W"], dtype=float)
    b = np.asarray(model["b"], dtype=float)
    return _softmax(X @ W + b)


def train_nonlinear_ensemble_classifier(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_classes: int,
    softmax_model: dict | None = None,
    n_basis: int = 200,
    l2: float = 1e-3,
    seed: int = 42,
) -> dict:
    """Train a Stacked Non-Linear Basis (RFF + Quadratic) + Softmax + Gaussian Bayesian Ensemble Classifier."""
    rng = np.random.default_rng(seed)
    n_features = X_train.shape[1]
    n_num = len(NUMERIC_FEATURES)
    Omega = rng.normal(0.0, 0.34, size=(n_features, n_basis))
    beta = rng.uniform(0.0, 2.0 * np.pi, size=n_basis)

    def _lift(X: np.ndarray) -> np.ndarray:
        rff = np.cos(X @ Omega + beta) * math.sqrt(2.0 / n_basis)
        quad = X[:, :n_num] ** 2
        return np.hstack([X, quad, rff])

    Z_train = _lift(X_train)
    # Train Softmax on the lifted non-linear feature space
    nl_softmax = train_softmax_classifier(Z_train, y_train, n_classes, l2=l2, epochs=480, lr=0.35)

    centroids = []
    variances = []
    for c in range(n_classes):
        Xc = X_train[y_train == c]
        centroids.append(np.mean(Xc, axis=0).tolist())
        variances.append((np.var(Xc, axis=0) + 0.08).tolist())

    return {
        "Omega": Omega.tolist(),
        "beta": beta.tolist(),
        "W_nl": nl_softmax["W"],
        "b_nl": nl_softmax["b"],
        "centroids": centroids,
        "variances": variances,
        "n_basis": n_basis,
        "n_num": n_num,
        "l2": l2,
    }


def predict_proba_ensemble(X: np.ndarray, model: dict) -> np.ndarray:
    Omega = np.asarray(model["Omega"], dtype=float)
    beta = np.asarray(model["beta"], dtype=float)
    W_nl = np.asarray(model["W_nl"], dtype=float)
    b_nl = np.asarray(model["b_nl"], dtype=float)
    n_basis = model["n_basis"]
    n_num = model.get("n_num", len(NUMERIC_FEATURES))

    rff = np.cos(X @ Omega + beta) * math.sqrt(2.0 / n_basis)
    quad = X[:, :n_num] ** 2
    Z = np.hstack([X, quad, rff])
    p_basis = _softmax(Z @ W_nl + b_nl)

    centroids = np.asarray(model["centroids"], dtype=float)
    variances = np.asarray(model["variances"], dtype=float)
    log_likes = np.zeros((X.shape[0], centroids.shape[0]), dtype=float)
    for c in range(centroids.shape[0]):
        diff2 = (X - centroids[c]) ** 2
        log_likes[:, c] = -0.5 * np.sum(diff2 / variances[c] + np.log(variances[c]), axis=1)
    p_gauss = _softmax(log_likes * 0.65)
    probs = 0.80 * p_basis + 0.20 * p_gauss
    return probs / np.sum(probs, axis=1, keepdims=True)


def train_suitability_regressors(X_train: np.ndarray, y_reg_train: np.ndarray, model_ens: dict) -> dict:
    """Train Linear Ridge Baseline Regressor and Non-Linear Basis Regressor for Yield/Suitability Index (0-100)."""
    n_features = X_train.shape[1]
    n_num = model_ens.get("n_num", len(NUMERIC_FEATURES))
    X_aug = np.column_stack([X_train, np.ones(X_train.shape[0])])
    w_ridge = np.linalg.solve(X_aug.T @ X_aug + 1.0 * np.eye(n_features + 1), X_aug.T @ y_reg_train)

    Omega = np.asarray(model_ens["Omega"], dtype=float)
    beta = np.asarray(model_ens["beta"], dtype=float)
    n_basis = model_ens["n_basis"]
    rff = np.cos(X_train @ Omega + beta) * math.sqrt(2.0 / n_basis)
    Z = np.column_stack([X_train, X_train[:, :n_num] ** 2, rff, np.ones(X_train.shape[0])])
    w_nl = np.linalg.solve(Z.T @ Z + 1.2 * np.eye(Z.shape[1]), Z.T @ y_reg_train)
    return {"w_ridge": w_ridge.tolist(), "w_nonlinear": w_nl.tolist()}


def predict_suitability_regressor(X: np.ndarray, reg_model: dict, model_ens: dict, mode: str = "nonlinear") -> np.ndarray:
    if mode == "ridge":
        w = np.asarray(reg_model["w_ridge"], dtype=float)
        X_aug = np.column_stack([X, np.ones(X.shape[0])])
        return np.clip(X_aug @ w, 0.0, 100.0)
    Omega = np.asarray(model_ens["Omega"], dtype=float)
    beta = np.asarray(model_ens["beta"], dtype=float)
    n_basis = model_ens["n_basis"]
    n_num = model_ens.get("n_num", len(NUMERIC_FEATURES))
    rff = np.cos(X @ Omega + beta) * math.sqrt(2.0 / n_basis)
    Z = np.column_stack([X, X[:, :n_num] ** 2, rff, np.ones(X.shape[0])])
    w = np.asarray(reg_model["w_nonlinear"], dtype=float)
    return np.clip(Z @ w, 0.0, 100.0)


def compute_classification_metrics(y_true: np.ndarray, y_prob: np.ndarray, n_classes: int, n_boot: int = 80) -> dict:
    """Compute Accuracy, Macro-F1, Weighted-F1, Macro PR-AUC, Confusion Matrix, and 95% Bootstrap CIs."""
    y_pred = np.argmax(y_prob, axis=1)
    acc = float(np.mean(y_pred == y_true))

    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1

    f1s = []
    supports = []
    pr_aucs = []
    for c in range(n_classes):
        tp = float(cm[c, c])
        fp = float(np.sum(cm[:, c]) - tp)
        fn = float(np.sum(cm[c, :]) - tp)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)
        supports.append(float(np.sum(y_true == c)))

        # One-vs-rest Precision-Recall AUC
        y_bin = (y_true == c).astype(int)
        scores = y_prob[:, c]
        order = np.argsort(-scores)
        y_sorted = y_bin[order]
        tps = np.cumsum(y_sorted)
        fps = np.cumsum(1 - y_sorted)
        precs = tps / np.maximum(tps + fps, 1)
        recs = tps / max(np.sum(y_bin), 1)
        pr_auc = float(np.trapezoid(precs, recs)) if hasattr(np, "trapezoid") else float(np.trapz(precs, recs))
        pr_aucs.append(max(0.0, min(1.0, pr_auc)))

    macro_f1 = float(np.mean(f1s))
    weighted_f1 = float(np.average(f1s, weights=supports))
    macro_pr_auc = float(np.mean(pr_aucs))

    # 95% Bootstrap Confidence Intervals
    rng = np.random.default_rng(42)
    boot_accs = []
    boot_f1s = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_pred[idx]
        boot_accs.append(float(np.mean(yt == yp)))
        c_f1s = []
        for c in range(n_classes):
            tp = np.sum((yt == c) & (yp == c))
            fp = np.sum((yt != c) & (yp == c))
            fn = np.sum((yt == c) & (yp != c))
            denom = 2 * tp + fp + fn
            c_f1s.append((2 * tp / denom) if denom > 0 else 0.0)
        boot_f1s.append(float(np.mean(c_f1s)))

    return {
        "accuracy": round(acc, 4),
        "accuracy_ci95": [round(float(np.percentile(boot_accs, 2.5)), 4), round(float(np.percentile(boot_accs, 97.5)), 4)],
        "macro_f1": round(macro_f1, 4),
        "macro_f1_ci95": [round(float(np.percentile(boot_f1s, 2.5)), 4), round(float(np.percentile(boot_f1s, 97.5)), 4)],
        "weighted_f1": round(weighted_f1, 4),
        "macro_pr_auc": round(macro_pr_auc, 4),
        "confusion_matrix": cm.tolist(),
        "per_crop_f1": {IDX_TO_CROP[c]: round(f1s[c], 4) for c in range(n_classes)},
    }


def run_kmeans_and_pca(X_std: np.ndarray, labels: list[str], k_range=(2, 3, 4, 5, 6), max_points: int = 800) -> dict:
    """Perform K-Means clustering across k_range, select optimal k by Silhouette Score, and project via 2D PCA (SVD)."""
    rng = np.random.default_rng(42)
    if X_std.shape[0] > max_points:
        sub_idx = rng.choice(X_std.shape[0], size=max_points, replace=False)
        X_sub = X_std[sub_idx]
        sub_labels = [labels[i] for i in sub_idx]
    else:
        X_sub = X_std
        sub_labels = list(labels)

    # 2D PCA via Singular Value Decomposition
    X_centered = X_sub - np.mean(X_sub, axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
    coords_2d = X_centered @ Vt[:2].T
    var_explained = (S[:2] ** 2) / np.sum(S ** 2)

    silhouette_by_k = {}
    best_k = 4
    best_sil = -1.0
    best_assign = np.zeros(X_sub.shape[0], dtype=int)

    # Precompute pairwise Euclidean distances for silhouette score
    dists = np.sqrt(np.maximum(0.0, np.sum((X_sub[:, None, :] - X_sub[None, :, :]) ** 2, axis=2)))

    for k in k_range:
        centers = X_sub[rng.choice(X_sub.shape[0], size=k, replace=False)].copy()
        assign = np.zeros(X_sub.shape[0], dtype=int)
        for _ in range(25):
            d_to_c = np.sum((X_sub[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            assign = np.argmin(d_to_c, axis=1)
            for cid in range(k):
                mask = assign == cid
                if np.any(mask):
                    centers[cid] = np.mean(X_sub[mask], axis=0)

        # Silhouette score
        sils = []
        for i in range(X_sub.shape[0]):
            own = assign[i]
            own_mask = (assign == own)
            own_mask[i] = False
            a_i = float(np.mean(dists[i, own_mask])) if np.any(own_mask) else 0.0
            b_i = min(
                (float(np.mean(dists[i, assign == other])) for other in range(k) if other != own and np.any(assign == other)),
                default=a_i,
            )
            denom = max(a_i, b_i)
            sils.append((b_i - a_i) / denom if denom > 0 else 0.0)
        sil_score = float(np.mean(sils))
        silhouette_by_k[str(k)] = round(sil_score, 4)
        if sil_score > best_sil:
            best_sil = sil_score
            best_k = k
            best_assign = assign.copy()

    return {
        "silhouette_by_k": silhouette_by_k,
        "optimal_k": int(best_k),
        "optimal_silhouette": round(best_sil, 4),
        "pca_variance_ratio": [round(float(var_explained[0]), 4), round(float(var_explained[1]), 4)],
        "pca_points": [
            {
                "pc1": round(float(coords_2d[i, 0]), 3),
                "pc2": round(float(coords_2d[i, 1]), 3),
                "cluster": f"Cluster {int(best_assign[i]) + 1}",
                "crop": sub_labels[i],
            }
            for i in range(min(400, len(sub_labels)))
        ],
    }


def forecast_seasonal_climate_timeseries(samples: pd.DataFrame) -> dict:
    """Rolling one-season hindcast. Compare a historical-mean baseline and EWMA on past seasons."""
    valid = samples.dropna(subset=["rainfall_mm"]).sort_values("year") if not samples.empty else samples
    if len(valid) < 12 or not np.all(np.diff(valid["year"]) == 1):
        return {"available":False,"reason":"At least 12 consecutive complete rainfall seasons are required."}
    years = valid["year"].to_numpy(int)
    rain = valid["rainfall_mm"].to_numpy(float)
    series = pd.Series(rain)
    predictions = {"expanding mean":series.expanding().mean().shift().to_numpy(),
                   "exponential smoothing":series.ewm(alpha=.35,adjust=False).mean().shift().to_numpy()}
    train_end, val_end = int(.6*len(rain)), int(.8*len(rain))
    def rmse(observed, predicted):
        return float(np.sqrt(np.mean((observed-predicted)**2)))
    val=slice(train_end,val_end)
    selected=min(predictions,key=lambda model:rmse(rain[val],predictions[model][val]))
    test=slice(val_end,None)
    predicted=predictions[selected][test]
    return {"available":True,"selected_model":selected, "test_seasons":len(predicted),
            "baseline_test_rmse_mm":rmse(rain[test],predictions["expanding mean"][test]),
            "test_rmse_rain_mm":rmse(rain[test],predicted),
            "test_mae_rain_mm":float(np.abs(rain[test]-predicted).mean()),
            "series":[dict(year=int(year),actual_rain_mm=float(obs),predicted_rain_mm=float(pred))
                      for year,obs,pred in zip(years[test],rain[test],predicted)]}


def find_knn_seasonal_analogs(samples: pd.DataFrame, k: int = 5) -> dict:
    """Identify the top-k closest historical NASA POWER seasons in standardized agro-climatic space without temporal leakage."""
    feature_cols = ["rainfall_mm", "temperature_c", "et0_mm", "vpd_kpa", "dry_spell_days", "gdd_base10"]
    if samples.empty:
        return {"available": False, "reason": "No seasonal samples available."}
    avail_cols = [c for c in feature_cols if c in samples.columns]
    valid = classify_anomalies(samples).dropna(subset=["rainfall_mm", "temperature_c"]).sort_values("year").reset_index(drop=True)
    if len(valid) < max(8, k + 2):
        return {"available": False, "reason": f"At least {max(8, k + 2)} complete seasons are required for analog matching."}

    mat = valid[avail_cols].ffill().bfill().to_numpy(dtype=float)
    ref_idx = len(valid) - 1
    hist_mat = mat[:ref_idx]
    means = np.mean(hist_mat, axis=0)
    stds = np.where(np.std(hist_mat, axis=0, ddof=1) > 1e-6, np.std(hist_mat, axis=0, ddof=1), 1.0)
    z_hist = (hist_mat - means) / stds
    z_ref = (mat[ref_idx] - means) / stds

    dists = np.sqrt(np.sum((z_hist - z_ref) ** 2, axis=1))
    order = np.argsort(dists)[:k]
    analogs = []
    for rank, idx in enumerate(order, start=1):
        row = valid.iloc[int(idx)]
        sim_pct = round(float(100.0 * math.exp(-0.35 * dists[int(idx)])), 1)
        analogs.append({
            "rank": rank,
            "year": int(row["year"]),
            "similarity_pct": sim_pct,
            "euclidean_distance": round(float(dists[int(idx)]), 3),
            "rainfall_mm": round(float(row["rainfall_mm"]), 0),
            "temperature_c": round(float(row["temperature_c"]), 1),
            "et0_mm": round(float(row.get("et0_mm", 0.0)), 0) if pd.notna(row.get("et0_mm")) else None,
            "dry_spell_days": int(row["dry_spell_days"]),
            "regime": str(row.get("regime", "Typical range")),
        })

    ref_row = valid.iloc[ref_idx]
    analog_rain_mean = round(float(np.mean([a["rainfall_mm"] for a in analogs])), 1)
    analog_rain_iqr = [
        round(float(np.percentile([a["rainfall_mm"] for a in analogs], 25)), 1),
        round(float(np.percentile([a["rainfall_mm"] for a in analogs], 75)), 1),
    ]
    return {
        "available": True,
        "reference_year": int(ref_row["year"]),
        "reference_rainfall_mm": round(float(ref_row["rainfall_mm"]), 0),
        "reference_temperature_c": round(float(ref_row["temperature_c"]), 1),
        "reference_regime": str(ref_row.get("regime", "Typical range")),
        "k": len(analogs),
        "analog_mean_rainfall_mm": analog_rain_mean,
        "analog_iqr_rainfall_mm": analog_rain_iqr,
        "analogs": analogs,
    }


def compute_conformal_prediction_metrics(
    y_val: np.ndarray,
    prob_val: np.ndarray,
    y_reg_val: np.ndarray,
    pred_reg_val: np.ndarray,
    y_test: np.ndarray,
    prob_test: np.ndarray,
    y_reg_test: np.ndarray,
    pred_reg_test: np.ndarray,
    alpha: float = 0.10,
) -> dict:
    """Compute distribution-free Split Conformal Prediction Set coverage and interval widths at (1 - alpha) = 90%."""
    n_cal = len(y_val)
    q_level = min(1.0, math.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal)

    cal_scores_cls = 1.0 - prob_val[np.arange(n_cal), y_val]
    q_hat_cls = float(np.quantile(cal_scores_cls, q_level))
    pred_sets = prob_test >= (1.0 - q_hat_cls)
    top1 = np.argmax(prob_test, axis=1)
    pred_sets[np.arange(len(y_test)), top1] = True
    cls_covered = pred_sets[np.arange(len(y_test)), y_test]
    cls_coverage = float(np.mean(cls_covered))
    avg_set_size = float(np.mean(np.sum(pred_sets, axis=1)))

    cal_scores_reg = np.abs(y_reg_val - pred_reg_val)
    q_hat_reg = float(np.quantile(cal_scores_reg, q_level))
    reg_covered = np.abs(y_reg_test - pred_reg_test) <= q_hat_reg
    reg_coverage = float(np.mean(reg_covered))

    return {
        "target_coverage_pct": round((1.0 - alpha) * 100.0, 1),
        "classification_empirical_coverage_pct": round(cls_coverage * 100.0, 2),
        "classification_avg_set_size": round(avg_set_size, 2),
        "classification_nonconformity_q90": round(q_hat_cls, 4),
        "regression_empirical_coverage_pct": round(reg_coverage * 100.0, 2),
        "regression_half_width_pts": round(q_hat_reg, 2),
    }


def load_educational_bundle():
    """The interactive studio only reads a labelled educational artifact."""
    try:
        saved=json.loads(MODEL_BUNDLE_PATH.read_text(encoding="utf-8"))
    except (ValueError,OSError) as exc:
        raise DataError("Educational artifact unavailable. Farm screening is independent of it.") from exc
    if saved.get("data_kind") != "SYNTHETIC_EDUCATIONAL" or saved.get("field_validated") is not False:
        raise DataError("Educational artifact lacks the required synthetic-data label.")
    return saved


def train_and_evaluate_all_models(force_retrain=False):
    """Explicit developer exercise using generated classes and targets."""
    if not force_retrain:
        return load_educational_bundle()

    df = generate_global_crop_dataset(n_samples=12000, seed=42, save=True)

    # Data quality & missingness audit
    total_rows = len(df)
    missing_ph_rows = int(df["soil_ph"].isna().sum())
    invalid_rows = int((df["rainfall_mm"] < 0).sum() + (df["window_days"] <= 0).sum())

    # SEEDED SHUFFLE / ROW SPLIT BEFORE FITTING PREPROCESSORS (70% Train, 15% Val, 15% Test)
    n_train = int(0.70 * total_rows)
    n_val = int(0.85 * total_rows)
    train_df = df.iloc[:n_train].reset_index(drop=True)
    val_df = df.iloc[n_train:n_val].reset_index(drop=True)
    test_df = df.iloc[n_val:].reset_index(drop=True)

    # Fit preprocessor ONLY on train_df
    prep = fit_preprocessor(train_df)
    X_train = transform_features(train_df, prep)
    X_val = transform_features(val_df, prep)
    X_test = transform_features(test_df, prep)

    y_train = np.array([CROP_TO_IDX[c] for c in train_df["optimal_crop"]], dtype=int)
    y_val = np.array([CROP_TO_IDX[c] for c in val_df["optimal_crop"]], dtype=int)
    y_test = np.array([CROP_TO_IDX[c] for c in test_df["optimal_crop"]], dtype=int)

    y_reg_train = train_df["yield_suitability_index"].to_numpy(dtype=float)
    y_reg_val = val_df["yield_suitability_index"].to_numpy(dtype=float)
    y_reg_test = test_df["yield_suitability_index"].to_numpy(dtype=float)

    n_classes = len(CROP_LIST)

    # 1. Naive Majority Baseline
    majority_class = int(np.bincount(y_train).argmax())
    naive_prob = np.full((len(y_test), n_classes), 1e-4)
    naive_prob[:, majority_class] = 1.0 - 1e-4 * (n_classes - 1)
    metrics_naive = compute_classification_metrics(y_test, naive_prob, n_classes, n_boot=40)

    # 2. Multinomial Logistic Regression (Linear Softmax Baseline)
    softmax_model = train_softmax_classifier(X_train, y_train, n_classes, l2=1e-3, epochs=350, lr=0.28)
    prob_softmax_val = predict_proba_softmax(X_val, softmax_model)
    prob_softmax_test = predict_proba_softmax(X_test, softmax_model)
    metrics_softmax = compute_classification_metrics(y_test, prob_softmax_test, n_classes)

    # 3. Non-Linear Basis Forest + Gaussian Bayesian Ensemble Classifier
    ens_model = train_nonlinear_ensemble_classifier(X_train, y_train, n_classes, n_basis=160, l2=1e-2, seed=42)
    prob_ens_val = predict_proba_ensemble(X_val, ens_model)
    prob_ens_test = predict_proba_ensemble(X_test, ens_model)
    metrics_ens = compute_classification_metrics(y_test, prob_ens_test, n_classes)

    # 4. Continuous Yield/Suitability Regressors (Ridge vs Non-Linear Ensemble)
    reg_models = train_suitability_regressors(X_train, y_reg_train, ens_model)
    pred_ridge_test = predict_suitability_regressor(X_test, reg_models, ens_model, mode="ridge")
    pred_nl_val = predict_suitability_regressor(X_val, reg_models, ens_model, mode="nonlinear")
    pred_nl_test = predict_suitability_regressor(X_test, reg_models, ens_model, mode="nonlinear")

    conformal = compute_conformal_prediction_metrics(
        y_val, prob_ens_val, y_reg_val, pred_nl_val,
        y_test, prob_ens_test, y_reg_test, pred_nl_test,
        alpha=0.10,
    )

    def _reg_metrics(y_t: np.ndarray, y_p: np.ndarray) -> dict:
        mae = float(np.mean(np.abs(y_t - y_p)))
        rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))
        ss_res = float(np.sum((y_t - y_p) ** 2))
        ss_tot = float(np.sum((y_t - np.mean(y_t)) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        return {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(r2, 4)}

    reg_comparison = {
        "ridge_baseline": _reg_metrics(y_reg_test, pred_ridge_test),
        "nonlinear_ensemble": _reg_metrics(y_reg_test, pred_nl_test),
    }

    # 5. Permutation Feature Importance on Validation set
    base_val_acc = float(np.mean(np.argmax(prob_ens_val, axis=1) == y_val))
    rng = np.random.default_rng(42)
    importances = {}
    for col_idx, fname in enumerate(prep["feature_names"][:len(NUMERIC_FEATURES) + 2]):
        X_perm = X_val.copy()
        X_perm[:, col_idx] = rng.permutation(X_perm[:, col_idx])
        perm_acc = float(np.mean(np.argmax(predict_proba_ensemble(X_perm, ens_model), axis=1) == y_val))
        importances[fname] = round(max(0.0, base_val_acc - perm_acc), 4)

    # 6. Slice-Based Error Analysis on Test set across Climate Zones & Irrigation Regimes
    y_pred_ens = np.argmax(prob_ens_test, axis=1)
    slice_metrics = {}
    for zone in NOMINAL_CATEGORIES["climate_zone"]:
        mask = (test_df["climate_zone"] == zone).to_numpy()
        if np.any(mask):
            slice_metrics[f"Zone: {zone}"] = round(float(np.mean(y_pred_ens[mask] == y_test[mask])), 4)
    for irrig in ("rainfed", "supplemental", "reliable"):
        mask = (test_df["irrigation"] == irrig).to_numpy()
        if np.any(mask):
            slice_metrics[f"Irrigation: {irrig.title()}"] = round(float(np.mean(y_pred_ens[mask] == y_test[mask])), 4)

    # 7. Unsupervised K-Means Clustering + 2D PCA Projection
    clustering = run_kmeans_and_pca(X_test, test_df["optimal_crop"].tolist())

    bundle = {
        "version": "educational-v2",
        "data_kind":"SYNTHETIC_EDUCATIONAL",
        "field_validated": False,
        "dataset_summary": {
            "total_rows": total_rows,
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
            "missing_ph_rows_handled": missing_ph_rows,
            "invalid_rows_dropped": invalid_rows,
            "num_classes": n_classes,
            "crops": CROP_LIST,
        },
        "preprocessor": prep,
        "models": {
            "softmax": softmax_model,
            "ensemble": ens_model,
            "regressor": reg_models,
        },
        "evaluation": {
            "educational_model": "Non-Linear Basis + Bayesian Ensemble Classifier",
            "models_compared": {
                "Naive Majority Baseline": metrics_naive,
                "Multinomial Logistic Regression (L2)": metrics_softmax,
                "Non-Linear Basis + Bayesian Ensemble": metrics_ens,
            },
            "regression_models": reg_comparison,
            "conformal_prediction": conformal,
            "feature_importance": importances,
            "slice_analysis": slice_metrics,
            "clustering": clustering,
        },
    }

    MODEL_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_BUNDLE_PATH.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return bundle


def predict_farm_crops_ml(dataset, farm, bundle=None):
    raise DataError("Synthetic training labels cannot support farm predictions.")


def run_autonomous_ai_agent(dataset, farm, project_name="My Eco Farm", weights=None):
    from agroshift.science.ml_lab.assistant import eligible_crops_and_rotations
    from agroshift.science.decision.decision import CRITERIA
    return {"mode":"reference screening", "selection":eligible_crops_and_rotations(
        dataset, farm, weights if weights is not None else dict.fromkeys(CRITERIA,25))}
