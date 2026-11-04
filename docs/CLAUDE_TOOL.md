# WhatsApp-Chats transkribieren – in Verba und mit Claude

## 1. WhatsApp-Chat exportieren

| Gerät | So geht's |
|---|---|
| **Android** | Chat öffnen → ⋮ → *Mehr* → *Chat exportieren* → **Medien einbeziehen** → z. B. in Google Drive oder per E-Mail speichern und auf den Computer holen. |
| **iPhone** | Chat öffnen → Name oben antippen → *Chat exportieren* → **Medien anhängen** → in „Dateien“ sichern und auf den Computer holen. |

Es entsteht eine ZIP-Datei (z. B. `WhatsApp Chat mit Maria.zip`) mit `_chat.txt` und allen Sprachnachrichten (`.opus`), Fotos und Videos. Ohne Medien gibt es nur die Textdatei. Dann sind nur Textnachrichten enthalten, und Sprachnachrichten erscheinen als „Datei fehlt im Export“.

## 2. In Verba

1. App öffnen → Reiter **WhatsApp-Chat**.
2. ZIP-Datei ablegen.
3. **Sprache der Sprachnachrichten** wählen, z. B. *Spanisch*. Bei gemischten Chats „Automatisch je Nachricht erkennen“ wählen.
4. **Chat importieren und transkribieren** klicken. Verba transkribiert jede Sprachnachricht und jedes Video nacheinander. Das kann bei vielen Nachrichten einige Minuten dauern. Die Seite darf dabei geschlossen werden.
5. Ergebnis:
   - **Textblock**: der ganze Chat chronologisch, nach Tagen gruppiert, mit Uhrzeit und Absender. Kopieren oder herunterladen als TXT, Markdown, Word oder JSON.
   - **Nachrichten**: jede Nachricht einzeln, Sprachnachrichten zum Anhören, Transkripte bearbeiten, Bilder beschreiben.

Beispiel für den Textblock:

```
WhatsApp-Chat: Maria
Teilnehmer: Stan, María López
Zeitraum: 04.11.2026 – 05.11.2026
Nachrichten: 4 · Sprachnachrichten: 2 (2 transkribiert) · Bilder: 1
Transkribiert mit Verba (faster-whisper · small)

── 04.11.2026 ──
[09:16] Stan: Hola María!
[09:17] María López – 🎤 Sprachnachricht (0:42): Hola Stan, te cuento que mañana …
[09:18] María López – 🖼 Bild: Beschreibung: Rechnung über 120 € | Bildunterschrift: Mira esto
```

### Sprache

- **Feste Sprache** (empfohlen, wenn der Chat einsprachig ist): Alle Sprachnachrichten werden in dieser Sprache erkannt. Das ist am zuverlässigsten.
- **Automatisch**: Whisper erkennt die Sprache pro Sprachnachricht. Ist Whisper bei einer kurzen Nachricht unsicher (unter 60 % Sicherheit) und weicht sie von der Hauptsprache des Chats ab, wird sie in der Hauptsprache wiederholt. Abweichende Sprachen werden im Text vermerkt, z. B. `(0:12, Sprache: pt)`.

### Bilder

