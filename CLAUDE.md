# NeuroRad Trainer – Projektbrief

Persönliche Lern-App für Maxi (Medizinstudent, 4. Jahr), um das Befunden von Schädel-CT (Computertomographie) und später MRT (Magnetresonanztomographie) zu trainieren. Ein einziger Nutzer, läuft lokal. Kein Produkt, keine Veröffentlichung.

## Worum es geht

Trainiert wird **Mustererkennung durch Wiederholung und sofortiges Feedback**, nicht Theorie. Vorbild sind Perceptual Adaptive Learning Modules (PALMs, Kellman): viele Entscheidungen, sofortige Auflösung, die Lösung direkt neben dem eigenen Fehler.

Daraus folgen feste Anforderungen. Sie sind der Kern der App und haben Vorrang vor Komfortfunktionen:

1. **Erst festlegen, dann auflösen.** Die Lösung erscheint erst, wenn der Nutzer jede Station des Suchschemas abgehakt und einen Befund abgegeben hat (inklusive „unauffällig“).
2. **Feedback auf Bildebene.** Die eigene Markierung wird als Overlay gegen die Referenz gezeigt, auf demselben Schnitt. Text ist dabei zweitrangig.
3. **Drei Klassen im Pool: pathologisch, normal, Mimic.** Ohne Mimics (Verkalkung, Aufhärtungsartefakt, hyperdenser Sinus usw.) lernt das Auge falsche Merkmale. Ziel ist ein Normalanteil von 30 bis 50 Prozent.
4. **Interleaving.** Kategorien werden gemischt, nie in Blöcken („heute nur Subduralhämatom“).
5. **Kontrastpaare.** Nach einem Fehler kann ein ähnlicher Fall mit anderer Diagnose daneben gezeigt werden (z. B. Epidural- gegen Subduralhämatom, Blut gegen Verkalkung).
6. **Fehlerprofil statt Punktzahl.** Gespeichert wird, *was* übersehen oder verwechselt wird (Kategorie, Lokalisation, Größe). Die Fallauswahl gewichtet danach.

## MVP-Umfang (zuerst bauen, sonst nichts)

- Nur **Schädel-CT nativ**, nur das Thema **intrakranielle Blutung gegen Normalbefund gegen Mimic**
- **Stapel-Modus:** ganzen axialen Stapel durchscrollen wie am Befundungsplatz
- Viewer: Scrollen, Fensterung mit Presets (Hirn W80/L40, Subdural W200/L80, Schlaganfall W40/L40, Knochen W2800/L600), Zoom, Pan
- Suchschema als Checkliste neben dem Viewer. Standard ist „Blood Can Be Very Bad“ (Blood, Cisterns, Brain, Ventricles, Bone). Die Stationen müssen konfigurierbar sein.
- Befundeingabe: Kategorie (Liste unten) plus Klick- oder Pinsel-Markierung auf dem Schnitt
- Auflösung: Referenz-Overlay, Referenzlabel, eigener Befund daneben, Zeit
- Speicherung jedes Versuchs in SQLite, einfache Statistikseite mit dem Fehlerprofil

Kategorien im MVP: epidural, subdural, subarachnoidal, intraventrikulär, intraparenchymatös, mehrere, unauffällig, Mimic (mit Unterart).

## Spätere Phasen (nicht im MVP)

- **Blitz-Modus:** Einzelschnitte im Sekundentakt, Entscheidung in unter 5 Sekunden (PALM-Stil), trainiert Erkennen statt Suchen
- Schlaganfall (CT, dann MRT mit DWI/ADC)
- Tumoren im MRT
- Spaced Repetition über Fälle hinweg

## Daten

Rohdaten kommen nie ins Repo. Sie liegen in `data/raw/` (in `.gitignore`), vorverarbeitete Fälle in `data/cases/`.

| Datensatz | Inhalt | Nutzung |
|---|---|---|
| RSNA Intracranial Hemorrhage Detection (Kaggle 2019) | sehr viele Schädel-CTs, Label **pro Schnitt** mit Blutungssubtyp, **keine Masken** | Hauptpool für Erkennung und Subtyp; Bewertung der Lokalisation nur auf Schnittebene |
| CQ500 (Qure.ai) | knapp 500 Schädel-CTs, Lesungen von 3 Radiologen auf Studienebene | Validierungs- und Mischpool |
| PhysioNet „CT-ICH“ (Hssayeni et al.) | kleiner Satz mit **Segmentierungsmasken** | Fälle mit pixelgenauer Bewertung der Markierung |
| BHSD (Brain Hemorrhage Segmentation Dataset) | Blutungen mit Masken | wie oben, falls verfügbar |
| Mimics | **gibt es nicht als gelabelten Datensatz** | zunächst aus normalen Fällen kuratieren (Plexus-, Pinealis-, Falxverkalkung sind dort häufig); Werkzeug zum manuellen Labeln einplanen |

