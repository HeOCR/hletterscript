# Licensing Policy

This repository is structured for compound licensing — the same model used
by [HeOCR/public-domain-hand-written-hebrew-scans][upstream].

[upstream]: https://github.com/HeOCR/public-domain-hand-written-hebrew-scans

## Repository-authored metadata

Metadata authored directly in this repository is dedicated to the public
domain under CC0 1.0 Universal (`CC0-1.0`):

https://creativecommons.org/publicdomain/zero/1.0/

To the extent possible under law, the repository contributors waive
copyright and related rights in this repository-authored metadata. The
canonical legal text is in [`LICENSE`](LICENSE).

This dedication includes:

- dataset structure documentation,
- writer and entry index metadata authored here,
- the JSON Schemas in `schemas/`,
- validation and release scripts in `scripts/`,
- generated metadata exports derived only from repository-authored
  metadata (e.g. `datapackage.json`, `CITATION.cff`, `NOTICE.md`).

The CC0 dedication does **not** extend to third-party image bytes,
upstream-owned descriptive text, or transcription bytes unless that
material is separately released under compatible terms.

## Per-letter image crops

Per-letter image bytes are **derivatives** of upstream scans hosted in
[HeOCR/public-domain-hand-written-hebrew-scans][upstream]. They are not
automatically covered by the metadata license. Each crop carries its own
entry-level rights record in `data/index/entries.jsonl`:

- `rights.license_expression` (SPDX expression or `LicenseRef-*`),
- `rights.commercial_use_allowed`,
- `rights.derivatives_allowed`,
- `rights.redistribution_allowed`,
- `rights.attribution_required`,
- `rights.attribution_text`,
- `rights.attribution_url`.

Consumers must use a crop according to the rights expressed in its own
entry record, not the repository-level metadata license.

### License inheritance

Because a per-letter crop is by definition a *derivative* of an upstream
scanned page, the crop's license is inherited from the upstream scan:

| Upstream scan license            | Per-letter crop license          | Attribution required?         |
| -------------------------------- | -------------------------------- | ----------------------------- |
| `CC0-1.0`                        | `CC0-1.0`                        | no                            |
| `PDM-1.0`                        | `PDM-1.0`                        | no                            |
| `LicenseRef-Public-Domain-*`     | same `LicenseRef-Public-Domain-*`| no                            |
| `CC-BY-4.0`                      | `CC-BY-4.0`                      | yes (text + url required)     |
| `CC-BY-SA-4.0`                   | `CC-BY-SA-4.0`                   | yes (text + url required)     |
| Anything else (NC, ND, unknown)  | **not ingestable**               | n/a                           |

The ShareAlike obligation propagates: anyone who redistributes a further
adaptation of a `CC-BY-SA-4.0` crop must release the adaptation under
`CC-BY-SA-4.0` or a compatible later version. Mere aggregation of
`CC-BY-SA-4.0` crops alongside public-domain or CC-BY crops in a release
bundle is not an adaptation, so the bundle itself does not need to be
relicensed.

## Release bundles

Remix-friendly public release bundles published from this repository
should include only entries where:

- redistribution is allowed,
- commercial use is allowed,
- derivatives are allowed,
- both upstream scan rights and inherited crop rights have been verified.

If a release bundle contains a mixture of public-domain, CC0, CC-BY, and
CC-BY-SA crops, the release must keep per-entry license metadata and
include attribution where required. Do not describe such a bundle as
having a single uniform crop license unless every included crop has the
same license.

## Exclusions

Do not include per-letter image crops with any of the following terms in
release bundles, and do not ingest upstream scans carrying these terms:

- non-commercial only,
- no derivatives,
- research-only,
- permission required,
- unknown rights,
- inaccessible source evidence.

This is stricter than the upstream scans repo's exclusion list because
this repository's deliverable is **only useful if downstream synthetic
document generators can redistribute and remix it**.
