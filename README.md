# Reklamacije / QMS (samostalni app)

Samostalna verzija modula za **reklamacije / upravljanje kvalitetom (QMS)** — izdvojeno iz
ERP/MES/WMS sustava. Isti kod (`app/modules/reklamacije`), ali vrti se zasebno: vlastita
baza, server i izbornik.

## Funkcionalnost
- **Reklamacije** — evidencija nesukladnosti/reklamacija (prijava, status, prioritet, vrsta,
  kupac/dobavljač, opis, analiza uzroka 5×zašto).
- **CAPA** — korektivne i preventivne mjere (vrsta, odgovorna osoba, rok, status, provjera).
- **PDF** — ispis zapisnika o nesukladnosti (`/reklamacije/{id}/pdf`).
- **Excel izvoz** — svih reklamacija + CAPA mjera (`/reklamacije/excel/izvoz`).
- Dashboard s metrikama + lista s pretragom (HTMX).

## Pokretanje
```bat
run.bat          REM lokalno (http://localhost:8601)
dev-wifi.bat     REM dostupno na LAN-u (ispiše mrežni URL za drugo računalo)
```
Prvi put `run.bat` sam napravi `.venv`, instalira `requirements.txt` i digne server.

## Priprema za DRUGO RAČUNALO
1. Na drugom računalu instaliraj **Python 3** (python.org) — pri instalaciji uključi
   **„Add Python to PATH"**.
2. Kopiraj cijeli folder **`Reklamacije-app`** na to računalo (USB / mreža).
   - NE moraš kopirati `.venv` (stvara se sam); dovoljni su `app/`, `requirements.txt`, `*.bat`.
3. Dvoklik na **`run.bat`** — prvi put instalira ovisnosti (~1 min) i digne app.
4. Otvori **http://localhost:8601** u pregledniku.
5. Za pristup s drugog uređaja na istoj mreži: pokreni **`dev-wifi.bat`** i upiši ispisani
   `http://<IP>:8601` (po potrebi otvori firewall — naredba je ispisana).

> Podaci se spremaju u `reklamacije.db` (SQLite, u folderu appa). PDF koristi Arial
> (Windows fontovi); fallback Helvetica ako fali.

## Backup baze
- **Automatski:** na svakom pokretanju app napravi kopiju u `backup\reklamacije_<datum_vrijeme>.db`
  (čuva zadnjih 20).
- **Ručno (bez pokretanja):** dvoklik na **`backup.bat`** → kopija u `backup\`.
- **Iz appa:** sidebar → **⤓ Backup baze (.db)** preuzme trenutnu bazu (i s drugog uređaja).
- Glavna baza je `reklamacije.db` — pri selidbi na drugo računalo **kopiraj tu datoteku** (i/ili `backup\`).

> **Napomena (sigurnost):** app je dostupan svima na mreži (`0.0.0.0`) i **nema prijavu** —
> bilo tko na WiFi-u može čitati/uređivati/brisati. Za interni siguran rad reci pa dodam prijavu
> ili ograničim na samo ovo računalo (`localhost`).

## Struktura
```
app/
  main.py                 # FastAPI, create_all (reklamacija, capa), root -> /reklamacije
  core/                   # config + database (vlastiti, samostalni)
  modules/reklamacije/    # ISTI kod kao u ERP-u (models/routes/utils) — NETAKNUT
  templates/
    base.html             # QMS-only izbornik
    reklamacije/          # ISTI templati kao u ERP-u
```
