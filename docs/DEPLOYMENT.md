# Bereitstellung auf einer Subdomain (Plan – nicht umgesetzt)

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
