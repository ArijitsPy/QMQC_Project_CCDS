"""
Perfect [[5, 1, 3]] QEC project runner.

This file builds a reproducible simulation and visualization suite for the
Member 3 task in idea.md.  It deliberately keeps the physics core small and
auditable: the logical codewords are derived from the stabilizer generators,
all 15 single-qubit Pauli errors are checked exactly, and noisy runs use the
same syndrome recovery map.

Run from the repository root with:

    qiskit_env/bin/python CCDS_QMQC_Project/Group_Project/qec_5qubit_project.py
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qec_5qubit_mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


LOGGER = logging.getLogger("perfect_513_project")

N_DATA_QUBITS = 5
STABILIZERS = ("XZZXI", "IXZZX", "XIXZZ", "ZXIXZ")
LOGICAL_X = "XXXXX"
LOGICAL_Z = "ZZZZZ"
PAULI_ORDER = ("X", "Y", "Z")

PAULI_MATS = {
    "I": np.array([[1, 0], [0, 1]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


@dataclass(frozen=True)
class CodeBasis:
    """Logical basis vectors and matrices derived from the stabilizers."""

    zero_l: np.ndarray
    one_l: np.ndarray
    stabilizer_mats: Tuple[np.ndarray, ...]
    logical_x: np.ndarray
    logical_z: np.ndarray
    projector: np.ndarray


@dataclass(frozen=True)
class LogicalStateSpec:
    """A single-qubit state |psi> = alpha|0> + beta|1>."""

    alpha: complex
    beta: complex
    theta: float
    phi: float


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("qiskit").setLevel(logging.WARNING)


def kron_all(matrices: Sequence[np.ndarray]) -> np.ndarray:
    out = matrices[0]
    for matrix in matrices[1:]:
        out = np.kron(out, matrix)
    return out


def pauli_matrix(label: str) -> np.ndarray:
    """Return the matrix for a Pauli label whose character i acts on qubit i."""

    if len(label) != N_DATA_QUBITS:
        raise ValueError(f"Expected {N_DATA_QUBITS} Pauli characters, got {label!r}")
    # Qiskit statevector indices use qubit 0 as the least significant bit, so
    # the Kronecker product is built from high qubit to low qubit.
    return kron_all([PAULI_MATS[label[q]] for q in reversed(range(N_DATA_QUBITS))])


def anticommutes(label_a: str, label_b: str) -> bool:
    clashes = 0
    for a, b in zip(label_a, label_b):
        if a != "I" and b != "I" and a != b:
            clashes += 1
    return bool(clashes % 2)


def syndrome_tuple(error_label: str) -> Tuple[int, int, int, int]:
    return tuple(1 if anticommutes(error_label, stabilizer) else 0 for stabilizer in STABILIZERS)


def syndrome_label(syndrome: Sequence[int]) -> str:
    return "".join(str(bit) for bit in syndrome)


def single_qubit_error_label(qubit: int, error: str) -> str:
    chars = ["I"] * N_DATA_QUBITS
    chars[qubit] = error
    return "".join(chars)


def derive_code_basis() -> CodeBasis:
    """Derive |0_L> and |1_L> from S_i=+1 and logical Z eigenvalue."""

    LOGGER.info("Deriving logical basis from stabilizers: %s", ", ".join(STABILIZERS))
    dim = 2**N_DATA_QUBITS
    identity = np.eye(dim, dtype=complex)
    stabilizer_mats = tuple(pauli_matrix(stabilizer) for stabilizer in STABILIZERS)
    logical_x = pauli_matrix(LOGICAL_X)
    logical_z = pauli_matrix(LOGICAL_Z)

    projector = identity.copy()
    for stabilizer in stabilizer_mats:
        projector = projector @ ((identity + stabilizer) / 2)

    zero_projector = projector @ ((identity + logical_z) / 2)
    zero_projector = (zero_projector + zero_projector.conj().T) / 2
    evals, evecs = np.linalg.eigh(zero_projector)
    zero_l = evecs[:, int(np.argmax(evals))]
    zero_l = zero_l / np.linalg.norm(zero_l)

    first_nonzero = int(np.argmax(np.abs(zero_l) > 1e-10))
    phase = np.angle(zero_l[first_nonzero])
    zero_l = zero_l * np.exp(-1j * phase)

    one_l = logical_x @ zero_l
    one_l = one_l / np.linalg.norm(one_l)

    # Make the logical X action exactly phase-aligned with |1_L>.
    overlap = np.vdot(one_l, logical_x @ zero_l)
    one_l = one_l * np.exp(-1j * np.angle(overlap))

    checks = []
    for name, vector in (("0_L", zero_l), ("1_L", one_l)):
        for idx, stabilizer in enumerate(stabilizer_mats, start=1):
            checks.append((name, f"S{idx}", float(np.real(np.vdot(vector, stabilizer @ vector)))))
    LOGGER.debug("Stabilizer expectation checks: %s", checks)

    if not np.isclose(np.vdot(zero_l, logical_z @ zero_l), 1.0, atol=1e-8):
        raise RuntimeError("Derived |0_L> is not a +1 logical-Z eigenstate")
    if not np.isclose(np.vdot(one_l, logical_z @ one_l), -1.0, atol=1e-8):
        raise RuntimeError("Derived |1_L> is not a -1 logical-Z eigenstate")
    if not np.isclose(abs(np.vdot(zero_l, one_l)), 0.0, atol=1e-8):
        raise RuntimeError("Derived logical basis is not orthogonal")

    LOGGER.info("Derived logical codewords successfully")
    return CodeBasis(
        zero_l=zero_l,
        one_l=one_l,
        stabilizer_mats=stabilizer_mats,
        logical_x=logical_x,
        logical_z=logical_z,
        projector=projector,
    )


def logical_state(theta: float, phi: float) -> LogicalStateSpec:
    alpha = math.cos(theta / 2)
    beta = np.exp(1j * phi) * math.sin(theta / 2)
    return LogicalStateSpec(alpha=complex(alpha), beta=complex(beta), theta=theta, phi=phi)


def encode_state(state: LogicalStateSpec, basis: CodeBasis) -> np.ndarray:
    encoded = state.alpha * basis.zero_l + state.beta * basis.one_l
    return encoded / np.linalg.norm(encoded)


def build_correction_table() -> Dict[Tuple[int, int, int, int], str]:
    table: Dict[Tuple[int, int, int, int], str] = {(0, 0, 0, 0): "IIIII"}
    for qubit in range(N_DATA_QUBITS):
        for error in PAULI_ORDER:
            label = single_qubit_error_label(qubit, error)
            syndrome = syndrome_tuple(label)
            if syndrome in table:
                raise RuntimeError(
                    f"Syndrome collision: {syndrome_label(syndrome)} maps to "
                    f"{table[syndrome]} and {label}"
                )
            table[syndrome] = label
    if len(table) != 16:
        raise RuntimeError(f"Expected 16 syndrome entries, found {len(table)}")
    LOGGER.info("Built perfect-code syndrome table with %d entries", len(table))
    return table


def apply_pauli(state: np.ndarray, label: str) -> np.ndarray:
    return pauli_matrix(label) @ state


def state_fidelity(state_a: np.ndarray, state_b: np.ndarray) -> float:
    return float(abs(np.vdot(state_a, state_b)) ** 2)


def density_fidelity(target: np.ndarray, rho: np.ndarray) -> float:
    return float(np.real(np.vdot(target, rho @ target)))


def projectors_by_syndrome(basis: CodeBasis) -> Dict[Tuple[int, int, int, int], np.ndarray]:
    identity = np.eye(2**N_DATA_QUBITS, dtype=complex)
    projectors: Dict[Tuple[int, int, int, int], np.ndarray] = {}
    for value in range(16):
        bits = tuple((value >> bit) & 1 for bit in range(4))
        projector = identity.copy()
        for bit, stabilizer in zip(bits, basis.stabilizer_mats):
            sign = -1 if bit else 1
            projector = projector @ ((identity + sign * stabilizer) / 2)
        projectors[bits] = projector
    return projectors


def recover_density_matrix(
    rho: np.ndarray,
    correction_table: Mapping[Tuple[int, int, int, int], str],
    syndrome_projectors: Mapping[Tuple[int, int, int, int], np.ndarray],
) -> np.ndarray:
    recovered = np.zeros_like(rho, dtype=complex)
    for syndrome, projector in syndrome_projectors.items():
        correction = pauli_matrix(correction_table[syndrome])
        recovered += correction @ projector @ rho @ projector @ correction.conj().T
    return (recovered + recovered.conj().T) / 2


def apply_independent_depolarizing_channel(rho: np.ndarray, p_by_qubit: Sequence[float]) -> np.ndarray:
    out = rho.copy()
    for qubit, p_error in enumerate(p_by_qubit):
        if not 0 <= p_error <= 1:
            raise ValueError(f"Depolarizing probability must be in [0, 1], got {p_error}")
        next_rho = (1 - p_error) * out
        for error in PAULI_ORDER:
            label = single_qubit_error_label(qubit, error)
            matrix = pauli_matrix(label)
            next_rho += (p_error / 3) * matrix @ out @ matrix.conj().T
        out = next_rho
    return (out + out.conj().T) / 2


def one_qubit_depolarized_fidelity(state: LogicalStateSpec, p_error: float) -> float:
    psi = np.array([state.alpha, state.beta], dtype=complex)
    rho = np.outer(psi, psi.conj())
    noisy = (1 - p_error) * rho
    for matrix in (PAULI_MATS["X"], PAULI_MATS["Y"], PAULI_MATS["Z"]):
        noisy += (p_error / 3) * matrix @ rho @ matrix.conj().T
    return float(np.real(np.vdot(psi, noisy @ psi)))


def analyze_single_errors(
    target: np.ndarray,
    correction_table: Mapping[Tuple[int, int, int, int], str],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for qubit in range(N_DATA_QUBITS):
        for error in PAULI_ORDER:
            error_label = single_qubit_error_label(qubit, error)
            corrupted = apply_pauli(target, error_label)
            syndrome = syndrome_tuple(error_label)
            corrected = apply_pauli(corrupted, correction_table[syndrome])
            rows.append(
                {
                    "qubit": qubit,
                    "error": error,
                    "pauli_label": error_label,
                    "syndrome": syndrome_label(syndrome),
                    "correction": correction_table[syndrome],
                    "fidelity_before": state_fidelity(target, corrupted),
                    "fidelity_after": state_fidelity(target, corrected),
                }
            )
    LOGGER.info("Finished exact single-error sweep over %d errors", len(rows))
    return rows


def run_random_noise_trials(
    target: np.ndarray,
    correction_table: Mapping[Tuple[int, int, int, int], str],
    p_values: Sequence[float],
    trials: int,
    seed: int,
) -> List[Dict[str, object]]:
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, object]] = []
    for p_error in p_values:
        failures = 0
        fidelity_sum = 0.0
        weight_counts = {idx: 0 for idx in range(N_DATA_QUBITS + 1)}
        LOGGER.info("Random Pauli trials at p=%.4f (%d trials)", p_error, trials)
        for trial in range(trials):
            chars = ["I"] * N_DATA_QUBITS
            for qubit in range(N_DATA_QUBITS):
                if rng.random() < p_error:
                    chars[qubit] = str(rng.choice(PAULI_ORDER))
            error_label = "".join(chars)
            weight = sum(char != "I" for char in chars)
            weight_counts[weight] += 1
            syndrome = syndrome_tuple(error_label)
            corrected = apply_pauli(apply_pauli(target, error_label), correction_table[syndrome])
            fidelity = state_fidelity(target, corrected)
            fidelity_sum += fidelity
            if 1 - fidelity > 1e-8:
                failures += 1
            if (trial + 1) % max(1, trials // 4) == 0:
                LOGGER.debug("  p=%.4f progress: %d/%d", p_error, trial + 1, trials)
        rows.append(
            {
                "physical_error_rate": p_error,
                "trials": trials,
                "logical_failure_rate": failures / trials,
                "mean_recovered_fidelity": fidelity_sum / trials,
                **{f"weight_{k}_count": v for k, v in weight_counts.items()},
            }
        )
    return rows


def run_threshold_scan(
    state: LogicalStateSpec,
    target: np.ndarray,
    basis: CodeBasis,
    correction_table: Mapping[Tuple[int, int, int, int], str],
    p_values: Sequence[float],
) -> List[Dict[str, float]]:
    projectors = projectors_by_syndrome(basis)
    rho0 = np.outer(target, target.conj())
    rows: List[Dict[str, float]] = []
    for p_error in p_values:
        noisy = apply_independent_depolarizing_channel(rho0, [p_error] * N_DATA_QUBITS)
        recovered = recover_density_matrix(noisy, correction_table, projectors)
        qec_fidelity = density_fidelity(target, recovered)
        bare_fidelity = one_qubit_depolarized_fidelity(state, p_error)
        rows.append(
            {
                "physical_error_rate": float(p_error),
                "qec_logical_infidelity": max(0.0, 1.0 - qec_fidelity),
                "bare_physical_infidelity": max(0.0, 1.0 - bare_fidelity),
                "qec_recovered_fidelity": qec_fidelity,
                "bare_recovered_fidelity": bare_fidelity,
            }
        )
    LOGGER.info("Finished exact threshold scan with %d physical error rates", len(rows))
    return rows


def estimate_intersection(rows: Sequence[Mapping[str, float]]) -> float | None:
    previous = None
    for row in rows:
        p_error = row["physical_error_rate"]
        if p_error <= 0:
            continue
        diff = row["qec_logical_infidelity"] - row["bare_physical_infidelity"]
        if previous is not None:
            old_p, old_diff = previous
            if old_diff <= 0 < diff:
                slope = (diff - old_diff) / (p_error - old_p)
                return float(old_p - old_diff / slope)
        previous = (p_error, diff)
    return None


def run_backend_like_scan(
    target: np.ndarray,
    basis: CodeBasis,
    correction_table: Mapping[Tuple[int, int, int, int], str],
    scale_values: Sequence[float],
) -> List[Dict[str, float]]:
    # A small, nonuniform synthetic profile in the range of contemporary
    # superconducting-qubit single-qubit gate/readout-scale errors.  The
    # hardware job template can replace this with Qiskit Runtime backend data.
    base_qubit_probs = np.array([0.0012, 0.0018, 0.0015, 0.0024, 0.0016])
    projectors = projectors_by_syndrome(basis)
    rho0 = np.outer(target, target.conj())
    rows: List[Dict[str, float]] = []
    for scale in scale_values:
        p_by_qubit = np.clip(base_qubit_probs * scale, 0.0, 0.45)
        noisy = apply_independent_depolarizing_channel(rho0, p_by_qubit)
        recovered = recover_density_matrix(noisy, correction_table, projectors)
        fidelity = density_fidelity(target, recovered)
        row = {
            "scale": float(scale),
            "mean_physical_error_rate": float(np.mean(p_by_qubit)),
            "max_physical_error_rate": float(np.max(p_by_qubit)),
            "qec_recovered_fidelity": fidelity,
            "qec_logical_infidelity": max(0.0, 1.0 - fidelity),
        }
        for qubit, p_error in enumerate(p_by_qubit):
            row[f"p_q{qubit}"] = float(p_error)
        rows.append(row)
    LOGGER.info("Finished backend-like scan over %d scale factors", len(rows))
    return rows


def nonzero_amplitudes(vector: np.ndarray, tolerance: float = 1e-9) -> List[Tuple[str, complex]]:
    rows = []
    for index, amplitude in enumerate(vector):
        if abs(amplitude) > tolerance:
            # q4...q0 is the conventional printed computational-basis order.
            rows.append((format(index, f"0{N_DATA_QUBITS}b"), amplitude))
    return rows


def build_encoded_state_circuit(target: np.ndarray) -> QuantumCircuit:
    qc = QuantumCircuit(N_DATA_QUBITS, name="encoded_state")
    qc.initialize(target, range(N_DATA_QUBITS))
    qc.barrier(label="encoded |psi_L>")
    return qc


def build_syndrome_extraction_circuit() -> QuantumCircuit:
    data = QuantumRegister(N_DATA_QUBITS, "data")
    anc = QuantumRegister(len(STABILIZERS), "syn")
    creg = ClassicalRegister(len(STABILIZERS), "c")
    qc = QuantumCircuit(data, anc, creg, name="syndrome_extraction")

    for stab_idx, stabilizer in enumerate(STABILIZERS):
        qc.barrier(label=f"S{stab_idx + 1}={stabilizer}")
        for qubit, pauli in enumerate(stabilizer):
            if pauli == "X":
                qc.h(data[qubit])
            elif pauli == "Y":
                qc.sdg(data[qubit])
                qc.h(data[qubit])
        for qubit, pauli in enumerate(stabilizer):
            if pauli != "I":
                qc.cx(data[qubit], anc[stab_idx])
        for qubit, pauli in enumerate(stabilizer):
            if pauli == "X":
                qc.h(data[qubit])
            elif pauli == "Y":
                qc.h(data[qubit])
                qc.s(data[qubit])
        qc.measure(anc[stab_idx], creg[stab_idx])
    return qc


def build_full_demo_circuit(target: np.ndarray, error_qubit: int = 2, error: str = "X") -> QuantumCircuit:
    data = QuantumRegister(N_DATA_QUBITS, "data")
    anc = QuantumRegister(len(STABILIZERS), "syn")
    creg = ClassicalRegister(len(STABILIZERS), "c")
    qc = QuantumCircuit(data, anc, creg, name="five_qubit_qec_demo")
    qc.initialize(target, data)
    qc.barrier(label="encode")
    getattr(qc, error.lower())(data[error_qubit])
    qc.barrier(label=f"inject {error}{error_qubit}")

    syndrome = build_syndrome_extraction_circuit()
    qc.compose(syndrome, qubits=list(data) + list(anc), clbits=list(creg), inplace=True)
    return qc


def save_circuit_diagram(qc: QuantumCircuit, output_path: Path, scale: float = 0.7) -> None:
    LOGGER.info("Saving circuit diagram: %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig = qc.draw(output="mpl", scale=scale, fold=-1)
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        LOGGER.warning("Matplotlib circuit drawer failed (%s); writing text fallback", exc)
        output_path.with_suffix(".txt").write_text(str(qc.draw(output="text")), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write for {path}")
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("Wrote %s", path)


def write_json(path: Path, data: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.info("Wrote %s", path)


def plot_syndrome_heatmap(lookup_rows: Sequence[Mapping[str, object]], output_path: Path) -> None:
    heatmap = np.zeros((N_DATA_QUBITS, len(PAULI_ORDER)), dtype=float)
    labels = [["" for _ in PAULI_ORDER] for _ in range(N_DATA_QUBITS)]
    syndrome_to_int = lambda s: int(str(s), 2)
    for row in lookup_rows:
        q = int(row["qubit"])
        e = PAULI_ORDER.index(str(row["error"]))
        heatmap[q, e] = syndrome_to_int(row["syndrome"])
        labels[q][e] = str(row["syndrome"])

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    im = ax.imshow(heatmap, cmap="viridis")
    ax.set_xticks(range(len(PAULI_ORDER)), labels=[f"{e} error" for e in PAULI_ORDER])
    ax.set_yticks(range(N_DATA_QUBITS), labels=[f"q{q}" for q in range(N_DATA_QUBITS)])
    ax.set_xlabel("Injected Pauli")
    ax.set_ylabel("Physical qubit")
    ax.set_title("[[5,1,3]] single-error syndrome lookup")
    for q in range(N_DATA_QUBITS):
        for e in range(len(PAULI_ORDER)):
            ax.text(e, q, labels[q][e], ha="center", va="center", color="white", weight="bold")
    fig.colorbar(im, ax=ax, label="Syndrome as binary integer")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_single_error_recovery(rows: Sequence[Mapping[str, object]], output_path: Path) -> None:
    labels = [f"{row['error']}{row['qubit']}" for row in rows]
    before = [float(row["fidelity_before"]) for row in rows]
    after = [float(row["fidelity_after"]) for row in rows]
    x = np.arange(len(rows))
    width = 0.42
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.bar(x - width / 2, before, width, label="Before recovery", color="#cc6677")
    ax.bar(x + width / 2, after, width, label="After recovery", color="#228833")
    ax.set_xticks(x, labels=labels, rotation=45)
    ax.set_ylim(-0.04, 1.08)
    ax.set_ylabel("Fidelity with original encoded state")
    ax.set_title("Every single-qubit Pauli error is corrected in the noiseless model")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_threshold(rows: Sequence[Mapping[str, float]], threshold: float | None, output_path: Path) -> None:
    p_values = np.array([row["physical_error_rate"] for row in rows])
    qec = np.array([row["qec_logical_infidelity"] for row in rows])
    bare = np.array([row["bare_physical_infidelity"] for row in rows])
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    ax.plot(p_values, bare, marker="s", linewidth=2, label="Bare physical qubit", color="#4477aa")
    ax.plot(p_values, qec, marker="o", linewidth=2, label="Recovered [[5,1,3]] block", color="#228833")
    if threshold is not None:
        ax.axvline(threshold, color="#aa3377", linestyle="--", label=f"Intersection p ~ {threshold:.3f}")
    ax.set_xlabel("Physical depolarizing error probability p")
    ax.set_ylabel("State infidelity")
    ax.set_title("Threshold-style crossing for the five-qubit code")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_random_noise(rows: Sequence[Mapping[str, object]], output_path: Path) -> None:
    p_values = [float(row["physical_error_rate"]) for row in rows]
    failures = [float(row["logical_failure_rate"]) for row in rows]
    fidelity = [float(row["mean_recovered_fidelity"]) for row in rows]
    fig, ax1 = plt.subplots(figsize=(8.5, 5.6))
    ax1.plot(p_values, failures, marker="o", linewidth=2, color="#cc6677", label="Logical failure rate")
    ax1.set_xlabel("Random Pauli error probability p")
    ax1.set_ylabel("Logical failure rate")
    ax1.set_ylim(bottom=0)
    ax1.grid(alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(p_values, fidelity, marker="s", linewidth=2, color="#228833", label="Mean recovered fidelity")
    ax2.set_ylabel("Mean recovered fidelity")
    ax2.set_ylim(0, 1.02)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="center right")
    ax1.set_title("Monte Carlo random Pauli noise after encoding")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_backend_like(rows: Sequence[Mapping[str, float]], output_path: Path) -> None:
    mean_p = [row["mean_physical_error_rate"] for row in rows]
    infidelity = [row["qec_logical_infidelity"] for row in rows]
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    ax.plot(mean_p, infidelity, marker="o", linewidth=2, color="#117733")
    for row in rows:
        ax.annotate(
            f"x{row['scale']:.1g}",
            (row["mean_physical_error_rate"], row["qec_logical_infidelity"]),
            textcoords="offset points",
            xytext=(4, 5),
            fontsize=8,
        )
    ax.set_xlabel("Mean per-qubit backend-like error probability")
    ax.set_ylabel("Recovered logical infidelity")
    ax.set_title("Nonuniform simulated backend-like noise profile")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_scaling(output_path: Path) -> None:
    names = ["5-qubit", "Steane", "Shor", "Bacon-Shor"]
    n_values = np.array([5, 7, 9, 9])
    k_values = np.array([1, 1, 1, 1])
    d_values = np.array([3, 3, 3, 3])
    t_values = (d_values - 1) // 2
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    colors = ["#228833", "#4477aa", "#cc6677", "#ddcc77"]
    axes[0].bar(names, n_values / k_values, color=colors)
    axes[0].set_title("Physical qubits per logical qubit")
    axes[0].set_ylabel("n/k")
    axes[1].bar(names, d_values, color=colors)
    axes[1].set_title("Distance")
    axes[1].set_ylabel("d")
    axes[2].bar(names, t_values, color=colors)
    axes[2].set_title("Correctable arbitrary errors")
    axes[2].set_ylabel("t=(d-1)/2")
    for ax in axes:
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("[[n,k,d]] scaling snapshot for the project codes")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_codeword_amplitudes(basis: CodeBasis, output_path: Path) -> None:
    zero_rows = nonzero_amplitudes(basis.zero_l)
    one_rows = nonzero_amplitudes(basis.one_l)
    labels = [label for label, _ in zero_rows]
    zero_real = [float(np.real(amp)) for _, amp in zero_rows]
    one_real_by_label = {label: float(np.real(amp)) for label, amp in one_rows}
    one_real = [one_real_by_label.get(label, 0.0) for label in labels]
    x = np.arange(len(labels))
    width = 0.42
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.bar(x - width / 2, zero_real, width, label="Re amplitude |0_L>", color="#4477aa")
    ax.bar(x + width / 2, one_real, width, label="Re amplitude |1_L>", color="#aa3377")
    ax.set_xticks(x, labels=labels, rotation=60, ha="right")
    ax.set_ylabel("Real amplitude")
    ax.set_title("Derived five-qubit logical codeword support")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def make_lookup_rows(correction_table: Mapping[Tuple[int, int, int, int], str]) -> List[Dict[str, object]]:
    rows = []
    for qubit in range(N_DATA_QUBITS):
        for error in PAULI_ORDER:
            label = single_qubit_error_label(qubit, error)
            syndrome = syndrome_tuple(label)
            rows.append(
                {
                    "qubit": qubit,
                    "error": error,
                    "pauli_label": label,
                    "syndrome": syndrome_label(syndrome),
                    "correction": correction_table[syndrome],
                }
            )
    return rows


def run_project(args: argparse.Namespace) -> None:
    project_dir = Path(__file__).resolve().parent
    figures_dir = project_dir / "figures"
    data_dir = project_dir / "data"
    figures_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    basis = derive_code_basis()
    correction_table = build_correction_table()
    state = logical_state(theta=args.theta, phi=args.phi)
    target = encode_state(state, basis)
    LOGGER.info(
        "Logical input state: alpha=%.6f, beta=%.6f%+.6fi (theta=%.3f, phi=%.3f)",
        state.alpha.real,
        state.beta.real,
        state.beta.imag,
        state.theta,
        state.phi,
    )

    lookup_rows = make_lookup_rows(correction_table)
    single_error_rows = analyze_single_errors(target, correction_table)
    random_p_values = [0.002, 0.005, 0.01, 0.02, 0.05, 0.08, 0.10, 0.15]
    random_rows = run_random_noise_trials(
        target=target,
        correction_table=correction_table,
        p_values=random_p_values,
        trials=args.random_trials,
        seed=args.seed,
    )
    threshold_p_values = np.concatenate(
        [
            np.array([0.0]),
            np.linspace(0.001, 0.02, 10),
            np.linspace(0.025, 0.35, args.threshold_points),
        ]
    )
    threshold_rows = run_threshold_scan(state, target, basis, correction_table, threshold_p_values)
    threshold = estimate_intersection(threshold_rows)
    backend_rows = run_backend_like_scan(
        target=target,
        basis=basis,
        correction_table=correction_table,
        scale_values=[0.5, 1, 2, 5, 10, 20, 40, 80, 120],
    )

    write_csv(data_dir / "syndrome_lookup.csv", lookup_rows)
    write_csv(data_dir / "single_error_recovery.csv", single_error_rows)
    write_csv(data_dir / "random_noise_monte_carlo.csv", random_rows)
    write_csv(data_dir / "threshold_scan.csv", threshold_rows)
    write_csv(data_dir / "backend_like_noise_scan.csv", backend_rows)

    codeword_rows = [
        {"logical": "0_L", "basis_state": label, "real": float(np.real(amp)), "imag": float(np.imag(amp))}
        for label, amp in nonzero_amplitudes(basis.zero_l)
    ] + [
        {"logical": "1_L", "basis_state": label, "real": float(np.real(amp)), "imag": float(np.imag(amp))}
        for label, amp in nonzero_amplitudes(basis.one_l)
    ]
    write_csv(data_dir / "derived_codeword_amplitudes.csv", codeword_rows)

    write_json(
        data_dir / "summary.json",
        {
            "code": "[[5,1,3]] perfect stabilizer code",
            "stabilizers": STABILIZERS,
            "logical_x": LOGICAL_X,
            "logical_z": LOGICAL_Z,
            "theta": state.theta,
            "phi": state.phi,
            "alpha": [state.alpha.real, state.alpha.imag],
            "beta": [state.beta.real, state.beta.imag],
            "single_error_min_fidelity_after": min(row["fidelity_after"] for row in single_error_rows),
            "single_error_max_fidelity_before": max(row["fidelity_before"] for row in single_error_rows),
            "threshold_intersection_estimate": threshold,
            "random_trials_per_p": args.random_trials,
            "seed": args.seed,
        },
    )

    plot_syndrome_heatmap(lookup_rows, figures_dir / "syndrome_lookup_heatmap.png")
    plot_single_error_recovery(single_error_rows, figures_dir / "single_error_recovery.png")
    plot_random_noise(random_rows, figures_dir / "random_noise_monte_carlo.png")
    plot_threshold(threshold_rows, threshold, figures_dir / "threshold_curve.png")
    plot_backend_like(backend_rows, figures_dir / "backend_like_noise.png")
    plot_scaling(figures_dir / "qec_scaling.png")
    plot_codeword_amplitudes(basis, figures_dir / "codeword_amplitudes.png")

    if not args.skip_circuit_drawings:
        save_circuit_diagram(build_encoded_state_circuit(target), figures_dir / "encoded_state_circuit.png")
        save_circuit_diagram(build_syndrome_extraction_circuit(), figures_dir / "syndrome_extraction_circuit.png", scale=0.56)
        save_circuit_diagram(build_full_demo_circuit(target), figures_dir / "full_qec_demo_circuit.png", scale=0.48)

    LOGGER.info("Project run complete. Figures: %s", figures_dir)
    LOGGER.info("Project run complete. Data: %s", data_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Perfect [[5,1,3]] QEC project simulations.")
    parser.add_argument("--theta", type=float, default=1.113, help="Input logical-state polar angle.")
    parser.add_argument("--phi", type=float, default=0.731, help="Input logical-state azimuthal phase.")
    parser.add_argument("--random-trials", type=int, default=3000, help="Monte Carlo trials per random-noise point.")
    parser.add_argument("--threshold-points", type=int, default=28, help="Points in the high-p threshold scan segment.")
    parser.add_argument("--seed", type=int, default=513, help="Random seed for Monte Carlo trials.")
    parser.add_argument("--skip-circuit-drawings", action="store_true", help="Skip matplotlib circuit diagrams.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


if __name__ == "__main__":
    parsed_args = parse_args()
    configure_logging(parsed_args.verbose)
    run_project(parsed_args)
