from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reklamacija(Base):
    __tablename__ = "reklamacija"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broj_predmeta: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    vrsta: Mapped[str] = mapped_column(String(20), default="INTERNA", index=True)
    status: Mapped[str] = mapped_column(String(20), default="NOVO", index=True)
    prioritet: Mapped[str] = mapped_column(String(10), default="SREDNJI", index=True)
    kategorija: Mapped[str | None] = mapped_column(String(10))

    # Klasifikacija defekta (Faza 2)
    defekt_kategorija: Mapped[str | None] = mapped_column(String(20), index=True)  # A..J
    izvor: Mapped[str | None] = mapped_column(String(20), index=True)              # DOBAVLJAC/INTERNO/KUPAC
    tezina: Mapped[str | None] = mapped_column(String(20), index=True)             # KRITICAN/VELIKI/MALI

    naslov: Mapped[str] = mapped_column(String(200))
    opis: Mapped[str] = mapped_column(Text)
    prijavitelj: Mapped[str] = mapped_column(String(100))

    kupac_dobavljac: Mapped[str | None] = mapped_column(String(150))
    referentni_broj: Mapped[str | None] = mapped_column(String(100))
    naziv_proizvoda: Mapped[str | None] = mapped_column(String(200))
    broj_radnog_naloga: Mapped[str | None] = mapped_column(String(100))
    stroj: Mapped[str | None] = mapped_column(String(100))
    osoblje: Mapped[str | None] = mapped_column(String(200))

    # Dodjela zaduženja (Faza 6) — soft veza na korisnik.id + snapshot imena za prikaz
    dodijeljeno_id: Mapped[int | None] = mapped_column(Integer, index=True)
    dodijeljeno_ime: Mapped[str | None] = mapped_column(String(120))

    datum_prijave: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    datum_azuriranja: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    datum_zatvaranja: Mapped[datetime | None] = mapped_column(DateTime)
    rok_rjesavanja: Mapped[date | None] = mapped_column(Date)

    korekcija: Mapped[str | None] = mapped_column(Text)
    analiza_uzroka: Mapped[str | None] = mapped_column(Text)
    uzrok_kategorija: Mapped[str | None] = mapped_column(String(100))
    napomena: Mapped[str | None] = mapped_column(Text)

    vezana_nesukladnost: Mapped[str | None] = mapped_column(String(50))
    promjene_sustava: Mapped[str | None] = mapped_column(String(2))
    broj_promjene: Mapped[str | None] = mapped_column(String(50))

    # ── Polja papirnatog obrasca „Nesukladnost" (OB) ───────────────────────
    # Uvedeno kod uvoza arhive 2026; obrazac ima korake koje QMS prije nije imao.
    izvorni_broj: Mapped[str | None] = mapped_column(String(30))        # broj kako je upisan u obrascu
    izvorna_mapa: Mapped[str | None] = mapped_column(String(255))       # mapa u arhivi na disku
    porijeklo: Mapped[str | None] = mapped_column(String(30), index=True)
    porijeklo_napomena: Mapped[str | None] = mapped_column(String(200))
    korekciju_proveo: Mapped[str | None] = mapped_column(String(120))
    korekcija_datum: Mapped[date | None] = mapped_column(Date)
    uzrok_potvrdio: Mapped[str | None] = mapped_column(String(120))
    potrebna_korektivna: Mapped[str | None] = mapped_column(String(2))  # DA/NE iz obrasca
    radnju_definirao: Mapped[str | None] = mapped_column(String(120))
    sifra_materijala: Mapped[str | None] = mapped_column(String(60))
    lot_sarza: Mapped[str | None] = mapped_column(String(120))
    broj_primke: Mapped[str | None] = mapped_column(String(60))
    direktor_potpis: Mapped[str | None] = mapped_column(String(120))
    izvorni_zapis: Mapped[str | None] = mapped_column(Text)             # cijeli obrazac, doslovno

    # Provjera učinkovitosti prije zatvaranja — ISO 9001 t.10.2 (Faza 9)
    ucinkovitost_provjerena: Mapped[bool] = mapped_column(Boolean, default=False)
    ucinkovitost_datum: Mapped[date | None] = mapped_column(Date)
    ucinkovitost_biljeska: Mapped[str | None] = mapped_column(Text)

    # Procjena rizika (FMEA) 1–10 -> RPN = sev × occ × det (Faza 9)
    fmea_sev: Mapped[int | None] = mapped_column(Integer)
    fmea_occ: Mapped[int | None] = mapped_column(Integer)
    fmea_det: Mapped[int | None] = mapped_column(Integer)

    capa: Mapped[list["CAPA"]] = relationship(back_populates="reklamacija",
                                               cascade="all, delete-orphan",
                                               order_by="CAPA.rok_izvrsenja")
    privici: Mapped[list["Privitak"]] = relationship(back_populates="reklamacija",
                                                     cascade="all, delete-orphan",
                                                     order_by="Privitak.id")
    troskovi: Mapped[list["StavkaTroska"]] = relationship(back_populates="reklamacija",
                                                          cascade="all, delete-orphan",
                                                          order_by="StavkaTroska.id")
    scars: Mapped[list["SCAR"]] = relationship(back_populates="reklamacija",
                                               cascade="all, delete-orphan",
                                               order_by="SCAR.id")

    VRSTA = {
        "INTERNA":   "Interna nesukladnost",
        "KUPAC":     "Reklamacija kupca",
        "DOBAVLJAC": "Nesukladnost dobavljača",
    }
    STATUS = {
        "NOVO":      "Novo",
        "U_OBRADI":  "U obradi",
        "CEKA":      "Čeka dijelove/odgovor",
        "RIJESENO":  "Riješeno",
        "ZATVORENO": "Zatvoreno",
    }
    PRIORITET = {
        "NIZAK":   "Nizak",
        "SREDNJI": "Srednji",
        "VISOK":   "Visok",
        "KRITICAN": "Kritičan",
    }
    KATEGORIJA = {
        "MANJA": "Manja",
        "VECA":  "Veća",
    }
    IZVOR = {
        "DOBAVLJAC": "Dobavljač (materijal)",
        "INTERNO":   "Interni proces",
        "KUPAC":     "Kupac (predložak/artwork)",
    }
    TEZINA = {
        "KRITICAN": "Kritičan",
        "VELIKI":   "Veliki",
        "MALI":     "Mali",
    }
    # Porijeklo nesukladnosti — kvačice iz papirnatog obrasca
    PORIJEKLO = {
        "POGRESKA_U_RADU":  "Pogreška u radu",
        "REKLAMACIJA":      "Reklamacija",
        "AUDIT":            "Izvještaj internog/vanjskog audita",
        "CERT_KUCA":        "Izvještaj certifikacijske kuće",
        "UPRAVINA_OCJENA":  "Upravina ocjena sustava",
        "OSTALO":           "Ostalo",
    }
    DEFEKT = {
        "A": "A · Boja i ton",
        "B": "B · Pasovanje / registracija",
        "C": "C · Kvaliteta otiska",
        "D": "D · Štanca i dorada",
        "E": "E · Ljepilo i prianjanje",
        "F": "F · Lak i laminacija",
        "G": "G · Materijal / podloga",
        "H": "H · Dimenzije i format",
        "I": "I · Sadržaj / barkod / priprema",
        "J": "J · Pakiranje / isporuka",
    }

    @property
    def vrsta_display(self): return self.VRSTA.get(self.vrsta, self.vrsta)
    @property
    def status_display(self): return self.STATUS.get(self.status, self.status)
    @property
    def prioritet_display(self): return self.PRIORITET.get(self.prioritet, self.prioritet)
    @property
    def kategorija_display(self): return self.KATEGORIJA.get(self.kategorija or "", "")
    @property
    def izvor_display(self): return self.IZVOR.get(self.izvor or "", "")
    @property
    def tezina_display(self): return self.TEZINA.get(self.tezina or "", "")
    @property
    def defekt_display(self): return self.DEFEKT.get(self.defekt_kategorija or "", "")
    @property
    def porijeklo_display(self):
        naziv = self.PORIJEKLO.get(self.porijeklo or "", "")
        if naziv and self.porijeklo_napomena:
            return f"{naziv}: {self.porijeklo_napomena}"
        return naziv or (self.porijeklo_napomena or "")

    @property
    def je_zatvorena(self): return self.status in ("RIJESENO", "ZATVORENO")

    @property
    def rok_prekoracen(self):
        return bool(self.rok_rjesavanja and self.rok_rjesavanja < date.today() and not self.je_zatvorena)

    @property
    def broj_capa(self): return len(self.capa)

    @property
    def broj_otvorenih_capa(self): return sum(1 for c in self.capa if c.status != "IZVRSENA")

    # ── Troškovi / COPQ rollup ──
    @property
    def trosak_ukupno(self) -> float:
        return round(sum(t.iznos or 0.0 for t in self.troskovi), 2)

    @property
    def trosak_povrativo(self) -> float:
        """Dio troška koji je nadoknadiv (npr. naplaćeno dobavljaču/osiguranju)."""
        return round(sum(t.iznos or 0.0 for t in self.troskovi if t.povrativo), 2)

    @property
    def trosak_neto(self) -> float:
        """Neto trošak koji stvarno tereti tvrtku (ukupno − povrativo)."""
        return round(self.trosak_ukupno - self.trosak_povrativo, 2)

    @property
    def trosak_po_snosiocu(self) -> dict:
        out = {"INTERNO": 0.0, "KUPAC": 0.0, "DOBAVLJAC": 0.0}
        for t in self.troskovi:
            out[t.tko_snosi or "INTERNO"] = out.get(t.tko_snosi or "INTERNO", 0.0) + (t.iznos or 0.0)
        return {k: round(v, 2) for k, v in out.items()}

    @property
    def broj_troskova(self) -> int: return len(self.troskovi)

    # ── FMEA / rizik ──
    @property
    def rpn(self) -> int | None:
        if self.fmea_sev and self.fmea_occ and self.fmea_det:
            return self.fmea_sev * self.fmea_occ * self.fmea_det
        return None

    @property
    def rizik_razina(self) -> str:
        """Razina rizika prema RPN (prag 100/200)."""
        r = self.rpn
        if r is None: return ""
        if r >= 200: return "VISOK"
        if r >= 100: return "SREDNJI"
        return "NIZAK"

    # ── Provjera učinkovitosti / zatvaranje ──
    @property
    def moze_zatvoriti(self) -> bool:
        """Smije li se zatvoriti — traži potvrđenu učinkovitost (ISO 10.2)."""
        return bool(self.ucinkovitost_provjerena)

    # ── SCAR (reklamacije dobavljaču) ──
    @property
    def broj_scar(self) -> int: return len(self.scars)

    @property
    def broj_otvorenih_scar(self) -> int:
        return sum(1 for s in self.scars if s.status not in ("ZATVOREN", "ODBIJEN"))

    @property
    def scar_naplaceno(self) -> float:
        """Ukupno priznato/naplaćeno od dobavljača kroz sve SCAR-ove."""
        return round(sum(s.iznos_priznat or 0.0 for s in self.scars), 2)


