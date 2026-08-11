from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import (FileResponse, HTMLResponse, PlainTextResponse,
                               RedirectResponse, StreamingResponse)
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.modules.auth.models import AuditLog, User
from app.modules.notifikacije import mailer
from app.modules.reklamacije import privici as pr
from app.modules.reklamacije.models import CAPA, SCAR, Privitak, Reklamacija, StavkaTroska
from app.modules.reklamacije.utils import generiraj_excel, generiraj_pdf

router = APIRouter(prefix="/reklamacije", tags=["reklamacije"])
templates = Jinja2Templates(directory="app/templates")

PER_PAGE = 50

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _auto_broj(db: Session) -> str:
    godina = datetime.now().year
    prefix = f"RK-{godina}-"
    count = db.scalar(
        select(func.count(Reklamacija.id))
        .where(Reklamacija.broj_predmeta.like(f"{prefix}%"))
    ) or 0
    return f"{prefix}{count + 1:04d}"


def _parse_rek(form) -> dict:
    def s(k): return str(form.get(k, "")).strip() or None
    def d(k):
        v = str(form.get(k, "")).strip()
        try: return date.fromisoformat(v)
        except: return None
    def i10(k):
        v = str(form.get(k, "")).strip()
        try:
            n = int(v)
            return n if 1 <= n <= 10 else None
        except: return None

    return dict(
        vrsta=str(form.get("vrsta", "INTERNA")),
        status=str(form.get("status", "NOVO")),
        prioritet=str(form.get("prioritet", "SREDNJI")),
        kategorija=s("kategorija"),
        defekt_kategorija=s("defekt_kategorija"),
        izvor=s("izvor"),
        tezina=s("tezina"),
        naslov=str(form.get("naslov", "")).strip() or "Bez naslova",
        opis=str(form.get("opis", "")).strip(),
        prijavitelj=str(form.get("prijavitelj", "")).strip(),
        kupac_dobavljac=s("kupac_dobavljac"),
        referentni_broj=s("referentni_broj"),
        naziv_proizvoda=s("naziv_proizvoda"),
        broj_radnog_naloga=s("broj_radnog_naloga"),
        stroj=s("stroj"),
        osoblje=s("osoblje"),
        rok_rjesavanja=d("rok_rjesavanja"),
        korekcija=s("korekcija"),
        analiza_uzroka=s("analiza_uzroka"),
        uzrok_kategorija=s("uzrok_kategorija"),
        napomena=s("napomena"),
        vezana_nesukladnost=s("vezana_nesukladnost"),
        promjene_sustava=s("promjene_sustava"),
        broj_promjene=s("broj_promjene"),
        # Polja papirnatog obrasca „Nesukladnost"
        izvorni_broj=s("izvorni_broj"),
        porijeklo=s("porijeklo"),
        porijeklo_napomena=s("porijeklo_napomena"),
        korekciju_proveo=s("korekciju_proveo"),
        korekcija_datum=d("korekcija_datum"),
        uzrok_potvrdio=s("uzrok_potvrdio"),
        potrebna_korektivna=s("potrebna_korektivna"),
        radnju_definirao=s("radnju_definirao"),
        sifra_materijala=s("sifra_materijala"),
        lot_sarza=s("lot_sarza"),
        broj_primke=s("broj_primke"),
        direktor_potpis=s("direktor_potpis"),
        fmea_sev=i10("fmea_sev"),
        fmea_occ=i10("fmea_occ"),
        fmea_det=i10("fmea_det"),
    )


def _load(db: Session, id: int) -> Reklamacija | None:
    return db.scalar(
        select(Reklamacija)
        .where(Reklamacija.id == id)
        .options(selectinload(Reklamacija.capa), selectinload(Reklamacija.privici),
                 selectinload(Reklamacija.troskovi), selectinload(Reklamacija.scars))
    )


