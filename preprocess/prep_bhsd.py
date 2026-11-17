"""BHSD (label_192) -> data/cases. Volumen liegen bereits in HU (aus RSNA-DICOMs rekonstruiert).

Aufruf: python preprocess/prep_bhsd.py [--ids datei.txt] [--n-per-type 2]
"""
import argparse
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, AIR, CATEGORIES, head_center, hu_check, save_case, to_target_grid  # noqa: E402

RAW = ROOT / "data" / "raw" / "bhsd_x" / "label_192"
# BHSD-Label -> Kategorie
BHSD_LABELS = {1: "epidural", 2: "intraparenchymatoes", 3: "intraventrikulaer",
               4: "subarachnoidal", 5: "subdural"}
# Kategorie -> App-Maskencode (1..5, Reihenfolge wie CATEGORIES)
APP_CODE = {c: i + 1 for i, c in enumerate(CATEGORIES)}


def load_canonical(path, order):
    img = nib.as_closest_canonical(nib.load(str(path)))  # RAS: x->R, y->A, z->S
    a = np.asarray(img.dataobj, dtype=np.float32)
    zooms = img.header.get_zooms()[:3]
    # [x,y,z] -> [z,y,x]; Zeile 0 = anterior (y umdrehen), Spalte 0 = Patient rechts (x umdrehen)
    a = np.transpose(a, (2, 1, 0))[:, ::-1, ::-1]
    return np.ascontiguousarray(a), (float(zooms[2]), float(zooms[1]), float(zooms[0]))


def convert(name):
    vol, (dz, dy, dx) = load_canonical(RAW / "images" / name, 1)
    msk, _ = load_canonical(RAW / "ground truths" / name, 0)
    vol[vol < AIR] = AIR  # Out-of-FOV-Padding (-2048/-3024) -> Luft
    remap = np.zeros(8, np.uint8)
    for k, cat in BHSD_LABELS.items():
        remap[k] = APP_CODE[cat]
    msk = remap[np.clip(np.round(msk).astype(int), 0, 7)]
    c = head_center(vol)
    vol_t = to_target_grid(vol, (dy, dx), order=1, fill=AIR, center=c)
    msk_t = to_target_grid(msk.astype(np.float32), (dy, dx), order=0, fill=0, center=c)
    labels = sorted({BHSD_LABELS[k] for k in np.unique(np.round(np.asarray(nib.load(str(RAW / 'ground truths' / name)).dataobj))).astype(int) if k})
    case_id = "bhsd_" + name.replace(".nii.gz", "")
    meta = {
        "source": "bhsd",
        "source_ref": name,
        "class": "pathologic",
        "labels": labels,
        "label_granularity": "voxel",
        "native_spacing_mm": [round(dz, 3), round(dy, 4), round(dx, 4)],
    }
    save_case(case_id, vol_t, dz, meta, mask=np.round(msk_t))
    return case_id, labels, hu_check(vol_t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="Datei mit BHSD-Dateinamen, eine pro Zeile")
    ap.add_argument("--n-per-type", type=int, default=2)
    args = ap.parse_args()
    if args.ids:
        names = [l.strip() for l in open(args.ids) if l.strip()]
    else:
        # Standard-Testsatz: je n Fälle mit genau einem Blutungstyp
        names, count = [], {k: 0 for k in BHSD_LABELS}
        for p in sorted((RAW / "ground truths").glob("*.nii.gz")):
            u = [int(x) for x in np.unique(np.asarray(nib.load(str(p)).dataobj)) if x]
            if len(u) == 1 and count[u[0]] < args.n_per_type:
                names.append(p.name)
                count[u[0]] += 1
    for n in names:
        cid, labels, chk = convert(n)
        print(cid, labels, chk)


if __name__ == "__main__":
    main()
