#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [sshConfig, sshAlias, output, secondsText = "24"] = process.argv.slice(2);
if (!sshConfig || !sshAlias || !output?.endsWith(".webm")) {
  throw new Error(
    "usage: capture-live-agentbus-video.mjs SSH_CONFIG SSH_ALIAS OUTPUT.webm [SECONDS]",
  );
}
const seconds = Number(secondsText);
if (!Number.isFinite(seconds) || seconds < 8 || seconds > 60) {
  throw new Error("SECONDS must be between 8 and 60");
}

const session = JSON.parse(
  execFileSync(
    "/usr/bin/ssh",
    [
      "-F",
      sshConfig,
      sshAlias,
      "sudo",
      "/usr/local/bin/agentbus",
      "ui-session",
      "--server",
      "http://127.0.0.1:7777",
      "--admin-token-file",
      "/etc/gaidemo-agentbus/admin.token",
    ],
    { encoding: "utf8" },
  ),
);

process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("../tmp/playwright/node_modules/playwright/index.mjs");
const browser = await chromium.launch({ headless: true });
const loginContext = await browser.newContext({
  viewport: { width: 1440, height: 900 },
});
const loginPage = await loginContext.newPage();
const server = "http://127.0.0.1:17779";

await loginPage.goto(`${server}/ui/`, { waitUntil: "networkidle" });
await loginPage.locator('input[name="code"]').fill(session.code);
await loginPage.locator('button[type="submit"]').click();
await loginPage.waitForLoadState("networkidle");
const storageState = await loginContext.storageState();
await loginContext.close();

const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  storageState,
  recordVideo: { dir: dirname(output), size: { width: 1440, height: 900 } },
});
const page = await context.newPage();

await page.goto(`${server}/ui/`, { waitUntil: "networkidle" });
const overviewMilliseconds = 3_000;
await page.waitForTimeout(overviewMilliseconds);
await page.goto(`${server}/ui/messages`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /conversation/i }).first().click();
await page.waitForLoadState("networkidle");

const holdMilliseconds = 2_000;
await page.waitForTimeout(holdMilliseconds);
const scrollMilliseconds = Math.max(
  2_000,
  seconds * 1_000 - overviewMilliseconds - holdMilliseconds * 2,
);
const steps = Math.max(1, Math.round(scrollMilliseconds / 250));
for (let step = 1; step <= steps; step += 1) {
  await page.evaluate(
    ({ current, total }) => {
      const maximum = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo({ top: maximum * (current / total), behavior: "instant" });
    },
    { current: step, total: steps },
  );
  await page.waitForTimeout(scrollMilliseconds / steps);
}
await page.waitForTimeout(holdMilliseconds);

const video = page.video();
if (!video) throw new Error("Playwright video recording did not start");
await page.close();
await video.saveAs(output);
await context.close();
await browser.close();
