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

  await evaluate("(() => { const question=document.getElementById('question'); question.value='Which official websites does the University of Tromsø list?'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const entitySuggestion = await evaluate("({heading:document.querySelector('#entity-suggestion-list h3').textContent, labelOrigin:document.querySelector('#entity-suggestion-list article p').textContent, text:document.getElementById('entity-suggestion-list').textContent, emptyProperties:!document.getElementById('suggestion-empty').hidden, rawLabel:document.getElementById('entity-suggestion-list').textContent.includes('</script><script>'), scripts:document.querySelectorAll('#entity-suggestion-list script').length, entity:document.getElementById('entity').value, predicate:document.getElementById('predicate').value, direction:document.getElementById('direction').value})");
  assert.equal(entitySuggestion.heading, "University of Tromsø – The Arctic University of Norway");
  assert.match(entitySuggestion.labelOrigin, /Untrusted label text from the selected graph/);
  assert.equal(entitySuggestion.emptyProperties, true);
  assert.equal(entitySuggestion.rawLabel, true);
  assert.equal(entitySuggestion.scripts, 0);
  assert.equal(entitySuggestion.entity, "");
  assert.equal(entitySuggestion.predicate, "");
  assert.equal(entitySuggestion.direction, "");
  assert.equal(requests.some(request => request.url.endsWith("/private")), false);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  const nearbyEntity = await evaluate("(() => { const article=[...document.querySelectorAll('#neighborhood-entity-suggestion-list article')].find(item => item.textContent.includes('/entity/Q20')); return {count:document.querySelectorAll('#neighborhood-entity-suggestion-list article').length, help:document.querySelector('[data-i18n=neighborhoodEntitiesHelp]').textContent, text:article?.textContent, buttons:article?.querySelectorAll('button').length ?? 0, clipped:!document.getElementById('neighborhood-entities-clipped').hidden}; })()");
  assert.ok(nearbyEntity.count > 0);
  assert.match(nearbyEntity.help, /does not indicate question relevance/);
  assert.match(nearbyEntity.text, /P17/);
  assert.match(nearbyEntity.text, /Q279724/);
  assert.equal(nearbyEntity.buttons, 0);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  const metadataSuggestion = await evaluate("(() => { const article=[...document.querySelectorAll('#metadata-suggestion-list article')].find(item => item.textContent.includes('/P856')); return {count:document.querySelectorAll('#metadata-suggestion-list article').length, help:document.querySelector('[data-i18n=metadataCandidatesHelp]').textContent, text:article?.textContent, provenance:document.getElementById('property-metadata-provenance').textContent, buttons:article?.querySelectorAll('button').length ?? 0}; })()");
  assert.ok(metadataSuggestion.count > 0);
  assert.match(metadataSuggestion.help, /not data facts or source witnesses/);
  assert.match(metadataSuggestion.text, /BM25 score \(not probability\)/);
  assert.match(metadataSuggestion.text, /official website/);
  assert.match(metadataSuggestion.text, /directClaim/);
  assert.match(metadataSuggestion.provenance, /CC0-1.0/);
  assert.equal(metadataSuggestion.buttons, 1);
  assert.equal(await evaluate("document.getElementById('metadata-language-note').hidden"), true);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  const neighborhoodSuggestion = await evaluate("({text:document.getElementById('neighborhood-suggestion-list').textContent, count:document.querySelectorAll('#neighborhood-suggestion-list article').length, help:document.querySelector('[data-i18n=neighborhoodHelp]').textContent, clipped:!document.getElementById('neighborhood-clipped').hidden, statement:document.querySelector('#neighborhood-suggestion-list details summary').textContent, provenance:document.getElementById('neighborhood-provenance').textContent})");
  assert.ok(neighborhoodSuggestion.count > 2);
  assert.match(neighborhoodSuggestion.text, /P1448/);
  assert.match(neighborhoodSuggestion.text, /P856/);
  assert.match(neighborhoodSuggestion.text, /P17/);
  assert.match(neighborhoodSuggestion.text, /Neighborhood rank \(not BM25\)/);
  assert.match(neighborhoodSuggestion.help, /does not show which property answers the question/);
  assert.equal(neighborhoodSuggestion.clipped, true);
  assert.match(neighborhoodSuggestion.statement, /Stored outgoing source edge from the BM25 entity/);
  assert.match(neighborhoodSuggestion.provenance, /question-vocabulary-packet-v2-neighborhood/);
  assert.match(neighborhoodSuggestion.provenance, /packet_id/);
  const unshapedProperty = await evaluate("[...document.querySelectorAll('#neighborhood-suggestion-list article')].find(item => item.textContent.includes('/P17'))?.textContent");
  assert.match(unshapedProperty, /No supported SHACL guidance for this candidate/);
  await evaluate("document.querySelector('#entity-suggestion-list button').click()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q279724");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "");
  assert.equal(await evaluate("document.getElementById('direction').value"), "");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("[...document.querySelectorAll('#neighborhood-suggestion-list article')].find(article => article.textContent.includes('/P856')).querySelector('button').click()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q279724");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P856");
  assert.equal(await evaluate("document.getElementById('direction').value"), "");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("[...document.querySelectorAll('#metadata-suggestion-list article')].find(article => article.textContent.includes('/P856')).querySelector('button').click()");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P856");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);

  await evaluate("const predicate=document.getElementById('predicate'); predicate.value=''; predicate.dispatchEvent(new Event('change'))");
  await evaluate("(() => { const question=document.getElementById('question'); question.value='P856'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const suggestion = await evaluate("({text:document.getElementById('suggestion-list').textContent, heading:document.querySelector('#suggestion-list h3').textContent, labelOrigin:document.querySelector('#suggestion-list article p').textContent, origin:document.getElementById('shape-origin').textContent, provenance:document.getElementById('shape-provenance').textContent, selected:document.getElementById('predicate').value})");
  assert.match(suggestion.text, /BM25 score \(not probability\)/);
  assert.match(suggestion.text, /P856/);
  assert.equal(suggestion.heading, "Official websites");
  assert.match(suggestion.labelOrigin, /Interface label only; no label exists in the selected language/);
  assert.match(suggestion.origin, /Operator-authored demo SHACL metadata/);
  assert.match(suggestion.origin, /not independently verified/);
  assert.match(suggestion.provenance, /Apache-2.0/);
  assert.match(suggestion.provenance, /shape_sha256/);
  assert.equal(suggestion.selected, "");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("document.querySelector('#suggestion-list button').click()");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P856");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("const language=document.getElementById('language'); language.value='nb'; language.dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.documentElement.lang"), "nb");
  assert.equal(await evaluate("document.getElementById('suggestions').hidden"), true);
  await evaluate("(() => { const question=document.getElementById('question'); question.value='Hvilke offisielle navn har Universitetet i Tromsø?'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const norwegianEntitySuggestion = await evaluate("({heading:document.querySelector('#entity-suggestion-list h3').textContent, labelOrigin:document.querySelector('#entity-suggestion-list article p').textContent})");
  assert.equal(norwegianEntitySuggestion.heading, "Universitetet i Tromsø");
  assert.match(norwegianEntitySuggestion.labelOrigin, /Ubetrodd etikett fra den valgte grafen/);
  assert.equal(await evaluate("!document.getElementById('metadata-language-note').hidden"), true);
  assert.match(await evaluate("document.getElementById('metadata-language-note').textContent"), /ingen norsk tekst/);

  await evaluate("(() => { const question=document.getElementById('question'); question.value='P1448'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const norwegianSuggestion = await evaluate("({heading:document.querySelector('#suggestion-list h3').textContent, labelOrigin:document.querySelector('#suggestion-list article p').textContent, selected:document.getElementById('predicate').value})");
  assert.equal(norwegianSuggestion.heading, "Offisielle navn");
  assert.match(norwegianSuggestion.labelOrigin, /Kun grensesnittnavn/);
  assert.equal(norwegianSuggestion.selected, "http://www.wikidata.org/prop/direct/P856");
  assert.match(await evaluate("document.getElementById('shape-origin').textContent"), /Operatørforfattede SHACL-demodata.*ikke verifisert/);
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
    const sources = await evaluate("document.getElementById('sources').textContent");
    assert.match(sources, /optional_guidance_only_not_query_evidence/);
    assert.match(sources, /operator_declared_not_independently_verified/);
    assert.match(sources, /Apache-2.0/);
    assert.match(sources, /shape_sha256/);
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
