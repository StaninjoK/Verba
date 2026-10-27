# Lokales Whisper einrichten

Verba unterstützt zwei lokale Whisper-Engines. Beide laufen offline und sind kostenlos (MIT-Lizenz). Empfohlen wird **faster-whisper**: auf CPUs deutlich schneller, braucht weniger Speicher, meldet echten Fortschritt und lässt sich sofort abbrechen.

Verba lädt **nie** automatisch Modelle herunter. Der Download ist ein bewusster, einmaliger Schritt.

## 1. Engine installieren (ca. 100 MB)

```bash
backend/.venv/bin/pip install -r backend/requirements-whisper.txt
```

Das installiert `faster-whisper` mit `ctranslate2`, `onnxruntime` (für die Sprachpausen-Erkennung), `av`, `tokenizers` und `huggingface_hub`.

## 2. Modell wählen

| Modell | Download (ca.) | RAM (ca.) | Qualität | Hinweis |
|---|---|---|---|---|
| `tiny` | 75 MB | < 1 GB | einfach | nur zum Ausprobieren |
| `base` | 145 MB | < 1 GB | ordentlich | **guter Start für CPUs** |
| `small` | 465 MB | 1–2 GB | gut | empfehlenswert, wenn Zeit keine Rolle spielt |
| `medium` | 1,5 GB | 2–3 GB | sehr gut | auf CPU langsam |
| `large-v3` | 3 GB | 3–5 GB | am besten | praktisch nur mit GPU sinnvoll |

Alle Zahlen sind Schätzungen. Die Geschwindigkeit hängt stark vom Prozessor ab – am besten mit einer eigenen 5-Minuten-Aufnahme messen.

## 3. Modell herunterladen (einmalig)

Variante A – über das mitgelieferte Hilfsprogramm von faster-whisper (lädt von Hugging Face, kostenlos, ohne Konto):

```bash
cd backend
.venv/bin/python -c "from faster_whisper import download_model; print(download_model('base', output_dir='models/faster-whisper-base'))"
```

Dann in `.env` (Repository-Hauptordner):

```
VERBA_WHISPER_MODEL=base
VERBA_WHISPER_MODEL_DIR=/absoluter/pfad/zu/Verba/backend/models
```

Variante B – automatisch beim ersten Auftrag: `VERBA_ALLOW_MODEL_DOWNLOAD=true` setzen. Nicht empfohlen, weil der erste Auftrag dann mit einem Download beginnt.

## 4. Prüfen

Backend neu starten. Oben rechts in der App steht dann **„Lokale Engine bereit“**, und im Engine-Menü erscheint „Whisper (lokal, faster-whisper) · base“. Alternativ:

```bash
curl -s http://127.0.0.1:8000/api/system | python3 -m json.tool | grep -A3 '"faster-whisper"'
```

## Alternative: openai-whisper

```bash
backend/.venv/bin/pip install openai-whisper
```

Achtung: zieht PyTorch nach (mehrere hundert MB bis über 2 GB, je nach Plattform). Modelle liegen als `~/.cache/whisper/<modell>.pt` bzw. in `VERBA_WHISPER_MODEL_DIR`. Diese Engine meldet keinen Fortschritt und kann nicht mitten in der Berechnung abgebrochen werden.

## GPU

Mit einer NVIDIA-Grafikkarte und installiertem CUDA: `VERBA_WHISPER_DEVICE=cuda`, `VERBA_WHISPER_COMPUTE_TYPE=float16`. Nicht getestet in dieser Version.

## Fehlerbehebung

| Meldung | Ursache |
|---|---|
| „faster-whisper is not installed“ | Schritt 1 fehlt oder falsches venv |
| „Model 'base' is not downloaded yet“ | Schritt 3 fehlt oder `VERBA_WHISPER_MODEL_DIR` zeigt auf den falschen Ordner (erwartet `…/faster-whisper-base/model.bin` oder `…/base/model.bin`) |
| „Not enough memory for this model“ | kleineres Modell wählen |
| „Processing took longer than the configured limit“ | Timeout = max(5 min, 6 × Aufnahmedauer). Kleineres Modell wählen |
