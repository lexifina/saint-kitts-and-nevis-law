"""Append secondary copies of Saint Kitts and Nevis legislation to the saint-kitts-and-nevis-law repository as git
fast-import commits on main (no history rewritten).

python -I tools/sk_build.py <repo> [--dry]
Input: leg/fetched.json + leg/pdf/ (tools/acquire.py). Only PDFs with a text layer are used; no OCR. A PDF whose text
repeats the Attorney General's Chambers' no-reproduction terms is skipped.
Layout (STRUCTURE.md): laws/cap-<a>-<b>-<slug>/ (Revised Edition chapters), nevis/laws/cap-<a>-<b>-<slug>/ (Nevis
Ordinances, Revised Edition), acts/<year>/<NNN>-<slug>/ (Acts as passed), statutory-rules-and-orders/<year>/<NNN>-<slug>/
(S.R.O.s as made), oecs/ and caricom/ (regional treaties); one file per section.
One commit per instrument, noon America/St_Kitts on its in-force day, with In-force and In-force-basis trailers.
Instruments whose Source trailer is already on main are skipped."""
import json, os, re, subprocess, sys, datetime, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date(2026, 11, 26)
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())}); MONTHS["sept"] = 9
HELD = []
DAY = r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:day\s+)?(?:of\s+)?([A-Za-z]+)\.?,?\s+(\d{4})"
NOTICE = re.compile(r"(?i)(may not be reproduc|no part of (?:this|these).{0,80}reproduc|reproduc\w*[^.]{0,80}(?:prohibit|forbid|without (?:the )?(?:prior )?(?:written )?(?:permission|consent))|terms of use)")
POLICY = re.compile(r"(?i)\b(plan|strategy|policy|contributions?|programme|report|framework|guidelines?)\b")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^the\s+", "", s.strip())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70].strip("-") or "untitled"


def mkdate(dd, mm, yy):
    mm = mm.lower().rstrip(".")
    if mm not in MONTHS:
        return None
    try:
        return datetime.date(int(yy), MONTHS[mm], int(dd))
    except ValueError:
        return None


def numkey(n):
    m = re.match(r"(\d+)([A-Z]*)", n)
    return (int(m.group(1)), m.group(2))


def page_lines(fn):
    import pymupdf
    d = pymupdf.open(fn)
    pages = [[ln.rstrip() for ln in p.get_text().replace("\r", "").replace(" ", " ").split("\n")] for p in d]
    cnt = collections.Counter(s for pg in pages for s in {x.strip() for x in pg} if s)
    run = {s for s, c in cnt.items() if c >= max(3, 0.4 * len(pages)) and len(s) < 120
           and not re.fullmatch(r"[(\[]?[0-9a-zA-Z]{1,5}[)\].]?[.;,]?|[-_—.\s]+|and|or|—|PART [IVXL0-9]+", s)}
    out = []
    for pg in pages:
        hits = [i for i, ln in enumerate(pg) if ln.strip() in run]
        keep = [ln for i, ln in enumerate(pg) if ln.strip() not in run and
                not ((i < 14 or i >= len(pg) - 10 or any(abs(i - h) <= 3 for h in hits))
                     and re.fullmatch(r"\s*\d{1,4}\s*", ln))]
        out.append("\n".join(keep))
    t = "\n".join(out)
    # ligatures in the text layer ("Ofﬁ cial"): expand, and drop the space the layer puts after them inside a word
    t = re.sub(r"(ﬁ|ﬂ|ﬀ|ﬃ|ﬄ) (?=[a-z])", r"\1", t)
    t = t.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip() + "\n", d.page_count


SEC_ALONE = re.compile(r"^[ \t]*(\d{1,3}[A-Z]{0,2})\.[ \t]*$", re.M)               # Revised Edition: "1." on its own line
SEC_INLINE = re.compile(r"^[ \t]*(\d{1,3}[A-Z]{0,2})\.[ \t]*(?=[(A-Z\"'“])", re.M)  # "12. (1) The ..." / "12. Heading."
ART = re.compile(r"^\s*ARTICLE\s+(\d{1,3}[A-Z]?)\b", re.M | re.I)
SCHED = re.compile(r"^\s*(?:(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+)?SCHEDULE(?:\s+[0-9IVX]+[A-Z]?)?\s*(?:\(.{0,60}\))?\s*$", re.M | re.I)