class CAPA(Base):
    __tablename__ = "capa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reklamacija_id: Mapped[int] = mapped_column(Integer, ForeignKey("reklamacija.id"), index=True)
    reklamacija: Mapped["Reklamacija"] = relationship(back_populates="capa")

    vrsta: Mapped[str] = mapped_column(String(20), default="KOREKTIVNA")
    opis_mjere: Mapped[str] = mapped_column(Text)
    odgovorna_osoba: Mapped[str] = mapped_column(String(100))
    rok_izvrsenja: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="PLANIRANA")
    datum_izvrsenja: Mapped[date | None] = mapped_column(Date)
    rezultat: Mapped[str | None] = mapped_column(Text)
    provjerio: Mapped[str | None] = mapped_column(String(100))
    datum_provjere: Mapped[date | None] = mapped_column(Date)

    VRSTA = {"KOREKTIVNA": "Korektivna mjera", "PREVENTIVNA": "Preventivna mjera"}
    STATUS = {
        "PLANIRANA": "Planirana",
        "U_TIJEKU":  "U tijeku",
        "IZVRSENA":  "Izvršena",
        "ODGODENA":  "Odgođena",
    }

    @property
    def vrsta_display(self): return self.VRSTA.get(self.vrsta, self.vrsta)
    @property
    def status_display(self): return self.STATUS.get(self.status, self.status)

    @property
    def je_prekoracen(self):
        return bool(self.rok_izvrsenja and self.rok_izvrsenja < date.today() and self.status != "IZVRSENA")


