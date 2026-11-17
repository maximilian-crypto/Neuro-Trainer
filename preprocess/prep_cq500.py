"""CQ500 (DICOM-Zips von Qure.ai) -> data/cases.

Labels: Studienebene, Mehrheitsentscheid der 3 Radiologen aus reads.csv.
Aufruf: python preprocess/prep_cq500.py CQ500-CT-17 CQ500-CT-46 ...
        (ohne Argumente: alle entpackten Studien in data/raw/cq500_x)
"""
import csv
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pydicom

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, AIR, head_center, hu_check, save_case, thick_slabs, to_target_grid  # noqa: E402

RAW = ROOT / "data" / "raw" / "cq500"
X = ROOT / "data" / "raw" / "cq500_x"
READS = {"IPH": "intraparenchymatoes", "IVH": "intraventrikulaer", "SDH": "subdural",
         "EDH": "epidural", "SAH": "subarachnoidal"}
BAD_SERIES = re.compile(r"(bone|(?<!pre )contrast|post|\bcc\b|\d+cc|d3d|lung|chst|scout|topo)", re.I)


def reads():
    return {r["name"]: r for r in csv.DictReader(open(RAW / "reads.csv"))}


def votes(r, key):
    return sum(int(r[f"R{i}:{key}"]) for i in (1, 2, 3))


def load_series(files):
    ds = [pydicom.dcmread(f) for f in files]
    ds = [d for d in ds if hasattr(d, "ImagePositionPatient") and hasattr(d, "pixel_array")]
    iop = np.array(ds[0].ImageOrientationPatient, float)
    rowdir, coldir = iop[:3], iop[3:]
    normal = np.cross(rowdir, coldir)
    ds.sort(key=lambda d: float(np.dot(np.array(d.ImagePositionPatient, float), normal)))
    pos = np.array([np.dot(np.array(d.ImagePositionPatient, float), normal) for d in ds])
    vol = np.stack([d.pixel_array.astype(np.float32) * float(getattr(d, "RescaleSlope", 1))
                    + float(getattr(d, "RescaleIntercept", 0)) for d in ds])
    # Sortierung nach Normalen: aufsteigend entlang normal. Bei Standard-IOP ist normal = +z (LPS: kranial).
    if normal[2] < 0:
        vol, pos = vol[::-1], pos[::-1]
    # Spalten sollen nach Patient links laufen (+x in LPS), Zeilen nach posterior (+y)
    if rowdir[0] < 0:
        vol = vol[:, :, ::-1]
    if coldir[1] < 0:
        vol = vol[:, ::-1, :]
    dz = float(np.median(np.abs(np.diff(pos)))) if len(pos) > 1 else float(ds[0].SliceThickness)
    ps = [float(x) for x in ds[0].PixelSpacing]
    info = {"series": str(getattr(ds[0], "SeriesDescription", "")),
            "kernel": str(getattr(ds[0], "ConvolutionKernel", "")),
            "manufacturer": str(getattr(ds[0], "Manufacturer", "")),
            "n_slices": len(ds), "slice_thickness": float(getattr(ds[0], "SliceThickness", 0) or 0)}
    return np.ascontiguousarray(vol), dz, ps, info


def pick_series(study_dir):
    """Nativserie im Weichteilkern, möglichst ~5 mm; sonst Dünnschicht (wird zu 5 mm gemittelt)."""
    best = None
    for sd in sorted(p for p in study_dir.rglob("*") if p.is_dir()):
        files = sorted(sd.glob("*.dcm"))
        if len(files) < 15:
            continue
        h = pydicom.dcmread(files[0], stop_before_pixels=True)
        desc = f"{sd.name} {getattr(h, 'SeriesDescription', '')} {getattr(h, 'ConvolutionKernel', '')}"
        if BAD_SERIES.search(desc):
            continue
        ps = float(h.PixelSpacing[0])
        if ps > 0.75:  # großes FOV -> vermutlich kein reiner Schädel-Datensatz
            continue
        th = float(getattr(h, "SliceThickness", 0) or 0)
        score = abs(th - 5.0) + (0 if "-2" not in sd.name else 0.1)
        if best is None or score < best[0]:
            best = (score, files)
    return best[1] if best else None


def ensure_extracted(name):
    d = X / name.replace("-", "")
    hits = list(X.glob(f"{name.replace('-', '')} *")) + ([d] if d.exists() else [])
    if hits:
        return hits[0]
    with zipfile.ZipFile(RAW / f"{name}.zip") as z:
        z.extractall(X)
    return list(X.glob(f"{name.replace('-', '')} *"))[0]


def convert(name, r):
    files = pick_series(ensure_extracted(name))
    if files is None:
        raise RuntimeError(f"{name}: keine passende Nativserie")
    vol, dz, ps, info = load_series(files)
    vol, dz = thick_slabs(vol, dz)
    c = head_center(vol)
    vol_t = to_target_grid(vol, ps, order=1, fill=AIR, center=c)
    ich = votes(r, "ICH") >= 2
    labels = sorted(cat for k, cat in READS.items() if votes(r, k) >= 2)
    findings = {k: votes(r, k) for k in ["ICH", *READS, "Fracture", "CalvarialFracture", "MassEffect",
                                       "MidlineShift", "ChronicBleed", "BleedLocation-Left",
                                       "BleedLocation-Right"]}
    meta = {
        "source": "cq500",
        "source_ref": name,
        "class": "pathologic" if ich else "normal",
        "labels": labels if ich else ["unauffaellig"],
        "label_granularity": "study",
        "reader_votes": findings,  # Anzahl der 3 Radiologen, die den Befund gesehen haben
        "series_info": info,
        "native_spacing_mm": [round(dz, 3), ps[0], ps[1]],
    }
    if votes(r, "Fracture") >= 2:
        meta["confounders"] = ["fracture"]
    cid = "cq500_" + name.split("-")[-1]
    save_case(cid, vol_t, dz, meta)
    return cid, meta["labels"], info["series"], hu_check(vol_t)


def main():
    rd = reads()
    names = sys.argv[1:] or sorted(p.stem for p in RAW.glob("CQ500-CT-*.zip"))
    for n in names:
        print(*convert(n, rd[n]))


if __name__ == "__main__":
    main()
