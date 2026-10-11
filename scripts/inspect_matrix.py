"""Inspect a BrainProject407 regional matrix without changing the source."""

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

from matrix_io import load_matrix, open_new_csv, validate_matrix


def summarize(matrix, input_path):
    square = matrix.shape[0] == matrix.shape[1]
    finite = np.isfinite(matrix)
    result = {
        "input": str(input_path),
        "shape": list(matrix.shape),
        "is_square": square,
        "nonfinite_count": int((~finite).sum()),
        "negative_count": int((matrix < 0).sum()),
        "valid_nonnegative_square": bool(square and finite.all() and not (matrix < 0).any()),
        "diagonal_meaning": "T1w gray-matter probability sum proxy; not self-connections",
    }
    if square:
        diagonal = np.diag(matrix)
        offdiag = matrix[~np.eye(matrix.shape[0], dtype=bool)]
        result["diagonal"] = {
            "count": int(diagonal.size),
            "finite_count": int(np.isfinite(diagonal).sum()),
            "min": float(diagonal.min()) if np.isfinite(diagonal).all() else None,
            "max": float(diagonal.max()) if np.isfinite(diagonal).all() else None,
        }
        result["off_diagonal"] = {
            "entry_count": int(offdiag.size),
            "positive_entry_count": int((offdiag > 0).sum()),
            "zero_entry_count": int((offdiag == 0).sum()),
            "min": float(offdiag.min()) if offdiag.size and np.isfinite(offdiag).all() else None,
            "max": float(offdiag.max()) if offdiag.size and np.isfinite(offdiag).all() else None,
        }
        if np.isfinite(offdiag).all():
            upper = np.triu_indices(matrix.shape[0], k=1)
            with np.errstate(over="ignore"):
                differences = np.abs(matrix[upper] - matrix.T[upper])
            max_difference = float(differences.max()) if differences.size else 0.0
            result["off_diagonal"]["exactly_symmetric"] = bool((differences == 0).all())
            result["off_diagonal"]["max_abs_symmetry_difference"] = (
                max_difference if np.isfinite(max_difference) else "overflow"
            )
        else:
            result["off_diagonal"]["exactly_symmetric"] = None
            result["off_diagonal"]["max_abs_symmetry_difference"] = None
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path, help="Headerless numeric CSV matrix")
    parser.add_argument("--diagonal-output", type=Path,
                        help="Create a new CSV of node_index,gray_matter_probability_sum_proxy")
    args = parser.parse_args(argv)
    try:
        matrix = load_matrix(args.matrix)
        summary = summarize(matrix, args.matrix)
        print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
        validate_matrix(matrix)
        if args.diagonal_output:
            with open_new_csv(args.diagonal_output) as stream:
                writer = csv.writer(stream)
                writer.writerow(["node_index", "gray_matter_probability_sum_proxy"])
                writer.writerows((i + 1, format(value, ".17g"))
                                 for i, value in enumerate(np.diag(matrix)))
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