def _ctx():
    return {
        "vrsta_choices": list(Reklamacija.VRSTA.items()),
        "status_choices": list(Reklamacija.STATUS.items()),
        "prioritet_choices": list(Reklamacija.PRIORITET.items()),
        "kategorija_choices": list(Reklamacija.KATEGORIJA.items()),
        "izvor_choices": list(Reklamacija.IZVOR.items()),
        "tezina_choices": list(Reklamacija.TEZINA.items()),
        "defekt_choices": list(Reklamacija.DEFEKT.items()),
        "porijeklo_opcije": Reklamacija.PORIJEKLO,
        "capa_vrsta_choices": list(CAPA.VRSTA.items()),
        "capa_status_choices": list(CAPA.STATUS.items()),
        "trosak_kat_choices": list(StavkaTroska.KATEGORIJA.items()),
        "snosi_choices": list(StavkaTroska.SNOSI.items()),
        "scar_status_choices": list(SCAR.STATUS.items()),
        "scar_rjesenje_choices": list(SCAR.RJESENJE.items()),
        "today": date.today(),
    }


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    ukupno       = db.scalar(select(func.count(Reklamacija.id))) or 0
    otvorene     = db.scalar(select(func.count(Reklamacija.id))
                             .where(Reklamacija.status.notin_(["RIJESENO","ZATVORENO"]))) or 0
    prekoraceni  = db.scalar(select(func.count(Reklamacija.id))
                             .where(Reklamacija.rok_rjesavanja < date.today())
                             .where(Reklamacija.status.notin_(["RIJESENO","ZATVORENO"]))) or 0
    capa_otv     = db.scalar(select(func.count(CAPA.id)).where(CAPA.status != "IZVRSENA")) or 0
    copq_ukupno  = db.scalar(select(func.coalesce(func.sum(StavkaTroska.iznos), 0.0))) or 0.0
    copq_neto    = db.scalar(select(func.coalesce(func.sum(StavkaTroska.iznos), 0.0))
                             .where(StavkaTroska.povrativo == False)) or 0.0  # noqa: E712

    po_statusu = db.execute(
        select(Reklamacija.status, func.count(Reklamacija.id).label("n"))
        .group_by(Reklamacija.status)
    ).all()
    po_vrsti = db.execute(
        select(Reklamacija.vrsta, func.count(Reklamacija.id).label("n"))
        .group_by(Reklamacija.vrsta)
    ).all()

    zadnjih = db.scalars(
        select(Reklamacija).options(selectinload(Reklamacija.capa))
        .order_by(Reklamacija.datum_prijave.desc()).limit(10)
    ).all()
    kriticne = db.scalars(
        select(Reklamacija).where(Reklamacija.prioritet == "KRITICAN")
        .where(Reklamacija.status.notin_(["RIJESENO","ZATVORENO"]))
        .options(selectinload(Reklamacija.capa))
    ).all()

    return templates.TemplateResponse(request, "reklamacije/dashboard.html", {
        **_ctx(),
        "ukupno": ukupno, "otvorene": otvorene,
        "prekoraceni": prekoraceni, "capa_otv": capa_otv,
        "copq_ukupno": copq_ukupno, "copq_neto": copq_neto,
        "po_statusu": [(s, Reklamacija.STATUS.get(s,s), n) for s,n in po_statusu],
        "po_vrsti":   [(v, Reklamacija.VRSTA.get(v,v),  n) for v,n in po_vrsti],
        "zadnjih": zadnjih, "kriticne": kriticne,
    })


# ─── Analitika (Dashboard 2.0) ────────────────────────────────────────────────

