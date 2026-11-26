"""List and fetch secondary copies of Saint Kitts and Nevis legislation (text layer only; no OCR).

python -I tools/acquire.py
Sources: ECOLEX listing for Saint Kitts and Nevis (FAOLEX record ids; robots Crawl-delay 30 s honoured), FAOLEX PDFs
(faolex.fao.org/docs/pdf/stk<id>.pdf), the WIPO Lex profile KN and its legislation pages, and the OECS Revised Treaty
of Basseterre. The Attorney General's Chambers site (lawcommission.gov.kn) is never contacted.
One request in flight per host, 1 s apart; back off on 429/5xx; stop on 403 or a challenge page.
Writes leg/catalogue.json, leg/pdf/<sha16>.pdf, leg/fetched.json; appends to progress.log. Re-runnable (cached)."""
import os, re, json, time, hashlib, html as H, urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = os.path.join(ROOT, "leg"); PD = os.path.join(L, "pdf"); os.makedirs(PD, exist_ok=True)
LOG = os.path.join(ROOT, "progress.log")
UA = "Mozilla/5.0 (compatible; lexifina-law-archive)"
delay = 1.0
STOPPED = set()


def log(m):
    with open(LOG, "a", encoding="utf8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + "leg " + m + "\n")


def get(url, pause=None):
    global delay
    host = urllib.parse.urlparse(url).netloc
    if host in STOPPED:
        return 403, b""
    q = urllib.parse.quote(url, safe=":/%?=&~+")
    st, b = -1, b""
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": UA}), timeout=180)
            b = r.read(); st = r.status
        except urllib.error.HTTPError as e:
            st, b = e.code, b""
        except Exception as e:
            st, b = -1, str(e).encode()
        head = b[:3000].lower()
        if st == 403 or b"just a moment" in head or b"captcha" in head or b"cf-challenge" in head:
            log(f"STOP host {host}: HTTP {st} or challenge at {url}"); STOPPED.add(host)
            return 403, b""
        if st == 429 or st >= 500 or st == -1:
            delay = min(120, delay * 2); log(f"backoff {delay:.0f}s: HTTP {st} {url}"); time.sleep(delay); continue
        time.sleep(pause or delay)
        delay = max(1.0, delay * 0.8)
        return st, b
    log(f"give up {url}"); return st, b


def links(b, base):
    out = []
    for href, txt in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', b.decode("utf8", "replace"), re.S):
        t = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", txt))).strip()
        out.append((urllib.parse.urljoin(base, H.unescape(href)), t))
    return out


def catalogue():
    cat, seen = [], set()

    def add(url, title, source, kind="text", **kw):
        key = url.split("?")[0]
        if key in seen:
            return
        seen.add(key); cat.append(dict(url=url, title=title, source=source, kind=kind, **kw))
    # ECOLEX legislation listing (FAOLEX ids)
    page = 1
    while page < 20:
        u = f"https://www.ecolex.org/result/?type=legislation&xcountry=Saint+Kitts+and+Nevis&page={page}"
        st, b = get(u, pause=30)
        if st != 200:
            break
        got = 0
        for m in re.finditer(r'href="(/details/legislation/[^"]*?lex-faoc(\d+)/)[^"]*"[^>]*>(.*?)</a', b.decode("utf8", "replace"), re.S):
            t = H.unescape(re.sub(r"<[^>]+>|\s+", " ", m.group(3))).strip()
            k = f"https://faolex.fao.org/docs/pdf/stk{m.group(2)}.pdf"
            if k not in seen:
                got += 1
            add(k, t, "FAOLEX", faoc=m.group(2), page="https://www.ecolex.org" + m.group(1))
        log(f"ecolex page {page}: {got}")
        if got == 0:
            break
        page += 1
    # WIPO Lex profile KN
    st, b = get("https://www.wipo.int/wipolex/en/members/profile/KN")
    for u, t in links(b, "https://www.wipo.int/"):
        if "/wipolex/en/legislation/details/" in u and t:
            st2, b2 = get(u)
            for u2, t2 in links(b2, u):
                if re.search(r"edocs/lexdocs/(?:laws|treaties)/en/", u2) and u2.lower().split("?")[0].endswith(".pdf"):
                    add(u2, t, "WIPO Lex", page=u); break
    # OECS Revised Treaty of Basseterre
    add("https://www.oecs.int/en/our-work/knowledge/library/revised-treaty-of-basseterre/download",
        "Revised Treaty of Basseterre Establishing the Organisation of Eastern Caribbean States Economic Union", "OECS",
        kind="treaty", page="https://www.oecs.int/en/our-work/knowledge/library/revised-treaty-of-basseterre")
    json.dump(cat, open(os.path.join(L, "catalogue.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    log(f"catalogue {len(cat)} items")
    return cat


def main():
    cp = os.path.join(L, "catalogue.json")
    cat = json.load(open(cp, encoding="utf8")) if os.path.exists(cp) else catalogue()
    fp = os.path.join(L, "fetched.json")
    got = json.load(open(fp, encoding="utf8")) if os.path.exists(fp) else {}
    import pymupdf
    for i, c in enumerate(cat):
        key = c["url"].split("?")[0]
        if key in got and got[key].get("status") == 200:
            continue
        if key in got and got[key].get("status") == 404 and c["source"] == "FAOLEX" and c.get("page"):
            # the FAOLEX file name is not always stk<id>.pdf: read it from the ECOLEX record (Crawl-delay 30 s)
            st0, b0 = get(c["page"], pause=30)
            alt = re.findall(r'href="(https?://faolex\.fao\.org/docs/(?:pdf|texts)/[^"]+)"', b0.decode("utf8", "replace"))
            if not alt:
                log(f"no FAOLEX file on {c['page']}"); continue
            c = dict(c, url=alt[0], listed_url=c["url"])
        if c["source"] == "WIPO Lex" and c.get("page"):
            # WIPO Lex PDF links are signed and expire within minutes: take a fresh link from the record page
            st0, b0 = get(c["page"])
            fresh = [u2 for u2, t2 in links(b0, c["page"]) if re.search(r"edocs/lexdocs/(?:laws|treaties)/en/", u2)
                     and u2.lower().split("?")[0].endswith(".pdf")]
            if fresh:
                c = dict(c, url=fresh[0])
        st, b = get(c["url"])
        rec = dict(c, status=st)
        if st == 200 and b[:4] == b"%PDF":
            h = hashlib.sha256(b).hexdigest(); fn = os.path.join(PD, h[:16] + ".pdf")
            open(fn, "wb").write(b)
            try:
                d = pymupdf.open(fn)
                rec.update(pages=d.page_count, chars=sum(len(p.get_text().strip()) for p in d),
                           producer=d.metadata.get("producer"), author=d.metadata.get("author"),
                           keywords=d.metadata.get("keywords"))
            except Exception:
                rec.update(pages=0, chars=-1)
            rec.update(file="leg/pdf/" + h[:16] + ".pdf", sha256=h)
        elif st == 200:
            rec["status"] = "not-pdf"
        got[key] = rec
        json.dump(got, open(fp + ".tmp", "w", encoding="utf8"), ensure_ascii=False, indent=0); os.replace(fp + ".tmp", fp)
        log(f"pdf {i + 1}/{len(cat)} {rec['status']} {rec.get('pages')}p {rec.get('chars')}ch {c['title'][:60]}")
    log("DONE acquire")


if __name__ == "__main__":
    main()
