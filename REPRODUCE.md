# How this repository was made (Saint Kitts and Nevis)

This file is written by the build on 2026-10-30, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| legislation.gov.uk: The Saint Christopher and Nevis Constitution Order 1983 (as made), scanned PDF | <http://www.legislation.gov.uk/uksi/1983/881/pdfs/uksi_19830881_en.pdf> | 2026-10-30 | Open Government Licence v3.0 |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `constitution` | The Constitution of Saint Christopher and Nevis (schedule 1 to SI 1983/881), as made | 1 | 1983-09-19 to 1983-09-19 |
| `constitution-order` | The Saint Christopher and Nevis Constitution Order 1983: sections 1 to 4 and the transitional provisions in schedule 2 | 1 | 1983-06-23 to 1983-06-23 |

The build made 2 commits:

| Commits | Kind |
| ---: | --- |
| 2 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `future`: laws not yet in force on 2026-10-30.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 1 laws in the record.
- 3 tags.

## Dates

Each commit is dated at noon (America/St_Kitts) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: The Order came into operation on 23 June 1983 (section 1(2)); the Constitution set out in its schedule 1 came into effect on 19 September 1983 (section 3). https://www.legislation.gov.uk/uksi/1983/881/made

## How the history is built

`tools/build.py` turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/SCHEMA.md`.

- Corpus: sha256 `029f3559ddb0e6b211eec84e838baaaf6afe25fd0988b554b78635ed36b4530f` (270118 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `a4faa25af85facb64b956b372f6b528aafdd7ec1`, `check.py` `3e59cb6f05eccb94a9ec14431a7f6781221e83ef`, `on.py` `644a6c0857fbcc72562032b58d57aa113fee0641`.
- Python 3.12.10; git version 2.46.0.windows.1.

## Checks

Not yet run for this build.

No second build of this corpus has been compared yet.

## Decisions made by hand

- The text is the Constitution as made in 1983. Later amendments are not applied, because the source holds only the 1983 Order; the repository is therefore a single version per act and is not the current Constitution.
- The scan has no text layer. It was read with Tesseract 5.4 (English, 300 dpi, page segmentation mode 3); mean word confidence 95.9 percent. Marginal notes (section headings) were left out because they could not be read reliably; chapter and part headings were left out of section units.
- Spot checks against the scan found and corrected: Chapter II misread as Chapter I (schedule 1); a marginal note merged into schedule 3 paragraph 1 (corrected by hand from the scan); and a short list of misread words (for example electud, disssolution, incidenial) corrected by hand. Every word was checked against a dictionary; a full proofread against the scan has not been done.
- Schedules 1 to 5 to the Constitution are one unit each. Schedule 6 to the Constitution (provisions applied with modifications), the Preamble and the explanatory note are not included.
- The Constitution takes effect on 19 September 1983 (Order, section 3); the Order itself came into operation on 23 June 1983 (section 1(2)). Both versions are credited to SI 1983/881.

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- Claude Code (Claude Sonnet 5.5) wrote the extraction code and made the hand corrections listed in decisions. The text itself was recovered by Tesseract OCR; no model wrote or summarised legal text.
