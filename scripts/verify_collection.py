#!/usr/bin/env python3
"""Read-only verification of the BP407-D001 through BP407-D008 collection.

An external manifest supplied by an authorized user is required. This repository
does not distribute a manifest or participant data. Only files explicitly listed
in the supplied manifest are opened. Matrix contents and
shape can be inspected with the separate matrix utilities; this command checks
manifest integrity, safe paths, file availability, and optional SHA-256 hashes.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys


DATASET_IDS = frozenset(f"BP407-D{number:03d}" for number in range(1, 9))
REQUIRED_COLUMNS = (
    "dataset_id", "project_subject_id", "atlas", "rows", "columns", "path", "sha256"
)


@dataclass
class VerificationSummary:
    manifest_rows: int = 0
    checked_files: int = 0
    hash_checks: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _relative_path(value: str, dataset_id: str) -> PurePosixPath:
    """Require portable, canonical paths rooted in the declared dataset."""
    windows_path = PureWindowsPath(value)
    parts = value.split("/")
    if (
        not value
        or "\\" in value
        or windows_path.drive
        or windows_path.is_absolute()
        or any(part in ("", ".", "..") for part in parts)
        or "\x00" in value
    ):
        raise ValueError("path must be a relative POSIX path without '.', '..', or a drive")
    path = PurePosixPath(value)
    if path.is_absolute() or len(path.parts) < 2 or path.parts[0] != dataset_id:
        raise ValueError("path must start with its dataset_id directory")
    if path.suffix.lower() != ".csv":
        raise ValueError("path must refer to a matrix CSV file")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_collection(
    data_root: Path,
    manifest_path: Path,
    *,
    skip_hash: bool = False,
) -> VerificationSummary:
    """Verify an explicitly supplied manifest without changing or scanning data."""
    summary = VerificationSummary()
    try:
        root = Path(data_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("data root is not a directory")
    except (OSError, RuntimeError, ValueError) as exc:
        summary.errors.append(f"Invalid data root: {exc}")
        return summary

    seen_paths: dict[str, int] = {}
    seen_ids: dict[tuple[str, str, str], int] = {}
    seen_resolved: dict[Path, int] = {}
    try:
        with Path(manifest_path).open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t", strict=True)
            headers = reader.fieldnames or []
            missing = set(REQUIRED_COLUMNS).difference(headers)
            if missing:
                summary.errors.append("Manifest is missing columns: " + ", ".join(sorted(missing)))
            if len(headers) != len(set(headers)) or any(not name for name in headers):
                summary.errors.append("Manifest has duplicate or empty column names")
            if summary.errors:
                return summary
            for record in reader:
                summary.manifest_rows += 1
                line = reader.line_num
                prefix = f"Manifest line {line}: "
                errors_before = len(summary.errors)
                if None in record or any(record.get(name) is None for name in REQUIRED_COLUMNS):
                    summary.errors.append(prefix + "row has the wrong number of columns")
                    continue
                values = {name: record[name] for name in REQUIRED_COLUMNS}
                if any(not value or value != value.strip() for value in values.values()):
                    summary.errors.append(prefix + "required values must be nonempty and have no surrounding whitespace")
                    continue
                dataset_id = values["dataset_id"]
                if dataset_id not in DATASET_IDS:
                    summary.errors.append(prefix + f"unsupported dataset_id {dataset_id!r}")
                matrix_id = (dataset_id, values["project_subject_id"], values["atlas"])
                if matrix_id in seen_ids:
                    summary.errors.append(prefix + f"duplicate matrix ID, first seen on line {seen_ids[matrix_id]}")
                else:
                    seen_ids[matrix_id] = line
                relative = None
                try:
                    relative = _relative_path(values["path"], dataset_id)
                except ValueError as exc:
                    summary.errors.append(prefix + str(exc))
                path_key = values["path"]
                if path_key in seen_paths:
                    summary.errors.append(prefix + f"duplicate path, first seen on line {seen_paths[path_key]}")
                else:
                    seen_paths[path_key] = line
                for name in ("rows", "columns"):
                    if not re.fullmatch(r"[1-9][0-9]*", values[name]):
                        summary.errors.append(prefix + f"{name} must be a positive integer")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", values["sha256"]):
                    summary.errors.append(prefix + "sha256 must contain exactly 64 hexadecimal characters")
                if len(summary.errors) != errors_before or relative is None:
                    continue
                try:
                    path = root.joinpath(*relative.parts).resolve(strict=True)
                    if not path.is_relative_to(root):
                        raise ValueError("resolved path escapes data root (possibly through a symlink)")
                    if not path.is_file():
                        raise ValueError("listed path is not a regular file")
                    if path in seen_resolved:
                        raise ValueError(f"duplicate resolved path, first seen on line {seen_resolved[path]}")
                    seen_resolved[path] = line
                    summary.checked_files += 1
                    if not skip_hash:
                        actual = _sha256(path)
                        summary.hash_checks += 1
                        if actual != values["sha256"].lower():
                            summary.errors.append(prefix + f"SHA256 mismatch for {relative}: expected {values['sha256']}, got {actual}")
                except (OSError, RuntimeError, ValueError) as exc:
                    summary.errors.append(prefix + f"{relative}: {exc}")
    except (OSError, UnicodeError, csv.Error) as exc:
        summary.errors.append(f"Cannot read manifest {manifest_path}: {exc}")
    if summary.manifest_rows == 0 and not summary.errors:
        summary.errors.append("Manifest contains no matrix records")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True,
                        help="Parent directory containing BP407-D001 through BP407-D008")
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Required external TSV manifest obtained through authorized access")
    parser.add_argument("--skip-hash", action="store_true",
                        help="Check manifest and file paths without reading file contents")
    args = parser.parse_args(argv)
    summary = verify_collection(args.data_root, args.manifest, skip_hash=args.skip_hash)
    for error in summary.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    status = "PASS" if summary.ok else "FAIL"
    print(f"{status}: {summary.manifest_rows} manifest rows; {summary.checked_files} files checked; "
          f"{summary.hash_checks} SHA256 checks; {len(summary.errors)} errors")
    if args.skip_hash:
        print("SHA256 verification skipped; file contents and matrix shapes were not checked.")
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
