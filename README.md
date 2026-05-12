# hletterscript

A dataset of **sets of per-letter images of handwritten Hebrew letters**.
Each set groups crops produced from documents written by the *same
writer*; each set typically contains several variants of the same letter
cut from different scans by that writer.

This repository is the downstream of:

- [HeOCR/public-domain-hand-written-hebrew-scans][upstream] — the
  canonical, permissively-licensed source of page-level scans. Every
  entry here cites its upstream scan.
- [HeOCR/hletterscriptgen][gen] — the framework that turns page scans
  into per-letter crops. Each entry records which version of that
  framework produced it.

The intended downstream consumers are synthetic-document generators
([HeOCR/hocrsyngen][syngen]) and the synthetic / real Hebrew handwriting
corpora they feed into ([HeOCR/HeOCRsynth][heocrsynth],
[HeOCR/HeOCR][heocr]).

[upstream]: https://github.com/HeOCR/public-domain-hand-written-hebrew-scans
[gen]: https://github.com/HeOCR/hletterscriptgen
[syngen]: https://github.com/HeOCR/hocrsyngen
[heocrsynth]: https://github.com/HeOCR/HeOCRsynth
[heocr]: https://github.com/HeOCR/HeOCR

## Dataset Layout

- `docs/dataset_structure.md` defines the repository layout and
  ingestion model.
- `docs/letters.md` is the canonical Hebrew-letter enumeration
  (27 forms — 22 base letters plus the 5 finals).
- `data/index/writers.jsonl` is the set-level catalog: one JSON object
  per writer/scribe.
- `data/index/entries.jsonl` is the image-level catalog: one JSON
  object per cropped letter image, with upstream provenance,
  extraction provenance, file checksums, and inherited rights.
- `data/letters/<writer_id>/<letter_name>/` stores the image bytes.
- `schemas/writer.schema.json` and `schemas/entry.schema.json` define
  the record contracts.
- `scripts/validate_indexes.py` validates JSONL records against the
  schemas, enforces referential integrity, checks Hebrew-letter
  codepoint/name/form consistency, pins the upstream repo URL, and
  re-verifies image file checksums and sizes on disk.
- `scripts/generate_release_artifacts.py` regenerates `NOTICE.md`,
  `CITATION.cff`, and `datapackage.json` deterministically from the
  indexes.
- `LICENSE.md` documents the compound licensing policy for
  metadata and per-image inherited rights.

## Serialization Decision

The canonical editable indexes are newline-delimited JSON (`.jsonl`),
matching the upstream scans repo's convention.

JSONL is deliberately used instead of CSV because these records need
nested upstream references, bounding boxes, rights inheritance,
extraction provenance, and quality measurements. CSV/Parquet/SQLite
exports can be generated later as derived artefacts; the source of
truth stays line-oriented, diffable, streamable JSON.

## Requirements

- **Python ≥ 3.11** (the validator uses `hashlib.file_digest`).
  CI pins 3.12.
- **Git LFS** — image bytes under `data/letters/**` are tracked via
  LFS (see `.gitattributes`). After cloning, run `git lfs install`
  once, then `git lfs pull` to fetch the actual image bytes.

Run the current validation check with:

```bash
git lfs install && git lfs pull
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_indexes.py
python3 scripts/generate_release_artifacts.py --check
python3 -m pytest
```

## Current Status

`v0.0.0-rc` — **initial setup**. The repository ships with the
schemas, validation tooling, release-artifact generator, CI workflow,
and licensing policy in place. The per-letter image indexes
(`writers.jsonl`, `entries.jsonl`) are empty: actual letter-image
ingestion happens in subsequent PRs, produced by
[HeOCR/hletterscriptgen][gen] from scans in the upstream repo.

The repository uses a compound licensing model: repository-authored
metadata is dedicated to the public domain under CC0 1.0 (see
[`LICENSE`](LICENSE)), while per-image rights are recorded individually
and inherited from each crop's upstream scan. See [`LICENSE.md`]\
(LICENSE.md) for the full policy, including the CC BY-SA ShareAlike
caveat and the rules for remix-friendly release bundles.

## How to use this repo

- [`data/index/entries.jsonl`](data/index/entries.jsonl) is the source
  of truth for the per-letter image corpus — one JSON object per crop,
  with upstream citation, file checksums, and inherited rights.
- [`data/index/writers.jsonl`](data/index/writers.jsonl) catalogs the
  writers, including candidate leads and rejected records.
- [`schemas/entry.schema.json`](schemas/entry.schema.json) and
  [`schemas/writer.schema.json`](schemas/writer.schema.json) define the
  record contracts; [`scripts/validate_indexes.py`]\
  (scripts/validate_indexes.py) enforces them in CI.
- Contributors adding new entries should start with
  [`AGENTS.md`](AGENTS.md) for ingest rules, naming, and the pre-PR
  checklist.
