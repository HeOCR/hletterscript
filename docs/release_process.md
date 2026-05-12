# Release Process

This document is the runbook for cutting a new dataset release. Releases
are tagged on `main` and follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** — backwards-incompatible schema changes, ID renames, or
  rights-policy changes that change what consumers can do with the data.
- **MINOR** — additive schema fields, new writers, or substantial new
  per-letter ingestion batches.
- **PATCH** — bug-fix re-extractions, metadata corrections, validator
  fixes, single-entry rights re-verifications.

Pre-1.0 releases use `0.X.Y-rc` (release candidate) suffixes; the
`-rc` is dropped at `1.0.0`.

## Two timestamps, deliberately distinct

The release generator emits two different timestamps with different
semantics. Keep them separated mentally:

| Field                                          | Source                                                       | Meaning                                              | Bumps when                                              |
| ---------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------- |
| `CITATION.cff::date-released`                  | `release_recipe.json::version_released_date`                 | The date *this version* of the dataset was released. | A human bumps `version` *and* `version_released_date`.  |
| `datapackage.json::released_at`                | `max(extraction.extracted_at)` across all entries            | Latest corpus-state timestamp.                       | Every ingest PR that adds or replaces an entry.         |

`date-released` is what citations should be reproducible against and what
Zenodo/GitHub indexers expect. `released_at` is informational metadata
about how fresh the corpus is right now. **Never collapse them into
one** — that was the v0.0.0-rc design's original bug.

## Cutting a release

1. **Choose the new version.** Decide MAJOR/MINOR/PATCH per the rules
   above. Open a release PR (label `release:vX.Y.Z`).
2. **Bump the recipe.** Edit `scripts/release_recipe.json`:
   - `version` → the new version.
   - `version_released_date` → today's date (YYYY-MM-DD).
3. **Regenerate artefacts.**
   ```bash
   python3 scripts/generate_release_artifacts.py
   ```
   Stage the resulting `NOTICE.md`, `CITATION.cff`, and `datapackage.json`.
4. **Update the changelog.** Move the `[Unreleased]` section to a new
   `[X.Y.Z] - YYYY-MM-DD` section and add a fresh empty `[Unreleased]`
   at the top. Update the link references at the bottom of the file.
5. **Re-run pre-merge checks.**
   ```bash
   python3 scripts/validate_indexes.py
   python3 scripts/generate_release_artifacts.py --check
   python3 -m pytest
   ```
6. **Merge the release PR.** Squash-merge into `main`.
7. **Tag the release.**
   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```
8. **Cut the GitHub release** from that tag. The body should be the
   relevant `CHANGELOG.md` section.

## When NOT to bump the version

Ingest PRs that add writers or entries do **not** bump the version on
their own. They bump `datapackage.json::released_at` (automatically, via
`max(extraction.extracted_at)`), and they update the per-license,
per-writer, and per-letter stats — but the version stays the same until
a human deliberately cuts a release. This keeps `CITATION.cff` stable
between releases.

## Pre-1.0 versioning

While the dataset is small and the schema may still shift, releases
carry the `-rc` suffix. The first non-rc release is `1.0.0`, signalling
that the schema and ID conventions are stable enough that downstream
consumers can build long-lived pipelines on top.
