# Saint Kitts and Nevis: law history in git

The law of Saint Kitts and Nevis as a git history: one file per provision, one commit per law on the day it took effect, and the law that made each change as the commit's author. `git blame` names the law behind every paragraph; `git log` lists every change; picking a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law).

**What is in it now (a first build, not complete)**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitution/` | The Constitution of Saint Christopher and Nevis (schedule 1 to SI 1983/881), as made: sections 1 to 120 and schedules 1 to 5 | 1 | As made, in effect 19 September 1983. Later amendments are not applied. |
| `constitution-order/` | The Saint Christopher and Nevis Constitution Order 1983: sections 1 to 4 and the transitional provisions (schedule 2 to the Order) | 1 | As made, in operation 23 June 1983 |

**Language.** English, the official language. The scan is of the English text as printed by Her Majesty's Stationery Office.

**Source.** [legislation.gov.uk](https://www.legislation.gov.uk/uksi/1983/881/made), The National Archives: *The Saint Christopher and Nevis Constitution Order 1983* (SI 1983/881), as made. The Constitution is schedule 1 to the Order. Retrieved 30 October 2026. **The text was recovered by optical character recognition (OCR).** legislation.gov.uk holds this Order only as an image-only scan (122 pages, no text layer), so the words in this repository were read from the scan with Tesseract 5.4 (English), then checked: every word against a dictionary, and a sample of pages against the scan. A few misreadings were corrected by hand (listed in `REPRODUCE.md`, under decisions), but a full proofread has not been done. Where this text matters, read the scan at the source link above.

## Dates

The Constitution is dated 19 September 1983, the day it came into effect (section 3 of the Order). The Order's own sections and its schedule 2 are dated 23 June 1983, when the Order came into operation (section 1(2)). Each act has a single version because the source is the Order as made: this is not the current Constitution, and later amendments (including those made by Saint Kitts and Nevis since independence) are not in this repository.

## How it is checked

Every version is read back from git on the day it took effect and on the day before (`tools/check_repo.py`) and must match `corpus.json`; results are in `REPRODUCE.md`.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist (`<law key>@legislation.gov.uk.invalid`). Both acts are credited to SI 1983/881. The committer is always Lexifina.

## Limits

Not complete and not current. Missing: every amendment since 1983; the Preamble; schedule 6 to the Constitution (provisions applied with modifications to the Nevis Island Assembly); the explanatory note; the marginal notes (section headings), which the OCR could not read reliably; and the chapter and part headings. The text is OCR output and may contain misreadings. The Government of Saint Kitts and Nevis (Attorney General's Chambers, lawcommission.gov.kn) publishes the laws of the Federation under terms that forbid reuse, so nothing is taken from it.
