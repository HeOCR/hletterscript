# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for the dataset version recorded in `scripts/release_recipe.json::version`.

## [Unreleased]

(no in-progress changes)

## [0.0.0-rc] - 2026-05-12

Initial scaffolding release. Per-letter image corpus is empty; the
repository ships the schemas, validators, release tooling, CI, and
licensing policy needed to start ingesting.

### Added

- Writer-level (`schemas/writer.schema.json`) and entry-level
  (`schemas/entry.schema.json`) record contracts. Each entry references
  an upstream scan in `HeOCR/public-domain-hand-written-hebrew-scans`
  by `source_id`, `entry_id`, `sha256` (mutable-tag-free), `commit`
  (40-char SHA), and `bbox`.
- `scripts/validate_indexes.py`: schema validation, referential
  integrity, Hebrew letter codepoint/name/form consistency,
  `rights_basis` ↔ `license_expression` cross-check, file-integrity
  re-hashing, and optional `--upstream-path` cross-validation of
  upstream `sha256` and `bbox` bounds.
- `scripts/generate_release_artifacts.py` + `scripts/release_recipe.json`:
  deterministic generation of `NOTICE.md`, `CITATION.cff`, and
  `datapackage.json`. Citation `date-released` is stable per version
  (`version_released_date` in the recipe); datapackage `released_at`
  tracks the corpus state (`max(extraction.extracted_at)`).
- `.gitattributes` configures Git LFS for `data/letters/**` image
  files. CI fetches LFS bytes before validation.
- `LICENSE` (CC0 1.0) and `LICENSE.md` compound-licensing policy with
  per-license inheritance table and CC-BY-SA-4.0 ShareAlike handling.
- `AGENTS.md`, `README.md`, `docs/dataset_structure.md`,
  `docs/letters.md`, and `docs/release_process.md`.
- `.github/workflows/ci.yml`, `.github/pull_request_template.md`,
  `.editorconfig`.
- Pytest test suite covering schema rejection, referential integrity,
  letter consistency, rights cross-check, attribution gating,
  file-integrity checks, empty-corpus fallbacks, non-empty corpus
  NOTICE/CITATION/datapackage rendering, upstream cross-validation,
  and Frictionless Data Package conformance.

[Unreleased]: https://github.com/HeOCR/hletterscript/compare/v0.0.0-rc...HEAD
[0.0.0-rc]: https://github.com/HeOCR/hletterscript/releases/tag/v0.0.0-rc
