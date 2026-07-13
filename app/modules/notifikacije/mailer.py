"""Email notifikacije (SMTP) — best-effort, nikad ne ruši zahtjev.

Slanje je omogućeno samo ako je `settings.notif_enabled` i postavljen SMTP host.
Inače je sve "dry-run": funkcije i dalje sastave i vrate PLAN poruka (za pregled/test),
ali `posalji_email` ne šalje ništa. Rokovi se provjeravaju na zahtjev (ruta ili
`provjeri-rokove.bat` preko Task Schedulera) — nema pozadinskog schedulera.
"""
from __future__ import annotations

import smtplib
from datetime import date
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.modules.auth.models import User
from app.modules.reklamacije.models import CAPA, Reklamacija


def posalji_email(to: str | None, subject: str, body: str) -> tuple[bool, str]:
    """Pošalji jedan email. Vraća (uspjeh, poruka). Best-effort: hvata sve iznimke."""
    if not to:
        return False, "nema primatelja"
    if not settings.notif_enabled or not settings.smtp_host:
        return False, "slanje onemogućeno (notif_enabled/SMTP nije postavljen)"
    try:
        msg = EmailMessage()
        msg["From"] = settings.notif_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            if settings.smtp_tls:
                s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True, "poslano"
    except Exception as e:  # noqa: BLE001 — notifikacija ne smije srušiti zahtjev
        return False, f"greška: {e}"


def _email_zaduzenog(db: Session, rek: Reklamacija) -> str | None:
    if rek.dodijeljeno_id:
        u = db.get(User, rek.dodijeljeno_id)
        if u and u.email:
            return u.email
    return settings.notif_default or None


def _admin_emailovi(db: Session) -> list[str]:
    users = db.scalars(select(User).where(User.aktivan.is_(True))).all()
    out = [u.email for u in users if u.email and "admin" in (u.dozvole or "").split(",")]
    if not out and settings.notif_default:
        out = [settings.notif_default]
    return out


def obavijesti_nova(db: Session, rek: Reklamacija) -> list[dict]:
    """Nova reklamacija -> obavijest administratorima / voditelju kvalitete."""
    subject = f"[QMS] Nova reklamacija {rek.broj_predmeta}: {rek.naslov}"
    body = (
        f"Prijavljena je nova reklamacija.\n\n"
        f"Broj: {rek.broj_predmeta}\nNaslov: {rek.naslov}\n"
        f"Vrsta: {rek.vrsta_display}\nPrioritet: {rek.prioritet_display}\n"
        f"Prijavitelj: {rek.prijavitelj}\n"
        f"Kupac/Dobavljač: {rek.kupac_dobavljac or '—'}\n\n"
        f"Opis:\n{rek.opis or '—'}\n"
    )
    plan = []
    for to in _admin_emailovi(db):
        ok, info = posalji_email(to, subject, body)
        plan.append({"to": to, "subject": subject, "ok": ok, "info": info})
    return plan


def obavijesti_dodjela(db: Session, rek: Reklamacija) -> list[dict]:
    """Reklamacija dodijeljena korisniku -> obavijest tom korisniku."""
    if not rek.dodijeljeno_id:
        return []
    u = db.get(User, rek.dodijeljeno_id)
    to = u.email if u else None
    subject = f"[QMS] Dodijeljena ti je reklamacija {rek.broj_predmeta}"
    body = (
        f"Dodijeljena ti je reklamacija na rješavanje.\n\n"
        f"Broj: {rek.broj_predmeta}\nNaslov: {rek.naslov}\n"
        f"Prioritet: {rek.prioritet_display}\n"
        f"Rok rješavanja: {rek.rok_rjesavanja.isoformat() if rek.rok_rjesavanja else '—'}\n"
    )
    ok, info = posalji_email(to, subject, body)
    return [{"to": to, "subject": subject, "ok": ok, "info": info}]


def provjeri_rokove(db: Session) -> dict:
    """Skenira prekoračene rokove (reklamacije + CAPA), šalje podsjetnike/eskalaciju.
    Vraća sažetak {rek_prekoraceno, capa_prekoraceno, plan:[...]} bez obzira šalje li se."""
    danas = date.today()
    plan: list[dict] = []

    # 1) Prekoračene reklamacije (nezatvorene)
    rek_over = db.scalars(
        select(Reklamacija)
        .where(Reklamacija.rok_rjesavanja.is_not(None))
        .where(Reklamacija.rok_rjesavanja < danas)
        .where(Reklamacija.status.notin_(["RIJESENO", "ZATVORENO"]))
    ).all()
    for rek in rek_over:
        to = _email_zaduzenog(db, rek)
        dana = (danas - rek.rok_rjesavanja).days
        subject = f"[QMS] PODSJETNIK: rok reklamacije {rek.broj_predmeta} prekoračen ({dana} d)"
        body = (f"Rok rješavanja reklamacije {rek.broj_predmeta} ({rek.naslov}) "
                f"prekoračen je za {dana} dan(a).\nRok je bio: {rek.rok_rjesavanja.isoformat()}.\n"
                f"Status: {rek.status_display}. Molimo poduzmi radnje.\n")
        ok, info = posalji_email(to, subject, body)
        plan.append({"tip": "reklamacija", "broj": rek.broj_predmeta, "dana": dana,
                     "to": to, "ok": ok, "info": info})

    # 2) Prekoračene CAPA mjere (neizvršene)
    capa_over = db.scalars(
        select(CAPA).options(selectinload(CAPA.reklamacija))
        .where(CAPA.rok_izvrsenja.is_not(None))
        .where(CAPA.rok_izvrsenja < danas)
        .where(CAPA.status != "IZVRSENA")
    ).all()
    for c in capa_over:
        rek = c.reklamacija
        to = _email_zaduzenog(db, rek) if rek else (settings.notif_default or None)
        dana = (danas - c.rok_izvrsenja).days
        # Eskalacija: ako je jako kasno (>7 d), dodaj administratore u kopiju
        primatelji = [to] if to else []
        if dana > 7:
            primatelji += [e for e in _admin_emailovi(db) if e != to]
        subject = (f"[QMS] {'ESKALACIJA' if dana > 7 else 'PODSJETNIK'}: CAPA mjera prekoračena "
                   f"({dana} d) — {rek.broj_predmeta if rek else '?'}")
        body = (f"CAPA mjera '{c.opis_mjere}' (odg. {c.odgovorna_osoba}) prekoračila je rok za "
                f"{dana} dan(a).\nRok je bio: {c.rok_izvrsenja.isoformat()}.\n"
                f"Reklamacija: {rek.broj_predmeta if rek else '—'}.\n")
        for p in (primatelji or [None]):
            ok, info = posalji_email(p, subject, body)
            plan.append({"tip": "capa", "broj": rek.broj_predmeta if rek else "—", "dana": dana,
                         "eskalacija": dana > 7, "to": p, "ok": ok, "info": info})

    return {
        "rek_prekoraceno": len(rek_over),
        "capa_prekoraceno": len(capa_over),
        "poslano": sum(1 for p in plan if p["ok"]),
        "plan": plan,
        "omoguceno": bool(settings.notif_enabled and settings.smtp_host),
    }
