# Rueckstandslisten

FastAPI-/Jinja2-Anwendung für die spätere Auswertung von Rückstandslisten und den lesenden Zugriff auf Microsoft Dynamics 365 Business Central per OData V4.

## Start

1. `python -m pip install -r requirements.txt`
2. `.env.example` als `.env` kopieren und für den geschützten Verwaltungsbereich `ADMIN_USERNAME` sowie ein starkes `ADMIN_PASSWORD` setzen.
3. `python -m uvicorn app.main:app --reload`
4. Dashboard: `http://127.0.0.1:8000`; Abfrage: `/odata/query`; Verwaltung: `/admin/odata`.

## OData

Beim ersten Start importiert die Anwendung die Tabelle `Adressen` aus `C:\Users\radke2\Documents\ODATA.xlsx` in die separate Tabelle `odata_services`. Alle 123 vollständigen Dienstadressen bleiben dadurch direkt verwendbar; Basis-URL, Mandant und Company werden nicht separat erzeugt oder gepflegt.

Der Backend-Zugriff nutzt Windows Integrated Authentication (SSPI) unter dem Konto, das Uvicorn/FastAPI startet. Es gibt keine BC-Benutzer- oder Passwortfelder. Abfragen unterstützen freie Parameter sowie `$filter`, `$select` und `$expand`; der Test liest nur `$top=1`.
