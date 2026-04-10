"""
Plot Member 3 threshold results and four-code comparison curves.

If teammate CSVs are present, they are used automatically:
  - data/member1_shor.csv
  - data/member2_steane.csv
  - data/member4_bacon_shor.csv

Until those files exist, this script draws clearly labelled distance-3 proxy
curves so the report has the requested four-curve figure layout.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qec_5qubit_mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from qec_5qubit_project import estimate_intersection, write_csv


LOGGER = logging.getLogger("member3_plot_results")


TEAM_CURVES = {
    "Shor [[9,1,3]]": ("member1_shor.csv", 9, 1.45, "#cc6677"),
    "Steane [[7,1,3]]": ("member2_steane.csv", 7, 1.25, "#4477aa"),
    "Bacon-Shor [[9,1,3]]": ("member4_bacon_shor.csv", 9, 1.15, "#ddcc77"),
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def numeric_column(row: Mapping[str, str], names: Sequence[str]) -> float:
    for name in names:
        if name in row and row[name] != "":
            return float(row[name])
    raise KeyError(f"None of these columns were found: {names}")


def load_curve(path: Path) -> List[Dict[str, float]]:
    rows = []
    for row in read_csv_rows(path):
        rows.append(
            {
                "physical_error": numeric_column(row, ["physical_error", "physical_error_rate", "p"]),
                "logical_error": numeric_column(row, ["logical_error", "logical_failure_rate", "qec_logical_infidelity"]),
            }
        )
    return rows


def proxy_distance3_curve(p_values: Sequence[float], n_qubits: int, overhead: float) -> List[Dict[str, float]]:
    rows = []
    for p_error in p_values:
        p_eff = min(0.95, p_error * overhead)
        logical_error = 1 - (1 - p_eff) ** n_qubits - n_qubits * p_eff * (1 - p_eff) ** (n_qubits - 1)
        rows.append({"physical_error": float(p_error), "logical_error": float(max(0.0, logical_error))})
    return rows


def load_four_code_curves(project_dir: Path, member3_rows: Sequence[Mapping[str, float]]) -> List[Dict[str, object]]:
    p_values = [float(row["physical_error"]) for row in member3_rows]
    data_dir = project_dir / "data"
    curves: List[Dict[str, object]] = [
        {
            "code": "Perfect [[5,1,3]]",
            "source": "member3_simulation",
            "rows": [{"physical_error": float(row["physical_error"]), "logical_error": float(row["logical_error"])} for row in member3_rows],
            "color": "#228833",
        }
    ]

    for code, (filename, n_qubits, overhead, color) in TEAM_CURVES.items():
        path = data_dir / filename
        if path.exists():
            rows = load_curve(path)
            source = "team_csv"
            label = code
        else:
            rows = proxy_distance3_curve(p_values, n_qubits=n_qubits, overhead=overhead)
            source = "proxy_until_team_data_arrives"
            label = f"{code} (proxy)"
        curves.append({"code": label, "source": source, "rows": rows, "color": color})
    return curves


def plot_member3_sweep(member3_rows: Sequence[Mapping[str, float]], output_path: Path) -> None:
    p_values = [row["physical_error"] for row in member3_rows]
    logical = [row["logical_error"] for row in member3_rows]
    no_qec = [row["no_qec_logical_error"] for row in member3_rows]

    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    ax.plot(p_values, logical, marker="o", linewidth=2.4, color="#228833", label="Perfect [[5,1,3]] QEC")
    ax.plot(p_values, no_qec, marker="s", linewidth=2.0, color="#444444", linestyle="--", label="No QEC")
    ax.set_xlabel("Physical Error Rate")
    ax.set_ylabel("Logical Error Rate")
    ax.set_title("Member 3 sweep: physical vs logical error")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_four_code_comparison(curves: Sequence[Mapping[str, object]], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    for curve in curves:
        rows = curve["rows"]
        p_values = [row["physical_error"] for row in rows]
        logical = [row["logical_error"] for row in rows]
        ax.plot(p_values, logical, marker="o", linewidth=2.1, label=str(curve["code"]), color=str(curve["color"]))
    ax.set_xlabel("Physical Error Rate")
    ax.set_ylabel("Logical Error Rate")
    ax.set_title("QEC code comparison for the shared arena")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_threshold(project_dir: Path, output_path: Path) -> float | None:
    extended_path = project_dir / "data" / "member3_threshold_extended.csv"
    if not extended_path.exists():
        raise FileNotFoundError(f"Run runner.py first; missing {extended_path}")

    rows = []
    for row in read_csv_rows(extended_path):
        rows.append(
            {
                "physical_error_rate": float(row["physical_error_rate"]),
                "qec_logical_infidelity": float(row["qec_logical_infidelity"]),
                "bare_physical_infidelity": float(row["bare_physical_infidelity"]),
            }
        )
    threshold = estimate_intersection(rows)

    p_values = [row["physical_error_rate"] for row in rows]
    qec = [row["qec_logical_infidelity"] for row in rows]
    no_qec = [row["bare_physical_infidelity"] for row in rows]

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    ax.plot(p_values, qec, marker="o", linewidth=2.3, color="#228833", label="Perfect [[5,1,3]] QEC")
    ax.plot(p_values, no_qec, marker="s", linewidth=2.0, linestyle="--", color="#444444", label="No QEC")
    if threshold is not None:
        ax.axvline(threshold, linestyle=":", linewidth=2.2, color="#aa3377", label=f"Intersection p ~= {threshold:.4f}")
    ax.axvspan(0.0, 0.05, color="#88ccee", alpha=0.14, label="Required 0 to 0.05 sweep")
    ax.set_xlabel("Physical Error Rate")
    ax.set_ylabel("Logical Error Rate")
    ax.set_title("Threshold theorem demonstration")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return threshold


def plot_supporting_graphs(project_dir: Path, member3_rows: Sequence[Mapping[str, float]]) -> None:
    data_dir = project_dir / "data"
    single_error_path = data_dir / "single_error_recovery.csv"
    lookup_path = data_dir / "syndrome_lookup.csv"
    figures_dir = project_dir / "figures"
    figures_dir.mkdir(exist_ok=True)

    if single_error_path.exists():
        rows = read_csv_rows(single_error_path)
        labels = [f"{row['error']}{row['qubit']}" for row in rows]
        after = [float(row["fidelity_after"]) for row in rows]
        fig, ax = plt.subplots(figsize=(10.5, 4.8))
        ax.bar(labels, after, color="#228833")
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("Injected single-qubit Pauli error")
        ax.set_ylabel("Recovered fidelity")
        ax.set_title("Perfect code corrects every single-qubit Pauli error")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(figures_dir / "member3_all_single_error_fidelities.png", dpi=180)
        plt.close(fig)

    if lookup_path.exists():
        rows = read_csv_rows(lookup_path)
        syndrome_values = [int(row["syndrome"], 2) for row in rows]
        labels = [f"{row['error']}{row['qubit']}" for row in rows]
        fig, ax = plt.subplots(figsize=(10.5, 4.8))
        ax.bar(labels, syndrome_values, color="#4477aa")
        ax.set_xlabel("Injected single-qubit Pauli error")
        ax.set_ylabel("Syndrome integer")
        ax.set_title("Unique syndrome for every correctable single-qubit error")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(figures_dir / "member3_unique_syndromes.png", dpi=180)
        plt.close(fig)

    p_values = [row["physical_error"] for row in member3_rows]
    successes = [row["fidelity"] for row in member3_rows]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.plot(p_values, successes, marker="o", linewidth=2.4, color="#228833")
    ax.set_xlabel("Physical Error Rate")
    ax.set_ylabel("Shot success fraction")
    ax.set_title("Shot success fraction under the required p sweep")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "member3_success_fraction.png", dpi=180)
    plt.close(fig)


def create_plots(project_dir: Path | None = None, verbose: bool = False) -> None:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    data_dir = project_dir / "data"
    figures_dir = project_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    member3_path = data_dir / "member3_perfect.csv"
    if not member3_path.exists():
        raise FileNotFoundError(f"Run runner.py first; missing {member3_path}")

    member3_rows = [
        {
            "physical_error": float(row["physical_error"]),
            "logical_error": float(row["logical_error"]),
            "no_qec_logical_error": float(row["no_qec_logical_error"]),
            "fidelity": float(row["fidelity"]),
        }
        for row in read_csv_rows(member3_path)
    ]
    curves = load_four_code_curves(project_dir, member3_rows)
    comparison_rows = []
    for curve in curves:
        for row in curve["rows"]:
            comparison_rows.append(
                {
                    "code": curve["code"],
                    "source": curve["source"],
                    "physical_error": row["physical_error"],
                    "logical_error": row["logical_error"],
                }
            )
    write_csv(data_dir / "comparison_curves.csv", comparison_rows)

    plot_member3_sweep(member3_rows, figures_dir / "member3_physical_vs_logical.png")
    plot_four_code_comparison(curves, figures_dir / "four_code_comparison.png")
    plot_four_code_comparison(curves, project_dir / "four_code_comparison.png")
    threshold = plot_threshold(project_dir, project_dir / "threshold_plot.png")
    plot_threshold(project_dir, figures_dir / "threshold_plot.png")
    plot_supporting_graphs(project_dir, member3_rows)

    if threshold is None:
        LOGGER.info("No threshold crossing found in extended data")
    else:
        LOGGER.info("Threshold-style intersection p ~= %.5f", threshold)
    LOGGER.info("Wrote required plot: %s", project_dir / "threshold_plot.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot Member 3 results.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_plots(verbose=args.verbose)

