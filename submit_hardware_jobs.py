"""
Optional IBM Quantum hardware submission template for the [[5,1,3]] demo.

This file is intentionally separate from qec_5qubit_project.py because the
local environment used for the project does not currently include
qiskit_ibm_runtime.  Install and configure IBM Quantum credentials before
using it, then run for example:

    qiskit_env/bin/python CCDS_QMQC_Project/Group_Project/submit_hardware_jobs.py --backend ibm_brisbane

The submitted circuit is the static encoded-state-plus-syndrome-extraction
demo.  Real hardware cannot branch on the measured syndrome inside this static
template; do recovery as post-processing using data/syndrome_lookup.csv.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from qec_5qubit_project import (
    build_full_demo_circuit,
    configure_logging,
    derive_code_basis,
    encode_state,
    logical_state,
)


LOGGER = logging.getLogger("perfect_513_hardware")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit the five-qubit QEC demo to IBM Quantum hardware.")
    parser.add_argument("--backend", default=None, help="IBM backend name, e.g. ibm_brisbane. Uses least_busy if omitted.")
    parser.add_argument("--shots", type=int, default=1024, help="Number of shots to request.")
    parser.add_argument("--theta", type=float, default=1.113, help="Input logical-state polar angle.")
    parser.add_argument("--phi", type=float, default=0.731, help="Input logical-state azimuthal phase.")
    parser.add_argument("--channel", default=os.getenv("IBM_QUANTUM_CHANNEL", "ibm_quantum"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    except ImportError as exc:
        raise SystemExit(
            "qiskit_ibm_runtime is not installed in this environment. "
            "Install it and configure IBM Quantum credentials before submitting hardware jobs."
        ) from exc

    basis = derive_code_basis()
    target = encode_state(logical_state(args.theta, args.phi), basis)
    circuit = build_full_demo_circuit(target)
    circuit.name = "perfect_513_static_syndrome_demo"

    service = QiskitRuntimeService(channel=args.channel)
    if args.backend:
        backend = service.backend(args.backend)
    else:
        backend = service.least_busy(operational=True, simulator=False, min_num_qubits=9)

    LOGGER.info("Selected backend: %s", backend.name)
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa_circuit = pass_manager.run(circuit)

    sampler = Sampler(mode=backend)
    job = sampler.run([isa_circuit], shots=args.shots)
    LOGGER.info("Submitted job %s to %s", job.job_id(), backend.name)

    output = {
        "job_id": job.job_id(),
        "backend": backend.name,
        "shots": args.shots,
        "circuit_name": circuit.name,
        "note": "Use IBM Quantum dashboard or job.result() later to retrieve counts.",
    }
    out_path = Path(__file__).resolve().parent / "data" / "hardware_job_submission.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    LOGGER.info("Wrote %s", out_path)


if __name__ == "__main__":
    main()
