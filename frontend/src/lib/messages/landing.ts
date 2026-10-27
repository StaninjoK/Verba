// Landing page strings. Keys are prefixed with "landing.".

export const landingEn = {
  "landing.nav.features": "Features",
  "landing.nav.how": "How it works",
  "landing.nav.privacy": "Privacy",
  "landing.nav.faq": "FAQ",
  "landing.nav.menu": "Menu",
  "landing.nav.main": "Main navigation",

  "landing.hero.eyebrow": "Transcription that stays on your computer",
  "landing.hero.titleA": "Every word,",
  "landing.hero.titleAccent": "beautifully",
  "landing.hero.titleB": "on the page.",
  "landing.hero.subtitle":
    "Verba turns interviews, lectures, meetings and podcasts into editable transcripts and subtitles – with timestamps, search and exports. Processed locally, without a cloud upload.",
  "landing.hero.ctaPrimary": "Start transcribing",
  "landing.hero.ctaSecondary": "See how it works",
  "landing.hero.note": "Free to use locally · No account required",
  "landing.hero.illustration": "Illustration – not real output",
  "landing.hero.demoFile": "interview-episode-12.mp3",
  "landing.hero.demoStatus": "Transcribing locally",
  "landing.hero.demoLine1": "Welcome back. Today we talk about how ideas become stories.",
  "landing.hero.demoLine2": "It always starts with listening – really listening.",
  "landing.hero.demoLine3": "And then you write down every single word.",
  "landing.hero.demoLine4": "Later, you search, edit and share what matters.",

  "landing.marquee.label": "Languages and formats",

  "landing.features.eyebrow": "Features",
  "landing.features.title": "Everything you need from a recording –",
  "landing.features.titleAccent": "nothing you don't.",
  "landing.features.local.title": "Local by design",
  "landing.features.local.body":
    "Speech recognition runs on your own machine with open-source Whisper. Your audio is never uploaded to a cloud service.",
  "landing.features.languages.title": "30+ languages",
  "landing.features.languages.body":
    "Choose the spoken language or let the engine detect it automatically. Quality depends on the Whisper model you install.",
  "landing.features.editor.title": "An editor made for reading",
  "landing.features.editor.body":
    "Correct text segment by segment, search the whole transcript and click any timestamp to jump there. Changes save automatically.",
  "landing.features.exports.title": "Export in one click",
  "landing.features.exports.body": "Plain text, text with timestamps, SRT and VTT subtitles, Word documents or JSON.",
  "landing.features.formats.title": "Audio and video",
  "landing.features.formats.body": "MP3, WAV, M4A, MP4, MOV, OGG, FLAC and WebM. Files are checked before processing.",
  "landing.features.playback.title": "Playback in sync",
  "landing.features.playback.body": "Listen while you read – the current segment is highlighted as the recording plays.",

  "landing.how.eyebrow": "How it works",
  "landing.how.title": "From recording to transcript in",
  "landing.how.titleAccent": "three steps.",
  "landing.how.step1.title": "Drop your file",
  "landing.how.step1.body": "Drag an audio or video file into Verba. It is validated and its details are shown right away.",
  "landing.how.step2.title": "Pick a language",
  "landing.how.step2.body":
    "Select the spoken language or automatic detection and start. Long recordings run in the background.",
  "landing.how.step3.title": "Edit and export",
  "landing.how.step3.body": "Refine the text, search it, and download it as text, subtitles or a Word document.",

  "landing.privacy.eyebrow": "Privacy",
  "landing.privacy.title": "Your recordings are",
  "landing.privacy.titleAccent": "yours.",
  "landing.privacy.body":
    "Interviews, lectures and meetings are often confidential. That's why Verba is built to work entirely on your own computer.",
  "landing.privacy.point1": "Files and transcripts are stored locally only",
  "landing.privacy.point2": "No cloud upload, no tracking, no account",
  "landing.privacy.point3": "External engines are switched off by default",
  "landing.privacy.point4": "Delete a project and its file is gone for good",
  "landing.privacy.cardTitle": "Processing location",
  "landing.privacy.cardLocal": "This computer",
  "landing.privacy.cardCloud": "Cloud services",
  "landing.privacy.cardOff": "Off",
  "landing.privacy.cardOn": "Active",

  "landing.uses.eyebrow": "Made for",
  "landing.uses.title": "Anyone who works with the spoken word.",
  "landing.uses.students": "Students",
  "landing.uses.journalists": "Journalists",
  "landing.uses.researchers": "Researchers",
  "landing.uses.podcasters": "Podcasters",
  "landing.uses.creators": "Content creators",
  "landing.uses.teams": "Teams & businesses",
  "landing.uses.lectures": "Lectures",
  "landing.uses.interviews": "Interviews",
  "landing.uses.meetings": "Meetings",
  "landing.uses.subtitles": "Video subtitles",

  "landing.faq.eyebrow": "FAQ",
  "landing.faq.title": "Questions & answers",
  "landing.faq.q1": "Is my audio uploaded anywhere?",
  "landing.faq.a1":
    "No. In this version all processing happens on your computer. Files and transcripts are stored in a local folder, and external transcription services are disabled.",
  "landing.faq.q2": "How accurate are the transcripts?",
  "landing.faq.a2":
    "Accuracy depends on the Whisper model you install, the audio quality and the language. Larger models are more accurate but slower. You can always correct the text in the editor.",
  "landing.faq.q3": "What do I need to run Verba?",
  "landing.faq.a3":
    "A computer with Python, Node.js and FFmpeg. For real transcription you also install a local Whisper engine and download a model once – the setup guide explains every step.",
  "landing.faq.q4": "Which file formats are supported?",
  "landing.faq.a4": "MP3, WAV, M4A, MP4, MOV, OGG, Opus, FLAC and WebM, as long as the file contains an audio track.",
  "landing.faq.q5": "Does it cost anything?",
  "landing.faq.a5":
    "Running Verba locally is free. It uses open-source software, and no paid services are activated.",
  "landing.faq.q6": "Can I create subtitles?",
  "landing.faq.a6":
    "Yes. Export SRT or VTT files with the timestamps the engine produced for each segment, ready for video players and editors.",

  "landing.cta.title": "Ready when your next recording is.",
  "landing.cta.body": "Open Verba, drop a file and get a transcript you can actually work with.",
  "landing.cta.button": "Open Verba",

  "landing.footer.tagline": "Local transcription for audio and video.",
  "landing.footer.product": "Product",
  "landing.footer.app": "Open app",
  "landing.footer.rights": "© {year} Verba. Working title – development version.",
};

