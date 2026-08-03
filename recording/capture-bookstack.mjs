#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const [bookOutput, pageOutput, pageId = "3"] = process.argv.slice(2);
if (
  !bookOutput?.endsWith(".png") ||
  !pageOutput?.endsWith(".png") ||
  !/^[1-9][0-9]*$/.test(pageId)
) {
  throw new Error(
    "usage: capture-bookstack.mjs BOOK.png PAGE.png [PAGE_ID]",
  );
}

const passwordPath =
  process.env.BOOKSTACK_PASSWORD_FILE ??
  `${projectRoot}tmp/bookstack/admin-password`;
const password = (await readFile(passwordPath, "utf8")).trim();
if (password.length < 12) {
  throw new Error("BookStack password file is missing or invalid");
}

process.env.PLAYWRIGHT_BROWSERS_PATH = `${projectRoot}tmp/playwright/browsers`;
const { chromium } = await import(
  "../tmp/playwright/node_modules/playwright/index.mjs"
);
const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
let page = context.pages().find((candidate) => {
  try {
    const url = new URL(candidate.url());
    return url.hostname === "127.0.0.1" && url.port === "6875";
  } catch {
    return false;
  }
});
page ??= await context.newPage();
await page.setViewportSize({ width: 1440, height: 900 });

await page.goto(`http://127.0.0.1:6875/link/${pageId}`, {
  waitUntil: "domcontentloaded",
});
if (new URL(page.url()).pathname === "/login") {
  await page.locator('input[name="email"]').fill(
    "demo.knowledge.owner@example.invalid",
  );
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole("button", { name: "Log In", exact: true }).click();
  await page.waitForLoadState("networkidle");
  await page.goto(`http://127.0.0.1:6875/link/${pageId}`, {
    waitUntil: "networkidle",
  });
}

const bookLink = page.locator('a[href*="/books/"]').filter({
  hasText: "IT Service Desk",
}).first();
if ((await bookLink.count()) !== 1) {
  throw new Error("BookStack demo book link was not visible");
}
const bookUrl = await bookLink.getAttribute("href");
await page.goto(new URL(bookUrl, page.url()).toString(), {
  waitUntil: "networkidle",
});
await page.screenshot({ path: bookOutput });

await page.goto(`http://127.0.0.1:6875/link/${pageId}`, {
  waitUntil: "networkidle",
});
await page.getByText("Approved synthetic demo article", { exact: false }).waitFor();
await page.screenshot({ path: pageOutput });
process.exit(0);
