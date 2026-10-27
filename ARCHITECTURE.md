# Architektur

```
Browser ──HTTP──▶ Next.js 16 (React 19, TypeScript)  :3000
   │                 Landingpage "/", Bibliothek "/app", Arbeitsbereich "/app/projects/[id]"
   │
   └──HTTP (CORS, nur erlaubte Origins)──▶ FastAPI  127.0.0.1:8000
                                             │
                     ┌───────────────────────┼─────────────────────────┐
                     ▼                       ▼                         ▼
               SQLite (WAL)          Dateisystem (data/)        JobManager (Threads)
          projects, jobs          uploads/, tmp/              │
                                                              ▼
                                                   ProviderRegistry
                                       faster-whisper │ openai-whisper │ mock │ external-api (aus)
```

## Ordner

| Pfad | Zweck |
|---|---|
| `backend/verba/config.py` | Einstellungen aus Umgebungsvariablen |
| `backend/verba/db.py` | SQLite-Schema, Zustandsautomat der Aufträge, optimistische Versionierung |
| `backend/verba/storage.py` | sichere Dateinamen, Pfad-Eingrenzung, Aufräumen |
| `backend/verba/media.py` | Signaturprüfung, `ffprobe`-Analyse, Umwandlung nach 16 kHz Mono-WAV |
| `backend/verba/providers/` | Provider-Schnittstelle und Engines |
| `backend/verba/jobs.py` | Hintergrund-Worker, Wiederholung, Timeout, Abbruch, Wiederanlauf |
| `backend/verba/exports.py` | TXT, SRT, VTT, DOCX |
| `backend/verba/api.py` | HTTP-Endpunkte, Sicherheits-Header |
| `frontend/src/app/` | Seiten (App Router) und CSS |
| `frontend/src/components/app/` | Upload, Bibliothek, Auftragsanzeige, Editor |
| `frontend/src/components/landing/` | Landingpage |
| `frontend/src/lib/` | API-Client, Formatierung, Übersetzungen |

## Datenfluss

1. **Upload** – Der Browser sendet die Datei als Rohdaten (`POST /api/projects`, Header `X-Verba-Filename`). Das Backend schreibt sie in Blöcken nach `data/tmp/`, bricht beim Überschreiten des Limits sofort ab und berechnet dabei SHA-256.
2. **Prüfung** – Endung erlaubt? Signatur passt zur Endung? `ffprobe` bestätigt Format, Tonspur und Dauer? Erst dann bekommt die Datei einen zufälligen Namen (`<uuid>.<ext>`) in `data/uploads/` und einen Projekteintrag. Gleiche Dateien werden als Duplikat gemeldet.
3. **Auftrag** – `POST /api/projects/{id}/transcribe` legt einen Auftrag `pending` an. Pro Projekt kann nur ein aktiver Auftrag existieren (Schutz vor Doppelklicks, in einer Transaktion geprüft).
4. **Worker** – Ein Dispatcher-Thread startet bis zu `VERBA_MAX_CONCURRENT_JOBS` Aufträge. Ablauf: `validating` (erneute Prüfung, Umwandlung zu WAV) → `processing` (Engine) → `completed` bzw. `failed`/`cancelled`.
5. **Ergebnis** – Nur wenn die Engine mindestens einen nicht-leeren Abschnitt liefert und dieser gespeichert wurde, wird der Auftrag `completed`. Die temporäre WAV-Datei wird immer gelöscht.
6. **Editor** – Das Frontend fragt den Auftrag jede Sekunde ab. Änderungen werden ~0,9 s nach der letzten Eingabe mit `PUT /api/projects/{id}/transcript` gespeichert. Die Versionsnummer verhindert, dass ältere Stände neuere überschreiben (HTTP 409). Nur der Text ändert sich – Zeitstempel bleiben so, wie die Engine sie geliefert hat.

## Zustandsautomat der Aufträge

```
pending ──▶ validating ──▶ processing ──▶ completed
   │            │   ▲           │   ▲
   │            │   └─(Wiederanlauf / Wiederholung)
   ▼            ▼               ▼
cancelled    failed/cancelled  failed/cancelled
```

Ungültige Übergänge werfen `InvalidTransition`. Beim Start setzt `JobManager.recover()` hängengebliebene Aufträge auf `pending` zurück (bis `VERBA_MAX_JOB_ATTEMPTS`) oder markiert sie als `failed` (`interrupted`).

## Provider-Schnittstelle

`TranscriptionProvider` (in `providers/base.py`):

| Methode / Feld | Bedeutung |
|---|---|
| `capabilities()` | Verfügbarkeit, Grund falls nicht verfügbar, Modell, Spracherkennung, Fortschritt, Abbruch, `is_mock`, `sends_data_externally` – ohne Netzwerkzugriff |
| `is_available()` | Kurzform |
| `validate_input(path)` | Eingabe prüfen |
| `transcribe(path, language, duration_seconds, on_progress, should_cancel)` | liefert `TranscriptionResult(segments, language, provider, model, is_mock)` |
| `ProviderError(code, message, retryable)` | strukturierte Fehler |

Regeln:

- `auto` wählt nur **lokale echte** Engines. Gibt es keine, kommt ein klarer Fehler – nie still die Test-Engine und nie eine Cloud-API.
- Schlägt die gewählte Engine fehl, gibt es **keinen Wechsel** zu einer anderen Engine.
- Fortschritt wird nur gemeldet, wenn die Engine ihn wirklich kennt (faster-whisper: Ende des letzten Abschnitts / Gesamtdauer). Sonst zeigt die Oberfläche einen unbestimmten Balken.
- Ergebnisse der Test-Engine tragen `is_mock = true`; jeder Abschnitt beginnt mit `[MOCK]`, und die Oberfläche zeigt ein Warnbanner und das Abzeichen „Testdaten“.
- `ExternalAPIProvider` ist ein Platzhalter ohne HTTP-Client. Er ist nie verfügbar und wirft immer `provider_disabled`.

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/health` | Lebenszeichen |
| GET | `/api/system` | Engines, Limits, Speicherbelegung, Sprachen |
| GET | `/api/projects?q=` | Liste/Suche |
| POST | `/api/projects` | Upload |
| GET/PATCH/DELETE | `/api/projects/{id}` | Details / Umbenennen / Löschen |
| POST | `/api/projects/{id}/transcribe` | Auftrag starten |
| GET | `/api/jobs/{id}` | Auftragsstatus |
| POST | `/api/jobs/{id}/cancel` | Abbrechen |
| PUT | `/api/projects/{id}/transcript` | Bearbeitungen speichern (versioniert) |
| GET | `/api/projects/{id}/export?format=txt\|srt\|vtt\|docx\|json&timestamps=` | Export |
| GET | `/api/projects/{id}/media` | Originaldatei für die Wiedergabe (mit Range-Unterstützung) |

## Bewusste Entscheidungen

- **SQLite + Threads statt Redis/Celery:** keine zusätzlichen Dienste, ausreichend für einen lokalen Nutzer, Zustand überlebt Neustarts.
- **Roh-Upload statt Multipart:** Größenlimit greift schon während des Streams, keine Zwischenspeicherung im System-Temp.
- **DOCX ohne Zusatzbibliothek:** minimales, gültiges Office-Open-XML mit der Standardbibliothek.
- **Kein Next.js-Proxy für Uploads:** Der Browser spricht direkt mit der API (CORS), damit große Dateien nicht durch das Body-Limit des Proxys laufen. Für ein Hosting hinter einem Reverse-Proxy wird `NEXT_PUBLIC_API_URL=""` (gleiche Herkunft) gesetzt.
