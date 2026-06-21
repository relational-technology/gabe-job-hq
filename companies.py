#!/usr/bin/env python3
"""Target-company scanners. Each fetcher returns (roles, ok): roles is a list of
{source, company, role, url, location, jd}; ok is True if the source responded so the
caller knows it is safe to reconcile-close that source's vanished roles. Endpoints verified
2026-06. Filters to London + producer/creative/content/film leadership titles. No em dashes."""
import re, json, datetime, urllib.request, urllib.parse
def _ms(ms):
    try: return datetime.datetime.utcfromtimestamp(int(ms)/1000).strftime('%Y-%m-%d')
    except Exception: return ""
def _rss_date(s):
    for f in ("%a, %d %b %Y %H:%M:%S %z","%a, %d %b %Y %H:%M:%S %Z"):
        try: return datetime.datetime.strptime(s.strip(),f).strftime('%Y-%m-%d')
        except Exception: pass
    return ""

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15"
def _get(url, headers=None, data=None, timeout=25):
    h={"User-Agent":UA,"Accept":"application/json, text/html, */*"}
    if headers: h.update(headers)
    req=urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8","replace")
def _getj(url, headers=None, data=None, timeout=25): return json.loads(_get(url,headers,data,timeout))
def _strip(html): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html or '')).strip().replace('—','-').replace('–','-')[:3000]

TITLE_RE=re.compile(r'\b(producer|production manager|creative lead|content lead|executive producer|video producer|branded content|head of (film|content|production|video|creative))\b',re.I)
EXCLUDE=re.compile(r'intern|assistant|coordinator|junior|graduate|apprentice|social media|videographer|video editor|content creator|community manager|influencer|ugc|engineer|developer|software|technical|game\b',re.I)
def want(title): return bool(title) and bool(TITLE_RE.search(title)) and not EXCLUDE.search(title)
def is_london(loc): return 'london' in (loc or '').lower()
def slug(s): return re.sub(r'[^a-z0-9]+','-',(s or '').lower()).strip('-')[:50]

def safe(fn, name):
    try:
        roles=fn(); return roles, True
    except Exception as e:
        print(f"  [{name}] FAILED: {str(e)[:120]}"); return [], False

