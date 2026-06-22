#!/usr/bin/env python3
"""Render Gabe's two CV variants to A4 PDF (Chromium), matching the reference layout:
Liberation Sans, full-bleed teal banner, KPI band, teal squared section headings,
Core Skills as pale pills, experience dates as pills, and phrase-level bold (via **markers**).
Single-column, ATS-safe. No em dashes."""
import re
from playwright.sync_api import sync_playwright
import cv_data as D

def md(t): return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
def sec(t): return f'<div class="sec"><span class="sq"></span>{t}</div>'

def html(key,v):
    kpi="".join(f'<div class="kpi"><div class="kn">{n}</div><div class="kl">{l}</div></div>' for n,l in D.KPIS)
    ach="".join(f'<li>{md(a)}</li>' for a in v.get("highlights",D.ACHIEVEMENTS))
    skills="".join(f'<span class="sk">{s}</span>' for s in v["skills"])
    exp=""
    for title,co,date,bl in D.EXPERIENCE:
        bls="".join(f'<li>{md(b)}</li>' for b in bl)
        exp+=f'<div class="job"><div class="jt"><span class="role">{title}</span><span class="date">{date}</span></div><div class="co">{co}</div><ul>{bls}</ul></div>'
    bring="".join(f'<li><b>{h}.</b> {md(d)}</li>' for h,d in D.BRING)
    bring_h="What I Bring to Content at Scale" if key=="bigtech" else "What I Bring"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page{{size:A4;margin:13mm 0;}}
@page:first{{margin-top:0;}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Liberation Sans',Arial,sans-serif;color:#1c2b30;font-size:9.3pt;line-height:1.205}}
.wrap{{padding:0 15mm}}
.banner{{background:#0E7C7B;padding:13mm 15mm 9mm}}
.name{{font-size:23.5pt;font-weight:700;color:#ffffff;letter-spacing:.3px}}
.sub{{font-size:8.3pt;font-weight:700;letter-spacing:2.8px;color:#bdeae6;margin-top:4px}}
.tag{{color:#dcf1ef;margin-top:6px;font-size:9pt}}
.contact{{color:#eaf6f5;margin-top:7px;font-size:8.6pt}}
.rtw{{color:#c3e6e3;font-size:8.3pt;margin-top:3px}}
.kpis{{display:flex;gap:6px;margin:9px 0 2px;border-top:1px solid #d3e7e4;border-bottom:1px solid #d3e7e4;padding:8px 0}}
.kpi{{flex:1;text-align:center}}
.kn{{font-size:16pt;font-weight:700;color:#0E7C7B;line-height:1}}
.kl{{font-size:7pt;letter-spacing:1.2px;text-transform:uppercase;color:#5b6b6b;font-weight:700;margin-top:4px}}
.sec{{font-size:9.2pt;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#0E7C7B;margin:9px 0 5px;padding-bottom:3px;border-bottom:1px solid #d3e7e4;display:flex;align-items:center}}
.sq{{display:inline-block;width:8px;height:8px;background:#0E7C7B;margin-right:9px}}
p.profile{{margin:0}}
ul{{list-style:none}}
li{{position:relative;padding-left:15px;margin-bottom:2.5px}}
li:before{{content:"";position:absolute;left:0;top:6px;width:5px;height:5px;background:#16b5ab;border-radius:50%}}
b{{font-weight:700;color:#16242a}}
.skills{{display:flex;flex-wrap:wrap;gap:5px 7px}}
.sk{{background:#e9f4f2;border:1px solid #d2e7e4;color:#0c5b59;border-radius:13px;padding:2px 10px;font-size:8.6pt}}
.job{{margin-bottom:7px;page-break-inside:avoid}}
.jt{{display:flex;justify-content:space-between;align-items:center}}
.role{{font-weight:700;color:#16242a;font-size:10pt}}
.date{{background:#e9f4f2;color:#566;border-radius:13px;padding:2px 11px;font-size:8.2pt;font-weight:400;white-space:nowrap}}
.co{{color:#0E7C7B;font-weight:700;margin:2px 0 5px;font-size:9pt}}
.brands{{color:#2c3b40}}
.endline{{margin-bottom:2px}}
</style></head><body>
<div class="banner">
<div class="name">{D.NAME}</div>
<div class="sub">{v['subtitle']}</div>
<div class="tag">{v['tagline']}</div>
<div class="contact">{D.CONTACT}</div>
<div class="rtw">{D.RTW}</div>
</div>
<div class="wrap">
<div class="kpis">{kpi}</div>
{sec('Profile')}<p class="profile">{md(v['profile'])}</p>
{sec('Key Achievements')}<ul>{ach}</ul>
{sec('Core Skills')}<div class="skills">{skills}</div>
{sec('Selected Brands')}<div class="brands">{D.BRANDS}</div>
{sec('Experience')}{exp}
{sec(bring_h)}<ul>{bring}</ul>
{sec('Tools & Technology')}<div class="endline">{D.TOOLS}</div>
{sec('Languages')}<div class="endline">{D.LANGUAGES}</div>
{sec('Education')}<div class="endline">{D.EDUCATION}</div>
</div>
</body></html>"""

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page()
        for key,v in D.VARIANTS.items():
            pg.set_content(html(key,v),wait_until="networkidle")
            pg.pdf(path=v["file"]+".pdf",format="A4",print_background=True,prefer_css_page_size=True)
            print("wrote",v["file"]+".pdf")
        b.close()

if __name__=="__main__": main()
