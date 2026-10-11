"""Synthetic regression cases; no subject data are needed."""

import contextlib
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_matrix import main as inspect_main, summarize
from matrix_io import load_matrix
from matrix_to_edges import export_edges, main as edges_main


class MatrixToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "edges.csv"
        self.symmetric = np.array([[99, 2, 0], [2, 88, 3.5], [0, 3.5, 77.]])

    def rows(self, path=None):
        with (path or self.output).open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def test_undirected_excludes_diagonal_and_zero_preserves_weights(self):
        self.assertEqual(export_edges(self.symmetric, self.output, "undirected"), 2)
        self.assertEqual(self.rows(), [
            {"source_node": "1", "target_node": "2", "weight": "2"},
            {"source_node": "2", "target_node": "3", "weight": "3.5"},
        ])

    def test_directed_preserves_asymmetry(self):
        asymmetric = np.array([[99., 2], [7, 88]])
        self.assertEqual(export_edges(asymmetric, self.output, "directed"), 2)
        self.assertEqual([row["weight"] for row in self.rows()], ["2", "7"])

    def test_undirected_rejects_asymmetry_before_creating_output(self):
        with self.assertRaisesRegex(ValueError, "requires symmetry"):
            export_edges(np.array([[9., 2], [3, 8]]), self.output, "undirected")
        self.assertFalse(self.output.exists())

    def test_explicit_tolerance_preserves_upper_triangle_without_averaging(self):
        export_edges(np.array([[9., 2], [2.0001, 8]]), self.output,
                     "undirected", symmetry_atol=.001)
        self.assertEqual(self.rows()[0]["weight"], "2")

    def test_nonfinite_and_negative_rejected_even_on_diagonal(self):
        for value in (float("nan"), float("inf"), -1.):
            for row, column in ((0, 1), (0, 0)):
                with self.subTest(value=value, row=row, column=column):
                    matrix = self.symmetric.copy()
                    matrix[row, column] = value
                    with self.assertRaises(ValueError):
                        export_edges(matrix, self.output, "directed")
                    self.assertFalse(self.output.exists())

    def test_nonsquare_and_bad_tolerances_rejected(self):
        with self.assertRaisesRegex(ValueError, "square"):
            export_edges(np.ones((2, 3)), self.output, "directed")
        for tolerance in (-1., float("nan"), float("inf")):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                export_edges(self.symmetric, self.output, "undirected", symmetry_atol=tolerance)
        self.assertFalse(self.output.exists())

    def test_include_zero_still_excludes_diagonal(self):
        self.assertEqual(export_edges(self.symmetric, self.output, "directed", include_zero=True), 6)
        self.assertTrue(all(row["source_node"] != row["target_node"] for row in self.rows()))
        self.assertEqual(sum(float(row["weight"]) == 0 for row in self.rows()), 2)

    def test_refuses_existing_output(self):
        self.output.write_text("keep this file", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_edges(self.symmetric, self.output, "undirected")
        self.assertEqual(self.output.read_text(encoding="utf-8"), "keep this file")

    def test_inspect_summary_and_diagonal_csv(self):
        source = self.root / "matrix.csv"
        np.savetxt(source, self.symmetric, delimiter=",")
        diagonal = self.root / "diagonal.csv"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(inspect_main([str(source), "--diagonal-output", str(diagonal)]), 0)
        summary = json.loads(stdout.getvalue())
        self.assertTrue(summary["valid_nonnegative_square"])
        self.assertEqual(summary["off_diagonal"]["max_abs_symmetry_difference"], 0)
        self.assertEqual([float(row["gray_matter_probability_sum_proxy"]) for row in self.rows(diagonal)],
                         [99, 88, 77])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(inspect_main([str(source), "--diagonal-output", str(diagonal)]), 2)
        self.assertEqual(len(self.rows(diagonal)), 3)

    def test_inspect_nonfinite_is_json_safe_and_blocks_diagonal_export(self):
        source = self.root / "invalid.csv"
        source.write_text("1,nan\n2,3\n", encoding="utf-8")
        diagonal = self.root / "diagonal.csv"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(inspect_main([str(source), "--diagonal-output", str(diagonal)]), 2)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["nonfinite_count"], 1)
        self.assertIsNone(summary["off_diagonal"]["exactly_symmetric"])
        self.assertFalse(diagonal.exists())

    def test_csv_empty_malformed_and_singleton(self):
        source = self.root / "input.csv"
        source.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "empty"):
            load_matrix(source)
        source.write_text("1,2\n3\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_matrix(source)
        source.write_text("42\n", encoding="utf-8")
        matrix = load_matrix(source)
        self.assertEqual(matrix.shape, (1, 1))
        self.assertEqual(export_edges(matrix, self.output, "undirected"), 0)
        self.assertEqual(summarize(matrix, source)["off_diagonal"]["entry_count"], 0)

    def test_direction_is_required_on_command_line(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            edges_main(["unused.csv", "unused-output.csv"])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