class Privitak(Base):
    """Privitak (slika/dokument) uz reklamaciju. Bajtovi na disku (`uploads/`),
    metapodaci u bazi."""
    __tablename__ = "privitak"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reklamacija_id: Mapped[int] = mapped_column(Integer, ForeignKey("reklamacija.id"), index=True)
    reklamacija: Mapped["Reklamacija"] = relationship(back_populates="privici")

    stored_name: Mapped[str] = mapped_column(String(80))            # uuid.ext na disku
    original_name: Mapped[str] = mapped_column(String(255))         # za prikaz/preuzimanje
    rel_path: Mapped[str] = mapped_column(String(120))             # npr. 2026/06/<uuid>.jpg
    mime_type: Mapped[str | None] = mapped_column(String(100))
    velicina: Mapped[int] = mapped_column(Integer, default=0)       # bajtovi
    vrsta: Mapped[str] = mapped_column(String(10), default="dokument")  # slika | dokument
    ima_thumb: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def velicina_kb(self) -> int:
        return round((self.velicina or 0) / 1024)


class StavkaTroska(Base):
    """Stavka troška nekvalitete (COPQ) vezana uz reklamaciju.
    iznos = kolicina × jed_cijena (izračunato pri spremanju). `povrativo` = trošak
    koji je nadoknadiv (naplata dobavljaču/osiguranju) i ne tereti neto COPQ."""
    __tablename__ = "stavka_troska"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reklamacija_id: Mapped[int] = mapped_column(Integer, ForeignKey("reklamacija.id"), index=True)
    reklamacija: Mapped["Reklamacija"] = relationship(back_populates="troskovi")

    kategorija: Mapped[str] = mapped_column(String(30), default="OSTALO", index=True)
    opis: Mapped[str | None] = mapped_column(String(200))
    kolicina: Mapped[float] = mapped_column(Float, default=1.0)
    jedinica: Mapped[str | None] = mapped_column(String(20))          # kom/kg/m/sat/EUR/…
    jed_cijena: Mapped[float] = mapped_column(Float, default=0.0)     # € po jedinici
    iznos: Mapped[float] = mapped_column(Float, default=0.0)          # € = kolicina×jed_cijena
    tko_snosi: Mapped[str] = mapped_column(String(20), default="INTERNO", index=True)  # INTERNO/KUPAC/DOBAVLJAC
    povrativo: Mapped[bool] = mapped_column(Boolean, default=False)   # nadoknadiv trošak
    stroj: Mapped[str | None] = mapped_column(String(100))
    kreirano_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    KATEGORIJA = {
        "OTPAD_MATERIJALA":  "Otpad materijala",
        "DORADA_RAD":        "Dorada / prerada (rad)",
        "STROJNI_SAT":       "Strojni sat",
        "SORTIRANJE":        "Sortiranje / kontrola",
        "POVRAT_TRANSPORT":  "Povrat i transport",
        "ODOBRENJE_KUPCU":   "Odobrenje / popust kupcu",
        "HITNI_REPRINT":     "Hitni reprint",
        "ADMIN":             "Administracija / obrada",
        "OSTALO":            "Ostalo",
    }
    SNOSI = {
        "INTERNO":   "Interno (tvrtka)",
        "KUPAC":     "Kupac",
        "DOBAVLJAC": "Dobavljač",
    }

    @property
    def kategorija_display(self): return self.KATEGORIJA.get(self.kategorija, self.kategorija)
    @property
    def snosi_display(self): return self.SNOSI.get(self.tko_snosi, self.tko_snosi)


