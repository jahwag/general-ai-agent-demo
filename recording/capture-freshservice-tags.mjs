#!/usr/bin/env node

import { fileURLToPath } from "node:url";
import { isTicketUrl, ticketUrl } from "./config.mjs";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [output, ticketId = "2"] = process.argv.slice(2);
if (!output || !output.endsWith(".png") || !/^[1-9][0-9]*$/.test(ticketId)) {
  throw new Error("usage: capture-freshservice-tags.mjs OUTPUT.png [TICKET_ID]");
}

ticketUrl(ticketId); // Validate configuration before connecting to a browser.
process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import("playwright");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
const page = context.pages().find((candidate) => isTicketUrl(candidate.url(), ticketId));
if (!page) throw new Error(`Freshservice ticket #${ticketId} was not open`);

for (const tag of ["synthetic-ai-demo", "ai-assisted", "human-approved"]) {
  if ((await page.getByText(tag, { exact: true }).count()) !== 1) {
    throw new Error(`expected one visible ${tag} tag`);
  }
}
await page.getByText("human-approved", { exact: true }).scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
await page.screenshot({ path: output });
process.exit(0);
