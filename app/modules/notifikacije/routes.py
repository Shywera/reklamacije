"""Admin rute za email notifikacije: pregled statusa + ručna provjera rokova.
Putanje su pod /admin (middleware traži 'admin' dozvolu). Pozadinskog schedulera
nema — provjera rokova pokreće se ovdje ili preko `provjeri-rokove.bat` (Task Scheduler)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.notifikacije import mailer

router = APIRouter(tags=["notifikacije"])
templates = Jinja2Templates(directory="app/templates")


def _status() -> dict:
    return {
        "omoguceno": bool(settings.notif_enabled and settings.smtp_host),
        "smtp_host": settings.smtp_host or "—",
        "smtp_port": settings.smtp_port,
        "notif_from": settings.notif_from,
        "notif_default": settings.notif_default or "—",
    }


@router.get("/admin/notifikacije", response_class=HTMLResponse)
def notif_home(request: Request):
    return templates.TemplateResponse(request, "notifikacije/notifikacije.html",
                                      {"st": _status(), "rezultat": None})


@router.post("/admin/notifikacije/provjeri", response_class=HTMLResponse)
def notif_provjeri(request: Request, db: Session = Depends(get_db)):
    rezultat = mailer.provjeri_rokove(db)
    return templates.TemplateResponse(request, "notifikacije/notifikacije.html",
                                      {"st": _status(), "rezultat": rezultat})
