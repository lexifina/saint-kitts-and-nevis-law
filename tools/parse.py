"""Parse OCR TSV (cache/ocr2) of SI 1983/881 into corpus.json. OCR text; see README."""
import csv, glob, json, os, re, hashlib, sys
C=os.path.join(os.path.dirname(os.path.abspath(__file__)),'.cache')
PDF=os.path.join(C,'uksi_19830881_en.pdf')
SHA=hashlib.sha256(open(PDF,'rb').read()).hexdigest()
def page(f):
    rows=list(csv.DictReader(open(f,encoding='utf8'),delimiter='	',quoting=csv.QUOTE_NONE))
    pw=int(rows[0]['width']); ph=int(rows[0]['height'])
    pageno=int(re.search(r'p(\d+)',f).group(1))
    left_notes = pageno%2==1
    W=[(int(r['left']),int(r['left'])+int(r['width']),int(r['top']),r) for r in rows if r['level']=='5' and r['text'].strip()]
    cov=[0]*(pw+2)
    for l,rt,t,r in W:
        if 0.18*ph<t<0.92*ph:
            for x in range(max(0,l),min(pw,rt)+1): cov[x]+=1
    cut=None
    if left_notes:
        x=int(0.36*pw)
        while x>8:
            if all(cov[x-k]==0 for k in range(6)): cut=x; break
            x-=1
        def isnote(l,rt): return cut is not None and rt<=cut+2 and rt<0.30*pw
    else:
        x=int(0.60*pw)
        while x<pw-8:
            if all(cov[x+k]==0 for k in range(6)): cut=x; break
            x+=1
        def isnote(l,rt): return cut is not None and l>=cut-2 and l>0.60*pw
    lines={};nw=[]
    for l,rt,t,r in W:
        if isnote(l,rt) and t>0.16*ph: nw.append((t,l,r['text']))
        elif isnote(l,rt): pass
        else: lines.setdefault((r['block_num'],r['par_num'],r['line_num']),[]).append((l,t,r['text']))
    body=sorted((min(w[1] for w in ws),' '.join(w[2] for w in sorted(ws))) for ws in lines.values())
    nw.sort(); notes=[]
    for t,l,x in nw:
        if notes and t-notes[-1][2]<=70: notes[-1][1].append(x); notes[-1][2]=t
        else: notes.append([t,[x],t])
    notes=[(n[0],' '.join(n[1])) for n in notes]
    return body,notes
def norm(s):
    s=s.replace(' ',' ').replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')
    s=re.sub(r'\s+',' ',s).strip()
    s=re.sub(r'''^[|\[\]{}_'`~.,;:\s]+(?=\d{1,3}\s*[.,])''','',s)
    return s
HDR=re.compile(r'^(SAINT CHRISTOPHER AND NEVIS|S\.?[1I]\.? 1983/881.*|\d{4}\s*(SAINT CHRISTOPHER AND NEVIS)?|S\.I\. 1983/881 \d{4})$')
def stream(p0,p1):
    out=[]  # (page, top, text)
    notes=[]
    for p in range(p0,p1+1):
        body,nt=page(os.path.join(C,'ocr2',f'p{p:03d}.tsv'))
        for t,x in body:
            x=norm(x)
            if not x or HDR.match(x): continue
            out.append((p,t,x))
        notes+=[(p,t,norm(x)) for t,x in nt]
    return out,notes

START=re.compile(r'^(\d{1,3})\s*[.,]\s*(?:[-_=~—]\s*)?(.*)$')
def paragraphs(lines):
    """-> [{'p':page,'t':top,'x':text}] using vertical gaps; section starts always begin a paragraph"""
    paras=[];prev=None
    for p,t,x in lines:
        newp=True
        if prev:
            pp,pt,_=prev
            if pp==p and t-pt<=76 and not START.match(x): newp=False
            if not newp and re.match(r'^(\([a-z]{1,3}\)|\([ivx]+\)|\(\d{1,2}\)) ',x) and re.search(r'([—;:.]|[;,]\s*(or|and))$',paras[-1]['x']): newp=True
            if pp!=p:
                last=paras[-1]['x']
                newp= bool(re.search(r'[.;:—-]$|\)$',last)) and bool(re.match(r'^(\(\w{1,4}\)|\d{1,3}\s*[.,]|Provided|[A-Z]{3})',x)) or bool(re.match(r'^(\d{1,3}\s*[.,]\s*[-_=~]|\(\d{1,2}\) [A-Z])',x))
                if re.search(r'[.;:—-]$',last)==None and not newp: newp=False
        if newp: paras.append({'p':p,'t':t,'x':x})
        else:
            a=paras[-1]['x']
            paras[-1]['x']=(a[:-1]+x) if (a.endswith('-') and not a.endswith(' -') and len(a)>1 and a[-2].isalpha()) else a+' '+x
        prev=(p,t,x)
    return paras
