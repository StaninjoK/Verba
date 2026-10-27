# Tests

## Befehle

```bash
npm test             # alles außer Browser-Tests
npm run test:backend # pytest
npm run test:frontend# TypeScript-Prüfung, ESLint, Unit-Tests (node --test)
npm run test:e2e     # Playwright: startet Backend + Frontend, falls nicht laufend
```

Alle Testdateien (Ton, Video, kaputte und gefälschte Dateien) werden lokal mit FFmpeg erzeugt. Es werden keine Aufnahmen heruntergeladen oder hochgeladen.

## Ergebnisse (zuletzt ausgeführt am 27.10.2026)

| Suite | Ergebnis |
|---|---|
| Backend `pytest` | **62 bestanden**, 0 fehlgeschlagen |
| Frontend `tsc --noEmit` | ohne Fehler |
| Frontend `eslint .` | ohne Fehler |
| Frontend Unit-Tests (`node --test`) | **7 bestanden** |
| Playwright E2E (Chromium Desktop + Pixel 7) | **6 bestanden** |
| `next build` (Produktions-Build) | erfolgreich |
| `npm audit` | 0 bekannte Schwachstellen |

## Was abgedeckt ist

| Anforderung | Tests |
|---|---|
| Dateiprüfung (MP3, WAV, M4A, MP4) | `test_uploads.py::test_valid_uploads_accepted` |
| Ungültige und nicht unterstützte Uploads | `test_unsupported_extension_rejected`, `test_fake_audio_rejected_by_content`, `test_extension_must_match_content`, `test_corrupted_file_rejected`, `test_video_without_audio_rejected`, `test_empty_upload_rejected`, E2E `invalid files are rejected` |
| Upload-Größen- und Speicherlimit | `test_upload_size_limit`, `test_storage_limit`, `test_too_long_recording_rejected` |
| Sichere Dateinamen und Pfade | `test_path_traversal_filename_is_neutralised`, `test_unicode_and_control_chars_in_filename`, `test_confined_path_blocks_traversal`, `test_safe_display_name`, `test_download_filename`, `test_invalid_ids_are_404` |
| Zustandsübergänge der Aufträge | `test_state_machine_rejects_invalid_transitions`, `test_recovery_after_restart`, `test_recovery_gives_up_after_attempt_limit`, `test_background_worker_processes_jobs` |
| Erfolgreiche Transkription mit Mock-Provider | `test_mock_transcription_completes_and_is_flagged`, `test_video_input_is_transcribed`, E2E `full workflow` |
| Provider-Fehler, Wiederholung, leeres Ergebnis | `test_provider_failure_marks_job_failed`, `test_retryable_failure_is_retried`, `test_empty_result_is_not_completed`, `test_missing_source_file_fails_job` |
| Abbruch | `test_cancel_pending_job`, `test_cancel_during_processing` |
| Doppelte Auftragsübermittlung | `test_duplicate_submission_rejected`, `test_duplicate_upload_is_flagged` |
| Speichern und Bearbeiten | `test_edit_transcript_with_versioning`, `test_edit_rejects_unknown_segments_and_missing_transcript`, `test_edit_blocked_while_job_active`, E2E (Bearbeiten → Autosave → Neu laden) |
| Umbenennen und Löschen | `test_list_search_rename_delete`, E2E |
| Suche | `test_search_matches_transcript_text_and_escapes_wildcards`, Frontend `findMatches`, E2E |
| TXT/SRT/VTT/DOCX-Export (geparst und geprüft) | `test_export_txt`, `test_export_srt_is_valid`, `test_export_vtt_is_valid`, `test_export_docx_is_valid_zip`, E2E (SRT und VTT heruntergeladen und geprüft) |
| Zeitstempel-Formatierung | `test_timestamp_formatting`, Frontend `formatClock` |
| Externe Provider deaktiviert / fehlende Zugangsdaten | `test_external_provider_disabled_by_default`, `test_external_provider_missing_credentials_fails_closed`, `test_external_provider_with_credentials_still_never_sends`, `test_api_refuses_external_provider` |
| Kein stilles Fallback auf Mock | `test_auto_without_real_engine_fails_closed`, `test_auto_never_selects_mock` |
| Sicherheits-Header, CORS, Logs ohne Inhalte | `test_security_headers_and_cors`, `test_logs_do_not_contain_transcript_or_filename` |
| Medienwiedergabe mit Range-Requests | `test_media_is_served_with_range_support` |
| Mobile ohne horizontales Scrollen | E2E `responsive.spec.ts` |

## Was nicht getestet werden konnte

- **Echte Transkription mit Whisper:** In der Entwicklungsumgebung war Whisper nicht installiert, und der Modell-Download (≥ 145 MB) wurde nicht ohne Freigabe durchgeführt. Der Code der Whisper-Provider ist geschrieben, aber **nicht gegen ein echtes Modell gelaufen**. Getestet ist nur, dass sie korrekt „nicht verfügbar“ melden.
- **Browser außer Chromium** (Firefox, Safari) wurden nicht automatisiert getestet.
- **GPU-Betrieb** nicht getestet.
- **Sehr große Dateien** (nahe 500 MB) und sehr lange Aufnahmen nur über Limits getestet, nicht mit echter Verarbeitung.
- **Windows/macOS**: entwickelt und getestet unter Linux.
