"use strict";
// Presentation only. The v1 session, request, navigation and Ask handlers stay authoritative.
Object.assign(words.en, {
  ready: "Local Find v2 prototype · BM25 only · frozen v1 study unchanged",
  footer: "Find v2 prototype · BM25 only · Stop with Ctrl-C. No participant-tested improvement is claimed; independent human review remains open.",
  ranked: "One exact lexical candidate before clipping. This is not a query answer.",
  ambiguous_exact: "Ambiguous: several graph-qualified exact lexical candidates before clipping. Choose explicitly.",
  ambiguous_candidates: "Ambiguous partial lexical candidates. Unverified suggestions; relevance to your phrase is unknown.",
  low_confidence: "Low confidence in interpretation: one partial lexical suggestion. No confidence probability was measured.",
  no_match: "No authorized lexical match for this role, scope and snapshot. Real-world absence is unknown.",
  truncated: "Candidate page truncated; more lexical matches exist.",
  evidenceClipped: "Evidence page truncated; more statements exist in this direction.",
  noResource: "No authorized resource resolved for this role, graph and snapshot. Other scopes and real-world absence remain unknown.",
  evidenceFull: "Evidence page not clipped. Other directions and real-world facts remain unknown.",
  missingExact: "No exact identifier resolved. No returned candidate has this exact authorized IRI in the selected role, scope and snapshot. Partial namespace/word suggestions below are not the requested identifier. Other scopes and snapshots remain unknown.",
  exactIri: "Exact authorized IRI identity", exactText: "Exact indexed label / alias / identifier text; inspect its source",
  partial: "Partial lexical suggestion — unverified for your phrase",
  suggestions: "Returned suggestions may be irrelevant, including for fictional or unsupported phrases. No semantic absence detector or score cutoff is applied. Choose a different role or an explicit graph path when needed; nothing is selected automatically.",
  score: "BM25 ranking score; not probability, truth or confidence",
  counts: "Graph-qualified exact candidates before clipping / distinct exact IRIs",
  witness: "Original source statement (subject → predicate → object)",
  mapping: "Predicate association: two actual source statements in the same graph. This is not a direct label on the candidate.",
  excerpt: "Clipped source text excerpt; this is not the complete original literal. Open graph evidence to inspect the source.",
  noLabel: "No direct label in the authorized indexed text. IRI identity is retained; associated labels are shown separately.",
  emptyText: "No authorized indexed text witness is available for this resource.",
  outgoingEdge: "Outgoing: selected resource is the subject.", incomingEdge: "Incoming: selected resource is the object.",
  usageEdge: "Predicate usage: selected resource is the predicate.",
  broader: "skos:broader: subject → broader concept (object).",
  narrower: "skos:narrower: subject → narrower concept (object).",
  restrictions: "Catalog limits: only the operator-authorized roles/graphs and indexed languages are searched; text may be missing or bounded. No claim about identifiers outside this catalog.",
  examples: "Examples: Entity → Norway / Norge; Predicate → capital / hovedstad. A phrase such as ‘capital of Norway’ / ‘hovedstaden i Norge’ needs explicit entity and directed-path choices, not a search answer.",
  context: "Submitted query / role / scope", sourceGraph: "Source graph", language: "Language", datatype: "Datatype",
  twoHopAction: "Explore two-hop source paths", twoHopTitle: "Source-witnessed two-hop paths",
  twoHopHelp: "Each path joins two original directed statements in this graph. Traversal order is not question relevance. Paths never select or execute an Ask operation.",
  twoHopLoading: "Reading bounded graph pages…", twoHopEmpty: "No additional two-hop IRI paths were found for this entity.",
  twoHopClipped: "Path exploration was capped or a source page had more evidence. Missing paths are unknown.",
  twoHopCount: "Source-witnessed paths", twoHopVia: "Intermediate IRI", twoHopFirst: "First traversal direction",
  twoHopSecond: "Second traversal direction", twoHopOpen: "Open this IRI in Find"
});
Object.assign(words.nb, {
  ready: "Lokal Find v2-prototype · kun BM25 · fryst v1-studie uendret",
  footer: "Find v2-prototype · kun BM25 · Stopp med Ctrl-C. Ingen deltakerprøvd forbedring påstås; uavhengig menneskelig vurdering gjenstår.",
  ranked: "Én eksakt leksikalsk kandidat før avkorting. Dette er ikke et svar på et spørsmål.",
  ambiguous_exact: "Tvetydig: flere eksakte leksikalske kandidater med grafidentitet før avkorting. Velg eksplisitt.",
  ambiguous_candidates: "Tvetydige delvise leksikalske kandidater. Ubekreftede forslag; relevans for uttrykket er ukjent.",
  low_confidence: "Lav sikkerhet om tolkningen: ett delvis leksikalsk forslag. Ingen sannsynlighet er målt.",
  no_match: "Ingen autoriserte leksikalske treff for rollen, omfanget og øyeblikksbildet. Faktisk fravær er ukjent.",
  truncated: "Kandidatsiden er avkortet; flere leksikalske treff finnes.",
  evidenceClipped: "Beleggsiden er avkortet; flere utsagn finnes i denne retningen.",
  noResource: "Ingen autorisert ressurs avklart for rollen, grafen og øyeblikksbildet. Andre omfang og faktisk fravær er ukjent.",
  evidenceFull: "Beleggsiden er ikke avkortet. Andre retninger og fakta i verden er fortsatt ukjente.",
  missingExact: "Ingen eksakt identifikator avklart. Ingen returnert kandidat har denne eksakte autoriserte IRI-en i valgt rolle, omfang og øyeblikksbilde. Delvise navnerom-/ordforslag nedenfor er ikke den forespurte identifikatoren. Andre omfang og øyeblikksbilder er ukjente.",
  exactIri: "Eksakt autorisert IRI-identitet", exactText: "Eksakt indeksert etikett / alias / identifikatortekst; undersøk kilden",
  partial: "Delvis leksikalsk forslag — ubekreftet for uttrykket ditt",
  suggestions: "Returnerte forslag kan være irrelevante, også for oppdiktede eller ustøttede uttrykk. Ingen semantisk fraværsdetektor eller poenggrense brukes. Velg en annen rolle eller en eksplisitt grafsti ved behov; ingenting velges automatisk.",
  score: "BM25-rangeringspoeng; ikke sannsynlighet, sannhet eller sikkerhet",
  counts: "Eksakte kandidater med grafidentitet før avkorting / ulike eksakte IRI-er",
  witness: "Opprinnelig kildeutsagn (subjekt → predikat → objekt)",
  mapping: "Predikatkobling: to faktiske kildeutsagn i samme graf. Dette er ikke en direkte etikett på kandidaten.",
  excerpt: "Avkortet kildetekstutdrag; dette er ikke hele den opprinnelige literalen. Åpne grafbelegg for å undersøke kilden.",
  noLabel: "Ingen direkte etikett i den autoriserte indekserte teksten. IRI-identiteten beholdes; koblede etiketter vises separat.",
  emptyText: "Ingen autoriserte indekserte tekstbelegg er tilgjengelige for ressursen.",
  outgoingEdge: "Utgående: valgt ressurs er subjektet.", incomingEdge: "Inngående: valgt ressurs er objektet.",
  usageEdge: "Predikatbruk: valgt ressurs er predikatet.",
  broader: "skos:broader: subjekt → bredere begrep (objekt).",
  narrower: "skos:narrower: subjekt → smalere begrep (objekt).",
  restrictions: "Kataloggrenser: bare operatørautoriserte roller/grafer og indekserte språk gjennomsøkes; tekst kan mangle eller være avgrenset. Ingen påstand om identifikatorer utenfor katalogen.",
  examples: "Eksempler: Entitet → Norge / Norway; Predikat → hovedstad / capital. Et uttrykk som «hovedstaden i Norge» / «capital of Norway» krever eksplisitte valg av entitet og rettet sti, ikke et søkesvar.",
  context: "Innsendt søk / rolle / omfang", sourceGraph: "Kildegraf", language: "Språk", datatype: "Datatype",
  twoHopAction: "Utforsk kildebevitnede stier med to kanter", twoHopTitle: "Kildebevitnede stier med to kanter",
  twoHopHelp: "Hver sti kobler sammen to opprinnelige, rettede utsagn i denne grafen. Traverseringsrekkefølgen viser ikke spørsmålsrelevans. Stiene velger eller kjører aldri en Ask-operasjon.",
  twoHopLoading: "Leser avgrensede grafsider…", twoHopEmpty: "Ingen ekstra to-kantede IRI-stier ble funnet for denne entiteten.",
  twoHopClipped: "Stiutforskingen var begrenset, eller en kildeside hadde flere belegg. Manglende stier er ukjent.",
  twoHopCount: "Kildebevitnede stier", twoHopVia: "Mellomliggende IRI", twoHopFirst: "Første traverseringsretning",
  twoHopSecond: "Andre traverseringsretning", twoHopOpen: "Åpne denne IRI-en i Find"
});

