#!/usr/bin/env python3
"""Generate BESPOKE cover letters + DMs for roles that still need one, using `claude -p`
headless (your Claude subscription via CLAUDE_CODE_OAUTH_TOKEN). Reads each role's stored
job description from Turso, batches roles per call (overhead paid once), writes pack back.
Self-healing: only fills roles missing a pack, never regenerates. No em dashes in output.
Creds from env or ~/.aura-ops-secrets: TURSO_TOKEN, TURSO_DB, CLAUDE_OAUTH_TOKEN."""
import os, re, json, subprocess, urllib.request

def cred(k):
    v=os.environ.get(k)
    if v: return v
    try:
        o=subprocess.check_output(["bash","-lc",f"grep '^{k}=' ~/.aura-ops-secrets|head -1"]).decode()
        return o.split("=",1)[1].strip().strip('"').strip("'")
    except Exception: return ""
TOKEN=cred("TURSO_TOKEN"); EP=re.sub(r'^(libsql|wss)://','https://',cred("TURSO_DB"))
if not EP.startswith("http"): EP="https://"+EP
OAUTH=cred("CLAUDE_OAUTH_TOKEN") or cred("CLAUDE_CODE_OAUTH_TOKEN")
BATCH=int(os.environ.get("LETTER_BATCH","4")); MAX_ROLES=int(os.environ.get("MAX_ROLES","60"))
MODEL=os.environ.get("LETTER_MODEL","haiku")

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

PROFILE=("Gabe Paoli, senior producer and content-operations lead, 15+ years. Senior Producer and Deputy Head of Film at IDX "
 "(Investcorp), London. Delivers integrated film, branded content and social at scale for global brands (Vodafone, Nike, "
 "Under Armour, Vogue), owning budgets up to 2M pounds across 500+ campaigns and 20+ markets, with reusable production systems "
 "and AI-supported workflows that hold quality at volume. Runs work from pitch to same-day global launch across production, "
 "creative, marketing and executive comms. One standout: produced Rolls-Royce's record-breaking Spirit of Innovation launch "
 "(25M+ reach). Right to work UK and EU, no sponsorship. London-based, one month notice.")

def claude(prompt):
    if not OAUTH: raise RuntimeError("no CLAUDE_OAUTH_TOKEN")
    env=os.environ.copy(); env["CLAUDE_CODE_OAUTH_TOKEN"]=OAUTH
    r=subprocess.run(["claude","-p",prompt,"--model",MODEL,"--output-format","json","--max-turns","2","--allowed-tools",""],
                     capture_output=True,text=True,env=env,timeout=300)
    if r.returncode!=0: raise RuntimeError("claude -p failed: "+(r.stderr or r.stdout)[:200])
    env_out=json.loads(r.stdout); text=env_out.get("result","") if isinstance(env_out,dict) else r.stdout
    m=re.search(r'\[.*\]',text,re.S)
    return json.loads(m.group(0) if m else text)

def clean(s): return str(s).replace("—","-").replace("–","-")

def gen_batch(rows):
    lines=[]
    for r in rows:
        lines.append(f"- id: {r['id']}\n  company: {r['company']}\n  role: {r['role']}\n  description: {(r.get('jd') or '')[:1800]}")
    prompt=("Do not use any tools, web search or file access. Work only from the text provided below.\n\n"
      "You assess fit and write bespoke job application materials for "+PROFILE+"\n\n"
      "For EACH role below: score how well it suits Gabe, then write a tailored cover letter and a short LinkedIn DM, "
      "grounded in that role's description (if a description is missing, use the title and company). "
      "Use British English and absolutely NO em dashes (use commas or full stops).\n"
      "Return ONLY a JSON array, one object per role, no prose around it:\n"
      '[{"id":"<id>","fit":<integer 1-10>,"rationale":"<one short sentence>","salary":"<band>","letter":"<letter>","dm":"<dm>"}]\n'
      "salary: if the description states a salary, return it exactly (e.g. £55,000 - £65,000). If not, give your best estimate of the "
      "London market band for this role and seniority, formatted like 'est. £60k - £75k'. Keep it short.\n"
      "fit: integer 1 to 10 for how well the role suits Gabe (a senior producer of film, branded content and social at scale, "
      "budgets to 2M pounds, big-brand and big-tech level). Score senior or lead or executive producer, head of film/content/production, "
      "and branded content or experiential producer roles HIGH (8-10). Score mid roles 6-7. Score junior, purely social-media, or "
      "off-discipline roles LOW (1-4). Be honest and discriminating, do not give everything 8.\n"
      "rationale: one short sentence on why it fits or does not.\n"
      "letter: 150 to 200 words, begins 'Dear <company> team,', references one or two concrete details, ends with 'Best,' then a newline then 'Gabe Paoli'.\n"
      "dm: 40 to 60 words, begins 'Hi [NAME],', names the <role> role, offers to share his reel and a one-pager.\n\n"
      "ROLES:\n"+"\n".join(lines))
    out=claude(prompt)
    by={o["id"]:o for o in out if isinstance(o,dict) and "id" in o}
    n=0
    for r in rows:
        o=by.get(r["id"])
        if not o or not o.get("letter"): print("  miss",r["company"]); continue
        pack={"letter":clean(o["letter"]),"dm":clean(o.get("dm","")),"contacts":[],
              "recipe":f"Search LinkedIn for the hiring manager, talent lead or head of content at {r['company']}, then send the DM above."}
        try: fitv=max(1.0,min(10.0,float(o.get("fit") or 7)))
        except Exception: fitv=7.0
        sal=clean(o.get("salary","")).replace('–','-')[:40]
        tq("UPDATE jobs SET fit=?, notes=?, pack=?, salary=COALESCE(NULLIF(salary,''),?), updated_at=datetime('now') WHERE id=?",
           [{"type":"float","value":fitv},{"type":"text","value":clean(o.get("rationale",""))},
            {"type":"text","value":json.dumps(pack)},{"type":"text","value":sal},{"type":"text","value":r["id"]}])
        n+=1; print(f"  wrote: {r['company']} - {r['role']} (fit {fitv:.0f})")
    return n

def main():
    pending=tq("SELECT id,company,role,jd FROM jobs WHERE (pack IS NULL OR pack='') "
               "AND status NOT IN('closed','archived') ORDER BY fit DESC LIMIT "+str(MAX_ROLES))
    print("roles needing a bespoke letter:",len(pending))
    total=0
    for i in range(0,len(pending),BATCH):
        batch=pending[i:i+BATCH]; print(f"batch {i//BATCH+1} ({len(batch)} roles)...")
        try: total+=gen_batch(batch)
        except Exception as e: print("  batch warn:",str(e)[:160])
    print("bespoke letters written:",total)
    print("still pending:",tq("SELECT count(*) c FROM jobs WHERE source='linkedin' AND (pack IS NULL OR pack='') AND jd IS NOT NULL AND jd!=''")[0]["c"])

if __name__=="__main__": main()
