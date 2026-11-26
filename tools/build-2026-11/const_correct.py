"""Replace the OCR text of the 1983 Constitution (constitution/) with the WIPO Lex text copy of the same version,
as one appended Kind: correction commit (approved by Alan 2026-11-26). Same files and layout: '# Section N' /
existing schedule headings kept; marginal notes and chapter headings left out, as in the first build.

python -I tools/const_correct.py <repo> [--dry]"""
import json, os, re, sys, subprocess, difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sk_build as B

ORIG = "9d58598e523e0e714ac2d649e3b6e8c62b87eaf9"
PAGE = "https://www.wipo.int/wipolex/en/legislation/details/10191"
MARK = re.compile(r"^(?:\(?[0-9a-zA-Z]{1,5}\)|[ivxlc]{1,6}\)|\d{1,2}\.\s)")


def reflow(body):
    out = []
    for ln in body.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if out and not MARK.match(s) and not re.match(r"^\d{1,3}[A-Z]?\.\s*[-–—]", s):
            prev = out[-1]
            out[-1] = (prev[:-1] + s) if prev.endswith("-") and re.match(r"[a-z]", s) and not prev.endswith(" -") and len(prev) > 1 and prev[-2].isalpha() else prev + " " + s
        else:
            out.append(s)
    return "\n".join(out)


def trim_heads(chunk):
    lines = chunk.rstrip().split("\n")
    while len(lines) > 1:
        s = lines[-1].strip()
        p = lines[-2].strip()
        if not s:
            lines.pop(); continue
        if re.fullmatch(r"(CHAPTER|PART)\s+[IVXL0-9]+[A-Z]?", s) or (s.isupper() and len(s) > 3 and not MARK.match(s)):
            lines.pop(); continue
        if s[0].isupper() and len(s) < 100 and (p.endswith((".", ";", ":")) or p.isupper() or re.fullmatch(r"(CHAPTER|PART)\s+\S+", p)) \
                and not MARK.match(s):
            lines.pop(); continue
        break
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    repo = sys.argv[1]
    idx = json.load(open(os.path.join(ROOT, "leg", "fetched.json"), encoding="utf-8"))
    r = [r for r in idx.values() if r["title"].startswith("Constitution of Saint Christopher") and r.get("file")][0]
    t, npages = B.page_lines(os.path.join(ROOT, r["file"]))
    s1 = t.find("\nSCHEDULE 1\n"); s6 = t.find("\nSCHEDULE 6\n")
    body = t[:s1]
    ms = list(re.finditer(r"^(\d{1,3}[A-Z]?)\.\s*(?:[-–—]+|(?=\(\d|[A-Z]))", body, re.M))
    seq = B.run_of(ms)
    nums = [m.group(1) for m in seq]
    assert nums == [str(i) for i in range(1, 121)], ("numbering", [n for n in map(str, range(1, 121)) if n not in nums])
    files = {}
    for i, m in enumerate(seq):
        e = seq[i + 1].start() if i + 1 < len(seq) else len(body)
        chunk = trim_heads(body[m.start():e])
        files[f"sec-{int(m.group(1)):03d}.md"] = f"# Section {int(m.group(1))}\n" + reflow(chunk)
    sch = t[s1:s6]
    parts = re.split(r"\nSCHEDULE (\d)\n", "\n" + sch.strip("\n").split("\n", 1)[1] if False else sch)
    # parts: ['', '1', text1, '2', text2, ...]
    for k in range(1, len(parts) - 1, 2):
        n = parts[k]
        old = open(os.path.join(repo, "constitution", f"schedule-{n}.md"), encoding="utf-8").read().split("\n", 1)[0]
        files[f"schedule-{n}.md"] = old + "\n" + reflow(parts[k + 1].strip())
    assert sorted(f for f in files if f.startswith("schedule")) == [f"schedule-{i}.md" for i in range(1, 6)]
    # sanity: similarity with the OCR files
    low = []
    for f, txt in files.items():
        old = open(os.path.join(repo, "constitution", f), encoding="utf-8").read()
        ratio = difflib.SequenceMatcher(None, old.split(), txt.split(), autojunk=False).ratio()
        if ratio < 0.85:
            low.append((round(ratio, 2), f))
    print("files", len(files), "low similarity", sorted(low))
    if "--dry" in sys.argv:
        for f in ["sec-001.md", "sec-019.md", "sec-120.md", "schedule-3.md"]:
            print("=====", f); print(files[f][:900])
        return
    src = r["url"].split("?")[0]
    msg = ("Constitution: replace the OCR text with the WIPO Lex text copy of the same 1983 version\n\n"
           f"The Constitution of Saint Christopher and Nevis (schedule 1 to SI 1983/881), as made, re-read from the text\n"
           f"layer of the copy held by WIPO Lex ({npages} pages), in place of the Tesseract OCR of the legislation.gov.uk scan.\n"
           "Same version, same in-force day, same files: sections 1 to 120 and schedules 1 to 5; marginal notes,\n"
           "chapter headings and the preamble are left out, as in the first build.\n\n"
           "Kind: correction\n"
           f"Corrects: {ORIG}\n"
           "Reason: replace OCR text with WIPO Lex text copy of the same 1983 version\n"
           "Law: SI 1983/881\n"
           "In-force: 1983-09-19\n"
           "In-force-basis: unchanged from the corrected commit: the day the Constitution came into effect (section 3 of the Order)\n"
           f"Source-status: secondary copy (WIPO Lex, {PAGE})\n"
           "Text-source: PDF text layer (Acrobat Distiller; no OCR run)\n"
           f"Source: {src}\n"
           f"Source-sha256: {r['sha256']}\n"
           f"Source-page: {PAGE}\n")
    when = "432835200 -0400"  # 1983-09-19 12:00 America/St_Kitts, as the corrected commit
    assert subprocess.run(["git", "-C", repo, "log", "-1", "--format=%at", ORIG], capture_output=True, text=True).stdout.strip() == "432835200"
    parent = subprocess.run(["git", "-C", repo, "rev-parse", "main"], capture_output=True, text=True).stdout.strip()
    p = subprocess.Popen(["git", "-C", repo, "fast-import", "--quiet", "--done"], stdin=subprocess.PIPE)
    w = p.stdin

    def data(b):
        w.write(f"data {len(b)}\n".encode()); w.write(b); w.write(b"\n")
    w.write(b"commit refs/heads/main\n")
    w.write(f"author SI 1983/881 <si-1983-881@nationalarchives.invalid> {when}\ncommitter Lexifina <saint-kitts-and-nevis-law@lexifina.com> {when}\n".encode())
    data(msg.encode("utf-8"))
    w.write(f"from {parent}\n".encode())
    for f, txt in sorted(files.items()):
        w.write(f"M 100644 inline constitution/{f}\n".encode()); data((txt.strip() + "\n").encode("utf-8"))
    w.write(b"\ndone\n"); w.close(); p.wait()
    print("fast-import rc", p.returncode)


if __name__ == "__main__":
    main()
