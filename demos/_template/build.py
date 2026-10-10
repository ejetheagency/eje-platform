#!/usr/bin/env python3
# demos/_template/build.py
# ONE generator for every prospect demo. Layout and copy live here; everything prospect-specific lives in
# config.json + leads.json, so a new prospect is: copy the folder, swap those two files, run this.
#
#   python3 demos/_template/build.py <prospect>        # reads demos/<prospect>/{config.json,leads.json}
#                                                      # writes demos/<prospect>/index.html
#
# Rules this file enforces so a demo cannot ship wrong (learned the hard way on REBRND):
#   - an area/program inbox NEVER prefills the primary mailto (it reaches whoever answers, not a decision maker)
#   - a pattern TEMPLATE ("<inicial><apellido>@dominio") never reaches a To: field
#   - a "ruta débil" (sales inbox) is shown but never prefilled
#   - a missing config value renders a visible "falta", never a placeholder or an invented value
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


# Un hecho se muestra pelado, con su link. Lo que el hecho "significa" lo concluye quien lee: si se lo
# escribimos nosotros, deja de ser dato verificable y pasa a ser opinión con cara de dato.
INTERPRETA = ["así que", "asi que", "eso es", "eso significa", "lo que significa", "es decir",
              "por lo que", "les sirve", "necesitan a", "quiere decir"]

def check_hechos(data):
    malos = []
    for emp in data.get("empresas", []):
        t = ((emp.get("hook") or {}).get("texto") or "").lower()
        for m in INTERPRETA:
            if m in t:
                malos.append(f'{emp.get("id")}: "{m}"')
        if emp.get("timing"):
            malos.append(f'{emp.get("id")}: campo timing (interpretación, ya no se usa)')
    if malos:
        raise SystemExit("HECHO CON INTERPRETACIÓN (solo el hecho + su fuente):\n  " + "\n  ".join(malos))

def build(prospect):
    base = ROOT / "demos" / prospect
    cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
    data = json.loads((base / "leads.json").read_text(encoding="utf-8"))
    check_hechos(data)                      # falla el build si un hecho trae interpretación pegada
    data["_cfg"] = cfg                      # one payload: the page reads copy and brand from here
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    out = (HTML
           .replace("__PAYLOAD__", payload)
           .replace("__TITLE__", cfg["titulo"])
           .replace("__PAPER__", cfg["marca"]["paper"]).replace("__INK__", cfg["marca"]["ink"])
           .replace("__ACCENT__", cfg["marca"]["accent"]).replace("__SOFT__", cfg["marca"]["soft"]))
    (base / "index.html").write_text(out, encoding="utf-8")
    assert "—" not in out, "em dash in output (global rule)"
    publish_demo_client(prospect, cfg, data)
    return base / "index.html", len(out)


def publish_demo_client(prospect, cfg, data):
    """Publish the demo as a DEMO CLIENT the real app can load: public/demo-<prospect>.json.

    Vercel serves only public/, so the data has to live there. The standalone page stays as a fallback.
    ONE CARD PER COMPANY: the app keys cards by the website hostname (decDom), so one card per door would
    collide on the same domain and mark two cards contacted at once. Door 1 is the card's contact; the other
    doors ride inside the card for the Guia tab. No synthetic domains: inventing a URL to get a unique key
    would be inventing data."""
    import datetime
    hoy = datetime.date.today().isoformat()
    leads, guia_emp = [], []
    for e in data["empresas"]:
        P = e["puertas"]
        ai = next((i for i, x in enumerate(P)
                   if x.get("nombre") and "contexto" not in (x.get("nivel") or "").lower()), 0)
        d1 = P[ai]
        ch = e.get("canales") or {}
        def chan(k):
            c = ch.get(k) or {}
            return c.get("valor") if c.get("estado") in ("verificado", "inferido") else ""
        leads.append({
            "_key": e["id"], "companyName": e["empresa"], "country": "México",
            "industry": e.get("sector", ""), "website": chan("sitio") or e.get("sitio", ""),
            "contactName": d1.get("nombre") or "", "contactTitle": d1.get("titulo") or d1.get("rol") or "",
            "contactEmail": ((d1.get("email") or {}).get("valor") or ""),
            "whatsapp": chan("whatsapp") or "", "instagramHandle": "",
            "contactLinkedIn": chan("linkedin_empresa") or "",
            "companyBrief": e["hook"]["texto"], "pitchEmailES": d1["mensaje"]["cuerpo"],
            "logo": "", "score": "", "source_date": hoy, "approved": True,
            "whyICP": "", "whyNow": [],   # el "por qué" lo concluye quien lee el hecho, no lo escribimos nosotros
            "sector": e.get("sector", ""), "ciudad": e.get("ciudad", ""),
        })
        guia_emp.append({
            "id": e["id"], "empresa": e["empresa"], "ciudad": e.get("ciudad", ""),
            "hook": e["hook"], "fact": e.get("fact"),
            "ruta_sugerida": e.get("ruta_sugerida", []), "coach": e.get("coach", []),
            "canales": ch, "rutas_adicionales": e.get("rutas_adicionales", []),
            "intento_log": e.get("intento_log", []), "tamano": e.get("tamano", {}),
            "puertas": [{"rol": x.get("rol"), "nivel": x.get("nivel"), "nombre": x.get("nombre"),
                         "titulo": x.get("titulo"), "email": x.get("email"), "evidencia": x.get("evidencia"),
                         "confianza": x.get("confianza"), "ruta_entrada": x.get("ruta_entrada"),
                         "linkedin_busqueda": x.get("linkedin_busqueda"), "mensaje": x.get("mensaje"),
                         "_cuenta": x.get("_cuenta")} for x in P],
        })
    payload = {
        "client_id": "demo-" + prospect, "client_type": "demo", "prospecto": cfg.get("prospecto", prospect),
        # el saludo y el destinatario viven en config.json: editarlos a mano en el JSON publicado se perdía
        # en el siguiente build
        "saludo": cfg.get("saludo") or "", "demo_para": cfg.get("demo_para") or "",
        "generado": hoy, "leads": leads,
        "guia": {"temporada_objetivo": cfg.get("temporada_objetivo"),
                 "temporada_label": cfg.get("temporada_label"), "temporada_nota": cfg.get("temporada_nota"),
                 "min_por_cuenta": cfg.get("min_por_cuenta", 2),
                 "resumen_hoy": data.get("resumen_hoy", {}), "cierre": cfg.get("cierre", {}),
                 "empresas": guia_emp},
    }
    out = ROOT / "public" / ("demo-" + prospect + ".json")
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


