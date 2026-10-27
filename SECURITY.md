# Sicherheit

Verba ist in dieser Version eine **lokale Einzelplatz-Anwendung**. Die Maßnahmen unten sind umgesetzt und größtenteils durch automatische Tests abgedeckt. Eine unabhängige Sicherheitsprüfung hat **nicht** stattgefunden. Die App ist **nicht** für den öffentlichen Betrieb freigegeben.

## Umgesetzt

| Bereich | Maßnahme | Test |
|---|---|---|
| Netzwerk | Backend bindet standardmäßig nur an `127.0.0.1` | – |
| CORS | Nur konfigurierte Origins (`VERBA_CORS_ORIGINS`), keine Credentials | `test_security_headers_and_cors` |
| Header | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, restriktive CSP für API-Antworten, `Cache-Control: no-store` | ✅ |
| Dateinamen | Nutzer-Dateinamen werden nur angezeigt (bereinigt: Pfadanteile, Steuer- und Bidi-Zeichen entfernt). Gespeichert wird unter `<uuid>.<ext>` | `test_path_traversal_*`, `test_safe_display_name` |
| Pfade | Jeder Dateizugriff läuft über `confined_path()`, das nur `^[0-9a-f]{32}\.[a-z0-9]{1,5}$` innerhalb des Upload-Ordners erlaubt | `test_confined_path_blocks_traversal` |
| IDs | Projekt- und Auftrags-IDs werden gegen ein festes Format geprüft, bevor sie die Datenbank erreichen | `test_invalid_ids_are_404` |
| Upload-Inhalt | Dreifache Prüfung: erlaubte Endung, passende Dateisignatur, passende `ffprobe`-Formatkennung. Textdateien, Playlists (`.m3u8`), ausführbare Dateien werden abgewiesen | `test_fake_audio_*`, `test_extension_must_match_content`, `test_sniffing` |
| FFmpeg | Aufruf ohne Shell, mit `-protocol_whitelist file`, Präfix `file:` und Timeouts – keine Netzwerkzugriffe durch präparierte Container | – |
| Ausführung | Hochgeladene Dateien werden nie ausgeführt | – |
| Limits | Upload-Größe (Abbruch während des Streams), Gesamtspeicher, maximale Dauer, parallele Aufträge, Auftrags-Timeout | `test_upload_size_limit`, `test_storage_limit`, `test_too_long_recording_rejected` |
| Header-Injection | Download-Dateinamen sind ASCII-bereinigt; zusätzlich RFC 5987 `filename*` | `test_export_filename_is_safe` |
| Export | VTT-Cues können durch `-->` im Text nicht aufgebrochen werden | `test_exports_skip_empty_segments_and_fix_zero_length` |
| SQL | Nur parametrisierte Abfragen; `LIKE`-Platzhalter in der Suche werden maskiert | `test_search_matches_transcript_text_and_escapes_wildcards` |
| Logs | Nur IDs, Status und Fehlercodes – keine Transkripttexte, keine Original-Dateinamen | `test_logs_do_not_contain_transcript_or_filename` |
| Geheimnisse | Keine Schlüssel im Code; `.env` ist in `.gitignore`; `.env.example` enthält nur Platzhalter | – |
| Externe Dienste | Standardmäßig aus; Adapter ohne HTTP-Client, schlägt immer geschlossen fehl | `test_external_provider_*` |
| Frontend | React-Escaping (kein `dangerouslySetInnerHTML` außer dem festen Theme-Skript), Sicherheits-Header über `next.config.ts`, keine externen Skripte, Schriften lokal gebündelt | – |
| Abhängigkeiten | `npm audit`: 0 bekannte Schwachstellen zum Zeitpunkt der Erstellung (Next 16.4.3, React 19.2.9) | – |

## Bekannte Grenzen

- **Keine Authentifizierung oder Autorisierung.** Jeder, der `127.0.0.1:8000` erreicht, kann alle Projekte lesen und löschen. Auf einem Mehrbenutzer-Rechner können andere lokale Nutzer zugreifen.
- **Kein Rate-Limiting.**
- **Keine Verschlüsselung der gespeicherten Daten** – Schutz nur über die Dateirechte des Betriebssystems bzw. Festplattenverschlüsselung.
- **Kein CSRF-Schutz** im klassischen Sinn; abgemildert durch die CORS-Allowlist und dadurch, dass schreibende Anfragen JSON bzw. einen eigenen Header benötigen.
- FFmpeg verarbeitet nicht vertrauenswürdige Mediendateien. FFmpeg aktuell halten.
- Der Thread-basierte Timeout ist kooperativ. `openai-whisper` kann nicht mitten in der Berechnung gestoppt werden.

## Vor einem öffentlichen Start zwingend erforderlich

1. Authentifizierung (Konten oder mindestens vorgeschalteter Zugangsschutz) und Autorisierung pro Projekt
2. Mandantentrennung in Datenbank und Dateispeicher
3. Rate-Limiting und Missbrauchsschutz (Upload-Volumen, Auftragsanzahl pro Nutzer)
4. HTTPS, HSTS, sichere Cookies
5. Verarbeitung der Medien in isolierten Prozessen/Containern mit Ressourcenlimits
6. Verschlüsselter Speicher, Backups, Löschkonzept
7. Abhängigkeits-Updates und Schwachstellen-Scans im CI
8. Externe Sicherheitsprüfung (Penetrationstest)

## Sicherheitsprobleme melden

Bitte nicht öffentlich als Issue. Direkt an den Projektinhaber wenden.
