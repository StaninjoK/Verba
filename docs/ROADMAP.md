# Kommerzieller Fahrplan

Jede Stufe beginnt erst nach ausdrücklicher Freigabe durch den Inhaber. Kostenangaben sind Prüfaufträge, keine Preise. Vor der Empfehlung eines kostenpflichtigen Anbieters werden aktuelle Preise, Lizenz, regionale Verfügbarkeit, Datenverarbeitung (Serverstandort, AV-Vertrag), Vertragsbedingungen und Limits geprüft und dem Inhaber vorgelegt.

## Stufe A – Lokales MVP ✅ (diese Version)

- **Voraussetzungen:** Node.js, Python, FFmpeg
- **Risiken:** Transkriptqualität und -tempo auf CPUs; Name „Verba“ nicht geprüft
- **Zu prüfende Kosten:** keine
- **Abnahme:** App startet mit dokumentierten Befehlen, Upload/Prüfung/Aufträge/Editor/Exporte/Bibliothek funktionieren, Tests laufen grün, echte Transkription funktioniert nach Whisper-Installation

## Stufe B – Tests mit echten Nutzern

- **Voraussetzungen:** Whisper installiert; 5–10 Testpersonen aus den Zielgruppen; Feedback-Leitfaden; Einverständnis für Testaufnahmen
- **Risiken:** sensible Aufnahmen der Tester; Installationshürde (Python/FFmpeg); unterschiedliche Hardware
- **Zu prüfende Kosten:** ggf. ein kleiner, passwortgeschützter Testserver (siehe DEPLOYMENT.md); Markenrecherche „Verba“ (DPMA/EUIPO/WIPO, Domains)
- **Abnahme:** Mehrheit der Tester schafft den Ablauf ohne Hilfe; Genauigkeit pro Sprache dokumentiert; Top-5-Probleme behoben

## Stufe C – Optionaler Cloud-Transkriptions-Adapter

- **Voraussetzungen:** Anbieter-Vergleich (Preis pro Minute, Datenstandort EU, Speicherung/Training mit Kundendaten, AV-Vertrag); Freigabe durch Inhaber
- **Risiken:** laufende Kosten pro Minute; Datenschutz; Abhängigkeit vom Anbieter
- **Zu prüfende Kosten:** Preis pro Audiominute, Mindestumsatz, Kosten bei Fehlversuchen
- **Abnahme:** Adapter nur bei expliziter Aktivierung; sichtbar als „extern“ gekennzeichnet; Ausgabenlimit pro Tag/Monat im Code; Tests mit Mock-Server; nie automatischer Wechsel von lokal zu extern

## Stufe D – Konten und private Cloud-Speicherung

- **Voraussetzungen:** Auth-Lösung (selbst gehostet oder Anbieter), Postgres, Objektspeicher, Mandantentrennung
- **Risiken:** Datenlecks zwischen Konten; Passwort-Sicherheit; DSGVO-Pflichten
- **Zu prüfende Kosten:** Datenbank, Objektspeicher, E-Mail-Versand, Backups
- **Abnahme:** Autorisierungstests (Nutzer A sieht nie Daten von B); Löschung entfernt alle Daten inkl. Backups innerhalb definierter Frist; Datenschutzerklärung

## Stufe E – Nutzungsmessung, Missbrauchsschutz, Kostenkontrolle

- **Voraussetzungen:** Minutenzähler pro Konto; Kontingente; Rate-Limits; Upload-Scans
- **Risiken:** Kosten durch Missbrauch; falsche Abrechnung
- **Zu prüfende Kosten:** Monitoring, ggf. CAPTCHA-Dienst
- **Abnahme:** harte Kontingente greifen vor jeder kostenverursachenden Aktion; Alarm bei ungewöhnlicher Nutzung

## Stufe F – Zahlungsanbieter und Abonnements

- **Voraussetzungen:** Unternehmensform, Steuerfragen (USt/OSS), AGB, Widerrufsbelehrung; Anbieter-Vergleich
- **Risiken:** rechtliche Pflichten; Zahlungsausfälle; Rückbuchungen
- **Zu prüfende Kosten:** Transaktionsgebühren, Steuerberatung, Rechtsberatung
- **Abnahme:** Testmodus-Zahlungen Ende-zu-Ende; Kündigung und Rückerstattung funktionieren; Rechnungen korrekt

## Stufe G – Produktionsbetrieb und Überwachung

- **Voraussetzungen:** Infrastruktur als Code, CI/CD, Monitoring, Alarmierung, Backup-Wiederherstellung geübt, Sicherheitsprüfung
- **Risiken:** Ausfälle; Datenverlust; Sicherheitsvorfälle
- **Zu prüfende Kosten:** Server/GPU, Monitoring, Backups, Penetrationstest
- **Abnahme:** definierte Verfügbarkeit erreicht; Wiederherstellung aus Backup getestet; Vorfallsplan dokumentiert; externer Sicherheitstest bestanden
