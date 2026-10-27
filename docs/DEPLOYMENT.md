# Bereitstellung auf einer Subdomain

## Spaceship Hyperlift (vorbereitet, noch nicht ausgeführt)

Das Repository enthält ein fertiges `Dockerfile`: ein einziger Container mit Backend, Weboberfläche, FFmpeg, faster-whisper und dem Modell `base`. Passwortschutz ist eingebaut und **Pflicht** – ohne `VERBA_AUTH_PASSWORD` startet der Container nicht.

**Kosten:** Hyperlift wird stündlich abgerechnet, laut Spaceship ab ca. 3,60 USD/Monat; ein Profil mit 1 GB RAM (für Whisper `base` empfohlen) wird von Drittanbietern mit ca. 6,50 USD/Monat angegeben. **Vor dem Anlegen aktuellen Preis prüfen und freigeben.**

Schritte im Spaceship-Konto:

1. *Starlight → Hyperlift → Neue App* → GitHub verbinden → Repository `staninjok/verba`, Branch `claude/great-ritchie-s7bqiu` (oder `main` nach dem Mergen).
2. Profil mit mindestens **1 GB RAM** wählen, Port **8080**.
3. Umgebungsvariablen setzen:
   - `VERBA_AUTH_PASSWORD` = ein langes, zufälliges Passwort (Benutzername ist `verba`, änderbar mit `VERBA_AUTH_USER`)
4. Deploy starten. Der erste Build dauert einige Minuten (Modell-Download ~145 MB).
5. *Custom Domain* → `verba.<deine-domain>` hinzufügen. Liegt die Domain bei Spaceship, wird der DNS-Eintrag dort (Advanced DNS) als CNAME auf die von Hyperlift angezeigte Adresse gesetzt.
6. Testen: `https://verba.<deine-domain>/api/health` → `{"status":"ok"}`; die Startseite fragt nach Benutzer `verba` und dem Passwort.

**Achtung Datenspeicher:** Projekte liegen im Container unter `/data`. Ob Hyperlift dauerhaften Speicher anbietet, ist ungeprüft. Ohne dauerhaften Speicher gehen Projekte bei jedem neuen Deploy verloren – für einen Testbetrieb in Ordnung, für echte Nutzung nicht.

---

## Allgemeiner Plan (andere Server)

Gewünscht ist Verba unter einer Subdomain wie `verba.kunzsystem.<tld>`. Dieser Schritt wurde **bewusst noch nicht ausgeführt**, weil er Zugriff auf deinen Hosting-Account und deine DNS-Einstellungen braucht, Kosten verursachen kann und die App ohne Zugangsschutz für jeden im Internet offen wäre.

## Warum nicht einfach „deployen“?

- **Kein Zugangsschutz:** Ohne Login könnte jeder Dateien hochladen, Transkripte lesen und löschen.
- **Rechenlast:** Whisper braucht einen Server mit genug CPU/RAM. Reines Static-/Serverless-Hosting (z. B. typische Frontend-Hosts) kann das Backend nicht ausführen.
- **Kosten nach dem Guthaben:** Viele Anbieter rechnen nach Verbrauch des Startguthabens automatisch weiter ab.

## Empfohlene Minimal-Architektur

```
Internet ──HTTPS──▶ Caddy (TLS + Passwortschutz)
                       ├─ /api/*  ──▶ FastAPI 127.0.0.1:8000
                       └─ /*      ──▶ Next.js 127.0.0.1:3000  (NEXT_PUBLIC_API_URL="")
```

Beispiel `Caddyfile`:

```
verba.example.com {
    basic_auth {
        # Hash erzeugen mit: caddy hash-password
        stan <BCRYPT-HASH>
    }
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
    request_body {
        max_size 500MB
    }
}
```

Backend-Einstellungen dafür: `VERBA_CORS_ORIGINS=https://verba.example.com`, `VERBA_HOST=127.0.0.1`.

## Was ich dafür von dir brauche

1. Bei welchem Anbieter liegt das Guthaben (z. B. 100 USD)? Läuft danach automatisch eine Abrechnung weiter? Lässt sich ein hartes Ausgabenlimit setzen?
2. Wo wird `kunzsystem` verwaltet (DNS-Anbieter) und wie lautet die vollständige Domain?
3. Deine ausdrückliche Freigabe für: Server anlegen, DNS-Eintrag (A/AAAA oder CNAME) setzen, öffentlich erreichbar machen.
4. Einverständnis, dass vor dem Start mindestens ein Passwortschutz (wie oben) aktiv ist.

## Checkliste vor dem Livegang

- [ ] Passwortschutz oder Konten aktiv
- [ ] HTTPS aktiv (Caddy macht das automatisch)
- [ ] `VERBA_MAX_UPLOAD_MB`, `VERBA_MAX_STORAGE_MB`, `VERBA_MAX_CONCURRENT_JOBS` passend zur Servergröße
- [ ] Backups von `VERBA_DATA_DIR`
- [ ] Server-Updates automatisch
- [ ] Ausgabenlimit beim Anbieter gesetzt
- [ ] Impressum und Datenschutzerklärung (bei öffentlichem Angebot in DE Pflicht)