# ---- generic ATS ----
def greenhouse(board, company):
    d=_getj(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    out=[]
    for j in d.get("jobs",[]):
        loc=(j.get("location") or {}).get("name","")
        if not (is_london(loc) and want(j.get("title",""))): continue
        out.append({"source":"gh:"+board,"company":company,"role":j["title"],"url":j.get("absolute_url",""),
                    "location":loc,"jd":_strip(j.get("content","")),"posted":(j.get("updated_at") or "")[:10]})
    return out
def lever(board, company):
    d=_getj(f"https://api.lever.co/v0/postings/{board}?mode=json")
    out=[]
    for j in d:
        loc=(j.get("categories") or {}).get("location","")
        if not (is_london(loc) and want(j.get("text",""))): continue
        out.append({"source":"lever:"+board,"company":company,"role":j["text"],"url":j.get("hostedUrl",""),
                    "location":loc,"jd":_strip(j.get("descriptionPlain") or j.get("description","")),"posted":_ms(j.get("createdAt"))})
    return out

# ---- specific ----
def amazon():
    out=[]
    d=_getj("https://www.amazon.jobs/en/search.json?"+urllib.parse.urlencode(
        {"base_query":"producer","loc_query":"London, England, GBR","country":"GBR","result_limit":100,"sort":"relevant"}))
    for j in d.get("jobs",[]):
        if j.get("country_code")!="GBR" or not is_london(j.get("city","")) or not want(j.get("title","")): continue
        out.append({"source":"amazon","company":"Amazon","role":j["title"],
                    "url":"https://www.amazon.jobs"+j.get("job_path",""),"location":j.get("city",""),
                    "jd":_strip((j.get("description","")+" "+j.get("basic_qualifications",""))),"posted":j.get("posted_date","")})
    return out
def netflix():
    out=[]
    d=_getj("https://explore.jobs.netflix.net/api/apply/v2/jobs?"+urllib.parse.urlencode(
        {"domain":"netflix.com","location":"London, United Kingdom","start":0,"num":40,"sort_by":"relevance"}))
    for j in d.get("positions",[]):
        if not is_london(j.get("location","")) or not want(j.get("name","")): continue
        jd=""
        try: jd=_strip(_getj(f"https://explore.jobs.netflix.net/api/apply/v2/jobs/{j['id']}?domain=netflix.com")["positions"][0].get("job_description",""))
        except Exception: pass
        out.append({"source":"netflix","company":"Netflix","role":j["name"],
                    "url":j.get("canonicalPositionUrl",""),"location":j.get("location",""),"jd":jd})
    return out
def apple():
    html=_get("https://jobs.apple.com/en-gb/search?"+urllib.parse.urlencode(
        {"search":"producer","location":"united-kingdom-GBR","sort":"newest"}))
    m=re.search(r'window\.__staticRouterHydrationData\s*=\s*JSON\.parse\("(.*?)"\);',html,re.S)
    if not m: return []
    data=json.loads(json.loads('"'+m.group(1)+'"'))
    res=(((data.get("loaderData") or {}).get("search") or {}).get("searchResults")) or []
    out=[]
    for j in res:
        locs=j.get("locations") or []
        if not any(is_london(l.get("name","") or l.get("city","")) for l in locs): continue
        if not want(j.get("postingTitle","")): continue
        jid=j.get("id",""); sl=j.get("transformedPostingTitle","")
        out.append({"source":"apple","company":"Apple","role":j["postingTitle"],
                    "url":f"https://jobs.apple.com/en-gb/details/{jid}/{sl}","location":"London","jd":_strip(j.get("jobSummary",""))})
    return out
def snap():
    base="https://snap.wd1.myworkdayjobs.com"
    d=_getj(base+"/wday/cxs/snapchat/snap/jobs",headers={"Content-Type":"application/json","Accept":"application/json"},
            data=json.dumps({"appliedFacets":{"locations":["efe1a8650731012ad1800e7e020a4437"]},"limit":20,"offset":0,"searchText":""}).encode())
    out=[]
    for j in d.get("jobPostings",[]):
        if not is_london(j.get("locationsText","")) or not want(j.get("title","")): continue
        path=j.get("externalPath","")
        jd=""
        try: jd=_strip(json.dumps(_getj(base+"/wday/cxs/snapchat/snap"+path).get("jobPostingInfo",{}).get("jobDescription","")))
        except Exception: pass
        out.append({"source":"snap","company":"Snap","role":j["title"],
                    "url":base+"/en-US/snap"+path,"location":j.get("locationsText",""),"jd":jd})
    return out
def tiktok():
    h={"Content-Type":"application/json","website-path":"tiktok","Referer":"https://lifeattiktok.com/","User-Agent":UA}
    d=_getj("https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts?keyword=producer&limit=50&offset=0",
            headers=h,data=json.dumps({"keyword":"producer","limit":50,"offset":0,"location_code_list":["CT_93"],
            "job_category_id_list":[],"subject_id_list":[],"recruitment_id_list":[]}).encode())
    out=[]
    for j in (d.get("data") or {}).get("job_post_list",[]):
        ci=(j.get("city_info") or {}).get("en_name","")
        if not is_london(ci) or not want(j.get("title","")): continue
        out.append({"source":"tiktok","company":"TikTok","role":j["title"],
                    "url":f"https://lifeattiktok.com/position/{j.get('id','')}","location":ci,
                    "jd":_strip((j.get("description","")+" "+j.get("requirement","")))})
    return out
def bbc():
    xml=_get("https://careers.bbc.co.uk/services/rss/job/?locale=en_GB&keywords="+urllib.parse.quote("(producer OR \"production manager\" OR \"head of content\" OR \"head of production\") AND locationSearch:(london)"))
    out=[]
    for it in re.findall(r'<item>(.*?)</item>',xml,re.S):
        t=re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>',it,re.S)
        link=re.search(r'<link>(.*?)</link>',it,re.S); desc=re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>',it,re.S)
        title=(t.group(1) if t else "").strip()
        if not (want(title) and 'london' in title.lower()): continue
        pub=re.search(r'<pubDate>(.*?)</pubDate>',it,re.S)
        out.append({"source":"bbc","company":"BBC","role":re.sub(r'\s*\(London.*?\)','',title).strip(),
                    "url":(link.group(1).strip() if link else ""),"location":"London","jd":_strip(desc.group(1) if desc else ""),
                    "posted":_rss_date(pub.group(1)) if pub else ""})
    return out
def itv():
    d=_getj("https://careers.itv.com/api/jobs")
    out=[]
    for j in d.get("jobs",[]):
        if not is_london(j.get("location_city","")) or not want(j.get("job_title","")): continue
        out.append({"source":"itv","company":"ITV","role":j["job_title"],"url":j.get("job_url") or j.get("application_url",""),
                    "location":j.get("location_city",""),"jd":_strip(j.get("description_html",""))})
    return out
def channel4():
    html=_get("https://4people.my.salesforce-sites.com/recruit/fRecruit__ApplyJobList?portal=4+Jobs")
    out=[]
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>',html,re.S):
        cells=re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)
        if len(cells)<2: continue
        title=_strip(cells[0]); loc=" ".join(_strip(c) for c in cells[1:])
        vn=re.search(r'vacancyNo=(VN\d+)',row)
        if not vn or not (want(title) and 'london' in loc.lower()): continue
        out.append({"source":"channel4","company":"Channel 4","role":title,
                    "url":f"https://4people.my.salesforce-sites.com/recruit/fRecruit__ApplyJob?vacancyNo={vn.group(1)}&portal=4+Jobs",
                    "location":"London","jd":""})
    return out
