import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const fixtures = path.join(__dirname, ".fixtures");

async function uploadAndTranscribe(page: Page, file: string) {
  await page.goto("/app");
  await page.getByTestId("file-input").setInputFiles(path.join(fixtures, file));
  const ready = page.getByTestId("upload-ready");
  await expect(ready).toBeVisible();
  await expect(ready.getByText("Datei geprüft und bereit")).toBeVisible();
  // Without Whisper installed the test engine must be chosen explicitly and is labelled as such.
  const engine = ready.getByLabel("Engine");
  await engine.selectOption("mock");
  await expect(page.getByTestId("mock-hint")).toBeVisible();
  await ready.getByRole("button", { name: "Transkription starten" }).click();
  await page.waitForURL(/\/app\/project\?id=[0-9a-f]{32}$/);
  await expect(page.getByTestId("segments")).toBeVisible({ timeout: 30_000 });
}

test("landing page leads to the app", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText(/Illustration/).first()).toBeVisible();
  await page.getByRole("link", { name: /App öffnen/ }).first().click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Audio und Video transkribieren" })).toBeVisible();
});

test("full workflow: upload, transcribe, edit, export, rename, search, delete", async ({ page }) => {
  await uploadAndTranscribe(page, "e2e-tone.wav");

  // Mock output is never presented as real.
  await expect(page.getByTestId("mock-banner")).toBeVisible();
  await expect(page.getByTestId("mock-badge")).toBeVisible();

  // Edit + autosave
  const first = page.getByRole("textbox", { name: /Abschnitt bei 0:00/ });
  await first.fill("Überarbeiteter erster Satz mit Stichwort Zebra.");
  await expect(page.getByTestId("save-state")).toHaveText(/Alle Änderungen gespeichert/, { timeout: 10_000 });
  await page.reload();
  await expect(page.getByRole("textbox", { name: /Abschnitt bei 0:00/ })).toHaveValue("Überarbeiteter erster Satz mit Stichwort Zebra.");

  // In-transcript search
  await page.getByPlaceholder("Im Transkript suchen").fill("zebra");
  await expect(page.getByTestId("match-count")).toHaveText("1 von 1");

  // SRT export is valid
  await page.getByTestId("export-button").click();
  const downloadPromise = page.waitForEvent("download");
  await page.locator('[data-format="srt"]').click();
  const download = await downloadPromise;
  const srtPath = path.join(fixtures, "out.srt");
  await download.saveAs(srtPath);
  const srt = readFileSync(srtPath, "utf8");
  expect(srt).toMatch(/^1\n00:00:00,000 --> 00:00:0\d,\d{3}\nÜberarbeiteter erster Satz/);
  for (const block of srt.trim().split("\n\n")) {
    expect(block.split("\n")[1]).toMatch(/^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$/);
  }

  // VTT export
  await page.getByTestId("export-button").click();
  const vttDownload = page.waitForEvent("download");
  await page.locator('[data-format="vtt"]').click();
  const vttPath = path.join(fixtures, "out.vtt");
  await (await vttDownload).saveAs(vttPath);
  expect(readFileSync(vttPath, "utf8")).toMatch(/^WEBVTT\n\n00:00:00\.000 --> /);

  // Rename
  const unique = `E2E Projekt ${Date.now()}`;
  await page.getByRole("button", { name: "Projekt umbenennen" }).click();
  await page.getByRole("dialog").getByRole("textbox").fill(unique);
  await page.getByRole("dialog").getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByTestId("project-title")).toHaveText(unique);

  // Library search by transcript content and by title
  await page.getByRole("link", { name: "Bibliothek" }).first().click();
  await page.getByPlaceholder("Titel und Transkripte durchsuchen").fill("Zebra");
  const row = page.getByTestId("project-row").filter({ hasText: unique });
  await expect(row).toHaveCount(1);

  // Delete
  await row.getByRole("button", { name: `Aktionen für ${unique}` }).click();
  await page.getByRole("menuitem", { name: "Löschen" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Endgültig löschen" }).click();
  await expect(page.getByText("Projekt gelöscht")).toBeVisible();
  await expect(page.getByTestId("project-row").filter({ hasText: unique })).toHaveCount(0);
});

test("video files are accepted and playable", async ({ page }) => {
  await uploadAndTranscribe(page, "e2e-clip.mp4");
  await expect(page.locator("video")).toBeVisible();
  await expect(page.getByText("Video · ", { exact: false })).toBeVisible();
});

test("invalid files are rejected with a clear message", async ({ page }) => {
  const fake = path.join(fixtures, "not-audio.mp3");
  writeFileSync(fake, "definitely not audio ".repeat(50));
  await page.goto("/app");
  await page.getByTestId("file-input").setInputFiles(fake);
  await expect(page.getByTestId("upload-error")).toContainText("passt nicht zur Endung");

  const exe = path.join(fixtures, "tool.exe");
  writeFileSync(exe, "MZ");
  await page.getByTestId("file-input").setInputFiles(exe);
  await expect(page.getByTestId("upload-error")).toContainText("nicht unterstützt");
});