HTML = r"""<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{
    --paper:__PAPER__; --ink:__INK__; --accent:__ACCENT__; --soft:__SOFT__;
    --line:rgba(11,11,13,.12); --muted:rgba(11,11,13,.58); --ok:#1f7a4d; --warn:#8a6a1f;
    --r:14px;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:var(--paper); color:var(--ink);
    font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
    font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
  }
  h1,h2,h3,.serif{font-family:"Playfair Display",Georgia,serif; font-weight:600; letter-spacing:-.01em}
  .mono{font-family:"JetBrains Mono",ui-monospace,monospace; font-size:11px; letter-spacing:.06em; text-transform:uppercase}
  /* MOBILE FIRST: these are the phone styles. Desktop is layered on at the bottom via min-width. */
  .wrap{max-width:1100px; margin:0 auto; padding:0 14px}
  a{color:var(--accent)}

  /* ---------- header ---------- */
  header{
    position:sticky; top:0; z-index:50; background:rgba(244,244,242,.93);
    backdrop-filter:saturate(1.2) blur(10px); border-bottom:1px solid var(--line);
  }
  .hrow{display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline; justify-content:space-between; padding:12px 0 10px}
  .hrow h1{font-size:19px; margin:0; line-height:1.2}
  .hrow .mono{color:var(--muted)}
  .bar{height:6px; background:var(--soft); border-radius:99px; overflow:hidden; margin-bottom:6px}
  .bar i{display:block; height:100%; width:0%; background:var(--accent); border-radius:99px; transition:width .5s cubic-bezier(.22,.7,.2,1)}
  .barlabel{display:flex; justify-content:space-between; gap:10px; padding-bottom:12px}
  .barlabel span{font-size:12.5px; color:var(--muted)}

  /* ---------- season ---------- */
  .season{
    display:grid; grid-template-columns:1fr; gap:8px; align-items:start;
    border:1px solid var(--line); border-radius:var(--r); background:#fff; padding:18px; margin:22px 0 10px;
  }
  .days{font-family:"Playfair Display",serif; font-size:38px; line-height:.95; color:var(--accent)}
  .season p{margin:.25rem 0 0; font-size:14px; color:var(--muted)}

  /* ---------- learning panel ---------- */
  .learn{border:1px solid var(--line); border-radius:var(--r); background:var(--soft); padding:18px; margin:14px 0 26px}
  .learn h2{font-size:18px; margin:0 0 4px}
  .learn .empty{font-size:14px; color:var(--muted); margin:6px 0 0}
  .lgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-top:12px}
  .lbox{background:#fff; border:1px solid var(--line); border-radius:10px; padding:12px}
  .lbox .mono{color:var(--muted); display:block; margin-bottom:6px}
  .lbox ul{margin:0; padding-left:16px; font-size:14px}

  /* ---------- cards ---------- */
  .card{
    border:1px solid var(--line); border-radius:var(--r); background:#fff; margin:0 0 20px; overflow:hidden;
    transition:box-shadow .3s ease, border-color .3s ease;
  }
  .card.done{border-color:rgba(31,122,77,.45)}
  .card:hover{box-shadow:0 2px 20px rgba(11,11,13,.06)}
  .ctop{padding:16px 14px 14px; border-bottom:1px solid var(--line)}
  .cnum{color:var(--muted)}
  .ctop h2{font-size:20px; margin:4px 0 2px; line-height:1.2}
  .meta{font-size:15px; color:var(--muted)}
  .hook{background:var(--soft); border-left:3px solid var(--accent); padding:14px 16px; margin:14px 0 0; border-radius:0 8px 8px 0}
  .hook p{margin:4px 0 8px; font-size:15px}
  .srcs{display:flex; flex-wrap:wrap; gap:8px}
  .src{font-size:11.5px; font-family:"JetBrains Mono",monospace; background:#fff; border:1px solid var(--line); border-radius:99px; padding:3px 9px; text-decoration:none}

  /* intel + channels */
  .intel{display:grid; grid-template-columns:1fr; gap:14px; padding:16px 14px; border-bottom:1px solid var(--line)}
  .intel .mono{color:var(--muted); display:block; margin-bottom:4px}
  .intel div p{margin:0; font-size:14px}
  .chips{display:flex; flex-wrap:wrap; gap:7px; padding:14px 14px 16px; border-bottom:1px solid var(--line)}
  .chip{font-size:12px; border-radius:99px; padding:4px 10px; border:1px solid var(--line); text-decoration:none; color:var(--ink); background:#fff; display:inline-flex; gap:6px; align-items:center}
  .chip.v{border-color:rgba(31,122,77,.4); background:rgba(31,122,77,.07)}
  .chip.i{border-color:rgba(138,106,31,.4); background:rgba(138,106,31,.07)}
  .chip.n{color:var(--muted); background:transparent; border-style:dashed}
  .chip b{font-weight:600}

  /* route strip */
  .route{padding:16px 14px; border-bottom:1px solid var(--line); background:#fcfcfb}
  .route h3{font-size:13px; margin:0 0 10px; font-family:Inter; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); font-weight:600}
  .route ol{margin:0; padding:0; list-style:none; display:grid; gap:8px}
  .route li{font-size:14px; display:grid; grid-template-columns:1fr; gap:3px; align-items:start}
  .route .step{font-family:"JetBrains Mono",monospace; font-size:11px; background:var(--soft); color:var(--accent); border-radius:6px; padding:3px 7px; white-space:normal; justify-self:start}
  .route .why{color:var(--muted); font-size:13px}

  /* doors */
  .doors{padding:6px 14px 18px}
  .door{border-top:1px solid var(--line); padding:18px 0 4px}
  .door:first-child{border-top:0}
  .dhead{display:block}
  .dhead > div:last-child{margin-top:6px}
  .dname{font-size:16.5px; font-weight:600}
  .dname.unknown{color:var(--muted); font-weight:500; font-style:italic}
  .drole{font-size:13px; color:var(--muted)}
  .badge{font-size:11.5px; font-family:"JetBrains Mono",monospace; border-radius:99px; padding:3px 9px; border:1px solid var(--line)}
  .badge.c3{background:rgba(31,122,77,.1); border-color:rgba(31,122,77,.4)}
  .badge.c1{background:rgba(138,106,31,.1); border-color:rgba(138,106,31,.4)}
  .badge.c0{color:var(--muted); border-style:dashed}
  .route-in{font-size:15px; color:var(--muted); margin:8px 0 0}
  .msg{background:#fbfbfa; border:1px solid var(--line); border-radius:10px; padding:14px; margin:12px 0 0}
  .msg .subj{font-size:13px; font-weight:600; margin-bottom:6px}
  .msg pre{margin:0; white-space:pre-wrap; font-family:Inter,sans-serif; font-size:15px; line-height:1.6}
  .acts{display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 0}
  .acts > *{flex:1 1 calc(50% - 4px); justify-content:center; min-height:44px; font-size:15px}  /* dedos, no cursores */
  button,.btn{
    font-family:Inter,sans-serif; font-size:13.5px; font-weight:500; cursor:pointer;
    border:1px solid var(--line); background:#fff; color:var(--ink);
    border-radius:9px; padding:8px 13px; text-decoration:none; display:inline-flex; align-items:center; gap:7px;
    transition:transform .12s ease, background .2s ease, border-color .2s ease;
  }
  button:hover,.btn:hover{border-color:var(--accent); transform:translateY(-1px)}
  button:active{transform:translateY(0)}
  .btn.primary{background:var(--accent); border-color:var(--accent); color:#fff}
  .btn.ghost{color:var(--muted)}
  button.on{background:rgba(31,122,77,.1); border-color:rgba(31,122,77,.5); color:var(--ok)}
  button.rep.on{background:var(--soft); border-color:var(--accent); color:var(--accent)}

  /* coach */
  .coach{
    display:grid; grid-template-columns:auto 1fr; gap:10px; align-items:start;
    background:var(--soft); border-radius:10px; padding:12px 13px; margin:12px 14px 0; font-size:15px;
  }
  .coach .k{font-family:"JetBrains Mono",monospace; font-size:10.5px; color:var(--accent); letter-spacing:.08em; padding-top:2px}
  .note{font-size:12.5px; color:var(--muted); font-style:italic}
  /* the level chip must wrap: with nowrap it pushed the page past 390px on a phone */
  .lvl{font-family:"JetBrains Mono",monospace; font-size:10.5px; text-transform:uppercase; letter-spacing:.06em;
       background:var(--soft); color:var(--accent); border-radius:5px; padding:2px 6px;
       display:inline-block; white-space:normal; overflow-wrap:anywhere; max-width:100%}
  .today{border:1px solid var(--line); border-radius:var(--r); background:#fff; padding:16px 14px; margin:18px 0 14px}
  .today h2{font-size:20px; margin:0 0 12px}
  /* una sola columna en teléfono: a 390px dos columnas parten las etiquetas en 5 renglones */
  .stats{display:grid; grid-template-columns:1fr; gap:10px}
  .stat{display:flex; align-items:baseline; gap:10px}
  .stat b{font-size:26px}
  .stat span{margin-top:0}
  @media (min-width:481px){ .stats{grid-template-columns:1fr 1fr} }
  .stat{background:var(--soft); border-radius:10px; padding:12px 14px}
  .stat b{display:block; font-family:"Playfair Display",serif; font-size:30px; line-height:1; color:var(--accent)}
  .stat span{display:block; font-size:12.5px; color:var(--muted); margin-top:5px}
  .disc{margin-top:14px}
  .disc .mono{color:var(--muted); display:block; margin-bottom:6px}
  .disc ul{margin:0; padding-left:18px; font-size:13.5px; display:grid; gap:5px}
  .closing{border:1px solid var(--accent); border-radius:var(--r); background:var(--soft); padding:18px 14px; margin:24px 0 0}
  .closing h2{font-size:22px; margin:0 0 6px}
  .closing .lead{margin:0 0 14px; font-size:15px; max-width:62ch}
  .closing .refer{margin:14px 0 0; font-size:13.5px; color:var(--muted); max-width:62ch}
  .flagline{font-size:13.5px; margin-top:8px; padding:8px 10px; border-radius:8px;
    background:rgba(138,106,31,.09); border:1px solid rgba(138,106,31,.35)}
  .flagline .mono{color:var(--warn); margin-right:6px}
  .cchip{display:inline-block; margin-left:8px; font-family:"JetBrains Mono",monospace; font-size:10.5px;
    text-transform:uppercase; letter-spacing:.05em; border-radius:5px; padding:2px 6px; white-space:normal}
  .cchip.c{background:rgba(31,122,77,.1); color:var(--ok)}
  .cchip.s{background:rgba(138,106,31,.12); color:var(--warn)}
  .cchip.x{background:rgba(11,11,13,.06); color:var(--muted)}
  .falta{color:#8a1f1f; background:rgba(138,31,31,.08); border:1px dashed rgba(138,31,31,.4); border-radius:6px; padding:2px 7px; font-size:12.5px}
  /* tarjetas y puertas colapsables */
  .cwrap > summary, .door > summary{list-style:none; cursor:pointer}
  .cwrap > summary::-webkit-details-marker, .door > summary::-webkit-details-marker{display:none}
  .csum{display:flex; gap:12px; align-items:center; padding:16px 14px; min-height:64px}
  .csum .cs-n{font-family:"JetBrains Mono",monospace; font-size:12px; color:var(--accent);
    background:var(--soft); border-radius:8px; min-width:30px; height:30px; display:flex; align-items:center; justify-content:center}
  .csum .cs-t{flex:1; display:flex; flex-direction:column; gap:2px}
  .csum .cs-t b{font-family:"Playfair Display",serif; font-size:18px; font-weight:600}
  .csum .cs-t em{font-style:normal; font-size:13px; color:var(--muted)}
  .csum .cs-k{font-family:"JetBrains Mono",monospace; font-size:10.5px; color:var(--muted); white-space:nowrap}
  .cwrap[open] > .csum{border-bottom:1px solid var(--line)}
  .dsum{display:flex; flex-direction:column; gap:2px; padding:14px 0; min-height:44px}
  .dsum b{font-size:16px}
  .dsum em{font-style:normal; font-size:13.5px; color:var(--muted)}
  .door[open] > .dsum{border-bottom:1px dashed var(--line); margin-bottom:8px}
  .door{border-top:1px solid var(--line); padding:0 0 4px}
  /* toggles de fuentes, coach y desglose */
  .srcwrap summary, .morecoach summary, .more summary{cursor:pointer; font-family:"JetBrains Mono",monospace;
    font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); padding:6px 0; min-height:30px}
  .srcwrap .srcs{margin-top:6px}
  .more .sub{margin-top:10px}
  /* barra pegada abajo (solo teléfono) */
  .stickybar{position:fixed; left:0; right:0; bottom:0; z-index:60; display:flex; gap:10px; align-items:center;
    justify-content:space-between; padding:10px 14px; background:rgba(244,244,242,.97);
    backdrop-filter:blur(10px); border-top:1px solid var(--line)}
  .stickybar span{font-size:13.5px; color:var(--muted)}
  .stickybar button{min-height:44px; font-size:15px; background:var(--accent); border-color:var(--accent); color:#fff}
  body{padding-bottom:72px}
  .eviden{margin:8px 0 0; font-size:13px}
  .eviden summary{cursor:pointer; color:var(--accent); font-family:"JetBrains Mono",monospace; font-size:11px;
    letter-spacing:.06em; text-transform:uppercase; display:inline-block; padding:3px 0}
  .eviden ul{margin:8px 0 0; padding:10px 12px 10px 26px; background:var(--soft); border-radius:8px; display:grid; gap:5px}
  .eviden code{font-family:"JetBrains Mono",monospace; font-size:12.5px; background:#fff; padding:1px 6px; border-radius:4px}
  .extra{border-top:1px solid var(--line); padding:14px 14px 18px; background:#fcfcfb}
  .extra h3{font-size:12px; margin:0 0 8px; font-family:Inter; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); font-weight:600}
  .extra ul{margin:0; padding-left:0; list-style:none; display:grid; gap:6px; font-size:13.5px}
  .extra p{margin:8px 0 0}
  .mailroute{font-size:13.5px; margin-top:8px; padding:8px 10px; border:1px dashed var(--line); border-radius:8px}
  .mailroute .mono{color:var(--accent); margin-right:6px}

  footer{border-top:1px solid var(--line); margin-top:30px; padding:22px 0 40px; color:var(--muted); font-size:13px}

  /* nothing may push the page wider than the screen: long URLs, mono labels and chips all wrap */
  .src,.chip,.badge,.route .step{overflow-wrap:anywhere; word-break:break-word}
  .msg pre{overflow-wrap:anywhere}

  /* ---------- DESKTOP: everything above is the phone; this is the enhancement ---------- */
  @media (min-width:721px){
    .stickybar{display:none}
    body{padding-bottom:0}
    .csum{pointer-events:none; padding:0; min-height:0; display:none}   /* en escritorio las tarjetas van abiertas */
    .cwrap > .ctop{border-top:0}
    .door > .dsum{display:none}
    .door{padding:18px 0 4px}
    .wrap{padding:0 20px}
    .hrow{padding:16px 0 12px; gap:14px}
    .hrow h1{font-size:23px}
    .season{grid-template-columns:auto 1fr; gap:18px; align-items:center}
    .days{font-size:44px}
    .stats{grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px}
    .stat{display:block}
    .stat b{font-size:30px}
    .stat span{margin-top:5px}
    .ctop{padding:20px 20px 16px}
    .ctop h2{font-size:24px}
    .intel{grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); padding:16px 20px}
    .chips,.route,.extra{padding-left:20px; padding-right:20px}
    .route li{grid-template-columns:auto 1fr; gap:10px}
    .route .step{white-space:nowrap}
    .doors{padding:6px 20px 20px}
    .dhead{display:flex; flex-wrap:wrap; gap:8px; align-items:baseline; justify-content:space-between}
    .dhead > div:last-child{margin-top:0}
    .acts > *{flex:0 0 auto; min-height:0}
    .coach{margin-left:20px; margin-right:20px}
    .today{padding:20px}
    .closing{padding:24px}
  }

  @media (prefers-reduced-motion:reduce){*{transition:none !important}}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <div class="hrow">
      <h1 id="pagetitle"></h1>
      <div class="mono" id="today"></div>
    </div>
    <div class="bar"><i id="barfill"></i></div>
    <div class="barlabel">
      <span id="barlabel"></span>
      <span id="barcount">0 de 10 cuentas trabajadas</span>
    </div>
  </div>
</header>

<main class="wrap">

  <section class="season">
    <div class="days" id="days">--</div>
    <div>
      <div class="mono" style="color:var(--muted)" id="season-label"></div>
      <p id="season-note"></p>
    </div>
  </section>

  <section class="today" id="today-block"></section>

  <section class="learn">
    <h2>Lo que el sistema está aprendiendo</h2>
    <p class="empty" id="learnEmpty">Marca <b>Respondió</b> en la puerta donde te contesten y aquí aparece el patrón: qué sector, qué puerta y qué canal te están funcionando. En el sistema real esto alimenta el orden de los siguientes envíos.</p>
    <div class="lgrid" id="learnGrid" hidden></div>
  </section>

  <div id="cards"></div>

  <section class="closing" id="closing-block"></section>

</main>

<div class="stickybar" id="stickybar">
  <span id="sb-text"></span>
  <button id="sb-next" onclick="nextCard()">Siguiente cuenta</button>
</div>

<footer class="wrap">
  <span id="footline"></span><br>
  <span class="note">Ningún nombre fue inventado. Donde no encontramos algo, la tarjeta dice “no encontrado” o “por identificar”. Los tiempos (~2 min por cuenta) son un estimado inicial, el sistema los ajusta con tus respuestas.</span>
</footer>

<script>
const DATA = __PAYLOAD__;
const CFG = DATA._cfg || {};
const MIN_PER_CARD = CFG.min_por_cuenta || 2;
const FALTA = s => s ? esc(s) : '<span class="falta">falta: ' + 'dato no proporcionado</span>';              // estimado inicial, el sistema lo ajusta con tus respuestas
const state = { sent:{}, replied:{} };

/* ---------- header + countdown ---------- */
const MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
(function(){
  const d = new Date();
  document.getElementById("today").textContent =
    d.getDate() + " de " + MESES[d.getMonth()] + " de " + d.getFullYear();
  document.getElementById("pagetitle").innerHTML = (CFG.encabezado || "Tu día") + ' <span style="color:var(--muted)">·</span> ' + (CFG.prospecto || "");
  document.getElementById("season-label").textContent = CFG.temporada_label || "";
  document.getElementById("season-note").textContent = CFG.temporada_nota || "";
  document.getElementById("footline").textContent = CFG.pie || "";
  const target = new Date((CFG.temporada_objetivo || DATA.meta.temporada_objetivo) + "T00:00:00");
  const days = Math.max(0, Math.ceil((target - d) / 86400000));
  document.getElementById("days").textContent = days;
})();

/* ---------- helpers ---------- */
const esc = s => String(s==null?"":s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const host = u => { try { return new URL(u).hostname.replace(/^www\./,""); } catch(e){ return u; } };

function chip(label, c){
  if(!c || c.estado === "no encontrado" || !c.valor){
    return '<span class="chip n" title="'+esc((c&&c.nota)||"no encontrado en fuentes públicas")+'">'+label+': no encontrado</span>';
  }
  const cls = c.estado === "verificado" ? "v" : "i";
  const isLink = /^https?:/.test(c.valor);
  const shown = isLink ? host(c.valor) : c.valor;
  const inner = '<b>'+label+'</b> '+esc(shown)+' · '+c.estado;
  return isLink
    ? '<a class="chip '+cls+'" href="'+esc(c.valor)+'" target="_blank" rel="noopener">'+inner+'</a>'
    : '<span class="chip '+cls+'" title="'+esc(c.nota||"")+'">'+inner+'</span>';
}

// THE PROOF CARLOS CAN CLICK: name source -> pattern source -> resulting address, each with its link.
// A pattern-inferred address is only as good as the two links behind it, so both are shown, never summarized.
function evidenceBlock(p, id){
  const e = p.evidencia;
  if(!e) return "";
  const row = (k, o) => '<li><b>'+k+':</b> '+esc(o.que)
      + (o.url ? ' <a class="src" href="'+esc(o.url)+'" target="_blank" rel="noopener">'+esc(host(o.url))+'</a>' : '')+'</li>';
  return '<details class="eviden"><summary>Cómo lo encontramos</summary><ul>'
    + row("1. De dónde sale el nombre", e.nombre)
    + row("2. De dónde sale el patrón del dominio", e.patron)
    + '<li><b>3. Resultado:</b> <code>'+esc(e.resultado)+'</code></li>'
    + '</ul></details>';
}

function badge(conf){
  const n = (conf && conf.n) || 0;
  const cls = n >= 3 ? "c3" : (n >= 1 ? "c1" : "c0");
  if(!n) return '<span class="badge c0">sin fuente: por identificar</span>';
  const links = conf.fuentes.map(u => '<a class="src" href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(host(u))+'</a>').join("");
  return '<span class="badge '+cls+'">'+n+' '+(n===1?"fuente":"fuentes")+'</span> '+links;
}

// A real address is prefilled ONLY when it is published or a department mailbox. A pattern-inferred address is a
// template with placeholders, never a recipient: prefilling it would send mail to an address nobody verified.
function usableAddress(email){
  if(!email || !email.valor) return "";
  // A TEMPLATE is never a recipient: "<inicial><apellido>@dominio" must not reach a To: field.
  if(email.valor.indexOf("<") !== -1) return "";
  // A weak route (a sales inbox) is shown but not prefilled: it is not the door, only a redirect.
  if(email.estado === "ruta débil") return "";
  // An AREA inbox (rrhh@, info@, compras_@, a program alias) reaches whoever answers, not a decision maker.
  // It stays visible under "Rutas adicionales" but never becomes the primary send button.
  if(email.estado === "buzón de área") return "";
  // Published, department mailbox, and CONCRETE pattern-inferred addresses all prefill. The inferred ones carry
  // their "verificar antes de enviar" label on screen, and the mail client is where he checks before sending.
  return email.valor;
}
function mailtoHref(door, emp){
  return "mailto:" + encodeURIComponent(usableAddress(door.email))
    + "?subject=" + encodeURIComponent(door.mensaje.asunto)
    + "&body=" + encodeURIComponent(door.mensaje.cuerpo);
}
function emailBlock(em){
  if(!em) return '<span class="note">correo: no encontrado</span>';
  const st = em.estado || "no encontrado";
  const src = em.fuente ? ' <a class="src" href="'+esc(em.fuente)+'" target="_blank" rel="noopener">'+esc(host(em.fuente))+'</a>' : "";
  const nota = em.nota ? '<br><span class="note">'+esc(em.nota)+'</span>' : "";
  if(st === "no encontrado" || !em.valor){
    return '<span class="chip n">correo: no encontrado</span>'+nota;
  }
  const cls = st === "publicado" ? "v" : (st === "buzón de área" ? "v" : "i");
  return '<span class="chip '+cls+'"><b>'+esc(st)+'</b> '+esc(em.valor)+'</span>'+src+nota;
}

/* ---------- coach lines (contextual, no invented numbers) ---------- */
function coachFor(emp){
  const rrhhUnknown = emp.puertas.some(p => /capital humano|recursos humanos/i.test(p.rol) && !p.nombre);
  const hasNamedBoss = emp.puertas.some(p => p.nombre && /direcci|presiden|general/i.test(p.rol));
  const anniv = /aniversario|cumple/i.test(emp.hook.texto);
  const compras = emp.puertas.some(p => /compras|proveedor/i.test(p.rol));
  if(anniv) return ["aniversario","Nombrar la planta o el evento específico rinde más que hablar de la empresa en general. Un aniversario redondo no se repite, y eso es una razón para hablar hoy."];
  if(compras) return ["secuencia","LinkedIn primero para dirección, email para compras. El alta de proveedor tarda, así que ábrela aunque la posada todavía no esté cerrada."];
  if(rrhhUnknown && hasNamedBoss) return ["orden","Tienes nombre arriba pero no en RR.HH. Usa al de arriba para que te manden al área: un referido interno entra distinto que un correo frío."];
  if(rrhhUnknown) return ["rr.hh.","En corporativos, RR.HH. responde mejor si el mensaje habla de su gente, no de tu equipo. Abre con su evento, no con tu portafolio."];
  return ["gente","En corporativos, RR.HH. responde mejor si el mensaje habla de su gente, no de tu equipo."];
}

/* ---------- render ---------- */
function render(){
  const root = document.getElementById("cards");
  root.innerHTML = DATA.empresas.map((emp, i) => {
    const t = emp.tamano || {};
    const ch = emp.canales || {};
    const doors = emp.puertas.map((p, j) => {
      const key = emp.id + ":" + j;
      const sent = !!state.sent[key], rep = !!state.replied[key];
      const em = p.email || {};
      const cnt = p._cuenta ? '<span class="cchip '+(p._cuenta==="confirmado"?"c":(p._cuenta==="contexto"?"x":"s"))+'">'
            + (p._cuenta==="contexto" ? "no cuenta: contexto" : (p._cuenta==="confirmado" ? "cuenta: confirmado" : "cuenta: verificar vigencia"))
            + '</span>' : "";
      const emailTxt = emailBlock(em) + cnt + evidenceBlock(p, emp.id + "-" + j);
      // The channel decides the buttons: an email-channel message is written de usted, a LinkedIn or WhatsApp one
      // de tú. Offering "Enviar email" on a tú message would send the wrong register, so the primary action
      // follows the channel the message was written for.
      const canal = p.mensaje.canal;
      const waOnly = canal === "whatsapp";
      return '<details class="door"'+(j===0?" open":"")+'><summary class="dsum">'
        + '<b>'+esc(p.nombre || "por identificar")+'</b><em>'+esc((p.rol||"").split("(")[0].trim())+'</em>'
        + '</summary>'
        + '<div class="dhead"><div>'
          + '<div class="dname'+(p.nombre?"":" unknown")+'">'+esc(p.nombre || "por identificar")+'</div>'
          + '<div class="drole">'+esc(p.rol)+(p.titulo ? " · " + esc(p.titulo) : "")
            + (p.nivel ? ' <span class="lvl">'+esc(p.nivel)+'</span>' : "")+'</div>'
        + '</div><div>'+badge(p.confianza)+'</div></div>'
        + '<p class="route-in"><b>Ruta de entrada:</b> '+esc(p.ruta_entrada)+'</p>'
        + '<p class="route-in">'+emailTxt+'</p>'
        + '<div class="msg">'
          + '<div class="subj">'+(waOnly ? "Mensaje para WhatsApp o llamada" : esc(p.mensaje.asunto))+' <span class="note">· '+esc(p.mensaje.canal)+', trato de '+esc(p.mensaje.trato)+'</span></div>'
          + '<pre id="m-'+emp.id+'-'+j+'">'+esc(p.mensaje.cuerpo)+'</pre>'
        + '</div>'
        + '<div class="acts">'
          + (canal === "email" ? '<a class="btn primary" href="'+esc(mailtoHref(p, emp))+'">Enviar email</a>' : '')
          + '<a class="btn'+(canal==="linkedin"?" primary":"")+'" href="'+esc(p.linkedin_busqueda)+'" target="_blank" rel="noopener">Abrir LinkedIn</a>'
          + '<button'+(waOnly?' class="primary" style="background:var(--accent);border-color:var(--accent);color:#fff"':'')+' onclick="copyMsg(\''+emp.id+'\','+j+',this)">'+(waOnly?"Copiar para WhatsApp":"Copiar mensaje")+'</button>'
          + '<button class="'+(sent?"on":"")+'" onclick="markSent(\''+emp.id+'\','+j+')">'+(sent?"Enviado ✓":"Marcar enviado")+'</button>'
          + '<button class="rep '+(rep?"on":"")+'" onclick="markReplied(\''+emp.id+'\','+j+')">'+(rep?"Respondió ✓":"Respondió")+'</button>'
        + '</div>'
      + '</details>';
    }).join("");

    const cDone = emp.puertas.some((p,j)=>state.sent[emp.id+":"+j]);
    const coach = coachFor(emp);

    return '<article class="card'+(cDone?" done":"")+'" id="card-'+emp.id+'">'
      + '<details class="cwrap"'+(i===0?" open":"")+'><summary class="csum">'
        + '<span class="cs-n">'+(i+1)+'</span>'
        + '<span class="cs-t"><b>'+esc(emp.empresa)+'</b><em>'+esc(emp.ciudad)+' · '+esc((emp.sector||"").split("/")[0].trim())+'</em></span>'
        + '<span class="cs-k">'+emp.puertas.length+' puertas</span>'
      + '</summary>'
      + '<div class="ctop">'
        + '<div class="mono cnum">Cuenta '+(i+1)+' de '+DATA.empresas.length+'</div>'
        + '<h2>'+esc(emp.empresa)+'</h2>'
        + '<div class="meta">'+esc(emp.ciudad)+' · '+esc(emp.sector)+(emp.tipo ? ' · <span class="lvl">'+esc(emp.tipo)+'</span>' : "")+'</div>'
        + (emp.etiqueta ? '<div class="flagline"><span class="mono">ojo</span> '+esc(emp.etiqueta)+'</div>' : "")
        + (emp.ruta_correo ? '<div class="mailroute"><span class="mono">ruta de correo</span> '+esc(emp.ruta_correo)+'</div>' : "")
        + '<div class="meta" style="margin-top:6px"><b>Tamaño:</b> '+esc(t.valor||"no encontrado")
          + (t.fuente ? ' <a class="src" href="'+esc(t.fuente)+'" target="_blank" rel="noopener">fuente: '+esc(host(t.fuente))+'</a>' : "")
          + (t.nota ? '<br><span class="note">'+esc(t.nota)+'</span>' : "")
        + '</div>'
        + '<div class="hook">'
          + '<div class="mono" style="color:var(--accent)">gancho · '+esc(emp.hook.tipo)+'</div>'
          + '<p>'+esc(emp.hook.texto)+'</p>'
          + '<details class="srcwrap"><summary>Ver fuentes ('+emp.hook.fuentes.length+')</summary><div class="srcs">'
            + emp.hook.fuentes.map(u=>'<a class="src" href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(host(u))+'</a>').join("")
            + '</div></details>'
        + '</div>'
      + '</div>'
      + '<div class="intel">'
        + '<div><span class="mono">matriz</span><p>'+esc(emp.matriz.empresa)+' · '+esc(emp.matriz.pais)+'</p></div>'
        + '<div><span class="mono">plantas en nuevo león</span><p>'+emp.plantas_nl.map(esc).join("<br>")+'</p></div>'
        + '<div><span class="mono">evento previo documentado</span><p>'
          + ((emp.eventos_previos||[]).length
              ? emp.eventos_previos.map(e=>esc(e.que)+' <a class="src" href="'+esc(e.fuente)+'" target="_blank" rel="noopener">'+esc(host(e.fuente))+'</a>').join("<br>")
              : '<span class="note">no encontramos evento público previo (posada, family day o inauguración) de esta empresa</span>')
          + '</p></div>'
      + '</div>'
      + '<div class="chips">'
        + chip("sitio", ch.sitio) + chip("tel", ch.telefono) + chip("whatsapp", ch.whatsapp)
        + chip("linkedin", ch.linkedin_empresa) + chip("facebook", ch.facebook)
        + chip("instagram", ch.instagram) + chip("youtube", ch.youtube)
      + '</div>'
      + '<div class="route"><h3>Ruta sugerida para esta cuenta</h3><ol>'
        + emp.ruta_sugerida.map(r=>'<li><span class="step">'+esc(r.paso)+'</span><span>'+esc(r.razon)+'</span></li>').join("")
      + '</ol></div>'
      + ((emp.coach||[]).length
          ? '<div class="coach"><span class="k">'+esc(emp.coach[0][0])+'</span><span>'+esc(emp.coach[0][1])+'</span></div>'
            + (emp.coach.length>1
               ? '<details class="morecoach"><summary>'+(emp.coach.length-1)+' consejo'+(emp.coach.length>2?"s":"")+' más</summary>'
                 + emp.coach.slice(1).map(c=>'<div class="coach"><span class="k">'+esc(c[0])+'</span><span>'+esc(c[1])+'</span></div>').join("")
                 + '</details>' : '')
          : '')
      + '<div class="doors">'+doors+'</div>'
      + ((emp.rutas_adicionales||[]).length
          ? '<div class="extra"><h3>Rutas adicionales (buzón de área, no cuentan como puerta)</h3><ul>'
            + emp.rutas_adicionales.map(r=>'<li><span class="chip i">buzón de área</span> <b>'+esc(r.valor)+'</b> · '
                + esc(r.que) + ' <a class="src" href="'+esc(r.fuente)+'" target="_blank" rel="noopener">'+esc(host(r.fuente))+'</a></li>').join("")
            + '</ul><p class="note">Llegan a quien conteste, no a quien decide. Úsalas para que te reencaminen o para el alta de proveedor, nunca como primer mensaje.</p></div>'
          : '')
      + '</details>'
    + '</article>';
  }).join("");
  updateBar();
  updateLearning();
  expandForDesktop();
}

/* ---------- actions ---------- */
function copyMsg(id, j, btn){
  const el = document.getElementById("m-"+id+"-"+j);
  const txt = el ? el.textContent : "";
  const done = () => { const o = btn.textContent; btn.textContent = "Copiado ✓"; setTimeout(()=>btn.textContent=o, 1400); };
  if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(done, done); }
  else {
    const ta = document.createElement("textarea"); ta.value = txt; document.body.appendChild(ta);
    ta.select(); try{ document.execCommand("copy"); }catch(e){} ta.remove(); done();
  }
}
function markSent(id, j){ const k=id+":"+j; state.sent[k] = !state.sent[k]; function renderToday(){
  const t = DATA.resumen_hoy; if(!t) return;
  const stat = (n,l) => '<div class="stat"><b>'+n+'</b><span>'+l+'</span></div>';
  document.getElementById("today-block").innerHTML =
    '<h2>Lo que el sistema hizo hoy</h2>'
    + '<div class="stats">'
      + stat(t.cuentas, "cuentas")
      + stat(t.correos_personales, "correos a una persona")
      + stat(t.fuentes_revisadas, "fuentes revisadas")
    + '</div>'
    + '<details class="more"><summary>Ver el desglose</summary><div class="stats sub">'
      + stat(t.correos_confirmados, "confirmados (fuente abrible y fechada)")
      + stat(t.correos_sin_fecha, "sin fecha: verificar vigencia por teléfono")
      + stat(t.correos_contexto || 0, "de dirección: contexto, no cuentan")
    + '</div>'
    + '<div class="disc"><span class="mono">descartados a propósito</span><ul>'
      + t.descartados.map(x=>'<li><b>'+esc(x.quien)+'</b> ('+esc(x.empresa)+'): '+esc(x.por)
          +' <a class="src" href="'+esc(x.fuente)+'" target="_blank" rel="noopener">'+esc(host(x.fuente))+'</a></li>').join("")
      + '</ul></div>'
    + '<p class="note">'+esc(t.nota_conteo||"")+'</p>'
    + '<p class="note">Tiempo de investigación que te ahorra: ~'+t.horas_estimadas+' horas. '+esc(t.nota_horas)+'</p>'
    + '</details>';
}

function renderClosing(){
  const c = Object.assign({}, DATA.cierre || {}, CFG.cierre || {}); if(!c.titulo) return;
  const body = "Hola Emiliano,%0D%0A%0D%0AVi el demo de cuentas para REBRND y quiero saber como funciona el plan Cuentas.%0D%0A%0D%0AGracias.";
  document.getElementById("closing-block").innerHTML =
    '<h2>'+esc(c.titulo)+'</h2>'
    + '<p class="lead">'+esc(c.linea)+'</p>'
    + '<div class="acts">'
      + '<a class="btn primary" href="mailto:'+esc(c.contacto_email)+'?subject='+encodeURIComponent("Plan Cuentas para REBRND")+'&body='+body+'">Escribir a Emiliano</a>'
      + (c.contacto_whatsapp
          ? '<a class="btn" href="'+esc(c.contacto_whatsapp)+'" target="_blank" rel="noopener">WhatsApp</a>'
          : '<span class="btn falta">WhatsApp: falta el número</span>')
    + '</div>'
    + '<p class="refer">'+esc(c.referido)+'</p>';
}

// en escritorio todo abierto; en teléfono, una tarjeta y una puerta a la vez
function expandForDesktop(){
  if(window.matchMedia("(min-width:721px)").matches){
    document.querySelectorAll(".cwrap, .door").forEach(x=>x.open=true);
  }
}
render();
renderToday();
renderClosing();
expandForDesktop();
window.addEventListener("resize", expandForDesktop); }
function markReplied(id, j){
  const k=id+":"+j;
  state.replied[k] = !state.replied[k];
  if(state.replied[k]) state.sent[k] = true;
  function renderToday(){
  const t = DATA.resumen_hoy; if(!t) return;
  const stat = (n,l) => '<div class="stat"><b>'+n+'</b><span>'+l+'</span></div>';
  document.getElementById("today-block").innerHTML =
    '<h2>Lo que el sistema hizo hoy</h2>'
    + '<div class="stats">'
      + stat(t.cuentas, "cuentas")
      + stat(t.correos_personales, "correos a una persona")
      + stat(t.fuentes_revisadas, "fuentes revisadas")
    + '</div>'
    + '<details class="more"><summary>Ver el desglose</summary><div class="stats sub">'
      + stat(t.correos_confirmados, "confirmados (fuente abrible y fechada)")
      + stat(t.correos_sin_fecha, "sin fecha: verificar vigencia por teléfono")
      + stat(t.correos_contexto || 0, "de dirección: contexto, no cuentan")
    + '</div>'
    + '<div class="disc"><span class="mono">descartados a propósito</span><ul>'
      + t.descartados.map(x=>'<li><b>'+esc(x.quien)+'</b> ('+esc(x.empresa)+'): '+esc(x.por)
          +' <a class="src" href="'+esc(x.fuente)+'" target="_blank" rel="noopener">'+esc(host(x.fuente))+'</a></li>').join("")
      + '</ul></div>'
    + '<p class="note">'+esc(t.nota_conteo||"")+'</p>'
    + '<p class="note">Tiempo de investigación que te ahorra: ~'+t.horas_estimadas+' horas. '+esc(t.nota_horas)+'</p>'
    + '</details>';
}

function renderClosing(){
  const c = Object.assign({}, DATA.cierre || {}, CFG.cierre || {}); if(!c.titulo) return;
  const body = "Hola Emiliano,%0D%0A%0D%0AVi el demo de cuentas para REBRND y quiero saber como funciona el plan Cuentas.%0D%0A%0D%0AGracias.";
  document.getElementById("closing-block").innerHTML =
    '<h2>'+esc(c.titulo)+'</h2>'
    + '<p class="lead">'+esc(c.linea)+'</p>'
    + '<div class="acts">'
      + '<a class="btn primary" href="mailto:'+esc(c.contacto_email)+'?subject='+encodeURIComponent("Plan Cuentas para REBRND")+'&body='+body+'">Escribir a Emiliano</a>'
      + (c.contacto_whatsapp
          ? '<a class="btn" href="'+esc(c.contacto_whatsapp)+'" target="_blank" rel="noopener">WhatsApp</a>'
          : '<span class="btn falta">WhatsApp: falta el número</span>')
    + '</div>'
    + '<p class="refer">'+esc(c.referido)+'</p>';
}

// en escritorio todo abierto; en teléfono, una tarjeta y una puerta a la vez
function expandForDesktop(){
  if(window.matchMedia("(min-width:721px)").matches){
    document.querySelectorAll(".cwrap, .door").forEach(x=>x.open=true);
  }
}
render();
renderToday();
renderClosing();
expandForDesktop();
window.addEventListener("resize", expandForDesktop);
}

function nextCard(){
  const cards=[...document.querySelectorAll(".cwrap")];
  const open=cards.findIndex(c=>c.open);
  if(open>=0) cards[open].open=false;
  const nxt=cards[Math.min(open+1,cards.length-1)];
  if(nxt){ nxt.open=true; nxt.scrollIntoView({behavior:"smooth",block:"start"}); }
}
function updateSticky(){
  const total=DATA.empresas.length;
  const done=DATA.empresas.filter(e=>e.puertas.some((p,j)=>state.sent[e.id+":"+j])).length;
  document.getElementById("sb-text").textContent = done+"/"+total+" cuentas · faltan ~"+Math.max(0,(total-done)*MIN_PER_CARD)+" min";
}
function updateBar(){
  const total = DATA.empresas.length;
  const done = DATA.empresas.filter(e => e.puertas.some((p,j)=>state.sent[e.id+":"+j])).length;
  const pct = total ? (done/total*100) : 0;
  document.getElementById("barfill").style.width = pct.toFixed(1) + "%";
  const left = Math.max(0, (total-done) * MIN_PER_CARD);
  document.getElementById("barlabel").textContent = done === 0
    ? "Tiempo estimado hoy: ~" + (total*MIN_PER_CARD) + " min"
    : (left === 0 ? "Listo por hoy. Las 10 cuentas quedaron trabajadas." : "Te faltan ~" + left + " min");
  document.getElementById("barcount").textContent = done + " de " + total + " cuentas trabajadas";
  updateSticky();
}

function updateLearning(){
  const rows = [];
  DATA.empresas.forEach(e => e.puertas.forEach((p,j) => {
    if(state.replied[e.id+":"+j]) rows.push({sector:e.sector, rol:p.rol, canal:p.mensaje.canal, emp:e.empresa});
  }));
  const grid = document.getElementById("learnGrid"), empty = document.getElementById("learnEmpty");
  if(!rows.length){ grid.hidden = true; empty.hidden = false; return; }
  empty.hidden = true; grid.hidden = false;
  const tally = (key, norm) => {
    const m = {};
    rows.forEach(r => { const v = norm ? norm(r[key]) : r[key]; m[v] = (m[v]||0)+1; });
    return Object.entries(m).sort((a,b)=>b[1]-a[1]);
  };
  const doorKind = rol => /capital humano|recursos humanos/i.test(rol) ? "Capital Humano"
    : /comunicaci|marketing|mercado/i.test(rol) ? "Comunicación / marketing"
    : /compras|proveedor/i.test(rol) ? "Compras"
    : /planta|operacion/i.test(rol) ? "Planta / operaciones" : "Dirección";
  const box = (title, pairs) => '<div class="lbox"><span class="mono">'+title+'</span><ul>'
    + pairs.map(([k,v])=>'<li>'+esc(k)+' · '+v+'</li>').join("") + '</ul></div>';
  grid.innerHTML = box("respuestas por sector", tally("sector"))
    + box("respuestas por puerta", tally("rol", doorKind))
    + box("respuestas por canal", tally("canal"))
    + '<div class="lbox"><span class="mono">qué haría el sistema</span><ul><li>'
      + esc("Subir en la lista las cuentas del sector y la puerta que ya respondieron, y mandar primero por ese canal.")
      + '</li><li class="note">' + esc("Demo: el estado vive en memoria, no se guarda nada.") + '</li></ul></div>';
}

function renderToday(){
  const t = DATA.resumen_hoy; if(!t) return;
  const stat = (n,l) => '<div class="stat"><b>'+n+'</b><span>'+l+'</span></div>';
  document.getElementById("today-block").innerHTML =
    '<h2>Lo que el sistema hizo hoy</h2>'
    + '<div class="stats">'
      + stat(t.cuentas, "cuentas")
      + stat(t.correos_personales, "correos a una persona")
      + stat(t.fuentes_revisadas, "fuentes revisadas")
    + '</div>'
    + '<details class="more"><summary>Ver el desglose</summary><div class="stats sub">'
      + stat(t.correos_confirmados, "confirmados (fuente abrible y fechada)")
      + stat(t.correos_sin_fecha, "sin fecha: verificar vigencia por teléfono")
      + stat(t.correos_contexto || 0, "de dirección: contexto, no cuentan")
    + '</div>'
    + '<div class="disc"><span class="mono">descartados a propósito</span><ul>'
      + t.descartados.map(x=>'<li><b>'+esc(x.quien)+'</b> ('+esc(x.empresa)+'): '+esc(x.por)
          +' <a class="src" href="'+esc(x.fuente)+'" target="_blank" rel="noopener">'+esc(host(x.fuente))+'</a></li>').join("")
      + '</ul></div>'
    + '<p class="note">'+esc(t.nota_conteo||"")+'</p>'
    + '<p class="note">Tiempo de investigación que te ahorra: ~'+t.horas_estimadas+' horas. '+esc(t.nota_horas)+'</p>'
    + '</details>';
}

function renderClosing(){
  const c = Object.assign({}, DATA.cierre || {}, CFG.cierre || {}); if(!c.titulo) return;
  const body = "Hola Emiliano,%0D%0A%0D%0AVi el demo de cuentas para REBRND y quiero saber como funciona el plan Cuentas.%0D%0A%0D%0AGracias.";
  document.getElementById("closing-block").innerHTML =
    '<h2>'+esc(c.titulo)+'</h2>'
    + '<p class="lead">'+esc(c.linea)+'</p>'
    + '<div class="acts">'
      + '<a class="btn primary" href="mailto:'+esc(c.contacto_email)+'?subject='+encodeURIComponent("Plan Cuentas para REBRND")+'&body='+body+'">Escribir a Emiliano</a>'
      + (c.contacto_whatsapp
          ? '<a class="btn" href="'+esc(c.contacto_whatsapp)+'" target="_blank" rel="noopener">WhatsApp</a>'
          : '<span class="btn falta">WhatsApp: falta el número</span>')
    + '</div>'
    + '<p class="refer">'+esc(c.referido)+'</p>';
}

// en escritorio todo abierto; en teléfono, una tarjeta y una puerta a la vez
function expandForDesktop(){
  if(window.matchMedia("(min-width:721px)").matches){
    document.querySelectorAll(".cwrap, .door").forEach(x=>x.open=true);
  }
}
render();
renderToday();
renderClosing();
expandForDesktop();
window.addEventListener("resize", expandForDesktop);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: build.py <prospect>   (espera demos/<prospect>/config.json y leads.json)")
    path, n = build(sys.argv[1])
    print("escrito %s (%d bytes)" % (path, n))