def dept():
    out=[]; page=1
    while page<=10:
        d=_getj(f"https://www.deptagency.com/wp-json/dept-gh/v1/fetch-vacancy-listing?rendered-output=true&page={page}&country=united-kingdom&lang=global")
        for h in d.get("jobs",[]):
            city=re.search(r'data-city="([^"]*)"',h); city=city.group(1) if city else ""
            href=re.search(r'href="(/vacancy/[^"]+)"',h); nm=re.search(r'&quot;name&quot;:&quot;([^&]*)&quot;',h)
            title=nm.group(1) if nm else ""
            if not (is_london(city) and want(title)): continue
            out.append({"source":"dept","company":"DEPT","role":title,
                        "url":"https://www.deptagency.com"+(href.group(1) if href else ""),"location":"London","jd":""})
        if d.get("isLastPage"): break
        page+=1
    return out
def ladbible():
    xml=_get("https://jobs.ladbiblegroup.com/jobs.rss")
    out=[]
    for it in re.findall(r'<item>(.*?)</item>',xml,re.S):
        t=re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>',it,re.S)
        city=re.search(r'<tt:city>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</tt:city>',it,re.S)
        link=re.search(r'<link>(.*?)</link>',it,re.S); desc=re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>',it,re.S)
        title=(t.group(1) if t else "").strip(); loc=(city.group(1) if city else "").strip()
        if not (is_london(loc) and want(title)): continue
        pub=re.search(r'<pubDate>(.*?)</pubDate>',it,re.S)
        out.append({"source":"ladbible","company":"LADbible Group","role":title,
                    "url":(link.group(1).strip() if link else ""),"location":loc,"jd":_strip(desc.group(1) if desc else ""),
                    "posted":_rss_date(pub.group(1)) if pub else ""})
    return out
def vevo(): return lever("vevo","Vevo")
def smartrecruiters(co, company):
    d=_getj(f"https://api.smartrecruiters.com/v1/companies/{co}/postings?limit=100")
    out=[]
    for j in d.get("content",[]):
        city=(j.get("location") or {}).get("city","")
        if not (is_london(city) and want(j.get("name",""))): continue
        out.append({"source":"sr:"+co,"company":company,"role":j["name"],
                    "url":f"https://jobs.smartrecruiters.com/{co}/{j.get('id','')}","location":city,
                    "jd":"","posted":(j.get("releasedDate") or "")[:10]})
    return out

SOURCES=[
 ("amazon",amazon),("netflix",netflix),("apple",apple),("snap",snap),("tiktok",tiktok),
 ("spotify",lambda: lever("spotify","Spotify")),
 ("nyt",lambda: greenhouse("thenewyorktimes","The New York Times")),
 ("wk",lambda: greenhouse("wk","Wieden+Kennedy")),
 ("dept",dept),("ladbible",ladbible),("bbc",bbc),("itv",itv),("channel4",channel4),("vevo",vevo),
 ("buzzfeed",lambda: greenhouse("buzzfeed","BuzzFeed")),
 ("condenast",lambda: smartrecruiters("CondeNast","Conde Nast")),
]
NOT_COVERED={"Meta":"aggressive bot-blocking, needs residential IP/Playwright","Pulse Films":"no careers data source exists",
             "Google/YouTube":"internal RPC, brittle","Disney":"custom careers site, not programmatically reachable",
             "Global":"custom careers site, not programmatically reachable"}

def scan_all():
    roles=[]; ok_sources=set()
    for name,fn in SOURCES:
        r,ok=safe(fn,name)
        if ok: ok_sources.add(name)
        for it in r:
            it.setdefault("source",name); it.setdefault("posted","")
        print(f"  [{name}] {len(r)} London role(s)")
        roles+=r
    return roles, ok_sources

if __name__=="__main__":
    rs,ok=scan_all()
    print("\nTOTAL target-company roles:",len(rs),"| sources ok:",len(ok))
    for r in rs[:40]: print(f"  {r['company']:18} | {r['role'][:50]:50} | jd={len(r['jd'])}")
    print("Not covered:",", ".join(NOT_COVERED))
