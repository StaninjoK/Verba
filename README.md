# Verba

Verba wandelt Audio- und Videodateien in bearbeitbare Transkripte und Untertitel um. Die Verarbeitung läuft **lokal auf deinem eigenen Computer**: kein Konto, keine Cloud-Datenbank, keine kostenpflichtige API.

> **Arbeitstitel:** „Verba“ ist ein vorläufiger Name. Vor einem kommerziellen Start müssen Marke, Domain und Namensrechte geprüft werden (siehe [docs/ROADMAP.md](docs/ROADMAP.md)).

## Was funktioniert (Stand dieser Version)

| Funktion | Status |
|---|---|
| Landingpage (DE/EN/ES, Hell/Dunkel, responsiv) | ✅ fertig |
| Upload per Drag & Drop oder Dateiauswahl, mit echtem Upload-Fortschritt | ✅ fertig |
| Prüfung von Endung, Dateiinhalt (Signatur) und Medienstruktur (ffprobe) | ✅ fertig |
| Anzeige der Metadaten (Dauer, Größe, Typ, Codec) | ✅ fertig |
| Hintergrund-Aufträge mit Status: Warteschlange → Vorbereitung → Transkription → Fertig/Fehler/Abgebrochen | ✅ fertig |
| Abbrechen, automatische Wiederholung, Wiederaufnahme nach Neustart | ✅ fertig |
| **Echte Transkription mit lokalem Whisper** | ⚙️ Code fertig, **Engine noch nicht installiert** (siehe unten) |
| Test-Engine („Mock“) zum Ausprobieren, deutlich als *Testdaten* markiert | ✅ fertig |
| Editor: Abschnitte bearbeiten, automatisch speichern, Wiederherstellen ungespeicherter Änderungen | ✅ fertig |
| Suche im Transkript mit Hervorhebung, Wiedergabe mit Mitlauf, Klick auf Zeitstempel | ✅ fertig |
| Export: TXT, TXT mit Zeitstempeln, SRT, VTT, DOCX, JSON | ✅ fertig |
| Bibliothek: öffnen, umbenennen, durchsuchen (Titel + Transkripttext), löschen | ✅ fertig |
| Oberfläche in Deutsch, Englisch, Spanisch | ✅ fertig |
| Benutzerkonten, Cloud-Speicher, Bezahlung, öffentliches Hosting | ❌ bewusst nicht enthalten |
| Cloud-Transkriptions-API | ❌ nur deaktivierter Platzhalter, sendet nichts |

## Voraussetzungen

- **Node.js** 20 oder neuer (getestet mit 22)
- **Python** 3.10 oder neuer (getestet mit 3.13)
- **FFmpeg** (enthält `ffprobe`)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`

Alles davon ist kostenlos.

## Installation

```bash
npm run setup
```

Das legt `backend/.venv` an, installiert die Python-Pakete (ca. 40 MB) und die Frontend-Pakete (ca. 490 MB in `frontend/node_modules`). Whisper und Modelle werden dabei **nicht** installiert.

Manuell geht es auch so:

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cd ../frontend && npm install
```

## Starten

```bash
npm run dev
```

- App: <http://localhost:3000> (Landingpage) und <http://localhost:3000/app> (Bibliothek)
- API: <http://127.0.0.1:8000/api/health>, API-Doku unter <http://127.0.0.1:8000/api/docs>

Produktionsmodus lokal: `npm start` (baut das Frontend und startet beides).

Einzeln:

```bash
cd backend && .venv/bin/python -m verba.main          # API auf 127.0.0.1:8000
cd frontend && npm run dev                             # Web auf :3000
```

## Echte Transkription aktivieren (lokales Whisper)

Hinweis: Ein Whisper, das „normal“ auf dem PC installiert ist (System-Python), sieht Verba nicht automatisch – Verba nutzt die eigene Umgebung `backend/.venv`. `npm run doctor` zeigt, was vorhanden ist und was zu tun ist.

Ohne Whisper zeigt die App „Nur Testmodus“ und du kannst den Ablauf mit der Test-Engine ausprobieren. Für echte Transkripte:

