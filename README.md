# NeuroRad Trainer

Lern-App für das Befunden von Schädel-CTs (siehe `CLAUDE.md`, Datenlage in `DATA.md`).

```bash
make install   # Python-Abhängigkeiten
make data      # Testsatz laden (~1,9 GB Rohdaten) und nach data/cases/ vorverarbeiten
make verify    # HU-Stichprobe, Schnittreihenfolge, Montage in data/verify/montage.png
make run       # Server auf http://localhost:8000, öffnet den Browser
```

Stand: Schritt 2 (Vorverarbeitung + Viewer). Schema-Checkliste, Befundeingabe und Auflösung folgen.
