# Datensätze – Verfügbarkeit, Download, Lizenz

Stand der Prüfung: 17.11.2026, direkt an den Quellen geprüft (HTTP-Abruf der Seiten und Buckets), nicht aus dem Gedächtnis.
Rohdaten liegen nur in `data/raw/` (gitignored), vorverarbeitete Fälle in `data/cases/` (ebenfalls gitignored).

## Übersicht

| Datensatz | Status | Downloadweg | Lizenz | Labeltyp | Im Testsatz |
|---|---|---|---|---|---|
| RSNA ICH Detection (2019) | ✅ frei erreichbar | AWS Open Data, Bucket `intracranial-hemorrhage` (us-west-2), **eine** ZIP-Datei `rsna-ihd-dataset.zip`, 194,7 GB, ohne AWS-Konto | RSNA MIRA Dataset Research Use Agreement (Forschung, nicht kommerziell) | pro Schnitt, Subtyp, keine Masken | noch nicht (s. u.) |
| CQ500 (Qure.ai) | ✅ frei erreichbar | `https://s3.ap-south-1.amazonaws.com/qure.headct.study/CQ500-CT-<n>.zip` und `reads.csv` (Listing gesperrt, Einzeldateien abrufbar). Die alte Seite headctstudy.qure.ai löst nicht mehr auf. | CC BY-NC-SA 4.0 laut Paper/Qure-Angaben; Original-Lizenzseite nicht mehr erreichbar, daher **nicht abschließend bestätigt** | Studienebene, 3 Radiologen (Subtyp, Seite, Fraktur, Masseneffekt) | 10 Studien |
| PhysioNet CT-ICH (Hssayeni) | ⚠️ eingeschränkt | Aktuelle Version 1.3.1: **Restricted Access**, PhysioNet-Konto plus unterschriebene Datennutzungsvereinbarung nötig. Die offene Version 1.0.0 (CC BY 4.0) ist zwar noch gelistet, ihre Dateien sind aber nicht mehr verfügbar. | PhysioNet Restricted Health Data License 1.5.0 | Maske pro Schnitt (NIfTI), 82 CTs, 5 mm | nein, Maxi muss sich selbst registrieren |
| BHSD | ✅ frei erreichbar | Hugging Face `Wendy-Fly/BHSD` (Alias `WuBiao/BHSD`): `label_192.zip` (1,45 GB, 192 Volumen mit Masken), `unlabel_1980.zip` (15 GB, ohne Masken) | widersprüchlich: HF-Tag „MIT“, README „protected under copyright“, `dataset.json` „licence: AIML“. Für private Lernnutzung vertretbar, **keine Weitergabe**. | Voxelmaske, 5 Klassen (EDH, IPH, IVH, SAH, SDH) | 10 Volumen |
| Mimics | ❌ kein gelabelter Datensatz | – | – | – | später aus CQ500-Normalfällen kuratieren (Werkzeug in Schritt 5) |
| Radiopaedia | nicht automatisiert laden | – | – | – | – |

## Details und Fallstricke

### RSNA
- Range-Requests auf das 194-GB-ZIP funktionieren. `preprocess/httpzip.py` liest das zentrale Verzeichnis (874.037 Einträge, ca. 20 s) und holt dann einzelne DICOMs gezielt. Kaggle-Konto oder Komplettdownload sind nicht nötig.
- Inhalt: `stage_2_train/` (752.803 DICOMs), `stage_2_test/`, `stage_2_train.csv` (Labels pro Bild-ID).
- **Problem:** Labels und Dateinamen sind pro Schnitt. Um eine Studie zusammenzusetzen, muss man aus jedem DICOM-Header die StudyInstanceUID lesen, also ca. 750.000 kleine Range-Requests. Für Normalfälle lohnt sich das erst mit einer gezielten Stichprobe (ein Schnitt pro Kandidat und dann die passende Serie). Das ist für Schritt 4 geplant.
- **BHSD ist aus RSNA abgeleitet.** Die Dateinamen `ID_<Patient>_ID_<Studie>` sind RSNA-IDs. BHSD-Fälle und RSNA-Fälle können also dieselben Patienten sein: nicht doppelt in den Pool aufnehmen.

