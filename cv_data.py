#!/usr/bin/env python3
"""Single source of truth for Gabe Paoli's CV, formatted to match his preferred reference
layout exactly (Liberation Sans, teal banner, KPI band, Core Skills pills, dated pills,
phrase-level bold via **markers**). Two targeted variants differ only in subtitle, tagline,
profile and core skills:
- bigtech: scale, content operations, AI, cross-functional (Meta/Amazon/TikTok/Apple/Netflix/Prime/YouTube)
- media:   creative leadership, storytelling, brand work (BBC/ITV/Conde Nast/Pulse/LADbible/Vevo/Disney)
Rolls-Royce appears once (IDX). No em dashes."""

import os, subprocess
NAME="Gabe Paoli"
def _contact():
    v=os.environ.get("CV_CONTACT")
    if v: return v
    try:
        o=subprocess.check_output(["bash","-lc","grep '^CV_CONTACT=' ~/.aura-ops-secrets|head -1"]).decode()
        x=o.split("=",1)[1].strip().strip('"').strip("'")
        if x: return x
    except Exception: pass
    # public default keeps the phone number OUT of the repo (full contact comes from the CV_CONTACT secret)
    return "London, UK &nbsp;•&nbsp; gabepaoli@gmail.com &nbsp;•&nbsp; linkedin.com/in/gabrielepaoli &nbsp;•&nbsp; gabrielepaoli.com/work"
CONTACT=_contact()
RTW="Right to work: UK &amp; EU (no sponsorship required)"
KPIS=[("500+","Campaigns delivered"),("1,200+","Events supported"),("20+","Markets localised"),("£2M","Largest budget")]

ACHIEVEMENTS=[
 "Scaled multi-market delivery to **20+ markets** with reusable localisation frameworks, cutting rework on high-volume campaigns.",
 "Cut **£87K** in external production spend while improving delivery speed and quality.",
 "Grew audience **30%** and revenue **20%** in six months by building a new commercial content strategy.",
 "Saved an estimated **200 staff hours per quarter** by re-engineering repeat production workflows.",
]
BRANDS="Under Armour, IKEA, Heineken, L'Oreal Paris, Vogue, Vanity Fair, Sony Music, Warner Music, Nike, Ray-Ban, KFC, Domino's, Sainsbury's, NHS, Royal Navy, Bvlgari"
EXPERIENCE=[
 ("Senior Producer / Deputy Head of Film","IDX (Investcorp), London","Jan 2020 - Present",[
   "Lead **end-to-end production** for integrated film, branded content, animation, social and digital campaigns for global blue-chip clients including **Vodafone**, from brief and creative development through final delivery.",
   "Delivered **500+ campaigns** and supported **1,200+ events** across **EMEA, APAC and the US**, balancing premium brand craft with high-volume, repeatable delivery.",
   "Own **budgets up to £2M**, controlling scope, vendors, **SOW negotiation**, schedules and delivery risk.",
   "Built global production toolkits and **localisation frameworks** adopted across **20+ markets**, standardising quality and reducing rework.",
   "Lead a **hybrid team** of 5 staff and **30+ freelance specialists** across creative, shoot, animation, edit, versioning and delivery.",
   "Introduced **AI-supported workflows** for localisation, versioning and platform-native adaptation, increasing content velocity while protecting brand, legal and quality standards.",
   "Partner **cross-functionally** with marketing, strategy and social teams to adapt assets for **LinkedIn, Instagram, YouTube, TikTok** and paid media.",
 ]),
 ("Senior Producer · Contract","Greenpark, London","Aug 2019 - Oct 2019",[
   "Delivered **40+ international campaigns** across the UAE, Asia and the US.",
   "Built localisation and production playbooks that improved consistency across multi-market adaptations.",
   "Partnered with sales and account teams on pitch scoping and feasibility, helping win **15+ new-business opportunities** including **Unilever and Adidas**.",
   "Contributed to **20% Q4 revenue growth** through portfolio expansion and multi-market package upsell.",
 ]),
 ("Head of Commercial Video","Reach PLC (Daily Mirror), London","Oct 2018 - May 2019",[
   "Built and executed a new commercial video and content strategy from the ground up, growing **audience 30%** and **revenue 20%** in six months.",
   "Managed and mentored a **15+ person** creative team, reducing external production spend by **£87K** while improving delivery speed and quality.",
   "Led **50+ commercial and branded productions** across digital, social and OOH for the Daily Mirror, Daily Express, Daily Star, OK! and regional titles.",
 ]),
 ("Commercial Video Producer · Contract","Global (Capital), London","Jun 2018 - Aug 2018",[
   "Delivered **35+ branded campaigns** in four months across digital, social and commercial video.",
   "Produced platform-native content for **TikTok, Snap, Meta, YouTube and X**.",
   "Directed shoots with **30+ crew**, overseeing logistics, budgets and on-set operations.",
   "Negotiated and applied industry production standards including markups, crew rates and **SAG/non-union rules**.",
 ]),
 ("Creative Producer","XYZ (160over90), London","Sep 2014 - Apr 2018",[
   "Produced integrated campaigns for **Nike, Ray-Ban** and international lifestyle brands across digital, social and branded content.",
   "Maintained brand and craft consistency across recurring digital and social formats for premium lifestyle clients.",
   "Re-engineered repeat production workflows, saving an estimated **200 staff hours per quarter** across recurring campaign formats.",
 ]),
 ("Video Producer · Freelance","MTV (Viacom, now Paramount), Italy and London","Sep 2006 - Jul 2014",[
   "Produced **350+ campaigns** and managed **1,000+ shoots** across EMEA with budgets up to **£1M**.",
   "Owned projects end to end, from development and filming through post-production and final delivery.",
   "Standardised recurring formats into repeatable processes, reducing delivery timelines across high-volume output.",
 ]),
]
BRING=[
 ("Systems, not one-offs","Reusable production toolkits and localisation frameworks that hold quality across **20+ markets** and reduce rework on high-volume delivery."),
 ("Cross-functional by default","Fluent partnering with marketing, strategy, social, account and executive stakeholders, translating ambiguous briefs into scoped, on-time delivery."),
 ("AI-enabled, human oversight","Hands-on AI workflows for localisation, versioning and platform-native adaptation, with production control on brand, legal, craft and risk."),
 ("Operator's discipline","Budgets to **£2M**, vendor and SOW negotiation, and program management of scope, schedule and delivery risk."),
]
TOOLS="Adobe Creative Suite, Frame.io, Monday.com, Smartsheet, Figma, CapCut, Canva, Google Workspace, Slack, AI production tools"
LANGUAGES="English (native), Italian (native), French (advanced), Spanish (intermediate)"
EDUCATION="Film &amp; TV Production, Roma Film Academy (ex NUCT), Rome &nbsp;|&nbsp; Film &amp; Media Studies, Alma Mater Studiorum University of Bologna"

