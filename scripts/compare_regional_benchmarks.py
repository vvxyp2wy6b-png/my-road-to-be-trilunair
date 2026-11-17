#!/usr/bin/env python3
"""
CLI Aggregator for QUANTUM TRILUNAIR Regional Benchmark Probes & Weighted Decision Matrix.
Usage:
  python3 scripts/compare_regional_benchmarks.py [--probes-dir backend/data/regional_probes] [--format markdown|json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.region_benchmark import evaluate_hosting_decision_matrix  # noqa: E402


def render_markdown(matrix: dict) -> str:
    lines = [
        "# QUANTUM TRILUNAIR — Weighted Cloud Region Decision Matrix",
        "",
        f"- **Selection Status:** `{matrix['selectionStatus']}`",
        f"- **Target Domain:** `{matrix['targetDomain']}` (Isolated from `{matrix['isolatedMedicalDomain']}`)",
        f"- **Verified Regional Cloud Probes Ingested:** `{matrix['regionalProbesIngestedCount']}`",
        f"- **Provisional / Primary Winner:** **{matrix['recommendedPrimaryOption']['regionNameEn']}** — "
        f"`{matrix['recommendedPrimaryOption']['provider']}` (Score: `{matrix['recommendedPrimaryOption']['weightedScore']}/100`, "
        f"Cost: `${matrix['recommendedPrimaryOption']['monthlyCostUsd']:.2f}/mo`)",
        f"- **Instant Paid SLA Fallback:** **{matrix['recommendedPaidSlaFallbackOption']['regionNameEn']}** — "
        f"`{matrix['recommendedPaidSlaFallbackOption']['provider']}` (Score: `{matrix['recommendedPaidSlaFallbackOption']['weightedScore']}/100`, "
        f"Cost: `${matrix['recommendedPaidSlaFallbackOption']['monthlyCostUsd']:.2f}/mo`)",
        "",
        "## Qualified Options Ranking",
        "",
        "| Rank | Region | Provider | Cost/mo | Regional Probe | REST P50 | Weighted Score |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for idx, opt in enumerate(matrix["rankedQualifiedOptions"], start=1):
        p50 = opt["measuredProbeSummary"].get("restP50Ms")
        p50_str = f"{p50:.2f} ms" if isinstance(p50, (int, float)) else "NOT MEASURED"
        lines.append(
            f"| {idx} | {opt['regionNameEn']} (`{opt['regionCode']}`) | {opt['provider']} | "
            f"${opt['monthlyCostUsd']:.2f} | `{opt['regionalMeasurementStatus']}` | `{p50_str}` | **{opt['weightedScore']:.2f}** |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate TRILUNAIR Regional Hosting Decision Matrix")
    parser.add_argument("--probes-dir", default=None, help="Directory containing CLOUD_REGIONAL_VM JSON probe files")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    probes_path = Path(args.probes_dir) if args.probes_dir else None
    matrix = evaluate_hosting_decision_matrix(probes_dir=probes_path)
    if args.format == "json":
        print(json.dumps(matrix, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(matrix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
