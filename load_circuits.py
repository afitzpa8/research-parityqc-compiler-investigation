

from turtle import pd
import qft_analysis_pqc as qft
import pprint
from qiskit.qasm3 import loads
from qiskit import QuantumCircuit
import matplotlib.pyplot as plt



def get_circuit(df, id_number, qft_method):
    """
    Filters the dataframe by the QFT method first, 
    then returns the n-th circuit within that filtered group 
    as a parsed Qiskit QuantumCircuit object.
    """
    # Filter the dataframe for just this method
    filtered_df = df[df["qft_method"] == qft_method]

    # Check if the filtered results have enough rows
    if id_number < len(filtered_df):
        # 1. Extract the raw OpenQASM string from the dataframe
        qasm_string = filtered_df.iloc[id_number]["transpiled_circuit"]

        # 2. Convert the QASM string back into a real Qiskit QuantumCircuit object
        circuit_object = loads(qasm_string)

        return circuit_object
    



def plot_circuit(df, id_number, qft_method):
    """
    Filters the dataframe by QFT method, converts the n-th OpenQASM 3.0 
    string into a Qiskit circuit, and plots it.
    """
    # 1. Filter the dataframe for this specific QFT method
    filtered_df = df[df['qft_method'] == qft_method]

    # 2. Safety check: Ensure the index exists in the filtered results
    if id_number >= len(filtered_df):
        print(f"Error: Index {id_number} is out of range. Only found {len(filtered_df)} circuits for '{qft_method}'.")
        return None
        
    # 3. Grab the raw OpenQASM 3.0 string
    qasm_string = filtered_df.iloc[id_number]['transpiled_circuit']
    # 4. Convert the text string into a Qiskit QuantumCircuit object
    circuit = loads(qasm_string)
    
    # 5. Draw the circuit using the Matplotlib ('mpl') backend
    return circuit.draw(output='mpl')
        


#analyses circuits one by one 
def analyse_circuit_parameters(circuit) -> dict:
    """
    Takes a Qiskit QuantumCircuit object
    and extracts hardware metrics.
    """
    # 1. Get the dictionary of all gate counts
    gate_counts = dict(circuit.count_ops())
    
    # 2. Count 2-qubit (non-local) gates specifically
    # Works natively in Qiskit 1.x/2.x environments
    two_qubit_gate_count = circuit.num_nonlocal_gates()
    
    # 3. Calculate total size excluding structural barriers
    # Barriers are not physical operations/gates
    actual_total_gates = circuit.size()
    if 'barrier' in gate_counts:
        actual_total_gates -= gate_counts['barrier']
        
    # 4. Compile all analytical data into a clean dictionary
    analysis_metrics = {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "circuit_depth": circuit.depth(),
        "total_gate_count": actual_total_gates,
        "two_qubit_gate_count": two_qubit_gate_count,
        "one_qubit_gate_count": actual_total_gates - two_qubit_gate_count,
        "gate_breakdown": gate_counts
    }
    
    return analysis_metrics

def get_circuit_metrics(circuit, backend=None, dt=None) -> dict:
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


#collect sample collection of circuits for each qft method for analysis 
def get_xth_circuits(df, qft_method_name: str, x: int) -> dict:
    """
    Filters the dataframe for a specific QFT method and returns a dictionary 
    mapping each number_of_qubits to its X-th transpiled circuit.
    
    Parameters:
    - df: The input pandas DataFrame.
    - qft_method_name: The string name of the QFT method to filter by.
    - x: The human-readable position of the circuit to extract (e.g., 10 for the 10th circuit).
    """
    # 1. Convert human position to Python 0-based index
    target_index = x - 1
    
    # 2. Filter the DataFrame for the requested QFT method
    filtered_df = df[df['qft_method'] == qft_method_name]
    
    if filtered_df.empty:
        print(f"Error: No circuits found for QFT method '{qft_method_name}'.")
        return {}
        
    circuits_dict = {}
    
    # 3. Group by the qubit size and pull the x-th circuit
    for num_qubits, group in filtered_df.groupby('number_of_qubits'):
        # Check if the group has enough rows to satisfy the requested position
        if len(group) >= x:
            # .iloc[target_index] grabs the exact requested positional row
            qasm_string = group.iloc[target_index]['transpiled_circuit']
            circuits_dict[int(num_qubits)] = loads(qasm_string)
    
    return circuits_dict


