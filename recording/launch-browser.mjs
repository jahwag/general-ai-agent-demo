#!/usr/bin/env node

import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const demoTicketId = process.argv[2] ?? "2";
if (!/^[1-9][0-9]*$/.test(demoTicketId)) {
  throw new Error("usage: launch-browser.mjs [TICKET_ID]");
}
process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("../tmp/playwright/node_modules/playwright/index.mjs");

const context = await chromium.launchPersistentContext(
  `${projectRoot}tmp/playwright-profile`,
  {
    headless: false,
    viewport: { width: 1440, height: 900 },
    args: [
      "--remote-debugging-address=127.0.0.1",
      "--remote-debugging-port=9222",
      "--window-position=100,100",
      "--window-size=1440,900",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--disable-session-crashed-bubble",
      "--hide-crash-restore-bubble",
    ],
  },
);

const page = context.pages()[0] ?? (await context.newPage());
try {
  await page.goto(
    `https://example.freshservice.com/a/tickets/${demoTicketId}`,
    {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    },
  );
} catch (error) {
  process.stderr.write(`initial navigation did not settle: ${error.message}\n`);
}

process.stdout.write("Freshservice demo browser is open; log in if prompted.\n");

async function close() {
  await context.close();
  process.exit(0);
}
process.once("SIGINT", close);
process.once("SIGTERM", close);
await new Promise(() => {});
