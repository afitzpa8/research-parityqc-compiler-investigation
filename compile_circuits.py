from qiskit.qasm3 import loads, dumps
from qiskit.compiler import transpile
from qiskit_aer import AerSimulator  # Using a simulator as a dummy backend target

def compile_qasm_string(qasm_str: str, backend=None) -> str:
    """
    Takes an OpenQASM 3.0 string, compiles it for a target backend,
    and returns the compiled circuit back as a single-line OpenQASM 3.0 string.
    """
    # 1. Parse the string into a Qiskit QuantumCircuit object
    circuit = loads(qasm_str)
    
    # 2. Use a default simulator backend if none is provided
    if backend is None:
        backend = AerSimulator()
        
    # 3. Compile (transpile) the circuit for the backend
    # Optimization_level 3 gives the highest compression/cleanup
    compiled_circuit = transpile(circuit, backend=backend, optimization_level=3)
    
    # 4. Export back to OpenQASM 3.0 string
    compiled_qasm_multiline = dumps(compiled_circuit)
    
    # 5. Strip out newlines to match your exact single-line format
    compiled_qasm_single_line = "".join(compiled_qasm_multiline.splitlines())
    
    return compiled_qasm_single_line