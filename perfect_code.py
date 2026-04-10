"""
Member 3 interface for the Perfect [[5,1,3]] code.

The shared arena can import perfect_code_circuit(input_state) and apply its own
noise_model(p).  The helper returns an encoded five-data-qubit circuit; the
syndrome/recovery logic used for benchmarking lives in qec_5qubit_project.py.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit

from qec_5qubit_project import (
    LogicalStateSpec,
    build_encoded_state_circuit,
    build_full_demo_circuit,
    build_syndrome_extraction_circuit,
    derive_code_basis,
    encode_state,
    logical_state,
)


def _state_from_input(input_state: Sequence[complex] | LogicalStateSpec | None) -> LogicalStateSpec:
    if input_state is None:
        return logical_state(theta=math.pi / 2, phi=0.0)
    if isinstance(input_state, LogicalStateSpec):
        return input_state
    if len(input_state) != 2:
        raise ValueError("input_state must be [alpha, beta]")

    alpha = complex(input_state[0])
    beta = complex(input_state[1])
    norm = math.sqrt(abs(alpha) ** 2 + abs(beta) ** 2)
    if norm == 0:
        raise ValueError("input_state cannot be the zero vector")
    alpha /= norm
    beta /= norm

    theta = 2 * math.acos(min(1.0, max(0.0, abs(alpha))))
    phi = float(np.angle(beta) - np.angle(alpha))
    return LogicalStateSpec(alpha=alpha, beta=beta, theta=theta, phi=phi)


def perfect_code_circuit(input_state: Sequence[complex] | LogicalStateSpec | None = None) -> QuantumCircuit:
    """
    Return the encoded Perfect [[5,1,3]] circuit for the shared arena.

    Parameters
    ----------
    input_state:
        Single logical qubit amplitudes [alpha, beta].  If omitted, the
        default logical state is |+>.

    Returns
    -------
    QuantumCircuit
        A 5-qubit encoded-state circuit.  Member 1's arena can append its
        noise_model(p), syndrome extraction, decoding, and measurement policy.
    """

    basis = derive_code_basis()
    encoded = encode_state(_state_from_input(input_state), basis)
    return build_encoded_state_circuit(encoded)


def syndrome_extraction_circuit() -> QuantumCircuit:
    """Return the four-stabilizer syndrome measurement circuit."""

    return build_syndrome_extraction_circuit()


def perfect_code_demo_circuit(
    input_state: Sequence[complex] | LogicalStateSpec | None = None,
    error_qubit: int = 2,
    error: str = "X",
) -> QuantumCircuit:
    """Return encode -> injected error -> syndrome extraction for diagrams."""

    basis = derive_code_basis()
    encoded = encode_state(_state_from_input(input_state), basis)
    return build_full_demo_circuit(encoded, error_qubit=error_qubit, error=error)