def label_text(paras):
    return paras

SIGN=re.compile(r'S\.?\s?[1Il]I?\.?\s?19[89]3/88[1\]l]\s*\d{0,4}')
CUT=re.compile(r'^(CHAPTER|PART|ParRT|PaRT|ParT)\s+[IVXl1\d]+',re.I)
FIX=[('electud','elected'),('disssolution','dissolution'),('incidenial','incidental'),('sovernment contract','government contract'),('twentyone','twenty-one'),('illwill','ill-will'),('planand','plan and'),('Ifit','If it'),('GovernorGeneral','Governor-General'),('AttorneyGeneral','Attorney-General'),('set owt in','set out in'),('(a )','(a)'),('(b})','(b)'),('(ii) Chapter I;','(ii) Chapter II;')]
INLINE=re.compile(r'\s+(?:CHAPTER [IVX]+|PART \d|PaRT \d|ParT \d|ParRT \d).*$')
def clean(x):
    x=x.replace(' ° ',' ').replace(' » ',' ')
    x=re.sub(r'(?<=\s)[.:;|_]+(?=\s|$)','',x)
    for a,b in FIX: x=x.replace(a,b)
    x=SIGN.sub('',x); x=re.sub(r'^(\d{1,3})\s*[.,]\s*[—_-]*\s*[({\[]{1,2}\s*\\?\s*[1lI]?\s*[)}\]]',lambda m:m.group(1)+'.—(1)',x); x=re.sub(r'^1\.1\)','1.—(1)',x); x=re.sub(r'(?<!\.)\.\.(?!\.)','.',x); x=re.sub(r'\s+',' ',x).strip(); return x
def split_sections(paras,notes,first=1,until=None):
    secs=[];n=first;cur=None
    for q in paras:
        if until and until(q['x']): break
        m=START.match(q['x'])
        if m and int(m.group(1))==n:
            cur={'n':n,'p':q['p'],'t':q['t'],'ps':[q['x']]};secs.append(cur);n+=1;continue
        if cur: cur['ps'].append(q['x'])
    used=set()
    for sc in secs:
        best=None
        for k,(p,t,x) in enumerate(notes):
            if p==sc['p'] and k not in used and abs(t-sc['t'])<=140:
                if best is None or abs(t-sc['t'])<abs(notes[best][1]-sc['t']): best=k
        sc['title']=None
        if best is not None: used.add(best); sc['title']=notes[best][2]
    return secs
def trim(ps):
    for i,x in enumerate(ps):
        if CUT.match(x): return ps[:i]
    return ps
NL=chr(10)
def unit(prefix,sc,cut=True):
    ps=[clean(x) for x in (trim(sc['ps']) if cut else sc['ps'])]
    if cut: ps=[INLINE.sub('',x) for x in ps]
    ps=[x for x in ps if x]
    head=f"# Section {sc['n']}" if prefix=='sec' else f"# Paragraph {sc['n']}"
    return head+NL+NL.join(ps)+NL

