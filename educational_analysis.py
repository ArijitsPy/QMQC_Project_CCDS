"""
Extra educational figures and theory comparisons for the Member-3 report.

Run:
    qiskit_env/bin/python CCDS_QMQC_Project/Group_Project/educational_analysis.py
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qec_5qubit_mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from qec_5qubit_project import write_csv


LOGGER = logging.getLogger("educational_analysis")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def no_qec_infidelity(p_error: float) -> float:
    """Expected state infidelity of a bare qubit under uniform Pauli noise."""

    return 2 * p_error / 3


def perfect_uncorrectable_probability(p_error: float, n_qubits: int = 5) -> float:
    """Probability that two or more data qubits are hit in one correction round."""

    return 1 - (1 - p_error) ** n_qubits - n_qubits * p_error * (1 - p_error) ** (n_qubits - 1)


def build_theory_rows(project_dir: Path) -> List[Dict[str, float]]:
    member3_rows = read_csv_rows(project_dir / "data" / "member3_perfect.csv")
    threshold_rows = read_csv_rows(project_dir / "data" / "member3_threshold_extended.csv")
    exact_by_p = {round(float(row["physical_error_rate"]), 12): float(row["qec_logical_infidelity"]) for row in threshold_rows}

    rows: List[Dict[str, float]] = []
    for row in member3_rows:
        p_error = float(row["physical_error"])
        rows.append(
            {
                "physical_error": p_error,
                "no_qec_theory": no_qec_infidelity(p_error),
                "perfect_uncorrectable_theory": perfect_uncorrectable_probability(p_error),
                "perfect_exact_qec_infidelity": exact_by_p.get(round(p_error, 12), float("nan")),
                "perfect_shot_logical_error": float(row["logical_error"]),
            }
        )
    return rows


def plot_theory_expected_error_rates(rows: Sequence[Mapping[str, float]], output_path: Path) -> None:
    p_values = [row["physical_error"] for row in rows]
    no_qec = [row["no_qec_theory"] for row in rows]
    uncorrectable = [row["perfect_uncorrectable_theory"] for row in rows]
    exact = [row["perfect_exact_qec_infidelity"] for row in rows]
    shot = [row["perfect_shot_logical_error"] for row in rows]

    fig, ax = plt.subplots(figsize=(9.2, 5.7))
    ax.plot(p_values, no_qec, marker="s", linewidth=2.3, color="#444444", label="No QEC theory: 2p/3")
    ax.plot(p_values, uncorrectable, marker="^", linewidth=2.3, color="#aa3377", label="Perfect code theory: P(2+ errors)")
    ax.plot(p_values, exact, marker="o", linewidth=2.3, color="#228833", label="Exact recovered infidelity")
    ax.scatter(p_values, shot, s=48, color="#cc6677", label="1000-shot logical error")
    ax.set_xlabel("Physical Error Rate p")
    ax.set_ylabel("Expected Logical Error / Infidelity")
    ax.set_title("Theory vs simulation for Perfect [[5,1,3]]")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_useful_region(rows: Sequence[Mapping[str, float]], output_path: Path) -> None:
    p_values = np.array([row["physical_error"] for row in rows], dtype=float)
    no_qec = np.array([row["no_qec_theory"] for row in rows], dtype=float)
    exact = np.array([row["perfect_exact_qec_infidelity"] for row in rows], dtype=float)
    gain = np.divide(no_qec, exact, out=np.full_like(no_qec, np.nan), where=exact > 0)

    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.plot(p_values, gain, marker="o", linewidth=2.4, color="#117733")
    ax.axhline(1.0, linestyle="--", color="#444444", label="Break-even")
    ax.fill_between(p_values, 1.0, gain, where=gain >= 1.0, alpha=0.18, color="#228833", label="QEC helps")
    ax.set_xlabel("Physical Error Rate p")
    ax.set_ylabel("No-QEC error / QEC error")
    ax.set_title("When the Perfect [[5,1,3]] code is useful")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_process_flow(output_path: Path) -> None:
    labels = [
        "Logical\nqubit",
        "Encode into\n5 qubits",
        "Noise hits\nhardware",
        "Measure\nsyndrome",
        "Apply\ncorrection",
        "Recovered\nlogical qubit",
    ]
    colors = ["#88ccee", "#44aa99", "#cc6677", "#ddcc77", "#117733", "#88ccee"]
    fig, ax = plt.subplots(figsize=(13.2, 3.3))
    ax.set_xlim(0, len(labels))
    ax.set_ylim(0, 1)
    ax.axis("off")
    for idx, (label, color) in enumerate(zip(labels, colors)):
        x = idx + 0.5
        ax.text(
            x,
            0.55,
            label,
            ha="center",
            va="center",
            fontsize=13,
            weight="bold",
            bbox=dict(boxstyle="round,pad=0.42,rounding_size=0.08", facecolor=color, edgecolor="#222222", linewidth=1.4),
        )
        if idx < len(labels) - 1:
            ax.annotate("", xy=(idx + 1.05, 0.55), xytext=(idx + 0.82, 0.55), arrowprops=dict(arrowstyle="->", lw=2.4))
    ax.text(2.5, 0.14, "Repeat for p = 0, 0.001, 0.005, ..., 0.05", ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_perfect_code_structure(output_path: Path) -> None:
    angles = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, 6)[:-1]
    points = np.column_stack([np.cos(angles), np.sin(angles)])
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.plot(np.append(points[:, 0], points[0, 0]), np.append(points[:, 1], points[0, 1]), color="#444444", linewidth=2)
    for idx, (x, y) in enumerate(points):
        ax.scatter([x], [y], s=1600, color="#88ccee", edgecolor="#222222", linewidth=2, zorder=3)
        ax.text(x, y, f"q{idx}", ha="center", va="center", fontsize=18, weight="bold", zorder=4)
    ax.text(0, 0.12, "One logical qubit\nspread over five\nphysical qubits", ha="center", va="center", fontsize=15, weight="bold")
    stabilizer_text = "Stabilizers\nS1 = XZZXI\nS2 = IXZZX\nS3 = XIXZZ\nS4 = ZXIXZ"
    ax.text(0, -1.55, stabilizer_text, ha="center", va="top", fontsize=12, bbox=dict(facecolor="#f7f7f7", edgecolor="#444444"))
    ax.set_title("Perfect [[5,1,3]] code structure", fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def surface_logical_error_model(p_error: float, distance: int, threshold: float = 0.01) -> float:
    # Simple educational scaling law, not a hardware-calibrated decoder model.
    return 0.10 * (p_error / threshold) ** ((distance + 1) / 2)


def build_scaling_rows() -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for distance in [3, 5, 7, 9, 11, 13]:
        rows.append(
            {
                "architecture": "surface_code_rough_model",
                "distance": distance,
                "correctable_errors_t": (distance - 1) // 2,
                "approx_physical_qubits": 2 * distance * distance,
                "logical_error_at_p_0.001": surface_logical_error_model(0.001, distance),
                "logical_error_at_p_0.003": surface_logical_error_model(0.003, distance),
                "logical_error_at_p_0.006": surface_logical_error_model(0.006, distance),
            }
        )
    return rows


def plot_scaling_analysis(rows: Sequence[Mapping[str, float]], output_path: Path) -> None:
    distances = np.array([row["distance"] for row in rows], dtype=int)
    physical = np.array([row["approx_physical_qubits"] for row in rows], dtype=float)
    t_values = np.array([row["correctable_errors_t"] for row in rows], dtype=float)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    axes[0].plot(distances, t_values, marker="o", linewidth=2.4, color="#4477aa")
    axes[0].set_title("Correctable errors")
    axes[0].set_xlabel("Code distance d")
    axes[0].set_ylabel("t = (d-1)/2")

    axes[1].plot(distances, physical, marker="s", linewidth=2.4, color="#cc6677")
    axes[1].set_title("Approximate surface-code overhead")
    axes[1].set_xlabel("Code distance d")
    axes[1].set_ylabel("Physical qubits ~ 2d^2")

    for p_error, color in [(0.001, "#117733"), (0.003, "#ddcc77"), (0.006, "#aa3377")]:
        values = [row[f"logical_error_at_p_{p_error}"] for row in rows]
        axes[2].plot(distances, values, marker="o", linewidth=2.2, label=f"p={p_error}", color=color)
    axes[2].set_yscale("log")
    axes[2].set_title("Why larger distance matters")
    axes[2].set_xlabel("Code distance d")
    axes[2].set_ylabel("Toy logical error model")
    axes[2].legend()

    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("Scaling beyond one-error correction", fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_project_roadmap(output_path: Path) -> None:
    stages = [
        ("1", "Build\ncode"),
        ("2", "Verify\nsingle errors"),
        ("3", "Sweep\nnoise p"),
        ("4", "Compare\nno QEC"),
        ("5", "Find\nthreshold"),
        ("6", "Scale to\nlarger codes"),
    ]
    fig, ax = plt.subplots(figsize=(12.8, 4.3))
    ax.axis("off")
    ax.set_xlim(-0.3, len(stages) - 0.7)
    ax.set_ylim(-0.6, 0.8)
    for idx, (num, text) in enumerate(stages):
        ax.scatter(idx, 0, s=1800, color="#88ccee", edgecolor="#222222", linewidth=2, zorder=3)
        ax.text(idx, 0.08, num, ha="center", va="center", fontsize=16, weight="bold", zorder=4)
        ax.text(idx, -0.33, text, ha="center", va="center", fontsize=12, weight="bold")
        if idx < len(stages) - 1:
            ax.annotate("", xy=(idx + 0.72, 0), xytext=(idx + 0.28, 0), arrowprops=dict(arrowstyle="->", lw=2.5))
    ax.set_title("Whole project workflow", fontsize=17, weight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def run(project_dir: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    figures_dir = project_dir / "figures"
    data_dir = project_dir / "data"
    figures_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    theory_rows = build_theory_rows(project_dir)
    write_csv(data_dir / "theory_expected_error_rates.csv", theory_rows)
    plot_theory_expected_error_rates(theory_rows, figures_dir / "theory_expected_error_rates.png")
    plot_useful_region(theory_rows, figures_dir / "perfect_code_useful_region.png")
    plot_process_flow(figures_dir / "qec_process_flow.png")
    plot_perfect_code_structure(figures_dir / "perfect_code_structure.png")
    plot_project_roadmap(figures_dir / "project_workflow_roadmap.png")

    scaling_rows = build_scaling_rows()
    write_csv(data_dir / "scaling_surface_code_model.csv", scaling_rows)
    plot_scaling_analysis(scaling_rows, figures_dir / "scaling_surface_code_model.png")
    LOGGER.info("Educational analysis figures written to %s", figures_dir)


if __name__ == "__main__":
    run(Path(__file__).resolve().parent)
