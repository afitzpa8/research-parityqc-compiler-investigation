from qiskit.qasm3 import loads, dumps
from qiskit.compiler import transpile
from qiskit_aer import AerSimulator  # Using a simulator as a dummy backend target
import warnings 
import load_circuits as lc

from qctrlqcpaibm.transpiler.staged_pass_manager_config_factory import IbmStagedPassManagerConfigFactory
from qctrlqcpaibm.transpiler.target_factory import IbmTargetFactory
from qiskit import QuantumCircuit
from qiskit.transpiler import Layout
from qctrlqces.transpiler.pass_manager import SuperconductingStagedPassManagerFactory



def qiskit_compile(circuit, backend=None) -> str:
    """
    Takes a Qiskit QuantumCircuit object, compiles it for a target backend,
    and returns the compiled circuit back as a single-line OpenQASM 3.0 string.
    """
     # Use a default simulator backend if none is provided
    if backend is None:
        backend = AerSimulator()
        
    # 3. Compile (transpile) the circuit for the backend
    # Optimization_level 3 gives the highest compression/cleanup
    compiled_circuit = transpile(circuit, backend=backend, optimization_level=3)
    
    return compiled_circuit

def fo_compiler(
    circuits: list[QuantumCircuit],
    device_name: str,
    credentials: dict[str, str] = dict(),
    initial_layout: Layout | None = None,
    unitary_resynthesis_threshold = None,
):
    target_factory = IbmTargetFactory()
    target = target_factory.build_target(device_name, credentials=credentials)
    transpiler_config = IbmStagedPassManagerConfigFactory.build_config(target)
    if unitary_resynthesis_threshold is not None:
        new_configs = {"unitary_resynthesis_threshold": unitary_resynthesis_threshold}
    else:
        new_configs = dict()
    if initial_layout:
        new_configs["initial_layout"] = initial_layout
    transpiler_config = transpiler_config.update_stage_configs(new_configs)
    transpiler_factory = SuperconductingStagedPassManagerFactory(transpiler_config)
    transpiler = transpiler_factory.build_non_parametric()
    return transpiler.run(circuits=circuits)


def get_transpilation_metrics(circuit, backend=None, dt=None) -> dict:
    """
    Takes a Qiskit QuantumCircuit object, transpiles it for a target backend,
    and returns a dictionary containing circuit depth, 2Q gate count, and duration.
    """
    # 3. Extract Circuit Depth
    depth = circuit.depth()
    
    # 4. Extract Number of 2Q Gates
    ops_count = circuit.count_ops()
    # Safely look for common 2Q basis gates used by IBM hardware (ecr, cz, cx)
    num_2q_gates = circuit.num_nonlocal_gates()  # This counts all non-local gates, which includes 2Q gates
    num_2q_depth = circuit.depth(filter_function=lambda x: len(x.qubits) == 2)
    # 4. Extract lowercase duration safely while ignoring the deprecation warning
    #with warnings.catch_warnings():
    #    warnings.filterwarnings("ignore", category=DeprecationWarning)
        # We look for 'duration' in lowercase
    #    raw_duration = getattr(circuit, 'duration', None)
        
    #if raw_duration is not None:
    #    circuit_duration = raw_duration * dt * 1e6  # Convert to microseconds
    #else:
    #    circuit_duration = 0.0
    return {
        "depth": depth,
        "num_2q_gates": num_2q_gates,
        "num_2q_depth": num_2q_depth,
    }

def compile_multiple_fo(
    input_circuits_dict,
    api_key,
    device_name="ibm_boston",
    resynthesis_threshold=4e-5
):
    """
    Compiles a dictionary of circuits using the Fire Opal compiler
    
    Parameters:
    -----------
    input_circuits_dict : dict
        A dictionary where values are quantum circuit objects (e.g., heavyhex_10th_dict)
    api_key : str
        Your API key for credentials.
    device_name : str
        The target quantum device (default: "ibm_boston")
    resynthesis_threshold : float
        Unitary resynthesis threshold for Fire Opal (default: 4e-5)
        
    Returns:
    --------
    compiled_circuits : dict
        Dict mapping {num_qubits: compiled_circuit_object}
    """
    compiled_circuits = {} 
  

    for circuit in input_circuits_dict.values():
        num_qubits = circuit.num_qubits
        
        # 1. Compile the circuit using Fire Opal
        compiled_circuit_list = fo_compiler(
            circuits=[circuit],
            device_name=device_name,
            credentials={"token": api_key},
            initial_layout=None,
            unitary_resynthesis_threshold=resynthesis_threshold,
        )
        
        # Extracted compiled circuit (Fire Opal returns a list)
        compiled_circuit = compiled_circuit_list[0]
        
        # 2. Store the compiled circuit object
        compiled_circuits[num_qubits] = compiled_circuit
        
        
    return compiled_circuits

def compile_multiple_qiskit(input_circuits_dict, backend):
    """
    Compiles a dictionary of circuits using Qiskit
    
    Parameters:
    -----------
    input_circuits_dict : dict
        A dictionary where values are quantum circuit objects (e.g., heavyhex_10th_dict)
    backend : qiskit.providers.backend.Backend
        The target Qiskit backend object to compile against.
        
    Returns:
    --------
    compiled_circuits : dict
        Dict mapping {num_qubits: compiled_circuit_object}
    """
    compiled_circuits = {}
  

    for circuit in input_circuits_dict.values():
        num_qubits = circuit.num_qubits
        
        # 1. Compile the circuit using Qiskit
        compiled_circuit = qiskit_compile(circuit, backend=backend)
        
        # 2. Store the compiled circuit object
        compiled_circuits[num_qubits] = compiled_circuit
        
    return compiled_circuits