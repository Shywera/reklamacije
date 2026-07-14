"""CI smoke — prijava, kreiranje s taksonomijom, COPQ rollup, PDF, analitika."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app


def _client():
    c = TestClient(app)
    r = c.post("/login", data={"username": "admin", "lozinka": "admin"},
               follow_redirects=False)
    assert r.status_code == 303
    return c


def test_bez_prijave_redirect():
    c = TestClient(app)
    r = c.get("/reklamacije", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_tok_reklamacije():
    c = _client()
    r = c.post("/reklamacije/nova", data={
        "naslov": "CI test", "opis": "opis", "prijavitelj": "CI",
        "defekt_kategorija": "A", "izvor": "INTERNO", "tezina": "MALI",
    }, follow_redirects=False)
    assert r.status_code == 303
    rid = int(r.headers["location"].rsplit("/", 1)[-1])

    assert c.get(f"/reklamacije/{rid}").status_code == 200

    r = c.post(f"/reklamacije/{rid}/trosak/dodaj", data={
        "kategorija": "OTPAD_MATERIJALA", "kolicina": "10",
        "jed_cijena": "2,5", "tko_snosi": "INTERNO"})
    assert r.status_code == 200 and "25.00" in r.text

    r = c.get(f"/reklamacije/{rid}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_analitika_i_lista():
    c = _client()
    assert c.get("/reklamacije/analitika").status_code == 200
    assert c.get("/reklamacije/lista").status_code == 200
