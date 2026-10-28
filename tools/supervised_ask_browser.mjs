// Headless browser integration without npm dependencies (Node >=22 + installed Chrome).
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url] = process.argv.slice(2);
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

  async function click(id) {
    const rect = await evaluate(`(() => {
      const element = document.getElementById(${JSON.stringify(id)}); element.scrollIntoView({block:'center'});
      const r = element.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
    await send('Input.dispatchMouseEvent', {type:'mousePressed',button:'left',clickCount:1,...rect});
    await send('Input.dispatchMouseEvent', {type:'mouseReleased',button:'left',clickCount:1,...rect});
  }
  const confirms = () => requests.filter(u => u.endsWith('/api/nl-ask-v2/confirm')).length;
  async function review(question, language, iri) {
    await evaluate(`document.getElementById('question').value=${JSON.stringify(question)};
      document.getElementById('language').value=${JSON.stringify(language)};
      document.getElementById('question').dispatchEvent(new Event('input',{bubbles:true}))`);
    await click('ask');
    await until("!document.getElementById('choose').hidden");
    assert.equal(await evaluate("document.getElementById('start').value"), '');
    await evaluate(`(() => { const select = document.getElementById('start');
      select.value = [...select.options].find(o => o.textContent.includes(${JSON.stringify(iri)})).value;
      select.dispatchEvent(new Event('change',{bubbles:true})); })()`);
    await click('preview');
    await until("!document.getElementById('review').hidden");
    assert.equal(await evaluate("document.getElementById('original').textContent"), question);
    const preview = await evaluate("JSON.parse(document.getElementById('rust-preview').textContent)");
    assert.ok(preview.approval_id && preview.plan && preview.summary && preview.limitations);
    assert.ok(await evaluate("document.getElementById('sources').textContent.includes('CC0-1.0')"));
    return preview;
  }
  await send('Network.enable'); await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url});
  await until("document.getElementById('ask') && !document.getElementById('ask').disabled");
  assert.match(await evaluate("document.getElementById('runtime').textContent"), /SAVED-DRAFT DEMO/);
  assert.equal(await evaluate('location.hash'), '');
  assert.equal(confirms(), 0);

  const forward = 'Which official websites does the University of Tromsø list?';
  const reverse = 'Which institution has https://uit.no as its official website?';
  const norwegian = 'Hvilke offisielle navn har Universitetet i Tromsø?';
  const wrong = 'Which country is the University of Tromsø in?';
  const preview = await review(wrong, 'en', '/entity/Q279724');
  assert.match(await evaluate("document.getElementById('explanation').textContent"), /administrative location/);
  assert.equal(await evaluate("(() => {const a=[...document.querySelectorAll('.columns article')];return a[0].getBoundingClientRect().top === a[1].getBoundingClientRect().top})()"),true);
  assert.ok(preview.plan.patterns[0].predicate.endsWith('/P131'));
  if (process.env.ASK_SCREENSHOT) {
    const shot = await send('Page.captureScreenshot', {captureBeyondViewport:true});
    await writeFile(process.env.ASK_SCREENSHOT, Buffer.from(shot.data, 'base64'));
  }
  assert.match(await evaluate("document.getElementById('plan-fields').textContent"), /Outgoing/);
  await evaluate("document.getElementById('approve').focus()");
  await key('Enter','Enter',13);
  assert.equal(confirms(),0);
  await key('Escape','Escape',27);
  assert.ok(await evaluate("document.getElementById('review').hidden"));
  await review(wrong, 'en', '/entity/Q279724');
  await click('cancel');
  assert.equal(confirms(),0);
  await review(wrong, 'en', '/entity/Q279724');
  await evaluate("document.getElementById('question').value='edited'; document.getElementById('question').dispatchEvent(new Event('input',{bubbles:true}))");
  assert.ok(await evaluate("document.getElementById('review').hidden && document.getElementById('approve').disabled"));
  assert.equal(confirms(),0);
  for (const [q, lang, start, count, direction] of [
    [forward, 'en', '/entity/Q279724', 2, 'forward'],
    [reverse, 'en', 'https://uit.no', 1, 'reverse'],
    [norwegian, 'nb', '/entity/Q279724', 3, 'forward'],
    ['Which published labels belong to the University of Tromsø?', 'en', '/entity/Q279724', 4, 'forward'],
    ['Which website lists the University of Tromsø as its official website?', 'en', '/entity/Q279724', 0, 'reverse']]) {
    const plan = await review(q, lang, start);
    assert.equal(plan.plan.patterns[0].direction, direction);
    const fields = await evaluate("document.getElementById('plan-fields').textContent");
    assert.ok(fields.includes(direction === 'forward' ? 'Outgoing' : 'Incoming'));
    assert.ok(fields.includes(plan.plan.snapshot_id));
    assert.ok(fields.includes('Packet-local numeric identities'));
    const before = confirms();
    await click('approve');
    await until("!document.getElementById('results').hidden");
    assert.equal(confirms(),before+1);
    const receipt = await evaluate("JSON.parse(document.getElementById('receipt').textContent)");
    assert.equal(receipt.answers.length,count);
    assert.ok(receipt.answers.every(a => a.source_triples.length));
    assert.equal(receipt.provenance.inference_performed,false);
    assert.equal(receipt.provenance.operator_confirmation.decision,'approve');
    if (count) {
      const evidence = await evaluate("document.getElementById('answers').textContent");
      assert.ok(evidence.includes('Graph: urn:graph-verity:nl-ask-v1:development:wikidata'));
      assert.ok(evidence.includes('Snapshot: '+receipt.outcome.result.snapshot_id));
      assert.ok(!evidence.includes('undefined'));
    } else assert.match(await evaluate("document.getElementById('result-status').textContent"), /does not establish real-world nonexistence/);
  }
  for (const [question, status] of [
    ['Which country is Campus in?', 'model_needs_clarification'],
    ['What is the University of Tromsø postal code?', 'model_needs_clarification'],
    ['How many official websites does the University of Tromsø list?', 'model_unsupported'],
    ['A question without a saved fixture', 'No saved draft']]) {
    const before = confirms();
    await evaluate(`document.getElementById('question').value=${JSON.stringify(question)}; document.getElementById('language').value='en'`);
    await click('ask');
    await until(`document.getElementById('status').textContent.includes(${JSON.stringify(status)})`);
    assert.ok(await evaluate("document.getElementById('review').hidden && document.getElementById('approve').disabled"));
    assert.equal(confirms(),before);
    if (question.includes('Campus')) {
      const candidates = await evaluate("document.getElementById('clarification-candidates').textContent");
      assert.ok(candidates.includes('/Q279724') && candidates.includes('https://en.uit.no/startsida'));
    }
  }
  assert.equal(await evaluate("document.querySelectorAll('img, iframe, object, script:not([src])').length"),0);
  assert.ok(requests.every(u => new URL(u).origin === new URL(url).origin || u === 'about:blank'));
  await send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.ok(await evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth'));
  assert.deepEqual(exceptions,[]);
  if (process.env.ASK_ALPHA_BROWSER) {
    const { check } = await import('./ask_alpha_browser.mjs');
    await check({ send, evaluate, until, click, review, confirms });
  }
  console.log('Supervised Ask v2: bilingual, reverse, multiple, empty, inert injection, ambiguity, missing vocabulary, wrong executable plan, Enter/Escape/cancel/edit and exact approval passed');
} finally {
  if (websocket) websocket.close();
  browser.kill('SIGTERM');
  await new Promise(resolve => browser.once('exit',resolve));
  await rm(directory,{recursive:true,force:true,maxRetries:5,retryDelay:100});
}
