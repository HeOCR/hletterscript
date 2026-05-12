# Hebrew Letter Enumeration

This file is the human-readable companion to the `letter` block in
`schemas/entry.schema.json`. The schema is authoritative; this table is meant
to be readable and stays in sync with it.

Per-letter image entries use lowercase ASCII `letter.name` slugs in
`entry_id`s, file paths, and statistics. The five letters that take a final
form get two distinct slugs (`kaf` / `kaf_final`, etc.) — final-form glyphs
are never collapsed into their base letter, because handwriting style varies
between the two.

| `letter.name`   | `letter.codepoint` | `letter.unicode_char` | `letter.form` | Hebrew name |
| --------------- | ------------------ | --------------------- | ------------- | ----------- |
| `alef`          | `U+05D0`           | א                     | `regular`     | אלף         |
| `bet`           | `U+05D1`           | ב                     | `regular`     | בית         |
| `gimel`         | `U+05D2`           | ג                     | `regular`     | גימל        |
| `dalet`         | `U+05D3`           | ד                     | `regular`     | דלת         |
| `he`            | `U+05D4`           | ה                     | `regular`     | הא          |
| `vav`           | `U+05D5`           | ו                     | `regular`     | וו          |
| `zayin`         | `U+05D6`           | ז                     | `regular`     | זין         |
| `het`           | `U+05D7`           | ח                     | `regular`     | חית         |
| `tet`           | `U+05D8`           | ט                     | `regular`     | טית         |
| `yod`           | `U+05D9`           | י                     | `regular`     | יוד         |
| `kaf_final`     | `U+05DA`           | ך                     | `final`       | כף סופית    |
| `kaf`           | `U+05DB`           | כ                     | `regular`     | כף          |
| `lamed`         | `U+05DC`           | ל                     | `regular`     | למד         |
| `mem_final`     | `U+05DD`           | ם                     | `final`       | מם סופית    |
| `mem`           | `U+05DE`           | מ                     | `regular`     | מם          |
| `nun_final`     | `U+05DF`           | ן                     | `final`       | נון סופית   |
| `nun`           | `U+05E0`           | נ                     | `regular`     | נון         |
| `samekh`        | `U+05E1`           | ס                     | `regular`     | סמך         |
| `ayin`          | `U+05E2`           | ע                     | `regular`     | עין         |
| `pe_final`      | `U+05E3`           | ף                     | `final`       | פא סופית    |
| `pe`            | `U+05E4`           | פ                     | `regular`     | פא          |
| `tsadi_final`   | `U+05E5`           | ץ                     | `final`       | צדי סופית   |
| `tsadi`         | `U+05E6`           | צ                     | `regular`     | צדי         |
| `qof`           | `U+05E7`           | ק                     | `regular`     | קוף         |
| `resh`          | `U+05E8`           | ר                     | `regular`     | ריש         |
| `shin`          | `U+05E9`           | ש                     | `regular`     | שין         |
| `tav`           | `U+05EA`           | ת                     | `regular`     | תו          |

## Letters this dataset does NOT split out

- **Pointed (niqqud) vowel marks** (`U+05B0`–`U+05BC`) and the rafe / sof
  pasuq marks (`U+05BF`, `U+05C0`) are diacritics, not letters, and are
  out of scope for the per-letter image corpus.
- **Yiddish digraphs** `װ` (`U+05F0`), `ױ` (`U+05F1`), `ײ` (`U+05F2`) are
  composed glyphs; they are out of scope. Underlying Yiddish handwriting
  that uses the standard 27 forms above is in scope.
- **Shin / sin dot variants** `שׁ` (`U+FB2A`) and `שׂ` (`U+FB2B`) are normalised
  to the bare `shin` slug. The pointed variant lives in `letter.notes` if
  the original page has the dot.

## File-path convention

Per-letter image files live at:

```text
data/letters/<writer_id>/<letter_name>/<entry_id>.<ext>
```

For example, the first verified alef variant from writer `chaim_nachman_bialik`:

```text
data/letters/chaim_nachman_bialik/alef/chaim_nachman_bialik__alef__v0001.png
```

`<entry_id>` always matches `^<writer_id>__<letter_name>__v[0-9]{4}$` and is
enforced by `schemas/entry.schema.json` and `scripts/validate_indexes.py`.
