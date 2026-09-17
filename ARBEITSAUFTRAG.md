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

### Bereitzustellende OData-Entitäten

- Einkaufsbestellköpfe und Einkaufsbestellzeilen
- Einkaufslieferköpfe und Einkaufslieferzeilen
- Verkaufsauftragsköpfe und Verkaufsauftragszeilen
- Einlagerungsköpfe und Einlagerungszeilen

### Einrichtungsseite für Business Central

Die Anwendung erhält eine geschützte Einrichtungsseite, über die eine berechtigte Person die Verbindung einmalig hinterlegt und später ändern kann. Vorgesehen sind:

- Business-Central-Server bzw. Basis-URL
- Mandant
- die OData-URL je bereitgestellter Entität
- optional Gesellschaft bzw. Company, sofern sie Bestandteil der OData-Adressierung ist
- Verbindungstest mit einer nicht verändernden Abfrage
- Anzeige des letzten erfolgreichen Abrufs und eventueller Fehler

Die OData-Abfragen erfolgen serverseitig. Als Verfahren ist Windows-Authentifizierung vorgesehen. Benutzernamen, Kennwörter oder vergleichbare Geheimnisse werden nicht im Klartext in der Datenbank gespeichert, sondern über eine geschützte Server-Konfiguration bzw. einen Secret-Speicher bereitgestellt. Die Einrichtungsseite speichert ausschließlich die fachliche Verbindungs- und URL-Konfiguration.

## Fachliche Zielrichtung

### Rückstandsüberwachung und historische KPIs

- Entwicklung und Dauer von Rückständen über die Zeit überwachen.
- Kennzahlen nach Hersteller, Fahrzeugmodell, Teilegruppe und Debitor bereitstellen.
- Besonders lange und stark belastete Vorgänge sichtbar machen, einschließlich Top-5-Listen.
- Lagerware und direkte Kundenbestellungen getrennt analysieren.
- Trends bei Wartezeiten erkennen, insbesondere Zu- oder Abnahmen je Teilegruppe und Hersteller.

### Liefertermin, Avis und tatsächliche Erfüllung

- Voraussichtlichen Liefertermin aus `Liefertermin` und Hinweise aus `Bemerkung OTLG` mit tatsächlichem Wareneingang und tatsächlicher Kundenauslieferung vergleichen.
- Lieferantenhinweise fachlich klassifizieren, etwa konkretes Datum, Kalenderwochen-Avis, Versandhinweis oder keine belastbare Aussage.
- Termintreue und Abweichung in Tagen je Hersteller bzw. Lieferant messen.
- Regeln für Folgeprozesse erst nach gemeinsamer fachlicher Bewertung dieser Klassifizierung festlegen.

### Operative Erkennung und Kommunikation

- Einlagerungen überwachen und erkennen, wenn ein rückständiger Kundenauftrag auf die eingegangene Artikelnummer wartet.
- Daraus eine prüfbare Aufgabe oder einen Auslöser für die Disposition ableiten.
- Später kontrolliert Business-Central-Datensätze anlegen und E-Mails an zuständige Disponenten versenden.

## Offene Punkte zur Finalisierung

- Finale Bewertung und Bedeutung der vorhandenen Datenfelder, insbesondere Lieferavise.
- Verbindliche Zuordnungslogik zwischen Rückstandsliste und Business Central.
- Gewünschte Kennzahlen, Filter, Rollen und Zugriffsrechte.
- Art, Berechtigung und Aktualisierungsrhythmus der Business-Central-Anbindung.
- Datenaufbewahrung und Umgang mit Korrekturen in historischen Tagesdateien.

## Nächster Schritt

Eine bzw. mehrere repräsentative Excel-Dateien prüfen. Auf Basis ihrer Tabellenblätter, Spalten, Schlüssel und Datenqualität wird dieser Arbeitsauftrag fachlich finalisiert, bevor die Implementierung startet.
