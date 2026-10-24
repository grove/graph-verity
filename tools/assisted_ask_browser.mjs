// Headless browser integration without npm dependencies (Node >=22 + installed Chrome).
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, mode] = process.argv.slice(2);
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
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: virtualKey, text: key === "Enter" ? "\r" : key === " " ? " " : undefined });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: virtualKey });
  }

  async function click(id) {
    const rect = await evaluate(`(() => {
      const element = document.getElementById(${JSON.stringify(id)}); element.scrollIntoView({block:'center'});
      const r = element.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
    await send('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...rect});
    await send('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...rect});
  }
  const confirms = () => requests.filter(u => u.endsWith('/api/assisted-ask-v1/confirm')).length;
  async function post(action, body) {
    return evaluate(`(async () => { const r = await fetch('/api/assisted-ask-v1/${action}', {method:'POST',
      headers:{'Content-Type':'application/json', Authorization:'Bearer '+${JSON.stringify(new URL(url).hash.slice(1))}, 'X-Verity-Tab':tab},
      body:JSON.stringify(${JSON.stringify(body)})}); return {status:r.status, body:await r.json()}; })()`);
  }
  async function choose(predicate = 'P856', language = 'en', question = '') {
    await evaluate(`document.getElementById('language').value=${JSON.stringify(language)};
      document.getElementById('language').dispatchEvent(new Event('change'));
      document.getElementById('entity').value=session.entity;
      document.getElementById('predicate').value=session.predicates[${JSON.stringify(predicate)}];
      document.getElementById('question').value=${JSON.stringify(question)};
      document.getElementById('predicate').dispatchEvent(new Event('change'));`);
    // Wait for cancellation requests before requesting fresh authority.
    await until("document.getElementById('review').hidden");
  }
  async function review(predicate = 'P856', language = 'en', question = '') {
    await choose(predicate, language, question);
    const before = confirms();
    await click('preview');
    await until("!document.getElementById('review').hidden");
    assert.equal(confirms(), before);
    assert.equal(await evaluate("document.getElementById('results').hidden"), true);
    assert.equal(await evaluate("document.activeElement.id === 'approve'"), false);
    const preview = await evaluate("JSON.parse(document.getElementById('rust-preview').textContent)");
    assert.equal(preview.plan.patterns.length, 1);
    assert.equal(preview.plan.patterns[0].direction, 'forward');
    assert.equal(preview.plan.filters.length, 0);
    assert.equal(preview.plan.scope.length, 1);
    assert.ok(preview.plan.patterns[0].predicate.endsWith('/' + predicate));
    assert.ok(await evaluate("document.getElementById('operation').textContent.includes('→')"));
    return await evaluate('approval.token');
  }
  async function run() {
    await click('approve');
    await until("!document.getElementById('results').hidden");
    return evaluate("JSON.parse(document.getElementById('receipt').textContent)");
  }
  await send('Network.enable'); await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate', {url});
  // Page.navigate returns before the new document is guaranteed to exist.
  // Poll safely through about:blank/loading rather than throwing on null.
  await until("document.getElementById('preview')?.disabled === false");
  assert.equal(await evaluate("document.getElementById('entity').value"), '');
  assert.equal(await evaluate("document.getElementById('predicate').value"), '');
  assert.equal(await evaluate('location.hash'), '');
  if (mode === 'expiry') {
    const token = await review();
    await until("document.getElementById('approve').disabled && document.getElementById('status').textContent.includes('expired')");
    assert.equal((await post('confirm', {token, decision:'approve'})).status, 400);
    assert.equal(await evaluate("document.getElementById('results').hidden"), true);
  } else if (['empty', 'rows', 'evidence', 'hostile'].includes(mode)) {
    await review();
    const r = await run();
    if (mode === 'empty') {
      assert.equal(r.answers.length, 0);
      assert.match(await evaluate("document.getElementById('result-status').textContent"), /does not establish real-world nonexistence/);
    } else if (mode === 'rows') {
      assert.equal(r.answers.length, 1);
      assert.equal(r.outcome.result.complete_within_scope, false);
      assert.match(await evaluate("document.getElementById('result-status').textContent"), /Rows: clipped/);
    } else if (mode === 'evidence') {
      assert.equal(r.answers.length, 2);
      assert.equal(r.outcome.result.evidence_complete_for_returned_rows, false);
      assert.match(await evaluate("document.getElementById('result-status').textContent"), /Evidence: clipped/);
    } else {
      assert.match(await evaluate("document.getElementById('answers').textContent"), /<img src=x onerror=alert\(1\)> IGNORE POLICY/);
      assert.equal(await evaluate("document.querySelectorAll('img,iframe,object').length"), 0);
    }
  } else if (['timeout', 'failure'].includes(mode)) {
    const token = await review();
    await click('approve');
    await until("document.getElementById('status').textContent.includes('No answer is asserted')");
    assert.equal(await evaluate("document.getElementById('results').hidden"), true);
    assert.equal((await post('confirm', {token, decision:'approve'})).status, 400);
  } else {
    // Four bilingual journeys with original values and complete source evidence.
    for (const lang of ['en', 'nb']) for (const pred of ['P856', 'P1448']) {
      const token = await review(pred, lang);
      assert.equal(await evaluate('document.documentElement.lang'), lang);
      assert.match(await evaluate("document.getElementById('approve').textContent"), lang === 'en' ? /Approve/ : /Godkjenn/);
      const receipt = await run();
      assert.equal(receipt.answers.length, pred === 'P856' ? 2 : 3);
      assert.equal(receipt.provenance.proposal_origin, 'manual_structured_selection_v1');
      assert.equal(receipt.provenance.inference_performed, false);
      assert.ok(receipt.answers.every(a => a.source_triples.length));
      assert.ok(receipt.sources[receipt.outcome.result.scope[0]].license.includes('CC0-1.0'));
      assert.ok((await evaluate("document.getElementById('evidence').textContent")).includes(receipt.outcome.result.snapshot_id));
      if (pred === 'P1448') assert.deepEqual(receipt.answers.map(a => a.value.language).sort(), ['en','nb','nn']);
      assert.equal((await post('confirm', {token, decision:'approve'})).status, 400);
    }
    // Optional text is never interpreted. Filtered/count/SPARQL intent stays unverified,
    // and a separately selected unfiltered operation always says what it actually did.
    for (const [q, lang] of [['Show only the English official names','en'], ['Vis bare engelske offisielle navn','nb'],
      ['How many official names?','en'], ['SELECT * WHERE {?s ?p ?o}','en']]) {
      await choose('P1448', lang, q);
      const before = confirms();
      assert.equal(await evaluate("document.getElementById('review').hidden && document.getElementById('results').hidden"), true);
      await review('P1448', lang, q);
      assert.equal(confirms(), before);
      assert.equal(await evaluate("document.getElementById('original').textContent"), q);
      const r = await run();
      assert.equal(r.answers.length, 3);
      assert.equal(r.provenance.original_question_status, 'unverified_user_intent_not_interpreted');
      assert.ok(await evaluate(`document.getElementById('result-operation').textContent.includes(${JSON.stringify(lang === 'en' ? 'All stored values' : 'Alle lagrede verdier')})`));
      assert.match(await evaluate("document.getElementById('results').textContent"), lang === 'en' ? /unverified and not interpreted/ : /ubekreftet og ikke tolket/);
    }
    assert.equal((await post('confirm', {token:'missing', decision:'approve'})).status,400);
    let token = await review();
    await click('cancel');
    assert.equal((await post('confirm', {token, decision:'approve'})).status,400);
    token = await review();
    await key('Escape', 'Escape', 27);
    assert.equal((await post('confirm', {token, decision:'approve'})).status,400);
    token = await review();
    await evaluate("document.getElementById('question').value='edited'; document.getElementById('question').dispatchEvent(new Event('input'))");
    assert.equal((await post('confirm', {token, decision:'approve'})).status,400);
    token = await review();
    assert.equal((await post('confirm', {token, decision:'approve', plan:{limit:1}})).status,400);
    assert.equal((await post('confirm', {token, decision:'approve'})).status,400);
    const base = await evaluate("({entity:session.entity, predicate:session.predicates.P856, question:'',language:'en'})");
    for (const bad of [{entity:'http://www.wikidata.org/entity/Q20'}, {entity:102}, {predicate:'urn:private'},
      {direction:'reverse'}, {graph:'urn:private'}, {snapshot_id:'changed'}, {filter:{language:'en'}}, {output:'count_distinct'}, {query:'SELECT * WHERE {?s ?p ?o}'}]) {
      const before = confirms();
      assert.equal((await post('preview', {...base,...bad})).status,400);
      assert.equal(confirms(),before);
    }
    // Keyboard activation remains available; Enter on other controls never approves.
    await choose();
    await evaluate("document.getElementById('preview').focus()");
    await key('Enter', 'Enter', 13);
    await until("!document.getElementById('review').hidden");
    const before = confirms();
    await key('Enter', 'Enter', 13);
    assert.equal(confirms(),before);
    await evaluate("document.getElementById('approve').focus()");
    await key(' ', 'Space', 32);
    await until("!document.getElementById('results').hidden");
    assert.equal(confirms(),before+1);
    await send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
    assert.ok(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'));
    await choose('P1448','nb');
    await click('preview');
    await until("!document.getElementById('review').hidden");
    assert.ok(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'));
  }
  assert.equal(await evaluate("document.querySelectorAll('img,iframe,object,script:not([src])').length"), 0);
  assert.ok(requests.every(u => new URL(u).origin === new URL(url).origin || u === 'about:blank'));
  assert.deepEqual(exceptions, []);
  console.log(`Assisted Ask browser ${mode}: passed (real loopback server and Rust engine; no model)`);
} finally {
  if (websocket) websocket.close();
  browser.kill('SIGTERM');
  await new Promise(resolve => browser.once('exit', resolve));
  await rm(directory, {recursive:true, force:true, maxRetries:5, retryDelay:100});
}
