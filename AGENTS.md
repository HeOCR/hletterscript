# AGENTS.md

Operational rules for agents and humans contributing per-letter image
crops, writer records, or tooling to this repository. If anything below
conflicts with `docs/dataset_structure.md` or `LICENSE.md`, those
documents win — this file is a working summary, not a re-derivation of
policy.

## What this repo is

A dataset of **sets of per-letter images of handwritten Hebrew letters**,
grouped by writer. Each set = one person/scribe. Each per-letter image
is a **crop** of a permissively-licensed upstream scan from
[HeOCR/public-domain-hand-written-hebrew-scans][upstream], with rights
inherited and recorded per image. Canonical layout, schema motivation,
and ingestion model live in [`docs/dataset_structure.md`]\
(docs/dataset_structure.md). The Hebrew letter enumeration is in
[`docs/letters.md`](docs/letters.md). Compound licensing (CC0 metadata,
per-image rights inheritance) is described in
[`LICENSE.md`](LICENSE.md). The machine-readable contracts are
[`schemas/writer.schema.json`](schemas/writer.schema.json) and
[`schemas/entry.schema.json`](schemas/entry.schema.json).

[upstream]: https://github.com/HeOCR/public-domain-hand-written-hebrew-scans

## Mandatory pre-PR commands

Run these from the repo root before opening or updating a PR. The first
three are also run in CI (`.github/workflows/ci.yml`) on every push to
`main` and every PR — they must stay green.

```bash
python3 scripts/validate_indexes.py
python3 scripts/generate_release_artifacts.py
python3 -m pytest
git diff --check
```

`validate_indexes.py` must end with
`ok: N writers, M entries, K files verified`.
`generate_release_artifacts.py` must leave `NOTICE.md`, `CITATION.cff`,
and `datapackage.json` unchanged in the diff — re-run it after any edit
to `data/index/*.jsonl` or `scripts/release_recipe.json` and stage the
regenerated artefacts.
`python3 scripts/generate_release_artifacts.py --check` is the
non-mutating equivalent (CI runs the `--check` form). `pytest` must
report all tests passing. `git diff --check` must produce no output.

## Release artefacts

`NOTICE.md`, `CITATION.cff`, and `datapackage.json` at the repo root are
generated deterministically from `data/index/*.jsonl` and
`scripts/release_recipe.json`. Do not edit them by hand. Their
`released_at` / `date-released` fields track
`max(extraction.extracted_at)` across the entries, which means every
ingest PR will bump these timestamps — that is intentional and avoids a
manually-maintained release-date field. When the corpus is empty (the
initial-setup state), generation falls back to
`release_recipe.json::initial_release_date`. Regenerate by running
`python3 scripts/generate_release_artifacts.py` from the repo root.

## GitHub workflow

- One PR per coherent change. Batching is fine when the changes are
  tightly coupled (for example, a tooling change plus the docs that
  describe it); avoid batching unrelated work.
- Open PRs non-draft.
- Use the `git` and `gh` CLIs. Do not push to `main` directly; always go
  through a PR.
- Standard commit hygiene: conventional `type(scope): subject`, real
  `Co-Authored-By` trailer when collaborating, no `--no-verify`, no
  force-push to `main`.

## Ingest rules

### In scope

- Cropped images of **single** Hebrew letters from handwriting attested
  to a specific writer.
- Both `regular` and `final` forms are first-class — they are never
  merged into a single base letter. See [`docs/letters.md`]\
  (docs/letters.md) for the canonical 27-form enumeration.
- The crop must come from a scan that exists as a row in the upstream
  repo's `data/index/entries.jsonl`. If the page is not yet in upstream,
  add it there first — that is the canonical place for new source pages.

### Out of scope

- Printed or typeset letters.
- Composite glyphs (digraphs, niqqud-only marks, shin/sin pointed
  variants `שׁ`/`שׂ`).
- Crops where the source scan's license does not permit redistribution,
  commercial use, and derivatives. The crop is a derivative; the upstream
  must allow that. See `LICENSE.md` for the inheritance table.

### Per-image metadata (mandatory)

Every entry must include:

- `upstream.repo`, `upstream.source_id`, `upstream.entry_id`,
  `upstream.sha256`, `upstream.commit`, and `upstream.bbox` — pinning the
  exact scan and crop region used.
- `image.local_path` matching
  `data/letters/<writer_id>/<letter.name>/<entry_id>.<ext>`.
- `image.sha256` — full file SHA-256 (lowercase hex).
- `image.bytes` — file size in bytes.
- `image.mime_type` — `image/png`, `image/jpeg`, `image/webp`, or
  `image/tiff`. The extension on `local_path` must match.
- `image.width_px` and `image.height_px` — pixel dimensions.
- `image.background` — `original`, `white`, or `transparent`.
- `extraction.tool`, `extraction.tool_version`, `extraction.method`,
  `extraction.extracted_at`, `extraction.extracted_by`.
- `rights.*` — inherited from the upstream entry per the table in
  `LICENSE.md`. For `CC-BY-4.0` or `CC-BY-SA-4.0`,
  `attribution_required` must be `true` and both `attribution_text` and
  `attribution_url` must be populated.

Helpers — macOS:

```bash
shasum -a 256 FILE
stat -f%z FILE
file --mime-type -b FILE
sips -g pixelWidth -g pixelHeight FILE
```

Helpers — Linux (CI runs on Ubuntu, so these are the same shapes used in
CI debugging):

```bash
sha256sum FILE
stat -c%s FILE
file --mime-type -b FILE
identify -format "%w %h\n" FILE   # ImageMagick; or use Pillow from Python.
```

`scripts/validate_indexes.py` re-checks file integrity against the
recorded metadata on every run. Mismatches block CI.

### Accepted licenses

- `PDM-1.0`
- `CC0-1.0`
- `CC-BY-4.0`
- `CC-BY-SA-4.0` (ShareAlike inheritance still applies to the crop)
- Jurisdiction public-domain refs such as
  `LicenseRef-Public-Domain-Israel`,
  `LicenseRef-Public-Domain-Ukraine`.

### Rejected licenses

- `CC-BY-NC`, `CC-BY-NC-SA`, `CC-BY-ND`.
- "Research only", "permission required", "educational use only".
- Anything unknown, ambiguous, or where the upstream entry's
  `rights.verification_status` is not at least `primary_page_checked`.

## Naming

```text
writer_id = <slug_of_writers_canonical_name>     # e.g. chaim_nachman_bialik
entry_id  = <writer_id>__<letter.name>__v<NNNN>  # zero-padded variant
```

`<letter.name>` is the canonical slug from `docs/letters.md`. `<NNNN>` is
the zero-padded 4-digit counter monotonic per (writer_id, letter.name).

## What NOT to commit

The following are already in `.gitignore` and should never appear in a
diff:

- `.claude/` — local agent session state.
- `.DS_Store` — macOS Finder metadata.
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd` — Python bytecode caches.
- `.venv/`, `venv/`, `.pytest_cache/`.

If `git status` shows any of these as untracked, leave them untracked.
Do not `git add -f` to override the ignore.
