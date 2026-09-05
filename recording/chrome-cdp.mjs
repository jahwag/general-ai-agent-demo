#!/usr/bin/env node

import { writeFile } from "node:fs/promises";
import { freshserviceOrigin, ticketUrl, isTicketUrl } from "./config.mjs";

const endpoint = "http://127.0.0.1:9222";
const tenantOrigin = freshserviceOrigin();
const demoTicketId = process.env.DEMO_TICKET_ID ?? "2";
if (!/^[1-9][0-9]*$/.test(demoTicketId)) {
  throw new Error("DEMO_TICKET_ID must be a positive integer");
}
const demoTicketUrl = ticketUrl(demoTicketId);

async function findDemoPage() {
  const targets = await fetch(`${endpoint}/json/list`).then((response) => response.json());
  const target = targets.find((item) => {
    try {
      return item.type === "page" && new URL(item.url).origin === tenantOrigin;
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
    expression: "JSON.stringify({title: document.title, pathname: location.pathname, url: location.href})",
    returnByValue: true,
  });
  return JSON.parse(result.result.value);
}

async function main() {
  const [command, output] = process.argv.slice(2);
  if (!new Set(["status", "reload", "screenshot", "screenshot-solution"]).has(command)) {
    throw new Error(
      "usage: chrome-cdp.mjs status|reload|screenshot|screenshot-solution [OUTPUT.png]",
    );
  }
  if (command.startsWith("screenshot") && !output) {
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
      if (isTicketUrl(initialState.url, demoTicketId)) {
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
    if (command === "screenshot" || command === "screenshot-solution") {
      if (!isTicketUrl(state.url, demoTicketId)) {
        throw new Error(`refusing capture outside ticket #${demoTicketId}: ${state.pathname}`);
      }
      await call("Runtime.evaluate", {
        expression:
          command === "screenshot-solution"
            ? `(() => {
                const element = [...document.querySelectorAll("*")].find(
                  (candidate) =>
                    candidate.children.length === 0 &&
                    candidate.textContent?.trim().startsWith("APPROVE AI "),
                );
                element?.scrollIntoView({block: "center", behavior: "instant"});
                return Boolean(element);
              })()`
            : "window.scrollTo({top: 0, behavior: 'instant'})",
      });
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const result = await call("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: false,
      });
      await writeFile(output, Buffer.from(result.data, "base64"), { mode: 0o600 });
    }
    process.stdout.write(`${JSON.stringify({ title: state.title, pathname: state.pathname })}\n`);
  } finally {
    socket.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
