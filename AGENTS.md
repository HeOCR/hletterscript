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
[`schemas/entry.schema.json`](schemas/entry.schema.json). The release
runbook is [`docs/release_process.md`](docs/release_process.md).

[upstream]: https://github.com/HeOCR/public-domain-hand-written-hebrew-scans

## First-time setup

Run once per clone:

```bash
git lfs install
git lfs pull
python3 -m pip install -r requirements-dev.txt
```

`data/letters/**` image files are tracked via Git LFS (see
`.gitattributes`). Without `git lfs pull` you have pointer files, not
images, and the validator's file-integrity check will fail.

**Python 3.11+ is required** — the validator uses `hashlib.file_digest`.
CI pins 3.12.

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

### Optional upstream cross-validation

If you have a local clone of the upstream scans repo, pass
`--upstream-path` to validate `upstream.sha256` and `upstream.bbox`
against the live upstream entry records:

```bash
python3 scripts/validate_indexes.py \
  --upstream-path ../public-domain-hand-written-hebrew-scans
```

CI checks out the upstream repo as a sibling and runs the validator with
`--upstream-path` automatically, so any mismatch (upstream re-encode,
bbox-out-of-bounds) blocks the PR.

### Tests-only flag

`--repo-root PATH` overrides the file-integrity check's repo root. It
exists for the pytest fixtures and is not part of the ingest workflow.

## Release artefacts

`NOTICE.md`, `CITATION.cff`, and `datapackage.json` at the repo root are
generated deterministically from `data/index/*.jsonl` and
`scripts/release_recipe.json`. Do not edit them by hand.

Two timestamps with deliberately different semantics:

- `datapackage.json::released_at` = `max(extraction.extracted_at)` —
  the corpus-state timestamp. Bumps automatically on every ingest PR.
  When the corpus is empty it falls back to
  `release_recipe.json::initial_release_date`.
- `CITATION.cff::date-released` = `release_recipe.json::version_released_date`
  — stable per version. Only changes when a human bumps `version`
  (see [`docs/release_process.md`](docs/release_process.md)).

This means an ingest PR will bump `released_at` but not `date-released`.
That is intentional: citations stay reproducible while
corpus-freshness metadata moves with reality.

Regenerate by running `python3 scripts/generate_release_artifacts.py`
from the repo root.

## GitHub workflow

- One PR per coherent change. Batching is fine when tightly coupled
  (tooling change + the docs that describe it); avoid batching
  unrelated work.
- Open PRs non-draft. The PR template's checkboxes are required.
- Use the `git` and `gh` CLIs. Do not push to `main` directly.
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
  add it there first.

### Out of scope

- Printed or typeset letters.
- Composite glyphs (digraphs, niqqud-only marks, pointed shin/sin
  variants `שׁ`/`שׂ`).
- Crops from scans whose license does not permit redistribution,
  commercial use, and derivatives.

### Per-image metadata (mandatory)

Every entry must include:

- `upstream.source_id`, `upstream.entry_id`, `upstream.sha256`,
  `upstream.commit` (40-char SHA — tag refs go in `upstream.release_tag`
  instead), `upstream.bbox`.
- `image.local_path` matching
  `data/letters/<writer_id>/<letter.name>/<entry_id>.<ext>`.
- `image.sha256` — full file SHA-256 (lowercase hex).
- `image.bytes` — file size in bytes.
- `image.mime_type` — `image/png`, `image/jpeg`, `image/webp`, or
  `image/tiff`. Extension on `local_path` must match.
- `image.width_px` and `image.height_px`.
- `image.background` — `original`, `white`, `black`, `gray`,
  `binarized`, or `transparent`. (`transparent` requires an
  alpha-capable mime type; the schema rejects `transparent` + JPEG.)
- `extraction.tool`, `extraction.tool_version` (SemVer or `git describe`
  output), `extraction.method`, `extraction.extracted_at`,
  `extraction.extracted_by`.
- `rights.*` — inherited from the upstream entry per the table in
  `LICENSE.md`. `rights.rights_basis` must match
  `rights.license_expression` per the validator's `LICENSE_BASIS_MAP`.

Helpers — macOS:

```bash
shasum -a 256 FILE
stat -f%z FILE
file --mime-type -b FILE
sips -g pixelWidth -g pixelHeight FILE
```

Helpers — Linux (CI runs on Ubuntu, so these are the same shapes used
in CI debugging):

```bash
sha256sum FILE
stat -c%s FILE
file --mime-type -b FILE
identify -format "%w %h\n" FILE   # ImageMagick; or use Pillow from Python.
```

`scripts/validate_indexes.py` re-checks file integrity against the
recorded metadata on every run. Mismatches block CI.

### Accepted licenses

- `PDM-1.0` → `rights_basis: public_domain`
- `CC0-1.0` → `rights_basis: cc0`
- `CC-BY-4.0` → `rights_basis: cc_by` (attribution required)
- `CC-BY-SA-4.0` → `rights_basis: cc_by_sa` (attribution required;
  ShareAlike applies to the crop, since the crop is an adaptation)
- `LicenseRef-Public-Domain-Israel` → `rights_basis: public_domain`
- `LicenseRef-Public-Domain-Ukraine` → `rights_basis: public_domain`

The validator's `LICENSE_BASIS_MAP` is the single source of truth for
this mapping. Adding a license means updating that map AND this list
AND `scripts/release_recipe.json::license_names`/`license_urls`.

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

`<letter.name>` is the canonical slug from `docs/letters.md`. `<NNNN>`
is the zero-padded 4-digit counter monotonic per
`(writer_id, letter.name)`.

### Writer disambiguation

On Latin-name collision (e.g. two writers named "Yosef Haim"), append
the birth year to disambiguate: `yosef_haim_1834`, `yosef_haim_1902`.
Fallbacks when birth year is unknown:

1. Death year: `yosef_haim_d1942`.
2. Period start year: `yosef_haim_p1880`.
3. Provider authority ID: `yosef_haim_viaf12345678` — last resort, only
   when none of the above are knowable.

Always record the rationale in the writer's `ingest.agent_notes`.

## What NOT to commit

The following are already in `.gitignore` and should never appear in a
diff:

- `.claude/` — local agent session state.
- `.DS_Store` — macOS Finder metadata.
- `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd` — Python bytecode caches.
- `.venv/`, `venv/`, `.pytest_cache/`.

If `git status` shows any of these as untracked, leave them untracked.
Do not `git add -f` to override the ignore.
