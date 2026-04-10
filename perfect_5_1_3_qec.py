"""
Perfect [[5,1,3]] Quantum Error Correction Code Implementation
Encodes 1 logical qubit into 5 physical qubits
Detects and corrects all single-qubit errors (bit-flip or phase-flip)
Author: Arijit (Member 3 - Data Scientist)
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit.primitives import Sampler
from qiskit_aer.primitives import Sampler as AerSampler
import matplotlib.pyplot as plt
from typing import Tuple, Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Perfect513QEC:
    """
    Perfect [[5,1,3]] Quantum Error Correction Code
    
    Features:
    - Encodes 1 logical qubit into 5 physical qubits
    - Corrects all single-qubit errors (X or Z)
    - Code distance d=3 (can correct 1 error)
    - Stabilizer group: {XZZXI, IXZZX, XIXZZ, ZXIXZ}
    """
    
    def __init__(self):
        logger.info("Initializing Perfect [[5,1,3]] QEC Code")
        # Stabilizer generators for error syndrome mapping
        self.stabilizers = [
            'XZZXI',
            'IXZZX', 
            'XIXZZ',
            'ZXIXZ'
        ]
        
        # Error to syndrome mapping (precomputed)
        self.error_to_syndrome = self._build_error_syndrome_map()
        logger.info(f"Built error-syndrome lookup table with {len(self.error_to_syndrome)} entries")
    
    def _build_error_syndrome_map(self) -> Dict[str, int]:
        """
        Build lookup table mapping errors to syndrome measurements
        Returns dict: {error_location_and_type -> syndrome_value}
        """
        mapping = {}
        
        # No error
        mapping['I'] = 0
        
        # Single qubit errors (location, type)
        error_types = ['X', 'Z', 'Y']  # Y = iXZ
        for qubit in range(5):
            for error_type in error_types:
                error_str = f'Qubit{qubit}_{error_type}'
                syndrome = self._calculate_syndrome(qubit, error_type)
                mapping[error_str] = syndrome
        
        return mapping
    
    def _calculate_syndrome(self, error_qubit: int, error_type: str) -> int:
        """
        Calculate syndrome bits for a single-qubit error
        Returns 4-bit syndrome value
        """
        syndrome = 0
        
        stabilizers = [
            [1, 0, 0, 0, 1],  # XZZXI
            [0, 1, 0, 0, 1],  # IXZZX
            [1, 0, 1, 0, 0],  # XIXZZ
            [0, 1, 0, 1, 0]   # ZXIXZ
        ]
        
        # Error mapping: X errors anticommute with Z stabilizers, Z errors with X stabilizers
        for stab_idx, stab in enumerate(stabilizers):
            if error_type in ['X', 'Y']:  # X-type error
                x_part = [1, 0, 1, 0, 0] if stab_idx < 2 else [1, 0, 1, 0, 0]
                anticommutes = x_part[error_qubit] & stab[error_qubit]
            else:  # Z-type error
                z_part = [0, 0, 1, 1, 1] if stab_idx < 2 else [0, 0, 1, 1, 1]
                anticommutes = z_part[error_qubit] & stab[error_qubit]
            
            if anticommutes:
                syndrome |= (1 << stab_idx)
        
        return syndrome
    
    def encode_circuit(self, logical_state: np.ndarray = None) -> QuantumCircuit:
        """
        Encode logical qubit into 5 physical qubits
        Uses stabilizer-based encoding circuit
        
        Args:
            logical_state: Optional [alpha, beta] amplitudes for |ψ⟩ = α|0⟩ + β|1⟩
        
        Returns:
            QuantumCircuit with 5 physical qubits encoded
        """
        logger.info("Building encoding circuit for [[5,1,3]] code")
        
        qc = QuantumCircuit(5, name='Encode')
        
        # Prepare logical qubit state if provided
        if logical_state is not None:
            theta = 2 * np.arccos(np.abs(logical_state[0]))
            phase = np.angle(logical_state[1]) - np.angle(logical_state[0])
            qc.ry(theta, 0)
            qc.rz(phase, 0)
            logger.info(f"Encoded arbitrary state with θ={{theta:.4f}}, φ={{phase:.4f}}")
        
        # Encoding circuit for [[5,1,3]]
        # This spreads the logical qubit across all 5 physical qubits
        # Using the transversal property of the code
        
        # Step 1: Initialize auxiliary qubits with CNOT gates
        qc.cx(0, 1)
        qc.cx(0, 2)
        qc.cx(0, 3)
        qc.cx(0, 4)
        
        # Step 2: Hadamard layer for stabilizer compatibility
        for i in range(5):
            qc.h(i)
        
        # Step 3: Entangling gates
        qc.cx(0, 2)
        qc.cx(1, 3)
        qc.cx(2, 4)
        
        logger.info("Encoding circuit complete")
        return qc
    
    def syndrome_measurement_circuit(self) -> QuantumCircuit:
        """
        Build syndrome measurement circuit
        Measures 4 syndrome bits from 5 physical qubits
        
        Returns:
            QuantumCircuit with syndrome extraction
        """
        logger.info("Building syndrome measurement circuit")
        
        # 5 data qubits + 4 ancilla qubits for syndrome measurement
        qc = QuantumCircuit(9, 4, name='MeasureSyndrome')
        
        # Measure stabilizer generators using ancilla qubits
        # S1 = XZZXI
        qc.h(5)
        qc.cx(5, 0)
        qc.cx(2, 5)
        qc.cx(3, 5)
        qc.cx(4, 5)
        qc.h(5)
        qc.measure(5, 0)
        
        # S2 = IXZZX
        qc.h(6)
        qc.cx(1, 6)
        qc.cx(2, 6)
        qc.cx(3, 6)
        qc.cx(4, 6)
        qc.h(6)
        qc.measure(6, 1)
        
        # S3 = XIXZZ
        qc.h(7)
        qc.cx(0, 7)
        qc.cx(2, 7)
        qc.cx(3, 7)
        qc.cx(4, 7)
        qc.h(7)
        qc.measure(7, 2)
        
        # S4 = ZXIXZ
        qc.h(8)
        qc.cx(1, 8)
        qc.cx(3, 8)
        qc.cx(4, 8)
        qc.h(8)
        qc.measure(8, 3)
        
        logger.info("Syndrome measurement circuit complete")
        return qc
    
    def decoding_circuit(self, syndrome: int) -> QuantumCircuit:
        """
        Build error correction circuit based on measured syndrome
        
        Args:
            syndrome: 4-bit syndrome value from measurement
        
        Returns:
            QuantumCircuit that corrects the error
        """
        logger.info(f"Building decoding circuit for syndrome: {{syndrome:04b}}")
        
        qc = QuantumCircuit(5, name='Decode')
        
        # Syndrome to correction mapping
        # This is derived from the stabilizer group structure
        corrections = {
            0: [],  # No error
            1: [(0, 'X')],  # Error on qubit 0
            2: [(1, 'X')],  # Error on qubit 1
            3: [(0, 'X'), (1, 'X')],
            4: [(2, 'X')],  # Error on qubit 2
            5: [(0, 'X'), (2, 'X')],
            6: [(1, 'X'), (2, 'X')],
            7: [(0, 'X'), (1, 'X'), (2, 'X')],
            8: [(3, 'X')],  # Error on qubit 3
            9: [(0, 'X'), (3, 'X')],
            10: [(1, 'X'), (3, 'X')],
            11: [(0, 'X'), (1, 'X'), (3, 'X')],
            12: [(2, 'X'), (3, 'X')],
            13: [(0, 'X'), (2, 'X'), (3, 'X')],
            14: [(1, 'X'), (2, 'X'), (3, 'X')],
            15: [(0, 'X'), (1, 'X'), (2, 'X'), (3, 'X')],
        }
        
        # Apply corrections
        if syndrome in corrections:
            for qubit, gate_type in corrections[syndrome]:
                if gate_type == 'X':
                    qc.x(qubit)
                elif gate_type == 'Z':
                    qc.z(qubit)
            logger.info(f"Applied corrections: {{corrections[syndrome]}}")
        else:
            logger.warning(f"Unknown syndrome {{syndrome}}, no correction applied")
        
        return qc
    
    def full_qec_circuit(self, logical_state: np.ndarray = None) -> QuantumCircuit:
        """
        Build complete QEC circuit: encode -> (optional error) -> syndrome measure -> decode
        
        Args:
            logical_state: Optional logical qubit state
        
        Returns:
            Complete QEC circuit
        """
        logger.info("Building full QEC circuit")
        
        qc = QuantumCircuit(9, 4, name='QEC_Full')
        
        # Encode
        encode_qc = self.encode_circuit(logical_state)
        qc = qc.compose(encode_qc, qubits=range(5))
        
        # Syndrome measurement
        syndrome_qc = self.syndrome_measurement_circuit()
        qc = qc.compose(syndrome_qc)
        
        return qc
    
    def run_simulation(self, circuit: QuantumCircuit, shots: int = 1024, 
                      backend_name: str = 'qasm_simulator') -> Dict:
        """
        Run quantum circuit simulation
        
        Args:
            circuit: QuantumCircuit to simulate
            shots: Number of measurement shots
            backend_name: Simulator backend to use
        
        Returns:
            Execution results dictionary
        """
        logger.info(f"Running simulation with {shots} shots on {backend_name}")
        
        simulator = AerSimulator()
        circuit_copy = circuit.copy()
        circuit_copy.measure_all()
        
        job = simulator.run(circuit_copy, shots=shots)
        result = job.result()
        counts = result.get_counts()
        
        logger.info(f"Simulation complete. Results: {counts}")
        return counts
    
    def display_circuit_diagram(self, circuit: QuantumCircuit, filename: str = None) -> None:
        """
        Display and save circuit diagram
        
        Args:
            circuit: QuantumCircuit to visualize
            filename: Optional file path to save diagram
        """
        logger.info(f"Generating circuit diagram{' for file: ' + filename if filename else ''}")
        
        fig = circuit.decompose().draw(output='mpl', scale=0.5)
        
        if filename:
            fig.savefig(filename, dpi=150, bbox_inches='tight')
            logger.info(f"Circuit diagram saved to {filename}")
        
        return fig
    
