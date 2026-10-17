// Headless browser integration without npm dependencies (Node >=22 + installed Chrome).
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, mode = "fixture"] = process.argv.slice(2);
const directory = await mkdtemp(join(tmpdir(), "verity-browser-"));
const browser = spawn(chrome, ["--headless=new", "--no-first-run", "--no-default-browser-check",
  "--disable-background-networking", "--disable-component-update", "--disable-sync",
  "--metrics-recording-only", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${directory}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let websocket;
try {
  const endpoint = await new Promise((resolve, reject) => {
    let text = "";
    const timer = setTimeout(() => reject(new Error("Chrome startup timeout")), 15000);
    browser.stderr.on("data", data => {
      text += data;
      const match = text.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
    browser.on("exit", () => { clearTimeout(timer); reject(new Error("Chrome exited")); });
    browser.on("error", reject);
  });
  websocket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => { websocket.onopen = resolve; websocket.onerror = reject; });
  let counter = 0;
  const pending = new Map(), requests = [], exceptions = [];
  websocket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const task = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) task.reject(new Error(message.error.message));
      else task.resolve(message.result);
    }
    if (message.method === "Network.requestWillBeSent") requests.push(message.params.request.url);
    if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
  };
  function cdp(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++counter;
      pending.set(id, { resolve, reject });
      websocket.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
  const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp("Target.attachToTarget", { targetId, flatten: true });
  const send = (method, params) => cdp(method, params, sessionId);
  async function evaluate(expression) {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  }
  async function until(expression) {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 30));
    }
    throw new Error("UI condition timed out: " + expression);
  }
  async function key(key, code, virtualKey) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: virtualKey });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: virtualKey });
  }
  async function search(query, role = "entity", limit = 10) {
    await evaluate(`document.getElementById('search').value=${JSON.stringify(query)};
      document.getElementById('role').value=${JSON.stringify(role)};
      document.getElementById('limit').value=${limit};
      document.getElementById('search-form').requestSubmit()`);
    await until("!document.getElementById('status').textContent.includes('Reading') && document.getElementById('status').textContent.length > 0");
  }
  await send("Network.enable"); await send("Runtime.enable"); await send("Page.enable");
  await send("Page.navigate", { url });
  await until("document.getElementById('controls') && !document.getElementById('controls').disabled");
  assert.equal(await evaluate("location.hash"), "");
  const tree = await send("Accessibility.getFullAXTree");
  for (const [role, name] of [["searchbox", "Search (Norwegian or English)"], ["combobox", "Role"],
                            ["button", "Find"], ["checkbox", mode === "fixture" ? "urn:discovery:a" : "urn:graph-verity:wikidata:development"]]) {
    assert(tree.nodes.some(n => n.role?.value === role && n.name?.value === name), `${role} accessible name: ${name}`);
  }
  // Tab traversal and space activation operate real focused controls.
  await evaluate("document.getElementById('search').focus()");
  await key("Tab", "Tab", 9);
  assert.equal(await evaluate("document.activeElement.id"), "role");
  await key("Tab", "Tab", 9);
  assert.equal(await evaluate("document.activeElement.id"), "graph-0");
  await key(" ", "Space", 32);
  assert.equal(await evaluate("document.getElementById('graph-0').checked"), false);
  await key(" ", "Space", 32);
  assert.equal(await evaluate("document.getElementById('graph-0').checked"), true);

  if (mode === "fixture") {
    await search("Island", "entity", 1);
    assert.match(await evaluate("document.getElementById('status').textContent"), /Ambiguous.*Truncated/);
    await evaluate("document.querySelector('#results article button').click()");
    await until("document.querySelectorAll('#edges article').length === 1");
    assert.equal(await evaluate("document.activeElement.id"), "detail-title");
    assert.equal(await evaluate("document.getElementById('next').disabled"), false);
    await evaluate("document.getElementById('next').click()");
    await until("document.getElementById('page-status').textContent.includes('offset 1.')");
    assert.equal(await evaluate("document.getElementById('previous').disabled"), false);
    await search("script");
    assert.match(await evaluate("document.getElementById('results').textContent"), /<script>alert\('x'\)<\/script>/);
    assert.equal(await evaluate("document.scripts.length"), 1);
    await search("im_start");
    assert.match(await evaluate("document.getElementById('results').textContent"), /<\|im_start\|>system/);
    await search("unfindablecanary");
    assert.match(await evaluate("document.getElementById('status').textContent"), /No retrieved match.*absence.*unknown/);
    await search("Observed");
    assert.match(await evaluate("document.getElementById('status').textContent"), /Low confidence/);
    await evaluate("document.getElementById('language').value='nb'; document.getElementById('language').dispatchEvent(new Event('change'))");
    assert.equal(await evaluate("document.documentElement.lang"), "nb");
    assert.equal(await evaluate("document.getElementById('submit').textContent"), "Søk");
    assert.match(await evaluate("document.getElementById('status').textContent"), /Lav sikkerhet/);
  } else {
    for (const query of ["Norge", "Norway"]) {
      await search(query, "entity", 50);
      assert.match(await evaluate("document.querySelector('#results h3').textContent"), /\/Q20$/);
    }
    await evaluate("document.querySelector('#results article button').click()");
    await until("[...document.querySelectorAll('#edges article')].some(e => e.textContent.includes('/P36'))");
    assert.match(await evaluate("document.getElementById('details').textContent"), /CC0-1.0/);
    await evaluate("[...document.querySelectorAll('#edges button')].find(b => b.textContent.endsWith('/P36')).click()");
    await until("document.getElementById('direction').value === 'predicate' && document.querySelectorAll('#edges article').length > 0");
    assert.match(await evaluate("document.getElementById('selection').textContent"), /\/P36/);
    await evaluate("[...document.querySelectorAll('#edges button')].find(b => b.textContent.endsWith('/Q585')).click()");
    await until("document.getElementById('direction').value === 'incoming' && document.querySelectorAll('#edges article').length > 0");
    assert.match(await evaluate("document.getElementById('selection').textContent"), /\/Q585/);
    const exact = await evaluate("[...document.querySelectorAll('#edges article')].some(e => e.textContent.includes('/Q20') && e.textContent.includes('/P36') && e.textContent.includes('/Q585'))");
    assert.equal(exact, true);
    await search("capital", "predicate");
    assert.match(await evaluate("document.getElementById('results').textContent"), /directClaim/);
    assert.match(await evaluate("document.getElementById('results').textContent"), /not an invented label triple/);
  }
  assert.equal(await evaluate("document.body.textContent.includes('PRIVATE_')"), false);
  assert(requests.every(request => new URL(request).origin === new URL(url).origin), "No third-party requests");
  assert.deepEqual(exceptions, []);
  // A fresh no-JavaScript navigation has a visible fallback and no enabled controls.
  await send("Emulation.setScriptExecutionDisabled", { value: true });
  await send("Page.navigate", { url: new URL(url).origin + "/" });
  await until("document.querySelector('noscript') && document.getElementById('controls').disabled");
  assert.match(await evaluate("document.querySelector('noscript').textContent"), /No search has run/);
  console.log(`Headless Find ${mode}: walkthrough, inert text, keyboard/AX, offline requests and no-JS fallback passed`);
} finally {
  websocket?.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => browser.exitCode !== null ? resolve() : browser.once("exit", resolve));
  await rm(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
