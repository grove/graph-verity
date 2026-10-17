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
  context: "Submitted query / role / scope", sourceGraph: "Source graph", language: "Language", datatype: "Datatype"
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
  context: "Innsendt søk / rolle / omfang", sourceGraph: "Kildegraf", language: "Språk", datatype: "Datatype"
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
};
