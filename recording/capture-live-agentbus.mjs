#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [sshConfig, sshAlias, fullOutput, lateOutput] = process.argv.slice(2);
if (!lateOutput) {
  throw new Error(
    "usage: capture-live-agentbus.mjs SSH_CONFIG SSH_ALIAS FULL.png LATE.png",
  );
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
const { chromium } = await import("playwright");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const server = "http://127.0.0.1:17779";

await page.goto(`${server}/ui/`, { waitUntil: "networkidle" });
await page.locator('input[name="code"]').fill(session.code);
await page.locator('button[type="submit"]').click();
await page.waitForLoadState("networkidle");
await page.goto(`${server}/ui/messages`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /conversation/i }).first().click();
await page.waitForLoadState("networkidle");
await page.screenshot({ path: fullOutput, fullPage: true });
await page.evaluate(() => window.scrollTo({ top: 520, behavior: "instant" }));
await page.waitForTimeout(300);
await page.screenshot({ path: lateOutput });
await browser.close();