VARIANTS={
 "bigtech":{
   "file":"Gabe-Paoli-CV-BigTech",
   "subtitle":"SENIOR PRODUCER / CREATIVE & CONTENT OPERATIONS LEAD",
   "tagline":"Premium creative production and content operations at scale, for global brands and platforms",
   "profile":("Senior producer with **15+ years** across **premium creative production** and large-scale content operations for global "
     "brands in **EMEA, APAC and the US**. My edge is the combination: **creative instinct** and **production craft** paired with the "
     "systems that ship at scale, reusable toolkits, **localisation frameworks** and **AI-supported workflows**, backed by confident "
     "**client-facing leadership**. I own **budgets up to £2M**, lead hybrid staff-and-freelance teams, and partner **cross-functionally** "
     "with marketing, product, strategy and executive stakeholders, turning ambitious ideas into work that ships on time, on budget and on brand."),
   "skills":["Premium creative production","Content operations at scale","Brand & film craft","AI-supported workflows",
     "Cross-functional leadership","Program & delivery management","Localisation across 20+ markets","Client & stakeholder management",
     "Platform-native social video","Vendor, SOW & budget ownership","Global campaign delivery","Team & freelance leadership"],
   "highlights":[
     "Produced Rolls-Royce's record-breaking **Spirit of Innovation** launch, the world's first all-electric flight record: **25M+ reach** and **500+ press placements** in 72 hours, now a permanent **Science Museum** exhibit.",
     "Scaled delivery to **20+ markets** with reusable production systems and **AI-supported workflows**, protecting craft and quality at high volume.",
     "A rare hybrid: premium creative production plus operational leadership, trusted with **£2M** budgets and senior client relationships.",
   ],
 },
 "media":{
   "file":"Gabe-Paoli-CV-Media",
   "subtitle":"SENIOR CREATIVE PRODUCER / CONTENT & BRAND STORYTELLER",
   "tagline":"Premium film, branded content and social-first storytelling for brands, broadcasters and culture",
   "profile":("Creative producer and storyteller with **15+ years** making **premium brand films**, branded content and "
     "**social-first stories** for global names across **EMEA, APAC and the US**. I live where **strong ideas** meet flawless craft: "
     "shaping concepts, partnering with **directors and talent**, and protecting the **creative vision** from pitch through shoot, edit "
     "and final cut. I have built and led **creative teams**, held **editorial and brand** standards side by side, and turned cultural "
     "insight into work that earns attention, travels across platforms and still feels premium at scale."),
   "skills":["Creative direction & production","Storytelling & brand building","Premium film & branded content","Talent & director partnerships",
     "Editorial & cultural awareness","Visual craft & creative judgement","Social-first storytelling","Concept & pitch development",
     "Creative team leadership","Multi-market campaign delivery","Client & stakeholder management","Platform-native video"],
   "highlights":[
     "Produced Rolls-Royce's **Spirit of Innovation** launch, a world-record film moment: **25M+ reach** and **500+ press placements** in 72 hours, now in the **Science Museum**.",
     "Premium brand storytelling for **Nike, Vodafone, Vogue, Ray-Ban and Bvlgari**, from concept and pitch through shoot to final cut.",
     "Built and led creative teams, partnering with **directors and talent** to turn ideas into standout film and social content.",
   ],
 },
}
