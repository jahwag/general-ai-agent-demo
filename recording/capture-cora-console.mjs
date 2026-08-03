#!/usr/bin/env node

import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [output, secondsText = "15"] = process.argv.slice(2);
if (!output || !/\.(png|webm)$/.test(output)) {
  throw new Error("usage: capture-cora-console.mjs OUTPUT.png|OUTPUT.webm [SECONDS]");
}
const seconds = Number(secondsText);
if (!Number.isFinite(seconds) || seconds < 1 || seconds > 120) {
  throw new Error("SECONDS must be between 1 and 120");
}

process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("../tmp/playwright/node_modules/playwright/index.mjs");
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  ...(output.endsWith(".webm")
    ? { recordVideo: { dir: dirname(output), size: { width: 1440, height: 900 } } }
    : {}),
});
const page = await context.newPage();
await page.goto("http://127.0.0.1:17681/", { waitUntil: "networkidle" });
await page.waitForTimeout(2_000);

if (output.endsWith(".png")) {
  await page.screenshot({ path: output });
} else {
  await page.waitForTimeout(seconds * 1_000);
  const video = page.video();
  if (!video) throw new Error("Playwright video recording did not start");
  await page.close();
  await video.saveAs(output);
}

await context.close();
await browser.close();
