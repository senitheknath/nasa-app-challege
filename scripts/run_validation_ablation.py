"""Run agricultural validation (geographic/temporal holdouts & missing-data stress) and 5-variant ablation study."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroshift.validation import (
    evaluate_missing_data_stress,
    evaluate_temporal_holdout,
    run_ablation_study,
)


def main():
    temporal = evaluate_temporal_holdout()
    stress = evaluate_missing_data_stress("nairobi_kenya")
    ablation = run_ablation_study()
    payload = {
        "generated_on": "2026-11-09",
        "temporal_holdout_2001_2015_vs_2016_2025": temporal,
        "missing_data_stress_test": stress,
        "ablation_study_5_variants": ablation,
    }
    out_path = ROOT / "data" / "validation_ablation_results.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Temporal holdout agreement: {temporal['overall_temporal_status_agreement_rate']:.1%}")
    print(f"Mean warming delta (2016-2025 vs 2001-2015): {temporal['mean_warming_delta_c']:+.3f} °C")
    print(f"Missing-data conservative fallback verified: {stress['conservative_fallback_verified']}")
    for row in ablation["variants"]:
        print(
            f"  {row['variant']:38s} | factors={row['mean_assessed_factors']:.2f} "
            f"| unknown={row['insufficient_evidence_rate']:.1%} "
            f"| unflagged_gaez_unsuitable={row['unflagged_gaez_unsuitable_promotion_rate']:.1%} "
            f"| gaez_agreement={row['gaez_directional_agreement_rate']:.1%}"
        )


if __name__ == "__main__":
    main()
