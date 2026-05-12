from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

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
    assert package["stats"]["entry_writer_count"] == len(
        {e["writer_id"] for e in entries}
    )


def test_datapackage_keys_are_sorted() -> None:
    raw = DATAPACKAGE.read_text(encoding="utf-8")
    package = json.loads(raw)
    assert list(package.keys()) == sorted(package.keys())


def test_datapackage_resource_record_counts_match() -> None:
    package = json.loads(DATAPACKAGE.read_text(encoding="utf-8"))
    by_name = {resource["name"]: resource for resource in package["resources"]}
    assert by_name["entries"]["record_count"] == len(_load_entries())
    assert by_name["writers"]["record_count"] == len(_load_writers())


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
    assert isinstance(document["authors"], list) and document["authors"]
    for author in document["authors"]:
        assert "name" in author


def test_datapackage_validates_against_frictionless_spec() -> None:
    package = Package(str(DATAPACKAGE))
    assert package.name == "hletterscript"

    errors = list(Package.metadata_validate(package.to_descriptor()))
    assert errors == [], [getattr(e, "message", str(e)) for e in errors]


def test_empty_corpus_falls_back_to_recipe_initial_date(tmp_path: Path) -> None:
    # The repo ships in this exact state at v0.0.0-rc: empty indexes,
    # release timestamp comes from recipe.initial_release_date. This is
    # the test that pins that behaviour and prevents future regressions.
    notice = tmp_path / "NOTICE.md"
    citation = tmp_path / "CITATION.cff"
    datapackage = tmp_path / "datapackage.json"

    result = _run_generator(
        cwd=tmp_path, notice=notice, citation=citation, datapackage=datapackage
    )
    assert result.returncode == 0, result.stderr

    package = json.loads(datapackage.read_text(encoding="utf-8"))
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    if _load_entries():
        return  # only meaningful when the committed corpus is empty
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
