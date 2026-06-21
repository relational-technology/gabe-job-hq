#!/usr/bin/env python3
"""Daily scanner (free, runs in GitHub Actions): pull the LinkedIn public guest jobs feed
for London producer roles, store each role PLUS its job-description text in Turso, mark
vanished auto-listings as closed, and roll run timestamps so the portal shows +new/-closed.
Bespoke cover letters are written separately by the daily Anthropic Cloud routine, which
reads the stored job descriptions. Reads TURSO_TOKEN / TURSO_DB from env or ~/.aura-ops-secrets.
No em dashes in stored text."""
import os, re, json, hashlib, urllib.request
from playwright.sync_api import sync_playwright
import companies

def cred(k):
    v=os.environ.get(k)
    if v: return v
    try:
        o=__import__("subprocess").check_output(["bash","-lc",f"grep '^{k}=' ~/.aura-ops-secrets|head -1"]).decode()
        return o.split("=",1)[1].strip().strip('"').strip("'")
    except Exception: return ""
TOKEN=cred("TURSO_TOKEN"); EP=re.sub(r'^(libsql|wss)://','https://',cred("TURSO_DB"))
if not EP.startswith("http"): EP="https://"+EP

def tq(sql,args=None):
    stmt={"sql":sql}
    if args is not None: stmt["args"]=args
    r=urllib.request.Request(EP+"/v2/pipeline",
      data=json.dumps({"requests":[{"type":"execute","stmt":stmt},{"type":"close"}]}).encode(),
      headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    res=json.loads(urllib.request.urlopen(r).read())["results"][0]
    if res["type"]!="ok": raise RuntimeError(json.dumps(res)[:200])
    rr=res["response"]["result"]
    return [{c["name"]:(row[i].get("value") if isinstance(row[i],dict) else row[i]) for i,c in enumerate(rr["cols"])} for row in rr["rows"]]
def T(v): return {"type":"text","value":str(v)}
def F(v): return {"type":"float","value":float(v)}

EXCLUDE=re.compile(r'interactive|technical|game|software|engineer|developer|content creator|social media|social content|website content|videographer|video editor|community manager|influencer|ugc|presenter|intern|assistant|coordinator|junior',re.I)
def fit(title):
    t=title.lower()
    if EXCLUDE.search(t): return None
    if 'head of' in t: return 8.0
    if 'executive producer' in t: return 8.0
    if 'senior' in t and 'producer' in t: return 7.5
    if 'branded content' in t or 'experiential' in t: return 7.5
    if 'creative producer' in t: return 7.0
    if 'content producer' in t or 'video producer' in t: return 6.5
    if 'producer' in t: return 6.0
    return None

UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15")
KW=["Senior Producer","Creative Producer","Executive Producer","Branded Content Producer","Content Producer"]
LOC="London%2C%20England%2C%20United%20Kingdom"

def fetch_jd(page, jobid):
    try:
        page.goto(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jobid}",wait_until="domcontentloaded",timeout=20000)
        page.wait_for_timeout(400)
        html=page.content()
        m=re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>',html,re.S)
        txt=re.sub(r'<[^>]+>',' ',m.group(1)) if m else ''
        txt=re.sub(r'\s+',' ',txt).strip().replace('—','-').replace('–','-')
        return txt[:3000]
    except Exception as e:
        print("jd warn",jobid,str(e)[:50]); return ""

def scan(page):
    found={}
    for kw in KW:
        url=f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw.replace(' ','%20')}&location={LOC}&f_TPR=r1209600&start=0"
        try:
            page.goto(url,wait_until="domcontentloaded",timeout=30000); page.wait_for_timeout(700)
            html=page.content()
            for jid,title,company,locn in re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)".*?base-search-card__title">\s*([^<]+?)\s*</h3>.*?subtitle">\s*<a[^>]*>\s*([^<]+?)\s*</a>.*?location">\s*([^<]+?)\s*</span>',html,re.S):
                f=fit(title)
                if f is None: continue
                found[jid]={"id":"li-"+jid,"jobid":jid,"company":company.strip().replace('&amp;','&'),
                            "role":title.strip().replace('&amp;','&'),"fit":f,"url":f"https://www.linkedin.com/jobs/view/{jid}"}
        except Exception as e:
            print("scan warn",kw,str(e)[:60])
    return list(found.values())

