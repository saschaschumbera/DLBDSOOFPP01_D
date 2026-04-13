# IU Studien-Dashboard

Python-Prototyp für das Portfolio im Kurs `Objektorientierte und funktionale Programmierung mit Python (DLBDSOOFPP01_D)`.

Das Projekt bildet einen Studiengang mit Semestern, Modulen und Prüfungsleistungen ab und stellt die wichtigsten Kennzahlen in einem `tkinter`-Dashboard dar.

## Funktionen

- Anzeige von vier KPIs zum Studienfortschritt
- Verwaltung von Semestern, Modulen und Prüfungsleistungen
- Speicherung der Daten in `studiengang.json`
- Fallback-Erzeugung einer Standard-JSON, falls die Datei fehlt
- Export der Studiendaten als JSON

## Projektstruktur

- `dashboard.py`: Anwendung mit Domänenmodell, Repository, Controller und GUI
- `studiengang.json`: persistente Studiendaten

## Voraussetzungen

- Windows
- Python 3.14 oder eine aktuelle Python-3-Version mit `tkinter`

## Start

```powershell
python dashboard.py
```

Beim ersten Start wird automatisch eine minimale `studiengang.json` erzeugt, falls noch keine Datei vorhanden ist.

## Hinweise

- Es werden keine externen Python-Pakete benötigt.
- Die Anwendung verwendet ausschließlich die Python-Standardbibliothek.
- Die eigentliche Portfolio-Abgabe erfolgt gemäß IU-Vorgaben zusätzlich über die geforderte ZIP-Struktur in PebblePad.