export type LandingKey = keyof typeof landingEn;

export const landingDe: Record<LandingKey, string> = {
  "landing.nav.features": "Funktionen",
  "landing.nav.how": "So funktioniert’s",
  "landing.nav.privacy": "Datenschutz",
  "landing.nav.faq": "FAQ",
  "landing.nav.menu": "Menü",
  "landing.nav.main": "Hauptnavigation",

  "landing.hero.eyebrow": "Transkription, die auf deinem Computer bleibt",
  "landing.hero.titleA": "Jedes Wort,",
  "landing.hero.titleAccent": "wunderschön",
  "landing.hero.titleB": "auf dem Papier.",
  "landing.hero.subtitle":
    "Verba verwandelt Interviews, Vorlesungen, Meetings und Podcasts in bearbeitbare Transkripte und Untertitel – mit Zeitstempeln, Suche und Exporten. Lokal verarbeitet, ohne Cloud-Upload.",
  "landing.hero.ctaPrimary": "Jetzt transkribieren",
  "landing.hero.ctaSecondary": "So funktioniert’s",
  "landing.hero.note": "Lokal kostenlos nutzbar · Kein Konto nötig",
  "landing.hero.illustration": "Illustration – keine echte Ausgabe",
  "landing.hero.demoFile": "interview-folge-12.mp3",
  "landing.hero.demoStatus": "Wird lokal transkribiert",
  "landing.hero.demoLine1": "Willkommen zurück. Heute geht es darum, wie aus Ideen Geschichten werden.",
  "landing.hero.demoLine2": "Es beginnt immer mit dem Zuhören – wirklichem Zuhören.",
  "landing.hero.demoLine3": "Und dann schreibst du jedes einzelne Wort auf.",
  "landing.hero.demoLine4": "Später suchst, bearbeitest und teilst du, was zählt.",

  "landing.marquee.label": "Sprachen und Formate",

  "landing.features.eyebrow": "Funktionen",
  "landing.features.title": "Alles, was du aus einer Aufnahme brauchst –",
  "landing.features.titleAccent": "nichts, was du nicht brauchst.",
  "landing.features.local.title": "Lokal aus Prinzip",
  "landing.features.local.body":
    "Die Spracherkennung läuft mit Open-Source-Whisper auf deinem eigenen Rechner. Deine Aufnahmen werden nie in eine Cloud hochgeladen.",
  "landing.features.languages.title": "Über 30 Sprachen",
  "landing.features.languages.body":
    "Wähle die gesprochene Sprache oder lass sie automatisch erkennen. Die Qualität hängt vom installierten Whisper-Modell ab.",
  "landing.features.editor.title": "Ein Editor zum Lesen gemacht",
  "landing.features.editor.body":
    "Korrigiere Abschnitt für Abschnitt, durchsuche das ganze Transkript und springe per Klick auf einen Zeitstempel. Änderungen werden automatisch gespeichert.",
  "landing.features.exports.title": "Export mit einem Klick",
  "landing.features.exports.body": "Reiner Text, Text mit Zeitstempeln, SRT- und VTT-Untertitel, Word-Dokumente oder JSON.",
  "landing.features.formats.title": "Audio und Video",
  "landing.features.formats.body": "MP3, WAV, M4A, MP4, MOV, OGG, FLAC und WebM. Dateien werden vor der Verarbeitung geprüft.",
  "landing.features.playback.title": "Synchrone Wiedergabe",
  "landing.features.playback.body": "Hören und mitlesen – der aktuelle Abschnitt wird während der Wiedergabe hervorgehoben.",

  "landing.how.eyebrow": "So funktioniert’s",
  "landing.how.title": "Von der Aufnahme zum Transkript in",
  "landing.how.titleAccent": "drei Schritten.",
  "landing.how.step1.title": "Datei ablegen",
  "landing.how.step1.body": "Zieh eine Audio- oder Videodatei in Verba. Sie wird geprüft und ihre Details werden sofort angezeigt.",
  "landing.how.step2.title": "Sprache wählen",
  "landing.how.step2.body":
    "Wähle die gesprochene Sprache oder die automatische Erkennung und starte. Lange Aufnahmen laufen im Hintergrund.",
  "landing.how.step3.title": "Bearbeiten und exportieren",
  "landing.how.step3.body": "Verfeinere den Text, durchsuche ihn und lade ihn als Text, Untertitel oder Word-Dokument herunter.",

  "landing.privacy.eyebrow": "Datenschutz",
  "landing.privacy.title": "Deine Aufnahmen gehören",
  "landing.privacy.titleAccent": "dir.",
  "landing.privacy.body":
    "Interviews, Vorlesungen und Meetings sind oft vertraulich. Deshalb ist Verba so gebaut, dass alles auf deinem eigenen Computer läuft.",
  "landing.privacy.point1": "Dateien und Transkripte werden nur lokal gespeichert",
  "landing.privacy.point2": "Kein Cloud-Upload, kein Tracking, kein Konto",
  "landing.privacy.point3": "Externe Engines sind standardmäßig ausgeschaltet",
  "landing.privacy.point4": "Löschst du ein Projekt, ist die Datei endgültig weg",
  "landing.privacy.cardTitle": "Verarbeitungsort",
  "landing.privacy.cardLocal": "Dieser Computer",
  "landing.privacy.cardCloud": "Cloud-Dienste",
  "landing.privacy.cardOff": "Aus",
  "landing.privacy.cardOn": "Aktiv",

  "landing.uses.eyebrow": "Gemacht für",
  "landing.uses.title": "Alle, die mit dem gesprochenen Wort arbeiten.",
  "landing.uses.students": "Studierende",
  "landing.uses.journalists": "Journalist:innen",
  "landing.uses.researchers": "Forschende",
  "landing.uses.podcasters": "Podcaster",
  "landing.uses.creators": "Content Creator",
  "landing.uses.teams": "Teams & Unternehmen",
  "landing.uses.lectures": "Vorlesungen",
  "landing.uses.interviews": "Interviews",
  "landing.uses.meetings": "Meetings",
  "landing.uses.subtitles": "Video-Untertitel",

  "landing.faq.eyebrow": "FAQ",
  "landing.faq.title": "Fragen & Antworten",
  "landing.faq.q1": "Wird mein Audio irgendwohin hochgeladen?",
  "landing.faq.a1":
    "Nein. In dieser Version läuft die gesamte Verarbeitung auf deinem Computer. Dateien und Transkripte liegen in einem lokalen Ordner, externe Transkriptionsdienste sind deaktiviert.",
  "landing.faq.q2": "Wie genau sind die Transkripte?",
  "landing.faq.a2":
    "Die Genauigkeit hängt vom installierten Whisper-Modell, der Tonqualität und der Sprache ab. Größere Modelle sind genauer, aber langsamer. Im Editor kannst du den Text jederzeit korrigieren.",
  "landing.faq.q3": "Was brauche ich, um Verba zu nutzen?",
  "landing.faq.a3":
    "Einen Computer mit Python, Node.js und FFmpeg. Für echte Transkription installierst du zusätzlich eine lokale Whisper-Engine und lädst einmalig ein Modell – die Anleitung erklärt jeden Schritt.",
  "landing.faq.q4": "Welche Dateiformate werden unterstützt?",
  "landing.faq.a4": "MP3, WAV, M4A, MP4, MOV, OGG, Opus, FLAC und WebM – sofern die Datei eine Tonspur enthält.",
  "landing.faq.q5": "Kostet das etwas?",
  "landing.faq.a5":
    "Die lokale Nutzung von Verba ist kostenlos. Es wird Open-Source-Software verwendet und es sind keine kostenpflichtigen Dienste aktiv.",
  "landing.faq.q6": "Kann ich Untertitel erstellen?",
  "landing.faq.a6":
    "Ja. Exportiere SRT- oder VTT-Dateien mit den Zeitstempeln, die die Engine für jeden Abschnitt geliefert hat – bereit für Videoplayer und Schnittprogramme.",

  "landing.cta.title": "Bereit für deine nächste Aufnahme.",
  "landing.cta.body": "Öffne Verba, leg eine Datei ab und erhalte ein Transkript, mit dem du wirklich arbeiten kannst.",
  "landing.cta.button": "Verba öffnen",

  "landing.footer.tagline": "Lokale Transkription für Audio und Video.",
  "landing.footer.product": "Produkt",
  "landing.footer.app": "App öffnen",
  "landing.footer.rights": "© {year} Verba. Arbeitstitel – Entwicklungsversion.",
};

