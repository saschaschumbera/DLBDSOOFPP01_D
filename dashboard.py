#!/usr/bin/env python3
"""
IU Studien-Dashboard – Prototyp
================================
Kurs   : Objektorientierte und funktionale Programmierung mit Python (DLBDSOOFPP01_D)
Autor  : Sascha Schumbera  |  Matrikelnummer: IU14153477
Phase  : 3 – Finalisierungsphase

Architektur (5 Schichten, analog zum UML-Klassendiagramm aus Phase 2):
  1. Entity-Klassen    – Fachliche Domänenobjekte
  2. Domain-Services   – KPI-Berechnung und KPI-Wertobjekte (@dataclass)
  3. Infrastruktur     – Persistenz (StudiengangRepository, JSONRepository)
  4. Anwendungsschicht – DashboardController als Vermittler zwischen UI und Domäne
  5. UI                – tkinter-Oberfläche (DashboardApp, Dialoge)

Start: python dashboard.py

Abhängigkeiten: ausschließlich Python-Standardbibliothek (tkinter, json,
dataclasses, enum, abc, datetime, os) – kein pip-Install erforderlich.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox


# ═══════════════════════════════════════════════════════════════════════════════
# 1 ─ ENTITY-KLASSEN
# ═══════════════════════════════════════════════════════════════════════════════

class ModulStatus(Enum):
    """Zulässige Zustände eines Moduls (Enumeration verhindert ungültige Werte)."""
    GEPLANT         = "Geplant"
    IN_BEARBEITUNG  = "In Bearbeitung"
    BESTANDEN       = "Bestanden"
    NICHT_BESTANDEN = "Nicht bestanden"


class Pruefungsleistung:
    """Repräsentiert einen einzelnen Prüfungsversuch zu einem Modul."""

    def __init__(self, note: float, datum: date, versuch: int) -> None:
        self._note: float = 0.0   # Platzhalter; Setter überschreibt sofort
        self.note = note          # Validierung über @property-Setter
        self._datum = datum
        self._versuch = versuch

    @property
    def note(self) -> float:
        """Prüfungsnote im Bereich 1.0 bis 5.0."""
        return self._note

    @note.setter
    def note(self, wert: float) -> None:
        """Setzt die Note nach Validierung (1.0 ≤ note ≤ 5.0)."""
        if not 1.0 <= wert <= 5.0:
            raise ValueError(f"Note {wert} ungültig – erlaubt: 1.0 bis 5.0.")
        self._note = wert

    @property
    def datum(self) -> date:
        """Datum der Prüfungsleistung."""
        return self._datum

    @property
    def versuch(self) -> int:
        """Versuchsnummer (1 = Erstversuch)."""
        return self._versuch

    def ist_bestanden(self) -> bool:
        """True, wenn die Note ≤ 4.0 ist."""
        return self._note <= 4.0


class Modul:
    """Repräsentiert ein Lehrmodul innerhalb eines Semesters."""

    def __init__(self, name: str, modulnummer: str, ects: int) -> None:
        self._name = name
        self._modulnummer = modulnummer
        self._ects = ects
        self._status = ModulStatus.GEPLANT
        self._pruefungsleistungen: list[Pruefungsleistung] = []

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, wert: str) -> None:
        self._name = wert

    @property
    def modulnummer(self) -> str:
        return self._modulnummer

    @modulnummer.setter
    def modulnummer(self, wert: str) -> None:
        self._modulnummer = wert

    @property
    def ects(self) -> int:
        return self._ects

    @ects.setter
    def ects(self, wert: int) -> None:
        if wert <= 0:
            raise ValueError("ECTS müssen positiv sein.")
        self._ects = wert

    @property
    def status(self) -> ModulStatus:
        return self._status

    @status.setter
    def status(self, wert: ModulStatus) -> None:
        """Setzt den Modulstatus direkt (z. B. beim Laden aus dem Repository)."""
        self._status = wert

    @property
    def pruefungsleistungen(self) -> list[Pruefungsleistung]:
        """Gibt eine Kopie der Prüfungsleistungsliste zurück."""
        return list(self._pruefungsleistungen)

    def pruefung_hinzufuegen(self, pl: Pruefungsleistung) -> None:
        """Fügt eine Prüfungsleistung hinzu und aktualisiert den Modulstatus."""
        self._pruefungsleistungen.append(pl)
        self._status = ModulStatus.BESTANDEN if pl.ist_bestanden() else ModulStatus.NICHT_BESTANDEN

    def _lade_pruefungsleistung(self, pl: Pruefungsleistung) -> None:
        """Intern: lädt eine Prüfungsleistung ohne Statusänderung (nur für JSONRepository)."""
        self._pruefungsleistungen.append(pl)

    def ist_bestanden(self) -> bool:
        """True, wenn der Modulstatus BESTANDEN ist."""
        return self._status == ModulStatus.BESTANDEN



class Abschlussarbeit(Modul):
    """
    Spezialisierung von Modul für die Bachelorarbeit.
    Kardinalität 0..1 pro Studiengang – wird in Studiengang.modul_hinzufuegen() erzwungen.
    """

    def __init__(self, thema: str = "", betreuer: str = "") -> None:
        super().__init__("Bachelorarbeit", "DLBABSCHLUSSB01", ects=12)
        self._thema = thema
        self._betreuer = betreuer

    @property
    def thema(self) -> str:
        return self._thema

    @thema.setter
    def thema(self, wert: str) -> None:
        self._thema = wert

    @property
    def betreuer(self) -> str:
        return self._betreuer

    @betreuer.setter
    def betreuer(self, wert: str) -> None:
        self._betreuer = wert


class Semester:
    """Fasst die Module eines Studiensemesters zusammen (Komposition mit Studiengang)."""

    def __init__(self, nummer: int, startdatum: date, enddatum: date) -> None:
        self._nummer = nummer
        self._startdatum = startdatum
        self._enddatum = enddatum
        self._module: list[Modul] = []

    @property
    def nummer(self) -> int:
        return self._nummer

    @property
    def startdatum(self) -> date:
        return self._startdatum

    @property
    def enddatum(self) -> date:
        return self._enddatum

    @property
    def module(self) -> list[Modul]:
        """Gibt eine Kopie der Modulliste zurück."""
        return list(self._module)

    def modul_hinzufuegen(self, modul: Modul) -> None:
        """Fügt ein Modul zum Semester hinzu."""
        self._module.append(modul)

    def modul_entfernen(self, modul: Modul) -> None:
        """Entfernt ein Modul aus dem Semester."""
        self._module.remove(modul)

    def berechne_ects(self) -> int:
        """Summiert die ECTS aller bestandenen Module des Semesters."""
        return sum(m.ects for m in self._module if m.ist_bestanden())

    def berechne_durchschnitt(self) -> Optional[float]:
        """Berechnet den Notendurchschnitt aller bestandenen Prüfungsleistungen."""
        noten = [pl.note for m in self._module for pl in m.pruefungsleistungen if pl.ist_bestanden()]
        return round(sum(noten) / len(noten), 2) if noten else None


class Studiengang:
    """Wurzelobjekt: repräsentiert den gesamten Studiengang eines Studierenden."""

    def __init__(self, name: str, gesamt_ects: int, regelstudienzeit: int) -> None:
        self._name = name
        self._gesamt_ects = gesamt_ects
        self._regelstudienzeit = regelstudienzeit
        self._semester: list[Semester] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def gesamt_ects(self) -> int:
        return self._gesamt_ects

    @property
    def regelstudienzeit(self) -> int:
        return self._regelstudienzeit

    @property
    def semester(self) -> list[Semester]:
        """Gibt eine Kopie der Semesterliste zurück."""
        return list(self._semester)

    def semester_entfernen(self, semester: Semester) -> None:
        """Entfernt ein Semester aus dem Studiengang."""
        self._semester.remove(semester)

    def erstelle_semester(self, nummer: int, startdatum: date, enddatum: date) -> Semester:
        """Erzeugt ein neues Semester und fügt es intern hinzu (Komposition)."""
        sem = Semester(nummer, startdatum, enddatum)
        self._semester.append(sem)
        return sem

    def get_semester(self, nummer: int) -> Optional[Semester]:
        """Gibt das Semester mit der angegebenen Nummer zurück, oder None."""
        for s in self._semester:
            if s.nummer == nummer:
                return s
        return None

    def modul_hinzufuegen(self, modul: Modul, semester: Semester) -> None:
        """
        Fügt ein Modul einem Semester hinzu.
        Verhindert, dass mehr als eine Abschlussarbeit angelegt wird (Geschäftsregel).
        """
        if isinstance(modul, Abschlussarbeit):
            alle = [m for s in self._semester for m in s.module]
            if any(isinstance(m, Abschlussarbeit) for m in alle):
                raise ValueError("Pro Studiengang ist nur eine Abschlussarbeit erlaubt.")
        semester.modul_hinzufuegen(modul)

    def berechne_fortschritt(self) -> float:
        """ECTS-Fortschritt in Prozent (0.0 bis 100.0)."""
        if self._gesamt_ects == 0:
            return 0.0
        erreicht = sum(m.ects for s in self._semester for m in s.module if m.ist_bestanden())
        return round(erreicht / self._gesamt_ects * 100, 1)

    def berechne_notendurchschnitt(self) -> Optional[float]:
        """Notendurchschnitt (ECTS-gewichtet) aller bestandenen Module."""
        gesamt_note = 0.0
        gesamt_ects = 0
        
        for s in self._semester:
            for m in s.module:
                if m.ist_bestanden():
                    # Letzte Note zählt als bestanden
                    pl = m.pruefungsleistungen[-1]
                    gesamt_note += pl.note * m.ects
                    gesamt_ects += m.ects
                    
        if gesamt_ects == 0:
            return None
        return round(gesamt_note / gesamt_ects, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 2 ─ DOMAIN-SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RegelstudienzeitKpi:
    """KPI: Fortschritt bezogen auf die Regelstudienzeit."""
    titel: str
    hauptwert: str
    zielhinweis: str
    ziel_erreicht: bool


@dataclass
class NotendurchschnittKpi:
    """KPI: Aktueller Notendurchschnitt aller bestandenen Prüfungsleistungen."""
    titel: str
    hauptwert: str
    zielhinweis: str
    ziel_erreicht: bool


@dataclass
class EctsFortschrittKpi:
    """KPI: Anteil der bereits erreichten ECTS am Gesamtumfang."""
    titel: str
    hauptwert: str
    zielhinweis: str
    ziel_erreicht: bool


@dataclass
class BestehensquoteKpi:
    """KPI: Anteil bestandener Module an allen geprüften Modulen."""
    titel: str
    hauptwert: str
    zielhinweis: str
    ziel_erreicht: bool


class KPICalculator:
    """
    Berechnet die vier Dashboard-KPIs aus einem Studiengang-Objekt.
    Statt generischer Dictionaries liefern alle Methoden typsichere
    @dataclass-Wertobjekte – Tippfehler beim Feldzugriff werden so
    zur Compile-Zeit statt zur Laufzeit erkannt.
    """

    _ZIEL_NOTE: float  = 2.0   # Notenziel aus der Konzeptionsphase
    _ZIEL_QUOTE: float = 80.0  # Mindest-Bestehensquote in Prozent

    def regelstudienzeit_kpi(self, sg: Studiengang) -> RegelstudienzeitKpi:
        """Verbleibende Monate bis zum geplanten Studienabschluss (datumsbasiert)."""
        heute = date.today()
        if sg.semester:
            abschluss = sorted(sg.semester, key=lambda s: s.nummer)[-1].enddatum
        else:
            # Fallback: Regelstudienzeit * 6 Monate ab heute
            abschluss = date(heute.year + sg.regelstudienzeit // 2,
                             heute.month, heute.day)
        delta = (abschluss.year - heute.year) * 12 + (abschluss.month - heute.month)
        verbleibend = max(0, delta)
        erreicht = heute <= abschluss
        check = " ✓" if erreicht else ""
        hauptwert = f"{verbleibend} Monate verbleibend" if erreicht else "Zeitplan überschritten"
        return RegelstudienzeitKpi(
            titel="Regelstudienzeit",
            hauptwert=hauptwert,
            zielhinweis=f"Ziel: {abschluss.strftime('%d.%m.%Y')}{check}",
            ziel_erreicht=erreicht,
        )

    def notendurchschnitt_kpi(self, sg: Studiengang) -> NotendurchschnittKpi:
        """Durchschnitt aller bestandenen Prüfungsleistungen."""
        schnitt = sg.berechne_notendurchschnitt()
        if schnitt is None:
            hauptwert, erreicht = "–", False
        else:
            hauptwert, erreicht = f"Ø {str(schnitt).replace('.', ',')}", schnitt <= self._ZIEL_NOTE
        check = " ✓" if erreicht else ""
        return NotendurchschnittKpi(
            titel="Notendurchschnitt",
            hauptwert=hauptwert,
            zielhinweis=f"Ziel: ≤ {str(self._ZIEL_NOTE).replace('.', ',')}{check}",
            ziel_erreicht=erreicht,
        )

    def ects_soll_kpi(self, sg: Studiengang) -> EctsFortschrittKpi:
        """Erreichte ECTS absolut und als Prozentwert."""
        erreicht = sum(m.ects for s in sg.semester for m in s.module if m.ist_bestanden())
        prozent = sg.berechne_fortschritt()
        ziel_erreicht = erreicht >= sg.gesamt_ects
        check = " ✓" if ziel_erreicht else ""
        return EctsFortschrittKpi(
            titel="ECTS-Fortschritt",
            hauptwert=f"{erreicht} / {sg.gesamt_ects} ECTS  ({prozent:.0f} %)",
            zielhinweis=f"Soll: ≥ 23 / Sem.{check}",
            ziel_erreicht=ziel_erreicht,
        )

    def bestehensquote_kpi(self, sg: Studiengang) -> BestehensquoteKpi:
        """Anteil bestandener Module an allen geprüften Modulen."""
        geprueft = [m for s in sg.semester for m in s.module if m.pruefungsleistungen]
        if not geprueft:
            quote, erreicht = 0.0, False
        else:
            bestanden = sum(1 for m in geprueft if m.ist_bestanden())
            quote = bestanden / len(geprueft) * 100
            erreicht = quote >= self._ZIEL_QUOTE
        check = " ✓" if erreicht else ""
        return BestehensquoteKpi(
            titel="Bestehensquote",
            hauptwert=f"{quote:.0f} %",
            zielhinweis=f"Ziel: ≥ {self._ZIEL_QUOTE:.0f} %{check}",
            ziel_erreicht=erreicht,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3 ─ INFRASTRUKTUR
# ═══════════════════════════════════════════════════════════════════════════════

class StudiengangRepository(ABC):
    """
    Abstrakte Schnittstelle für die Studiendaten-Persistenz.
    Dependency Inversion: Controller und UI hängen von dieser Schnittstelle
    ab, nicht von JSONRepository direkt – Persistenzwechsel erfordert nur
    eine neue Implementierung.
    """

    @abstractmethod
    def laden(self) -> Studiengang:
        """Lädt einen Studiengang aus dem Datenspeicher."""

    @abstractmethod
    def speichern(self, studiengang: Studiengang) -> None:
        """Persistiert den Studiengang im Datenspeicher."""


class JSONRepository(StudiengangRepository):
    """Konkrete Persistenz in einer JSON-Datei; implementiert StudiengangRepository."""

    def __init__(self, dateipfad: str) -> None:
        self._dateipfad = dateipfad

    def laden(self) -> Studiengang:
        """Deserialisiert den Studiengang aus der JSON-Datei."""
        with open(self._dateipfad, encoding="utf-8") as f:
            data = json.load(f)

        sg = Studiengang(data["name"], data["gesamt_ects"], data["regelstudienzeit"])

        for sem_data in data.get("semester", []):
            sem = sg.erstelle_semester(
                sem_data["nummer"],
                date.fromisoformat(sem_data["startdatum"]),
                date.fromisoformat(sem_data["enddatum"]),
            )
            for m_data in sem_data.get("module", []):
                if m_data.get("typ") == "Abschlussarbeit":
                    modul: Modul = Abschlussarbeit(
                        m_data.get("thema", ""),
                        m_data.get("betreuer", ""),
                    )
                else:
                    modul = Modul(m_data["name"], m_data["modulnummer"], m_data["ects"])

                modul.status = ModulStatus(m_data["status"])

                for pl_data in m_data.get("pruefungsleistungen", []):
                    pl = Pruefungsleistung(
                        pl_data["note"],
                        date.fromisoformat(pl_data["datum"]),
                        pl_data["versuch"],
                    )
                    modul._lade_pruefungsleistung(pl)  # Status-Override beim Laden vermeiden

                sem.modul_hinzufuegen(modul)

        return sg

    def speichern(self, sg: Studiengang) -> None:
        """Serialisiert den Studiengang in die JSON-Datei."""
        data = {
            "name": sg.name,
            "gesamt_ects": sg.gesamt_ects,
            "regelstudienzeit": sg.regelstudienzeit,
            "semester": [
                {
                    "nummer": s.nummer,
                    "startdatum": s.startdatum.isoformat(),
                    "enddatum": s.enddatum.isoformat(),
                    "module": [self._modul_zu_dict(m) for m in s.module],
                }
                for s in sg.semester
            ],
        }
        with open(self._dateipfad, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _modul_zu_dict(m: Modul) -> dict:
        """Wandelt ein Modul-Objekt in ein JSON-serialisierbares Dictionary."""
        d: dict = {
            "typ": "Abschlussarbeit" if isinstance(m, Abschlussarbeit) else "Modul",
            "name": m.name,
            "modulnummer": m.modulnummer,
            "ects": m.ects,
            "status": m.status.value,
            "pruefungsleistungen": [
                {"note": pl.note, "datum": pl.datum.isoformat(), "versuch": pl.versuch}
                for pl in m.pruefungsleistungen
            ],
        }
        if isinstance(m, Abschlussarbeit):
            d["thema"] = m.thema
            d["betreuer"] = m.betreuer
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# 4 ─ ANWENDUNGSSCHICHT
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardController:
    """
    Vermittelt zwischen UI und Domäne: kapselt alle Anwendungsfälle
    (Laden, Speichern, KPI-Abfragen, Modul-/Notenverwaltung).
    Die UI kennt kein konkretes JSONRepository – Testbarkeit und
    Austauschbarkeit der Persistenz bleiben erhalten.
    """

    def __init__(self, repository: StudiengangRepository) -> None:
        self._repository = repository
        self._studiengang: Optional[Studiengang] = None
        self._kpi_calc = KPICalculator()

    def initialisieren(self) -> None:
        """Lädt den Studiengang aus dem Repository."""
        self._studiengang = self._repository.laden()

    def speichern(self) -> None:
        """Persistiert den aktuellen Studiengang."""
        self._repository.speichern(self._studiengang)

    def aktueller_studiengang(self) -> Studiengang:
        """Gibt das aktuelle Studiengang-Objekt zurück."""
        return self._studiengang

    # ── KPI-Abfragen (Delegation an KPICalculator) ──────────────────────────

    def regelstudienzeit_kpi(self) -> RegelstudienzeitKpi:
        return self._kpi_calc.regelstudienzeit_kpi(self._studiengang)

    def notendurchschnitt_kpi(self) -> NotendurchschnittKpi:
        return self._kpi_calc.notendurchschnitt_kpi(self._studiengang)

    def ects_soll_kpi(self) -> EctsFortschrittKpi:
        return self._kpi_calc.ects_soll_kpi(self._studiengang)

    def bestehensquote_kpi(self) -> BestehensquoteKpi:
        return self._kpi_calc.bestehensquote_kpi(self._studiengang)

    # ── Anwendungsfälle ──────────────────────────────────────────────────────

    def modul_hinzufuegen(self, modul: Modul, semester_nr: int) -> None:
        """Fügt ein Modul dem Semester hinzu; legt das Semester bei Bedarf neu an."""
        sg = self._studiengang
        sem = sg.get_semester(semester_nr)
        if sem is None:
            start, ende = self._semester_daten(semester_nr)
            sem = sg.erstelle_semester(semester_nr, start, ende)
        sg.modul_hinzufuegen(modul, sem)
        self.speichern()

    def modul_entfernen(self, semester_nr: int, modul_name: str) -> bool:
        """Entfernt ein Modul aus einem Semester. Gibt True zurück bei Erfolg."""
        sem = self._studiengang.get_semester(semester_nr)
        if sem is None:
            return False
        for m in sem.module:
            if m.name == modul_name:
                sem.modul_entfernen(m)
                self.speichern()
                return True
        return False

    def semester_entfernen(self, nummer: int) -> bool:
        """Entfernt ein komplettes Semester. Gibt True zurück bei Erfolg."""
        sg = self._studiengang
        sem = self._studiengang.get_semester(nummer)
        if sem is None:
            return False
        sg.semester_entfernen(sem)
        self.speichern()
        return True

    def semester_anlegen(self, nummer: int, startdatum: date, enddatum: date) -> Semester:
        """Legt ein neues Semester an und speichert."""
        sem = self._studiengang.erstelle_semester(nummer, startdatum, enddatum)
        self.speichern()
        return sem

    def pruefung_hinzufuegen(self, modul: Modul, pl: Pruefungsleistung) -> None:
        """Trägt eine Prüfungsleistung ein, aktualisiert Status und speichert."""
        modul.pruefung_hinzufuegen(pl)
        self.speichern()

    def daten_exportieren(self, dateipfad: str) -> None:
        """Exportiert den Studiengang in eine separate JSON-Datei."""
        sg = self._studiengang
        data = {
            "name": sg.name,
            "gesamt_ects": sg.gesamt_ects,
            "regelstudienzeit": sg.regelstudienzeit,
            "semester": [
                {
                    "nummer": s.nummer,
                    "startdatum": s.startdatum.isoformat(),
                    "enddatum": s.enddatum.isoformat(),
                    "module": [JSONRepository._modul_zu_dict(m) for m in s.module],
                }
                for s in sg.semester
            ],
        }
        with open(dateipfad, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _semester_daten(nummer: int) -> tuple[date, date]:
        """Berechnet Platzhalterdaten für ein Semester (WS/SS-Rhythmus ab WS 2024/25)."""
        basis = 2024
        if nummer % 2 == 1:  # Wintersemester
            j = basis + (nummer - 1) // 2
            return date(j, 10, 1), date(j + 1, 3, 31)
        else:               # Sommersemester
            j = basis + (nummer - 2) // 2 + 1
            return date(j, 4, 1), date(j, 9, 30)


# ═══════════════════════════════════════════════════════════════════════════════
# 5 ─ UI
# ═══════════════════════════════════════════════════════════════════════════════

_GRUEN_BG     = "#d4edda"
_GRUEN_FG     = "#155724"
_ROT_BG       = "#f8d7da"
_ROT_FG       = "#721c24"
_HEADER_BG    = "#003366"
_HEADER_FG    = "#ffffff"
_BTN_BG       = "#2b7a96"
_BTN_FG       = "#ffffff"
_BEIGE_BG     = "#fff8e1"
_GRAU_BG      = "#e8e8e8"
_BESTANDEN_BG = "#d4edda"
_NB_BG        = "#f8d7da"

# Farb-Zuordnung je ModulStatus für Tabellenzeilen
_STATUS_FARBEN: dict[str, str] = {
    "Bestanden":       _BESTANDEN_BG,
    "Nicht bestanden": _NB_BG,
    "In Bearbeitung":  _BEIGE_BG,
    "Geplant":         _GRAU_BG,
}


class ModulDialog:
    """Zeigt Detailinformationen und alle Prüfungsversuche eines Moduls. Erlaubt Bearbeitung."""

    def __init__(self, parent: tk.Tk, controller: DashboardController) -> None:
        self._controller = controller
        self._parent = parent

    def oeffnen(self, modul: Modul) -> None:
        """Öffnet den Detaildialog für das angegebene Modul (modal)."""
        self._modul = modul
        self._win = tk.Toplevel(self._parent)
        self._win.title(f"Modul bearbeiten: {modul.name}")
        self._win.geometry("540x500")
        self._win.resizable(False, False)
        self._baue_layout()
        self._parent.wait_window(self._win)

    def _baue_layout(self) -> None:
        # ── STAMMDATEN (EDITIERBAR) ──
        info_frame = tk.LabelFrame(self._win, text="Stammdaten", padx=12, pady=8)
        info_frame.pack(fill=tk.X, padx=12, pady=10)

        is_abschluss = isinstance(self._modul, Abschlussarbeit)

        tk.Label(info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._name_var = tk.StringVar(value=self._modul.name)
        tk.Entry(info_frame, textvariable=self._name_var, width=35, state="disabled" if is_abschluss else "normal").grid(row=0, column=1, sticky=tk.W, pady=2)

        tk.Label(info_frame, text="Nummer:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._nr_var = tk.StringVar(value=self._modul.modulnummer)
        tk.Entry(info_frame, textvariable=self._nr_var, width=20, state="disabled" if is_abschluss else "normal").grid(row=1, column=1, sticky=tk.W, pady=2)

        tk.Label(info_frame, text="ECTS:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._ects_var = tk.StringVar(value=str(self._modul.ects))
        tk.Entry(info_frame, textvariable=self._ects_var, width=10, state="disabled" if is_abschluss else "normal").grid(row=2, column=1, sticky=tk.W, pady=2)

        if is_abschluss:
            tk.Label(info_frame, text="Thema:").grid(row=3, column=0, sticky=tk.W, pady=2)
            self._thema_var = tk.StringVar(value=self._modul.thema or "")
            tk.Entry(info_frame, textvariable=self._thema_var, width=35).grid(row=3, column=1, sticky=tk.W, pady=2)
            tk.Label(info_frame, text="Betreuer:").grid(row=4, column=0, sticky=tk.W, pady=2)
            self._betreuer_var = tk.StringVar(value=self._modul.betreuer or "")
            tk.Entry(info_frame, textvariable=self._betreuer_var, width=35).grid(row=4, column=1, sticky=tk.W, pady=2)

        tk.Button(info_frame, text="Änderungen speichern", command=self._speichere_stammdaten, cursor="hand2").grid(
            row=5 if is_abschluss else 3, column=1, sticky=tk.W, pady=(8,0))

        # ── PRÜFUNGSVERSUCHE ──
        versuch_frame = tk.LabelFrame(self._win, text="Prüfungsversuche", padx=12, pady=8)
        versuch_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # Toolbar mit Neuer Eintrag
        toolbar = tk.Frame(versuch_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(toolbar, text="Note:").pack(side=tk.LEFT)
        self._note_var_neu = tk.StringVar()
        tk.Entry(toolbar, textvariable=self._note_var_neu, width=6).pack(side=tk.LEFT, padx=(0,10))
        
        tk.Label(toolbar, text="Datum:").pack(side=tk.LEFT)
        self._datum_var_neu = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        tk.Entry(toolbar, textvariable=self._datum_var_neu, width=12).pack(side=tk.LEFT)
        
        tk.Button(toolbar, text="+ Versuch hinzufügen", command=self._neuer_versuch, cursor="hand2").pack(side=tk.RIGHT)

        cols = ("versuch", "datum", "note", "ergebnis")
        self._tree_versuche = ttk.Treeview(versuch_frame, columns=cols, show="headings", height=5)
        for col, head, w in [
            ("versuch", "Versuch", 60), ("datum", "Datum", 110),
            ("note", "Note", 60), ("ergebnis", "Ergebnis", 140),
        ]:
            self._tree_versuche.heading(col, text=head)
            self._tree_versuche.column(col, width=w, anchor=tk.CENTER)
        self._tree_versuche.pack(fill=tk.X)
        self._lade_versuche()

        tk.Button(self._win, text="Schließen", command=self._win.destroy,
                  padx=10, cursor="hand2").pack(pady=(0, 10))

    def _lade_versuche(self) -> None:
        self._tree_versuche.delete(*self._tree_versuche.get_children())
        for pl in self._modul.pruefungsleistungen:
            self._tree_versuche.insert("", tk.END, values=(
                pl.versuch,
                pl.datum.strftime("%d.%m.%Y"),
                f"{pl.note:.1f}".replace(".", ","),
                "Bestanden" if pl.ist_bestanden() else "Nicht bestanden",
            ))
        if not self._modul.pruefungsleistungen:
            self._tree_versuche.insert("", tk.END, values=("–", "–", "–", "Noch keine Prüfung"))

    def _speichere_stammdaten(self) -> None:
        try:
            self._modul.name = self._name_var.get().strip()
            self._modul.modulnummer = self._nr_var.get().strip()
            self._modul.ects = int(self._ects_var.get())
            if isinstance(self._modul, Abschlussarbeit):
                self._modul.thema = self._thema_var.get().strip()
                self._modul.betreuer = self._betreuer_var.get().strip()
            self._controller.speichern()
            messagebox.showinfo("Erfolg", "Modul wurde gespeichert.", parent=self._win)
        except ValueError as e:
            messagebox.showerror("Fehler", f"Ungültige Eingabe:\n{str(e)}", parent=self._win)

    def _neuer_versuch(self) -> None:
        try:
            note_str = self._note_var_neu.get().replace(",", ".")
            if not note_str:
                raise ValueError("Bitte eine Note eingeben.")
            note = float(note_str)
            d = self._datum_var_neu.get().strip()
            if len(d) != 10 or d[2] != "." or d[5] != ".":
                raise ValueError("Datum muss im Format TT.MM.JJJJ sein.")
            datum = date(int(d[6:10]), int(d[3:5]), int(d[0:2]))
            
            versuch = len(self._modul.pruefungsleistungen) + 1
            self._controller.pruefung_hinzufuegen(self._modul, Pruefungsleistung(note, datum, versuch))
            self._note_var_neu.set("")
            self._lade_versuche()
        except ValueError as e:
            messagebox.showerror("Eingabefehler", str(e), parent=self._win)


class EingabeDialog:
    """Dialog zum Hinzufügen eines neuen Moduls."""

    def __init__(self, parent: tk.Tk, controller: DashboardController,
                 aktuelles_semester: int) -> None:
        self._controller = controller
        self._parent = parent
        self._aktuelles_semester = aktuelles_semester
        self._result: Optional[Modul] = None

    def modul_hinzufuegen(self) -> Optional[Modul]:
        """Öffnet den Dialog modal, fügt das neue Modul hinzu und gibt es zurück."""
        self._win = tk.Toplevel(self._parent)
        self._win.title("Neues Modul hinzufügen")
        self._win.geometry("390x260")
        self._win.resizable(False, False)
        self._baue_layout()
        self._parent.wait_window(self._win)
        return self._result

    def _baue_layout(self) -> None:
        frame = tk.Frame(self._win, padx=16, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        self._vars: dict[str, tk.StringVar] = {}
        for i, (label, key, default) in enumerate([
            ("Modulname:",    "name",     ""),
            ("Modulnummer:",  "nummer",   ""),
            ("ECTS:",         "ects",     "5"),
            ("Semester:",     "semester", str(self._aktuelles_semester)),
        ]):
            tk.Label(frame, text=label, anchor=tk.W).grid(row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar(value=default)
            self._vars[key] = var
            tk.Entry(frame, textvariable=var, width=28).grid(row=i, column=1, sticky=tk.W, pady=3)

        self._ist_ba = tk.BooleanVar()
        tk.Checkbutton(frame, text="Abschlussarbeit (12 ECTS, fest vorgegeben)",
                       variable=self._ist_ba,
                       command=self._toggle_ba).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=4)

        tk.Button(frame, text="Hinzufügen", command=self._speichern,
                  padx=10).grid(row=5, column=0, pady=8)
        tk.Button(frame, text="Abbrechen", command=self._win.destroy,
                  padx=10).grid(row=5, column=1, pady=8)

    def _toggle_ba(self) -> None:
        """Füllt Felder mit festen Abschlussarbeit-Werten, wenn Checkbox aktiv."""
        if self._ist_ba.get():
            self._vars["name"].set("Bachelorarbeit")
            self._vars["nummer"].set("DLBABSCHLUSSB01")
            self._vars["ects"].set("12")

    def _speichern(self) -> None:
        try:
            sem_nr = int(self._vars["semester"].get())
            if self._ist_ba.get():
                modul: Modul = Abschlussarbeit()
            else:
                name = self._vars["name"].get().strip()
                nummer = self._vars["nummer"].get().strip()
                ects = int(self._vars["ects"].get())
                if not name or not nummer:
                    raise ValueError("Modulname und Modulnummer dürfen nicht leer sein.")
                if ects <= 0:
                    raise ValueError("ECTS müssen eine positive Zahl sein.")
                modul = Modul(name, nummer, ects)
            self._controller.modul_hinzufuegen(modul, sem_nr)
            self._result = modul
            self._win.destroy()
        except ValueError as exc:
            messagebox.showerror("Eingabefehler", str(exc), parent=self._win)


class NoteDialog:
    """Dialog zum Eintragen einer neuen Prüfungsleistung."""

    def __init__(self, parent: tk.Tk, controller: DashboardController) -> None:
        self._controller = controller
        self._parent = parent
        self._result: Optional[Pruefungsleistung] = None

    def note_eingeben(self) -> Optional[Pruefungsleistung]:
        """Öffnet den Dialog modal, trägt die Note ein und gibt die Prüfungsleistung zurück."""
        self._win = tk.Toplevel(self._parent)
        self._win.title("Note eintragen")
        self._win.geometry("390x230")
        self._win.resizable(False, False)
        self._baue_layout()
        self._parent.wait_window(self._win)
        return self._result

    def _baue_layout(self) -> None:
        frame = tk.Frame(self._win, padx=16, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        alle: list[tuple[str, Modul, int]] = [
            (f"Sem. {s.nummer} – {m.name}", m, s.nummer)
            for s in self._controller.aktueller_studiengang().semester
            for m in s.module
        ]
        self._modul_map: dict[str, tuple[Modul, int]] = {label: (m, nr) for label, m, nr in alle}
        labels = list(self._modul_map.keys())

        tk.Label(frame, text="Modul:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=3)
        self._modul_var = tk.StringVar(value=labels[0] if labels else "")
        # Füge einen Trace hinzu, der den Versuchszähler dynamisch berechnet sobald das Modul im Dropdown gewechselt wird
        def update_versuch(*args):
            label = self._modul_var.get()
            if label in self._modul_map:
                gewaehltes_modul = self._modul_map[label][0]
                naechster_versuch = len(gewaehltes_modul.pruefungsleistungen) + 1
                self._versuch_var.set(str(naechster_versuch))
                
        self._modul_var.trace_add("write", update_versuch)

        ttk.Combobox(frame, textvariable=self._modul_var, values=labels,
                     width=32, state="readonly").grid(row=0, column=1, sticky=tk.W)

        tk.Label(frame, text="Note (1.0 – 5.0):", anchor=tk.W).grid(
            row=1, column=0, sticky=tk.W, pady=3)
        self._note_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._note_var, width=10).grid(
            row=1, column=1, sticky=tk.W)

        tk.Label(frame, text="Datum (TT.MM.JJJJ):", anchor=tk.W).grid(
            row=2, column=0, sticky=tk.W, pady=3)
        self._datum_var = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        tk.Entry(frame, textvariable=self._datum_var, width=14).grid(
            row=2, column=1, sticky=tk.W)

        tk.Label(frame, text="Versuch:", anchor=tk.W).grid(
            row=3, column=0, sticky=tk.W, pady=3)
        # Initiale Zähler-Anzeige
        default_versuch = "1"
        if labels:
            erstes_modul = self._modul_map[labels[0]][0]
            if erstes_modul.pruefungsleistungen:
                default_versuch = str(len(erstes_modul.pruefungsleistungen) + 1)
        self._versuch_var = tk.StringVar(value=default_versuch)
        tk.Spinbox(frame, textvariable=self._versuch_var, from_=1, to=3,
                   width=5).grid(row=3, column=1, sticky=tk.W)

        tk.Button(frame, text="Eintragen", command=self._speichern,
                  padx=10).grid(row=4, column=0, pady=10)
        tk.Button(frame, text="Abbrechen", command=self._win.destroy,
                  padx=10).grid(row=4, column=1, pady=10)

    def _speichern(self) -> None:
        try:
            label = self._modul_var.get()
            if not label:
                raise ValueError("Bitte ein Modul auswählen.")
            modul, sem_nr = self._modul_map[label]
            note_str = self._note_var.get().replace(",", ".")
            if not note_str:
                raise ValueError("Bitte eine Note eingeben.")
            note = float(note_str)
            d = self._datum_var.get().strip()
            if len(d) != 10 or d[2] != "." or d[5] != ".":
                raise ValueError("Datum muss im Format TT.MM.JJJJ angegeben werden.")
            datum = date(int(d[6:10]), int(d[3:5]), int(d[0:2]))
            versuch = int(self._versuch_var.get())
            pl = Pruefungsleistung(note, datum, versuch)
            self._controller.pruefung_hinzufuegen(modul, pl)
            self._result = pl
            self._win.destroy()
        except ValueError as exc:
            messagebox.showerror("Eingabefehler", str(exc), parent=self._win)


class SemesterDialog:
    """Dialog zum Anlegen eines neuen Semesters."""

    def __init__(self, parent: tk.Tk, controller: DashboardController) -> None:
        self._controller = controller
        self._parent = parent

    def semester_anlegen(self) -> None:
        """Öffnet den Dialog modal und legt ein neues Semester an."""
        self._win = tk.Toplevel(self._parent)
        self._win.title("Neues Semester anlegen")
        self._win.geometry("380x200")
        self._win.resizable(False, False)
        self._baue_layout()
        self._parent.wait_window(self._win)

    def _baue_layout(self) -> None:
        frame = tk.Frame(self._win, padx=16, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        vorhandene = [s.nummer for s in self._controller.aktueller_studiengang().semester]
        naechste = max(vorhandene) + 1 if vorhandene else 1

        tk.Label(frame, text="Semesternummer:", anchor=tk.W).grid(
            row=0, column=0, sticky=tk.W, pady=3)
        self._nr_var = tk.StringVar(value=str(naechste))
        tk.Entry(frame, textvariable=self._nr_var, width=10).grid(
            row=0, column=1, sticky=tk.W, pady=3)

        tk.Label(frame, text="Startdatum (TT.MM.JJJJ):", anchor=tk.W).grid(
            row=1, column=0, sticky=tk.W, pady=3)
        self._start_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._start_var, width=14).grid(
            row=1, column=1, sticky=tk.W, pady=3)

        tk.Label(frame, text="Enddatum (TT.MM.JJJJ):", anchor=tk.W).grid(
            row=2, column=0, sticky=tk.W, pady=3)
        self._end_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._end_var, width=14).grid(
            row=2, column=1, sticky=tk.W, pady=3)

        tk.Button(frame, text="Anlegen", command=self._speichern,
                  padx=10).grid(row=3, column=0, pady=10)
        tk.Button(frame, text="Abbrechen", command=self._win.destroy,
                  padx=10).grid(row=3, column=1, pady=10)

    @staticmethod
    def _parse_datum(text: str) -> date:
        """Parst ein Datum im Format TT.MM.JJJJ."""
        text = text.strip()
        if len(text) != 10 or text[2] != "." or text[5] != ".":
            raise ValueError("Datum muss im Format TT.MM.JJJJ angegeben werden.")
        return date(int(text[6:10]), int(text[3:5]), int(text[0:2]))

    def _speichern(self) -> None:
        try:
            nummer = int(self._nr_var.get())
            if nummer <= 0:
                raise ValueError("Semesternummer muss positiv sein.")
            vorhandene = [s.nummer for s in self._controller.aktueller_studiengang().semester]
            if nummer in vorhandene:
                raise ValueError(f"Semester {nummer} existiert bereits.")
            start = self._parse_datum(self._start_var.get())
            ende = self._parse_datum(self._end_var.get())
            if ende <= start:
                raise ValueError("Enddatum muss nach dem Startdatum liegen.")
            self._controller.semester_anlegen(nummer, start, ende)
            self._win.destroy()
        except ValueError as exc:
            messagebox.showerror("Eingabefehler", str(exc), parent=self._win)


class DashboardApp:
    """
    Hauptfenster des Studien-Dashboards.
    Hält eine Referenz auf DashboardController und delegiert alle Daten-
    und Speicheroperationen dorthin – kennt kein Repository direkt.

    Layout orientiert sich an der Dashboard-Skizze aus Phase 1:
    - Header mit Titel und Stand-Datum
    - KPI-Leiste (4 Kacheln)
    - Semester-Navigation (◄ / ►) mit Modultabelle pro Semester
    - 4 Aktionsbuttons am unteren Rand
    """

    def __init__(self, controller: DashboardController) -> None:
        self._controller = controller
        self._root = tk.Tk()
        self._root.title("IU Studien-Dashboard")
        self._root.geometry("960x620")
        self._root.minsize(800, 520)
        self._aktuelles_semester_idx: int = 0   # Index in der Semesterliste
        self._baue_layout()

    def starten(self) -> None:
        """Startet die tkinter-Hauptschleife."""
        self._root.mainloop()

    # ── Layout-Aufbau ────────────────────────────────────────────────────────

    def _baue_layout(self) -> None:
        """Erstellt alle UI-Elemente gemäß Dashboard-Skizze Phase 1."""
        sg = self._controller.aktueller_studiengang()

        # ── Header ──────────────────────────────────────────────────────────
        header = tk.Frame(self._root, bg=_HEADER_BG, pady=10)
        header.pack(fill=tk.X)
        header.columnconfigure(0, weight=1)
        titel_frame = tk.Frame(header, bg=_HEADER_BG)
        titel_frame.pack(fill=tk.X, padx=16)
        tk.Label(titel_frame, text="IU Studien-Dashboard",
                 bg=_HEADER_BG, fg=_HEADER_FG,
                 font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(titel_frame,
                 text=f"Stand: {date.today().strftime('%d.%m.%Y')}",
                 bg=_HEADER_BG, fg=_HEADER_FG,
                 font=("Arial", 10)).pack(side=tk.RIGHT)
        tk.Label(header, text=sg.name,
                 bg=_HEADER_BG, fg=_HEADER_FG,
                 font=("Arial", 10)).pack()

        # ── KPI-Leiste ──────────────────────────────────────────────────────
        self._kpi_frame = tk.Frame(self._root, pady=8)
        self._kpi_frame.pack(fill=tk.X, padx=12)
        self._zeige_kpi_leiste()

        kpi_hinweis = tk.Label(
            self._root,
            text="KPI-Leiste: Zielkennzahlen auf einen Blick  "
                 "(grün = Ziel erreicht  |  rot = Handlungsbedarf)",
            fg="gray", font=("Arial", 8),
        )
        kpi_hinweis.pack(pady=(0, 4))

        ttk.Separator(self._root).pack(fill=tk.X, padx=8, pady=2)

        # ── Semester-Navigation ─────────────────────────────────────────────
        nav_frame = tk.Frame(self._root, pady=4)
        nav_frame.pack(fill=tk.X, padx=12)

        self._btn_prev = tk.Button(nav_frame, text="◄", font=("Arial", 14, "bold"),
                                   command=self._semester_zurueck, width=3, relief=tk.FLAT, fg="#2b7a96")
        self._btn_prev.pack(side=tk.LEFT)
        
        self._btn_next = tk.Button(nav_frame, text="►", font=("Arial", 14, "bold"),
                                   command=self._semester_vor, width=3, relief=tk.FLAT, fg="#2b7a96")
        self._btn_next.pack(side=tk.RIGHT)
        
        self._btn_del_sem = tk.Button(nav_frame, text="🗑", font=("Arial", 14),
                                      command=self._semester_loeschen, width=2, relief=tk.FLAT, fg="gray", cursor="hand2")
        self._btn_del_sem.pack(side=tk.RIGHT, padx=4)

        self._semester_label = tk.Label(nav_frame, text="",
                                        font=("Arial", 10, "bold"))
        self._semester_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ── Modultabelle ────────────────────────────────────────────────────
        tabelle_frame = tk.Frame(self._root)
        tabelle_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        cols = ("name", "ects", "note", "versuch", "status")
        self._tree = ttk.Treeview(tabelle_frame, columns=cols, show="headings")
        for col, head, w, anchor in [
            ("name",    "Modulname", 360, tk.W),
            ("ects",    "ECTS",       60, tk.CENTER),
            ("note",    "Note",       80, tk.CENTER),
            ("versuch", "Versuch",    80, tk.CENTER),
            ("status",  "Status",    140, tk.W),
        ]:
            self._tree.heading(col, text=head)
            self._tree.column(col, width=w, anchor=anchor)

        # Zeilen-Tags für Status-Farben
        for status_text, bg in _STATUS_FARBEN.items():
            tag_name = status_text.replace(" ", "_")
            self._tree.tag_configure(tag_name, background=bg)

        sb = ttk.Scrollbar(tabelle_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.bind("<Double-1>", self._oeffne_modul_dialog)
        self._tree.bind("<Delete>", lambda e: self._modul_loeschen())
        self._tree.bind("<Button-3>", self._zeige_kontextmenue)

        # Kontextmenü erstellen
        self._kontextmenue = tk.Menu(self._root, tearoff=0)
        self._kontextmenue.add_command(label="🗑 Modul löschen", command=self._modul_loeschen)

        hinweis = tk.Label(
            self._root,
            text="Modultabelle: Module des gewählten Semesters  |  Klick auf Zeile → Detailansicht mit allen Prüfungsversuchen",
            fg="gray", font=("Arial", 8, "italic"),
        )
        hinweis.pack(pady=(0, 2))

        # ── Aktionsbuttons (4 Stück, wie in der Skizze) ─────────────────────
        btn_frame = tk.Frame(self._root, pady=8)
        btn_frame.pack(fill=tk.X, padx=12)
        btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

        for i, (text, cmd) in enumerate([
            ("+ Note eintragen",    self._oeffne_note_dialog),
            ("+ Modul hinzufügen",  self._oeffne_eingabe_dialog),
            ("+ Semester anlegen",  self._oeffne_semester_dialog),
            ("Daten exportieren",   self._daten_exportieren),
        ]):
            btn = tk.Button(
                btn_frame, text=text, command=cmd,
                bg=_BTN_BG, fg=_BTN_FG, activebackground="#1e5f78",
                font=("Arial", 10, "bold"), relief=tk.FLAT,
                padx=16, pady=8, cursor="hand2",
            )
            btn.grid(row=0, column=i, padx=6, sticky="ew")
        
        navi_hinweis = tk.Label(
            self._root,
            text="Navigationsleiste: Dateneingabe und Verwaltung",
            fg="gray", font=("Arial", 8, "italic"),
        )
        navi_hinweis.pack(pady=(0, 4))

        # ── Initiale Anzeige ────────────────────────────────────────────────
        self._aktualisieren()

    # ── KPIs ─────────────────────────────────────────────────────────────────

    def _zeige_kpi_leiste(self) -> None:
        """Erzeugt oder aktualisiert die vier KPI-Kacheln."""
        for widget in self._kpi_frame.winfo_children():
            widget.destroy()

        for kpi in [
            self._controller.regelstudienzeit_kpi(),
            self._controller.notendurchschnitt_kpi(),
            self._controller.ects_soll_kpi(),
            self._controller.bestehensquote_kpi(),
        ]:
            bg_color = "#f0f8fb"  # Hellblau aus Skizze
            bar_color = "#28a745" if kpi.ziel_erreicht else "#dc3545"
            
            karte = tk.Frame(self._kpi_frame, bg=bg_color, bd=1, relief=tk.SOLID)
            karte.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
            
            # Grüner/Roter Balken oben
            tk.Frame(karte, bg=bar_color, height=6).pack(side=tk.TOP, fill=tk.X)
            
            # Inneres Layout
            inner = tk.Frame(karte, bg=bg_color, padx=10, pady=8)
            inner.pack(fill=tk.BOTH, expand=True)

            tk.Label(inner, text=kpi.titel, bg=bg_color, fg="#333333", font=("Arial", 9, "bold")).pack()
            tk.Label(inner, text=kpi.hauptwert, bg=bg_color, fg="#333333", font=("Arial", 13, "bold"), pady=8).pack()
            tk.Label(inner, text=kpi.zielhinweis, bg=bg_color, fg="#555555", font=("Arial", 9)).pack()

    # ── Semester-Navigation ──────────────────────────────────────────────────

    def _semester_liste(self) -> list[Semester]:
        """Gibt eine sortierte Kopie der Semesterliste zurück."""
        return sorted(self._controller.aktueller_studiengang().semester, key=lambda s: s.nummer)

    def _semester_zurueck(self) -> None:
        """Wechselt zum vorherigen Semester."""
        if self._aktuelles_semester_idx > 0:
            self._aktuelles_semester_idx -= 1
            self._aktualisieren()

    def _semester_vor(self) -> None:
        """Wechselt zum nächsten Semester."""
        sems = self._semester_liste()
        if self._aktuelles_semester_idx < len(sems) - 1:
            self._aktuelles_semester_idx += 1
            self._aktualisieren()

    def _aktuelles_semester(self) -> Optional[Semester]:
        """Gibt das aktuell angezeigte Semester-Objekt zurück."""
        sems = self._semester_liste()
        if not sems:
            return None
        idx = min(self._aktuelles_semester_idx, len(sems) - 1)
        self._aktuelles_semester_idx = idx
        return sems[idx]

    # ── Tabelle ──────────────────────────────────────────────────────────────

    def _zeige_modultabelle(self) -> None:
        """Befüllt die Modultabelle mit Modulen des aktuell gewählten Semesters."""
        self._tree.delete(*self._tree.get_children())
        sem = self._aktuelles_semester()
        if sem is None:
            return

        # Deutsche Monatsnamen (unabhängig von System-Locale)
        _MONATE = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
        }
        start_str = f"{_MONATE[sem.startdatum.month]} {sem.startdatum.year}"
        ende_str = f"{_MONATE[sem.enddatum.month]} {sem.enddatum.year}"
        self._semester_label.config(
            text=f"Semester {sem.nummer}  –  {start_str} bis {ende_str}"
        )

        # Navigations-Buttons aktivieren/deaktivieren
        sems = self._semester_liste()
        self._btn_prev.config(state=tk.NORMAL if self._aktuelles_semester_idx > 0 else tk.DISABLED)
        self._btn_next.config(state=tk.NORMAL if self._aktuelles_semester_idx < len(sems) - 1 else tk.DISABLED)

        for modul in sem.module:
            pls = modul.pruefungsleistungen
            # Letzte Note und letzten Versuch anzeigen (mit Komma)
            if pls:
                letzte_pl = pls[-1]
                note_text = f"{letzte_pl.note:.1f}".replace(".", ",")
                versuch = letzte_pl.versuch
            else:
                note_text = "—"
                versuch = "—"

            tag = modul.status.value.replace(" ", "_")
            self._tree.insert("", tk.END, values=(
                modul.name,
                modul.ects,
                note_text,
                versuch,
                modul.status.value,
            ), tags=(tag,))

    # ── Aktualisierung ───────────────────────────────────────────────────────

    def _aktualisieren(self) -> None:
        """Aktualisiert KPI-Leiste, Semester-Header und Tabelle."""
        self._zeige_kpi_leiste()
        self._zeige_modultabelle()

    # ── Dialoge ──────────────────────────────────────────────────────────────

    def _oeffne_modul_dialog(self, event: tk.Event) -> None:
        """Öffnet den Modul-Detaildialog bei Doppelklick auf eine Tabellenzeile."""
        auswahl = self._tree.selection()
        if not auswahl:
            return
        werte = self._tree.item(auswahl[0])["values"]
        modul_name = str(werte[0])
        sem = self._aktuelles_semester()
        if sem:
            for m in sem.module:
                if m.name == modul_name:
                    ModulDialog(self._root, self._controller).oeffnen(m)
                    self._aktualisieren()
                    return

    def _oeffne_eingabe_dialog(self) -> None:
        """Öffnet den Dialog zum Hinzufügen eines neuen Moduls."""
        sem = self._aktuelles_semester()
        sem_nr = sem.nummer if sem else 1
        EingabeDialog(self._root, self._controller, sem_nr).modul_hinzufuegen()
        self._aktualisieren()

    def _springe_zu_semester(self, nummer: int) -> None:
        """Sucht das Semester mit der Nummer und wählt es als aktuelles aus."""
        sems = self._semester_liste()
        for idx, s in enumerate(sems):
            if s.nummer == nummer:
                self._aktuelles_semester_idx = idx
                break

    def _oeffne_note_dialog(self) -> None:
        """Öffnet den Dialog zum Eintragen einer neuen Prüfungsleistung."""
        NoteDialog(self._root, self._controller).note_eingeben()
        self._aktualisieren()

    def _oeffne_semester_dialog(self) -> None:
        """Öffnet den Dialog zum Anlegen eines neuen Semesters."""
        SemesterDialog(self._root, self._controller).semester_anlegen()
        self._aktualisieren()

    def _modul_loeschen(self) -> None:
        """Löscht das ausgewählte Modul nach Bestätigung."""
        auswahl = self._tree.selection()
        if not auswahl:
            messagebox.showinfo("Hinweis",
                                "Bitte zuerst ein Modul in der Tabelle auswählen.",
                                parent=self._root)
            return
        werte = self._tree.item(auswahl[0])["values"]
        modul_name = str(werte[0])
        sem = self._aktuelles_semester()
        if sem is None:
            return
        ok = messagebox.askyesno(
            "Modul löschen",
            f"Modul \"{modul_name}\" wirklich löschen?\n"
            f"Alle Prüfungsleistungen gehen verloren.",
            parent=self._root,
        )
        if ok:
            if self._controller.modul_entfernen(sem.nummer, modul_name):
                self._aktualisieren()
            else:
                messagebox.showerror("Fehler", "Modul konnte nicht gelöscht werden.",
                                     parent=self._root)

    def _zeige_kontextmenue(self, event: tk.Event) -> None:
        """Zeigt das Rechtsklick-Kontextmenü an der Mausposition."""
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._kontextmenue.post(event.x_root, event.y_root)

    def _semester_loeschen(self) -> None:
        """Löscht das aktuell angezeigte Semester nach Bestätigung."""
        sem = self._aktuelles_semester()
        if sem is None:
            return
        ok = messagebox.askyesno(
            "Semester löschen",
            f"Semester {sem.nummer} wirklich löschen?\nAlle darin enthaltenen Module gehen verloren.",
            parent=self._root
        )
        if ok:
            if self._controller.semester_entfernen(sem.nummer):
                # Wenn wir nicht mehr auf 0 sind, eins zurückgehen, damit wir nicht auf ein out-of-bounds Semester zeigen.
                self._aktuelles_semester_idx = max(0, self._aktuelles_semester_idx - 1)
                self._aktualisieren()
            else:
                messagebox.showerror("Fehler", "Semester konnte nicht gelöscht werden.", parent=self._root)

    def _daten_exportieren(self) -> None:
        """Öffnet einen Speichern-Dialog und exportiert den Studiengang."""
        from tkinter import filedialog
        pfad = filedialog.asksaveasfilename(
            parent=self._root,
            defaultextension=".json",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialfile="studiengang_export.json",
            title="Studien-Daten exportieren"
        )
        if pfad:
            try:
                self._controller.daten_exportieren(pfad)
                messagebox.showinfo("Export erfolgreich", f"Daten erfolgreich exportiert nach:\n{pfad}", parent=self._root)
            except Exception as e:
                messagebox.showerror("Exportfehler", f"Fehler beim Exportieren:\n{e}", parent=self._root)


# ═══════════════════════════════════════════════════════════════════════════════
# EINSTIEGSPUNKT
# ═══════════════════════════════════════════════════════════════════════════════

_JSON_PFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studiengang.json")

_FALLBACK_DATEN: dict = {
    "name": "B.Sc. Angewandte Künstliche Intelligenz",
    "gesamt_ects": 180,
    "regelstudienzeit": 6,
    "semester": [
        {
            "nummer": 1,
            "startdatum": "2024-10-01",
            "enddatum": "2025-03-31",
            "module": [
                {
                    "typ": "Modul",
                    "name": "Objektorientierte und funktionale Programmierung mit Python",
                    "modulnummer": "DLBDSOOFPP01",
                    "ects": 5,
                    "status": "In Bearbeitung",
                    "pruefungsleistungen": [],
                }
            ],
        }
    ],
}


def _erstelle_fallback_json(dateipfad: str) -> None:
    """Legt eine kleine Standard-JSON-Datei an, falls noch keine Datenbasis existiert."""
    with open(dateipfad, "w", encoding="utf-8") as f:
        json.dump(_FALLBACK_DATEN, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Primär wird die externe JSON-Datei verwendet; nur wenn sie fehlt,
    # erzeugen wir eine kleine Standarddatenbasis für den Erststart.
    if not os.path.exists(_JSON_PFAD):
        _erstelle_fallback_json(_JSON_PFAD)

    repository = JSONRepository(_JSON_PFAD)
    controller = DashboardController(repository)
    controller.initialisieren()

    app = DashboardApp(controller)
    app.starten()
