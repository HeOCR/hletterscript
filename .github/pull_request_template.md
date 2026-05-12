<!--
  hletterscript PR template.
  - Delete sections that don't apply.
  - All checkboxes are mandatory unless you explicitly note why one
    does not apply (e.g. "docs-only change, no entries touched").
-->

## Summary

<!-- 1-3 bullets: what changed and why. -->

## Type of change

- [ ] New writer(s) / new per-letter image entries (ingest)
- [ ] Schema or validator change
- [ ] Release tooling / CI change
- [ ] Documentation / policy
- [ ] Refactor / chore (no behaviour change)

## Pre-merge checklist

- [ ] `python3 scripts/validate_indexes.py` passes locally.
- [ ] `python3 scripts/generate_release_artifacts.py` was re-run after
      any change to `data/index/*.jsonl` or `scripts/release_recipe.json`,
      and the regenerated `NOTICE.md` / `CITATION.cff` / `datapackage.json`
      are staged in this PR.
- [ ] `python3 -m pytest` passes locally.
- [ ] `git diff --check` shows no whitespace issues.
- [ ] If image files were added/changed, they are tracked via Git LFS
      (see `.gitattributes`).

## Rights / licensing

<!-- Only required for PRs that add entries. -->
<!-- Confirm: every new entry's rights block matches the inheritance -->
<!-- table in LICENSE.md (specifically, attribution_required and -->
<!-- license_expression are aligned with the upstream scan). -->

## Notes for reviewers

<!-- Anything load-bearing the reviewer should focus on. Paste the -->
<!-- validator output and pytest summary if this PR touches data or -->
<!-- tooling. -->
