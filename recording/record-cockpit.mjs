#!/usr/bin/env node

import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const output = process.argv[2];
if (!output) throw new Error("usage: record-cockpit.mjs OUTPUT.webm");

process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("playwright");

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: dirname(output), size: { width: 1440, height: 900 } },
});
const page = await context.newPage();
await page.goto(
  "http://127.0.0.1:8765/recording/cockpit-prototype/?variant=A&autoplay=1&record=1",
  { waitUntil: "networkidle" },
);
await page.waitForTimeout(42_000);

const video = page.video();
if (!video) throw new Error("Playwright video recording did not start");
await page.close();
await video.saveAs(output);
await context.close();
await browser.close();
