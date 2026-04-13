# IU Studien-Dashboard

Python-Prototyp fuer das Portfolio im Kurs `Objektorientierte und funktionale Programmierung mit Python (DLBDSOOFPP01_D)`.

Das Projekt bildet einen Studiengang mit Semestern, Modulen und Pruefungsleistungen ab und stellt die wichtigsten Kennzahlen in einem `tkinter`-Dashboard dar.

## Funktionen

- Anzeige von vier KPIs zum Studienfortschritt
- Verwaltung von Semestern, Modulen und Pruefungsleistungen
- Speicherung der Daten in `studiengang.json`
- Fallback-Erzeugung einer Standard-JSON, falls die Datei fehlt
- Export der Studiendaten als JSON

## Projektstruktur

- `dashboard.py`: Anwendung mit Domaenenmodell, Repository, Controller und GUI
- `studiengang.json`: persistente Studiendaten
- `uml_studium_v2.png`: UML der Entity-Klassen
- `uml_gesamtarchitektur_v2.png`: UML der Gesamtarchitektur
- `Schumbera-Sascha_IU14153477_Python_Phase1_v2.pdf`: finales Dokument Phase 1
- `Schumbera-Sascha_IU14153477_Python_Phase2_v2.pdf`: finales Dokument Phase 2

## Voraussetzungen

- Windows
- Python 3.14 oder eine aktuelle Python-3-Version mit `tkinter`

## Start

```powershell
python dashboard.py
```

Beim ersten Start wird automatisch eine minimale `studiengang.json` erzeugt, falls noch keine Datei vorhanden ist.

## Hinweise

- Es werden keine externen Python-Pakete benoetigt.
- Die Anwendung verwendet ausschliesslich die Python-Standardbibliothek.
- Die eigentliche Portfolio-Abgabe erfolgt gemaess IU-Vorgaben zusaetzlich ueber die geforderte ZIP-Struktur in PebblePad.
