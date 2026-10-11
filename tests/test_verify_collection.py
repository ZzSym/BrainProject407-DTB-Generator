"""Generate entirely synthetic fixtures at runtime; never load participant data."""

import csv
import hashlib
import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_collection.py"
SPEC = importlib.util.spec_from_file_location("verify_collection", SCRIPT)
verify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify
SPEC.loader.exec_module(verify)


class VerifyCollectionTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures in the workspace so Windows sandbox path resolution is
        # permitted; TemporaryDirectory removes them after each test.
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "collection"
        self.matrix = self.root / "BP407-D001" / "matrix.csv"
        self.matrix.parent.mkdir(parents=True)
        self.content = b"0,1\n1,0\n"
        self.matrix.write_bytes(self.content)
        self.manifest = self.base / "matrices.tsv"
        self.record = {
            "dataset_id": "BP407-D001", "project_subject_id": "subject-1",
            "atlas": "test-atlas", "rows": "2", "columns": "2",
            "path": "BP407-D001/matrix.csv",
            "sha256": hashlib.sha256(self.content).hexdigest(),
        }

    def write_manifest(self, records=None):
        with self.manifest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=verify.REQUIRED_COLUMNS, delimiter="\t")
            writer.writeheader()
            writer.writerows(records if records is not None else [self.record])

    def check(self, records=None, **kwargs):
        self.write_manifest(records)
        return verify.verify_collection(self.root, self.manifest, **kwargs)

    def test_valid_file_and_unlisted_files_are_untouched(self):
        (self.matrix.parent / "unlisted.npz").write_bytes(b"not a matrix")
        result = self.check()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual((result.manifest_rows, result.checked_files, result.hash_checks), (1, 1, 1))
        self.assertEqual(self.matrix.read_bytes(), self.content)

    def test_hash_mismatch(self):
        self.matrix.write_bytes(b"changed")
        result = self.check()
        self.assertFalse(result.ok)
        self.assertIn("SHA256 mismatch", "\n".join(result.errors))

    def test_skip_hash_does_not_read_matrix(self):
        self.matrix.write_bytes(b"changed")
        with patch.object(verify, "_sha256", side_effect=AssertionError("must not read contents")):
            result = self.check(skip_hash=True)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.hash_checks, 0)

    def test_missing_file(self):
        self.matrix.unlink()
        result = self.check(skip_hash=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.checked_files, 0)

    def test_unsafe_and_non_csv_paths(self):
        for path in (
            "../outside.csv", "BP407-D001/../../outside.csv", "/tmp/outside.csv",
            "C:/outside.csv", "C:outside.csv", "\\\\server\\share\\matrix.csv",
            "BP407-D001\\matrix.csv", "BP407-D001/./matrix.csv",
            "BP407-D001//matrix.csv", "BP407-D002/matrix.csv", "BP407-D001/data.npz",
        ):
            with self.subTest(path=path):
                result = self.check([{**self.record, "path": path}])
                self.assertFalse(result.ok)
                self.assertEqual(result.checked_files, 0)

    def test_symlink_escape(self):
        external = self.base / "outside.csv"
        external.write_bytes(self.content)
        link = self.matrix.parent / "link.csv"
        try:
            link.symlink_to(external)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlinks unavailable on this host: {exc}")
        result = self.check([{**self.record, "path": "BP407-D001/link.csv"}])
        self.assertFalse(result.ok)
        self.assertIn("escapes data root", "\n".join(result.errors))

    def test_resolved_path_escape_without_symlink_privileges(self):
        external = self.base / "outside.csv"
        external.write_bytes(self.content)
        original_resolve = Path.resolve

        def resolve(path, strict=False):
            if path == self.matrix:
                return external
            return original_resolve(path, strict=strict)

        with patch.object(Path, "resolve", resolve):
            result = self.check()
        self.assertFalse(result.ok)
        self.assertEqual(result.hash_checks, 0)
        self.assertIn("escapes data root", "\n".join(result.errors))

    def test_duplicate_path(self):
        second = {**self.record, "project_subject_id": "subject-2"}
        result = self.check([self.record, second])
        self.assertFalse(result.ok)
        self.assertIn("duplicate path", "\n".join(result.errors))

    def test_duplicate_matrix_id(self):
        second = {**self.record, "path": "BP407-D001/other.csv"}
        result = self.check([self.record, second])
        self.assertFalse(result.ok)
        self.assertIn("duplicate matrix ID", "\n".join(result.errors))

    def test_dataset_outside_delivery(self):
        result = self.check([{**self.record, "dataset_id": "BP407-D009",
                              "path": "BP407-D009/matrix.csv"}])
        self.assertFalse(result.ok)
        self.assertIn("unsupported dataset_id", "\n".join(result.errors))

    def test_invalid_dimensions_and_hash(self):
        for key, value in (("rows", "0"), ("columns", "2.5"), ("sha256", "bad")):
            with self.subTest(key=key):
                result = self.check([{**self.record, key: value}])
                self.assertFalse(result.ok)
                self.assertEqual(result.checked_files, 0)

    def test_empty_manifest_fails(self):
        result = self.check([])
        self.assertFalse(result.ok)
        self.assertIn("no matrix records", "\n".join(result.errors))

    def test_api_requires_explicit_manifest(self):
        manifest = inspect.signature(verify.verify_collection).parameters["manifest_path"]
        self.assertIs(manifest.default, inspect.Parameter.empty)
        self.assertFalse(hasattr(verify, "DEFAULT_MANIFEST"))
        with self.assertRaises(TypeError):
            verify.verify_collection(self.root)

    def test_cli_requires_explicit_manifest(self):
        command = [sys.executable, str(SCRIPT), "--data-root", str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--manifest", result.stderr)
        self.assertIn("required", result.stderr)

    def test_cli_exit_codes_and_summary(self):
        self.write_manifest()
        command = [sys.executable, str(SCRIPT), "--data-root", str(self.root),
                   "--manifest", str(self.manifest)]
        passed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertIn("PASS: 1 manifest rows; 1 files checked; 1 SHA256 checks; 0 errors", passed.stdout)
        self.matrix.unlink()
        failed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("FAIL:", failed.stdout)
        self.assertIn("ERROR:", failed.stderr)


if __name__ == "__main__":
    unittest.main()
