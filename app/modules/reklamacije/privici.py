"""Privici — spremanje datoteka na disk (`uploads/`) + validacija + thumbnail.

Sigurnost: UUID nazivi na disku (nikad korisnikov naziv), allowlist ekstenzija,
provjera da je slika stvarno slika (Pillow), limit veličine. Bez libmagic (portabilno).
"""
import io
import uuid
from datetime import datetime
from pathlib import Path

UPLOAD_DIR = Path("uploads")

SLIKE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DOKUMENTI = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".txt"}
DOZVOLJENE = SLIKE | DOKUMENTI

MAX_SLIKA = 15 * 1024 * 1024   # 15 MB
MAX_DOK = 30 * 1024 * 1024     # 30 MB


def _ext(name: str) -> str:
    return Path(name).suffix.lower()


def validiraj(original_name: str, velicina: int) -> str | None:
    """Vrati poruku greške ili None ako je OK."""
    e = _ext(original_name)
    if e not in DOZVOLJENE:
        return f"Nedozvoljen tip datoteke: {e or '(bez ekstenzije)'}"
    limit = MAX_SLIKA if e in SLIKE else MAX_DOK
    if velicina > limit:
        return f"Prevelika datoteka ({round(velicina/1024/1024)} MB, max {limit//1024//1024} MB)"
    if velicina == 0:
        return "Prazna datoteka."
    return None


def spremi_datoteku(reklamacija_id: int, original_name: str, data: bytes):
    """Spremi bajtove na disk + (za slike) thumbnail. Vrati dict kwargs za Privitak, ili str greške."""
    err = validiraj(original_name, len(data))
    if err:
        return err
    e = _ext(original_name)
    je_slika = e in SLIKE
    if je_slika:
        try:
            from PIL import Image
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            return "Datoteka nije valjana slika."

    now = datetime.now()
    subdir = UPLOAD_DIR / f"{now:%Y}" / f"{now:%m}"
    subdir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{e}"
    (subdir / stored).write_bytes(data)

    ima_thumb = False
    if je_slika:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            img.thumbnail((260, 260))
            img.convert("RGB").save(subdir / f"{Path(stored).stem}_thumb.jpg", "JPEG", quality=80)
            ima_thumb = True
        except Exception:
            ima_thumb = False

    return dict(
        reklamacija_id=reklamacija_id, stored_name=stored,
        original_name=original_name[:255], rel_path=f"{now:%Y}/{now:%m}/{stored}",
        velicina=len(data), vrsta="slika" if je_slika else "dokument", ima_thumb=ima_thumb,
    )


def putanja(p) -> Path:
    return UPLOAD_DIR / p.rel_path


def thumb_putanja(p) -> Path:
    pp = putanja(p)
    return pp.parent / f"{pp.stem}_thumb.jpg"


def obrisi_datoteke(p) -> None:
    for f in (putanja(p), thumb_putanja(p)):
        try:
            f.unlink()
        except Exception:
            pass
