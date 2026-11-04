import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

const zip = path.join(__dirname, ".fixtures", "WhatsApp Chat mit Maria.zip");

test("WhatsApp chat: import, transcribe voice notes, describe image, export text block", async ({ page }) => {
  await page.goto("/app");
  await page.getByTestId("tab-chat").click();
  await page.getByTestId("chat-file-input").setInputFiles(zip);
  await page.getByLabel("Sprache der Sprachnachrichten").selectOption("es");
  await page.getByLabel("Engine").selectOption("mock");
  await page.getByTestId("chat-start").click();
  await page.waitForURL(/\/app\/chat\?id=[0-9a-f]{32}$/);

  await expect(page.getByTestId("chat-title")).toContainText("Maria");
  const block = page.getByTestId("chat-block");
  await expect(page.locator('[data-status="completed"]')).toBeVisible({ timeout: 30_000 });
  await expect(block).toContainText("WhatsApp-Chat: Maria");
  await expect(block).toContainText("[09:16] Stan: Hola María!");
  await expect(block).toContainText("🎤 Sprachnachricht (0:03): [MOCK]");
  await expect(block).toContainText("── 05.11.2026 ──");
  await expect(page.getByTestId("mock-banner")).toBeVisible();

  // describe the image in the message view
  await page.getByTestId("view-messages").click();
  await page.getByRole("button", { name: /Bild beschreiben/ }).click();
  await page.getByLabel("Bildbeschreibung").fill("Ein grünes Quadrat");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByText("Bildbeschreibung: Ein grünes Quadrat")).toBeVisible();

  await page.getByRole("tab", { name: "Textblock" }).click();
  await expect(block).toContainText("Beschreibung: Ein grünes Quadrat | Bildunterschrift: Mira esto");

  // TXT download contains the same block
  await page.getByTestId("chat-export").click();
  const dl = page.waitForEvent("download");
  await page.locator('[data-format="txt"]').click();
  const file = path.join(__dirname, ".fixtures", "chat-out.txt");
  await (await dl).saveAs(file);
  expect(readFileSync(file, "utf8")).toContain("[09:17] María López – 🎤 Sprachnachricht (0:03): [MOCK]");

  // listed on the dashboard, then deleted
  await page.getByRole("link", { name: "Bibliothek" }).first().click();
  await expect(page.getByTestId("chat-row").filter({ hasText: "Maria" }).first()).toBeVisible();
});