def main():
    have_jd={r["id"] for r in tq("SELECT id FROM jobs WHERE jd IS NOT NULL AND jd!=''")}
    tq("INSERT INTO meta(k,v) VALUES('prev_run',(SELECT v FROM meta WHERE k='last_run')) ON CONFLICT(k) DO UPDATE SET v=(SELECT v FROM meta WHERE k='last_run')")
    tq("UPDATE meta SET v=datetime('now') WHERE k='last_run'")
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA); page=ctx.new_page()
        rolesnow=scan(page); print("scanned roles:",len(rolesnow))
        fetched=0
        for r in rolesnow:
            jd=""
            if r["id"] not in have_jd:
                jd=fetch_jd(page,r["jobid"]);
                if jd: fetched+=1
            if jd:
                tq("INSERT INTO jobs(id,company,role,fit,url,status,source,jd,first_seen,last_seen) "
                   "VALUES(?,?,?,?,?,'ready','linkedin',?,datetime('now'),datetime('now')) "
                   "ON CONFLICT(id) DO UPDATE SET last_seen=datetime('now'), role=excluded.role, company=excluded.company, jd=excluded.jd, "
                   "status=CASE WHEN jobs.status='closed' THEN 'ready' ELSE jobs.status END, closed_at=CASE WHEN jobs.status='closed' THEN NULL ELSE jobs.closed_at END",
                   [T(r["id"]),T(r["company"]),T(r["role"]),F(r["fit"]),T(r["url"]),T(jd)])
            else:
                tq("INSERT INTO jobs(id,company,role,fit,url,status,source,first_seen,last_seen) "
                   "VALUES(?,?,?,?,?,'ready','linkedin',datetime('now'),datetime('now')) "
                   "ON CONFLICT(id) DO UPDATE SET last_seen=datetime('now'), role=excluded.role, company=excluded.company, "
                   "status=CASE WHEN jobs.status='closed' THEN 'ready' ELSE jobs.status END, closed_at=CASE WHEN jobs.status='closed' THEN NULL ELSE jobs.closed_at END",
                   [T(r["id"]),T(r["company"]),T(r["role"]),F(r["fit"]),T(r["url"])])
        b.close()
    # target companies (incl big tech) via verified careers endpoints (urllib, no browser)
    ok_sources=set(); croles=[]
    try: croles, ok_sources = companies.scan_all()
    except Exception as e: print("company scan error",str(e)[:120])
    for r in croles:
        cid="co-"+r["source"]+"-"+hashlib.md5((r.get("url") or r["role"]).encode()).hexdigest()[:10]
        fitv=fit(r["role"]) or 7.0
        if r.get("jd"):
            tq("INSERT INTO jobs(id,company,role,fit,url,status,source,jd,first_seen,last_seen) VALUES(?,?,?,?,?,'ready',?,?,datetime('now'),datetime('now')) "
               "ON CONFLICT(id) DO UPDATE SET last_seen=datetime('now'), role=excluded.role, company=excluded.company, jd=excluded.jd, "
               "status=CASE WHEN jobs.status='closed' THEN 'ready' ELSE jobs.status END, closed_at=CASE WHEN jobs.status='closed' THEN NULL ELSE jobs.closed_at END",
               [T(cid),T(r["company"]),T(r["role"]),F(fitv),T(r["url"]),T(r["source"]),T(r["jd"])])
        else:
            tq("INSERT INTO jobs(id,company,role,fit,url,status,source,first_seen,last_seen) VALUES(?,?,?,?,?,'ready',?,datetime('now'),datetime('now')) "
               "ON CONFLICT(id) DO UPDATE SET last_seen=datetime('now'), role=excluded.role, company=excluded.company, "
               "status=CASE WHEN jobs.status='closed' THEN 'ready' ELSE jobs.status END, closed_at=CASE WHEN jobs.status='closed' THEN NULL ELSE jobs.closed_at END",
               [T(cid),T(r["company"]),T(r["role"]),F(fitv),T(r["url"]),T(r["source"])])
    # reconcile: close vanished roles only for sources that actually responded this run
    reconc=set(ok_sources)
    if len(rolesnow)>=5: reconc.add("linkedin")
    if reconc:
        inlist=",".join("'"+s.replace("'","")+"'" for s in reconc)
        tq("UPDATE jobs SET status='closed', closed_at=datetime('now') WHERE source IN ("+inlist+") "
           "AND status NOT IN('applied','interviewing','rejected','archived','closed') "
           "AND last_seen < (SELECT v FROM meta WHERE k='last_run')")
    print("target-company roles found:",len(croles),"| sources ok:",len(ok_sources),
          "| not covered:",", ".join(companies.NOT_COVERED))
    print("job descriptions fetched this run:",fetched)
    print("active jobs now:",tq("SELECT count(*) c FROM jobs WHERE status NOT IN('closed','archived')")[0]["c"])

if __name__=="__main__": main()