export const landingEs: Record<LandingKey, string> = {
  "landing.nav.features": "Funciones",
  "landing.nav.how": "Cómo funciona",
  "landing.nav.privacy": "Privacidad",
  "landing.nav.faq": "Preguntas",
  "landing.nav.menu": "Menú",
  "landing.nav.main": "Navegación principal",

  "landing.hero.eyebrow": "Transcripción que se queda en tu ordenador",
  "landing.hero.titleA": "Cada palabra,",
  "landing.hero.titleAccent": "perfectamente",
  "landing.hero.titleB": "sobre el papel.",
  "landing.hero.subtitle":
    "Verba convierte entrevistas, clases, reuniones y pódcasts en transcripciones y subtítulos editables, con marcas de tiempo, búsqueda y exportación. Procesado localmente, sin subir nada a la nube.",
  "landing.hero.ctaPrimary": "Empezar a transcribir",
  "landing.hero.ctaSecondary": "Ver cómo funciona",
  "landing.hero.note": "Gratis en local · Sin cuenta",
  "landing.hero.illustration": "Ilustración: no es un resultado real",
  "landing.hero.demoFile": "entrevista-episodio-12.mp3",
  "landing.hero.demoStatus": "Transcribiendo en local",
  "landing.hero.demoLine1": "Bienvenidos de nuevo. Hoy hablamos de cómo las ideas se convierten en historias.",
  "landing.hero.demoLine2": "Todo empieza escuchando, escuchando de verdad.",
  "landing.hero.demoLine3": "Y luego anotas cada una de las palabras.",
  "landing.hero.demoLine4": "Después buscas, editas y compartes lo importante.",

  "landing.marquee.label": "Idiomas y formatos",

  "landing.features.eyebrow": "Funciones",
  "landing.features.title": "Todo lo que necesitas de una grabación,",
  "landing.features.titleAccent": "nada que te sobre.",
  "landing.features.local.title": "Local por diseño",
  "landing.features.local.body":
    "El reconocimiento de voz se ejecuta en tu propio equipo con Whisper, de código abierto. Tu audio nunca se sube a un servicio en la nube.",
  "landing.features.languages.title": "Más de 30 idiomas",
  "landing.features.languages.body":
    "Elige el idioma hablado o deja que el motor lo detecte automáticamente. La calidad depende del modelo de Whisper que instales.",
  "landing.features.editor.title": "Un editor pensado para leer",
  "landing.features.editor.body":
    "Corrige el texto fragmento a fragmento, busca en toda la transcripción y haz clic en una marca de tiempo para saltar allí. Los cambios se guardan solos.",
  "landing.features.exports.title": "Exporta con un clic",
  "landing.features.exports.body": "Texto sin formato, texto con marcas de tiempo, subtítulos SRT y VTT, documentos de Word o JSON.",
  "landing.features.formats.title": "Audio y vídeo",
  "landing.features.formats.body": "MP3, WAV, M4A, MP4, MOV, OGG, FLAC y WebM. Los archivos se comprueban antes de procesarlos.",
  "landing.features.playback.title": "Reproducción sincronizada",
  "landing.features.playback.body": "Escucha mientras lees: el fragmento actual se resalta durante la reproducción.",

  "landing.how.eyebrow": "Cómo funciona",
  "landing.how.title": "De la grabación a la transcripción en",
  "landing.how.titleAccent": "tres pasos.",
  "landing.how.step1.title": "Suelta tu archivo",
  "landing.how.step1.body": "Arrastra un archivo de audio o vídeo a Verba. Se comprueba y ves sus detalles al instante.",
  "landing.how.step2.title": "Elige el idioma",
  "landing.how.step2.body":
    "Selecciona el idioma hablado o la detección automática y empieza. Las grabaciones largas se procesan en segundo plano.",
  "landing.how.step3.title": "Edita y exporta",
  "landing.how.step3.body": "Pule el texto, busca en él y descárgalo como texto, subtítulos o documento de Word.",

  "landing.privacy.eyebrow": "Privacidad",
  "landing.privacy.title": "Tus grabaciones son",
  "landing.privacy.titleAccent": "tuyas.",
  "landing.privacy.body":
    "Las entrevistas, clases y reuniones suelen ser confidenciales. Por eso Verba está pensado para funcionar por completo en tu propio ordenador.",
  "landing.privacy.point1": "Los archivos y las transcripciones se guardan solo en local",
  "landing.privacy.point2": "Sin subida a la nube, sin rastreo, sin cuenta",
  "landing.privacy.point3": "Los motores externos están desactivados por defecto",
  "landing.privacy.point4": "Si eliminas un proyecto, su archivo desaparece para siempre",
  "landing.privacy.cardTitle": "Lugar de procesamiento",
  "landing.privacy.cardLocal": "Este ordenador",
  "landing.privacy.cardCloud": "Servicios en la nube",
  "landing.privacy.cardOff": "Desactivado",
  "landing.privacy.cardOn": "Activo",

  "landing.uses.eyebrow": "Pensado para",
  "landing.uses.title": "Quien trabaja con la palabra hablada.",
  "landing.uses.students": "Estudiantes",
  "landing.uses.journalists": "Periodistas",
  "landing.uses.researchers": "Investigadores",
  "landing.uses.podcasters": "Podcasters",
  "landing.uses.creators": "Creadores de contenido",
  "landing.uses.teams": "Equipos y empresas",
  "landing.uses.lectures": "Clases",
  "landing.uses.interviews": "Entrevistas",
  "landing.uses.meetings": "Reuniones",
  "landing.uses.subtitles": "Subtítulos de vídeo",

  "landing.faq.eyebrow": "Preguntas",
  "landing.faq.title": "Preguntas y respuestas",
  "landing.faq.q1": "¿Se sube mi audio a algún sitio?",
  "landing.faq.a1":
    "No. En esta versión todo el procesamiento se realiza en tu ordenador. Los archivos y las transcripciones se guardan en una carpeta local y los servicios de transcripción externos están desactivados.",
  "landing.faq.q2": "¿Qué precisión tienen las transcripciones?",
  "landing.faq.a2":
    "La precisión depende del modelo de Whisper que instales, de la calidad del audio y del idioma. Los modelos grandes son más precisos pero más lentos. Siempre puedes corregir el texto en el editor.",
  "landing.faq.q3": "¿Qué necesito para usar Verba?",
  "landing.faq.a3":
    "Un ordenador con Python, Node.js y FFmpeg. Para transcribir de verdad instalas además un motor Whisper local y descargas un modelo una vez; la guía explica cada paso.",
  "landing.faq.q4": "¿Qué formatos de archivo se admiten?",
  "landing.faq.a4": "MP3, WAV, M4A, MP4, MOV, OGG, Opus, FLAC y WebM, siempre que el archivo tenga una pista de audio.",
  "landing.faq.q5": "¿Tiene algún coste?",
  "landing.faq.a5":
    "Usar Verba en local es gratis. Utiliza software de código abierto y no hay servicios de pago activados.",
  "landing.faq.q6": "¿Puedo crear subtítulos?",
  "landing.faq.a6":
    "Sí. Exporta archivos SRT o VTT con las marcas de tiempo que el motor generó para cada fragmento, listos para reproductores y editores de vídeo.",

  "landing.cta.title": "Listo para tu próxima grabación.",
  "landing.cta.body": "Abre Verba, suelta un archivo y obtén una transcripción con la que de verdad puedes trabajar.",
  "landing.cta.button": "Abrir Verba",

  "landing.footer.tagline": "Transcripción local para audio y vídeo.",
  "landing.footer.product": "Producto",
  "landing.footer.app": "Abrir app",
  "landing.footer.rights": "© {year} Verba. Nombre provisional: versión de desarrollo.",
};