def run_of(ms):
    starts = [i for i, m in enumerate(ms) if m.group(1) == "1"]
    best = []
    for s in starts:
        seq, last = [ms[s]], numkey("1")
        for m in ms[s + 1:]:
            k = numkey(m.group(1))
            if k > last and k[0] <= last[0] + 12:
                seq.append(m); last = k
        if len(seq) > len(best) or (len(seq) == len(best) and seq[-1].start() - seq[0].start() > best[-1].start() - best[0].start()):
            best = seq
    return best


def heading_start(text, pos):
    """Move a section start back over its marginal note (one or two short lines ending with '.')."""
    before = text[:pos].rstrip("\n")
    lines = before.split("\n")
    take = 0
    for ln in reversed(lines[-2:]):
        s = ln.strip()
        if s and len(s) < 90 and not s.startswith("(") and s[0].isupper() and not re.search(r"[;:,—-]$", s):
            take += 1
            if s.endswith("."):
                break
        else:
            break
    if take:
        return len("\n".join(lines[:-take])) + 1 if len(lines) > take else 0
    return pos


SEC_ANY = re.compile(r"^[ \t]*(\d{1,3}[A-Z]{0,2})\.(?:[ \t]*$|[ \t]*(?=[(A-Z\"'\u201c]))", re.M)


