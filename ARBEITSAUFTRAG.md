# Arbeitsauftrag – Dashboard Rückstandslisten

**Status:** Entwurf – vor fachlicher Finalisierung  
**Stand:** 17.09.2026

## Ziel

Eine responsive, webbasierte Anwendung erstellen, die historische tägliche Rückstandslisten aus Excel dauerhaft und nachvollziehbar auswertbar macht. In einem zweiten Schritt werden passende Auftrags- und Lieferdaten aus Microsoft Dynamics 365 Business Central ergänzt, um Warte- und Lieferzeiten zu analysieren.

## Technischer Rahmen

- Backend: FastAPI
- Seiten-Rendering: Jinja2
- Oberfläche: responsiv für Desktop und mobile Endgeräte
- Datenhaltung: relationale Datenbank, bevorzugt PostgreSQL

## Historische Quelldaten

Die Dateien liegen in einer hierarchischen Ablage:

```text
Jahr / Monat / RückständeTTMMJJ.xlsx
```

Beispiel: `Rückstände190826.xlsx` steht für den Stichtag 19.08.2026.

Der Stichtag wird verbindlich aus dem Dateinamen gewonnen, nicht aus dem Änderungsdatum der Datei.

## Import – erster Ausbauschritt

- Historische Excel-Dateien einmalig als Tages-Snapshots importieren.
- Originaldatei, Quelle, Importzeitpunkt und Importergebnis nachvollziehbar protokollieren.
- Doppelte Importe derselben Datei bzw. desselben Stichtags verhindern oder eindeutig kennzeichnen.
- Fehlerhafte oder strukturell abweichende Dateien nicht stillschweigend übernehmen, sondern im Importprotokoll ausweisen.
- Die fachlichen Spalten, Schlüssel und Bereinigungsregeln werden nach Prüfung repräsentativer Dateien verbindlich festgelegt.

## Dashboard – erster Ausbauschritt

- Übersicht über Rückstände und ihren Verlauf über die Zeit.
- Filter und Detailansichten, voraussichtlich nach Stichtag, Lieferant, Artikel, Auftrag und Status.
- Datenqualität und Verweildauer im Rückstand sichtbar machen.
- Konkrete Kennzahlen und deren Definitionen werden nach Sichtung der Daten finalisiert.

## Business-Central-Anbindung – zweiter Ausbauschritt

- Relevante Bestell-, Auftrags-, Liefer- und Positionsdaten aus Business Central anbinden.
- Zuordnung über stabile fachliche Schlüssel, bevorzugt Bestellnummer und Position; ergänzende Schlüssel werden nach Datenprüfung festgelegt.
- Kennzahl: durchschnittliche Zeit von Bestellung bis tatsächlicher Lieferung.
- Kennzahlen zu Lieferavisen und Abweichungen erst nach gemeinsamer fachlicher Definition umsetzen.

## Offene Punkte zur Finalisierung

- Finale Bewertung und Bedeutung der vorhandenen Datenfelder, insbesondere Lieferavise.
- Verbindliche Zuordnungslogik zwischen Rückstandsliste und Business Central.
- Gewünschte Kennzahlen, Filter, Rollen und Zugriffsrechte.
- Art, Berechtigung und Aktualisierungsrhythmus der Business-Central-Anbindung.
- Datenaufbewahrung und Umgang mit Korrekturen in historischen Tagesdateien.

## Nächster Schritt

Eine bzw. mehrere repräsentative Excel-Dateien prüfen. Auf Basis ihrer Tabellenblätter, Spalten, Schlüssel und Datenqualität wird dieser Arbeitsauftrag fachlich finalisiert, bevor die Implementierung startet.
