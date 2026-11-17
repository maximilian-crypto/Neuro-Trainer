"""Stichprobenprüfung der vorverarbeiteten Fälle.

- HU: Liquor (Ventrikel) um 0, Hirngewebe 20-45, Knochen > 700
- Schnittreihenfolge: Index 0 kaudal (Kopfquerschnitt wächst nach kranial bis zur Mitte,
  ganz oben am Vertex klein; Orbita/Schädelbasis unten)
- Montage-PNG mit Maskenoverlay zur visuellen Kontrolle: data/verify/montage.png
Aufruf: python preprocess/verify.py
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from common import CASES_DIR, ROOT  # noqa: E402


def load(d):
    meta = json.loads((d / "case.json").read_text())
    z, y, x = meta["shape"]
    v = np.frombuffer(gzip.open(d / meta["volume_file"]).read(), "<i2").reshape(z, y, x)
    m = None
    if meta.get("mask_file"):
        m = np.frombuffer(gzip.open(d / meta["mask_file"]).read(), np.uint8).reshape(z, y, x)
    return meta, v, m


def window(a, w=80, l=40):
    return (np.clip((a - (l - w / 2)) / w, 0, 1) * 255).astype(np.uint8)


def checks(meta, v):
    z = v.shape[0]
    mid = v[z // 2 : z // 2 + 3]
    brain = mid[(mid > 15) & (mid < 60)]
    csf = mid[(mid > -15) & (mid < 15)]  # grobe Liquorklasse
    area = [(s > -200).sum() for s in v]
    peak = int(np.argmax(area))
    # Luft innerhalb des Kopfes (Nasennebenhöhlen, Mastoid) liegt kaudal -> z-Schwerpunkt in der unteren Hälfte
    from scipy import ndimage
    air = np.array([(ndimage.binary_fill_holes(s > -300) & (s < -500)).sum() for s in v], float)
    air_cz = float((air * np.arange(z)).sum() / max(air.sum(), 1))
    return {
        "brain_median": round(float(np.median(brain)), 1),
        "csf_mode": round(float(np.median(csf)), 1),
        "bone_p99": float(np.percentile(v[v > 300], 99)) if (v > 300).any() else None,
        "area_peak_slice": f"{peak}/{z}",
        "air_centroid": f"{air_cz:.1f}/{z}",
        "order_ok": bool(air_cz < z / 2 and area[-1] < max(area)),
    }


def main():
    out = ROOT / "data" / "verify"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    ok = True
    for d in sorted(p for p in CASES_DIR.iterdir() if (p / "case.json").exists()):
        meta, v, m = load(d)
        c = checks(meta, v)
        ok &= c["order_ok"] and 15 < c["brain_median"] < 50
        print(f"{meta['id']:34s} {meta['class']:10s} {','.join(meta['labels']):40s} {c}")
        z = v.shape[0]
        if m is not None and meta["slices_positive"]:
            sp = meta["slices_positive"]
            ks = [sp[len(sp) // 2], int(z * 0.3), int(z * 0.75)]
        else:
            ks = [int(z * 0.3), int(z * 0.5), int(z * 0.75)]
        tiles = []
        for k in ks:
            g = window(v[k].astype(np.float32))
            rgb = np.stack([g, g, g], -1)
            if m is not None:
                mk = m[k] > 0
                rgb[mk] = (0.5 * rgb[mk] + 0.5 * np.array([255, 0, 0])).astype(np.uint8)
            im = Image.fromarray(rgb).resize((192, 192))
            ImageDraw.Draw(im).text((4, 4), f"{meta['id'][:22]} z{k}", fill=(255, 255, 0))
            tiles.append(im)
        rows.append(tiles)
    W = Image.new("RGB", (192 * 3 * 2, 192 * ((len(rows) + 1) // 2)))
    for i, tiles in enumerate(rows):
        for j, t in enumerate(tiles):
            W.paste(t, ((i % 2) * 576 + j * 192, (i // 2) * 192))
    W.save(out / "montage.png")
    print("Montage:", out / "montage.png", "| alle Checks ok:" , ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