let submittedQuery = "";
$("search-form").addEventListener("submit", () => {
  submittedQuery = $("search").value.trim();
  $("query-context").textContent = "";
}, true);
const originalTranslate = translate;
translate = function () {
  originalTranslate();
  $("examples").textContent = t("examples");
};
function rdfText(value) {
  if (value.kind === "iri") return `<${value.value}>`;
  if (value.kind === "blank_node") return `_:${value.value}`;
  return JSON.stringify(value.value) + (value.language ? `@${value.language}` : `^^<${value.datatype}>`);
}
function statement(subject, predicate, object, graph, parent) {
  const witness = node("div", undefined, parent, "witness");
  node("p", t("witness"), witness);
  node("pre", `${rdfText(subject)} → <${predicate}> → ${rdfText(object)}`, witness);
  node("p", `${t("sourceGraph")}: ${graph}`, witness);
}
const iriTerm = value => ({ kind: "iri", value });
const TWO_HOP_SEED_LIMIT = 5, TWO_HOP_PATH_LIMIT = 20;
let twoHopResult = null;
function clearTwoHop() {
  twoHopResult = null;
  $("two-hop-panel").hidden = true;
  $("two-hop-results").replaceChildren();
}
function renderTwoHop() {
  if (!twoHopResult || selected.iri !== twoHopResult.seed || selected.graph !== twoHopResult.graph) return;
  const result = twoHopResult, panel = $("two-hop-panel"), paths = $("two-hop-results");
  panel.hidden = false;
  $("two-hop-heading").textContent = t("twoHopTitle");
  $("two-hop-help").textContent = t("twoHopHelp");
  $("two-hop-clipped").hidden = !result.clipped;
  $("two-hop-clipped").textContent = t("twoHopClipped");
  paths.replaceChildren();
  if (result.loading) {
    $("two-hop-status").textContent = t("twoHopLoading");
    return;
  }
  $("two-hop-status").textContent = `${t("twoHopCount")}: ${result.paths.length} · ${result.graph} · ${result.snapshot_id}`;
  if (result.error) {
    $("two-hop-status").textContent = t("failed");
    return;
  }
  if (!result.paths.length) {
    node("p", t("twoHopEmpty"), paths);
    return;
  }
  for (const path of result.paths) {
    const card = node("article", undefined, paths);
    node("h4", path.endpoint, card);
    node("p", `${t("twoHopVia")}: ${path.intermediate}`, card);
    node("p", `${t("twoHopFirst")}: ${t(path.first_direction)}`, card);
    statement(path.first_statement.subject, path.first_statement.predicate.value,
      path.first_statement.object, path.graph, card);
    node("p", `${t("twoHopSecond")}: ${t(path.second_direction)}`, card);
    statement(path.second_statement.subject, path.second_statement.predicate.value,
      path.second_statement.object, path.graph, card);
    button(t("twoHopOpen"), card, () => open(path.endpoint, path.graph, "outgoing", true));
  }
}
async function exploreTwoHop(seed, graph) {
  const ticket = ++generation, snapshotId = session.snapshot_id;
  const limit = Math.min(selected.limit, session.page_limit);
  twoHopResult = { seed, graph, snapshot_id: snapshotId, paths: [], clipped: false, loading: true };
  renderTwoHop();
  const read = (iri, direction) => api("/api/entity", {
    snapshot_id: snapshotId, scope: [graph], iri, direction, offset: 0, limit
  });
  try {
    const firstDirections = ["outgoing", "incoming"];
    const firstPages = await Promise.all(firstDirections.map(direction => read(seed, direction)));
    if (ticket !== generation || selected.iri !== seed || selected.graph !== graph) return;
    if (firstPages.some(page => page.iri !== seed)) throw new Error(t("failed"));
    let clipped = firstPages.some(page => page.truncated);
    const direct = new Set(), intermediates = new Map();
    for (let index = 0; index < firstPages.length; index++) {
      const direction = firstDirections[index];
      for (const edge of firstPages[index].evidence) {
        if (edge.source_graph.kind !== "iri" || edge.source_graph.value !== graph) continue;
        const start = direction === "outgoing" ? edge.subject : edge.object;
        const endpoint = direction === "outgoing" ? edge.object : edge.subject;
        if (start.kind !== "iri" || start.value !== seed || endpoint.kind !== "iri" || endpoint.value === seed) continue;
        direct.add(endpoint.value);
        if (!intermediates.has(endpoint.value)) {
          intermediates.set(endpoint.value, { iri: endpoint.value, first_direction: direction, first_statement: edge });
        }
      }
    }
    const seeds = [...intermediates.values()];
    if (seeds.length > TWO_HOP_SEED_LIMIT) clipped = true;
    const paths = [], seen = new Set();
    outer: for (const intermediate of seeds.slice(0, TWO_HOP_SEED_LIMIT)) {
      const secondDirections = ["outgoing", "incoming"];
      const secondPages = await Promise.all(secondDirections.map(direction => read(intermediate.iri, direction)));
      if (ticket !== generation || selected.iri !== seed || selected.graph !== graph) return;
      clipped ||= secondPages.some(page => page.truncated);
      for (let index = 0; index < secondPages.length; index++) {
        const direction = secondDirections[index], page = secondPages[index];
        if (page.iri !== intermediate.iri) continue;
        for (const edge of page.evidence) {
          if (edge.source_graph.kind !== "iri" || edge.source_graph.value !== graph) continue;
          const start = direction === "outgoing" ? edge.subject : edge.object;
          const endpoint = direction === "outgoing" ? edge.object : edge.subject;
          if (start.kind !== "iri" || start.value !== intermediate.iri || endpoint.kind !== "iri"
              || endpoint.value === seed || endpoint.value === intermediate.iri || direct.has(endpoint.value)) continue;
          const key = JSON.stringify([intermediate.first_statement, edge]);
          if (seen.has(key)) continue;
          seen.add(key);
          if (paths.length >= TWO_HOP_PATH_LIMIT) { clipped = true; break outer; }
          paths.push({ seed, graph, intermediate: intermediate.iri, endpoint: endpoint.value,
            first_direction: intermediate.first_direction, first_statement: intermediate.first_statement,
            second_direction: direction, second_statement: edge });
        }
      }
    }
    if (ticket !== generation || selected.iri !== seed || selected.graph !== graph) return;
    twoHopResult = { seed, graph, snapshot_id: snapshotId, paths, clipped, loading: false };
    renderTwoHop();
  } catch {
    if (ticket !== generation || selected.iri !== seed || selected.graph !== graph) return;
    twoHopResult = { seed, graph, snapshot_id: snapshotId, paths: [], clipped: false, error: true };
    renderTwoHop();
    $("two-hop-status").textContent = t("failed");
  }
}
const findOpen = open;
open = function (iri, graph, direction, fromFind = false) {
  clearTwoHop();
  findOpen(iri, graph, direction, fromFind);
};
const findPage = page;
page = function (offset, focus = false) {
  clearTwoHop();
  return findPage(offset, focus);
};
$("search-form").addEventListener("submit", clearTwoHop, true);
documentText = function (doc, graph, parent, iri) {
  if (!doc.texts.some(text => text.field === "label" && !text.via)) node("p", t("noLabel"), parent);
  if (!doc.texts.length) node("p", t("emptyText"), parent);
  for (const text of doc.texts) {
    node("p", `${text.field}: ${text.value.text}`, parent);
    node("p", `${t("language")}: ${text.value.language || "—"} · ${t("datatype")}: ${text.value.datatype}`, parent);
    if (text.via) node("p", t("mapping"), parent);
    if (text.truncated) node("p", t("excerpt"), parent);
    else statement(iriTerm(text.via?.source_iri || iri), text.predicate,
      { kind: "literal", value: text.value.text, language: text.value.language, datatype: text.value.datatype }, graph, parent);
    if (text.via) {
      statement(iriTerm(text.via.source_iri), text.via.predicate, iriTerm(iri), graph, parent);
      button(t("back") + ": " + text.via.source_iri, parent, () => open(text.via.source_iri, graph, "outgoing"));
    }
  }
};
renderFind = function (result) {
  $("results").replaceChildren();
  const looksLikeIri = /^[a-z][a-z0-9+.-]*:[^\s]+$/iu.test(submittedQuery);
  const resolvedIri = result.hits.some(hit => hit.explanation.exact_iri && hit.iri === submittedQuery
    && result.scope.includes(hit.graph));
  $("status").textContent = `${looksLikeIri && !resolvedIri ? t("missingExact") + " " : ""}${t(result.status)} ${t(result.truncated ? "truncated" : "unclipped")} (${result.hits.length}/${result.matches}). ${t("counts")}: ${result.exact_candidates}/${result.exact_ids}.`;
  $("query-context").textContent = `${t("context")}: ${submittedQuery} · ${t(result.role)} · ${result.scope.join(" / ")}`;
  node("p", t("suggestions"), $("results"));
  node("p", t("restrictions") + " " + session.roles.map(t).join(" / ") + " · " + session.scope.join(" / "), $("results"));
  for (const hit of result.hits) {
    const card = node("article", undefined, $("results"));
    node("h3", hit.iri, card);
    node("p", hit.graph, card);
    node("p", t(hit.explanation.exact_iri ? "exactIri" : hit.exact ? "exactText" : "partial"), card);
    node("p", `${t("score")}: ${hit.score}`, card);
    // Retain the core explanation verbatim; do not guess which literal supplied a token.
    json(hit.explanation, card);
    documentText(hit.document, hit.graph, card, hit.iri);
    button(t("select"), card, () => open(hit.iri, hit.graph,
      result.role === "predicate" ? "predicate" : "outgoing", result.role === "entity"));
    provenance(result, card);
  }
  provenance(result, $("results"));
};
renderEntity = function (result) {
  $("details").replaceChildren(); $("edges").replaceChildren();
  $("selection").textContent = `${result.iri || "—"} · ${selected.graph} · ${result.snapshot_id}`;
  const status = result.status === "truncated" ? "observed" : result.status === "no_match" ? "noResource" : result.status;
  $("page-status").textContent = `${t(status)} ${t("page")} ${result.offset}. ${t(result.truncated ? "evidenceClipped" : "evidenceFull")}`;
  for (const [graph, doc] of Object.entries(result.documents)) documentText(doc, graph, $("details"), result.iri);
  if (result.iri && selected.fromFind && session.roles.includes("predicate")) {
    button("Build exact follow_path plan from this selected Find entity", $("details"), beginAsk);
  }
  if (result.iri && selected.fromFind && session.roles.includes("entity")) {
    button(t("twoHopAction"), $("details"), () => exploreTwoHop(result.iri, selected.graph));
  }
  provenance(result, $("details"));
  for (const edge of result.evidence) {
    const row = node("article", undefined, $("edges"), "edge");
    node("p", t(result.direction === "predicate" ? "usageEdge" : result.direction === "incoming" ? "incomingEdge" : "outgoingEdge"), row);
    statement(edge.subject, edge.predicate.value, edge.object, edge.source_graph.value, row);
    for (const name of ["broader", "narrower"]) {
      if (edge.predicate.value === "http://www.w3.org/2004/02/skos/core#" + name) node("p", t(name), row);
    }
    term(edge.subject, edge.source_graph.value, row, "outgoing");
    term(edge.predicate, edge.source_graph.value, row, "predicate");
    term(edge.object, edge.source_graph.value, row, "incoming");
  }
  $("previous").disabled = result.offset === 0;
  $("next").disabled = result.next_offset === null || result.next_offset > 100000;
  if (twoHopResult?.seed === result.iri && twoHopResult.graph === selected.graph) renderTwoHop();
};
// The v1 session may already be ready when this deferred asset finishes loading.
if (session) translate();
else $("examples").textContent = t("examples");
