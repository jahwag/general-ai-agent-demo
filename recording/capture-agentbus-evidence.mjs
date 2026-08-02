#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [agentbusBin, server, adminTokenFile, fullOutput, lateOutput] = process.argv.slice(2);
if (!lateOutput) {
  throw new Error(
    "usage: capture-agentbus-evidence.mjs AGENTBUS_BIN SERVER ADMIN_TOKEN FULL.png LATE.png",
  );
}

const session = JSON.parse(
  execFileSync(
    agentbusBin,
    ["ui-session", "--server", server, "--admin-token-file", adminTokenFile],
    { encoding: "utf8" },
  ),
);

process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("../tmp/playwright/node_modules/playwright/index.mjs");
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

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

