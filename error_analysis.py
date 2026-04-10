# Error Injection Utilities for Quantum Circuits

def inject_single_bit_flip(state, target_qubit):
    """
    Injects a single-bit flip error on the specified qubit.
    Args:
        state (list): The quantum state vector.
        target_qubit (int): The index of the qubit to flip.
    """  
    # Calculate the size of the state vector
    size = len(state)
    # Create a new state vector
    new_state = state.copy()
    # Perform the bit flip
    if 0 <= target_qubit < size:
        new_state[target_qubit] = 1 - new_state[target_qubit]  # Assuming binary state
    else:
        raise IndexError("Target qubit index out of bounds.")
    return new_state


def inject_phase_flip(state, target_qubit):
    """
    Injects a phase-flip error on the specified qubit.
    Args:
        state (list): The quantum state vector.
        target_qubit (int): The index of the qubit to flip.
    """
    # Here we will use a complex representation to apply phase-flip
    new_state = state.copy()
    if 0 <= target_qubit < len(state):
        new_state[target_qubit] *= -1  # Apply phase flip
    else:
        raise IndexError("Target qubit index out of bounds.")
    return new_state


def inject_error(state, target_qubit, error_type):
    """
    Inject an error of the specified type on the target qubit.
    Args:
        state (list): The quantum state vector.
        target_qubit (int): The index of the qubit to apply the error on.
        error_type (str): Type of the error ('bit-flip' or 'phase-flip').
    """  
    if error_type == 'bit-flip':
        return inject_single_bit_flip(state, target_qubit)
    elif error_type == 'phase-flip':
        return inject_phase_flip(state, target_qubit)
    else:
        raise ValueError("Unsupported error type. Use 'bit-flip' or 'phase-flip'.")
