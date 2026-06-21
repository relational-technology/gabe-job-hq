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

PROFILE=("Gabe Paoli, senior producer, 15+ years. Senior Producer and Deputy Head of Film at IDX (Investcorp), London. "
 "Flagship: produced Rolls-Royce 'Spirit of Innovation', the world-record all-electric aircraft launch: 25M+ reach, "
 "500+ press placements in 72 hours, now a permanent Science Museum exhibition. Brands: Vodafone, Spotify, Nike, Bvlgari, Vogue. "
 "Budgets up to 2M pounds; 500+ campaigns delivered; grew client revenue 700%+. Runs work from first pitch to same-day global "
 "launch across production, creative, marketing and AI tooling. Right to work UK and EU, no sponsorship. London-based.")

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
      "You write bespoke job application materials for "+PROFILE+"\n\n"
      "For EACH role below, write a tailored cover letter and a short LinkedIn DM, grounded in that role's description. "
      "Use British English and absolutely NO em dashes (use commas or full stops).\n"
      "Return ONLY a JSON array, one object per role, no prose around it:\n"
      '[{"id":"<id>","letter":"<letter>","dm":"<dm>"}]\n'
      "letter: 150 to 200 words, begins 'Dear <company> team,', references one or two concrete details from the description, "
      "ends with 'Best,' then a newline then 'Gabe Paoli'.\n"
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
        tq("UPDATE jobs SET pack=?, updated_at=datetime('now') WHERE id=?",
           [{"type":"text","value":json.dumps(pack)},{"type":"text","value":r["id"]}])
        n+=1; print(f"  wrote: {r['company']} - {r['role']}")
    return n

def main():
    pending=tq("SELECT id,company,role,jd FROM jobs WHERE source='linkedin' AND (pack IS NULL OR pack='') "
               "AND jd IS NOT NULL AND jd!='' ORDER BY fit DESC LIMIT "+str(MAX_ROLES))
    print("roles needing a bespoke letter:",len(pending))
    total=0
    for i in range(0,len(pending),BATCH):
        batch=pending[i:i+BATCH]; print(f"batch {i//BATCH+1} ({len(batch)} roles)...")
        try: total+=gen_batch(batch)
        except Exception as e: print("  batch warn:",str(e)[:160])
    print("bespoke letters written:",total)
    print("still pending:",tq("SELECT count(*) c FROM jobs WHERE source='linkedin' AND (pack IS NULL OR pack='') AND jd IS NOT NULL AND jd!=''")[0]["c"])

if __name__=="__main__": main()
