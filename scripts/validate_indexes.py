#!/usr/bin/env python3
"""Validate the JSONL dataset indexes against their JSON Schemas.

Validates writers.jsonl + entries.jsonl, enforces referential integrity
between them, checks Hebrew-letter codepoint/name/form consistency, pins
the upstream repo URL, and re-verifies image file checksums and sizes on
disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError as exc:  # pragma: no cover - exercised when deps are absent.
    raise SystemExit(
        "Missing dependency: jsonschema. Install development dependencies with "
        "`python3 -m pip install -r requirements-dev.txt`."
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
WRITERS_PATH = REPO_ROOT / "data" / "index" / "writers.jsonl"
ENTRIES_PATH = REPO_ROOT / "data" / "index" / "entries.jsonl"
WRITER_SCHEMA_PATH = REPO_ROOT / "schemas" / "writer.schema.json"
ENTRY_SCHEMA_PATH = REPO_ROOT / "schemas" / "entry.schema.json"

UPSTREAM_REPO_URL = "https://github.com/HeOCR/public-domain-hand-written-hebrew-scans"

# Canonical Hebrew letter table. Mirrors docs/letters.md and the
# `letter.name` enum in schemas/entry.schema.json. The validator uses
# this table to enforce cross-field consistency on the `letter` block.
LETTER_TABLE: list[tuple[str, str, str, str]] = [
    ("U+05D0", "א", "alef", "regular"),
    ("U+05D1", "ב", "bet", "regular"),
    ("U+05D2", "ג", "gimel", "regular"),
    ("U+05D3", "ד", "dalet", "regular"),
    ("U+05D4", "ה", "he", "regular"),
    ("U+05D5", "ו", "vav", "regular"),
    ("U+05D6", "ז", "zayin", "regular"),
    ("U+05D7", "ח", "het", "regular"),
    ("U+05D8", "ט", "tet", "regular"),
    ("U+05D9", "י", "yod", "regular"),
    ("U+05DA", "ך", "kaf_final", "final"),
    ("U+05DB", "כ", "kaf", "regular"),
    ("U+05DC", "ל", "lamed", "regular"),
    ("U+05DD", "ם", "mem_final", "final"),
    ("U+05DE", "מ", "mem", "regular"),
    ("U+05DF", "ן", "nun_final", "final"),
    ("U+05E0", "נ", "nun", "regular"),
    ("U+05E1", "ס", "samekh", "regular"),
    ("U+05E2", "ע", "ayin", "regular"),
    ("U+05E3", "ף", "pe_final", "final"),
    ("U+05E4", "פ", "pe", "regular"),
    ("U+05E5", "ץ", "tsadi_final", "final"),
    ("U+05E6", "צ", "tsadi", "regular"),
    ("U+05E7", "ק", "qof", "regular"),
    ("U+05E8", "ר", "resh", "regular"),
    ("U+05E9", "ש", "shin", "regular"),
    ("U+05EA", "ת", "tav", "regular"),
]
LETTER_BY_NAME: dict[str, tuple[str, str, str, str]] = {row[2]: row for row in LETTER_TABLE}

# Permitted file extensions per `image.mime_type`. The first entry is the
# preferred extension; subsequent ones are accepted aliases.
MIME_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/webp": (".webp",),
    "image/tiff": (".tif", ".tiff"),
}


def load_schema(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"{path}: file does not exist")
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON schema: {exc}") from exc
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise SystemExit(f"{path}: invalid JSON schema: {exc.message}") from exc
    return schema


def load_jsonl(
    path: Path,
    validator: Draft202012Validator,
    id_key: str,
) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"{path}: file does not exist")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"{path}:{line_number}: row must be a JSON object")

            errors = sorted(validator.iter_errors(row), key=lambda error: list(error.path))
            if errors:
                first = errors[0]
                location = ".".join(str(part) for part in first.path) or "<root>"
                raise SystemExit(f"{path}:{line_number}: {location}: {first.message}")

            row_id = row.get(id_key)
            if not isinstance(row_id, str) or not row_id:
                raise SystemExit(f"{path}:{line_number}: {id_key} must be a non-empty string")
            if row_id in seen:
                raise SystemExit(f"{path}:{line_number}: duplicate {id_key}: {row_id}")
            seen.add(row_id)
            rows.append(row)
    return rows


def _check_letter_consistency(entry_id: str, letter: dict[str, Any]) -> None:
    name = letter["name"]
    canonical = LETTER_BY_NAME.get(name)
    if canonical is None:
        # The schema's enum should have caught this already; defensive.
        raise SystemExit(f"{entry_id}: unknown letter.name: {name}")
    expected_codepoint, expected_char, _, expected_form = canonical
    if letter["codepoint"] != expected_codepoint:
        raise SystemExit(
            f"{entry_id}: letter.codepoint mismatch for {name}: "
            f"expected {expected_codepoint}, got {letter['codepoint']}"
        )
    if letter["unicode_char"] != expected_char:
        raise SystemExit(
            f"{entry_id}: letter.unicode_char mismatch for {name}: "
            f"expected {expected_char!r}, got {letter['unicode_char']!r}"
        )
    if letter["form"] != expected_form:
        raise SystemExit(
            f"{entry_id}: letter.form mismatch for {name}: "
            f"expected {expected_form}, got {letter['form']}"
        )


def _check_upstream(entry_id: str, upstream: dict[str, Any]) -> None:
    if upstream["repo"] != UPSTREAM_REPO_URL:
        raise SystemExit(
            f"{entry_id}: upstream.repo must be {UPSTREAM_REPO_URL}, "
            f"got {upstream['repo']}"
        )
    upstream_entry_id = upstream["entry_id"]
    upstream_source_id = upstream["source_id"]
    if not upstream_entry_id.startswith(f"{upstream_source_id}__p"):
        raise SystemExit(
            f"{entry_id}: upstream.entry_id ({upstream_entry_id}) must start with "
            f"upstream.source_id ({upstream_source_id}) plus '__p'"
        )


def _check_local_path(
    entry_id: str,
    writer_id: str,
    letter_name: str,
    image: dict[str, Any],
) -> None:
    local_path = image["local_path"]
    local_path_obj = Path(local_path)
    if local_path_obj.is_absolute() or ".." in local_path_obj.parts:
        raise SystemExit(
            f"{entry_id}: image.local_path must be repo-relative without '..': {local_path}"
        )

    expected_prefix = f"data/letters/{writer_id}/{letter_name}/"
    if not local_path.startswith(expected_prefix):
        raise SystemExit(
            f"{entry_id}: image.local_path must start with {expected_prefix!r}, "
            f"got {local_path!r}"
        )

    suffix = local_path_obj.suffix.lower()
    expected_exts = MIME_EXTENSIONS.get(image["mime_type"], ())
    if suffix not in expected_exts:
        raise SystemExit(
            f"{entry_id}: image.local_path extension {suffix!r} does not match "
            f"image.mime_type {image['mime_type']!r} (allowed: {list(expected_exts)})"
        )

    expected_stem = f"data/letters/{writer_id}/{letter_name}/{entry_id}"
    actual_stem = str(local_path_obj.with_suffix(""))
    if actual_stem != expected_stem:
        raise SystemExit(
            f"{entry_id}: image.local_path stem must equal {expected_stem!r}, "
            f"got {actual_stem!r}"
        )


def _check_attribution_fields(entry_id: str, rights: dict[str, Any]) -> None:
    if rights.get("attribution_required") is not True:
        return
    attribution_text = rights.get("attribution_text")
    if not isinstance(attribution_text, str) or not attribution_text.strip():
        raise SystemExit(
            f"{entry_id}: rights.attribution_required is true but "
            f"rights.attribution_text is null, blank, or whitespace-only"
        )
    attribution_url = rights.get("attribution_url")
    if not isinstance(attribution_url, str) or not attribution_url.strip():
        raise SystemExit(
            f"{entry_id}: rights.attribution_required is true but "
            f"rights.attribution_url is null, blank, or whitespace-only"
        )


def validate_entries(entries: list[dict[str, Any]], writer_ids: set[str]) -> None:
    seen_entry_ids: set[str] = set()
    for entry in entries:
        entry_id = entry["entry_id"]
        writer_id = entry["writer_id"]
        letter = entry["letter"]

        if writer_id not in writer_ids:
            raise SystemExit(f"{entry_id}: unknown writer_id: {writer_id}")

        expected_prefix = f"{writer_id}__{letter['name']}__v"
        if not entry_id.startswith(expected_prefix):
            raise SystemExit(
                f"{entry_id}: entry_id must start with {expected_prefix!r}"
            )

        if entry_id in seen_entry_ids:
            raise SystemExit(f"{entry_id}: duplicate entry_id")
        seen_entry_ids.add(entry_id)

        _check_letter_consistency(entry_id, letter)
        _check_upstream(entry_id, entry["upstream"])
        _check_local_path(entry_id, writer_id, letter["name"], entry["image"])
        _check_attribution_fields(entry_id, entry["rights"])


def _sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def validate_entry_files(entries: list[dict[str, Any]], repo_root: Path) -> int:
    verified = 0
    for entry in entries:
        entry_id = entry["entry_id"]
        image = entry["image"]
        local_path = image["local_path"]
        absolute = repo_root / local_path
        if not absolute.is_file():
            raise SystemExit(f"{entry_id}: file does not exist: {local_path}")

        actual_bytes = absolute.stat().st_size
        if actual_bytes != image["bytes"]:
            raise SystemExit(
                f"{entry_id}: byte size mismatch for {local_path}: "
                f"expected {image['bytes']}, got {actual_bytes}"
            )

        actual_sha = _sha256_file(absolute)
        if actual_sha != image["sha256"]:
            raise SystemExit(
                f"{entry_id}: sha256 mismatch for {local_path}: "
                f"expected {image['sha256']}, got {actual_sha}"
            )
        verified += 1
    return verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--writers", type=Path, default=WRITERS_PATH)
    parser.add_argument("--entries", type=Path, default=ENTRIES_PATH)
    parser.add_argument("--writer-schema", type=Path, default=WRITER_SCHEMA_PATH)
    parser.add_argument("--entry-schema", type=Path, default=ENTRY_SCHEMA_PATH)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root used to resolve image.local_path during file-integrity checks. Defaults to this repository.",
    )
    args = parser.parse_args()

    writer_validator = Draft202012Validator(
        load_schema(args.writer_schema), format_checker=FormatChecker()
    )
    entry_validator = Draft202012Validator(
        load_schema(args.entry_schema), format_checker=FormatChecker()
    )

    writers = load_jsonl(args.writers, writer_validator, "writer_id")
    entries = load_jsonl(args.entries, entry_validator, "entry_id")
    validate_entries(entries, {writer["writer_id"] for writer in writers})
    verified = validate_entry_files(entries, args.repo_root)

    print(
        f"ok: {len(writers)} writers, {len(entries)} entries, "
        f"{verified} files verified"
    )


if __name__ == "__main__":
    main()
