"""
Member 3 benchmark runner.

Outputs requested by the workflow:
  - data/member3_perfect.csv
  - results.csv
  - threshold_plot.png, produced by plot_results.py

The 0 to 0.05 sweep uses 1000 Monte Carlo shots by default.  The extended
threshold scan is exact density-matrix data, used only to identify where QEC
starts to hurt relative to an unencoded qubit.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

import numpy as np

from qec_5qubit_project import (
    build_correction_table,
    configure_logging,
    derive_code_basis,
    encode_state,
    estimate_intersection,
    logical_state,
    run_random_noise_trials,
    run_threshold_scan,
    write_csv,
    write_json,
)


LOGGER = logging.getLogger("member3_runner")


def default_physical_error_rates() -> List[float]:
    return [0.0, 0.001, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05]


def build_member3_rows(random_rows: Sequence[Mapping[str, object]], threshold_rows: Sequence[Mapping[str, float]]) -> List[Dict[str, object]]:
    threshold_by_p = {round(row["physical_error_rate"], 12): row for row in threshold_rows}
    rows: List[Dict[str, object]] = []
    for row in random_rows:
        p_error = float(row["physical_error_rate"])
        shots = int(row["trials"])
        logical_error = float(row["logical_failure_rate"])
        success = int(round((1.0 - logical_error) * shots))
        threshold_row = threshold_by_p.get(round(p_error, 12), {})
        no_qec_logical_error = float(threshold_row.get("bare_physical_infidelity", 0.0))
        rows.append(
            {
                "physical_error": p_error,
                "logical_error": logical_error,
                "fidelity": success / shots,
                "successful_output": success,
                "total_shots": shots,
                "no_qec_logical_error": no_qec_logical_error,
                "mean_recovered_fidelity": float(row["mean_recovered_fidelity"]),
                "code": "Perfect [[5,1,3]]",
            }
        )
    return rows


def run_member3_benchmark(args: argparse.Namespace) -> None:
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    basis = derive_code_basis()
    correction_table = build_correction_table()
    state = logical_state(theta=args.theta, phi=args.phi)
    target = encode_state(state, basis)

    sweep_p = default_physical_error_rates()
    LOGGER.info("Running Member 3 shot sweep from p=0 to p=0.05 with %d shots", args.shots)
    random_rows = run_random_noise_trials(
        target=target,
        correction_table=correction_table,
        p_values=sweep_p,
        trials=args.shots,
        seed=args.seed,
    )

    LOGGER.info("Running exact threshold scan for intersection detection")
    extended_p = np.concatenate([np.array(sweep_p), np.linspace(0.06, 0.35, args.threshold_points)])
    threshold_rows = run_threshold_scan(state, target, basis, correction_table, extended_p)
    threshold = estimate_intersection(threshold_rows)
    member3_rows = build_member3_rows(random_rows, threshold_rows)

    write_csv(data_dir / "member3_perfect.csv", member3_rows)
    write_csv(project_dir / "results.csv", member3_rows)
    write_csv(data_dir / "results.csv", member3_rows)
    write_csv(data_dir / "member3_threshold_extended.csv", threshold_rows)
    write_json(
        data_dir / "member3_summary.json",
        {
            "shots": args.shots,
            "seed": args.seed,
            "p_sweep_min": min(sweep_p),
            "p_sweep_max": max(sweep_p),
            "threshold_intersection_estimate": threshold,
            "note": "The 0 to 0.05 sweep is shot-based. The threshold intersection uses an extended exact scan.",
        },
    )

    LOGGER.info("Member 3 CSV written: %s", data_dir / "member3_perfect.csv")
    if threshold is None:
        LOGGER.info("No threshold crossing found in extended scan")
    else:
        LOGGER.info("Threshold-style intersection p ~= %.5f", threshold)

    if not args.skip_plots:
        from plot_results import create_plots

        create_plots(project_dir=project_dir, verbose=args.verbose)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Member 3 Perfect [[5,1,3]] benchmark.")
    parser.add_argument("--shots", type=int, default=1000, help="Shots per p value in the 0 to 0.05 sweep.")
    parser.add_argument("--theta", type=float, default=1.113, help="Input logical-state polar angle.")
    parser.add_argument("--phi", type=float, default=0.731, help="Input logical-state azimuthal phase.")
    parser.add_argument("--threshold-points", type=int, default=30, help="Extra p points for the extended threshold scan.")
    parser.add_argument("--seed", type=int, default=513, help="Random seed.")
    parser.add_argument("--skip-plots", action="store_true", help="Only write CSV files.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


if __name__ == "__main__":
    parsed_args = parse_args()
    configure_logging(parsed_args.verbose)
    run_member3_benchmark(parsed_args)

