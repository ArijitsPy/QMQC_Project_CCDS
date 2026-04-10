# Member 3 Metatask: Data Scientist Track

This document explains how the Member 3 work is organized and how it should plug into the full group project.

## What Was Built

The main runner is:

```bash
qiskit_env/bin/python CCDS_QMQC_Project/Group_Project/qec_5qubit_project.py
```

It performs these tasks:

1. Derives the `[[5,1,3]]` logical codewords from the stabilizers `XZZXI`, `IXZZX`, `XIXZZ`, and `ZXIXZ`.
2. Builds the full syndrome lookup table for all 15 single-qubit Pauli errors.
3. Demonstrates noiseless recovery for every `X`, `Y`, and `Z` error on all five data qubits.
4. Runs Monte Carlo random Pauli noise after encoding.
5. Runs an exact threshold-style scan under independent depolarizing noise.
6. Runs a nonuniform backend-like noise scan as a stand-in for unavailable IBM calibration data.
7. Produces circuit diagrams and report figures.

## Generated Artifacts

Data:

- `data/syndrome_lookup.csv`
- `data/single_error_recovery.csv`
- `data/random_noise_monte_carlo.csv`
- `data/threshold_scan.csv`
- `data/backend_like_noise_scan.csv`
- `data/derived_codeword_amplitudes.csv`
- `data/summary.json`

Figures:

- `figures/encoded_state_circuit.png`
- `figures/syndrome_extraction_circuit.png`
- `figures/full_qec_demo_circuit.png`
- `figures/codeword_amplitudes.png`
- `figures/syndrome_lookup_heatmap.png`
- `figures/single_error_recovery.png`
- `figures/random_noise_monte_carlo.png`
- `figures/backend_like_noise.png`
- `figures/threshold_curve.png`
- `figures/qec_scaling.png`

Report:

- `report.md`

Hardware template:

- `submit_hardware_jobs.py`

## How To Use The Results In The Group Report

Use the noiseless single-error figure to show that the code is implemented correctly. The strongest quantitative sentence is:

`All 15 single-qubit Pauli errors recover to fidelity 0.9999999999999998 or better in the exact noiseless simulation.`

Use the random-noise and threshold plots for the Data Scientist visualization section. The simplified crossing in this run is around:

`p ~= 0.1375`

State clearly that this is a threshold-style crossing for a one-round depolarizing model, not a full fault-tolerant threshold estimate.

## Hardware And Backend Noise Next Steps

The local environment has Qiskit and Aer installed, but not `qiskit_ibm_runtime`. Because of that, the current run could not fetch live backend calibrations or submit actual IBM Quantum jobs.

To run on hardware later:

1. Install `qiskit_ibm_runtime` in the project environment.
2. Save or provide IBM Quantum credentials.
3. Run:

```bash
qiskit_env/bin/python CCDS_QMQC_Project/Group_Project/submit_hardware_jobs.py --backend ibm_brisbane --shots 1024
```

4. Record the returned job id in the final report.
5. Retrieve counts later and post-process syndromes using `data/syndrome_lookup.csv`.

The static hardware template extracts syndromes but does not apply all corrections inside the circuit. If the group wants live conditional correction, update the hardware part to use dynamic circuits where supported by the selected backend.

## Integration With Member 1 Arena

When the shared noise arena is ready, plug in the Member 3 data in one of two ways:

- Use `data/threshold_scan.csv` directly for the five-qubit curve in the group-level comparison plot.
- Or import the recovery logic from `qec_5qubit_project.py` and call it from the shared script so the Shor, Steane, five-qubit, and Bacon-Shor codes all use the same physical-error grid.

For true `NoiseModel.from_backend()` integration, the shared arena should own backend selection and noise extraction. Then this module can receive either a scaled per-qubit error profile or the resulting processed logical-error data.

## Limitations To Mention

- The five-qubit code here is a stabilizer code, not a subsystem code.
- The exact simulator assumes ideal syndrome extraction and recovery.
- The backend-like noise scan is synthetic because runtime backend calibration access is not installed locally.
- The threshold plot is a compact visualization for the report, not a large-distance threshold theorem proof.
- Real hardware runs will be deeper than the diagram because `initialize` must be decomposed into native gates.

