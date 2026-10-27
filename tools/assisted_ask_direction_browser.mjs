// Minimal headless browser check for the versioned explicit-direction UI.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url] = process.argv.slice(2);
const profile = await mkdtemp(join(tmpdir(), "verity-direction-browser-"));
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
  let nextId = 0;
  const pending = new Map(), requests = [], exceptions = [];
  websocket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const call = pending.get(message.id); pending.delete(message.id);
      if (message.error) call.reject(new Error(message.error.message)); else call.resolve(message.result);
    }
    if (message.method === "Network.requestWillBeSent") requests.push(message.params.request);
    if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
  };
  function cdp(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++nextId; pending.set(id, { resolve, reject });
      websocket.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
  const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp("Target.attachToTarget", { targetId, flatten: true });
  const send = (method, params) => cdp(method, params, sessionId);
  const evaluate = async expression => {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const until = async expression => {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 30));
    }
    throw new Error("UI condition timed out: " + expression);
  };
  await send("Network.enable", {});
  await send("Page.enable", {});
  await send("Page.navigate", { url });
  await until("document.getElementById('direction') && !document.getElementById('direction').disabled");
  assert.equal(await evaluate("document.querySelector('.badge').textContent.includes('explicit direction')"), true);
  await evaluate("document.getElementById('preview').click()");
  assert.match(await evaluate("document.getElementById('status').textContent"), /Choose the entity, relationship and direction first/);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);

  async function select(language, direction) {
    await evaluate(`(() => {
      const language=document.getElementById('language'); language.value=${JSON.stringify(language)};
      language.dispatchEvent(new Event('change'));
      for (const [id,value] of [['entity',session.entity],['predicate',session.predicates.P856],['direction',${JSON.stringify(direction)}]]) {
        const element=document.getElementById(id); element.value=value; element.dispatchEvent(new Event('change'));
      }
    })()`);
  }
  async function preview(language, direction) {
    await select(language, direction);
    await evaluate("document.getElementById('preview').click()");
    await until("!document.getElementById('review').hidden");
    const review = await evaluate("({operation:document.getElementById('operation').textContent, relation:document.getElementById('relation').textContent, lang:document.documentElement.lang})");
    assert.equal(review.lang, language);
    assert.match(review.operation, direction === "reverse" ? /←/ : /→/);
    assert.match(review.relation, direction === "reverse" ? /does not create inverse RDF statements|oppretter ingen omvendte RDF-utsagn/ : /follows the relationship|følger relasjonen/);
    const request = requests.findLast(r => r.url.endsWith("/api/assisted-ask-v1-direction/preview"));
    assert.ok(request?.postData);
    assert.equal(JSON.parse(request.postData).direction, direction);
    await evaluate("document.getElementById('cancel').click()");
    await until("document.getElementById('review').hidden");
  }
  await preview("nb", "reverse");
  await preview("en", "forward");
  await select("en", "reverse");
  await evaluate("document.getElementById('preview').click()");
  await until("!document.getElementById('review').hidden");
  await evaluate("const direction=document.getElementById('direction'); direction.value='forward'; direction.dispatchEvent(new Event('change'))");
  await until("document.getElementById('review').hidden && document.getElementById('status').textContent.includes('Choices or question changed')");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/confirm")), false);
  assert.deepEqual(exceptions, []);
  console.log("Assisted Ask v1 direction browser: passed (loopback UI and Rust previews; no answer execution)");
} finally {
  if (websocket) websocket.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => browser.once("exit", resolve));
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
