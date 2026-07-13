"""Samostalni Reklamacije / QMS app — s prijavom, granularnim dozvolama i audit logom.

Isti modul kao u ERP-u (`app.modules.reklamacije`), ali vrti se zasebno: vlastita
SQLite baza (`reklamacije.db`), vlastiti `base.html`. Prijava/dozvole/audit dodani
su kroz `auth` modul + middleware:
  * SessionMiddleware (potpisani httpOnly cookie) drži `user_id`.
  * `auth_audit` middleware: traži prijavu, provjerava dozvolu po putanji, te
    bilježi svaku mutaciju (POST/PUT/DELETE) u `audit_log` (tko/kad/što/predmet).
Tablice se kreiraju na startu (`create_all`); na svakom startu radi se auto-backup.

Pokretanje:  .venv\\Scripts\\uvicorn app.main:app   (ili run.bat / dev-wifi.bat)
"""
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import (FileResponse, PlainTextResponse, RedirectResponse,
                               Response)
from sqlalchemy import func, inspect as sa_inspect, select, text
from starlette.middleware.sessions import SessionMiddleware

from app.core.backup import auto_backup, db_putanja
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.modules.auth import models as auth_models  # noqa: F401 — registrira korisnik/audit_log
from app.modules.auth import security as sec
from app.modules.auth.models import AuditLog, User
from app.modules.auth.routes import router as auth_router, templates as auth_templates
from app.modules.notifikacije.routes import router as notifikacije_router
from app.modules.reklamacije import models  # noqa: F401 — registrira reklamacija/capa/…
from app.modules.reklamacije.routes import router as reklamacije_router

auto_backup()                          # backup postojeće baze prije starta
Base.metadata.create_all(bind=engine)

# Dodaj nove stupce na postojeću bazu ako fale (create_all ne mijenja postojeće tablice).
_rek_cols = {c["name"] for c in sa_inspect(engine).get_columns("reklamacija")}
_dodaj = [("defekt_kategorija", "VARCHAR(20)"), ("izvor", "VARCHAR(20)"), ("tezina", "VARCHAR(20)"),
          ("dodijeljeno_id", "INTEGER"), ("dodijeljeno_ime", "VARCHAR(120)"),
          ("ucinkovitost_provjerena", "BOOLEAN DEFAULT 0"), ("ucinkovitost_datum", "DATE"),
          ("ucinkovitost_biljeska", "TEXT"),
          ("fmea_sev", "INTEGER"), ("fmea_occ", "INTEGER"), ("fmea_det", "INTEGER")]
for _c, _tip in _dodaj:
    if _c not in _rek_cols:
        with engine.begin() as _conn:
            _conn.execute(text(f"ALTER TABLE reklamacija ADD COLUMN {_c} {_tip}"))

# Korisnik.email (Faza 7)
if "email" not in {c["name"] for c in sa_inspect(engine).get_columns("korisnik")}:
    with engine.begin() as _conn:
        _conn.execute(text("ALTER TABLE korisnik ADD COLUMN email VARCHAR(160)"))


def _seed_admin() -> None:
    """Ako nema nijednog korisnika, kreiraj početnog admina (lozinka iz ADMIN_PASSWORD)."""
    db = SessionLocal()
    try:
        if (db.scalar(select(func.count(User.id))) or 0) == 0:
            pw = settings.admin_password
            db.add(User(username="admin", ime="Administrator",
                        lozinka_hash=sec.hash_password(pw), dozvole="admin", aktivan=True))
            db.commit()
            print(f"[QMS] Kreiran pocetni admin -> korisnik: admin  lozinka: {pw}  "
                  f"(PROMIJENI nakon prve prijave!)")
    finally:
        db.close()


_seed_admin()

app = FastAPI(title="Reklamacije / QMS", docs_url="/api-docs", redoc_url=None)


@app.middleware("http")
async def auth_audit(request: Request, call_next):
    path = request.url.path
    if path in sec.PUBLIC_PATHS or path.startswith("/api-docs"):
        return await call_next(request)

    db = SessionLocal()
    try:
        uid = request.session.get("user_id")
        user = db.get(User, uid) if uid else None
        if user is not None and not user.aktivan:
            user = None
        request.state.user = user

        if user is None:
            if request.headers.get("HX-Request"):
                r = Response(status_code=401)
                r.headers["HX-Redirect"] = "/login"
                return r
            return RedirectResponse("/login", status_code=303)

        needed = sec.required_perm(request.method, path)
        if needed and not sec.has_perm(user.dozvole, needed):
            if request.headers.get("HX-Request"):
                return PlainTextResponse("Nemaš dozvolu za ovu radnju.", status_code=403)
            return auth_templates.TemplateResponse(
                request, "auth/403.html",
                {"perm": needed, "opis": sec.PERMISSIONS.get(needed, needed)},
                status_code=403)

        response = await call_next(request)

        if sec.should_audit(request.method, path, response.status_code):
            db.add(AuditLog(user_id=user.id, username=user.username, metoda=request.method,
                            putanja=path, akcija=sec.akcija_label(request.method, path),
                            predmet_id=sec.predmet_id_iz(path)))
            db.commit()
        return response
    finally:
        db.close()


# SessionMiddleware se dodaje ZADNJI -> vanjski sloj -> postavi request.session
# prije nego auth_audit pokuša čitati prijavu.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key,
                   same_site="lax", https_only=False)

app.include_router(auth_router)
app.include_router(notifikacije_router)
app.include_router(reklamacije_router)


@app.get("/backup", include_in_schema=False)
def backup(request: Request):
    """Preuzmi kopiju trenutne baze (samo administrator)."""
    u = getattr(request.state, "user", None)
    if not (u and sec.has_perm(u.dozvole, "admin")):
        return PlainTextResponse("Samo administrator.", status_code=403)
    p = db_putanja()
    if p is None or not p.exists():
        return PlainTextResponse("Baza ne postoji.", status_code=404)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(p, filename=f"{p.stem}_{stamp}{p.suffix}",
                        media_type="application/octet-stream")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/reklamacije")
