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

UPSTREAM_REPO = "https://github.com/HeOCR/public-domain-hand-written-hebrew-scans"


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
    # Write a tiny placeholder PNG (1x1 pixel) so the file-integrity check
    # has something real to hash. The validator only cares about size and
    # sha256; the bytes do not need to be a valid PNG decoder-wise, just
    # consistent with the recorded metadata.
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
            "repo": UPSTREAM_REPO,
            "source_id": "commons__fixture_source",
            "entry_id": "commons__fixture_source__p0001",
            "sha256": "a" * 64,
            "commit": "release:v0.1.0-rc",
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
) -> subprocess.CompletedProcess[str]:
    writers_path, entries_path = _write_indexes(tmp_path, writers, entries)
    return subprocess.run(
        [
            sys.executable, str(VALIDATOR),
            "--writers", str(writers_path),
            "--entries", str(entries_path),
            "--repo-root", str(tmp_path),
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
    # The repo ships with empty index files. They must validate cleanly.
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


def test_schema_errors_are_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    writer_fixture["status"] = "garbage"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "is not one of" in result.stderr


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
    # Schema regex on entry_id is structural; this test exercises the
    # validator-level cross-check against writer_id + letter.name.
    entry_fixture["entry_id"] = "fixture_writer__bet__v0001"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "must start with" in result.stderr


def test_letter_codepoint_must_match_name(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["letter"]["codepoint"] = "U+05D1"  # bet, not alef
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
    entry_fixture["letter"]["form"] = "final"  # alef is regular
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "letter.form mismatch" in result.stderr


def test_upstream_repo_url_is_pinned(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["upstream"]["repo"] = "https://github.com/HeOCR/somewhere_else"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "upstream.repo must be" in result.stderr


def test_upstream_entry_id_must_match_source(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    entry_fixture["upstream"]["entry_id"] = "commons__another_source__p0001"
    result = _run_against(tmp_path, [writer_fixture], [entry_fixture])
    assert result.returncode != 0
    assert "upstream.entry_id" in result.stderr


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
    assert "mime_type" in result.stderr


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
    assert "attribution_text" in result.stderr or "attribution_url" in result.stderr


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


def test_missing_local_image_is_rejected(
    tmp_path: Path,
    writer_fixture: dict,
    entry_fixture: dict,
) -> None:
    # Delete the fixture image but keep the entry pointing at its
    # canonical path. The schema-conformant path stays valid; only the
    # on-disk file is missing.
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
    # Two rows with the same entry_id.
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
