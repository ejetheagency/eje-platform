import os, json, datetime
SP=os.path.dirname(__file__)
P=json.load(open(os.path.join(SP,"projection.json")))
routes=P["routes"]; cal=P["calendar"]; prob=P["problems"]; N=P["n_leads"]
CHC={"email":"#2563eb","whatsapp":"#16a34a","instagram":"#c13584","linkedin":"#0a66c2"}
CHL={"email":"email","whatsapp":"WhatsApp","instagram":"Instagram","linkedin":"LinkedIn"}
def esc(s): return (str(s or "")).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def dshort(d):
    try: dt=datetime.date.fromisoformat(d); return "%d %s"%(dt.day,["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][dt.month-1])
    except Exception: return d
def wd(d):
    try: return ["lun","mar","mié","jue","vie","sáb","dom"][datetime.date.fromisoformat(d).weekday()]
    except Exception: return ""
days=sorted(cal.keys())
dayrows=""
for d in days:
    c=cal[d]; tot=sum(c.values()); spike=tot>=30
    segs="".join('<span class="seg" style="flex:%d;background:%s"></span>'%(c[ch],CHC[ch]) for ch in ["email","whatsapp","instagram","linkedin"] if c.get(ch))
    dayrows+='<div class="day%s"><div class="dlabel"><b>%s</b><span>%s</span></div><div class="dbar">%s</div><div class="dtot">%d%s</div></div>'%(
        " spike" if spike else "", esc(dshort(d)), esc(wd(d)), segs, tot, ' <span class="flag">pico</span>' if spike else "")
legend="".join('<span><i style="background:%s"></i>%s</span>'%(CHC[k],CHL[k]) for k in ["email","whatsapp","instagram","linkedin"])
by={}
for r in routes: by.setdefault(r["send_date"],[]).append(r)
REPN={"2026-10-08":"Jue 8 oct","2026-10-09":"Vie 9 oct","2026-10-12":"Lun 12 oct","2026-10-13":"Mar 13 oct","2026-10-14":"Mié 14 oct","2026-10-15":"Jue 15 oct"}
rsec=""
for sd in sorted(by):
    ls=sorted(by[sd],key=lambda z:(z["segment"]!="universidades", z["company"])); rows=""
    for r in ls:
        has=r["has"]
        chips="".join('<span class="have" style="%s">%s</span>'%("" if has.get(k) else "opacity:.2",lab) for k,lab in [("email","@"),("wa","WA"),("ig","IG"),("li","in")])
        tr="".join('<span class="tp" style="--c:%s"><b>%d</b>%s<span class="td">%s</span></span>'%(CHC.get(t["channel"],"#888"),t["t"],esc(CHL.get(t["channel"],t["channel"])[:2]),esc(dshort(t["date"]))) for t in r["touches"])
        seg='<span class="segc %s">%s</span>'%("uni" if r["segment"]=="universidades" else "biz","Universidad" if r["segment"]=="universidades" else "Pyme")
        rows+='<tr><td class="co"><div class="cn">%s</div><div class="ct">%s%s</div></td><td class="ch">%s</td><td class="rt">%s</td></tr>'%(
            esc(r["company"]),seg,'<span class="dec">%s</span>'%esc(r["contact"]) if r.get("contact") else "",chips,tr)
    rsec+='<section class="rep"><h3>%s <span class="rc">%d</span></h3><div class="tw"><table><thead><tr><th>Lead</th><th>Canales</th><th>Ruta · vida útil</th></tr></thead><tbody>%s</tbody></table></div></section>'%(esc(REPN.get(sd,sd)),len(ls),rows)
pure="".join('<li>%s</li>'%esc(x) for x in prob["pure_email"]) or "<li>ninguno</li>"
spikes=[d for d in days if sum(cal[d].values())>=30]
STYLE="""<style>
:root{--bg:#f5f6f8;--card:#ffffff;--ink:#121820;--mut:#5c6774;--line:#e5e8ec;--acc:#0e7490;--win:#15803d;--warn:#b45309;--info:#2563eb;--spike:#b91c1c;--chipbg:#eef1f4}
@media (prefers-color-scheme:dark){:root{--bg:#0e1217;--card:#161c24;--ink:#e7ebf0;--mut:#93a0b0;--line:#232b36;--acc:#22b8cf;--win:#4ade80;--warn:#f59e0b;--info:#60a5fa;--spike:#f87171;--chipbg:#1e2530}}
:root[data-theme=dark]{--bg:#0e1217;--card:#161c24;--ink:#e7ebf0;--mut:#93a0b0;--line:#232b36;--acc:#22b8cf;--win:#4ade80;--warn:#f59e0b;--info:#60a5fa;--spike:#f87171;--chipbg:#1e2530}
:root[data-theme=light]{--bg:#f5f6f8;--card:#ffffff;--ink:#121820;--mut:#5c6774;--line:#e5e8ec;--acc:#0e7490;--win:#15803d;--warn:#b45309;--info:#2563eb;--spike:#b91c1c;--chipbg:#eef1f4}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:38px 22px 70px;display:flex;flex-direction:column;gap:34px}
.eye{font-size:11.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--acc)}
header h1{font-size:clamp(23px,3.4vw,33px);font-weight:760;letter-spacing:-.02em;margin:7px 0 10px;text-wrap:balance;line-height:1.12}
.sub{color:var(--mut);max-width:72ch;font-size:14.5px;margin:0}
h2{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);margin:0 0 14px;padding-bottom:9px;border-bottom:1px solid var(--line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.c{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:17px 18px;border-top:3px solid var(--line)}
.c.win{border-top-color:var(--win)} .c.warn{border-top-color:var(--warn)} .c.info{border-top-color:var(--info)}
.c .n{font-size:34px;font-weight:780;letter-spacing:-.02em;line-height:1}
.c.win .n{color:var(--win)} .c.warn .n{color:var(--warn)} .c.info .n{color:var(--info)}
.c .n span{font-size:17px;color:var(--mut);font-weight:600}
.c .l{font-weight:650;margin:7px 0 5px;font-size:13.5px}
.c .d{color:var(--mut);font-size:12.5px}
.pe{margin:9px 0 0;padding-left:16px;color:var(--mut);font-size:11.5px;columns:1}
.pe li{margin:1px 0}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;font-size:12px;color:var(--mut)}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.days{display:flex;flex-direction:column;gap:5px}
.day{display:grid;grid-template-columns:92px 1fr 72px;align-items:center;gap:12px}
.dlabel b{font-size:13px;font-weight:650} .dlabel span{color:var(--mut);font-size:11px;margin-left:5px}
.dbar{display:flex;height:17px;border-radius:5px;overflow:hidden;background:var(--chipbg)}
.seg{min-width:3px}
.dtot{font-size:12.5px;color:var(--mut);text-align:right}
.day.spike .dtot{color:var(--spike);font-weight:700}
.flag{font-size:9.5px;font-weight:800;color:#fff;background:var(--spike);padding:1px 5px;border-radius:5px;letter-spacing:.04em;text-transform:uppercase}
.note{color:var(--mut);font-size:12px;margin:12px 0 0}
.rep{margin-bottom:18px}
.rep h3{font-size:14px;font-weight:720;margin:0 0 9px;display:flex;align-items:center;gap:8px}
.rep h3 .rc{font-size:11px;font-weight:700;color:var(--mut);background:var(--chipbg);border-radius:20px;padding:2px 9px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;min-width:720px;font-size:12.5px}
th{text-align:left;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--mut);font-weight:700;padding:9px 12px;border-bottom:1px solid var(--line)}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:last-child td{border-bottom:none}
.cn{font-weight:650} .ct{color:var(--mut);font-size:11px;margin-top:2px;display:flex;gap:6px;align-items:center}
.segc{font-size:9.5px;font-weight:700;padding:1px 6px;border-radius:5px;text-transform:uppercase;letter-spacing:.03em}
.segc.uni{background:color-mix(in srgb,var(--acc) 15%,transparent);color:var(--acc)}
.segc.biz{background:color-mix(in srgb,var(--info) 14%,transparent);color:var(--info)}
.dec{color:var(--mut)}
.ch{white-space:nowrap} .have{display:inline-block;font-size:9.5px;font-weight:700;width:22px;text-align:center;padding:2px 0;border-radius:4px;background:var(--chipbg);margin-right:2px;color:var(--ink)}
.rt{white-space:nowrap}
.tp{display:inline-flex;flex-direction:column;align-items:center;gap:1px;margin-right:4px;padding:3px 7px;border-radius:7px;background:color-mix(in srgb,var(--c) 13%,transparent);border:1px solid color-mix(in srgb,var(--c) 30%,transparent);min-width:34px}
.tp b{font-size:9px;color:var(--c);font-weight:800}
.tp{font-size:10.5px;color:var(--c);font-weight:700}
.tp .td{font-size:9px;color:var(--mut);font-weight:600}
footer{color:var(--mut);font-size:11.5px;border-top:1px solid var(--line);padding-top:16px}
@media (max-width:620px){.day{grid-template-columns:72px 1fr 58px}}
</style>
"""
html=STYLE+"""<div class="wrap">
<header>
<div class="eye">Proyección de vida útil · ciclo de contacto</div>
<h1>2uplatam · ruta WhatsApp-forward de cada lead y carga diaria</h1>
<p class="sub">%d leads. Cada lead recorre 6 toques: <b>email → WhatsApp → Instagram → email → LinkedIn → mensual</b>, resueltos al canal que el lead realmente tiene. WhatsApp es ahora el 2º toque (el canal más relevante).</p>
</header>
<section class="cards">
  <div class="c win"><div class="n">%d<span>/%d</span></div><div class="l">leads alcanzados por WhatsApp en la ruta</div><div class="d">Antes era 0 (WhatsApp no estaba en la cadencia). Ahora dispara como 2º toque.</div></div>
  <div class="c warn"><div class="n">%d</div><div class="l">leads puro-email (sin WhatsApp/IG/LinkedIn)</div><div class="d">Todo cae a email. Son universidades sin canal alterno, re-enriquecer o aceptar email-only.</div><ul class="pe">%s</ul></div>
  <div class="c info"><div class="n">%d</div><div class="l">toques que aún caen a email por falta de canal</div><div class="d">Menos multicanal en esos toques puntuales.</div></div>
</section>
<section class="load">
<h2>Carga diaria · toques por día</h2>
<div class="legend">%s</div>
<div class="days">%s</div>
<p class="note">Picos de ~40 toques (%s) cuando se solapan seguimientos de varios reportes. Para suavizar: escalonar envíos o repartir el seguimiento.</p>
</section>
<section class="routes"><h2>Ruta por lead · reporte por reporte</h2>%s</section>
<footer>Generado de la cadencia real del sistema (WhatsApp-forward, no-EJE). El canal de cada toque refleja lo que el lead tiene hoy; re-enriquecer cambia la ruta.</footer>
</div>"""%(N, prob["wa_reach"], N, len(prob["pure_email"]), pure, prob["fallback_email"], legend, dayrows, ", ".join(dshort(d) for d in spikes), rsec)
open(os.path.join(SP,"projection.html"),"w").write(html)
print("wrote projection.html (%d bytes)"%len(html))
