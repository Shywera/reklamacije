"""Autentikacija i autorizacija — čiste funkcije (bez DB/route ovisnosti).

- Lozinke: bcrypt (nikad plain/SHA).
- Dozvole: granularne, po korisniku (CSV ključeva u `User.dozvole`). `admin` = sve.
- `required_perm(method, path)` mapira zahtjev na potrebnu dozvolu (middleware).
- `akcija_label(method, path)` daje čitljiv naziv akcije za audit log.
- `predmet_id_iz(path)` izvlači id reklamacije iz putanje (za timeline).
"""
from __future__ import annotations

import re

# ── Katalog dozvola (ključ -> opis za UI) ───────────────────────────────────────
PERMISSIONS: dict[str, str] = {
    "unos":  "Unos i uređivanje reklamacija (CAPA, troškovi, SCAR, privici)",
    "admin": "Administracija (korisnici, log, backup)",
}

# Pregled (dashboard, lista, detalj, PDF, Excel) — ima svaki prijavljeni korisnik.

_MUTACIJE = ("POST", "PUT", "DELETE", "PATCH")

# Putanje dostupne BEZ prijave.
PUBLIC_PATHS = {"/login", "/logout", "/api-docs", "/openapi.json", "/favicon.ico"}


def perms_set(dozvole: str | None) -> set[str]:
    return {p for p in (dozvole or "").split(",") if p}


def has_perm(dozvole: str | None, perm: str) -> bool:
    p = perms_set(dozvole)
    return "admin" in p or perm in p


def required_perm(method: str, path: str) -> str | None:
    """Koja je dozvola potrebna za dani zahtjev (ili None = dovoljna prijava)."""
    if path == "/admin" or path.startswith("/admin/") or path == "/backup":
        return "admin"
    if method in _MUTACIJE and (path == "/reklamacije" or path.startswith("/reklamacije/")):
        return "unos"
    return None


def should_audit(method: str, path: str, status: int) -> bool:
    if not (path == "/reklamacije" or path.startswith("/reklamacije/")):
        return False
    return method in _MUTACIJE and status < 400


_PREDMET_RE = re.compile(r"^/reklamacije/(\d+)(?:/|$)")


def predmet_id_iz(path: str) -> int | None:
    m = _PREDMET_RE.match(path)
    return int(m.group(1)) if m else None


# ── Lozinke (bcrypt) ────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── Audit oznake ────────────────────────────────────────────────────────────────

_AKCIJE: list[tuple[str, str]] = [
    (r"^/login$",                                 "Prijava"),
    (r"^/logout$",                                "Odjava"),
    (r"^/reklamacije/nova$",                      "Kreirana reklamacija"),
    (r"^/reklamacije/\d+$",                       "Uređena reklamacija"),
    (r"^/reklamacije/\d+/obrisi$",                "Obrisana reklamacija"),
    (r"^/reklamacije/\d+/capa/dodaj$",            "Dodana CAPA mjera"),
    (r"^/reklamacije/\d+/capa/\d+/status$",       "Promjena statusa CAPA"),
    (r"^/reklamacije/\d+/capa/\d+/obrisi$",       "Obrisana CAPA mjera"),
    (r"^/reklamacije/\d+/trosak/dodaj$",          "Dodan trošak (COPQ)"),
    (r"^/reklamacije/\d+/trosak/\d+/obrisi$",     "Obrisan trošak"),
    (r"^/reklamacije/\d+/scar/dodaj$",            "Pokrenut SCAR (dobavljač)"),
    (r"^/reklamacije/\d+/scar/\d+/uredi$",        "Uređen SCAR"),
    (r"^/reklamacije/\d+/scar/\d+/obrisi$",       "Obrisan SCAR"),
    (r"^/reklamacije/\d+/privitak$",              "Dodan privitak"),
    (r"^/reklamacije/\d+/privitak/\d+/obrisi$",   "Obrisan privitak"),
    (r"^/reklamacije/\d+/dodijeli$",              "Dodjela zaduženja"),
    (r"^/admin/korisnici$",                       "Kreiranje korisnika"),
    (r"^/admin/korisnici/\d+/uredi$",             "Uređivanje korisnika"),
    (r"^/admin/korisnici/\d+/lozinka$",           "Promjena lozinke"),
    (r"^/admin/korisnici/\d+/obrisi$",            "Brisanje korisnika"),
]


def akcija_label(method: str, path: str) -> str:
    for pat, lbl in _AKCIJE:
        if re.match(pat, path):
            return lbl
    return f"{method} {path}"
