"""FastAPI-Backend: Fallliste, Volumen (binär, gzip), statisches Frontend.

Start: make run   (oder: uvicorn server.app:app --port 8000)
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "cases"
WEB = ROOT / "web"

app = FastAPI(title="NeuroRad Trainer")


def _case_dir(case_id: str) -> Path:
    d = (CASES / case_id).resolve()
    if d.parent != CASES.resolve() or not (d / "case.json").exists():
        raise HTTPException(404, "Fall nicht gefunden")
    return d


def _meta(d: Path) -> dict:
    return json.loads((d / "case.json").read_text())


@app.get("/api/cases")
def list_cases():
    """Fallliste ohne Lösung (Labels erst nach Abgabe, siehe /meta)."""
    out = []
    for d in sorted(CASES.iterdir()) if CASES.exists() else []:
        if (d / "case.json").exists():
            m = _meta(d)
            out.append({"id": m["id"], "shape": m["shape"], "spacing_mm": m["spacing_mm"],
                        "has_mask": bool(m.get("mask_file"))})
    return out


@app.get("/api/cases/{case_id}/meta")
def case_meta(case_id: str):
    return _meta(_case_dir(case_id))


def _gz(path: Path):
    if not path.exists():
        raise HTTPException(404)
    # Datei ist gzip-komprimiert; der Browser entpackt sie über Content-Encoding selbst.
    return Response(path.read_bytes(), media_type="application/octet-stream",
                    headers={"Content-Encoding": "gzip", "Cache-Control": "max-age=3600"})


@app.get("/api/cases/{case_id}/volume")
def case_volume(case_id: str):
    d = _case_dir(case_id)
    return _gz(d / _meta(d)["volume_file"])


@app.get("/api/cases/{case_id}/mask")
def case_mask(case_id: str):
    d = _case_dir(case_id)
    mf = _meta(d).get("mask_file")
    if not mf:
        raise HTTPException(404, "keine Maske")
    return _gz(d / mf)


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