def sched_text(k,p0,p1,title):
    """schedules come from the plain page OCR (clean layout); header lines and marginal notes dropped by hand rules"""
    txt=NL.join(open(os.path.join(C,'ocr',f'p{p:03d}.txt'),encoding='utf8').read() for p in range(p0,p1+1))
    if k=='schedule-3':
        pat=r'.The State 1.\(1\) The island of Saint Christopher \(which is other-\nand its wise known as Saint Kitts\) shall be a sovereign democratic\nterritory\. state which may be styled Saint Christopher or Saint Kitts\.'
        new='1.—(1) The island of Saint Christopher (which is otherwise known as Saint Kitts) shall be a sovereign democratic state which may be styled Saint Christopher or Saint Kitts.'
        txt,n=re.subn(pat,new,txt)
        assert n==1 and 'The State' not in txt
    drop=re.compile(r'^(\d{4}\s+SAINT CHRISTOPHER AND NEVIS|S\.\s?[1Il]I?\.?\s?19[89]3/88[1\]l]\s*\d{0,4}|\d{4}|II/tv|Section \d+(\(\d+\))?\s*SCHEDULE \d)$')
    paras=[]
    for blk in re.split(r'\n\s*\n',txt):
        ls=[l.strip() for l in blk.split(NL) if l.strip()]
        ls=[l for l in ls if not drop.match(l)]
        if not ls: continue
        out=''
        for l in ls:
            if out and re.match(r'^(\((\d+|[a-z]{1,4})\) |(PART|ParT|PaRT|ParRT) \d)',l): paras.append(out); out=''
            if out.endswith('-') and l[:1].islower() and not out.endswith(' -'): out=out[:-1]+l
            else: out=(out+' '+l).strip()
        paras.append(out)
    paras=[clean(re.sub(r'^(PaRT|ParT|ParRT) ',r'PART ',x).replace('“','"').replace('”','"').replace('’',"'")) for x in paras]
    paras=[x for x in paras if x]
    return '# '+title+NL+NL.join(paras)+NL

def main():
    lines,notes=stream(8,94)
    i=next(k for k,(p,t,x) in enumerate(lines) if x.startswith('CHAPTER I') and p==8)
    paras=paragraphs(lines[i:])
    secs=split_sections(paras,notes)
    assert len(secs)==120,len(secs)
    units={}
    for sc in secs[:-1]:
        units[f"sec-{sc['n']:03d}"]={'label':f"Section {sc['n']}",'kind':'section','text':unit('sec',sc)}
    last=secs[-1]
    full=NL.join(clean(x) for x in last['ps'])
    marks=[('schedule-1',r'PROVISIONS REFERRED TO IN SECTION 38\(3\)'),('schedule-2',r'SCHEDULE 2 Section 50\(1\)'),
           ('schedule-3',r'Section 115 SCHEDULE 3'),('schedule-4',r'SCHEDULE 4 Section 119\(1\)'),
           ('schedule-5',r'(?:II/tv )?Section 119\(1\) SCHEDULE 5')]
    pos=[]
    for k,rx in marks:
        m=re.search(rx,full); assert m,k; pos.append((m.start(),m.end(),k))
    sec120=re.sub(r'\s*Section 38\(3\) SCHEDULE 1\s*$','',full[:pos[0][0]].strip())
    units['sec-120']={'label':'Section 120','kind':'section','text':'# Section 120'+NL+sec120+NL}
    titles={'schedule-1':'Schedule 1: Provisions referred to in section 38(3)','schedule-2':'Schedule 2: Rules for delimitation of constituencies',
            'schedule-3':'Schedule 3: Alterations if Nevis secedes','schedule-4':'Schedule 4: Forms of oath','schedule-5':'Schedule 5: Legislative powers'}
    for k,(p0,p1) in {'schedule-1':(89,89),'schedule-2':(90,90),'schedule-3':(91,91),'schedule-4':(92,92),'schedule-5':(93,94)}.items():
        units[k]={'label':titles[k].split(':')[0],'kind':'schedule','text':sched_text(k,p0,p1,titles[k])}
    lo,no=stream(1,2)
    i=next(k for k,(p,t,x) in enumerate(lo) if x.startswith('1.1)'))
    po=paragraphs(lo[i:]); so=split_sections(po,no,until=lambda x:x.startswith('N.E. Leigh'))
    assert len(so)==4,len(so)
    order={}
    for sc in so:
        order[f"sec-{sc['n']:03d}"]={'label':f"Section {sc['n']}",'kind':'section','text':unit('sec',sc,cut=False)}
    lt,nt=stream(116,121)
    i=next(k for k,(p,t,x) in enumerate(lt) if x.startswith('1. Until such time'))
    pt=paragraphs(lt[i:]); st=split_sections(pt,nt,until=lambda x:x.startswith('EXPLANATORY NOTE'))
    for sc in st:
        order[f"sched2-para-{sc['n']:02d}"]={'label':f"Schedule 2, paragraph {sc['n']}",'kind':'schedule','text':unit('para',sc,cut=False)}
    json.dump({'constitution':units,'order':order},open(os.path.join(C,'units.json'),'w',encoding='utf8'),ensure_ascii=False,indent=1)
    print(len(units),len(order))
