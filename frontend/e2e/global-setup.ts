import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

// Synthetic fixtures generated locally with FFmpeg – no downloaded or private recordings.
export default function globalSetup() {
  const dir = path.join(__dirname, ".fixtures");
  mkdirSync(dir, { recursive: true });
  const ff = (...args: string[]) => execFileSync("ffmpeg", ["-nostdin", "-loglevel", "error", "-y", ...args]);
  ff("-f", "lavfi", "-i", "sine=frequency=440:duration=9", path.join(dir, "e2e-tone.wav"));
  ff("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=4", "-f", "lavfi", "-i", "sine=frequency=500:duration=4",
    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path.join(dir, "e2e-clip.mp4"));

  // A small WhatsApp export (Android, German labels) with two voice notes and a photo.
  const wa = path.join(dir, "wa");
  mkdirSync(wa, { recursive: true });
  ff("-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:a", "libopus", path.join(wa, "PTT-20261104-WA0001.opus"));
  ff("-f", "lavfi", "-i", "sine=frequency=500:duration=2", "-c:a", "libopus", path.join(wa, "PTT-20261104-WA0003.opus"));
  ff("-f", "lavfi", "-i", "color=c=green:s=64x64", "-frames:v", "1", path.join(wa, "IMG-20261104-WA0002.jpg"));
  writeFileSync(path.join(wa, "_chat.txt"), [
    "04.11.26, 09:16 - Stan: Hola María!",
    "04.11.26, 09:17 - María López: PTT-20261104-WA0001.opus (Datei angehängt)",
    "04.11.26, 09:18 - María López: IMG-20261104-WA0002.jpg (Datei angehängt)",
    "Mira esto",
    "05.11.26, 18:01 - Stan: PTT-20261104-WA0003.opus (Datei angehängt)",
    "",
  ].join("\n"));
  const zip = path.join(dir, "WhatsApp Chat mit Maria.zip");
  rmSync(zip, { force: true });
  execFileSync("python3", ["-c", "import sys,zipfile,os;z=zipfile.ZipFile(sys.argv[1],'w');[z.write(os.path.join(sys.argv[2],f),f) for f in os.listdir(sys.argv[2])];z.close()", zip, wa]);
}
