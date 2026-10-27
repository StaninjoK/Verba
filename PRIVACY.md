# Datenschutz und Datenverarbeitung

Dieses Dokument beschreibt, wie die **lokale Version** von Verba mit Daten umgeht. Es ist keine Datenschutzerklärung für einen öffentlichen Dienst und keine Aussage zur DSGVO-Konformität – dafür wäre eine rechtliche Prüfung nötig.

## Was verarbeitet wird

| Daten | Wo | Wie lange |
|---|---|---|
| Hochgeladene Audio-/Videodatei | `data/uploads/<zufällige-id>.<ext>` | bis du das Projekt löschst |
| Original-Dateiname, Titel, Metadaten (Dauer, Codec, Größe, SHA-256-Prüfsumme) | `data/verba.sqlite3` | bis du das Projekt löschst |
| Transkript (Abschnitte mit Zeitstempeln, deine Bearbeitungen) | `data/verba.sqlite3` | bis du das Projekt löschst |
| Temporäre WAV-Datei während der Transkription | `data/tmp/` | wird nach jedem Auftrag gelöscht; Reste nach Abstürzen beim nächsten Start bzw. nach 1 Stunde |
| Abgebrochene Uploads | `data/tmp/upload-*.part` | sofort gelöscht |
| Ungespeicherte Editor-Änderungen | `localStorage` deines Browsers | bis sie gespeichert oder verworfen werden |
| Einstellungen (Sprache, Design) | `localStorage` deines Browsers | dauerhaft, bis du sie löschst |

## Was nicht passiert

- Keine Übertragung von Dateien oder Transkripten an Dritte oder an Cloud-Dienste.
- Keine Analyse-, Tracking- oder Werbedienste, keine Cookies.
- Keine externen Schriftarten oder Skripte (alles lokal gebündelt).
- Keine Transkripttexte oder Dateinamen in den Logs.
- Whisper läuft vollständig offline, sobald das Modell heruntergeladen ist.

## Lokal oder extern?

Die Oberfläche zeigt im Kopfbereich und in der Seitenleiste, dass lokal verarbeitet wird. Jede Engine meldet `sends_data_externally`. Der einzige externe Adapter ist deaktiviert und sendet nichts, selbst wenn er konfiguriert würde. Sollte künftig eine Cloud-Engine eingebaut werden, muss sie ausdrücklich eingeschaltet werden und in der Oberfläche sichtbar als extern gekennzeichnet sein.

## Löschen

- **Ein Projekt:** Bibliothek → „…“ → „Löschen“ → bestätigen. Datei und Datenbankeintrag werden sofort entfernt. Es gibt keinen Papierkorb und keine automatische Löschung.
- **Alles:** Backend stoppen, Ordner `backend/data/` (bzw. `VERBA_DATA_DIR`) löschen; im Browser die Website-Daten für `localhost:3000` löschen.
- SQLite gibt gelöschten Platz nicht sofort an das Dateisystem zurück. Für eine gründliche Bereinigung: `sqlite3 backend/data/verba.sqlite3 "VACUUM;"`.

Verba löscht Nutzerdaten nie stillschweigend. Nur eindeutig temporäre Dateien werden automatisch entfernt. Upload-Dateien ohne Datenbankeintrag (z. B. nach einem Absturz) werden **nicht** automatisch gelöscht, sondern unter `/api/system` als `orphan_files` gemeldet.

## Vor einem öffentlichen Angebot nötig

Datenschutzerklärung, Auftragsverarbeitungsverträge mit allen Dienstleistern, Verzeichnis der Verarbeitungstätigkeiten, Lösch- und Aufbewahrungsfristen, Auskunfts- und Löschprozesse für Betroffene, ggf. Datenschutz-Folgenabschätzung bei sensiblen Aufnahmen. Siehe [docs/ROADMAP.md](docs/ROADMAP.md).
