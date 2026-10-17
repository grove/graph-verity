"use strict";
// RDF is always textContent; no markup, external links, models or network destinations.
const $ = id => document.getElementById(id);
const words = {
  en: {
    boundary: "Ranked candidates are not verified answers. Source triples describe this graph snapshot, not proof of real-world truth. No match does not establish factual absence.",
    "search-title": "Find in authorized graphs", "query-label": "Search (Norwegian or English)",
    "role-label": "Role", "graphs-title": "Authorized graphs — select one or more",
    "limit-label": "Maximum candidates / edges per page", submit: "Find", "results-title": "Candidates",
    "detail-title": "Graph evidence", "direction-label": "Direction", previous: "Previous page", next: "Next page",
    "receipt-title": "Local runtime receipt", entity: "Entity", predicate: "Predicate", class: "Class",
    outgoing: "Outgoing", incoming: "Incoming", usage: "Predicate usage", select: "Select candidate",
    ranked: "Exact candidate — inspect and deliberately select; this is not an answer.",
    ambiguous_exact: "Ambiguous: several graph-qualified exact candidates. Choose deliberately.",
    ambiguous_candidates: "Ambiguous: several partial candidates. Choose deliberately.",
    low_confidence: "Low confidence: one partial lexical candidate.", no_match: "No retrieved match. Factual absence remains unknown.",
    truncated: "Truncated: more records exist in this search/direction.",
    unclipped: "This page was not clipped. Search top-k never establishes semantic completeness.",
    no_relationships_on_page: "No relationships on this page/direction. Other directions and real-world facts remain unknown.",
    observed: "Observed source statements in this snapshot; real-world truth is not established.",
    failed: "Request unavailable. Check selection or restart with a valid operator bundle.",
    credential: "Open the private session URL printed by the operator. No search has run.",
    ready: "Local session ready · BM25 only", busy: "Reading local snapshot…", exact: "Exact match", partial: "Partial match",
    source: "Graph / source / license", mapping: "Retrieval mapping evidence, not an invented label triple. Open original label subject:",
    page: "Page offset", back: "Open resource", footer: "BM25 only · Offline local pilot · Stop the server with Ctrl-C. No usability or relevance study is claimed."
  },
  nb: {
    boundary: "Rangerte kandidater er ikke bekreftede svar. Kildetripler beskriver dette graføyeblikksbildet, ikke bevis på sannhet i verden. Ingen treff betyr ikke faktisk fravær.",
    "search-title": "Søk i autoriserte grafer", "query-label": "Søk (norsk eller engelsk)",
    "role-label": "Rolle", "graphs-title": "Autoriserte grafer — velg én eller flere",
    "limit-label": "Maksimalt antall kandidater / kanter per side", submit: "Søk", "results-title": "Kandidater",
    "detail-title": "Grafbelegg", "direction-label": "Retning", previous: "Forrige side", next: "Neste side",
    "receipt-title": "Lokal kjørekvittering", entity: "Entitet", predicate: "Predikat", class: "Klasse",
    outgoing: "Utgående", incoming: "Inngående", usage: "Bruk av predikat", select: "Velg kandidat",
    ranked: "Eksakt kandidat — undersøk og velg bevisst; dette er ikke et svar.",
    ambiguous_exact: "Tvetydig: flere eksakte kandidater med grafidentitet. Velg bevisst.",
    ambiguous_candidates: "Tvetydig: flere delvise kandidater. Velg bevisst.",
    low_confidence: "Lav sikkerhet: én delvis leksikalsk kandidat.", no_match: "Ingen gjenfunne treff. Faktisk fravær er fortsatt ukjent.",
    truncated: "Avkortet: flere poster finnes i dette søket / denne retningen.",
    unclipped: "Siden er ikke avkortet. Topp-k-søk fastslår aldri semantisk fullstendighet.",
    no_relationships_on_page: "Ingen relasjoner på denne siden / i denne retningen. Andre retninger og fakta i verden er fortsatt ukjente.",
    observed: "Observerte kildeutsagn i dette øyeblikksbildet; sannhet i verden er ikke fastslått.",
    failed: "Forespørselen er utilgjengelig. Kontroller valget eller start på nytt med gyldige operatørdata.",
    credential: "Åpne den private øktadressen fra operatørens terminal. Ingen søk er kjørt.",
    ready: "Lokal økt er klar · kun BM25", busy: "Leser lokalt øyeblikksbilde…", exact: "Eksakt treff", partial: "Delvis treff",
    source: "Graf / kilde / lisens", mapping: "Søkekobling med belegg, ikke en oppdiktet etikett-trippel. Åpne opprinnelig etikettsubjekt:",
    page: "Sideforskyvning", back: "Åpne ressurs", footer: "Kun BM25 · Frakoblet lokal pilot · Stopp tjeneren med Ctrl-C. Ingen bruker- eller relevansstudie påstås."
  }
};
let locale = "en", session, selected, lastFind, lastEntity, generation = 0;
const t = key => words[locale][key] || key;
let credential = location.hash.slice(1);
history.replaceState(null, "", "/");
if (credential) sessionStorage.setItem("verity-session", credential);
credential ||= sessionStorage.getItem("verity-session");

