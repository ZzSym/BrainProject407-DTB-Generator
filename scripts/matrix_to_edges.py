"""Export a regional edge table, not a DTB neuron-level connection table."""

import argparse
import csv
import math
from pathlib import Path
import sys

import numpy as np

from matrix_io import load_matrix, open_new_csv, validate_matrix


def export_edges(matrix, output, direction, include_zero=False, symmetry_atol=0.0):
    """Validate everything before exclusively creating the output CSV."""
    validate_matrix(matrix)
    if direction not in ("directed", "undirected"):
        raise ValueError("direction must be directed or undirected")
    if not math.isfinite(symmetry_atol) or symmetry_atol < 0:
        raise ValueError("symmetry-atol must be finite and nonnegative")
    n_nodes = matrix.shape[0]
    if direction == "undirected":
        rows, columns = np.triu_indices(n_nodes, k=1)
        with np.errstate(over="ignore"):
            difference = np.abs(matrix[rows, columns] - matrix[columns, rows])
        if np.any(difference > symmetry_atol):
            raise ValueError(
                "undirected export requires symmetry: "
                f"max absolute off-diagonal difference={difference.max():.17g}, "
                f"allowed={symmetry_atol:.17g}; no averaging was performed"
            )
    else:
        rows, columns = np.where(~np.eye(n_nodes, dtype=bool))
    values = matrix[rows, columns]
    if not include_zero:
        keep = values > 0
        rows, columns, values = rows[keep], columns[keep], values[keep]
    with open_new_csv(output) as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_node", "target_node", "weight"])
        writer.writerows((int(i) + 1, int(j) + 1, format(value, ".17g"))
                         for i, j, value in zip(rows, columns, values))
    return len(values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path, help="Headerless numeric CSV matrix")
    parser.add_argument("output", type=Path, help="New regional edge CSV; must not exist")
    parser.add_argument("--direction", choices=["directed", "undirected"], required=True,
                        help="Explicitly choose whether reverse directions are separate edges")
    parser.add_argument("--include-zero", action="store_true",
                        help="Also include zero-weight off-diagonal pairs (default: omit zeros)")
    parser.add_argument("--symmetry-atol", type=float, default=0.0,
                        help="Undirected absolute symmetry tolerance; default 0 (exact)")
    args = parser.parse_args(argv)
    try:
        if args.direction == "directed" and args.symmetry_atol != 0:
            raise ValueError("symmetry-atol applies only to undirected export")
        matrix = load_matrix(args.matrix)
        count = export_edges(matrix, args.output, args.direction,
                             args.include_zero, args.symmetry_atol)
        print(f"Created {args.output}: {count} regional edges; 1-based nodes; diagonal excluded.")
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