@router.get("/analitika", response_class=HTMLResponse)
def analitika(request: Request, db: Session = Depends(get_db)):
    # 1) Pareto po kategoriji defekta (A–J), sortirano + kumulativni %
    redci = db.execute(
        select(Reklamacija.defekt_kategorija, func.count(Reklamacija.id))
        .where(Reklamacija.defekt_kategorija.is_not(None))
        .group_by(Reklamacija.defekt_kategorija)
    ).all()
    parovi = sorted(((Reklamacija.DEFEKT.get(k, k), n) for k, n in redci), key=lambda x: -x[1])
    uk = sum(n for _, n in parovi) or 1
    kum = 0
    pareto = []
    for label, n in parovi:
        kum += n
        pareto.append({"label": label, "n": n, "kum_pct": round(100 * kum / uk, 1)})

    # 2) Trend po mjesecu (broj reklamacija + COPQ neto), zadnjih 12 mj
    mj_broj = dict(db.execute(
        select(func.strftime("%Y-%m", Reklamacija.datum_prijave), func.count(Reklamacija.id))
        .group_by(func.strftime("%Y-%m", Reklamacija.datum_prijave))
    ).all())
    mj_copq = dict(db.execute(
        select(func.strftime("%Y-%m", Reklamacija.datum_prijave),
               func.coalesce(func.sum(StavkaTroska.iznos), 0.0))
        .join(StavkaTroska, StavkaTroska.reklamacija_id == Reklamacija.id)
        .where(StavkaTroska.povrativo == False)  # noqa: E712
        .group_by(func.strftime("%Y-%m", Reklamacija.datum_prijave))
    ).all())
    mjeseci = sorted(set(mj_broj) | set(mj_copq))[-12:]
    trend = [{"mj": m, "broj": mj_broj.get(m, 0), "copq": round(mj_copq.get(m, 0.0), 2)} for m in mjeseci]

    # 3) On-time zatvaranje (zatvorene: rok ispoštovan vs prekoračen)
    zatvorene = db.scalars(
        select(Reklamacija).where(Reklamacija.datum_zatvaranja.is_not(None))
        .where(Reklamacija.rok_rjesavanja.is_not(None))
    ).all()
    on_time = sum(1 for r in zatvorene if r.datum_zatvaranja.date() <= r.rok_rjesavanja)
    late = len(zatvorene) - on_time
    ontime_pct = round(100 * on_time / len(zatvorene), 1) if zatvorene else None

    # 4) Recurrence: udio reklamacija koje referenciraju vezanu nesukladnost
    total = db.scalar(select(func.count(Reklamacija.id))) or 0
    ponovljene = db.scalar(select(func.count(Reklamacija.id))
                           .where(Reklamacija.vezana_nesukladnost.is_not(None))
                           .where(Reklamacija.vezana_nesukladnost != "")) or 0
    recurrence_pct = round(100 * ponovljene / total, 1) if total else 0.0

    # 5) Po izvoru defekta
    po_izvoru = [{"label": Reklamacija.IZVOR.get(k, k or "—"), "n": n} for k, n in db.execute(
        select(Reklamacija.izvor, func.count(Reklamacija.id)).group_by(Reklamacija.izvor)
    ).all()]

    # 6) COPQ po snosiocu
    snos = dict(db.execute(
        select(StavkaTroska.tko_snosi, func.coalesce(func.sum(StavkaTroska.iznos), 0.0))
        .group_by(StavkaTroska.tko_snosi)
    ).all())
    copq_snosilac = {k: round(snos.get(k, 0.0), 2) for k in ("INTERNO", "KUPAC", "DOBAVLJAC")}

    # 7) Top dobavljači po SCAR (broj + naplaćeno)
    top_dobavljaci = [
        {"dobavljac": d, "broj": n, "naplaceno": round(iz or 0.0, 2)}
        for d, n, iz in db.execute(
            select(SCAR.dobavljac, func.count(SCAR.id), func.coalesce(func.sum(SCAR.iznos_priznat), 0.0))
            .group_by(SCAR.dobavljac).order_by(func.count(SCAR.id).desc()).limit(8)
        ).all()
    ]

    return templates.TemplateResponse(request, "reklamacije/analitika.html", {
        **_ctx(),
        "pareto": pareto, "trend": trend,
        "on_time": on_time, "late": late, "ontime_pct": ontime_pct,
        "ponovljene": ponovljene, "recurrence_pct": recurrence_pct, "total": total,
        "po_izvoru": po_izvoru, "copq_snosilac": copq_snosilac,
        "top_dobavljaci": top_dobavljaci,
    })


# ─── Supplier scorecard ───────────────────────────────────────────────────────