def split_sections(text, articles=False, revised=False):
    margin = False
    if articles:
        seq = run_of(list(ART.finditer(text)))
        fname = "article"
    else:
        # candidate runs from every "1." in both styles; the body, not the arrangement of sections, has long sections
        cands = []
        for style, ms in (("alone", list(SEC_ALONE.finditer(text))), ("inline", list(SEC_INLINE.finditer(text))), ("any", list(SEC_ANY.finditer(text)))):
            for i, m in enumerate(ms):
                if m.group(1) == "1":
                    sq = run_of(ms[i:])
                    if len(sq) >= 2:
                        gaps = sorted(sq[j + 1].start() - sq[j].start() for j in range(len(sq) - 1))
                        cands.append((len(sq), gaps[len(gaps) // 2], style, sq))
        seq = []
        if cands:
            top = max(c[0] for c in cands)
            ok = [c for c in cands if c[0] >= 0.6 * top and c[1] >= 60]
            if ok:
                best = max(ok, key=lambda c: c[0] * min(c[1], 2000))
                seq = best[3]
                # marginal note before the number ("Short title.\n1.\nThis Act ...") or after it ("1.\nShort title.\n...")
                after = before = 0
                for m in seq:
                    if m.group(0).strip().endswith("."):
                        nxt = text[m.end():m.end() + 200].lstrip("\n").split("\n", 1)[0].strip()
                        prv = text[:m.start()].rstrip("\n").rsplit("\n", 1)[-1].strip()
                        if nxt and len(nxt) < 90 and nxt.endswith(".") and not nxt.startswith("("):
                            after += 1
                        elif prv and len(prv) < 90 and prv.endswith(".") and not prv.startswith("("):
                            before += 1
                margin = before > after
        fname = "section"
    if len(seq) < 2:
        return None
    starts = [heading_start(text, m.start()) if margin else m.start() for m in seq]
    files = []
    head = text[:starts[0]].strip()
    if head:
        files.append(("front-matter.md", head))
    sub = re.search(r"^\s*SUBSIDIARY LEGISLATION\s*$", text[seq[-1].start():], re.M)
    end_body = seq[-1].start() + sub.start() if sub else len(text)
    sm = [m for m in SCHED.finditer(text) if seq[-1].start() < m.start() < end_body]
    end_body_s = sm[0].start() if sm else end_body
    seen = set()
    for i, m in enumerate(seq):
        e = starts[i + 1] if i + 1 < len(seq) else end_body_s
        n = m.group(1)
        name = f"{fname}-{int(re.match(r'[0-9]+', n).group()):03d}{re.sub(r'^[0-9]+', '', n).lower()}.md"
        if name in seen:
            return None
        seen.add(name)
        files.append((name, text[starts[i]:e].strip()))
    for j, s in enumerate(sm):
        e = sm[j + 1].start() if j + 1 < len(sm) else end_body
        files.append((f"schedule-{j + 1:02d}.md", text[s.start():e].strip()))
    if sub:
        files.append(("subsidiary-legislation.md", text[end_body:].strip()))
    return [(n, t) for n, t in files if t]


def quality(t):
    toks = t.split()
    good = sum(1 for x in toks if re.fullmatch(r"[(\[\"\u201c\u2018]?([A-Za-z][a-z]*(?:[-\u2019'][a-z]+)*|[A-Z]+|\d+(?:\.\d+)*|\([a-z0-9]+\))[)\]\"\u201d\u2019]?[.,;:]?[)\"\u201d]?", x))
    return good / max(1, len(toks))


def done_sources(repo):
    r = subprocess.run(["git", "-C", repo, "log", "--format=%(trailers:key=Source,valueonly,separator=%x0A)", "main"],
                       capture_output=True, text=True, encoding="utf-8")
    return {x.strip() for x in r.stdout.split("\n") if x.strip()}


def titlecase(s):
    small = {"and", "of", "the", "for", "in", "on", "to", "or", "by", "a", "an"}
    w = re.sub(r"\s+", " ", s).strip().lower().split(" ")
    return " ".join(x if (i and x in small) else re.sub(r"^(\W*)(\w)", lambda m: m.group(1) + m.group(2).upper(), x)
                    for i, x in enumerate(w))


def source_name(r):
    if r["source"] == "FAOLEX":
        return "FAOLEX (FAO legislative database), a copy of the Government of Saint Christopher and Nevis' own PDF"
    if r["source"] == "WIPO Lex":
        return "WIPO Lex (World Intellectual Property Organization), a copy of the Government of Saint Christopher and Nevis' own PDF"
    return r["source"]


def secondary(r):
    return f"secondary copy ({'FAOLEX' if r['source'] == 'FAOLEX' else r['source']}, {r.get('page') or r['url']})"


def commencement(text, published, y):
    """Return (day, basis) or (None, reason)."""
    head = text[:40000]
    fixed = re.search(r"(?:come|comes)\s+into\s+(?:force|operation|effect)\s+on\s+(?:such\s+)?(?:a\s+)?(?:day|date)s?(?:\s+or\s+(?:days|dates))?\s+(?:to\s+be\s+)?(?:fixed|appointed|as)", head, re.I)
    c = re.search(r"(?:come|comes|came|shall be deemed to have come)\s+into\s+(?:force|operation|effect)\s+on\s+(?:the\s+)?" + DAY, head, re.I)
    c = mkdate(*c.groups()) if c else None
    if c and abs(c.year - y) <= 3:
        return c, "commencement day stated in the text"
    if fixed:
        return None, "comes into force on a day to be fixed by order; the commencement order is not in the record"
    pub = re.search(r"(?:come|comes)\s+into\s+(?:force|operation|effect)\s+on\s+(?:the\s+)?(?:date|day)\s+of\s+(?:its\s+)?publication", head, re.I)
    if published:
        if pub:
            return published, "day of publication in the Official Gazette, printed on the instrument; it comes into force on publication"
        return published, ("day of publication in the Official Gazette, printed on the instrument; it states no other "
                           "commencement day, and an enactment comes into operation on publication unless it provides otherwise")
    return None, "no publication or commencement day found in the text"


def plan(have, idx):
    rows, seen_keys = [], {}
    for url, r in idx.items():
        title = re.sub(r"\s+", " ", r["title"]).strip()
        src = r["url"].split("?")[0] if "wipolex-res" in r["url"] else r["url"]
        if src in have or url in have:
            continue
        if r.get("status") != 200 or not r.get("file"):
            HELD.append((src, title, f"not fetched (HTTP {r.get('status')})")); continue
        if r.get("kind") == "treaty":
            continue  # regional treaties are planned by plan_treaties()
        pages = max(1, r.get("pages") or 1)
        if (r.get("chars") or 0) < 300 * pages:
            HELD.append((src, title, f"no usable text layer ({r.get('pages')} pages, {r.get('chars')} characters): page scans, not OCRed")); continue
        text, npages = page_lines(os.path.join(ROOT, r["file"]))
        if NOTICE.search(text):
            HELD.append((src, title, "the copy repeats a no-reproduction notice: skipped")); continue
        head = text[:8000]
        is_legal = re.search(r"(?i)\b(act|acts|regulations?|order|ordinance|rules|constitution|code|proclamation|by-?laws?)\b", title)
        if POLICY.search(title) and not is_legal:
            HELD.append((src, title, "not a legal instrument (policy or planning document)")); continue
        if not is_legal:
            HELD.append((src, title, "not recognised as a legal instrument")); continue
        page = r.get("page")
        sname = source_name(r)
        qual = quality(text)
        capture = "paper capture" in (r.get("producer") or "").lower()
        if qual < (0.95 if capture else 0.9):
            HELD.append((src, title, f"text layer too noisy to use ({qual:.0%} clean words; the PDF is a page scan with a poor OCR layer)")); continue
        tsrc = ("publisher OCR (the PDF's own Adobe Paper Capture text layer over a page scan; no OCR run by Lexifina)" if capture else
                "PDF text layer (the publisher's own; no OCR run)")
        trail_src = [("Source-status", secondary(r)), ("Text-source", tsrc), ("Source", src), ("Source-sha256", r["sha256"])] + \
                    ([("Source-page", page)] if page else [])
        cm = re.search(r"CHAPTER\s+(\d{1,2})\.(\d{2})\s*(\(N\))?", head)
        asat = re.search(r"showing the (?:law|subsidiary legislation)\s+as\s+at\s+" + DAY, head, re.I)
        rev = re.search(r"Revision Date:\s*(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})", head)
        if re.search(r"(?i)constitution of saint christopher", title) and not cm:
            HELD.append((src, title, "a copy of the Constitution: needs its own matching to constitution/ (not built in this pass)")); continue
        if cm and (asat or rev):
            d = mkdate(*asat.groups()) if asat else mkdate(*rev.groups())
            if not d:
                HELD.append((src, title, "Revised Edition chapter with no readable revision day")); continue
            cap = f"{int(cm.group(1))}.{cm.group(2)}"
            nevis = bool(cm.group(3))
            nm = re.search(r"CHAPTER\s+\d{1,2}\.\d{2}\s*(?:\(N\))?\s*\n+((?:[A-Z0-9(][A-Z0-9 ,()&'’./-]*\n){1,4})", head)
            name = titlecase(nm.group(1).replace("\n", " ")) if nm else re.sub(r"[.,]?\s*(?:Chapter|Cap\.?).*$", "", title)
            name = re.sub(r"\s+and Subsidiary Legislation$", "", name, flags=re.I).strip()
            name = re.sub(r"\s*\((?:No\.|Act No).*$", "", name).strip()
            key = ("cap", cap, nevis, d)
            files = split_sections(text, revised=True) or [("text.md", text)]
            if key in seen_keys:
                old = seen_keys[key]
                if len(text) <= old["len"]:
                    HELD.append((src, title, f"duplicate copy of Cap. {cap} as at {d} (a longer copy is used)")); continue
                HELD.append((old["src"], old["title"], f"duplicate copy of Cap. {cap} as at {d} (a longer copy is used)"))
                rows.remove(old["row"])
            folder = ("nevis/laws/" if nevis else "laws/") + f"cap-{cap.replace('.', '-')}-{slug(re.sub(r',?\s*(?:19|20)\d\d$', '', name))}"
            cons = re.findall(r"(Act No\.?\s*\d{1,3}\s+of\s+\d{4}|Ordinance No\.?\s*\d{1,3}\s+of\s+\d{4})\s*[–—-]+\s*in force\s+" + DAY, head)
            row = dict(date=d, folder=folder, files=files,
                       author=f"Laws of Saint Christopher and Nevis, Revised Edition (law as at {d.day} {d.strftime('%B %Y')})",
                       email=f"revised-edition-{d.isoformat()}@lawcommission.gov.kn.invalid", kind="revised",
                       subject=f"Cap. {cap}{' (N)' if nevis else ''} {name}: Revised Edition text as at {d.isoformat()}",
                       lines=[f"Chapter {cap}{' (N)' if nevis else ''} of the Laws of Saint Christopher and Nevis, {name}, Revised Edition "
                              f"showing the law as at {d.day} {d.strftime('%B %Y')} (prepared by the Law Commission), as held by {sname}, {npages} pages.",
                              "The text is the PDF's own text layer; running heads and page numbers are removed.",
                              ("One file: no section numbering was found to split on." if files[0][0] == "text.md" else
                               f"{len(files)} files: the front matter (laws consolidated and arrangement), one per section, schedules"
                               " and the chapter's subsidiary legislation in one file.")],
                       trailers=[("In-force", d.isoformat()),
                                 ("In-force-basis", f"the Revised Edition states the law as at {d.isoformat()} (title page and running head 'Revision Date'); the text is the consolidated text in force on that day")] +
                                ([("Consolidates", "; ".join(f"{c[0]} in force {mkdate(*c[1:]) or ''}" for c in cons[:6]))] if cons else []) + trail_src)
            seen_keys[key] = dict(len=len(text), row=row, src=src, title=title)
            rows.append(row)
            continue
        # an Act, Ordinance or S.R.O. as passed / made
        pubm = re.search(r"[\[!(]\s*Published\s+" + DAY, text[:60000], re.I)
        published = mkdate(*pubm.groups()) if pubm else None
        sro = re.search(r"\bno\.?\s*(\d{1,3})\s+of\s+((?:19|20)\d\d)", title, re.I) or \
            re.search(r"STATUTORY\s+RULES\s+AND\s+ORDERS\s*\n?\s*No\.?\s*(\d{1,3})\s+of\s+((?:19|20)\d\d)", head, re.I) or \
            re.search(r"\b(?:S\.\s?R\.\s?O\.|SRO)\s*(?:No\.?\s*)?(\d{1,3})\s*(?:of|/)\s*((?:19|20)\d\d)", head[:1500])
        actm = re.search(r"\bno\.?\s*(\d{1,3})\s+of\s+((?:19|20)\d\d)", title, re.I) or \
            re.search(r"\b(\d{1,3})\s+of\s+((?:19|20)\d\d)\b", title) or \
            re.search(r"^\s*No\.?\s*(\d{1,3})\s+of\s+((?:19|20)\d\d)", head[:1500], re.M)
        is_ord = bool(re.search(r"\bOrdinance\b", title)) and not re.search(r"\bAct\b", title)
        is_reg = bool(re.search(r"Regulations?|Order\b|Rules\b", title)) and not re.search(r"\bAct\b", title)
        if is_reg and sro:
            n, y = int(sro.group(1)), int(sro.group(2)); kind = "sro"
        elif is_reg and actm:
            n, y = int(actm.group(1)), int(actm.group(2)); kind = "sro"
        elif actm:
            n, y = int(actm.group(1)), int(actm.group(2)); kind = "ordinance" if is_ord else "act"
        else:
            HELD.append((src, title, "no Act, Ordinance or S.R.O. number found in the title or the text")); continue
        if re.search(r"^\s*[A-Z][A-Z ,()&'-]+ BILL,? (?:19|20)\d\d\s*$", head[:1500], re.M):
            HELD.append((src, title, "the PDF is the Bill as printed, not the Act")); continue
        d, basis = commencement(text, published, y)
        if d is None:
            HELD.append((src, title, basis)); continue
        if d > TODAY:
            HELD.append((src, title, f"in force {d} after the build day")); continue
        short = re.sub(r"[.,]?\s*\(?(?:no\.?|No\.)\s*\d{1,3}\s+of\s+\d{4}\)?\.?.*$", "", title, flags=re.I).strip().rstrip(",.")
        short = re.sub(r"\s*\.?\s*\(?Chapter\s+[\d.]+.*$", "", short).strip().rstrip(",.")
        short = re.sub(r"\s*\((?:Act|L\.?\s*N|S\.?\s*R\.?\s*O)[^)]*\)?\s*$", "", short).strip().rstrip(",.")
        short = re.sub(r"^The\s+", "", short)
        key = (kind, n, y)
        if key in seen_keys:
            old = seen_keys[key]
            if len(text) <= old["len"]:
                HELD.append((src, title, f"duplicate copy of {kind} {n} of {y} (a longer copy is used)")); continue
            HELD.append((old["src"], old["title"], f"duplicate copy of {kind} {n} of {y} (a longer copy is used)"))
            rows.remove(old["row"])
        files = split_sections(text) or [("text.md", text)]
        folder = {"sro": "statutory-rules-and-orders", "act": "acts", "ordinance": "nevis/ordinances"}[kind] + f"/{y}/{n:03d}-{slug(short)}"
        label = {"sro": f"S.R.O. No. {n} of {y}", "act": f"Act No. {n} of {y}", "ordinance": f"Nevis Ordinance No. {n} of {y}"}[kind]
        passed = re.search(r"Passed (?:by )?the National Assembly this\s+" + DAY, text, re.I)
        passed = mkdate(*passed.groups()) if passed else None
        assent = re.search(r"I assent,?.{0,120}?" + DAY, text, re.I | re.S)
        assent = mkdate(*assent.groups()) if assent else None
        tr = [("In-force", d.isoformat()), ("In-force-basis", basis)]
        if passed:
            tr.append(("Passed", passed.isoformat()))
        if assent:
            tr.append(("Assented", assent.isoformat()))
        if published:
            tr.append(("Published", published.isoformat()))
        row = dict(date=d, folder=folder, files=files, author=label,
                   email=f"{kind}-{y}-{n}@gov.kn.invalid", kind="enactment",
                   subject=f"{short}: as {'made' if kind == 'sro' else 'passed'}, in force {d.isoformat()}",
                   lines=[f"{short} ({label}), as held by {sname}, {npages} pages.",
                          "The text is the PDF's own text layer; running heads and page numbers are removed.",
                          ("One file: no section numbering was found to split on." if files[0][0] == "text.md" else
                           f"{len(files)} files: the front matter, one per section and each schedule.")],
                   trailers=tr + trail_src)
        seen_keys[key] = dict(len=len(text), row=row, src=src, title=title)
        rows.append(row)
    return rows


TREATIES = {
    # url -> (folder, author, email, in-force day, basis, subject)
    "https://www.oecs.int/en/our-work/knowledge/library/revised-treaty-of-basseterre/download":
        ("oecs/revised-treaty-of-basseterre", "Revised Treaty of Basseterre (OECS), 2010", "revised-treaty-of-basseterre-2010@oecs.int.invalid"),
    "https://caricom.org/documents/4906-revised_treaty-text.pdf":
        ("caricom/revised-treaty-of-chaguaramas", "Revised Treaty of Chaguaramas (CARICOM), 2001", "revised-treaty-of-chaguaramas-2001@caricom.org.invalid"),
}
TREATY_DATES = json.load(open(os.path.join(ROOT, "leg", "treaty_dates.json"), encoding="utf8")) if os.path.exists(os.path.join(ROOT, "leg", "treaty_dates.json")) else {}


def plan_treaties(have, idx, rows):
    for url, r in idx.items():
        if r.get("kind") != "treaty" or url in have:
            continue
        title = r["title"]
        if r.get("status") != 200 or not r.get("file"):
            HELD.append((url, title, f"not fetched (HTTP {r.get('status')})")); continue
        if (r.get("chars") or 0) < 300 * max(1, r.get("pages") or 1):
            HELD.append((url, title, "no usable text layer: page scans, not OCRed")); continue
        folder, author, email = TREATIES[url]
        dd = TREATY_DATES.get(url)
        if not dd:
            HELD.append((url, title, "no reliable in-force day found for this treaty")); continue
        d = datetime.date.fromisoformat(dd["date"])
        text, npages = page_lines(os.path.join(ROOT, r["file"]))
        files = split_sections(text, articles=True) or [("text.md", text)]
        rows.append(dict(date=d, folder=folder, files=files, author=author, email=email, kind="treaty",
                         subject=f"{title}: text as signed, in force {d.isoformat()}",
                         lines=[f"{title}, as published by {r['source']} ({r.get('page') or url}), {npages} pages.",
                                "Regional law that applies in Saint Christopher and Nevis; kept in its own folder.",
                                "The text is the PDF's own text layer; running heads and page numbers are removed.",
                                ("One file: no article numbering was found to split on." if files[0][0] == "text.md" else
                                 f"{len(files)} files: the front matter, one per article and each annex.")],
                         trailers=[("In-force", d.isoformat()), ("In-force-basis", dd["basis"]),
                                   ("Source-status", f"secondary copy ({r['source']}, {r.get('page') or url})"),
                                   ("Text-source", "PDF text layer (the publisher's own; no OCR run)"),
                                   ("Source", url), ("Source-sha256", r["sha256"])]))


def git_when(d, seq):
    if d.year < 1970:
        return f"{16 * 3600 + seq} -0400"
    t = int(datetime.datetime(d.year, d.month, d.day, 16, 0, tzinfo=datetime.timezone.utc).timestamp())
    return f"{t} -0400"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    repo = sys.argv[1]
    idx =json.load(open(os.path.join(ROOT, "leg", "fetched.json"), encoding="utf-8"))
    have = done_sources(repo)
    rows = plan(have, idx)
    plan_treaties(have, idx, rows)
    rows.sort(key=lambda r: (r["date"], r["folder"]))
    json.dump([dict(source=h[0], title=h[1], reason=h[2]) for h in HELD],
              open(os.path.join(ROOT, "leg", "held.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--dry" in sys.argv:
        for r in rows:
            print(r["date"], r["folder"], len(r["files"]), r["subject"][:90])
        print(f"rows {len(rows)} held {len(HELD)}")
        for h in HELD:
            print("HELD", h[1][:60], "|", h[2][:90])
        return
    if not rows:
        print(f"nothing new; held {len(HELD)}"); return
    parent = subprocess.run(["git", "-C", repo, "rev-parse", "main"], capture_output=True, text=True).stdout.strip()
    p = subprocess.Popen(["git", "-C", repo, "fast-import", "--quiet", "--done"], stdin=subprocess.PIPE)
    w = p.stdin

    def data(b):
        w.write(f"data {len(b)}\n".encode()); w.write(b); w.write(b"\n")
    for seq, r in enumerate(rows):
        msg = r["subject"] + "\n\n" + "\n".join(r["lines"]) + "\n\n" + f"Kind: {r['kind']}\n" + \
            "".join(f"{k}: {v}\n" for k, v in r["trailers"])
        when = git_when(r["date"], seq)
        w.write(b"commit refs/heads/main\n")
        w.write(f"author {r['author']} <{r['email']}> {when}\ncommitter Lexifina <saint-kitts-and-nevis-law@lexifina.com> {when}\n".encode("utf-8"))
        data(msg.encode("utf-8"))
        if seq == 0:
            w.write(f"from {parent}\n".encode())
        w.write(f"D {r['folder']}\n".encode("utf-8"))
        for name, txt in r["files"]:
            w.write(f"M 100644 inline {r['folder']}/{name}\n".encode("utf-8")); data((txt.strip() + "\n").encode("utf-8"))
        w.write(b"\n")
    w.write(b"done\n"); w.close(); p.wait()
    print(f"committed {len(rows)}; held {len(HELD)}; fast-import rc {p.returncode}")


if __name__ == "__main__":
    main()
