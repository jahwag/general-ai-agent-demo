import test from "node:test";
import assert from "node:assert/strict";
import { freshserviceOrigin, ticketUrl, isTicketUrl } from "./config.mjs";

const env = { FRESHWORKS_BASE_URL: "https://demo.freshservice.com" };
test("recording requires explicit tenant configuration", () => {
  assert.throws(() => freshserviceOrigin({}), /FRESHWORKS_BASE_URL/);
  for (const value of ["http://demo.freshservice.com", "https://user:password@demo.freshservice.com", "https://demo.freshservice.com/a/tickets/5", "https://demo.freshservice.com?key=dummy", "https://demo.freshservice.com#fragment", "https://demo.freshservice.com:9443"]) {
    assert.throws(() => freshserviceOrigin({ FRESHWORKS_BASE_URL: value }));
  }
});
test("ticket IDs cannot change the configured route", () => {
  assert.equal(ticketUrl("5", env), "https://demo.freshservice.com/a/tickets/5");
  for (const id of [0, -1, "5/notes", "../5", "5?other=6", "", "05"]) {
    assert.throws(() => ticketUrl(id, env));
  }
});
test("capture remains restricted to the exact tenant and ticket", () => {
  assert.equal(isTicketUrl("https://demo.freshservice.com/a/tickets/5?tab=conversations", "5", env), true);
  for (const url of ["https://other.freshservice.com/a/tickets/5", "https://demo.freshservice.com.evil.invalid/a/tickets/5", "https://demo.freshservice.com/a/tickets/50", "http://demo.freshservice.com/a/tickets/5", "https://demo.freshservice.com:9443/a/tickets/5", "https://user:password@demo.freshservice.com/a/tickets/5", "not a URL"]) {
    assert.equal(isTicketUrl(url, "5", env), false, url);
  }
});
