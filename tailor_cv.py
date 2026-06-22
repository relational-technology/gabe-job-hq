#!/usr/bin/env python3
"""Auto-tailor Gabe's CV to each high-fit (green, fit>=7) and well-paid (>= MIN) role that
has a job description and is not yet tailored. Uses claude -p (Haiku, subscription) to choose
the base variant and truthfully rewrite profile, skills and highlights to mirror the job, then
renders a tailored CV PDF + ATS Word and caches both in Turso (table 'tailored'). Tailored
once per role, never re-run. No invented experience. No em dashes."""
import os, re, json, base64, tempfile
from playwright.sync_api import sync_playwright
from gen_letters import claude, tq
import generate_cv_pdf as GP
import generate_cv_docx as GD
import cv_data as D

MIN=int(os.environ.get("TAILOR_MIN","50000")); BATCH=3; LIMIT=int(os.environ.get("TAILOR_LIMIT","40"))
def low(s):
    if not s: return 0
    mm=re.search(r'£\s?(\d+(?:\.\d+)?)\s?(k?)', re.sub(',','',str(s)).lower())
    if not mm: return 0
    n=float(mm.group(1))
    return n*1000 if (mm.group(2) or n<1000) else n

MASTER=("Gabe Paoli, senior producer, 15+ years, London. Right to work UK and EU, one month notice.\n"
 "Experience (do not change facts): Senior Producer / Deputy Head of Film, IDX (Investcorp), 2020-present: lead end-to-end "
 "production of film, branded content, animation and social for global clients including Vodafone; 500+ campaigns and 1,200+ "
 "events across EMEA, APAC and the US; budgets to 2M pounds; localisation across 20+ markets; AI-supported workflows; hybrid "
 "team of 5 staff and 30+ freelancers. Senior Producer, Greenpark, 2019: 40+ international campaigns, helped win 15+ new-business "
 "incl Unilever and Adidas. Head of Commercial Video, Reach PLC (Daily Mirror), 2018-19: built new commercial video strategy, "
 "audience +30%, revenue +20%, cut £87K, led 15+ team, 50+ productions. Commercial Video Producer, Global (Capital), 2018: 35+ "
 "branded campaigns, platform-native for TikTok/Snap/Meta/YouTube/X, directed 30+ crew. Creative Producer, XYZ (160over90), "
 "2014-18: Nike, Ray-Ban, saved 200 staff hours per quarter. Video Producer (Freelance), MTV (Viacom, now Paramount), 2006-14: "
 "350+ campaigns, 1,000+ shoots, budgets to 1M pounds.\n"
 "Standout: Rolls-Royce Spirit of Innovation, world-first all-electric flight record, 25M+ reach, 500+ press placements in 72 "
 "hours, now a permanent Science Museum exhibit.\n"
 "Brands: Vodafone, Nike, Ray-Ban, Vogue, Vanity Fair, Bvlgari, Under Armour, IKEA, Heineken, Sony Music, Warner Music, MTV, "
 "KFC, Domino's, Sainsbury's, NHS, Royal Navy.\n"
 "Two base angles: bigtech (scale, content operations, AI, cross-functional leadership) and media (creative leadership, "
 "storytelling, premium brand and editorial craft).")

def tailor_batch(rows):
    lines=[f"- id: {r['id']}\n  role: {r['role']} at {r['company']}\n  description: {(r.get('jd') or '')[:2000]}" for r in rows]
    prompt=("Do not use any tools. Tailor Gabe's CV to each job below, truthfully. Use ONLY the facts in his profile, never invent "
      "experience, titles or numbers. British English, absolutely no em dashes.\n\nGABE PROFILE:\n"+MASTER+"\n\n"
      "For EACH job return: variant ('bigtech' or 'media', whichever fits the company and role); subtitle (UPPERCASE, role-aligned, "
      "like 'SENIOR PRODUCER / CONTENT OPERATIONS LEAD'); tagline (one short line); profile (4 to 5 sentences in first person that "
      "mirror this job's language and priorities and lead with his most relevant strengths); skills (exactly 12 short skill phrases, "
      "reordered and reworded to match this job's requirements, all real); highlights (exactly 3 short bullet strings, the most "
      "relevant proof, include the Rolls-Royce standout where it fits). In profile and highlights wrap key metrics and phrases in "
      "**double asterisks** for bold.\n"
      'Return ONLY a JSON array: [{"id":"..","variant":"bigtech","subtitle":"..","tagline":"..","profile":"..","skills":[".."],"highlights":["..","..",".."]}]\n\n'
      "JOBS:\n"+"\n".join(lines))
    return {o["id"]:o for o in claude(prompt) if isinstance(o,dict) and o.get("id")}

def render_pdf(pg,key,v):
    pg.set_content(GP.html(key,v),wait_until="networkidle")
    f=tempfile.NamedTemporaryFile(suffix=".pdf",delete=False).name
    pg.pdf(path=f,format="A4",print_background=True,prefer_css_page_size=True)
    return f

def main():
    tq("CREATE TABLE IF NOT EXISTS tailored(job_id TEXT PRIMARY KEY, company TEXT, pdf TEXT, docx TEXT, updated_at TEXT DEFAULT (datetime('now')))")
    have={r["job_id"] for r in tq("SELECT job_id FROM tailored")}
    rows=tq("SELECT id,company,role,jd,salary FROM jobs WHERE fit>=7 AND status NOT IN('closed','archived') AND jd IS NOT NULL AND jd!='' ORDER BY fit DESC LIMIT "+str(LIMIT))
    todo=[r for r in rows if r["id"] not in have and low(r.get("salary"))>=MIN]
    print(f"green + >=£{MIN//1000}k roles to tailor:",len(todo))
    if not todo: return
    done=0
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page()
        for i in range(0,len(todo),BATCH):
            batch=todo[i:i+BATCH]
            try: res=tailor_batch(batch)
            except Exception as e: print("  batch warn",str(e)[:90]); continue
            for r in batch:
                o=res.get(r["id"])
                if not o or not o.get("profile"): print("  miss",r["company"]); continue
                key=o.get("variant","bigtech"); key='media' if key not in('bigtech','media') else key
                v={"file":tempfile.gettempdir()+"/tcv","subtitle":o.get("subtitle",D.VARIANTS[key]["subtitle"]),
                   "tagline":o.get("tagline",D.VARIANTS[key]["tagline"]),"profile":o["profile"],
                   "skills":(o.get("skills") or D.VARIANTS[key]["skills"])[:12],
                   "highlights":(o.get("highlights") or D.VARIANTS[key]["highlights"])[:3]}
                try:
                    pdff=render_pdf(pg,key,v)
                    GD.build(key,v)  # writes /tmp/tcv.docx
                    pdf_b=base64.b64encode(open(pdff,"rb").read()).decode()
                    docx_b=base64.b64encode(open(v["file"]+".docx","rb").read()).decode()
                    tq("INSERT INTO tailored(job_id,company,pdf,docx,updated_at) VALUES(?,?,?,?,datetime('now')) "
                       "ON CONFLICT(job_id) DO UPDATE SET pdf=excluded.pdf, docx=excluded.docx, updated_at=datetime('now')",
                       [{"type":"text","value":r["id"]},{"type":"text","value":r["company"]},
                        {"type":"text","value":pdf_b},{"type":"text","value":docx_b}])
                    os.unlink(pdff); done+=1; print(f"  tailored: {r['company']} - {r['role'][:34]} ({key})")
                except Exception as e: print("  render warn",r["company"],str(e)[:80])
        b.close()
    print("tailored CVs created this run:",done)

if __name__=="__main__": main()
