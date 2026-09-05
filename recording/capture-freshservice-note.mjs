#!/usr/bin/env node

import { fileURLToPath } from "node:url";
import { isTicketUrl, ticketUrl } from "./config.mjs";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [output, ticketId] = process.argv.slice(2);
if (!output || !output.endsWith(".png") || !/^[1-9][0-9]*$/.test(ticketId || "")) {
  throw new Error("usage: capture-freshservice-note.mjs OUTPUT.png TICKET_ID");
}

ticketUrl(ticketId); // Validate configuration before connecting to a browser.
process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import(
  "playwright"
);
const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
const page = context.pages().find((candidate) => isTicketUrl(candidate.url(), ticketId));
if (!page) throw new Error(`Freshservice ticket #${ticketId} was not open`);

const author = page.getByText("Cora AI", { exact: true }).last();
const guidance = page.getByText(/AI-generated private guidance for operator review/i).last();
if ((await author.count()) !== 1 || (await guidance.count()) !== 1) {
  throw new Error("expected one visible Cora AI private guidance note");
}
await guidance.evaluate((element) =>
  element.scrollIntoView({ block: "center", behavior: "instant" }),
);
await page.waitForTimeout(700);
await page.screenshot({ path: output });
process.exit(0);
