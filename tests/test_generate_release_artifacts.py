from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from frictionless import Package


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "generate_release_artifacts.py"
RECIPE = REPO_ROOT / "scripts" / "release_recipe.json"
WRITERS = REPO_ROOT / "data" / "index" / "writers.jsonl"
ENTRIES = REPO_ROOT / "data" / "index" / "entries.jsonl"
NOTICE = REPO_ROOT / "NOTICE.md"
CITATION = REPO_ROOT / "CITATION.cff"
DATAPACKAGE = REPO_ROOT / "datapackage.json"


def _load_entries() -> list[dict]:
    return [
        json.loads(line)
        for line in ENTRIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_writers() -> list[dict]:
    return [
        json.loads(line)
        for line in WRITERS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _run_generator(
    *,
    cwd: Path,
    writers: Path = WRITERS,
    entries: Path = ENTRIES,
    recipe: Path = RECIPE,
    notice: Path,
    citation: Path,
    datapackage: Path,
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--writers", str(writers),
            "--entries", str(entries),
            "--recipe", str(recipe),
            "--notice", str(notice),
            "--citation", str(citation),
            "--datapackage", str(datapackage),
            *extra_args,
        ],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


# --- Empty-corpus tests (the current committed state) ----------------------


def test_committed_artifacts_are_up_to_date(tmp_path: Path) -> None:
    notice = tmp_path / "NOTICE.md"
    citation = tmp_path / "CITATION.cff"
    datapackage = tmp_path / "datapackage.json"

    result = _run_generator(
        cwd=tmp_path, notice=notice, citation=citation, datapackage=datapackage
    )
    assert result.returncode == 0, result.stderr

    assert notice.read_bytes() == NOTICE.read_bytes(), (
        "NOTICE.md is stale; run `python3 scripts/generate_release_artifacts.py`"
    )
    assert citation.read_bytes() == CITATION.read_bytes(), (
        "CITATION.cff is stale; run `python3 scripts/generate_release_artifacts.py`"
    )
    assert datapackage.read_bytes() == DATAPACKAGE.read_bytes(), (
        "datapackage.json is stale; run `python3 scripts/generate_release_artifacts.py`"
    )


def test_generator_is_idempotent(tmp_path: Path) -> None:
    paths = {
        "notice": tmp_path / "NOTICE.md",
        "citation": tmp_path / "CITATION.cff",
        "datapackage": tmp_path / "datapackage.json",
    }

    first = _run_generator(cwd=tmp_path, **paths)
    assert first.returncode == 0, first.stderr
    snapshot = {name: path.read_bytes() for name, path in paths.items()}

    second = _run_generator(cwd=tmp_path, **paths)
    assert second.returncode == 0, second.stderr
    for name, path in paths.items():
        assert path.read_bytes() == snapshot[name], f"{name} differed between runs"


def test_datapackage_counts_match_index() -> None:
    entries = _load_entries()
    writers = _load_writers()
    package = json.loads(DATAPACKAGE.read_text(encoding="utf-8"))
    assert package["stats"]["record_count"] == len(entries)
    assert package["stats"]["writer_record_count"] == len(writers)


def test_datapackage_keys_are_sorted() -> None:
    package = json.loads(DATAPACKAGE.read_text(encoding="utf-8"))
    assert list(package.keys()) == sorted(package.keys())


def test_citation_parses_and_has_required_cff_keys() -> None:
    document = yaml.safe_load(CITATION.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    for required in (
        "cff-version", "type", "title", "authors", "version", "date-released"
    ):
        assert required in document, f"CITATION.cff missing required key: {required}"
    assert document["cff-version"] == "1.2.0"
    assert document["type"] == "dataset"
    assert document["license"] == "CC0-1.0"


def test_datapackage_validates_against_frictionless_spec() -> None:
    package = Package(str(DATAPACKAGE))
    assert package.name == "hletterscript"
    errors = list(Package.metadata_validate(package.to_descriptor()))
    assert errors == [], [getattr(e, "message", str(e)) for e in errors]


def test_empty_corpus_falls_back_to_recipe_initial_date(tmp_path: Path) -> None:
    if _load_entries():
        pytest.skip("corpus is no longer empty")
    notice = tmp_path / "NOTICE.md"
    citation = tmp_path / "CITATION.cff"
    datapackage = tmp_path / "datapackage.json"
    result = _run_generator(
        cwd=tmp_path, notice=notice, citation=citation, datapackage=datapackage
    )
    assert result.returncode == 0, result.stderr
    package = json.loads(datapackage.read_text(encoding="utf-8"))
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    assert package["released_at"] == recipe["initial_release_date"]
    assert package["stats"]["record_count"] == 0


def test_empty_corpus_falls_back_when_recipe_initial_date_missing(
    tmp_path: Path,
) -> None:
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    del recipe["initial_release_date"]
    bad_recipe = tmp_path / "bad_recipe.json"
    bad_recipe.write_text(json.dumps(recipe), encoding="utf-8")

    writers_path = tmp_path / "writers.jsonl"
    entries_path = tmp_path / "entries.jsonl"
    writers_path.write_text("", encoding="utf-8")
    entries_path.write_text("", encoding="utf-8")

    result = _run_generator(
        cwd=tmp_path,
        writers=writers_path,
        entries=entries_path,
        recipe=bad_recipe,
        notice=tmp_path / "NOTICE.md",
        citation=tmp_path / "CITATION.cff",
        datapackage=tmp_path / "datapackage.json",
    )
    assert result.returncode != 0
    assert "initial_release_date" in result.stderr


def test_check_mode_passes_when_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_check_mode_fails_when_stale(tmp_path: Path) -> None:
    notice = tmp_path / "NOTICE.md"
    citation = tmp_path / "CITATION.cff"
    datapackage = tmp_path / "datapackage.json"
    shutil.copyfile(NOTICE, notice)
    shutil.copyfile(CITATION, citation)
    shutil.copyfile(DATAPACKAGE, datapackage)
    datapackage.write_text("{}\n", encoding="utf-8")

    result = _run_generator(
        cwd=tmp_path,
        notice=notice,
        citation=citation,
        datapackage=datapackage,
        extra_args=("--check",),
    )
    assert result.returncode == 1
    assert "stale" in result.stderr
    assert "datapackage.json" in result.stderr


def test_recipe_required_fields_must_be_present(tmp_path: Path) -> None:
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    del recipe["authors"]
    bad_recipe = tmp_path / "bad_recipe.json"
    bad_recipe.write_text(json.dumps(recipe), encoding="utf-8")

    result = _run_generator(
        cwd=tmp_path,
        recipe=bad_recipe,
        notice=tmp_path / "NOTICE.md",
        citation=tmp_path / "CITATION.cff",
        datapackage=tmp_path / "datapackage.json",
    )
    assert result.returncode != 0
    assert "authors" in result.stderr


def test_version_released_date_required(tmp_path: Path) -> None:
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    del recipe["version_released_date"]
    bad_recipe = tmp_path / "bad_recipe.json"
    bad_recipe.write_text(json.dumps(recipe), encoding="utf-8")
    result = _run_generator(
        cwd=tmp_path,
        recipe=bad_recipe,
        notice=tmp_path / "NOTICE.md",
        citation=tmp_path / "CITATION.cff",
        datapackage=tmp_path / "datapackage.json",
    )
    assert result.returncode != 0
    assert "version_released_date" in result.stderr


# --- Non-empty-corpus tests (the bug-prevention tier) ----------------------
#
# These tests construct a synthetic 2-entry corpus including one
# CC-BY-SA-4.0 attribution-required entry, run the generator, and
# verify the rendered artefacts. Without these, the entire NOTICE.md
# stanza-building path would be unreachable by CI for as long as the
# committed corpus stays empty.


def _hash(data: bytes) -> tuple[str, int]:
    return hashlib.sha256(data).hexdigest(), len(data)


def _synthetic_writer(writer_id: str) -> dict:
    return {
        "writer_id": writer_id,
        "status": "verified",
        "display_name": writer_id.replace("_", " ").title(),
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
                "citation": "tests/test_generate_release_artifacts.py",
                "quote": None,
                "url": None,
            }
        ],
        "ingest": {"agent_notes": "fixture", "blocked_reason": None},
    }


def _synthetic_entry(
    tmp_path: Path,
    writer_id: str,
    letter_name: str,
    codepoint: str,
    char: str,
    form: str,
    variant: int,
    license_expression: str,
    rights_basis: str,
    extracted_at: str,
    *,
    attribution_required: bool = False,
    attribution_text: str | None = None,
    attribution_url: str | None = None,
) -> dict:
    entry_id = f"{writer_id}__{letter_name}__v{variant:04d}"
    rel_dir = Path("data") / "letters" / writer_id / letter_name
    abs_dir = tmp_path / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    rel_path = rel_dir / f"{entry_id}.png"
    abs_path = tmp_path / rel_path
    payload = f"png-{entry_id}".encode("utf-8")
    abs_path.write_bytes(payload)
    sha, size = _hash(payload)
    return {
        "entry_id": entry_id,
        "writer_id": writer_id,
        "letter": {
            "codepoint": codepoint,
            "unicode_char": char,
            "name": letter_name,
            "form": form,
        },
        "upstream": {
            "source_id": f"commons__{writer_id}_doc",
            "entry_id": f"commons__{writer_id}_doc__p0001",
            "sha256": "a" * 64,
            "commit": "0" * 40,
            "release_tag": "v0.1.0-rc",
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
        },
        "image": {
            "local_path": str(rel_path),
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
            "extracted_at": extracted_at,
            "extracted_by": "test_suite",
            "notes": None,
        },
        "rights": {
            "rights_basis": rights_basis,
            "license_expression": license_expression,
            "commercial_use_allowed": True,
            "derivatives_allowed": True,
            "redistribution_allowed": True,
            "attribution_required": attribution_required,
            "attribution_text": attribution_text,
            "attribution_url": attribution_url,
            "verification_status": "inherited_from_upstream",
            "evidence_text": "Upstream verified.",
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


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> dict:
    writers = [
        _synthetic_writer("writer_pdm"),
        _synthetic_writer("writer_cc_by_sa"),
    ]
    entries = [
        _synthetic_entry(
            tmp_path,
            writer_id="writer_pdm",
            letter_name="alef",
            codepoint="U+05D0",
            char="א",
            form="regular",
            variant=1,
            license_expression="PDM-1.0",
            rights_basis="public_domain",
            extracted_at="2026-05-10T12:00:00Z",
        ),
        _synthetic_entry(
            tmp_path,
            writer_id="writer_cc_by_sa",
            letter_name="bet",
            codepoint="U+05D1",
            char="ב",
            form="regular",
            variant=1,
            license_expression="CC-BY-SA-4.0",
            rights_basis="cc_by_sa",
            extracted_at="2026-05-11T18:30:00Z",
            attribution_required=True,
            attribution_text="User:Example via Wikimedia Commons, CC BY-SA 4.0",
            attribution_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
        ),
    ]
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
    return {
        "writers_path": writers_path,
        "entries_path": entries_path,
        "writers": writers,
        "entries": entries,
    }


def _generate_for_corpus(
    tmp_path: Path, synthetic_corpus: dict
) -> tuple[Path, Path, Path]:
    notice = tmp_path / "NOTICE.md"
    citation = tmp_path / "CITATION.cff"
    datapackage = tmp_path / "datapackage.json"
    result = _run_generator(
        cwd=tmp_path,
        writers=synthetic_corpus["writers_path"],
        entries=synthetic_corpus["entries_path"],
        notice=notice,
        citation=citation,
        datapackage=datapackage,
    )
    assert result.returncode == 0, result.stderr
    return notice, citation, datapackage


def test_non_empty_corpus_notice_lists_attribution_required(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    notice, _, _ = _generate_for_corpus(tmp_path, synthetic_corpus)
    text = notice.read_text(encoding="utf-8")
    assert "writer_cc_by_sa__bet__v0001" in text, (
        "CC-BY-SA entry should be listed in NOTICE.md"
    )
    assert "writer_pdm__alef__v0001" not in text, (
        "PDM entry should NOT be listed in NOTICE.md (no attribution required)"
    )
    assert "User:Example" in text
    assert "https://commons.wikimedia.org/wiki/File:Example.jpg" in text


def test_non_empty_corpus_notice_url_is_valid_github_blob(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    # The bug-fix verification: NOTICE.md must NOT embed a `release:`
    # prefix in the upstream blob URL. The commit field is a SHA; the
    # release_tag is metadata only. A `release:` substring in any URL
    # would indicate the bug from the original PR has regressed.
    notice, _, _ = _generate_for_corpus(tmp_path, synthetic_corpus)
    text = notice.read_text(encoding="utf-8")

    # Scan only URLs inside angle brackets (the markdown-link form the
    # generator uses). Free prose like "Corpus release:" is unrelated.
    urls = re.findall(r"<(https?://[^>]+)>", text)
    for url in urls:
        assert "release:" not in url, (
            f"NOTICE.md URL must not contain `release:` prefix: {url!r}"
        )

    # The upstream link should contain a 40-char hex sha after /blob/.
    pattern = re.compile(r"/blob/([a-f0-9]{40})/data/index/entries\.jsonl")
    matches = pattern.findall(text)
    assert matches, "expected at least one /blob/<sha>/ link in NOTICE.md"


def test_non_empty_corpus_datapackage_stats(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    _, _, datapackage = _generate_for_corpus(tmp_path, synthetic_corpus)
    package = json.loads(datapackage.read_text(encoding="utf-8"))
    stats = package["stats"]
    assert stats["record_count"] == 2
    assert stats["writer_record_count"] == 2
    assert stats["entry_writer_count"] == 2
    assert stats["attribution_required_count"] == 1
    assert stats["license_breakdown"] == {"CC-BY-SA-4.0": 1, "PDM-1.0": 1}
    assert stats["letter_breakdown"] == {"alef": 1, "bet": 1}
    assert stats["writer_breakdown"] == {"writer_cc_by_sa": 1, "writer_pdm": 1}


def test_non_empty_corpus_released_at_is_latest_extraction(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    _, _, datapackage = _generate_for_corpus(tmp_path, synthetic_corpus)
    package = json.loads(datapackage.read_text(encoding="utf-8"))
    assert package["released_at"] == "2026-05-11T18:30:00Z"


def test_non_empty_corpus_citation_date_is_stable_not_extraction(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    # The whole point of separating `version_released_date` from
    # `released_at`: citations must not drift as entries accumulate.
    _, citation, datapackage = _generate_for_corpus(tmp_path, synthetic_corpus)
    document = yaml.safe_load(citation.read_text(encoding="utf-8"))
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    assert str(document["date-released"]) == recipe["version_released_date"]
    # And it must NOT equal the (later) corpus-state timestamp.
    package = json.loads(datapackage.read_text(encoding="utf-8"))
    assert str(document["date-released"]) != package["released_at"][:10] or (
        recipe["version_released_date"] == package["released_at"][:10]
    )


def test_non_empty_corpus_datapackage_frictionless_valid(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    _, _, datapackage = _generate_for_corpus(tmp_path, synthetic_corpus)
    package = Package(str(datapackage))
    errors = list(Package.metadata_validate(package.to_descriptor()))
    assert errors == [], [getattr(e, "message", str(e)) for e in errors]


def test_non_empty_corpus_missing_attribution_flag_is_rejected(
    tmp_path: Path, synthetic_corpus: dict
) -> None:
    # If a CC-BY-SA entry forgets attribution_required=True the
    # generator's consistency check must fail loudly rather than silently
    # dropping the entry from NOTICE.md.
    entries = synthetic_corpus["entries"]
    cc_entry = next(e for e in entries if e["rights"]["license_expression"] == "CC-BY-SA-4.0")
    cc_entry["rights"]["attribution_required"] = False
    cc_entry["rights"]["attribution_text"] = None
    cc_entry["rights"]["attribution_url"] = None
    synthetic_corpus["entries_path"].write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )
    result = _run_generator(
        cwd=tmp_path,
        writers=synthetic_corpus["writers_path"],
        entries=synthetic_corpus["entries_path"],
        notice=tmp_path / "NOTICE.md",
        citation=tmp_path / "CITATION.cff",
        datapackage=tmp_path / "datapackage.json",
    )
    assert result.returncode != 0
    assert "CC-BY-SA-4.0" in result.stderr
    assert "attribution_required" in result.stderr