### CQ500
- Pro Studie mehrere Serien (Dünnschicht 0,625 mm, 5 mm, Knochenkern, teils KM). `prep_cq500.py` wählt die native Weichteilserie nahe 5 mm, schließt Knochenkern und KM aus und mittelt Dünnschicht notfalls auf 5 mm.
- Einige DICOMs sind JPEG-Lossless-komprimiert und brauchen deshalb `pylibjpeg` und `pylibjpeg-libjpeg`.
- **„Normal“ heißt hier: keiner der 3 Radiologen sah ICH, Fraktur oder Masseneffekt.** Andere Befunde (Atrophie, alte Infarkte) sind möglich. Beispiel: `cq500_17` hat deutlich erweiterte Ventrikel bzw. einen alten Defekt. Für das Blutungstraining ist „normal“ also „keine akute Blutung“.
- Blutungsfälle haben nur Labels auf Studienebene. Die Lokalisation lässt sich nicht pro Schnitt bewerten, nur Kategorie und Seite.

### BHSD
- Volumen liegen bereits in HU, außerhalb des Messfelds mit −2048 bzw. −3024 aufgefüllt (wird auf −1024 gesetzt).
- Alle 192 gelabelten Volumen sind pathologisch. Normalfälle müssen also aus anderen Quellen kommen (s. Shortcut-Risiko).
- Häufigkeit (Volumen mit Label): IPH 127, SAH 109, IVH 104, SDH 70, EDH 23. Mit nur einem Typ: EDH 11, IPH 11, IVH 8, SAH 9, SDH 10.

### PhysioNet CT-ICH
Zugang: auf physionet.org registrieren und die Datennutzungsvereinbarung für `ct-ich` 1.3.1 unterschreiben. Danach kann die App die Dateien per Benutzername/Passwort laden. Bis dahin decken BHSD-Masken die pixelgenaue Bewertung ab.

## Shortcut-Risiko (Stand Testsatz)

| Risiko | Befund | Maßnahme |
|---|---|---|
| Quelle verrät Klasse | BHSD ist immer pathologisch, alle Normalfälle stammen aus CQ500. | Einheitliches Gitter: 0,5 mm in-plane, festes FOV 256 mm, Hintergrund −1024 HU, 5 mm Schichtdicke. Langfristig Normalfälle auch aus RSNA (gleicher Scannerpark wie BHSD) und Blutungen auch aus CQ500 (schon im Testsatz). |
| Schichtdicke | BHSD 5,0–5,4 mm (Gantry-Kippung), CQ500 5 mm bzw. gemittelt (`cq500_46`: 3 mm → 6 mm) | In `case.json` steht `spacing_mm`; im Viewer nicht angezeigt |
| Metall, Drainagen, OP-Folgen | `bhsd_ID_39bdd84b…` (IVH): Metallartefakte bis 16.600 HU, gekippter Stapel → vermutlich Drainage oder Clip | in `preprocess/overrides.json` als `confounders` markiert |
| Gantry-Kippung | häufiger in RSNA/BHSD | vorerst nicht korrigiert, Bild wird gestapelt angezeigt wie am Befundplatz |

## Testsatz (20 Fälle, 3 Kategorien)
- 10 × BHSD mit Voxelmaske: je 2 × EDH, SDH, SAH, IVH, IPH (jeweils nur ein Typ)
- 6 × CQ500 normal (einstimmig ohne ICH, Fraktur, Masseneffekt)
- 4 × CQ500 Blutung (einstimmig EDH, SDH, SAH bzw. IVH, meist mit weiteren Typen)
- Normalanteil 30 %, Mimics 0 % (kommen mit dem Kurationswerkzeug)

Reproduzieren: `make data` (lädt und verarbeitet genau diese Fälle), `make verify` (HU-Stichprobe und Montage).
