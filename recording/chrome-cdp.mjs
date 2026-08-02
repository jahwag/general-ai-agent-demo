#!/usr/bin/env node

import { writeFile } from "node:fs/promises";

const endpoint = "http://127.0.0.1:9222";
const tenantHost = "example.freshservice.com";
const demoTicketUrl = `https://${tenantHost}/a/tickets/1`;

async function findDemoPage() {
  const targets = await fetch(`${endpoint}/json/list`).then((response) => response.json());
  const target = targets.find((item) => {
    try {
      return item.type === "page" && new URL(item.url).hostname === tenantHost;
    } catch {
      return false;
    }
  });
  if (!target) {
    throw new Error("dedicated Freshservice page is not open")
  }
  return target;
}

async function connect(target) {
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  let nextId = 1;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    clearTimeout(pending.get(message.id).timer);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });
  socket.addEventListener("close", () => {
    for (const { reject, timer } of pending.values()) {
      clearTimeout(timer);
      reject(new Error("Chrome closed the DevTools connection"));
    }
    pending.clear();
  });

  function call(method, params = {}) {
    const id = nextId++;
    socket.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`Chrome DevTools timeout: ${method}`));
      }, 10000);
      pending.set(id, { resolve, reject, timer });
    });
  }

  return { socket, call };
}

async function pageState(call) {
  const result = await call("Runtime.evaluate", {
    expression: "JSON.stringify({title: document.title, pathname: location.pathname})",
    returnByValue: true,
  });
  return JSON.parse(result.result.value);
}

async function main() {
  const [command, output] = process.argv.slice(2);
  if (!new Set(["status", "reload", "screenshot"]).has(command)) {
    throw new Error("usage: chrome-cdp.mjs status|reload|screenshot [OUTPUT.png]");
  }
  if (command === "screenshot" && !output) {
    throw new Error("screenshot requires an output path");
  }

  const target = await findDemoPage();
  const { socket, call } = await connect(target);
  try {
    await call("Page.enable");
    await call("Runtime.enable");
    await call("Page.bringToFront");
    await call("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    if (command === "reload") {
      const initialState = await pageState(call);
      if (initialState.pathname.includes("/tickets/1")) {
        await call("Page.reload", { ignoreCache: true });
      } else {
        try {
          await call("Runtime.evaluate", {
            expression: `location.assign(${JSON.stringify(demoTicketUrl)})`,
          });
        } catch (error) {
          if (!error.message.startsWith("Chrome DevTools timeout")) throw error;
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 5000));
      process.stdout.write('{"reload":"requested"}\n');
      return;
    }

    const state = await pageState(call);
    if (command === "screenshot") {
      if (!state.pathname.includes("/tickets/1")) {
        throw new Error(`refusing capture outside ticket #1: ${state.pathname}`);
      }
      await call("Runtime.evaluate", {
        expression: "window.scrollTo({top: 0, behavior: 'instant'})",
      });
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const result = await call("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: false,
      });
      await writeFile(output, Buffer.from(result.data, "base64"), { mode: 0o600 });
    }
    process.stdout.write(`${JSON.stringify(state)}\n`);
  } finally {
    socket.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
