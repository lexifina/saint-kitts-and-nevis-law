# Structure

The law of Saint Kitts and Nevis, laid out by type and year. No folder holds more than 1,000 entries.

```
constitution/                         The Constitution (Schedule 1 to the Saint Christopher and Nevis Constitution
                                      Order 1983, SI 1983/881), one file per section or schedule
constitution-order/                   The Order's own sections 1 to 4 and the transitional provisions in its schedule 2
laws/cap-<a>-<b>-<slug>/              A chapter of the Laws of Saint Christopher and Nevis, Revised Edition, as at the
                                      day its title page gives (Cap. 11.08 is laws/cap-11-08-...), one file per section
nevis/laws/cap-<a>-<b>-<slug>/        A Nevis Ordinance chapter (Cap. 3.02 (N)) of the Revised Edition
acts/<year>/<NNN>-<slug>/             An Act of Parliament as passed: Act No. NNN of <year>
statutory-rules-and-orders/<year>/<NNN>-<slug>/
                                      A statutory rule or order (regulations, orders, rules) as made: S.R.O. NNN of <year>
```

`constitution/` and `constitution-order/` keep the paths of the first build (October 2026), which global-law and the
tags already use. Regional law that applies in the Federation (OECS, CARICOM, the Eastern Caribbean Supreme Court) goes
in its own folder (`oecs/`, `caricom/`, `ecsc/`) when a copy with a text layer and a reliable in-force day is found.

Files in each `laws/`, `acts/` and `statutory-rules-and-orders/` folder: `front-matter.md` (the chapter's list of
consolidated laws and arrangement of sections, or an Act's title, long title and enacting words), `section-NNN.md` (one
per section, `section-033a.md` for section 33A, with its marginal note as the first line), `schedule-NN.md` (one per
schedule, in order) and, for a Revised Edition chapter, `subsidiary-legislation.md` (the subsidiary legislation printed
under the chapter, in one file). Where the text layer has no section numbering to split on, the whole text is in
`text.md`.

## Commits

One commit per version, dated noon America/St_Kitts (UTC-04:00) on the day the version took effect. Every commit
carries:

- `In-force:` the day (YYYY-MM-DD) and `In-force-basis:` how it was found;
- `Source-status:` `secondary copy (<source>, <address>)` for every text taken from a copy held by someone other than
  the Government of Saint Kitts and Nevis (FAOLEX, WIPO Lex);
- `Text-source:` `PDF text layer`: the publisher's own text layer. No OCR is run for new material; PDFs that are page
  scans are held back and listed in `data/held.json`;
- `Source:` the PDF's address and `Source-sha256:` its hash; `Source-page:` the catalogue record it was listed on.

The author of each commit is the law that made the version: `Act No. N of YYYY`, `S.R.O. No. N of YYYY`, or, for a
Revised Edition chapter, `Laws of Saint Christopher and Nevis, Revised Edition (law as at <day>)`; the committer is
Lexifina.

### Revised Edition dates

Each Revised Edition chapter states on its title page, and in its running head ("Revision Date"), the day whose law it
shows ("Revised Edition showing the law as at 31 December 2020"). The chapter is dated on that day: its text is the
consolidated text in force then. `Consolidates:` lists the laws its title page says it consolidates, with their days
in force.

### Acts and S.R.O.s

An Act or S.R.O. is dated on a commencement day stated in its text; or, when it states none, on its day of publication
in the Official Gazette, printed under its long title ("[Published 26th November 2020, Official Gazette No. 86 of
2020.]"), since an enactment comes into operation on publication unless it provides otherwise. An instrument that comes
into force "on a day to be fixed by the Minister by Order" is held back until that order is found.
