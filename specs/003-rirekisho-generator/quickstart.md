# Quickstart: 履歴書 Generator

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/openapi.yaml](./contracts/openapi.yaml)

How to bring the stack up and prove this feature works. A validation guide: what
to run and what to expect, not how anything is built.

Every check here extracts the **text** back out of a generated PDF and asserts
on it. Asserting on bytes or on a file existing would pass for a document full
of hollow boxes, which is exactly what a missing Japanese font produces.

## Prerequisites

Everything from [feature 001's quickstart](../001-master-career-profile/quickstart.md).
No new configuration — this feature calls no external service.

```bash
docker compose up -d postgres

cd apps/api
uv run alembic upgrade head          # adds date of birth and address to the profile
uv run uvicorn app.main:app --reload

cd apps/web
pnpm gen:api                         # now generates three clients, one per contract
pnpm dev
```

Throughout, `$TOKEN` is a verified session and `$A=localhost:8000/api/v1`.

A helper for reading a produced document:

```bash
pdftext() { uv run python -c "
import sys
from pypdf import PdfReader
print('\n'.join(p.extract_text() or '' for p in PdfReader(sys.argv[1]).pages))
" "$1"; }
```

---

## Scenario 0 — The Japanese font is embedded

Run this first. If it fails, every other check below is meaningless, because the
document will be produced, correctly sized, and unreadable.

```bash
curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' -o /tmp/r.pdf

pdftext /tmp/r.pdf | head -5
```

**Expect** the heading 履歴書 to appear **as text**. If the output is empty, or
shows boxes or question marks, the font was not embedded — the file is a PDF of
nothing readable, and no amount of layout work fixes it.

---

## Scenario 1 — A profile becomes a 履歴書 (User Story 1, P1)

With a profile holding an identity, one education entry and two work
experiences, one of them ongoing:

```bash
curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' -D /tmp/h.txt -o /tmp/r.pdf

pdftext /tmp/r.pdf
```

**Expect**, in this order:

| Check | Expected |
|---|---|
| 学歴 rows | The education entry, 入学 then 卒業 |
| 職歴 rows | Both roles, oldest first, each 入社 then 退社 |
| The ongoing role | 現在に至る rather than a date |
| The last line | 以上 |
| Response headers | `X-Snapshot-Id` present (FR-016) |

**And the traceability check**, which is what makes the document trustworthy
rather than merely plausible:

```bash
SNAP=$(grep -i '^x-snapshot-id' /tmp/h.txt | tr -d '\r' | cut -d' ' -f2)
curl -s "$A/profile/snapshots/$SNAP" -H "Authorization: Bearer $TOKEN" | jq '.captured_entry_ids | length'
```

**Expect** a count matching the entries that produced rows. Then edit one of
those entries and read the snapshot again — it must still show what the document
was based on, not what the profile says now.

---

## Scenario 2 — The conventions the user chose (User Story 2, P2)

```bash
for c in seireki wareki; do
  curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d "{\"date_convention\":\"$c\"}" -o /tmp/$c.pdf
done

pdftext /tmp/seireki.pdf | grep -E '20[0-9]{2}年'
pdftext /tmp/wareki.pdf  | grep -E '令和|平成'
```

**Expect** each to match its own convention and neither to match the other's. A
document mixing the two is a failure of FR-019 even if every date is correct.

```bash
curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"paper_size":"b5"}' -o /tmp/b5.pdf
```

**Expect** B5 page dimensions and the same text content as the A4 version.
Presentation differs; content does not.

### Preview matches the download

```bash
curl -s -X POST "$A/profile/documents/rirekisho?preview=true" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' -D /tmp/p.txt -o /tmp/preview.pdf

grep -i '^content-disposition' /tmp/p.txt     # inline
diff <(pdftext /tmp/preview.pdf) <(pdftext /tmp/r.pdf) && echo "identical content"
```

**Expect** the dispositions to differ and the text to be identical. A user must
never preview one document and download another.

---

## Scenario 3 — Nothing invented to fill a blank (User Story 3, P3)

The scenario that matters most, and the one most easily broken by a later change
that tries to be helpful.

With a deliberately incomplete profile — no education, no address, no date of
birth:

```bash
pdftext /tmp/r.pdf | grep -c '学歴'          # the heading exists
pdftext /tmp/r.pdf | grep -cE '入学|卒業'    # expect 0 — no rows, no placeholder
```

**Expect** the section present and empty. Not a sample row, not "N/A", not a
plausible guess.

```bash
curl -s $A/profile/documents/rirekisho/readiness -H "Authorization: Bearer $TOKEN" | jq .
```

**Expect** `can_generate: true`, with `missing_optional` naming the date of
birth and address. Blank fields are reported rather than silently left, so
nothing is a surprise after printing (FR-022c).

### A profile with no name

**Expect** `422`, naming the missing field. A document with a blank name is not
a 履歴書, and producing one would waste the user's time more expensively than
refusing (FR-015).

---

## Scenario 4 — Disclosure is respected

The first real test of a rule set three features ago: a flag defaulting false
in a table nothing had yet read.

With a profile holding a nationality and a visa type, both undisclosed:

```bash
pdftext /tmp/r.pdf | grep -cE '国籍|在留|ビザ'
```

**Expect** `0`. Not blank labels — absent entirely.

```bash
curl -s -X PUT $A/profile/japan -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nationality":"Example nationality","disclose_nationality":true}' > /dev/null

curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' -o /tmp/disclosed.pdf
pdftext /tmp/disclosed.pdf | grep -c 'Example nationality'
```

**Expect** `1`, appearing in 本人希望記入欄. Then withdraw the disclosure,
regenerate, and expect it gone again (FR-021).

**Repeat for every flag.** This is the one place where a mistake publishes
someone's immigration status, so each is checked rather than assumed to follow
from the first.

---

## Scenario 5 — English entries are reported, not translated

```bash
curl -s $A/profile/documents/rirekisho/readiness -H "Authorization: Bearer $TOKEN" \
  | jq '.entries_without_japanese'
```

**Expect** the English entries listed with labels the user will recognise.

```bash
pdftext /tmp/r.pdf | grep -c 'Example Corp'
```

**Expect** `1` — the English appears as written. **Nothing in the document may
be Japanese that the user did not write.** The system reports what has no
Japanese version; it does not supply one (research.md R-001).

---

## Scenario 6 — A long history keeps every entry

With a profile holding more roles than fit two pages:

```bash
curl -s -X POST $A/profile/documents/rirekisho -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}' -D /tmp/h2.txt -o /tmp/long.pdf

grep -i '^x-document-pages' /tmp/h2.txt
pdftext /tmp/long.pdf | grep -c '入社'
```

**Expect** more than two pages, and a count of 入社 rows matching the number of
work experiences in the profile. **No entry may be dropped or shortened to fit**
(SC-007a) — losing someone's career to a layout constraint is worse than an
unusual page count.

---

## Scenario 7 — No gender field

```bash
pdftext /tmp/r.pdf | grep -c '性別'
```

**Expect** `0`. Not an empty box inviting completion — absent (FR-022).

---

## What "done" looks like

| Check | Proves |
|---|---|
| **Scenario 0** | **The Japanese font is embedded; everything else is meaningful** |
| Scenario 1 | The table follows the conventions, and the document is traceable |
| Scenario 2 | Conventions change presentation only; preview matches download |
| **Scenario 3** | **Nothing is invented to fill a conventional blank** |
| **Scenario 4** | **Undisclosed fields never appear — gate G5** |
| Scenario 5 | English is reported, never translated |
| Scenario 6 | No entry lost to a page count |
| Scenario 7 | No gender field |
| `uv run pytest` and `pnpm test` green | The suites |

Field-level rules these assert are in [data-model.md](./data-model.md); the
routes in [contracts/openapi.yaml](./contracts/openapi.yaml).