**Erste Aufgabe vor jedem Code:** Verfügbarkeit, Downloadweg und Lizenz jedes Datensatzes aktuell prüfen und in `DATA.md` festhalten. Die Angaben oben stammen aus dem Gedächtnis, nicht aus einer Prüfung. Lizenzen sind meist auf nicht-kommerzielle Forschung beschränkt; für private Nutzung sollte das passen, aber bitte prüfen. Radiopaedia-Fälle **nicht** automatisiert herunterladen.

**Wichtige Falle:** Die Bewertung hängt vom Labeltyp ab. Fälle mit Maske werden pixelgenau bewertet, RSNA-Fälle nur danach, ob der richtige Schnittbereich markiert wurde. Das Datenmodell muss diesen Unterschied abbilden, statt so zu tun, als hätten alle Fälle Masken.

**Shortcut-Risiko:** Prüfen, ob pathologische Fälle systematisch andere Merkmale haben (Drainagen, Bohrlöcher, Schichtdicke, Scanner, Tubus). Solche Fälle markieren oder ausgleichen, sonst lernt Maxi das Artefakt statt der Blutung.

## Architektur (Vorschlag, begründet abweichen ist ok)

- **Vorverarbeitung (Python):** `pydicom`, `nibabel`, `numpy`. Pro Fall: in Hounsfield-Einheiten umrechnen, axial sortieren, auf einheitliche Schichtdicke bringen, als komprimiertes int16-Volumen plus `case.json` speichern. Masken auf dasselbe Gitter.
- **Backend:** FastAPI, liefert Fallliste, Volumen (binär), speichert Versuche in SQLite.
- **Frontend:** eine schlanke Web-App. Fensterung clientseitig auf int16-Daten im Canvas oder WebGL, damit die Fenster sofort umschalten. Erst eigener Viewer. Cornerstone3D nur, wenn der eigene Viewer an Grenzen stößt.
- Start mit einem Befehl (`make run` oder ein Skript), öffnet im Browser.

### Fallmodell (`case.json`, Entwurf)

```json
{
  "id": "rsna_ID_xxx",
  "source": "rsna|cq500|physionet_ctich|bhsd|curated",
  "modality": "CT",
  "class": "pathologic|normal|mimic",
  "labels": ["subdural"],
  "mimic_type": null,
  "label_granularity": "voxel|slice|study",
  "slices_positive": [12, 13, 14],
  "mask_file": "mask.npy.gz",
  "confounders": ["drain"],
  "contrast_partner_ids": []
}
```

### Versuch (SQLite)

Fall-ID, Zeitstempel, Modus, Dauer, abgehakte Schemastationen, abgegebene Kategorie, Markierung (Koordinaten oder Maske), Ergebnis (richtig, falsch positiv, falsch negativ, falscher Subtyp, falsche Lokalisation), betroffene Region.

### Fallauswahl

Gewichtete Zufallsauswahl: Basisanteile nach Klasse (pathologisch, normal, Mimic) plus Zuschlag für Kategorien und Regionen mit hoher Fehlerrate im Fehlerprofil. Keine zwei Fälle derselben Kategorie hintereinander, wenn vermeidbar.

## Nicht-Ziele

- Keine KI-generierten Erklärungen zu Bildern. Feedback kommt nur aus echten Labels und Masken.
- Kein Login, keine Cloud, kein Mehrbenutzer.
- Kein Befundbericht-Generator.

## Vorgehen

1. Datensätze prüfen, `DATA.md` schreiben, kleinen Testsatz laden (etwa 20 Fälle aus 2 Quellen).
2. Vorverarbeitung plus Viewer mit Scrollen und Fensterung. **Hier stoppen und Maxi zeigen.**
3. Schema-Checkliste, Befundeingabe, Auflösung mit Overlay.
4. SQLite, Fehlerprofil, gewichtete Auswahl.
5. Mimic-Kurationswerkzeug.

Nach jedem Schritt lauffähiger Zustand. Bei Unklarheiten in der Didaktik fragen, statt zu raten: Maxi will die Lernlogik mitgestalten.

## Prüfung

- Vorverarbeitung: Stichproben mit bekannten HU-Werten (Liquor um 0, Knochen über 700) und richtiger Schnittreihenfolge
- Masken liegen deckungsgleich auf dem Bild (visuell prüfen, Screenshot)
- Ein Durchlauf von 10 Fällen ohne Fehler im Browser, Versuche korrekt in SQLite

## Offene Entscheidungen (mit Maxi klären)

- Sprache der Oberfläche: Deutsch oder Englisch (Studium an der RSU auf Englisch)
- Reihenfolge Blitz- gegen Stapel-Modus, falls Maxi Erkennen vor Suchen trainieren will
- Wie viel Zeitdruck im Stapel-Modus
