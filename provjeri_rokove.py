"""Provjera prekoračenih rokova (reklamacije + CAPA) i slanje podsjetnika/eskalacija.

Pokreće se ručno ili preko Windows Task Schedulera (vidi provjeri-rokove.bat).
Slanje e-pošte radi samo ako je u .env postavljeno NOTIF_ENABLED=true + SMTP_*.
Bez toga skripta samo ispiše koliko je rokova prekoračeno (dry-run).
"""
from app.core.database import SessionLocal
from app.modules.notifikacije import mailer


def main() -> None:
    db = SessionLocal()
    try:
        rez = mailer.provjeri_rokove(db)
    finally:
        db.close()
    print(f"Prekoracenih reklamacija: {rez['rek_prekoraceno']}")
    print(f"Prekoracenih CAPA mjera:  {rez['capa_prekoraceno']}")
    print(f"Poslano e-mailova:        {rez['poslano']}"
          f"{'' if rez['omoguceno'] else '  (slanje iskljuceno - dry run)'}")
    for p in rez["plan"]:
        print(f"  - {p['tip']:11} {p['broj']:14} {p['dana']}d -> {p.get('to') or '-'} : {p['info']}")


if __name__ == "__main__":
    main()
