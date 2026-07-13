# Reklamacije / QMS — Sustav upravljanja kvalitetom

Web aplikacija za vođenje reklamacija i nesukladnosti u proizvodnji, po načelima
ISO 9001 (t. 10.2): od prijave, preko analize uzroka i korektivnih mjera, do
provjere učinkovitosti prije zatvaranja.

## Mogućnosti

- **Reklamacije i nesukladnosti** — interne, kupaca i dobavljača; automatska numeracija,
  statusi, prioriteti, rokovi
- **Taksonomija defekata** — 10 kategorija (boja, pasovanje, štanca, materijal…),
  izvor defekta i težina → omogućuje Pareto analizu
- **CAPA mjere** — korektivne/preventivne mjere s rokovima, odgovornima i praćenjem
- **Troškovi nekvalitete (COPQ)** — stavke troška po kategoriji, tko snosi, nadoknadivi dio
- **SCAR** — reklamacije prema dobavljačima: rokovi odgovora, rješenja, naplata, scorecard
- **Privici** — slike i dokumenti uz reklamaciju (thumbnaili, kontrolirani tipovi)
- **Gate učinkovitosti** — zatvaranje moguće tek uz potvrđenu provjeru učinkovitosti mjera
- **FMEA/RPN** procjena rizika (S×O×D)
- **Analitika** — Pareto defekata, trend, on-time zatvaranje, recurrence, COPQ (Chart.js)
- **Prijava, dozvole, audit log, dodjela zaduženja, email podsjetnici** za prekoračene rokove
- **PDF i Excel izvještaji**, automatski backup baze

## Tehnologije

FastAPI · SQLAlchemy 2.0 · SQLite · Jinja2 · HTMX · Alpine.js · Tailwind CSS · reportlab · Chart.js

## Brzi start (Windows)

1. Instalirajte [Python 3](https://python.org) (*Add Python to PATH*)
2. Pokrenite **`run.bat`** — prvi put izgradi okruženje i generira `.env`
3. Otvorite **http://localhost:8601** — prijava `admin` / `admin` (odmah promijenite lozinku)

## Konfiguracija (`.env`)

| Varijabla | Opis |
|---|---|
| `ADMIN_PASSWORD` | lozinka početnog administratora |
| `FIRMA_NAZIV` | naziv tvrtke za PDF zaglavlja (zadano demo) |
| `NOTIF_ENABLED` + `SMTP_*` | email obavijesti (bez toga sustav radi, samo ne šalje) |

Dnevna provjera rokova: `provjeri-rokove.bat` (Windows Task Scheduler).

## Povezani projekti

[ERP/MES/WMS](https://github.com/Shywera/erp) · [WMS](https://github.com/Shywera/wms) ·
[Ponude](https://github.com/Shywera/Ponude) · [Alati](https://github.com/Shywera/tools)
