# Kosten

## Heute: 0 €

Für diese Version wurde **nichts gekauft, abonniert, freigeschaltet oder veröffentlicht**. Alle Bestandteile sind kostenlos und unter freien Lizenzen:

| Bestandteil | Lizenz |
|---|---|
| Next.js, React | MIT |
| FastAPI, Uvicorn, Starlette, Pydantic | MIT / BSD |
| Inter, Instrument Serif (über Fontsource, lokal gebündelt) | SIL Open Font License |
| FFmpeg | LGPL/GPL (als separates Programm aufgerufen, nicht eingebunden) |
| faster-whisper (optional) | MIT |
| Whisper-Modelle (optional) | MIT |
| Playwright (nur Tests) | Apache 2.0 |

Lokale Ressourcen statt Geld: Speicherplatz (siehe unten), Strom und Rechenzeit.

## Lokaler Ressourcenbedarf

| Was | Größe |
|---|---|
| `frontend/node_modules` | ca. 490 MB |
| `backend/.venv` (ohne Whisper) | ca. 40 MB |
| faster-whisper + Abhängigkeiten | ca. 100 MB (Schätzung) |
| Whisper-Modell `base` / `small` / `medium` / `large-v3` | ca. 145 MB / 465 MB / 1,5 GB / 3 GB |
| Deine Aufnahmen | so groß wie die Dateien selbst |

Arbeitsspeicher während der Transkription (faster-whisper, int8, CPU), grobe Schätzung: `base` unter 1 GB, `small` ca. 1–2 GB, `large-v3` ca. 3–5 GB.

## Mögliche künftige Kosten (Schätzungen – vor jeder Entscheidung aktuell prüfen)

Keiner dieser Posten ist aktiv. Preise ändern sich; die Angaben sind **nur Größenordnungen** und müssen vor einer Freigabe beim Anbieter geprüft werden.

| Posten | Wofür | Größenordnung |
|---|---|---|
| Domain / Subdomain | Öffentliche Adresse | Subdomain einer vorhandenen Domain: meist 0 €; neue Domain ca. 10–20 €/Jahr |
| Kleiner Cloud-Server (CPU) | Hosting von Frontend + Backend + Whisper `base`/`small` | ca. 5–20 €/Monat; Transkription langsam, nur für wenige Nutzer |
| GPU-Server | Schnelle Transkription mit großen Modellen | ca. 0,30–2 €/Stunde bzw. mehrere hundert €/Monat im Dauerbetrieb |
| Cloud-Transkriptions-API | Statt eigener Rechenleistung | typischerweise Bruchteile eines Cents bis wenige Cent pro Audiominute |
| Objektspeicher + Backups | Nutzerdateien in der Cloud | wenige Cent pro GB und Monat, plus Datenverkehr |
| E-Mail-Versand | Konten, Passwort-Reset | oft kostenloses Kontingent, danach nutzungsabhängig |
| Zahlungsanbieter | Abonnements | prozentuale Gebühr pro Zahlung |
| Monitoring / Fehlertracking | Betrieb | kostenlose Stufen vorhanden, danach nutzungsabhängig |
| Rechtliches | Markenprüfung, Datenschutzerklärung, AGB | einmalig, stark abhängig vom Umfang |

## Kostenkontrollen im Code

- Externe Engines sind **standardmäßig aus** (`VERBA_EXTERNAL_PROVIDERS_ENABLED=false`) und müssen ausdrücklich in `VERBA_ALLOWED_PROVIDERS` stehen.
- Fehlen Zugangsdaten oder die Freigabe, schlägt der Aufruf **geschlossen** fehl.
- Kein automatischer Wechsel zu einer kostenpflichtigen Engine, wenn die lokale Verarbeitung scheitert.
- Limits für Upload-Größe, Gesamtspeicher, Dauer, parallele Aufträge und Laufzeit.
- Keine nutzungsabhängigen Dienste, keine Analyse- oder Abrechnungsbibliotheken.

## Hinweis zum vorhandenen Guthaben

Ein vorhandenes Anbieter-Guthaben (z. B. 100 USD) wurde **nicht** verwendet. Bevor es eingesetzt wird, muss geklärt sein, bei welchem Anbieter es liegt, was nach Verbrauch des Guthabens automatisch berechnet würde und wie ein hartes Ausgabenlimit gesetzt werden kann. Siehe [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
