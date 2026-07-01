#  Parity Quantum Computing GmbH © 2026. All rights reserved.

import gzip
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pandas import DataFrame
from parityos.bits import Qubit
from parityos.operators import Z
from parityos.states import PauliBasisState, PauliBasisStateCounts


def process_qft_experiments(file_path: str) -> pd.DataFrame:
    # Decompress and load the JSON data efficiently
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        data = json.load(f)

    # Parse data
    rows = []
    for sample in data:
        inner_data = sample.get("_data", {})

        counts_inner = inner_data.get("counts", {}).get("_data", {})
        exporter_inner = inner_data.get("exporter_result", {}).get("_data", {})

        state_to_count = {
            pair_data[0]: float(pair_data[1])
            for pair in counts_inner.get("bitstring_count_pairs", {}).get("_data", [])
            if len(pair_data := pair.get("_data", [])) == 2
        }

        ordered_qubits = tuple(
            q.get("_data", {}).get("id")
            for q in counts_inner.get("ordered_qubits", {}).get("_data", [])
            if isinstance(q, dict)
        )

        clean_qubit_map = {
            item[0].get("_data", {}).get("id"): item[1]
            for item in exporter_inner.get("qubit_map", [])
            if len(item) == 2
        }

        rows.append(
            {
                "transpiled_circuit": inner_data.get("transpiled_circuit"),
                "qft_method": inner_data.get("qft_method"),
                "backend": inner_data.get("backend"),
                "number_of_qubits": inner_data.get("number_of_qubits"),
                "basis_state_index": inner_data.get("basis_state_index"),
                "counts": {
                    "ordered_qubits": ordered_qubits,
                    "state_to_count": state_to_count,
                    "total_count": sum(state_to_count.values()),
                },
                "exporter_result": {
                    "circuit": exporter_inner.get("circuit", {}).get("_data", ""),
                    "qubit_map": clean_qubit_map,
                },
            }
        )

    return pd.DataFrame(rows)


def calculate_process_fidelity_for_different_k(
    results_for_different_k: list[
        tuple[PauliBasisState[Qubit, Z], PauliBasisStateCounts[Qubit, Z]]
    ],
) -> float:
    """Calculate the process fidelity as defined by IBM in equation (2) of this
    preprint: https://arxiv.org/pdf/2403.09514. In this context 'k' refers to the index of the
    computational basis state. In theory, the fidelity is the average of all basis states, while
    in practise only a subset of basis states is considered. This is reflected by the fact that
    the results parameter is a dictionary mapping a limited set of basis states to measurement
    results.

    :param results_for_different_k: Dictionary mapping each basis state index k (int) to its
        measurement results (Counts).
        Each Counts object contains bitstring keys and their respective
        counts as values. Alternatively, the same mapping can be used as
        a tuple, this is useful if repeated basis_indices are used.
    :returns: The process fidelity calculated based on the input data.

    :raises ValueError: If no basis states are provided in `results_for_different_k`.
    """
    probability_sum_terms = []
    for bitstring_of_k, counts in results_for_different_k:
        assert bitstring_of_k.ordered_qubits == counts["ordered_qubits"]
        counts_of_expected_bitstring = counts["state_to_count"].get(bitstring_of_k.bitstring, 0)
        probability_sum_terms.append(abs(counts_of_expected_bitstring / counts["total_count"]))

    m = len(results_for_different_k)
    if m <= 1:
        raise ValueError("There should be at least two different basis states per instance.")
    process_fidelity = (
        1
        / (m**2 - m)
        * (
            sum(
                [
                    np.sqrt(scaled_counts_of_expected_bitstring)
                    for scaled_counts_of_expected_bitstring in probability_sum_terms
                ]
            )
            ** 2
            - sum(probability_sum_terms)
        )
    )
    return process_fidelity


def convert_k_to_bitstring(k: int, qubit_map: dict[Qubit, int]) -> PauliBasisState[Qubit, Z]:
    """Convert the index of the basis state k to a corresponding bitstring. The conversion uses
    binary representation, and the resulting bitstring is padded with leading zeros to match
    the number of qubits.

    :param k: Index of the basis state k.
    :param qubit_map: Map from ParityOS qubits to indices in the bitstring. e.g. {qubit_a: 0,
        qubit_b: 1} means that qubit_a appears first in a two-character bitstring.

    :returns: Bitstring which corresponds to the basis state index k, padded with leading zeros to
        match the number of qubits.
    """
    bitstring = f"{k:0{len(qubit_map)}b}"[::-1]
    return PauliBasisState(bitstring, ordered_qubits=sorted(qubit_map, key=lambda q: qubit_map[q]))


def calculate_process_fidelity(
    experiments_dataframe: DataFrame, bootstrap_sample_size: int = 20, n_bootstrap_samples: int = 20
) -> DataFrame:
    """
    Calculate process fidelity for quantum experiments using bootstrap sampling.

    :param experiments_dataframe: DataFrame containing experimental results with columns including
        'qft_method', 'number_of_qubits', 'counts', 'basis_state_index', and 'exporter_result'
    :param bootstrap_sample_size: Number of samples to draw in each bootstrap iteration
    :param n_bootstrap_samples: Number of bootstrap samples to generate for each experiment
        configuration

    :return: DataFrame with columns 'number_of_qubits', 'qft_variant', and 'process_fidelity'
    """
    analysis_rows = []

    for (qft_method, n_qubits), subdf in experiments_dataframe.groupby(
        ["qft_method", "number_of_qubits"]
    ):
        if subdf["counts"].isnull().any():
            for _ in range(n_bootstrap_samples):
                analysis_rows.append(
                    {
                        "number_of_qubits": n_qubits,
                        "qft_variant": qft_method,
                        "process_fidelity": None,
                    }
                )
            continue

        for _ in range(n_bootstrap_samples):
            results_for_different_k = []

            for _, row in subdf.sample(n=bootstrap_sample_size, replace=True).iterrows():
                results_for_different_k.append(
                    (
                        convert_k_to_bitstring(
                            row["basis_state_index"],
                            row["exporter_result"]["qubit_map"],
                        ),
                        row["counts"],
                    )
                )

            process_fidelity = calculate_process_fidelity_for_different_k(results_for_different_k)

            analysis_rows.append(
                {
                    "number_of_qubits": n_qubits,
                    "qft_variant": qft_method,
                    "process_fidelity": process_fidelity,
                }
            )

    analysis_dataframe = pd.DataFrame(analysis_rows)

    return analysis_dataframe


if __name__ == "__main__":
    file_path = "circuit_data_fo.json.gz"
    experiment_file = os.path.expanduser(file_path)
    # 1) Decompress and load file
    experiments_df = process_qft_experiments(experiment_file)
    # 2) Calculate process fidelity based on results
    analysis_dataframe = calculate_process_fidelity(experiments_df)
    # 3) Plot results
    ax = sns.lineplot(
        data=analysis_dataframe,
        x="number_of_qubits",
        y="process_fidelity",
        hue="qft_variant",
        marker="o",
        err_style="band",
    )
    ax.legend()
    ax.set_ylabel("QFT Process Fidelity")
    ax.set_xlabel("System size (Number of Qubits)")
    ax.set_yscale("log")
    plt.title("Parity Twine QFT w. QCTRL FireOpal performance management")
    plt.show()
    print(analysis_dataframe)
