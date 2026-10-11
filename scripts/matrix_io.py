"""Shared CSV parsing and validation; this module does not alter matrix values."""

from pathlib import Path
import warnings

import numpy as np


def load_matrix(path):
    """Read a headerless comma-separated numeric matrix, preserving two axes."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        matrix = np.loadtxt(Path(path), delimiter=",", dtype=np.float64, ndmin=2)
    if matrix.size == 0:
        raise ValueError("input matrix is empty")
    return matrix


def validate_matrix(matrix):
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"matrix must be square; got shape {matrix.shape}")
    if not np.isfinite(matrix).all():
        raise ValueError("matrix contains non-finite values (NaN or infinity)")
    if (matrix < 0).any():
        raise ValueError("matrix contains negative values")


def open_new_csv(path):
    """Exclusive creation also protects against races between check and write."""
    return Path(path).open("x", encoding="utf-8", newline="")
