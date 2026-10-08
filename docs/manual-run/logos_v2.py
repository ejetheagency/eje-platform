# Real logo per lead: scrape the site's apple-touch-icon (square brand logo); fallback to Google favicon sz=128
# (always resolves, passes the app's 40px quality gate). Universities use their institutional domain.
import sys, os, re, json, urllib.request, urllib.parse
sys.path.insert(0, "/Users/jofreeyzaguirre/claude/unabase-app")
from factory.packages import db
from concurrent.futures import ThreadPoolExecutor
CID="2uplatam"
def host(url, lid):
    u=(url or "").strip()
    if u:
        h=re.sub(r'^https?://','',u).split('/')[0]; h=h[4:] if h.startswith('www.') else h
        if '.' in h and ' ' not in h: return h
    if lid and '.' in lid and not lid.startswith(('uni','lib')): return lid
    return ""
def absu(href, base):
    if href.startswith('//'): return 'https:'+href
    if href.startswith('http'): return href
    if href.startswith('/'): return base.rstrip('/')+href
    return base.rstrip('/')+'/'+href
def best_logo(dom):
    fav='https://www.google.com/s2/favicons?domain=%s&sz=128'%dom
    for base in ['https://'+dom,'https://www.'+dom]:
        try:
            req=urllib.request.Request(base,headers={'User-Agent':'Mozilla/5.0'})
            html=urllib.request.urlopen(req,timeout=10).read(200000).decode('utf-8','ignore')
        except Exception: continue
        for pat in [r'<link[^>]+rel=["\'][^"\']*apple-touch-icon[^"\']*["\'][^>]+href=["\']([^"\']+)',
                    r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'][^"\']*apple-touch-icon']:
            m=re.search(pat,html,re.I)
            if m: return absu(m.group(1).strip(), base)
        break
    return fav  # reliable square favicon
rows=db.select_all("leads","client_id=eq.%s&select=id,company,lead_data"%CID)
leads=[x for x in rows if (x.get('lead_data') or {}).get('approved')]
tasks={}
for x in leads:
    ld=x.get('lead_data') or {}
    dom=host(ld.get('website'), x['id'])
    if dom: tasks[x['id']]=dom
uniq=sorted(set(tasks.values()))
print("resolving logos for %d unique domains"%len(uniq))
cache={}
with ThreadPoolExecutor(max_workers=14) as ex:
    for d,res in zip(uniq, ex.map(best_logo, uniq)): cache[d]=res
setn=real=0
for x in leads:
    ld=x.get('lead_data') or {}; dom=tasks.get(x['id'])
    if not dom: continue
    logo=cache.get(dom)
    if not logo: continue
    ld['logo']=logo
    if 'google.com/s2' not in logo: real+=1
    db.update("leads","id=eq.%s&client_id=eq.%s"%(urllib.request.quote(x['id'],safe=''),CID),{'lead_data':ld}); setn+=1
print("set logos on %d leads (%d real apple-touch-icon, %d favicon fallback)"%(setn,real,setn-real))
ap=[x for x in db.select_all("leads","client_id=eq.%s&select=lead_data"%CID) if (x.get('lead_data') or {}).get('approved')]
print("LOGO coverage: %d/%d"%(sum(1 for x in ap if (x.get('lead_data') or {}).get('logo')),len(ap)))
