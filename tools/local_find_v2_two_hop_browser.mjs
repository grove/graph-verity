// Narrow real-graph browser regression for the v2 two-hop path explorer.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url] = process.argv.slice(2);
const profile = await mkdtemp(join(tmpdir(), "verity-two-hop-"));
const browser = spawn(chrome, ["--headless=new", "--no-first-run", "--no-default-browser-check",
  "--disable-background-networking", "--disable-component-update", "--disable-sync",
  "--metrics-recording-only", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${profile}`, "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
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
  let id = 0;
  const pending = new Map(), requests = [];
  websocket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const task = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) task.reject(new Error(message.error.message));
      else task.resolve(message.result);
    }
    if (message.method === "Network.requestWillBeSent") requests.push(message.params.request.url);
  };
  function cdp(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      websocket.send(JSON.stringify({ id: requestId, method, params, sessionId }));
    });
  }
  const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp("Target.attachToTarget", { targetId, flatten: true });
  const send = (method, params) => cdp(method, params, sessionId);
  async function evaluate(expression) {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
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
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  await send("Page.navigate", { url });
  await until("document.getElementById('controls') && !document.getElementById('controls').disabled");
  const oslo = "http://www.wikidata.org/entity/Q585", trondheim = "http://www.wikidata.org/entity/Q26793";
  await evaluate(`document.getElementById('search').value=${JSON.stringify(oslo)};
    document.getElementById('role').value='entity'; document.getElementById('limit').value=50;
    document.getElementById('search-form').requestSubmit()`);
  await until(`lastFind && lastFind.hits.some(hit => hit.iri === ${JSON.stringify(oslo)})`);
  await evaluate("[...document.querySelectorAll('#results article button')].find(b => b.textContent === t('select')).click()");
  await until(`lastEntity && lastEntity.iri === ${JSON.stringify(oslo)}`);
  await evaluate("[...document.querySelectorAll('#details button')].find(b => b.textContent === t('twoHopAction')).click()");
  await until("twoHopResult && !twoHopResult.loading");
  const path = await evaluate(`twoHopResult.paths.find(p => p.intermediate === 'http://www.wikidata.org/entity/Q20' && p.endpoint === ${JSON.stringify(trondheim)})`);
  assert(path, "Oslo → Norway → Trondheim must use source statements");
  assert.equal(path.first_direction, "outgoing");
  assert.equal(path.first_statement.subject.value, oslo);
  assert.equal(path.first_statement.object.value, "http://www.wikidata.org/entity/Q20");
  assert.equal(path.second_direction, "incoming");
  assert.equal(path.second_statement.subject.value, trondheim);
  assert.equal(path.second_statement.object.value, "http://www.wikidata.org/entity/Q20");
  assert.equal(path.first_statement.source_graph.value, "urn:graph-verity:wikidata:development");
  assert.equal(path.second_statement.source_graph.value, "urn:graph-verity:wikidata:development");
  assert.match(await evaluate("document.getElementById('two-hop-panel').textContent"), /not question relevance/);
  await evaluate("document.getElementById('language').value='nb'; document.getElementById('language').dispatchEvent(new Event('change', {bubbles:true}))");
  assert.match(await evaluate("document.getElementById('two-hop-panel').textContent"), /Traverseringsrekkefølgen/);
  await evaluate("document.getElementById('language').value='en'; document.getElementById('language').dispatchEvent(new Event('change', {bubbles:true}))");
  await evaluate(`[...document.querySelectorAll('#two-hop-results article')].find(card => card.querySelector('h4')?.textContent === ${JSON.stringify(trondheim)}).querySelector('button').click()`);
  await until(`lastEntity && lastEntity.iri === ${JSON.stringify(trondheim)}`);
  assert.equal(await evaluate("document.getElementById('two-hop-panel').hidden"), true);
  assert.equal(requests.some(request => request.endsWith("/api/ask-preview") || request.endsWith("/api/ask-confirm")), false);
  assert.deepEqual(requests.map(request => new URL(request).origin).filter(origin => origin !== new URL(url).origin), []);
  console.log("Headless Find v2 Wikidata two-hop path: witnesses, direction, language, navigation, and no Ask passed");
} finally {
  websocket?.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => browser.exitCode !== null ? resolve() : browser.once("exit", resolve));
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
