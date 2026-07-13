# CLAUDE.md

Kontekst za Claude Code. Ovo je **jedini kontekst koji putuje između računala** kroz git —
Claudova lokalna memorija se NE sinkronizira. Na kraju sesije ažuriraj "Trenutno stanje" i
pokreni `spremi.bat`.

## Što je ovo
Samostalna **Reklamacije / QMS** web-aplikacija za tiskaru samoljepljivih etiketa —
upravljanje reklamacijama i nesukladnostima (interne / kupac / dobavljač), CAPA mjere,
troškovi nekvalitete (COPQ), reklamacije dobavljaču (SCAR), analitika. FastAPI +
SQLAlchemy 2.0 + SQLite + Jinja2 + HTMX + Alpine + Tailwind (CDN). Izdvojeno iz većeg
ERP/MES/WMS projekta (`app/modules/reklamacije` kopiran uz `app.` namespace).

## Pokretanje i alati (Windows, .bat)
- `run.bat` — lokalno, port **8601**; prvi put gradi `.venv` + generira `.env`.
- `dev-wifi.bat` — na `0.0.0.0` + mrežni URL. `backup.bat` — ručni backup baze.
- `update.bat` — `git pull` + osvježi deps. `spremi.bat` — add+commit+pull+push.
- `provjeri-rokove.bat` / `provjeri_rokove.py` — provjera prekoračenih rokova + email
  (Windows Task Scheduler; NEMA pozadinskog schedulera).
- Ručni test: `.venv\Scripts\python.exe` + FastAPI `TestClient` (`httpx` je u venvu lokalno,
  NIJE u `requirements.txt`).

## Arhitektura
```
app/main.py                FastAPI: create_all + idempotentne ALTER migracije, _seed_admin,
                           auth_audit middleware, SessionMiddleware, /backup (admin)
app/core/                  config (pydantic-settings, .env) + database + backup
app/modules/reklamacije/   modeli (Reklamacija, CAPA, Privitak, StavkaTroska, SCAR), routes,
                           privici (upload), utils (PDF/Excel), templates
app/modules/auth/          security (dozvole/bcrypt) + models (korisnik/audit_log) + routes
app/modules/notifikacije/  mailer (SMTP, dry-run bez konfiguracije) + admin routes
app/templates/             base.html (sidebar) + reklamacije/ + auth/ + notifikacije/
```

## Funkcionalnost (9 faza — SVE GOTOVO, 2026-07)
1. **Privici** — upload slika/dokumenata (disk `uploads/`, metapodaci u bazi, Pillow thumb).
2. **Taksonomija defekta** — `defekt_kategorija` A–J + `izvor` + `tezina`.
3. **Troškovi/COPQ** — `StavkaTroska` (1→N), rollup ukupno/neto/po-snosiocu, KPI.
4. **SCAR** — reklamacija dobavljaču (auto-broj, status, rješenje, naplata, scorecard).
5. **Auth** — prijava + dozvole (`unos`/`admin`) + audit log (bcrypt, SessionMiddleware).
6. **Audit timeline + dodjela** — `dodijeljeno_id`, timeline na detalju, "Moje reklamacije".
7. **Notifikacije** — email nova/dodjela/prekoračeni rokovi + eskalacija (>7d).
8. **Analitika** — Chart.js: Pareto, trend, on-time, recurrence, COPQ, top dobavljači.
9. **Zrelost** — gate učinkovitosti prije zatvaranja (ISO 10.2), FMEA/RPN, supplier scorecard.

## Konvencije i zamke (naučeno)
- **Migracije:** `create_all` + idempotentni `ALTER TABLE` preko `sa_inspect(engine).get_columns()`.
  Nove tablice pokriva create_all; novi stupci na postojećim tablicama trebaju ALTER (vidi `main.py`).
- **Route ordering:** statičke rute (`/analitika`, `/dobavljaci`, `/nova`, `/lista`) MORAJU biti
  registrirane PRIJE `/{id}` (inače ih int-konverzija proguta).
- **HTMX partiali** koji se uključuju u `detail.html` moraju čitati iz `r.` (npr. `r.capa`,
  `r.troskovi`) jer include NE prosljeđuje zasebne varijable.
- **.bat MORA biti CRLF** (Write daje LF → cmd se zatvori). Konverzija:
  `awk '{sub(/\r$/,""); printf "%s\r\n",$0}'`; provjera `od -c`. Zagrade u `echo` unutar `if()`
  → koristi `goto`.
- **Python 3.14 venv nije prenosiv** → `run.bat` self-healing (rebuild ako `import` padne).
- **pydantic-settings:** `.env` varijabla radi samo ako postoji polje u `Settings`
  (secret_key, admin_password, notif_enabled, smtp_*).
- **Portovi:** ERP=8000, WMS-app=8600, **Reklamacije-app=8601**.
- **NIKAD ne commitati:** `.env`, `*.db`, `.venv`, `uploads/`, `backup/`, `__pycache__`.

## Email (opcionalno)
Ne šalje se dok se u `.env` ne postavi `NOTIF_ENABLED=true` + `SMTP_HOST/USER/PASSWORD` +
`NOTIF_FROM`. Bez toga sve radi (dry-run). Korisnici trebaju upisan `email` za obavijesti.

## Sinkronizacija kuća/posao
Sinkronizira se **samo kod + CLAUDE.md**. Baza (`reklamacije.db`), `.env` i `uploads/` su
lokalni po računalu (svako ima svoje podatke, admin/admin na praznoj bazi). Tijek:
`spremi.bat` na jednom → `update.bat` na drugom.

## Trenutno stanje (ažuriraj na kraju sesije)
- 2026-07: svih 9 faza QMS-a gotovo i testirano. Na GitHubu (`Shywera/reklamacije`).
- Sljedeće / ideje: puni 8D wizard, šifrarnik veza (kupac/dobavljač/materijal kao FK) — namjerno
  odgođeno. (dopuni po potrebi)
