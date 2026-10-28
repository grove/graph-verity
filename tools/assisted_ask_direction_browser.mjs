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
  const clippingNotices = await evaluate(`(() => {
    const original = suggestions;
    const clippedFirst = items => items.map((item, index) => index ? item :
      {...item, candidate:{...item.candidate, texts_clipped:true}});
    const withUsage = items => items.map((item, index) => index ? item :
      {...item, candidate:{...item.candidate, usage:[
        {direction:'outgoing',evidence:[{}],clipped:true}, {direction:'incoming',evidence:[],clipped:false}
      ]}});
    suggestions = {...suggestions, entity_candidates_clipped:true, predicate_candidates_clipped:true,
      entity_candidates:withUsage(clippedFirst(suggestions.entity_candidates)),
      neighborhood_candidates:clippedFirst(suggestions.neighborhood_candidates),
      property_metadata:{...suggestions.property_metadata, clipped:true,
        candidates:clippedFirst(suggestions.property_metadata.candidates)}};
    renderSuggestions();
    const en = ['entity-candidates-clipped','predicate-candidates-clipped','metadata-candidates-clipped']
      .map(id => document.getElementById(id).textContent);
    const visible = ['entity-candidates-clipped','predicate-candidates-clipped','metadata-candidates-clipped']
      .map(id => !document.getElementById(id).hidden);
    const text = ['entity-suggestion-list','neighborhood-suggestion-list','metadata-suggestion-list']
      .map(id => [...document.querySelectorAll('#' + id + ' article [role=note]')].map(note => note.textContent).join(' '));
    const usage = document.querySelector('#entity-suggestion-list article').textContent;
    const summaryEn = ['two-hop-summary','metadata-summary','neighborhood-summary']
      .map(id => document.getElementById(id).textContent);
    const operationEn = [...document.querySelectorAll('#neighborhood-entity-suggestion-list article button')]
      .find(button => button.textContent.includes('/prop/direct/P17'))?.textContent;
    document.getElementById('language').value = 'nb'; translate();
    const nb = ['entity-candidates-clipped','predicate-candidates-clipped','metadata-candidates-clipped']
      .map(id => document.getElementById(id).textContent);
    const textNb = ['entity-suggestion-list','neighborhood-suggestion-list','metadata-suggestion-list']
      .map(id => [...document.querySelectorAll('#' + id + ' article [role=note]')].map(note => note.textContent).join(' '));
    const usageNb = document.querySelector('#entity-suggestion-list article').textContent;
    const summaryNb = ['two-hop-summary','metadata-summary','neighborhood-summary']
      .map(id => document.getElementById(id).textContent);
    const operationNb = [...document.querySelectorAll('#neighborhood-entity-suggestion-list article button')]
      .find(button => button.textContent.includes('/prop/direct/P17'))?.textContent;
    suggestions = original; document.getElementById('language').value = 'en'; translate(); renderSuggestions();
    return {visible, en, nb, text, textNb, usage, usageNb, summaryEn, summaryNb, operationEn, operationNb};
  })()`);
  assert.deepEqual(clippingNotices.visible, [true, true, true]);
  assert.match(clippingNotices.en[0], /additional candidates are unknown/);
  assert.match(clippingNotices.en[1], /additional candidates are unknown/);
  assert.match(clippingNotices.en[2], /additional property candidates are unknown/);
  assert.match(clippingNotices.nb[0], /flere kandidater er ukjente/);
  assert.match(clippingNotices.nb[1], /flere kandidater er ukjente/);
  assert.match(clippingNotices.nb[2], /flere egenskapskandidater er ukjente/);
  assert.match(clippingNotices.summaryEn[1], /retrieval clipped; additional results unknown/);
  assert.match(clippingNotices.summaryNb[1], /hentingen er avkortet; flere treff er ukjente/);
  assert.equal(clippingNotices.text.length, 3);
  assert.ok(clippingNotices.text.every(text => /source text was clipped or omitted/.test(text)));
  assert.ok(clippingNotices.textNb.every(text => /kildetekst er avkortet eller utelatt/.test(text)));
  assert.match(clippingNotices.usage, /Outgoing source statement examples in this packet: 1/);
  assert.match(clippingNotices.usage, /No examples were returned; absence is unknown/);
  assert.match(clippingNotices.usage, /This evidence page is capped; additional source statements may exist/);
  assert.match(clippingNotices.usageNb, /Eksempler på utgående kildeutsagn i denne pakken: 1/);
  assert.match(clippingNotices.usageNb, /Ingen eksempler ble returnert; fravær er ukjent/);
  assert.match(clippingNotices.usageNb, /Denne bevislisten er begrenset/);
  assert.match(clippingNotices.operationEn, /Select source-witnessed operation.*Reverse/);
  assert.match(clippingNotices.operationNb, /Velg kildebevitnet operasjon.*Bakover/);
  const secondarySections = await evaluate(`(() => {
    const ids = ['neighborhood-entities-section','two-hop-section','metadata-section','neighborhood-section'];
    return ids.map(id => ({open:document.getElementById(id).open, summary:document.querySelector('#' + id + ' > summary').textContent}));
  })()`);
  assert.ok(secondarySections.every(section => !section.open));
  assert.match(secondarySections[0].summary, /\(\d+\)/);
  assert.match(secondarySections[1].summary, /\(0\)/);
  await evaluate("['neighborhood-entities-section','two-hop-section','metadata-section','neighborhood-section'].forEach(id => document.querySelector('#' + id + ' > summary').click())");
  assert.equal(await evaluate("['neighborhood-entities-section','two-hop-section','metadata-section','neighborhood-section'].every(id => document.getElementById(id).open)"), true);
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
  const twoHop = await evaluate("({count:document.querySelectorAll('#two-hop-suggestion-list article').length, help:document.querySelector('[data-i18n=twoHopCandidatesHelp]').textContent, empty:!document.getElementById('two-hop-empty').hidden, clipped:!document.getElementById('two-hop-clipped').hidden})");
  assert.equal(twoHop.count, 0);
  assert.match(twoHop.help, /does not indicate question relevance/);
  assert.equal(twoHop.empty, true);
  assert.equal(twoHop.clipped, false);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  const nearbyEntity = await evaluate("(() => { const article=[...document.querySelectorAll('#neighborhood-entity-suggestion-list article')].find(item => item.textContent.includes('/entity/Q20')); return {count:document.querySelectorAll('#neighborhood-entity-suggestion-list article').length, help:document.querySelector('[data-i18n=neighborhoodEntitiesHelp]').textContent, text:article?.textContent, buttons:article?.querySelectorAll('button').length ?? 0, clipped:!document.getElementById('neighborhood-entities-clipped').hidden}; })()");
  assert.ok(nearbyEntity.count > 0);
  assert.match(nearbyEntity.help, /does not indicate question relevance/);
  assert.match(nearbyEntity.text, /P17/);
  assert.match(nearbyEntity.text, /Q279724/);
  assert.equal(nearbyEntity.buttons, 2);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  const metadataSuggestion = await evaluate("(() => { const article=[...document.querySelectorAll('#metadata-suggestion-list article')].find(item => item.textContent.includes('/P856')); return {count:document.querySelectorAll('#metadata-suggestion-list article').length, help:document.querySelector('[data-i18n=metadataCandidatesHelp]').textContent, text:article?.textContent, provenance:document.getElementById('property-metadata-provenance').textContent, buttons:article?.querySelectorAll('button').length ?? 0}; })()");
  assert.ok(metadataSuggestion.count > 0);
  assert.match(metadataSuggestion.help, /not data facts or source witnesses/);
  assert.match(metadataSuggestion.text, /BM25 score \(not probability\)/);
  assert.match(metadataSuggestion.text, /official website/);
  assert.match(metadataSuggestion.text, /directClaim/);
  assert.match(metadataSuggestion.provenance, /CC0-1.0/);
  assert.equal(metadataSuggestion.buttons, 1);
  await evaluate("[...document.querySelectorAll('#metadata-suggestion-list article')].find(article => article.textContent.includes('/P131')).querySelector('button').click()");
  const englishPropertyOption = await evaluate("document.getElementById('predicate').selectedOptions[0].textContent");
  assert.match(englishPropertyOption, /located in the administrative territorial entity/);
  await evaluate("(() => { const language=document.getElementById('language'); language.value='nb'; language.dispatchEvent(new Event('change')); })()");
  assert.match(await evaluate("document.getElementById('predicate').selectedOptions[0].textContent"), /located in the administrative territorial entity \(en\) — http:\/\/www\.wikidata\.org\/prop\/direct\/P131/);
  assert.equal(await evaluate("document.getElementById('suggestions').hidden"), true);
  await evaluate("(() => { const language=document.getElementById('language'); language.value='en'; language.dispatchEvent(new Event('change')); })()");
  assert.match(await evaluate("document.getElementById('predicate').selectedOptions[0].textContent"), /located in the administrative territorial entity/);
  assert.equal(await evaluate("document.getElementById('metadata-language-note').hidden"), true);
  await evaluate("(() => { const predicate=document.getElementById('predicate'); predicate.value=''; predicate.dispatchEvent(new Event('change')); })()");
  assert.equal(await evaluate("document.getElementById('metadata-language-note').hidden"), true);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("document.getElementById('suggest').click()");
  await until("!document.getElementById('suggestions').hidden");
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
  assert.equal(await evaluate("document.querySelector('#entity-suggestion-list article [data-selection-state=entity]')?.textContent"), "Current entity choice");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "");
  assert.equal(await evaluate("document.getElementById('direction').value"), "");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("[...document.querySelectorAll('#neighborhood-suggestion-list article')].find(article => article.textContent.includes('/P856')).querySelector('button').click()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q279724");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P856");
  assert.equal(await evaluate("[...document.querySelectorAll('#neighborhood-suggestion-list article')].find(article => article.textContent.includes('/P856')).querySelector('[data-selection-state=property]').textContent"), "Current property choice");
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
  assert.equal(await evaluate("document.querySelector('#entity-suggestion-list article [data-selection-state=entity]').textContent"), "Valgt entitet");
  assert.equal(await evaluate("!document.getElementById('metadata-language-note').hidden"), true);
  assert.match(await evaluate("document.getElementById('metadata-language-note').textContent"), /ingen norsk tekst/);

  await evaluate("(() => { const question=document.getElementById('question'); question.value='P856'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const norwegianFallbackLabel = await evaluate("[...document.querySelectorAll('#metadata-suggestion-list article')].find(article => article.textContent.includes('/P856'))?.textContent");
  assert.match(norwegianFallbackLabel, /Kildeetikett \(en\):/);
  assert.match(norwegianFallbackLabel, /official website/i);

  await evaluate("(() => { const question=document.getElementById('question'); question.value='P1448'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const norwegianSuggestion = await evaluate("({heading:document.querySelector('#suggestion-list h3').textContent, labelOrigin:document.querySelector('#suggestion-list article p').textContent, selected:document.getElementById('predicate').value})");
  assert.equal(norwegianSuggestion.heading, "Offisielle navn");
  assert.match(norwegianSuggestion.labelOrigin, /Kun grensesnittnavn/);
  assert.equal(norwegianSuggestion.selected, "http://www.wikidata.org/prop/direct/P856");
  assert.match(await evaluate("document.getElementById('shape-origin').textContent"), /Operatørforfattede SHACL-demodata.*ikke verifisert/);
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);

  await evaluate("(() => { const question=document.getElementById('question'); question.value='Which official websites does the University of Tromsø list?'; question.dispatchEvent(new Event('input')); document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  await evaluate("[...document.querySelectorAll('#neighborhood-entity-suggestion-list article')].find(article => article.textContent.includes('/entity/Q20')).querySelector('button').click()");
  await evaluate("[...document.querySelectorAll('#neighborhood-suggestion-list article')].find(article => article.textContent.includes('/P17')).querySelector('button').click()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q20");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P17");
  assert.equal(await evaluate("document.getElementById('direction').value"), "");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")), false);
  await evaluate("(() => { const language=document.getElementById('language'); language.value='nb'; language.dispatchEvent(new Event('change')); })()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q20");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P17");
  assert.equal(await evaluate("document.getElementById('entity').selectedOptions[0].textContent"), "http://www.wikidata.org/entity/Q20");
  await evaluate("(() => { const language=document.getElementById('language'); language.value='en'; language.dispatchEvent(new Event('change')); })()");
  assert.equal(await evaluate("document.getElementById('entity').selectedOptions[0].textContent"), "http://www.wikidata.org/entity/Q20");
  await evaluate("document.getElementById('suggest').click()");
  await until("!document.getElementById('suggestions').hidden");
  await evaluate("(() => { const direction=document.getElementById('direction'); direction.value='reverse'; direction.dispatchEvent(new Event('change')); document.getElementById('preview').click(); })()");
  await until("!document.getElementById('review').hidden");
  await evaluate("document.querySelector('#review details summary[data-i18n=selectionOriginTitle]').click()");
  const selectionOrigins = JSON.parse(await evaluate("document.getElementById('selection-origin-evidence').textContent"));
  assert.equal(selectionOrigins.entity.source, "neighborhood_entity");
  assert.equal(selectionOrigins.entity.suggestion_language, "nb");
  assert.equal(selectionOrigins.entity.retrieval_question, "Which official websites does the University of Tromsø list?");
  assert.equal(await evaluate("!document.getElementById('selection-origin-warning').hidden"), true);
  assert.ok(selectionOrigins.entity.witness);
  assert.equal(selectionOrigins.predicate.source, "neighborhood");
  assert.ok(selectionOrigins.predicate.witness);
  assert.equal(selectionOrigins.direction.source, "explicit_operator_selection");
  const catalogPreview = requests.findLast(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview"));
  assert.ok(catalogPreview?.postData);
  assert.deepEqual(JSON.parse(catalogPreview.postData), {
    entity: "http://www.wikidata.org/entity/Q20",
    predicate: "http://www.wikidata.org/prop/direct/P17",
    direction: "reverse",
    question: "Which official websites does the University of Tromsø list?",
    language: "en"
  });
  await evaluate("document.getElementById('cancel').click()");
  await until("document.getElementById('review').hidden");

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
  const manualOrigins = JSON.parse(await evaluate("document.getElementById('selection-origin-evidence').textContent"));
  assert.equal(manualOrigins.entity.source, "manual_authorized_catalog_selection");
  assert.equal(manualOrigins.predicate.source, "manual_authorized_catalog_selection");
  assert.equal(manualOrigins.direction.source, "explicit_operator_selection");
  await evaluate("(() => { for (const id of ['entity','predicate','direction']) { const select=document.getElementById(id); select.value=''; select.dispatchEvent(new Event('change')); } document.getElementById('suggest').click(); })()");
  await until("!document.getElementById('suggestions').hidden");
  const previewCount = requests.filter(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")).length;
  const witnessedButton = await evaluate("[...document.querySelectorAll('#neighborhood-entity-suggestion-list article')].find(article => article.textContent.includes('/entity/Q20'))?.querySelector('button:nth-of-type(2)')?.textContent");
  assert.match(witnessedButton, /source-witnessed operation/i);
  assert.match(witnessedButton, /\/prop\/direct\/P17.*Reverse/);
  await evaluate("[...document.querySelectorAll('#neighborhood-entity-suggestion-list article')].find(article => article.textContent.includes('/entity/Q20')).querySelector('button:nth-of-type(2)').click()");
  assert.equal(await evaluate("document.getElementById('entity').value"), "http://www.wikidata.org/entity/Q20");
  assert.equal(await evaluate("document.getElementById('predicate').value"), "http://www.wikidata.org/prop/direct/P17");
  assert.equal(await evaluate("document.getElementById('direction').value"), "reverse");
  assert.equal(await evaluate("document.querySelector('#neighborhood-entity-suggestion-list article [data-selection-state=witnessed-operation]').textContent"), "The entity, property, and direction match this source-witnessed choice.");
  assert.match(await evaluate("document.getElementById('status').textContent"), /Source-witnessed choices filled/);
  assert.equal(requests.filter(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview")).length, previewCount);
  await evaluate("document.getElementById('preview').click()");
  await until("!document.getElementById('review').hidden");
  const witnessedOrigins = JSON.parse(await evaluate("document.getElementById('selection-origin-evidence').textContent"));
  assert.equal(witnessedOrigins.entity.source, "source_witnessed_operation");
  assert.equal(witnessedOrigins.predicate.source, "source_witnessed_operation");
  assert.equal(witnessedOrigins.direction.source, "source_witnessed_operation");
  assert.equal(witnessedOrigins.direction.direction, "reverse");
  assert.equal(await evaluate("document.getElementById('selection-origin-warning').hidden"), true);
  const witnessedPreview = requests.findLast(request => request.url.endsWith("/api/assisted-ask-v1-direction/preview"));
  assert.deepEqual(JSON.parse(witnessedPreview.postData), {
    entity: "http://www.wikidata.org/entity/Q20",
    predicate: "http://www.wikidata.org/prop/direct/P17",
    direction: "reverse",
    question: "Which official websites does the University of Tromsø list?",
    language: "en"
  });
  await evaluate("(() => { const question=document.getElementById('question'); question.value='Which cities have sources about the university?'; question.dispatchEvent(new Event('input')); document.getElementById('preview').click(); })()");
  await until("!document.getElementById('review').hidden");
  assert.equal(await evaluate("!document.getElementById('selection-origin-warning').hidden"), true);
  assert.match(await evaluate("document.getElementById('selection-origin-warning').textContent"), /earlier question or a different interface language/);
  await evaluate("(() => { const language=document.getElementById('language'); language.value='nb'; language.dispatchEvent(new Event('change')); document.getElementById('preview').click(); })()");
  await until("!document.getElementById('review').hidden");
  assert.match(await evaluate("document.getElementById('selection-origin-warning').textContent"), /tidligere spørsmål eller et annet grensesnittspråk/);
  await evaluate("document.getElementById('cancel').click()");
  await until("document.getElementById('review').hidden");
  assert.equal(requests.some(request => request.url.endsWith("/api/assisted-ask-v1-direction/confirm")), false);
  await evaluate("(() => { const question=document.getElementById('question'); question.value='Which official websites does the University of Tromsø list?'; question.dispatchEvent(new Event('input')); const language=document.getElementById('language'); language.value='en'; language.dispatchEvent(new Event('change')); })()");
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
