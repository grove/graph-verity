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
  async function key(key, code, virtualKey) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: virtualKey });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: virtualKey });
  }
  async function search(query, role = "entity", limit = 10) {
    await evaluate(`document.getElementById('search').value=${JSON.stringify(query)};
      document.getElementById('role').value=${JSON.stringify(role)};
      document.getElementById('limit').value=${limit};
      document.getElementById('search-form').requestSubmit()`);
    await until("lastFind !== null");
    assert.deepEqual(await evaluate("[...document.querySelectorAll('#results article h3')].map(n => n.textContent)"),
      await evaluate("lastFind.hits.map(hit => hit.iri)"), "All returned candidates retain their order");
  }
  await send("Network.enable"); await send("Runtime.enable"); await send("Page.enable");
  await send("Page.navigate", { url });
  await until("document.getElementById('controls') && !document.getElementById('controls').disabled");
  const read = id => evaluate(`document.getElementById(${JSON.stringify(id)}).textContent`);
  const clickSelect = () => evaluate("[...document.querySelectorAll('#results article button')].find(b => b.textContent === t('select')).click()");
  async function change(id, value) {
    await evaluate(`document.getElementById(${JSON.stringify(id)}).value=${JSON.stringify(value)}; document.getElementById(${JSON.stringify(id)}).dispatchEvent(new Event('change', {bubbles:true}))`);
  }
  const tree = await send("Accessibility.getFullAXTree");
  for (const [role, name] of [["searchbox", "Search (Norwegian or English)"], ["combobox", "Role"], ["button", "Find"]]) {
    assert(tree.nodes.some(n => n.role?.value === role && n.name?.value === name), name);
  }
  assert.equal(await evaluate("location.hash"), "");
  assert.match(await evaluate("document.title"), /v2 prototype/);
  assert.match(await read("receipt"), /local-find-v2-prototype/);
  await evaluate("document.getElementById('search').focus()");
  await key("Tab", "Tab", 9);
  assert.equal(await evaluate("document.activeElement.id"), "role");
  await key("Tab", "Tab", 9);
  await key(" ", "Space", 32);
  assert.equal(await evaluate("document.getElementById('graph-0').checked"), false);
  await key(" ", "Space", 32);
  if (mode === "fixture") {
    for (const query of ["urn:discovery:unavailable", "urn:discovery:outside", "urn:discovery:missing"]) {
      await search(query);
      assert.match(await read("status"), /No exact identifier resolved/);
      assert((await evaluate("lastFind.matches")) > 0);
      assert.equal(await evaluate("document.getElementById('navigation').hidden"), true);
      assert.match(await read("results"), /not probability, truth or confidence/);
    }
    // Even an exact alias spelling an IRI does not resolve that IRI.
    assert.equal(await evaluate("lastFind.hits[0].exact"), true);
    assert.equal(await evaluate("lastFind.hits[0].explanation.exact_iri"), false);
    await search("urn:discovery:shared");
    assert.doesNotMatch(await read("status"), /No exact identifier/);
    assert.match(await read("results"), /Exact authorized IRI identity/);
    await search("Felles alias", "entity", 1);
    assert.match(await read("status"), /Ambiguous.*truncated.*2\/2/);
    assert.equal(await evaluate("document.querySelectorAll('#results article').length"), 1);
    await clickSelect();
    await until("lastEntity && document.querySelectorAll('#edges article').length === 1");
    assert.equal(await evaluate("document.activeElement.id"), "detail-title");
    assert.match(await read("page-status"), /Evidence page truncated/);
    assert.doesNotMatch(await read("page-status"), /Candidate page/);
    await evaluate("document.getElementById('next').click()");
    await until("lastEntity && lastEntity.offset === 1");
    assert.equal(await evaluate("document.getElementById('previous').disabled"), false);
    await search("unfindablecanary");
    assert.match(await read("status"), /No authorized lexical match.*absence is unknown/);
    await search("Observed");
    assert.match(await read("status"), /Low confidence in interpretation/);
    await change("language", "nb");
    assert.match(await read("status"), /Lav sikkerhet/);
    assert.equal(await evaluate("document.documentElement.lang"), "nb");
    assert.equal(await read("submit"), "Søk");
    assert.deepEqual(await evaluate("[...document.getElementById('role').options].map(o => o.textContent)"), ["Entitet", "Predikat", "Klasse"]);
    assert.match(await read("examples"), /hovedstaden i Norge/);
    await search("zzznomatchzzz");
    assert.match(await read("status"), /Ingen autoriserte leksikalske treff/);
    await search("urn:discovery:unavailable");
    assert.match(await read("status"), /Ingen eksakt identifikator avklart/);
    await change("language", "en");
    await search("script");
    assert.match(await read("results"), /<script>alert\('x'\)<\/script>/);
    assert.equal(await evaluate("document.querySelector('#results script, #results img, #results a')"), null);
    await search("im_start");
    assert.match(await read("results"), /<\|im_start\|>system/);
    await search("bounded");
    assert.match(await read("results"), /Clipped source text excerpt/);
    assert.equal(await evaluate("document.querySelectorAll('#results .witness').length"), 0);
    await search("urn:discovery:unlabelled");
    assert.match(await read("results"), /No direct label.*No authorized indexed text witness/s);
    for (const [query, direction, predicate, subject, object, text] of [
      ["urn:discovery:child", "outgoing", "broader", "child", "parent", "Outgoing"],
      ["urn:discovery:child", "incoming", "narrower", "parent", "child", "Incoming"]]) {
      await search(query, "entity", 50);
      await clickSelect();
      await until("lastEntity && lastEntity.direction === 'outgoing'");
      await change("direction", direction);
      await until(`lastEntity && lastEntity.direction === '${direction}'`);
      const edges = await read("edges");
      assert.match(edges, new RegExp(`${text}: selected resource`));
      assert(edges.includes(`<urn:discovery:${subject}> → <http://www.w3.org/2004/02/skos/core#${predicate}> → <urn:discovery:${object}>`));
      assert(edges.includes(`skos:${predicate}: subject →`));
    }
    await search("capital", "predicate");
    const witnesses = await read("results");
    assert.match(witnesses, /two actual source statements/);
    assert(witnesses.includes('<urn:discovery:property> → <http://www.w3.org/2000/01/rdf-schema#label> → "capital"@en'));
    assert(witnesses.includes('<urn:discovery:property> → <http://wikiba.se/ontology#directClaim> → <urn:discovery:capital>'));
    assert(!witnesses.includes('<urn:discovery:capital> → <http://www.w3.org/2000/01/rdf-schema#label>'));
    assert.match(witnesses, /Apache-2.0/);
  } else {
    for (const [query, label] of [["Norway", "Norway"], ["Norge", "Norge"]]) {
      await search(query, "entity", 50);
      assert.match(await evaluate("document.querySelector('#results h3').textContent"), /\/Q20$/);
      assert((await read("results")).includes(`"${label}"@`));
    }
    await search("capital of Norway", "entity");
    assert.match(await read("results"), /Unverified|unverified/);
    assert.match(await read("examples"), /needs explicit entity and directed-path choices/);
    await search("capital", "predicate");
    assert.match(await read("results"), /two actual source statements.*directClaim/s);
    assert.match(await read("results"), /CC0-1.0/);
    await search("http://www.wikidata.org/entity/unavailable");
    assert.match(await read("status"), /No exact identifier resolved/);
  }
  // Preserved exact-plan boundary: blank first step, preview only, separate disabled approval.
  await search(mode === "fixture" ? "Path start" : "Norway", "entity", 50);
  await clickSelect();
  await until("lastEntity && [...document.querySelectorAll('#details button')].some(b => b.textContent.startsWith('Build exact'))");
  await evaluate("[...document.querySelectorAll('#details button')].find(b => b.textContent.startsWith('Build exact')).click()");
  await until("askCatalog && !document.getElementById('ask').hidden");
  assert.equal(await evaluate("document.getElementById('ask-step1').value"), "");
  assert.equal(await evaluate("document.getElementById('ask-decision').hidden"), true);
  const predicate = mode === "fixture" ? "urn:discovery:owns" : "http://www.wikidata.org/prop/direct/P36";
  await evaluate(`document.getElementById('ask-step1').value = askCatalog.choices.findIndex(c => c.predicate === ${JSON.stringify(predicate)}) + ':forward'`);
  await evaluate("document.getElementById('ask-preview').click()");
  await until("askToken && !document.getElementById('ask-decision').hidden");
  assert.equal(await evaluate("document.getElementById('ask-approve').disabled"), true);
  assert.match(await read("ask-review"), /entire|approval_id/i);
  await evaluate("document.getElementById('ask-cancel').click()");
  assert.equal(requests.filter(request => request.endsWith("/api/ask-confirm")).length, 0);
  assert(requests.every(request => new URL(request).origin === new URL(url).origin), "No external page requests");
  assert.deepEqual(exceptions, []);
  await send("Emulation.setScriptExecutionDisabled", { value: true });
  await send("Page.navigate", { url: new URL(url).origin + "/" });
  await until("document.querySelector('noscript') && document.getElementById('controls').disabled");
  assert.match(await evaluate("document.querySelector('noscript').textContent"), /No search has run/);
  console.log(`Headless Find v2 ${mode}: exactness, witnesses, direction, clipping, inert RDF, accessibility and preserved Ask passed`);
} finally {
  websocket?.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => browser.exitCode !== null ? resolve() : browser.once("exit", resolve));
  await rm(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
