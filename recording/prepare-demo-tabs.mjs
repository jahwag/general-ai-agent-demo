#!/usr/bin/env node

const endpoint = "http://127.0.0.1:9222";
const ticketId = process.argv[2] ?? "2";
if (!/^[1-9][0-9]*$/.test(ticketId)) {
  throw new Error("usage: prepare-demo-tabs.mjs [TICKET_ID]");
}

const tabs = [
  {
    label: "Freshservice",
    url: `https://example.freshservice.com/a/tickets/${ticketId}`,
    matches: (url) => url === `/a/tickets/${ticketId}`,
  },
  {
    label: "Cora console",
    url: "http://127.0.0.1:17681/",
    matches: (url) => url === "http://127.0.0.1:17681/",
  },
  {
    label: "AgentBus cockpit",
    url: "http://127.0.0.1:18765/",
    matches: (url) => url === "http://127.0.0.1:18765/",
  },
];

async function targets() {
  const response = await fetch(`${endpoint}/json/list`);
  if (!response.ok) throw new Error(`Chrome target list failed: HTTP ${response.status}`);
  return response.json();
}

let current = await targets();
for (const tab of tabs) {
  const existing = current.find((target) => {
    try {
      const parsed = new URL(target.url);
      return tab.matches(parsed.hostname.includes("freshservice.com") ? parsed.pathname : target.url);
    } catch {
      return false;
    }
  });
  if (!existing) {
    const response = await fetch(
      `${endpoint}/json/new?${encodeURIComponent(tab.url)}`,
      { method: "PUT" },
    );
    if (!response.ok) throw new Error(`${tab.label} tab failed: HTTP ${response.status}`);
    current = await targets();
  }
}

const freshservice = current.find((target) => {
  try {
    const parsed = new URL(target.url);
    return (
      parsed.hostname === "example.freshservice.com" &&
      parsed.pathname === `/a/tickets/${ticketId}`
    );
  } catch {
    return false;
  }
});
if (!freshservice) throw new Error("Freshservice demo tab was not available");

const activated = await fetch(`${endpoint}/json/activate/${freshservice.id}`);
if (!activated.ok) throw new Error(`Freshservice activation failed: HTTP ${activated.status}`);
process.stdout.write(`Prepared three live demo tabs for synthetic ticket #${ticketId}.\n`);
