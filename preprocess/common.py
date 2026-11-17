"""Gemeinsame Vorverarbeitung: einheitliches Gitter und Speicherformat für alle Quellen.

Zielgitter (Konvention für alle Fälle):
  Array-Achsen [z, y, x]
  z: Index 0 = kaudal (Schädelbasis), aufsteigend nach kranial, Ziel 5 mm
  y: Zeile 0 = anterior
  x: Spalte 0 = rechte Patientenseite (radiologische Konvention: rechts im Bild links)
  In-plane 0.5 mm, 512 x 512 Pixel (= 256 mm FOV), zentriert auf den Kopf.

Das feste FOV und der einheitliche Hintergrund (-1024 HU) entfernen zwei
Shortcut-Merkmale, an denen man sonst die Quelle (und damit oft die Klasse)
erkennen könnte: unterschiedliche Zoomstufen und Padding-Werte (-2048/-3024).
"""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

TARGET_Z_MM = 5.0
TARGET_XY_MM = 0.5
TARGET_XY_PX = 512
AIR = -1024

ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "data" / "cases"

# Labelnamen der App (Kategorien aus dem Projektbrief)
CATEGORIES = ["epidural", "subdural", "subarachnoidal", "intraventrikulaer",
              "intraparenchymatoes"]


def thick_slabs(vol, z_mm):
    """Dünnschicht-Stapel zu ~5-mm-Schichten mitteln (wie eine klinische Rekonstruktion).
    vol [z,y,x] float, z_mm = Schichtabstand. Schichten mit Abstand 4-6 mm bleiben wie sie sind."""
    if 4.0 <= z_mm <= 6.0:
        return vol, z_mm
    n = max(1, int(round(TARGET_Z_MM / z_mm)))
    nz = vol.shape[0] // n
    v = vol[: nz * n].reshape(nz, n, *vol.shape[1:]).mean(axis=1)
    return v, z_mm * n


def head_center(vol):
    """Schwerpunkt des Kopfes in-plane (Pixel > -500 HU über alle Schichten)."""
    proj = (vol > -500).sum(axis=0)
    if proj.sum() == 0:
        return np.array(vol.shape[1:]) / 2
    return np.array(ndimage.center_of_mass(proj))


def to_target_grid(vol, xy_mm, order, fill, center=None):
    """In-plane auf 0.5 mm resamplen und 512x512 um den Kopfschwerpunkt ausschneiden.
    vol [z,y,x]; xy_mm (dy, dx). center: Pixelkoordinate im Eingangsgitter."""
    if center is None:
        center = np.array(vol.shape[1:]) / 2
    out = np.empty((vol.shape[0], TARGET_XY_PX, TARGET_XY_PX), dtype=np.float32)
    half = TARGET_XY_PX / 2
    # Ausgabepixel (i,j) -> Eingabepixel
    sy = TARGET_XY_MM / xy_mm[0]
    sx = TARGET_XY_MM / xy_mm[1]
    oy = center[0] - half * sy
    ox = center[1] - half * sx
    for k in range(vol.shape[0]):
        out[k] = ndimage.affine_transform(
            vol[k].astype(np.float32), matrix=[sy, sx], offset=[oy, ox],
            output_shape=(TARGET_XY_PX, TARGET_XY_PX), order=order,
            mode="constant", cval=fill)
    return out


def save_case(case_id, vol_hu, z_mm, meta, mask=None):
    """Speichert volume.i16.gz (+ mask.u8.gz) und case.json in data/cases/<id>/."""
    d = CASES_DIR / case_id
    d.mkdir(parents=True, exist_ok=True)
    v = np.clip(np.round(vol_hu), -1024, 3071).astype("<i2")
    with gzip.open(d / "volume.i16.gz", "wb", compresslevel=6) as f:
        f.write(v.tobytes())
    meta = dict(meta)
    meta.update({
        "id": case_id,
        "modality": "CT",
        "shape": list(v.shape),
        "spacing_mm": [round(float(z_mm), 3), TARGET_XY_MM, TARGET_XY_MM],
        "volume_file": "volume.i16.gz",
        "volume_dtype": "int16-le",
        "axes": "z(kaudal->kranial), y(anterior->posterior), x(Patient rechts->links)",
    })
    if mask is not None:
        m = mask.astype(np.uint8)
        with gzip.open(d / "mask.u8.gz", "wb", compresslevel=6) as f:
            f.write(m.tobytes())
        meta["mask_file"] = "mask.u8.gz"
        meta["slices_positive"] = [int(i) for i in np.nonzero(m.reshape(m.shape[0], -1).any(1))[0]]
    else:
        meta.setdefault("mask_file", None)
    ov = json.loads((Path(__file__).parent / "overrides.json").read_text()).get(case_id, {})
    meta.update(ov)
    meta.setdefault("slices_positive", [])
    meta.setdefault("confounders", [])
    meta.setdefault("contrast_partner_ids", [])
    meta.setdefault("mimic_type", None)
    (d / "case.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return d


def hu_check(vol):
    """Plausibilitätswerte für die Stichprobenprüfung."""
    brainish = vol[(vol > -100) & (vol < 100)]
    return {
        "p50_softtissue": float(np.median(brainish)) if brainish.size else None,
        "max": float(vol.max()),
        "frac_bone_gt700": float((vol > 700).mean()),
    }