@router.get("/dobavljaci", response_class=HTMLResponse)
def dobavljaci(request: Request, db: Session = Depends(get_db)):
    scars = db.scalars(select(SCAR)).all()
    agg: dict[str, dict] = {}
    for s in scars:
        d = agg.setdefault(s.dobavljac, {
            "dobavljac": s.dobavljac, "broj": 0, "otvoreni": 0,
            "reklamirano": 0.0, "naplaceno": 0.0, "dana_odgovor": [], "zatvoreni": 0,
        })
        d["broj"] += 1
        if s.je_zatvoren: d["zatvoreni"] += 1
        else: d["otvoreni"] += 1
        d["reklamirano"] += s.iznos_reklamiran or 0.0
        d["naplaceno"] += s.iznos_priznat or 0.0
        if s.datum_slanja and s.datum_odgovora:
            d["dana_odgovor"].append((s.datum_odgovora - s.datum_slanja).days)

    kartice = []
    for d in agg.values():
        dani = d.pop("dana_odgovor")
        d["prosj_odgovor"] = round(sum(dani) / len(dani), 1) if dani else None
        d["stopa_naplate"] = (round(100 * d["naplaceno"] / d["reklamirano"], 1)
                              if d["reklamirano"] else None)
        d["reklamirano"] = round(d["reklamirano"], 2)
        d["naplaceno"] = round(d["naplaceno"], 2)
        kartice.append(d)
    kartice.sort(key=lambda x: -x["broj"])

    return templates.TemplateResponse(request, "reklamacije/dobavljaci.html",
                                      {**_ctx(), "kartice": kartice})


# ─── Lista ────────────────────────────────────────────────────────────────────

@router.get("/lista", response_class=HTMLResponse)
def lista(request: Request):
    return templates.TemplateResponse(request, "reklamacije/list.html", _ctx())


@router.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "", status: str = "", vrsta: str = "",
           prioritet: str = "", dodijeljeni: int = 0, page: int = 1,
           db: Session = Depends(get_db)):
    conds = []
    if q:
        like = f"%{q}%"
        conds.append(or_(
            Reklamacija.broj_predmeta.ilike(like),
            Reklamacija.naslov.ilike(like),
            Reklamacija.prijavitelj.ilike(like),
            Reklamacija.kupac_dobavljac.ilike(like),
            Reklamacija.naziv_proizvoda.ilike(like),
            Reklamacija.opis.ilike(like),
        ))
    if status:  conds.append(Reklamacija.status == status)
    if vrsta:   conds.append(Reklamacija.vrsta == vrsta)
    if prioritet: conds.append(Reklamacija.prioritet == prioritet)
    if dodijeljeni: conds.append(Reklamacija.dodijeljeno_id == dodijeljeni)

    total = db.scalar(select(func.count(Reklamacija.id)).where(*conds)) or 0
    page  = max(1, page)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page  = min(page, total_pages)

    rows = db.scalars(
        select(Reklamacija).where(*conds)
        .options(selectinload(Reklamacija.capa))
        .order_by(Reklamacija.datum_prijave.desc())
        .offset((page-1)*PER_PAGE).limit(PER_PAGE)
    ).all()

    return templates.TemplateResponse(request, "reklamacije/_table_body.html", {
        **_ctx(), "reklamacije": rows, "q": q,
        "filter_status": status, "filter_vrsta": vrsta, "filter_prioritet": prioritet,
        "filter_dodijeljeni": dodijeljeni,
        "page": page, "total": total, "total_pages": total_pages, "per_page": PER_PAGE,
    })


# ─── Nova ─────────────────────────────────────────────────────────────────────

@router.get("/nova", response_class=HTMLResponse)
def nova_get(request: Request):
    return templates.TemplateResponse(request, "reklamacije/detail.html", {**_ctx(), "r": None})


@router.post("/nova", response_class=RedirectResponse)
async def nova_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = _parse_rek(form)
    r = Reklamacija(**data, broj_predmeta=_auto_broj(db))
    db.add(r); db.commit(); db.refresh(r)
    try: mailer.obavijesti_nova(db, r)
    except Exception: pass
    return RedirectResponse(f"/reklamacije/{r.id}", status_code=303)


