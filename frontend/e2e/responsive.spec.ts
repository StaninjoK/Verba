import { expect, test } from "@playwright/test";

for (const route of ["/", "/app"]) {
  test(`no horizontal scrolling on mobile: ${route}`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
