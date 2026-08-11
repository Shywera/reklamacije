"""Shema baze: create_all + idempotentni ALTER za stupce dodane naknadno.

`create_all` ne mijenja postojeće tablice, pa novi stupci na starim tablicama
idu kroz `ALTER TABLE` uz provjeru postoji li stupac već.

Zove se iz `app/main.py` pri pokretanju servera, ali i iz alata koji rade nad
bazom bez servera (npr. `uvoz_nesukladnosti.py`) — zato je izdvojeno ovdje.
"""
from __future__ import annotations

from sqlalchemy import inspect as sa_inspect, text

from app.core.database import Base, engine

# (tablica, stupac, tip) — dodavati na kraj, nikad ne mijenjati postojeće retke.
NOVI_STUPCI = [
    ("reklamacija", "defekt_kategorija", "VARCHAR(20)"),
    ("reklamacija", "izvor", "VARCHAR(20)"),
    ("reklamacija", "tezina", "VARCHAR(20)"),
    ("reklamacija", "dodijeljeno_id", "INTEGER"),
    ("reklamacija", "dodijeljeno_ime", "VARCHAR(120)"),
    ("reklamacija", "ucinkovitost_provjerena", "BOOLEAN DEFAULT 0"),
    ("reklamacija", "ucinkovitost_datum", "DATE"),
    ("reklamacija", "ucinkovitost_biljeska", "TEXT"),
    ("reklamacija", "fmea_sev", "INTEGER"),
    ("reklamacija", "fmea_occ", "INTEGER"),
    ("reklamacija", "fmea_det", "INTEGER"),
    # Polja papirnatog obrasca „Nesukladnost" (uvoz arhive 2026)
    ("reklamacija", "izvorni_broj", "VARCHAR(30)"),
    ("reklamacija", "izvorna_mapa", "VARCHAR(255)"),
    ("reklamacija", "porijeklo", "VARCHAR(30)"),
    ("reklamacija", "porijeklo_napomena", "VARCHAR(200)"),
    ("reklamacija", "korekciju_proveo", "VARCHAR(120)"),
    ("reklamacija", "korekcija_datum", "DATE"),
    ("reklamacija", "uzrok_potvrdio", "VARCHAR(120)"),
    ("reklamacija", "potrebna_korektivna", "VARCHAR(2)"),
    ("reklamacija", "radnju_definirao", "VARCHAR(120)"),
    ("reklamacija", "sifra_materijala", "VARCHAR(60)"),
    ("reklamacija", "lot_sarza", "VARCHAR(120)"),
    ("reklamacija", "broj_primke", "VARCHAR(60)"),
    ("reklamacija", "direktor_potpis", "VARCHAR(120)"),
    ("reklamacija", "izvorni_zapis", "TEXT"),
    ("korisnik", "email", "VARCHAR(160)"),
]


def primijeni() -> None:
    """Napravi tablice koje fale i dodaj stupce koji fale. Sigurno je zvati više puta."""
    Base.metadata.create_all(bind=engine)
    inspektor = sa_inspect(engine)
    postojeci: dict[str, set[str]] = {}
    for tablica, stupac, tip in NOVI_STUPCI:
        if tablica not in postojeci:
            postojeci[tablica] = {c["name"] for c in inspektor.get_columns(tablica)}
        if stupac in postojeci[tablica]:
            continue
        with engine.begin() as veza:
            veza.execute(text(f"ALTER TABLE {tablica} ADD COLUMN {stupac} {tip}"))
        postojeci[tablica].add(stupac)