- **Text in Bildern** (Screenshots, Rechnungen): Verba liest ihn automatisch aus, wenn das kostenlose Programm [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installiert ist (Windows: `winget install UB-Mannheim.TesseractOCR`).
- **Bildinhalt beschreiben**: Das macht **Claude**, siehe unten. Alternativ kannst du die Beschreibung selbst in der Nachrichtenansicht eintragen.

Alles läuft lokal. Dateien verlassen den Computer nicht. Nur wenn du Claude die Bilder beschreiben lässt, sieht Claude diese Bilder, so wie bei jedem anderen Bild, das du Claude zeigst.

## 3. Verba als Werkzeug für Claude

Verba enthält einen MCP-Server, über den Claude Verba direkt bedienen kann. Danach kannst du Claude z. B. schreiben:

> „Transkribiere den WhatsApp-Chat `C:\Users\Stan\Downloads\WhatsApp Chat mit Maria.zip` auf Spanisch, beschreibe die Bilder und gib mir den kompletten Chat als Text.“

Claude ruft dann diese Werkzeuge auf:

| Werkzeug | Zweck |
|---|---|
| `verba_status` | Prüfen, ob Verba läuft und welches Whisper-Modell bereitsteht |
| `transcribe_whatsapp_chat` | ZIP/TXT importieren, alle Sprachnachrichten transkribieren, Textblock zurückgeben |
| `get_whatsapp_chat` | Fortschritt und Text eines Chats abrufen (TXT, Markdown oder JSON) |
| `list_whatsapp_chats` | Importierte Chats auflisten und durchsuchen |
| `get_chat_images` | Bilder eines Chats an Claude übergeben, damit Claude sie ansieht |
| `set_image_descriptions` | Claudes Bildbeschreibungen in Verba speichern; sie erscheinen im Textblock |
| `transcribe_audio_file` | Eine einzelne Audio- oder Videodatei transkribieren |

Das Verba-Backend muss nicht vorher laufen: Der MCP-Server startet es bei Bedarf selbst.

### Claude Desktop (Windows)

Der Windows-Installer (`windows/install-verba.ps1`) trägt Verba automatisch ein. Danach **Claude Desktop neu starten**. Manuell: *Einstellungen → Entwickler → Konfiguration bearbeiten* und Folgendes ergänzen (Pfade anpassen):

```json
{
  "mcpServers": {
    "verba": {
      "command": "C:\\Users\\DEINNAME\\Verba\\backend\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\DEINNAME\\Verba\\backend\\verba_mcp.py"]
    }
  }
}
```

### Claude Desktop (macOS)

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "verba": {
      "command": "/Users/DEINNAME/Verba/backend/.venv/bin/python",
      "args": ["/Users/DEINNAME/Verba/backend/verba_mcp.py"]
    }
  }
}
```

### Claude Code

Im Verba-Ordner liegt bereits `.mcp.json` für macOS und Linux. Claude Code fragt beim ersten Start im Ordner, ob der Server „verba“ genutzt werden darf. Unter Windows:

```powershell
claude mcp add verba -- "$HOME\Verba\backend\.venv\Scripts\python.exe" "$HOME\Verba\backend\verba_mcp.py"
```

### Kommandozeile (ohne Claude)

```bash
backend/.venv/bin/python -m verba.cli chat "WhatsApp Chat mit Maria.zip" --language es --out maria.txt
backend/.venv/bin/python -m verba.cli chat export.zip --format docx --out chat.docx
backend/.venv/bin/python -m verba.cli status
```

### Einstellungen

| Variable | Bedeutung |
|---|---|
| `VERBA_API_URL` | Adresse des Backends (Standard `http://127.0.0.1:8000`) |
| `VERBA_AUTH_USER` / `VERBA_AUTH_PASSWORD` | Falls Verba mit Passwortschutz läuft |
| `VERBA_MCP_AUTOSTART=0` | Backend nicht automatisch starten |
| `VERBA_MAX_CHAT_IMPORT_MB` | Maximale Größe eines Chat-Exports (Standard 2000 MB) |

## Grenzen

- Die Genauigkeit hängt vom Whisper-Modell ab. Für Spanisch empfiehlt sich mindestens `small`, das der Windows-Installer einrichtet.
- Sehr kurze Sprachnachrichten („sí“, „ok“) werden manchmal ungenau erkannt.
- Zeitangaben werden so übernommen, wie sie im Export stehen (Ortszeit des Telefons beim Export).
- Bei mehrdeutigen Datumsformaten (z. B. 04.05.26) wird Tag.Monat angenommen, außer der Export enthält Daten, die nur als Monat/Tag Sinn ergeben.
- Umfragen, Standorte und Kontakte erscheinen so, wie WhatsApp sie als Text exportiert.
