"""Train, validate, compare, and persist the AgroShift AI Machine Learning Models & 12,000-row Global Dataset."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agroshift.ml_engine import DATASET_PATH, MODEL_BUNDLE_PATH, train_and_evaluate_all_models


def main():
    bundle = train_and_evaluate_all_models(force_retrain=True)
    ds = bundle["dataset_summary"]
    ev = bundle["evaluation"]
    print(f"Synthetic educational examples generated: {DATASET_PATH} ({ds['total_rows']:,} rows; Train={ds['train_rows']:,}, Val={ds['val_rows']:,}, Test={ds['test_rows']:,})")
    print(f"Model bundle saved: {MODEL_BUNDLE_PATH}")
    for name, m in ev["models_compared"].items():
        print(f"  - {name}: Synthetic label agreement={m['accuracy']*100:.2f}% (95% CI: {m['accuracy_ci95']}), Macro-F1={m['macro_f1']:.4f}, PR-AUC={m['macro_pr_auc']:.4f}")
    print("Simulated target metrics:", ev["regression_models"])
    print(f"K-Means optimal k={ev['clustering']['optimal_k']} (Silhouette={ev['clustering']['optimal_silhouette']})")


if __name__ == "__main__":
    main()