function node(tag, text, parent, className) {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  if (className) item.className = className;
  if (parent) parent.append(item);
  return item;
}
function button(text, parent, action) {
  const item = node("button", text, parent);
  item.type = "button";
  item.addEventListener("click", action);
  return item;
}
function json(value, parent) { node("pre", JSON.stringify(value, null, 2), parent, "muted"); }
async function api(route, body) {
  const response = await fetch(route, { method: "POST", credentials: "omit", cache: "no-store",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + credential },
    body: JSON.stringify(body) });
  if (!response.ok) throw new Error(t("failed"));
  return response.json();
}
function provenance(result, parent) {
  const details = node("details", undefined, parent);
  node("summary", t("source"), details);
  json({ snapshot_id: result.snapshot_id, graph_hashes: result.graph_hashes, sources: result.sources }, details);
}
function documentText(doc, graph, parent) {
  for (const text of doc.texts) {
    node("p", `${text.field}: ${text.value.text}`, parent);
    json({ language: text.value.language, datatype: text.value.datatype, predicate: text.predicate,
      truncated: text.truncated }, parent);
    if (text.via) {
      node("p", t("mapping"), parent);
      json(text.via, parent);
      button(text.via.source_iri, parent, () => open(text.via.source_iri, graph, "outgoing"));
    }
  }
}
function renderFind(result) {
  $("results").replaceChildren();
  $("status").textContent = `${t(result.status)} ${t(result.truncated ? "truncated" : "unclipped")} (${result.hits.length}/${result.matches})`;
  for (const hit of result.hits) {
    const card = node("article", undefined, $("results"));
    node("h3", hit.iri, card);
    node("p", hit.graph, card);
    node("p", `${t(hit.exact ? "exact" : "partial")} · BM25 ${hit.score.toFixed(3)}`, card);
    json(hit.explanation, card);
    documentText(hit.document, hit.graph, card);
    button(t("select"), card, () => open(hit.iri, hit.graph,
      $("role").value === "predicate" ? "predicate" : "outgoing"));
  }
  provenance(result, $("results"));
}
function term(value, graph, parent, direction) {
  node("p", `${value.kind}: ${value.value}`, parent);
  if (value.kind === "iri") button(t("back") + ": " + value.value, parent,
    () => open(value.value, graph, direction));
  else if (value.kind === "literal") json({ datatype: value.datatype, language: value.language }, parent);
}
function renderEntity(result) {
  $("details").replaceChildren(); $("edges").replaceChildren();
  $("selection").textContent = `${result.iri || "—"} · ${selected.graph} · ${result.snapshot_id}`;
  $("page-status").textContent = `${t(result.status)} ${t("page")} ${result.offset}. ${t(result.truncated ? "truncated" : "unclipped")}`;
  for (const [graph, doc] of Object.entries(result.documents)) documentText(doc, graph, $("details"));
  provenance(result, $("details"));
  for (const edge of result.evidence) {
    const row = node("article", undefined, $("edges"), "edge");
    node("h3", edge.source_graph.value, row);
    term(edge.subject, edge.source_graph.value, row, "outgoing");
    term(edge.predicate, edge.source_graph.value, row, "predicate");
    term(edge.object, edge.source_graph.value, row, "incoming");
  }
  $("previous").disabled = result.offset === 0;
  $("next").disabled = result.next_offset === null || result.next_offset > 100000;
}
async function page(offset, focus = false) {
  const ticket = ++generation;
  $("page-status").textContent = t("busy");
  $("previous").disabled = true; $("next").disabled = true;
  $("details").replaceChildren(); $("edges").replaceChildren();
  lastEntity = null;
  try {
    const result = await api("/api/entity", { snapshot_id: session.snapshot_id,
      scope: [selected.graph], iri: selected.iri, direction: $("direction").value,
      offset, limit: selected.limit });
    if (ticket !== generation) return;
    lastEntity = result; renderEntity(result);
    if (focus) $("detail-title").focus();
  } catch { if (ticket === generation) $("page-status").textContent = t("failed"); }
}
function open(iri, graph, direction) {
  selected = { iri, graph, limit: Math.min(Number($("limit").value) || 10, session.page_limit) };
  $("navigation").hidden = false; $("direction").value = direction;
  page(0, true);
}
$("search-form").addEventListener("submit", async event => {
  event.preventDefault();
  const scope = [...$("graphs").querySelectorAll("input:checked")].map(input => input.value);
  const ticket = ++generation;
  $("navigation").hidden = true; $("results").replaceChildren(); lastFind = null; lastEntity = null;
  $("status").textContent = t("busy");
  try {
    const result = await api("/api/find", { query: $("search").value, scope,
      role: $("role").value, limit: Number($("limit").value) });
    if (ticket !== generation) return;
    lastFind = result; renderFind(result);
  } catch { if (ticket === generation) $("status").textContent = t("failed"); }
});
$("direction").addEventListener("change", () => page(0));
$("previous").addEventListener("click", () => page(Math.max(0, lastEntity.offset - selected.limit), true));
$("next").addEventListener("click", () => page(lastEntity.next_offset, true));
function translate() {
  document.documentElement.lang = locale;
  for (const id of ["boundary", "search-title", "query-label", "role-label", "graphs-title", "limit-label", "submit",
    "results-title", "detail-title", "direction-label", "previous", "next", "receipt-title", "footer"]) $(id).textContent = t(id);
  for (const option of $("role").options) option.textContent = t(option.value);
  for (const option of $("direction").options) option.textContent = t(option.value === "predicate" ? "usage" : option.value);
  $("connection").textContent = t(session ? "ready" : "credential");
  if (lastFind) renderFind(lastFind);
  if (lastEntity) renderEntity(lastEntity);
}
$("language").addEventListener("change", () => { locale = $("language").value; translate(); });
async function start() {
  if (!credential) { $("connection").textContent = t("credential"); return; }
  try {
    session = await api("/api/session", {});
    for (const role of session.roles) {
      const option = node("option", t(role), $("role")); option.value = role;
    }
    for (const [index, graph] of session.scope.entries()) {
      const label = node("label", undefined, $("graphs"));
      const input = node("input", undefined, label);
      input.type = "checkbox"; input.id = "graph-" + index; input.value = graph; input.checked = true;
      label.append(document.createTextNode(graph));
    }
    $("limit").max = session.page_limit;
    $("limit").value = Math.min(10, session.page_limit);
    json(session.receipt, $("receipt"));
    $("controls").disabled = false; translate();
  } catch { $("connection").textContent = t("failed"); }
}
start();