0. Prüfen, was schon da ist: `npm run doctor` (installiert nichts, zeigt vorhandene Whisper-Engines und Modelle)
1. Engine installieren (ca. 450 MB Pakete, gemessen): `backend/.venv/bin/pip install -r backend/requirements-whisper.txt`
2. Ein Modell einmalig herunterladen (z. B. `base`, ca. 145 MB)
3. Backend neu starten – oben rechts erscheint „Lokale Engine bereit“.

Die genaue Anleitung mit Modellgrößen und Hardware-Hinweisen steht in **[docs/WHISPER_SETUP.md](docs/WHISPER_SETUP.md)**.

## Unterstützte Formate

MP3, WAV, M4A, MP4, MOV, OGG/OGA/Opus, FLAC, WebM – sofern die Datei eine Tonspur enthält. Jede Datei wird dreifach geprüft: Endung, Dateisignatur und FFmpeg-Analyse. Standardlimits: 500 MB pro Datei, 240 Minuten Länge, 10 GB Gesamtspeicher (einstellbar in `.env`).

## Wo liegen meine Daten?

Standardmäßig in `backend/data/` (änderbar mit `VERBA_DATA_DIR`):

| Pfad | Inhalt |
|---|---|
| `backend/data/verba.sqlite3` | Projekte, Aufträge, Transkripte |
| `backend/data/uploads/` | Hochgeladene Originaldateien (zufällige Dateinamen) |
| `backend/data/tmp/` | Temporäre Dateien während der Verarbeitung (werden automatisch aufgeräumt) |

**Sichern:** Backend stoppen und den Ordner `backend/data/` kopieren.
**Alles löschen:** Backend stoppen und `backend/data/` löschen.
**Einzelnes Projekt löschen:** in der Bibliothek über „…“ → „Löschen“. Datei und Transkript werden sofort endgültig entfernt. Es gibt keinen Papierkorb.

Ungespeicherte Editor-Änderungen liegen zusätzlich kurzzeitig im `localStorage` des Browsers, bis sie gespeichert sind.

## Konfiguration

Kopiere `.env.example` nach `.env` im Repository-Hauptordner. Alle Optionen sind dort erklärt. Für das Frontend: `frontend/.env.local` mit `NEXT_PUBLIC_API_URL`.

## Tests

```bash
npm test            # Backend (pytest) + Frontend (Typecheck, Lint, Unit-Tests)
npm run test:e2e    # Browser-Tests mit Playwright (startet Backend + Frontend selbst)
```

Details und die zuletzt ausgeführten Ergebnisse: [TESTING.md](TESTING.md).

## Bekannte Einschränkungen

- Echte Transkription erfordert die manuelle Installation von Whisper und einem Modell.
- Auf CPU ohne Grafikkarte ist Whisper deutlich langsamer als in Cloud-Diensten; große Modelle sind für lange Aufnahmen auf schwachen Rechnern kaum praktikabel.
- Zeitstempel gibt es pro Abschnitt (Segment), nicht pro Wort.
- Beim Abbrechen mit der `openai-whisper`-Engine läuft die Berechnung bis zum Ende weiter; das Ergebnis wird dann verworfen. `faster-whisper` stoppt sofort.
- Keine Benutzerkonten und keine Zugriffskontrolle: Die App ist für **einen Nutzer auf dem eigenen Rechner** gedacht und lauscht nur auf `127.0.0.1`. Nicht ungeschützt ins Internet stellen (siehe [SECURITY.md](SECURITY.md) und [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)).
- Keine Sprecher-Erkennung (Diarisierung), keine Übersetzung.

## Weitere Dokumente

- [ARCHITECTURE.md](ARCHITECTURE.md) – Aufbau, Datenfluss, Provider-Schnittstelle
- [SECURITY.md](SECURITY.md) – Sicherheitsmaßnahmen und offene Punkte
- [PRIVACY.md](PRIVACY.md) – Datenverarbeitung und Aufbewahrung
- [COSTS.md](COSTS.md) – Kosten jetzt und mögliche künftige Kosten
- [TESTING.md](TESTING.md) – Teststrategie und Ergebnisse
- [docs/WHISPER_SETUP.md](docs/WHISPER_SETUP.md) – Whisper und Modelle einrichten
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) – Docker/Spaceship-Hyperlift-Anleitung für die Subdomain (vorbereitet, noch nicht ausgeführt)
- [docs/ROADMAP.md](docs/ROADMAP.md) – kommerzieller Fahrplan (Stufen A–G)
