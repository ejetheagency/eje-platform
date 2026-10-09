# factory/test_fit.py  (run: python3 -m factory.test_fit)
# Locks the fit-score repair (queue item 1, 2026-10-09). Pure unit assertions, no DB, no network, no spend.
# Each case is a defect found in the REAL pooled 2uplatam cards, so a regression here is a regression in what ships.
from factory.workers import fit

PASS = True
IC = {"geo": "Ecuador", "prefer_female_decisor": True}


def check(label, cond):
    global PASS
    print(("  PASS " if cond else "  FAIL ") + label)
    PASS = PASS and cond


def score(co=None, ct=None, sigs=None, ic=None):
    return fit.fit_score(co or {}, ct or {}, sigs or [], ic if ic is not None else IC)


def main():
    print("Fit score repair\n")

    # --- geo: companies.country is empty for 28 of the 29 pooled cards that have a companies row ---
    check("geo from ccTLD when country is empty", fit.geo_country({"domain": "indicium.com.ec"}) == "Ecuador")
    check("geo from a bare ccTLD", fit.geo_country({"domain": "aborigen.ec"}) == "Ecuador")
    check("geo from the website when there is no domain", fit.geo_country({"website": "https://www.somos.rest/x"}) == "")
    check("geo from the phone dial code", fit.geo_country({}, {"phone": "+593 99 123 4567"}) == "Ecuador")
    check("longest dial code wins (593 not 59)", fit.geo_country({}, {"phone": "+5939912345"}) == "Ecuador")
    check("stored country still wins", fit.geo_country({"country": "Mexico", "domain": "x.com.ec"}) == "Mexico")
    check("unknown country stays unknown (never guessed)", fit.geo_country({"domain": "example.com"}) == "")
    check("an .ec lead now scores the geo match",
          score({"domain": "indicium.com.ec"}, {"full_name": "Ana Lopez", "title": "Presidente"}) >
          score({"domain": "indicium.example"}, {"full_name": "Ana Lopez", "title": "Presidente"}))

    # --- seniority: titles that were scoring the generic +12 ---
    for t in ("Decano de la Facultad de Ciencias Economicas", "Decana de la Facultad", "Rector", "Rectora",
              "Vicerrector Academico", "Subdecano de la Facultad", "Subdecana", "Sub-decano",
              "Socia", "Socio", "Dueña", "Dueno", "Fundadora", "Fundador", "CEO",
              "Propietaria", "propietario", "Chef copropietario", "Director General", "Gerente General"):
        check("owner-level: %s" % t, bool(fit._OWNER.search(t.lower())))
    # "Director/a" splits by WHAT is being directed: the organization or the unit we sell to (decisor) vs a
    # craft inside someone else's company (mid). This is the one judgment in the repair, so it is pinned here.
    for t in ("Director Ejecutivo", "Directora Ejecutiva"):
        check("owner-level: %s" % t, bool(fit._OWNER.search(t.lower())))

    # --- ACADEMIC AUTHORITY TIER: scores as decisor (the unit's budget holder), without being owner-level ---
    def academic(t):
        return bool(fit._ACADEMIC.search(fit._strip_accents(t).lower()))

    for t in ("Coordinador Academico (carreras de Marketing)", "Coordinadora Académica", "Coordinador de Carrera",
              "Coordinadora de Programa", "Jefe de Departamento", "Jefa de Departamento", "Jefe de Carrera",
              "Director de Escuela de Negocios", "Directora de Carrera de Administracion", "Director de Facultad",
              "Director de Posgrado", "Director de Departamento",
              "Director de Carrera de Administracion de Empresas (sede Cuenca)"):
        check("academic authority (decisor): %s" % t[:48], academic(t))
    check("accented and unaccented behave identically",
          academic("Coordinadora Académica") == academic("Coordinadora Academica") is True)
    # Teaching or researching is not deciding. These stay mid, i.e. below the fit floor on their own.
    for t in ("Docente", "Docente-investigador de la Facultad de Ciencias", "Docente investigador", "Profesor",
              "Profesora titular de la Facultad"):
        check("NOT academic authority (teaches, does not decide): %s" % t[:44], not academic(t))
    # "titular" = owner in business Spanish, TENURE in academia. The owner pattern has matched it for far longer
    # than universities have been in the ICP, so without disambiguation every tenured professor read as an owner.
    check("'Profesora titular' is NOT an owner (academic tenure)",
          score({"domain": "u.edu.ec"}, {"full_name": "Silvia Norona", "title": "Profesora titular de la Facultad"}) < 60)
    check("'Titular de la empresa' IS still an owner",
          score({"domain": "x.com.ec"}, {"full_name": "Luis Paz", "title": "Titular de la empresa"}) >= 60)
    check("a genuine owner who also teaches stays owner-level",
          score({"domain": "x.com.ec"}, {"full_name": "Ana Vera", "title": "Dueña y profesora"}) >=
          score({"domain": "x.com.ec"}, {"full_name": "Ana Vera", "title": "Dueña"}))
    check("authority wins when a card says both: 'Docente y Coordinador de Carrera'",
          academic("Docente y Coordinador de Carrera"))
    for t in ("Coordinador de Redes Sociales", "Coordinadora de Emprendimiento e Innovacion", "Director de Arte"):
        check("NOT academic authority (not an academic unit): %s" % t[:44], not academic(t))
    check("a Docente-investigador stays below the fit floor",
          score({"domain": "u.edu.ec"}, {"full_name": "Cesar Guerrero",
                                         "title": "Docente-investigador de la Facultad de Ciencias"}) < 60)
    check("a Coordinador Academico clears the fit floor",
          score({"domain": "u.edu.ec", "linkedin": "x"},
                {"full_name": "Oscar Calderon", "title": "Coordinador Academico (carreras de Marketing)"}) >= 60)
    for t in ("Director de Arte", "Director de Marketing", "Director Creativo", "Directora de Comunicaciones"):
        check("mid-level (directs a craft): %s" % t,
              bool(fit._MID.search(t.lower())) and not fit._OWNER.search(t.lower()))
    for t in ("Coordinadora de Emprendimiento", "Director de Arte", "Gerente de Marketing", "Jefe de Operaciones",
              "Director", "Directora Comercial", "Gerente de Redes Sociales"):
        check("mid-level (not owner): %s" % t, bool(fit._MID.search(t.lower())) and not fit._OWNER.search(t.lower()))
    # SUBSTRING TRAPS: each of these matched owner-level before the word boundaries went in. A false owner match
    # inflates fit, and fit decides who the client gets tomorrow, so these are the cases that matter most.
    for t in ("Director de Arte", "Directora Comercial", "Gerente de Redes Sociales", "Especialista en Medios Sociales",
              "Asociado Senior", "Trabajadora Social", "Community Manager de Redes Sociales"):
        check("NOT owner-level (substring trap): %s" % t, not fit._OWNER.search(t.lower()))
    check("a Decana outscores a Coordinadora",
          score({"domain": "u.edu.ec"}, {"full_name": "Maria Paz", "title": "Decana de la Facultad"}) >
          score({"domain": "u.edu.ec"}, {"full_name": "Maria Paz", "title": "Coordinadora de Emprendimiento"}))

    # --- empty title on a one-person business: the signal was in the card all along ---
    check("role word on the person", fit.owner_signal("Domenica (cofundadora)", {"name": "Everglow Candles"}))
    check("role word in the company brief (own site)",
          fit.owner_signal("Alejandra Tapia", {"name": "YogaLe Studio", "brief": "yoga en Quito. Duena mujer con 4 canales"}))
    check("company named after the person",
          fit.owner_signal("Nadia Valdivieso", {"name": "NadiaVaro Consultora", "domain": "nadiavaro.com"}))
    check("empty title + owner signal scores owner-level",
          score({"name": "Everglow Candles", "domain": "everglow.ec"}, {"full_name": "Domenica (cofundadora)"}) ==
          score({"name": "Everglow Candles", "domain": "everglow.ec"}, {"full_name": "Domenica", "title": "CEO"}))

    # THE TRAP: "fundada/cofundado en 2024" says when the COMPANY started, not who decides. It must NOT read as a
    # person's owner role, or every company with a founding date in its brief would score as owner-run.
    check("'Fundada 21-ago-2024' is NOT an owner signal",
          not fit.owner_signal("Mikaela Rosero", {"name": "Matiz Studio", "brief": "marketing. Fundada 21-ago-2024"}))
    check("'Cofundado por mujer' alone is NOT an owner signal",
          not fit.owner_signal("Carla", {"name": "Pilates Conecta", "brief": "pilates. Cofundado por mujer; 3 sedes"}))
    check("a short name token cannot match a random substring",
          not fit.owner_signal("Ana Ruiz", {"name": "Banana Republic Quito", "domain": "bananarepublic.ec"}))
    check("no title and no owner signal stays unscored on seniority",
          not fit.owner_signal("Juan Perez", {"name": "Acme Industrial", "domain": "acme.ec"}))

    # --- PER-CLIENT decisor titles (icp_config.decisor_titles_extra), not the global scorer ---
    # "Coordinador/a de Emprendimiento / Innovacion" decides for 2uplatam (a scale hub sold into university
    # entrepreneurship programs). For another client the same title is a middle manager, so it lives in config.
    UP = {"geo": "Ecuador", "prefer_female_decisor": True, "decisor_titles_extra": [
        r"\bcoordinador[ao]?\b[^,;|]{0,24}\b(?:emprendimiento|innovacion)\b",
        r"\b(?:jefe|jefa|director[ao]?)\b[^,;|]{0,24}\b(?:emprendimiento|innovacion)\b"]}

    def cdt(t, ic=UP):
        return fit._client_decisor_title(fit._strip_accents(t).lower(), ic)

    for t in ("Coordinadora de Emprendimiento e Innovacion", "Coordinadora de Emprendimiento e Innovación",
              "Coordinador de Innovacion Social", "Jefa de Emprendimiento", "Directora de Innovacion"):
        check("client decisor title: %s" % t[:44], cdt(t))
    check("accents do not change the client match",
          cdt("Coordinadora de Emprendimiento e Innovación") == cdt("Coordinadora de Emprendimiento e Innovacion") is True)
    check("the same title is NOT a decisor for a client without the config", not cdt("Coordinadora de Emprendimiento", IC))
    check("client config lifts the card over the floor",
          score({"domain": "u.edu.ec", "linkedin": "x"},
                {"full_name": "Amparo Pilicita", "title": "Coordinadora de Emprendimiento e Innovacion"}, ic=UP) >= 60)
    check("without the config the same card stays under the floor",
          score({"domain": "u.edu.ec", "linkedin": "x"},
                {"full_name": "Amparo Pilicita", "title": "Coordinadora de Emprendimiento e Innovacion"}, ic=IC) < 60)
    # TEACHING IS NOT DECIDING, FOR ANY CLIENT: a config that tries to promote it is refused, not obeyed.
    BAD = {"geo": "Ecuador", "decisor_titles_extra": [r"docente", r"\bdocente-investigador\b", r"profesor"]}
    for t in ("Docente", "Docente-investigador de la Facultad", "Profesora titular"):
        check("config cannot promote teaching: %s" % t[:40], not cdt(t, BAD))
    check("a malformed client regex cannot break scoring",
          not cdt("coordinador de emprendimiento", {"decisor_titles_extra": ["(unclosed["]}))
    check("one client's config never raises another client's score",
          score({"domain": "u.edu.ec"}, {"full_name": "X", "title": "Coordinadora de Emprendimiento"}, ic=IC) ==
          score({"domain": "u.edu.ec"}, {"full_name": "X", "title": "Coordinadora de Emprendimiento"}, ic={"geo": "Ecuador", "prefer_female_decisor": True}))

    # --- the repair only ADDS credit: it must never lower a score (proved over the real pool, locked here) ---
    cases = [({"domain": "x.com.ec", "country": "Ecuador"}, {"full_name": "Ana", "title": "CEO"}),
             ({"domain": "x.com", "country": ""}, {"full_name": "Luis", "title": ""}),
             ({"domain": "x.ec"}, {"full_name": "Maria", "title": "Coordinadora"})]
    check("scores stay within 0..100", all(0 <= score(co, ct) <= 100 for co, ct in cases))

    # --- the card adapter must agree with the DB path: ONE scorer, two ways in ---
    ld = {"companyName": "Indicium S.A.", "_key": "indicium.com.ec", "website": "https://indicium.com.ec",
          "country": "Ecuador", "contactName": "David Bonilla", "contactTitle": "Presidente",
          "contactEmail": "info@indicium.com.ec", "companyBrief": "consultoria", "whyNow": []}
    co = {"name": ld["companyName"], "domain": ld["_key"], "website": ld["website"], "country": ld["country"],
          "brief": ld["companyBrief"], "instagram": None, "linkedin": None, "instagramFollowers": 0, "whatsapp": None}
    ct = {"full_name": ld["contactName"], "title": ld["contactTitle"], "email": ld["contactEmail"],
          "phone": None, "linkedin_url": None}
    check("fit_score_card == fit_score on the same lead", fit.fit_score_card(ld, IC) == fit.fit_score(co, ct, [], IC))

    print("\n" + ("FIT TEST: PASS" if PASS else "FIT TEST: FAIL"))
    return PASS


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
