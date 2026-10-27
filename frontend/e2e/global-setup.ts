import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";

// Synthetic fixtures generated locally with FFmpeg – no downloaded or private recordings.
export default function globalSetup() {
  const dir = path.join(__dirname, ".fixtures");
  mkdirSync(dir, { recursive: true });
  const ff = (...args: string[]) => execFileSync("ffmpeg", ["-nostdin", "-loglevel", "error", "-y", ...args]);
  ff("-f", "lavfi", "-i", "sine=frequency=440:duration=9", path.join(dir, "e2e-tone.wav"));
  ff("-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=4", "-f", "lavfi", "-i", "sine=frequency=500:duration=4",
    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path.join(dir, "e2e-clip.mp4"));
}
