// Headless browser walk through without npm dependencies (Node >=22 + Chrome).
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, syntheticResult] = process.argv.slice(2);
const directory = await mkdtemp(join(tmpdir(), "verity-document-ask-browser-"));
const browser = spawn(chrome, ["--headless=new", "--no-first-run", "--no-default-browser-check",
  "--disable-background-networking", "--disable-component-update", "--disable-sync",
  "--metrics-recording-only", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${directory}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let websocket;
try {
  const endpoint = await new Promise((resolve, reject) => {
    let output = "";
    const timer = setTimeout(() => reject(new Error("Chrome startup timeout")), 15000);
    browser.stderr.on("data", data => {
      output += data;
      const match = output.match(/DevTools listening on (ws:\/\/[^\s]+)/);
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
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error("UI condition timed out: " + expression);
  }
  async function ask(question, language) {
    await evaluate(`(() => {
      document.getElementById('question').value=${JSON.stringify(question)};
      document.getElementById('language').value=${JSON.stringify(language)};
      document.getElementById('ask-form').requestSubmit();
    })()`);
    await until("document.getElementById('status').textContent.includes('model not invoked') || document.getElementById('status').textContent.includes('Generated') || document.getElementById('status').textContent.includes('Synthetic')");
  }

  await send("Network.enable"); await send("Runtime.enable"); await send("Page.enable");
  await send("Page.navigate", { url });
  await until("document.getElementById('ask') && !document.getElementById('ask').disabled");
  assert.equal(await evaluate("location.hash"), "");

  await ask("What does the default local answer mode display?", "en");
  assert.match(await evaluate("document.getElementById('status').textContent"), /Sources only — model not invoked/);
  assert.ok(await evaluate("document.getElementById('passages').textContent.includes('The default local answer mode displays source passages.')"));
  assert.ok(await evaluate("document.getElementById('passages').textContent.includes('d:')"));
  assert.ok(await evaluate("document.getElementById('coverage-content').textContent.includes('not invoked')"));

  await ask("Hva viser kildevisningen?", "nb");
  assert.ok(await evaluate("document.getElementById('passages').textContent.includes('Kildevisningen viser originale dokumentutdrag.')"));
  assert.ok(await evaluate("document.getElementById('passages').textContent.includes('operator-no')"));

  await ask("What identifier does the CPU trial have?", "en");
  const conflictText = await evaluate("document.getElementById('passages').textContent");
  assert.match(await evaluate("document.getElementById('status').textContent"), /conflicting evidence/);
  assert.ok(conflictText.includes("RAG-CPU-01") && conflictText.includes("RAG-CPU-99"));

  const syntheticJSON = Buffer.from(syntheticResult, "base64").toString("utf8");
  await evaluate(`(() => {
    const original = window.fetch.bind(window);
    const result = JSON.parse(${JSON.stringify(syntheticJSON)});
    window.fetch = (url, options) => String(url).endsWith('/api/document-ask/ask') ? Promise.resolve(new Response(JSON.stringify(result), {status:200,headers:{'Content-Type':'application/json'}})) : original(url, options);
  })()`);
  await ask("Synthetic display check", "en");
  assert.match(await evaluate("document.getElementById('status').textContent"), /Synthetic generated-answer fixture — no native model run/);
  assert.ok(await evaluate("document.getElementById('answer').textContent.includes('The default local answer mode displays source passages.')"));
  assert.ok(await evaluate("document.getElementById('answer').textContent.includes('Citation: d:')"));

  await evaluate(`document.getElementById('question').value=${JSON.stringify("What does the default local answer mode display?")}; document.getElementById('language').value='en'; document.getElementById('prepare').click()`);
  await until("!document.getElementById('preparation').hidden");
  assert.ok(await evaluate("document.getElementById('prepare-content').textContent.includes('model_registration_unavailable')"));
  assert.equal(await evaluate("document.querySelectorAll('img,iframe,object').length"), 0);
  assert.ok(requests.every(request => new URL(request).origin === new URL(url).origin));
  assert.deepEqual(exceptions, []);
  console.log("Local document Ask: bilingual source-only, conflicts, citation inspection, synthetic answer display and request preparation passed");
} finally {
  if (websocket) websocket.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => browser.once("exit", resolve));
  await rm(directory, {recursive:true, force:true, maxRetries:5, retryDelay:100});
}