def corpus():
    u=json.load(open(os.path.join(C,'units.json'),encoding='utf8'))
    LAW='si-1983-881'
    def acts_units(d): return {k:{'label':v['label'],'kind':v['kind'],'text':v['text']} for k,v in d.items()}
    src='https://www.legislation.gov.uk/uksi/1983/881/made'
    pdf='http://www.legislation.gov.uk/uksi/1983/881/pdfs/uksi_19830881_en.pdf'
    def act(slug,short,title,units,frm,url):
        return {'slug':slug,'short':short,'title':title,'url':url,'first_law':LAW,'earlier_laws':[],
                'versions':[{'from':frm,'source_url':pdf,'sha256':SHA,'units':acts_units(units),'credits':{k:[LAW] for k in units},
                  'note':'Text read from an image-only scan by optical character recognition (OCR); see README.'}]}
    corpus={'country':{'code':'KN','name':'Saint Kitts and Nevis','slug':'saint-kitts-and-nevis','lang':'en','tz':'America/St_Kitts','future_branch':'future',
        'publisher':{'name':'legislation.gov.uk (The National Archives)','email':'legislation@nationalarchives.invalid'},
        'default_in_force_rule':{'text':'The Order came into operation on 23 June 1983 (section 1(2)); the Constitution set out in its schedule 1 came into effect on 19 September 1983 (section 3).','source':src},
        'licence_note':'Contains public sector information licensed under the Open Government Licence v3.0. Source: legislation.gov.uk, The Saint Christopher and Nevis Constitution Order 1983 (SI 1983/881), as made. https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'},
      'sources':[{'name':'legislation.gov.uk: The Saint Christopher and Nevis Constitution Order 1983 (as made), scanned PDF','url':pdf,'retrieved':'2026-10-30','requests':2,'licence':'Open Government Licence v3.0','notes':'Image-only scan of the printed Statutory Instrument (122 pages, no text layer). Text recovered with Tesseract 5.4 (English); see decisions.'}],
      'laws':{LAW:{'label':'SI 1983/881','title':'The Saint Christopher and Nevis Constitution Order 1983','kind':'decree','enacted':'1983-06-22','published':'1983-06-22','url':src,'temporary_until':None,'restores':None,'note':None}},
      'acts':[act('constitution','Constitution','The Constitution of Saint Christopher and Nevis (schedule 1 to SI 1983/881), as made',u['constitution'],'1983-09-19',src),
              act('constitution-order','SI 1983/881','The Saint Christopher and Nevis Constitution Order 1983: sections 1 to 4 and the transitional provisions in schedule 2',u['order'],'1983-06-23',src)],
      'applies':[],
      'decisions':['The text is the Constitution as made in 1983. Later amendments are not applied, because the source holds only the 1983 Order; the repository is therefore a single version per act and is not the current Constitution.',
        'The scan has no text layer. It was read with Tesseract 5.4 (English, 300 dpi, page segmentation mode 3); mean word confidence 95.9 percent. Marginal notes (section headings) were left out because they could not be read reliably; chapter and part headings were left out of section units.',
        'Spot checks against the scan found and corrected: Chapter II misread as Chapter I (schedule 1); a marginal note merged into schedule 3 paragraph 1 (corrected by hand from the scan); and a short list of misread words (for example electud, disssolution, incidenial) corrected by hand. Every word was checked against a dictionary; a full proofread against the scan has not been done.',
        'Schedules 1 to 5 to the Constitution are one unit each. Schedule 6 to the Constitution (provisions applied with modifications), the Preamble and the explanatory note are not included.',
        'The Constitution takes effect on 19 September 1983 (Order, section 3); the Order itself came into operation on 23 June 1983 (section 1(2)). Both versions are credited to SI 1983/881.'],
      'ai_use':['Claude Code (Claude Sonnet 5.5) wrote the extraction code and made the hand corrections listed in decisions. The text itself was recovered by Tesseract OCR; no model wrote or summarised legal text.']}
    json.dump(corpus,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'corpus.json'),'w',encoding='utf8',newline=chr(10)),ensure_ascii=False,indent=1)
if __name__=='__main__':
    main(); corpus()
