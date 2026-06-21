#!/usr/bin/env python3
"""Daily refresher: scan the LinkedIn public guest jobs feed for London producer roles,
upsert new ones into Turso, mark vanished auto-listings as closed, and roll the run
timestamps so the portal can show +new / -closed. Reads TURSO_TOKEN / TURSO_DB from env
(GitHub Actions secrets) or ~/.aura-ops-secrets locally. No em dashes in stored text."""
import os, re, json, urllib.request
from playwright.sync_api import sync_playwright

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
    return [{c["name"]:(row[i] and row[i]["value"]) for i,c in enumerate(rr["cols"])} for row in rr["rows"]]
def T(v): return {"type":"text","value":str(v)}
def F(v): return {"type":"float","value":float(v)}

EXCLUDE=re.compile(r'interactive|technical|game|software|engineer|developer|content creator|social media (manager|creator)|community manager',re.I)
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
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:60]

UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15")
KW=["Senior Producer","Creative Producer","Executive Producer","Branded Content Producer","Content Producer"]
LOC="London%2C%20England%2C%20United%20Kingdom"
def scan():
    found={}
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA); pg=ctx.new_page()
        for kw in KW:
            url=f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw.replace(' ','%20')}&location={LOC}&f_TPR=r1209600&start=0"
            try:
                pg.goto(url,wait_until="domcontentloaded",timeout=30000); pg.wait_for_timeout(700)
                html=pg.content()
                for jid,title,company,locn in re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)".*?base-search-card__title">\s*([^<]+?)\s*</h3>.*?subtitle">\s*<a[^>]*>\s*([^<]+?)\s*</a>.*?location">\s*([^<]+?)\s*</span>',html,re.S):
                    f=fit(title)
                    if f is None: continue
                    found[jid]={"id":"li-"+jid,"company":company.strip().replace('&amp;','&'),"role":title.strip().replace('&amp;','&'),
                                "fit":f,"url":f"https://www.linkedin.com/jobs/view/{jid}"}
            except Exception as e:
                print("scan warn",kw,str(e)[:60])
        b.close()
    return list(found.values())

def main():
    # roll run timestamps
    tq("INSERT INTO meta(k,v) VALUES('prev_run',(SELECT v FROM meta WHERE k='last_run')) ON CONFLICT(k) DO UPDATE SET v=(SELECT v FROM meta WHERE k='last_run')")
    tq("UPDATE meta SET v=datetime('now') WHERE k='last_run'")
    rolesnow=scan()
    print("scanned roles:",len(rolesnow))
    for r in rolesnow:
        tq("INSERT INTO jobs(id,company,role,fit,url,status,source,first_seen,last_seen) VALUES(?,?,?,?,?,'ready','linkedin',datetime('now'),datetime('now')) "
           "ON CONFLICT(id) DO UPDATE SET last_seen=datetime('now'), role=excluded.role, company=excluded.company, "
           "status=CASE WHEN jobs.status='closed' THEN 'ready' ELSE jobs.status END, closed_at=CASE WHEN jobs.status='closed' THEN NULL ELSE jobs.closed_at END",
           [T(r["id"]),T(r["company"]),T(r["role"]),F(r["fit"]),T(r["url"])])
    # only reconcile-close if the scan clearly worked (avoid false closures when LinkedIn blocks the runner)
    if len(rolesnow)>=5:
        tq("UPDATE jobs SET status='closed', closed_at=datetime('now') "
           "WHERE source='linkedin' AND status NOT IN('applied','interviewing','rejected','archived','closed') "
           "AND last_seen < (SELECT v FROM meta WHERE k='last_run')")
    else:
        print("scan returned few results; skipping close-reconciliation this run")
    n=tq("SELECT count(*) c FROM jobs WHERE status NOT IN('closed','archived')")[0]["c"]
    print("active jobs now:",n)

if __name__=="__main__": main()
