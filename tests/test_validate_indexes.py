from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_indexes.py"
WRITERS = REPO_ROOT / "data" / "index" / "writers.jsonl"
ENTRIES = REPO_ROOT / "data" / "index" / "entries.jsonl"


def run_validator(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def writer_fixture() -> dict:
    return {
        "writer_id": "fixture_writer",
        "status": "verified",
        "display_name": "Fixture Writer",
        "also_known_as": [],
        "description": "Synthetic writer used only by the test suite.",
        "dates": {
            "birth_year": 1890,
            "birth_precision": "exact",
            "death_year": 1950,
            "death_precision": "exact",
        },
        "languages_written": ["he"],
        "scripts_written": ["Hebr"],
        "period": {
            "start": "1920",
            "end": "1949",
            "precision": "year",
        },
        "references": [
            {
                "kind": "repo_note",
                "citation": "tests/test_validate_indexes.py::writer_fixture",
                "quote": None,
                "url": None,
            }
        ],
        "ingest": {
            "agent_notes": "fixture",
            "blocked_reason": None,
        },
    }


def _hash_bytes(data: bytes) -> tuple[str, int]:
    return hashlib.sha256(data).hexdigest(), len(data)


@pytest.fixture
def entry_fixture(tmp_path: Path) -> dict:
    # Write a tiny placeholder PNG (1x1 pixel) so the file-integrity
    # check has something real to hash. The validator only cares about
    # size and sha256; the bytes do not need to decode as a valid PNG.
    image_dir = tmp_path / "data" / "letters" / "fixture_writer" / "alef"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "fixture_writer__alef__v0001.png"
    image_bytes = b"\x89PNG\r\n\x1a\nfixture-test-bytes"
    image_path.write_bytes(image_bytes)
    sha, size = _hash_bytes(image_bytes)

    return {
        "entry_id": "fixture_writer__alef__v0001",
        "writer_id": "fixture_writer",
        "letter": {
            "codepoint": "U+05D0",
            "unicode_char": "א",
            "name": "alef",
            "form": "regular",
        },
        "upstream": {
            "source_id": "commons__fixture_source",
            "entry_id": "commons__fixture_source__p0001",
            "sha256": "a" * 64,
            "commit": "0" * 40,
            "release_tag": "v0.1.0-rc",
            "bbox": {"x": 10, "y": 20, "w": 64, "h": 64},
        },
        "image": {
            "local_path": "data/letters/fixture_writer/alef/fixture_writer__alef__v0001.png",
            "sha256": sha,
            "mime_type": "image/png",
            "bytes": size,
            "width_px": 1,
            "height_px": 1,
            "background": "original",
        },
        "extraction": {
            "tool": "hletterscriptgen",
            "tool_version": "v0.0.1",
            "method": "manual",
            "extracted_at": "2026-05-12T00:00:00Z",
            "extracted_by": "test_suite",
            "notes": None,
        },
        "rights": {
            "rights_basis": "public_domain",
            "license_expression": "PDM-1.0",
            "commercial_use_allowed": True,
            "derivatives_allowed": True,
            "redistribution_allowed": True,
            "attribution_required": False,
            "attribution_text": None,
            "attribution_url": None,
            "verification_status": "inherited_from_upstream",
            "evidence_text": "Upstream entry verified as PDM-1.0.",
            "verified_at": "2026-05-12",
        },
        "quality": {
            "usable_for_htr": True,
            "usable_for_syngen": True,
            "legibility": "high",
            "exclusion_reasons": [],
            "notes": None,
        },
    }


def _write_indexes(
    tmp_path: Path,
    writers: list[dict],
    entries: list[dict],
) -> tuple[Path, Path]:
    writers_path = tmp_path / "writers.jsonl"
    entries_path = tmp_path / "entries.jsonl"
    writers_path.write_text(
        "".join(json.dumps(w, ensure_ascii=False) + "\n" for w in writers),
        encoding="utf-8",
    )
    entries_path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    return writers_path, entries_path


def _run_against(
    tmp_path: Path,
    writers: list[dict],
    entries: list[dict],
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    writers_path, entries_path = _write_indexes(tmp_path, writers, entries)
    return subprocess.run(
        [
            sys.executable, str(VALIDATOR),
            "--writers", str(writers_path),
            "--entries", str(entries_path),
            "--repo-root", str(tmp_path),
            *extra_args,
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def test_current_indexes_validate() -> None:
    result = run_validator()
    assert result.returncode == 0, result.stderr
    assert "ok:" in result.stdout


def test_empty_indexes_validate(tmp_path: Path) -> None:
    writers_path = tmp_path / "writers.jsonl"
    entries_path = tmp_path / "entries.jsonl"
    writers_path.write_text("", encoding="utf-8")
    entries_path.write_text("", encoding="utf-8")
    result = run_validator("--writers", writers_path, "--entries", entries_path)
    assert result.returncode == 0, result.stderr
    assert "0 writers, 0 entries" in result.stdout


def test_fixture_round_trip(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode == 0, result.stderr
    assert "ok: 1 writers, 1 entries, 1 files verified" in result.stdout


# --- Schema-level rejections ------------------------------------------------


def test_schema_errors_are_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    writer_fixture["status"] = "garbage"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "is not one of" in result.stderr


def test_candidate_writer_with_zero_references_is_accepted(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # The references.minItems requirement is conditional on status; a
    # `candidate` writer is allowed to ship with no references yet.
    writer_fixture["status"] = "candidate"
    writer_fixture["references"] = []
    # Remove the entry so the writer can be candidate without a verified
    # crop referencing it.
    result = _run_against(tmp_path, [writer_fixture], [])
    assert result.returncode == 0, result.stderr


def test_verified_writer_without_references_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
) -> None:
    writer_fixture["references"] = []
    result = _run_against(tmp_path, [writer_fixture], [])
    assert result.returncode != 0
    assert "references" in result.stderr
    # jsonschema's exact wording for "minItems violated" is
    # "[] should be non-empty"; accept either that or a generic
    # if/then failure message for forward compatibility.
    lower = result.stderr.lower()
    assert any(needle in lower for needle in (
        "should be non-empty",
        "minitems",
        "is too short",
        "should not be valid",
    ))


# --- Cross-field validation -------------------------------------------------


def test_unknown_writer_id_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["writer_id"] = "missing_writer"
    entry_fixture["entry_id"] = "missing_writer__alef__v0001"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "unknown writer_id" in result.stderr


def test_entry_id_must_start_with_writer_and_letter(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["entry_id"] = "fixture_writer__bet__v0001"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "must start with" in result.stderr


def test_letter_codepoint_must_match_name(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["letter"]["codepoint"] = "U+05D1"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "letter.codepoint mismatch" in result.stderr


def test_letter_char_must_match_name(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["letter"]["unicode_char"] = "ב"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "letter.unicode_char mismatch" in result.stderr


def test_letter_form_must_match_name(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["letter"]["form"] = "final"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "letter.form mismatch" in result.stderr


# --- Upstream block ---------------------------------------------------------


def test_upstream_commit_must_be_sha(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # Tag-style refs are no longer accepted in `upstream.commit`. They
    # belong in `upstream.release_tag` instead.
    entry_fixture["upstream"]["commit"] = "v0.1.0-rc"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "does not match" in result.stderr or "pattern" in result.stderr


def test_upstream_release_tag_is_optional(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["upstream"]["release_tag"] = None
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode == 0, result.stderr


def test_upstream_repo_field_is_not_allowed(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # The upstream URL lives in scripts/release_recipe.json now; per-row
    # duplication is rejected by additionalProperties:false.
    entry_fixture["upstream"]["repo"] = "https://github.com/HeOCR/whatever"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "Additional properties are not allowed" in result.stderr or "additionalProperties" in result.stderr


def test_upstream_entry_id_must_match_source(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["upstream"]["entry_id"] = "commons__another_source__p0001"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "upstream.entry_id" in result.stderr


# --- Local path conventions -------------------------------------------------


def test_local_path_prefix_is_enforced(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["image"]["local_path"] = "data/letters/wrong/alef/x.png"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "must start with" in result.stderr


def test_local_path_extension_must_match_mime(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["image"]["local_path"] = (
        "data/letters/fixture_writer/alef/fixture_writer__alef__v0001.jpg"
    )
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "does not match" in result.stderr


# --- Background <-> mime guard ----------------------------------------------


def test_transparent_background_with_jpeg_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # Schema if/then enforces that transparent backgrounds require an
    # alpha-capable mime type. JPEG has no alpha.
    entry_fixture["image"]["mime_type"] = "image/jpeg"
    entry_fixture["image"]["local_path"] = (
        "data/letters/fixture_writer/alef/fixture_writer__alef__v0001.jpg"
    )
    # Rename the on-disk fixture to match.
    src = tmp_path / "data/letters/fixture_writer/alef/fixture_writer__alef__v0001.png"
    dst = tmp_path / "data/letters/fixture_writer/alef/fixture_writer__alef__v0001.jpg"
    src.rename(dst)
    entry_fixture["image"]["background"] = "transparent"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0


# --- Rights validation ------------------------------------------------------


def test_unverified_entry_cannot_claim_positive_permissions(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["rights"]["verification_status"] = "source_note_only"
    entry_fixture["rights"]["commercial_use_allowed"] = True
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "should not be valid" in result.stderr


def test_attribution_required_without_text_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["rights"]["license_expression"] = "CC-BY-SA-4.0"
    entry_fixture["rights"]["rights_basis"] = "cc_by_sa"
    entry_fixture["rights"]["attribution_required"] = True
    entry_fixture["rights"]["attribution_text"] = None
    entry_fixture["rights"]["attribution_url"] = None
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0


def test_attribution_with_blank_text_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["rights"]["license_expression"] = "CC-BY-SA-4.0"
    entry_fixture["rights"]["rights_basis"] = "cc_by_sa"
    entry_fixture["rights"]["attribution_required"] = True
    entry_fixture["rights"]["attribution_text"] = "   "
    entry_fixture["rights"]["attribution_url"] = (
        "https://commons.wikimedia.org/wiki/File:Example.jpg"
    )
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "attribution_text is null, blank, or whitespace-only" in result.stderr


def test_rights_basis_must_match_license_expression(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # The validator's LICENSE_BASIS_MAP says CC-BY-SA-4.0 → cc_by_sa.
    # An ingester who flips one but not the other is rejected.
    entry_fixture["rights"]["license_expression"] = "CC-BY-SA-4.0"
    entry_fixture["rights"]["rights_basis"] = "cc0"
    entry_fixture["rights"]["attribution_required"] = True
    entry_fixture["rights"]["attribution_text"] = "Example licensor"
    entry_fixture["rights"]["attribution_url"] = (
        "https://commons.wikimedia.org/wiki/File:Example.jpg"
    )
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "rights_basis" in result.stderr
    assert "does not match" in result.stderr


def test_unknown_license_expression_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["rights"]["license_expression"] = "GPL-3.0"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "LICENSE_BASIS_MAP" in result.stderr or "not in" in result.stderr


def test_null_license_requires_unknown_basis(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["rights"]["license_expression"] = None
    entry_fixture["rights"]["rights_basis"] = "public_domain"
    # null license + positive permissions is also conditionally blocked
    # by the schema, so flip to a verification status that allows null
    # everywhere.
    entry_fixture["rights"]["verification_status"] = "unverified"
    entry_fixture["rights"]["commercial_use_allowed"] = None
    entry_fixture["rights"]["derivatives_allowed"] = None
    entry_fixture["rights"]["redistribution_allowed"] = None
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "license_expression is null" in result.stderr


# --- File integrity ---------------------------------------------------------


def test_missing_local_image_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    (tmp_path / entry_fixture["image"]["local_path"]).unlink()
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "file does not exist" in result.stderr


def test_byte_size_mismatch_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    real_bytes = entry_fixture["image"]["bytes"]
    entry_fixture["image"]["bytes"] = real_bytes + 1
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "byte size mismatch" in result.stderr


def test_sha256_mismatch_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["image"]["sha256"] = "0" * 64
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "sha256 mismatch" in result.stderr


def test_duplicate_entry_id_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    second = json.loads(json.dumps(entry_fixture))
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture, second])
    assert result.returncode != 0
    assert "duplicate" in result.stderr


def test_missing_index_file_is_rejected(tmp_path: Path) -> None:
    result = run_validator(
        "--writers", tmp_path / "missing.jsonl",
        "--entries", ENTRIES,
    )
    assert result.returncode != 0
    assert "file does not exist" in result.stderr


# --- Tool version ----------------------------------------------------------


@pytest.mark.parametrize("version", [
    "v0.0.1",
    "0.0.1",
    "v1.2.3",
    "v1.2.3-rc1",
    "v1.2.3-3-gabc1234",
    "v1.2.3+build.5",
    "v1.2.3-rc1+build.5",
])
def test_tool_version_accepts_common_shapes(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
    version: str,
) -> None:
    entry_fixture["extraction"]["tool_version"] = version
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("version", [
    "not-semver",
    "v1",
    "v1.2",
    "1.2.3.4",
])
def test_tool_version_rejects_garbage(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
    version: str,
) -> None:
    entry_fixture["extraction"]["tool_version"] = version
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0


# --- Upstream cross-validation ---------------------------------------------


def _write_upstream(tmp_path: Path, entries: list[dict]) -> Path:
    upstream_root = tmp_path / "upstream"
    (upstream_root / "data" / "index").mkdir(parents=True)
    upstream_entries = upstream_root / "data" / "index" / "entries.jsonl"
    upstream_entries.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    return upstream_root


def _upstream_entry(width: int = 4000, height: int = 5000) -> dict:
    """Minimal upstream entry shape (only the fields the validator
    actually reads). The full upstream schema is enforced by the upstream
    repo's own CI, not here."""
    return {
        "entry_id": "commons__fixture_source__p0001",
        "files": [{
            "sha256": "a" * 64,
            "width_px": width,
            "height_px": height,
        }],
    }


def test_upstream_cross_check_passes_for_in_bounds_bbox(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    upstream_root = _write_upstream(tmp_path, [_upstream_entry()])
    result = _run_against(
        tmp_path, [writer_fixture], [entry_fixture],
        "--upstream-path", str(upstream_root),
    )
    assert result.returncode == 0, result.stderr
    assert "1 upstream-cross-checked" in result.stdout


def test_upstream_cross_check_rejects_missing_entry(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    upstream_root = _write_upstream(tmp_path, [])
    result = _run_against(
        tmp_path, [writer_fixture], [entry_fixture],
        "--upstream-path", str(upstream_root),
    )
    assert result.returncode != 0
    assert "not found in" in result.stderr


def test_upstream_cross_check_rejects_sha_mismatch(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    upstream = _upstream_entry()
    upstream["files"][0]["sha256"] = "b" * 64
    upstream_root = _write_upstream(tmp_path, [upstream])
    result = _run_against(
        tmp_path, [writer_fixture], [entry_fixture],
        "--upstream-path", str(upstream_root),
    )
    assert result.returncode != 0
    assert "upstream.sha256" in result.stderr


def test_upstream_cross_check_rejects_bbox_out_of_bounds(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    upstream_root = _write_upstream(tmp_path, [_upstream_entry(width=50, height=50)])
    entry_fixture["upstream"]["bbox"] = {"x": 10, "y": 20, "w": 100, "h": 100}
    result = _run_against(
        tmp_path, [writer_fixture], [entry_fixture],
        "--upstream-path", str(upstream_root),
    )
    assert result.returncode != 0
    assert "beyond upstream scan" in result.stderr
