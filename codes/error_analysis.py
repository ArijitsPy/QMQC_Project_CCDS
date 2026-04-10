"""
Error Analysis and Injection Module for [[5,1,3]] QEC Code
Handles error injection at different circuit stages and noise model simulations
Author: Arijit (Member 3 - Data Scientist)
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error, depolarizing_error
import logging
from typing import Dict, List, Tuple, Callable

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ErrorInjector:
    """
    Inject single and multiple errors at specific circuit locations
    """
    
    def __init__(self):
        logger.info("Initializing Error Injector")
        self.error_types = ['X', 'Z', 'Y', 'I']
    
    def inject_single_error(self, circuit: QuantumCircuit, qubit: int, 
                           error_type: str, location: str = 'after_encoding') -> QuantumCircuit:
        """
        Inject single-qubit error at specified location
        
        Args:
            circuit: Base quantum circuit
            qubit: Target qubit
            error_type: 'X', 'Z', 'Y', or 'I' (no error)
            location: 'after_encoding', 'during_syndrome', etc.
        
        Returns:
            Circuit with injected error
        """
        logger.info(f"Injecting {error_type} error on qubit {qubit} at {location}")
        
        qc = circuit.copy()
        
        if error_type == 'X':
            qc.x(qubit)
        elif error_type == 'Z':
            qc.z(qubit)
        elif error_type == 'Y':
            qc.y(qubit)
        # 'I' means no error, so do nothing
        
        return qc
    
    def inject_multiple_errors(self, circuit: QuantumCircuit, 
                              errors: List[Tuple[int, str]]) -> QuantumCircuit:
        """
        Inject multiple errors simultaneously
        
        Args:
            circuit: Base quantum circuit
            errors: List of (qubit, error_type) tuples
        
        Returns:
            Circuit with all errors injected
        """
        logger.info(f"Injecting {len(errors)} errors: {errors}")
        
        qc = circuit.copy()
        for qubit, error_type in errors:
            if error_type == 'X':
                qc.x(qubit)
            elif error_type == 'Z':
                qc.z(qubit)
            elif error_type == 'Y':
                qc.y(qubit)
        
        return qc
    
    def inject_random_error(self, circuit: QuantumCircuit, 
                           num_qubits: int = 5, 
                           num_errors: int = 1) -> QuantumCircuit:
        """
        Inject random errors on random qubits
        
        Args:
            circuit: Base quantum circuit
            num_qubits: Number of physical qubits
            num_errors: Number of random errors to inject
        
        Returns:
            Circuit with random errors
        """
        logger.info(f"Injecting {num_errors} random errors on {num_qubits} qubits")
        
        qc = circuit.copy()
        
        for _ in range(num_errors):
            qubit = np.random.randint(0, num_qubits)
            error_type = np.random.choice(['X', 'Z', 'Y'])
            
            if error_type == 'X':
                qc.x(qubit)
            elif error_type == 'Z':
                qc.z(qubit)
            elif error_type == 'Y':
                qc.y(qubit)
            
            logger.info(f"  - Random {error_type} on qubit {qubit}")
        
        return qc


class NoiseModelBuilder:
    """
    Build and manage various noise models for realistic simulations
    """
    
    def __init__(self):
        logger.info("Initializing Noise Model Builder")
    
    def depolarizing_noise(self, error_rate: float) -> NoiseModel:
        """
        Create depolarizing noise model where each gate has error_rate probability
        of being replaced with a random Pauli operation
        
        Args:
            error_rate: Probability of error per gate (0.0 to 1.0)
        
        Returns:
            NoiseModel object
        """
        logger.info(f"Building depolarizing noise model with error rate: {error_rate}")
        
        noise_model = NoiseModel()
        
        # Single-qubit gate errors
        error_1q = depolarizing_error(error_rate, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, ['h', 'x', 'y', 'z', 's', 't'])
        
        # Two-qubit gate errors (higher error rate)
        error_2q = depolarizing_error(error_rate * 2, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ['cx'])
        
        # Measurement errors
        error_meas = depolarizing_error(error_rate, 1)
        noise_model.add_all_qubit_quantum_error(error_meas, ['measure'])
        
        logger.info("Depolarizing noise model created")
        return noise_model
    
    def amplitude_damping_noise(self, error_rate: float) -> NoiseModel:
        """
        Create amplitude damping noise model (energy dissipation)
        
        Args:
            error_rate: Probability of amplitude damping
        
        Returns:
            NoiseModel object
        """
        logger.info(f"Building amplitude damping noise model with error rate: {error_rate}")
        
        from qiskit_aer.noise import amplitude_damping_error
        
        noise_model = NoiseModel()
        
        error_ad = amplitude_damping_error(error_rate)
        noise_model.add_all_qubit_quantum_error(error_ad, ['h', 'x', 'y', 'z', 'cx'])
        
        logger.info("Amplitude damping noise model created")
        return noise_model
    
    def phase_damping_noise(self, error_rate: float) -> NoiseModel:
        """
        Create phase damping noise model (dephasing)
        
        Args:
            error_rate: Probability of phase damping
        
        Returns:
            NoiseModel object
        """
        logger.info(f"Building phase damping noise model with error rate: {error_rate}")
        
        from qiskit_aer.noise import phase_damping_error
        
        noise_model = NoiseModel()
        
        error_pd = phase_damping_error(error_rate)
        noise_model.add_all_qubit_quantum_error(error_pd, ['h', 'x', 'y', 'z', 'cx'])
        
        logger.info("Phase damping noise model created")
        return noise_model
    
    def combined_noise(self, depol_rate: float, 
                      amplitude_damp_rate: float,
                      phase_damp_rate: float) -> NoiseModel:
        """
        Create combined noise model with multiple error sources
        
        Args:
            depol_rate: Depolarizing error rate
            amplitude_damp_rate: Amplitude damping rate
            phase_damp_rate: Phase damping rate
        
        Returns:
            Combined NoiseModel object
        """
        logger.info(f"Building combined noise model: depol={depol_rate}, "
                   f"amp_damp={amplitude_damp_rate}, phase_damp={phase_damp_rate}")
        
        from qiskit_aer.noise import phase_damping_error, amplitude_damping_error
        
        noise_model = NoiseModel()
        
        # Combine multiple error types
        errors_1q = []
        if depol_rate > 0:
            errors_1q.append(depolarizing_error(depol_rate, 1))
        if amplitude_damp_rate > 0:
            errors_1q.append(amplitude_damping_error(amplitude_damp_rate))
        if phase_damp_rate > 0:
            errors_1q.append(phase_damping_error(phase_damp_rate))
        
        if errors_1q:
            combined_error_1q = errors_1q[0]
            for error in errors_1q[1:]:
                combined_error_1q = combined_error_1q.compose(error)
            
            noise_model.add_all_qubit_quantum_error(combined_error_1q, 
                                                   ['h', 'x', 'y', 'z', 's', 't'])
        
        # Two-qubit errors
        error_2q = depolarizing_error(depol_rate * 2, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ['cx'])
        
        logger.info("Combined noise model created")
        return noise_model
    
    def scale_noise_rate(self, base_rate: float, scale_factor: float) -> float:
        """
        Scale error rate by factor, clamping to [0, 0.5]
        
        Args:
            base_rate: Original error rate
            scale_factor: Scaling factor (typically 0.5 to 2.0)
        
        Returns:
            Scaled error rate
        """
        scaled = base_rate * scale_factor
        clamped = np.clip(scaled, 0.0, 0.5)
        
        logger.info(f"Scaled error rate: {base_rate} * {scale_factor} = {scaled} "
                   f"(clamped to {clamped})")
        return clamped


class ErrorCorrection:
    """
    Evaluate error correction performance
    """
    
    def __init__(self):
        logger.info("Initializing Error Correction Evaluator")
    
    def calculate_fidelity(self, expected_state: np.ndarray, 
                          measured_counts: Dict[str, int], 
                          shots: int) -> float:
        """
        Calculate state fidelity from measurement results
        
        Args:
            expected_state: Expected quantum state [alpha, beta]
            measured_counts: Measurement result counts dictionary
            shots: Total number of shots
        
        Returns:
            Fidelity value (0 to 1)
        """
        # Extract probability of measuring |0⟩
        prob_0 = measured_counts.get('0' * (len(next(iter(measured_counts)))), 0) / shots
        
        # Theoretical probability
        expected_prob_0 = np.abs(expected_state[0]) ** 2;
        
        # Simplified fidelity metric
        fidelity = 1 - np.abs(prob_0 - expected_prob_0);
        
        logger.info(f"Calculated fidelity: {fidelity:.4f}")
        return fidelity;
    
    def compare_with_without_correction(self, circuit_without_qec: QuantumCircuit,
                                       circuit_with_qec: QuantumCircuit,
                                       shots: int = 1024) -> Tuple[float, float]:
        """
        Compare fidelity with and without error correction
        
        Args:
            circuit_without_qec: Circuit without QEC
            circuit_with_qec: Circuit with QEC
            shots: Number of shots
        
        Returns:
            (fidelity_without_qec, fidelity_with_qec)
        """
        simulator = AerSimulator();
        
        # Run without QEC
        job1 = simulator.run(circuit_without_qec.copy().measure_all(), shots=shots);
        counts1 = job1.result().get_counts();
        
        # Run with QEC
        job2 = simulator.run(circuit_with_qec.copy().measure_all(), shots=shots);
        counts2 = job2.result().get_counts();
        
        # Simplified fidelity: probability of correct measurement
        fidelity_without = max(counts1.values()) / shots;
        fidelity_with = max(counts2.values()) / shots;
        
        logger.info(f"Fidelity comparison - Without QEC: {fidelity_without:.4f}, "
                   f"With QEC: {fidelity_with:.4f}");
        
        return fidelity_without, fidelity_with;