# ─── Detail ───────────────────────────────────────────────────────────────────

def _aktivni_korisnici(db: Session):
    return db.scalars(select(User).where(User.aktivan.is_(True)).order_by(User.username)).all()


def _timeline(db: Session, predmet_id: int):
    return db.scalars(
        select(AuditLog).where(AuditLog.predmet_id == predmet_id)
        .order_by(AuditLog.timestamp.desc()).limit(50)
    ).all()


@router.get("/{id}", response_class=HTMLResponse)
def detail(request: Request, id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return HTMLResponse("Nije pronađeno.", status_code=404)
    return templates.TemplateResponse(request, "reklamacije/detail.html", {
        **_ctx(), "r": r,
        "korisnici": _aktivni_korisnici(db),
        "timeline": _timeline(db, id),
    })


@router.post("/{id}/dodijeli", response_class=RedirectResponse)
async def dodijeli(request: Request, id: int, db: Session = Depends(get_db)):
    r = db.get(Reklamacija, id)
    if not r:
        return RedirectResponse("/reklamacije/lista", status_code=303)
    form = await request.form()
    kid = str(form.get("dodijeljeno_id", "")).strip()
    if not kid:
        r.dodijeljeno_id = None
        r.dodijeljeno_ime = None
    else:
        u = db.get(User, int(kid)) if kid.isdigit() else None
        if u:
            r.dodijeljeno_id = u.id
            r.dodijeljeno_ime = u.ime or u.username
    db.commit()
    if r.dodijeljeno_id:
        try: mailer.obavijesti_dodjela(db, r)
        except Exception: pass
    return RedirectResponse(f"/reklamacije/{id}", status_code=303)


@router.post("/{id}", response_class=RedirectResponse)
async def update(request: Request, id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return RedirectResponse("/reklamacije/lista", status_code=303)
    form  = await request.form()
    data  = _parse_rek(form)
    # Gate učinkovitosti (ISO 10.2): zatvaranje traži potvrđenu učinkovitost.
    if data["status"] == "ZATVORENO" and not r.ucinkovitost_provjerena:
        data["status"] = "RIJESENO"
        for k, v in data.items():
            setattr(r, k, v)
        db.commit()
        return RedirectResponse(
            f"/reklamacije/{id}?greska=Zatvaranje+nije+moguce+bez+potvrdene+ucinkovitosti+mjera",
            status_code=303)
    # Auto datum zatvaranja
    if data["status"] == "ZATVORENO" and not r.datum_zatvaranja:
        r.datum_zatvaranja = datetime.now()
    elif data["status"] not in ("ZATVORENO", "RIJESENO"):
        r.datum_zatvaranja = None
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    return RedirectResponse(f"/reklamacije/{id}", status_code=303)


@router.post("/{id}/ucinkovitost", response_class=RedirectResponse)
async def ucinkovitost(request: Request, id: int, db: Session = Depends(get_db)):
    r = db.get(Reklamacija, id)
    if not r:
        return RedirectResponse("/reklamacije/lista", status_code=303)
    form = await request.form()
    potvrdi = str(form.get("potvrdi", "")).strip() in ("1", "on", "true", "da")
    r.ucinkovitost_biljeska = str(form.get("ucinkovitost_biljeska", "")).strip() or None
    r.ucinkovitost_provjerena = potvrdi
    r.ucinkovitost_datum = date.today() if potvrdi else None
    db.commit()
    return RedirectResponse(f"/reklamacije/{id}", status_code=303)


@router.post("/{id}/obrisi", response_class=RedirectResponse)
async def obrisi(request: Request, id: int, db: Session = Depends(get_db)):
    r = db.get(Reklamacija, id)
    if r: db.delete(r); db.commit()
    return RedirectResponse("/reklamacije/lista", status_code=303)


# ─── CAPA ─────────────────────────────────────────────────────────────────────

def _render_capa(request, r, db):
    return templates.TemplateResponse(request, "reklamacije/_capa.html", {
        **_ctx(), "r": r,
        "capa_list": r.capa,
    })


@router.post("/{id}/capa/dodaj", response_class=HTMLResponse)
async def capa_dodaj(request: Request, id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return HTMLResponse("", status_code=404)
    form = await request.form()
    def s(k): return str(form.get(k,"")).strip() or None
    def d(k):
        v = str(form.get(k,"")).strip()
        try: return date.fromisoformat(v)
        except: return None
    c = CAPA(
        reklamacija_id=id,
        vrsta=str(form.get("vrsta","KOREKTIVNA")),
        opis_mjere=str(form.get("opis_mjere","")).strip(),
        odgovorna_osoba=str(form.get("odgovorna_osoba","")).strip(),
        rok_izvrsenja=d("rok_izvrsenja"),
        status=str(form.get("status","PLANIRANA")),
    )
    db.add(c); db.commit()
    db.refresh(r)
    r = _load(db, id)
    return _render_capa(request, r, db)


@router.post("/{id}/capa/{capa_id}/status", response_class=HTMLResponse)
async def capa_status(request: Request, id: int, capa_id: int, db: Session = Depends(get_db)):
    c = db.get(CAPA, capa_id)
    if c and c.reklamacija_id == id:
        form = await request.form()
        c.status = str(form.get("status", c.status))
        if c.status == "IZVRSENA" and not c.datum_izvrsenja:
            c.datum_izvrsenja = date.today()
        c.rezultat = str(form.get("rezultat","")).strip() or c.rezultat
        c.provjerio = str(form.get("provjerio","")).strip() or c.provjerio
        def d(k):
            v = str(form.get(k,"")).strip()
            try: return date.fromisoformat(v)
            except: return None
        if d("datum_provjere"): c.datum_provjere = d("datum_provjere")
        db.commit()
    r = _load(db, id)
    return _render_capa(request, r, db)


@router.post("/{id}/capa/{capa_id}/obrisi", response_class=HTMLResponse)
async def capa_obrisi(request: Request, id: int, capa_id: int, db: Session = Depends(get_db)):
    c = db.get(CAPA, capa_id)
    if c and c.reklamacija_id == id:
        db.delete(c); db.commit()
    r = _load(db, id)
    return _render_capa(request, r, db)


# ─── Troškovi / COPQ ──────────────────────────────────────────────────────────

def _render_troskovi(request, r):
    return templates.TemplateResponse(request, "reklamacije/_troskovi.html", {
        **_ctx(), "r": r, "troskovi": r.troskovi,
    })


def _fnum(form, k, default=0.0):
    v = str(form.get(k, "")).strip().replace(",", ".")
    try: return float(v)
    except: return default


@router.post("/{id}/trosak/dodaj", response_class=HTMLResponse)
async def trosak_dodaj(request: Request, id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return HTMLResponse("", status_code=404)
    form = await request.form()
    kolicina = _fnum(form, "kolicina", 1.0)
    jed_cijena = _fnum(form, "jed_cijena", 0.0)
    iznos_form = _fnum(form, "iznos", 0.0)
    # Ako je iznos upisan ručno koristi njega, inače izračunaj kolicina×cijena.
    iznos = iznos_form if iznos_form > 0 else round(kolicina * jed_cijena, 2)
    t = StavkaTroska(
        reklamacija_id=id,
        kategorija=str(form.get("kategorija", "OSTALO")),
        opis=str(form.get("opis", "")).strip() or None,
        kolicina=kolicina,
        jedinica=str(form.get("jedinica", "")).strip() or None,
        jed_cijena=jed_cijena,
        iznos=iznos,
        tko_snosi=str(form.get("tko_snosi", "INTERNO")),
        povrativo=str(form.get("povrativo", "")).strip() in ("1", "on", "true", "da"),
        stroj=str(form.get("stroj", "")).strip() or None,
    )
    db.add(t); db.commit()
    r = _load(db, id)
    return _render_troskovi(request, r)


@router.post("/{id}/trosak/{tid}/obrisi", response_class=HTMLResponse)
async def trosak_obrisi(request: Request, id: int, tid: int, db: Session = Depends(get_db)):
    t = db.get(StavkaTroska, tid)
    if t and t.reklamacija_id == id:
        db.delete(t); db.commit()
    r = _load(db, id)
    return _render_troskovi(request, r)


# ─── SCAR (reklamacije dobavljaču) ────────────────────────────────────────────

def _auto_scar_broj(db: Session) -> str:
    godina = datetime.now().year
    prefix = f"SCAR-{godina}-"
    count = db.scalar(select(func.count(SCAR.id)).where(SCAR.broj_scar.like(f"{prefix}%"))) or 0
    return f"{prefix}{count + 1:04d}"


def _render_scar(request, r):
    return templates.TemplateResponse(request, "reklamacije/_scar.html", {**_ctx(), "r": r})


@router.post("/{id}/scar/dodaj", response_class=HTMLResponse)
async def scar_dodaj(request: Request, id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return HTMLResponse("", status_code=404)
    form = await request.form()
    def s(k): return str(form.get(k, "")).strip() or None
    def d(k):
        v = str(form.get(k, "")).strip()
        try: return date.fromisoformat(v)
        except: return None
    sc = SCAR(
        reklamacija_id=id,
        broj_scar=_auto_scar_broj(db),
        dobavljac=str(form.get("dobavljac", "")).strip() or "Nepoznat dobavljač",
        status=str(form.get("status", "OTVOREN")),
        lot_sarza=s("lot_sarza"),
        broj_primke=s("broj_primke"),
        broj_narudzbe=s("broj_narudzbe"),
        kolicina=_fnum(form, "kolicina", 0.0) or None,
        jedinica=s("jedinica"),
        rok_odgovora=d("rok_odgovora"),
        datum_slanja=d("datum_slanja"),
        opis_zahtjeva=s("opis_zahtjeva"),
        iznos_reklamiran=_fnum(form, "iznos_reklamiran", 0.0),
    )
    db.add(sc); db.commit()
    r = _load(db, id)
    return _render_scar(request, r)


@router.post("/{id}/scar/{sid}/uredi", response_class=HTMLResponse)
async def scar_uredi(request: Request, id: int, sid: int, db: Session = Depends(get_db)):
    sc = db.get(SCAR, sid)
    if sc and sc.reklamacija_id == id:
        form = await request.form()
        def s(k, cur): return str(form.get(k, "")).strip() or cur
        def d(k, cur):
            v = str(form.get(k, "")).strip()
            if not v: return cur
            try: return date.fromisoformat(v)
            except: return cur
        sc.status = str(form.get("status", sc.status))
        sc.rjesenje = str(form.get("rjesenje", "")).strip() or None
        sc.dobavljac = s("dobavljac", sc.dobavljac)
        sc.lot_sarza = s("lot_sarza", sc.lot_sarza)
        sc.broj_primke = s("broj_primke", sc.broj_primke)
        sc.broj_narudzbe = s("broj_narudzbe", sc.broj_narudzbe)
        sc.broj_debit_note = s("broj_debit_note", sc.broj_debit_note)
        sc.rok_odgovora = d("rok_odgovora", sc.rok_odgovora)
        sc.datum_slanja = d("datum_slanja", sc.datum_slanja)
        sc.datum_odgovora = d("datum_odgovora", sc.datum_odgovora)
        sc.opis_zahtjeva = str(form.get("opis_zahtjeva", "")).strip() or None
        sc.odgovor_dobavljaca = str(form.get("odgovor_dobavljaca", "")).strip() or None
        sc.napomena = str(form.get("napomena", "")).strip() or None
        sc.iznos_reklamiran = _fnum(form, "iznos_reklamiran", sc.iznos_reklamiran)
        sc.iznos_priznat = _fnum(form, "iznos_priznat", sc.iznos_priznat)
        if "kolicina" in form:
            sc.kolicina = _fnum(form, "kolicina", 0.0) or None
        sc.jedinica = str(form.get("jedinica", "")).strip() or sc.jedinica
        # auto datum odgovora kad status pređe u odgovor/zatvoren
        if sc.status in ("ODGOVOR_PRIMLJEN", "ZATVOREN") and not sc.datum_odgovora:
            sc.datum_odgovora = date.today()
        db.commit()
    r = _load(db, id)
    return _render_scar(request, r)


@router.post("/{id}/scar/{sid}/obrisi", response_class=HTMLResponse)
async def scar_obrisi(request: Request, id: int, sid: int, db: Session = Depends(get_db)):
    sc = db.get(SCAR, sid)
    if sc and sc.reklamacija_id == id:
        db.delete(sc); db.commit()
    r = _load(db, id)
    return _render_scar(request, r)


# ─── PDF / Excel ──────────────────────────────────────────────────────────────

@router.get("/{id}/pdf")
def pdf(id: int, db: Session = Depends(get_db)):
    r = _load(db, id)
    if not r: return HTMLResponse("Nije pronađeno.", status_code=404)
    buf = generiraj_pdf(r)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Reklamacija_{r.broj_predmeta}.pdf"'})


@router.get("/excel/izvoz")
def excel(db: Session = Depends(get_db), status: str = "", vrsta: str = ""):
    conds = []
    if status: conds.append(Reklamacija.status == status)
    if vrsta:  conds.append(Reklamacija.vrsta == vrsta)
    rows = db.scalars(
        select(Reklamacija).where(*conds)
        .options(selectinload(Reklamacija.capa))
        .order_by(Reklamacija.datum_prijave.desc())
    ).all()
    buf  = generiraj_excel(rows)
    naziv = f"Reklamacije_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{naziv}"'})


# ─── Privici (slike/dokumenti) ────────────────────────────────────────────────

def _privici_partial(request: Request, db: Session, rek_id: int, greske=None):
    r = _load(db, rek_id)
    return templates.TemplateResponse(request, "reklamacije/_privici.html",
                                      {"r": r, "greske": greske or []})


@router.post("/{id}/privitak", response_class=HTMLResponse)
async def privitak_upload(request: Request, id: int,
                          datoteke: list[UploadFile] = File(default=[]),
                          db: Session = Depends(get_db)):
    if db.get(Reklamacija, id) is None:
        return PlainTextResponse("Nije pronađeno.", status_code=404)
    greske = []
    for f in datoteke:
        if not f or not f.filename:
            continue
        rez = pr.spremi_datoteku(id, f.filename, await f.read())
        if isinstance(rez, str):
            greske.append(f"{f.filename}: {rez}")
        else:
            db.add(Privitak(**rez))
    db.commit()
    return _privici_partial(request, db, id, greske)


@router.get("/{id}/privitak/{pid}")
def privitak_download(id: int, pid: int, db: Session = Depends(get_db)):
    p = db.get(Privitak, pid)
    if p is None or p.reklamacija_id != id:
        return PlainTextResponse("Nije pronađeno.", status_code=404)
    fp = pr.putanja(p)
    if not fp.exists():
        return PlainTextResponse("Datoteka nedostaje na disku.", status_code=404)
    return FileResponse(fp, filename=p.original_name,
                        media_type="application/octet-stream",
                        headers={"X-Content-Type-Options": "nosniff"})


@router.get("/{id}/privitak/{pid}/thumb")
def privitak_thumb(id: int, pid: int, db: Session = Depends(get_db)):
    p = db.get(Privitak, pid)
    if p is None or p.reklamacija_id != id or not p.ima_thumb:
        return PlainTextResponse("Nema sličice.", status_code=404)
    tp = pr.thumb_putanja(p)
    if not tp.exists():
        return PlainTextResponse("Nema sličice.", status_code=404)
    return FileResponse(tp, media_type="image/jpeg",
                        headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{id}/privitak/{pid}/obrisi", response_class=HTMLResponse)
def privitak_obrisi(request: Request, id: int, pid: int, db: Session = Depends(get_db)):
    p = db.get(Privitak, pid)
    if p and p.reklamacija_id == id:
        pr.obrisi_datoteke(p)
        db.delete(p)
        db.commit()
    return _privici_partial(request, db, id)