class SCAR(Base):
    """SCAR — Supplier Corrective Action Request (reklamacija prema dobavljaču).
    Vezan uz internu reklamaciju/nesukladnost; prati zahtjev, rok odgovora,
    rješenje i naplaćeni iznos."""
    __tablename__ = "scar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reklamacija_id: Mapped[int] = mapped_column(Integer, ForeignKey("reklamacija.id"), index=True)
    reklamacija: Mapped["Reklamacija"] = relationship(back_populates="scars")

    broj_scar: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # SCAR-YYYY-000N
    dobavljac: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default="OTVOREN", index=True)

    lot_sarza: Mapped[str | None] = mapped_column(String(120))   # lot / šarža / broj role
    broj_primke: Mapped[str | None] = mapped_column(String(60))  # GR — primka
    broj_narudzbe: Mapped[str | None] = mapped_column(String(60))  # PO — narudžba
    kolicina: Mapped[float | None] = mapped_column(Float)
    jedinica: Mapped[str | None] = mapped_column(String(20))

    datum_slanja: Mapped[date | None] = mapped_column(Date)
    rok_odgovora: Mapped[date | None] = mapped_column(Date)
    datum_odgovora: Mapped[date | None] = mapped_column(Date)

    opis_zahtjeva: Mapped[str | None] = mapped_column(Text)
    odgovor_dobavljaca: Mapped[str | None] = mapped_column(Text)   # njihova analiza uzroka / 8D
    rjesenje: Mapped[str | None] = mapped_column(String(20))       # CREDIT/ZAMJENA/DORADA/POVRAT/OTPIS
    broj_debit_note: Mapped[str | None] = mapped_column(String(60))
    iznos_reklamiran: Mapped[float] = mapped_column(Float, default=0.0)
    iznos_priznat: Mapped[float] = mapped_column(Float, default=0.0)
    napomena: Mapped[str | None] = mapped_column(Text)

    kreirano_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    STATUS = {
        "OTVOREN":          "Otvoren",
        "POSLANO":          "Poslano dobavljaču",
        "U_ANALIZI":        "Dobavljač analizira",
        "ODGOVOR_PRIMLJEN": "Odgovor primljen",
        "ZATVOREN":         "Zatvoren",
        "ODBIJEN":          "Odbijen",
    }
    RJESENJE = {
        "CREDIT":  "Knjižno odobrenje (credit)",
        "ZAMJENA": "Zamjena robe",
        "DORADA":  "Dorada / sortiranje",
        "POVRAT":  "Povrat dobavljaču (RTV)",
        "OTPIS":   "Otpis (scrap)",
    }

    @property
    def status_display(self): return self.STATUS.get(self.status, self.status)
    @property
    def rjesenje_display(self): return self.RJESENJE.get(self.rjesenje or "", "")
    @property
    def je_zatvoren(self): return self.status in ("ZATVOREN", "ODBIJEN")

    @property
    def rok_prekoracen(self):
        return bool(self.rok_odgovora and self.rok_odgovora < date.today() and not self.je_zatvoren)

    @property
    def stopa_naplate(self) -> float:
        """% priznatog u odnosu na reklamirani iznos."""
        if not self.iznos_reklamiran:
            return 0.0
        return round(100.0 * (self.iznos_priznat or 0.0) / self.iznos_reklamiran, 1)
