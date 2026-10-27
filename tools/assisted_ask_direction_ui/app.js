"use strict";
const $ = id => document.getElementById(id);
const prefix = "/api/assisted-ask-v1-direction/";
const credential = location.hash.slice(1);
history.replaceState(null, "", location.pathname);
let tab, session, approval, suggestions, epoch = 0, timer;
const json = (id, value) => { $(id).textContent = JSON.stringify(value, null, 2); };
const words = {
  en: {
    title: "Select a graph operation", intro: "Choose an entity, relationship and direction. These choices define the query. No language model or question interpretation is used.",
    language: "Interface language", entity: "Entity", relationship: "Relationship", direction: "Direction", forward: "Forward", reverse: "Reverse (selected entity is the object)", choose: "Choose…", name: "University of Tromsø", P856: "Official websites", P1448: "Official names", all: "All stored values",
    contract: "Choose forward (entity → relationship → values) or reverse (values ← relationship — entity). No filtering, counting, joins, writes or raw SPARQL.",
    optional: "Optional original question — unverified user intent", question: "Original question (not interpreted)",
    warning: "This text can retrieve optional BM25 entity and property suggestions, but never selects an operation. You must choose any suggestion yourself. Requests such as ‘only English names’, counting or raw SPARQL are unsupported; the original question remains unverified.",
    suggest: "Retrieve BM25 entity and property suggestions", suggestionsTitle: "Optional graph suggestions", suggestionsHelp: "BM25 ranks text matches; scores are not probabilities. Suggestions never select or authorize a query.", suggesting: "Retrieving BM25 candidates and shape guidance…", noQuestionForSuggestions: "Enter a question to retrieve graph suggestions.",
    suggestionsReady: "Suggestions loaded. Review the source evidence and shape guidance, then choose any supported entity and property yourself.", entityCandidatesTitle: "Entity candidates", propertyCandidatesTitle: "Property candidates", noEntityCandidates: "No entity candidates matched this question in the selected graph.", noSuggestions: "No property candidates matched this question in the selected graph.", metadataCandidatesTitle: "Source-backed property metadata", metadataCandidatesHelp: "These BM25 suggestions use retained CC0 Wikidata property labels and descriptions, mapped only to predicates already present in the selected graph. They are metadata, not data facts or source witnesses.", metadataCandidatesEmpty: "No retained property metadata matched this question.", metadataProvenance: "Property metadata source, mapping and index", metadataLabelOrigin: "Property label from retained source metadata; language", metadataEvidence: "CC0 property definition text and directClaim mapping (not a data edge)", neighborhoodEntitiesTitle: "Source-witnessed nearby entities", neighborhoodEntitiesHelp: "These entities are endpoints of stored edges connected to BM25 entity candidates. Their display order does not indicate question relevance; some are outside this demo operation scope.", neighborhoodEntitiesClipped: "Nearby entity suggestions were capped. Missing entities are unknown.", neighborhoodEntitiesEmpty: "No additional entity endpoints with a selected-graph entity role were found.", neighborhoodCandidatesTitle: "Source-witnessed nearby properties", neighborhoodHelp: "These properties have stored edges to a BM25 entity candidate. Their neighborhood rank does not show which property answers the question. Inspect the original edge and choose manually.", neighborhoodClipped: "Neighborhood retrieval was clipped. Missing entities, properties or edges are unknown.", neighborhoodEmpty: "No supported SHACL property was witnessed next to the retrieved entities.", neighborhoodRank: "Neighborhood rank (not BM25)", bm25SeedRank: "BM25 seed rank", outgoingWitness: "Stored outgoing source edge from the BM25 entity", incomingWitness: "Stored incoming source edge to the BM25 entity", neighborhoodEvidence: "Original RDF witness and BM25 entity seed", neighborhoodProvenance: "Neighborhood retrieval version, rules, and packet ID", useEntity: "Use this entity", unsupportedEntity: "This entity is outside the currently supported operation.", useProperty: "Use this property", shapeOrigin: "Operator-authored demo SHACL metadata — guidance only, not source facts or a data validation result.",
    sourceLabel: "Untrusted label text from the selected graph", interfaceLabelOnly: "Interface label only; no label exists in the selected language.", noSourceLabel: "No label in the selected language; showing the IRI.",
    score: "BM25 score (not probability)", rank: "Rank", pathForward: "Forward SHACL path", pathInverse: "Inverse SHACL path", pathMismatch: "SHACL path direction differs from your selected query direction. The manual query choice remains in force.", noShapeGuidance: "No supported SHACL guidance for this candidate; it remains available as a BM25 suggestion.", candidateEvidence: "Untrusted graph text and observed RDF usage evidence", shapeMetadata: "Shape source, license, snapshots, and SHA-256",
    preview: "Preview selected operation separately", review: "Review before approval", relationForward: "This operation follows the relationship from the selected entity. Approval executes this operation only.", relationReverse: "This operation finds subjects that point to the selected entity. It does not create inverse RDF statements. Approval executes this operation only.",
    unverified: "Original question: unverified and not interpreted. The result answers only the manually selected graph operation.",
    rust: "Authoritative Rust query preview", technical: "Exact plan, authorization, snapshot, source and limits", approve: "Approve this exact operation and run once", cancel: "Cancel",
    results: "Results of the selected operation", evidence: "Original source triples, graph, snapshot, provenance, licenses and receipt", scope: "Authorized local scope and limitations",
    limits: "Only University of Tromsø (Q279724), official websites (P856) and official names (P1448), in the retained Wikidata development graph. Missing facts do not establish real-world absence. Source labels are untrusted. Human comprehension is unmeasured. This is not general natural-language understanding.",
    changed: "Choices or question changed. Request a new preview.", error: "Operation unavailable, stale or failed. No answer is asserted. Request a new preview or reopen the private terminal URL.",
    building: "Building the Rust preview; no answer query executes.", select: "Choose the entity, relationship and direction first.", ready: "Inspect the operation, graph, snapshot and limits. Approval is a separate action.",
    expired: "Review expired. Request a new preview.", cancelled: "Cancelled. Pending approval invalidated.", running: "Running the separately approved read-only operation…", done: "Selected graph operation executed after separate approval.",
    noQuestion: "No original question supplied.", graph: "Authorized graph", lease: "Single-use approval expires within", seconds: "seconds.", values: "RDF values", empty: "No rows under this operation and snapshot. This does not establish real-world nonexistence.",
    rows: "Rows", evidenceLabel: "Evidence", complete: "complete", clipped: "clipped", truth: "Source correctness describes the retained snapshot; real-world truth is not established.",
    languageTag: "Language", datatype: "Datatype", iri: "Original IRI", literal: "Original RDF literal", missing: "Original source evidence clipped; inspect the receipt."
  },
  nb: {
    title: "Velg en grafoperasjon", intro: "Velg entitet, relasjon og retning. Valgene bestemmer spørringen. Ingen språkmodell eller tolkning av spørsmål brukes.",
    language: "Grensesnittspråk", entity: "Entitet", relationship: "Relasjon", direction: "Retning", forward: "Forover", reverse: "Bakover (valgt entitet er objektet)", choose: "Velg…", name: "Universitetet i Tromsø", P856: "Offisielle nettsteder", P1448: "Offisielle navn", all: "Alle lagrede verdier",
    contract: "Velg forover (entitet → relasjon → verdier) eller bakover (verdier ← relasjon — entitet). Ingen filtrering, telling, sammenkoblinger, skriving eller rå SPARQL.",
    optional: "Valgfritt originalspørsmål — ubekreftet brukerintensjon", question: "Originalspørsmål (tolkes ikke)",
    warning: "Teksten kan hente valgfrie BM25-forslag til entiteter og egenskaper, men velger aldri en operasjon. Du må selv velge et forslag. Ønsker som «bare engelske navn», telling eller rå SPARQL støttes ikke; originalspørsmålet er fortsatt ubekreftet.",
    suggest: "Hent BM25-forslag til entiteter og egenskaper", suggestionsTitle: "Valgfrie grafkandidater", suggestionsHelp: "BM25 rangerer teksttreff; poengsummer er ikke sannsynligheter. Forslagene velger eller autoriserer aldri en spørring.", suggesting: "Henter BM25-kandidater og formveiledning…", noQuestionForSuggestions: "Skriv inn et spørsmål for å hente grafkandidater.",
    suggestionsReady: "Forslag hentet. Se gjennom kildebevis og formveiledning, og velg deretter en støttet entitet og egenskap selv.", entityCandidatesTitle: "Entitetskandidater", propertyCandidatesTitle: "Egenskapskandidater", noEntityCandidates: "Ingen entitetskandidater passet spørsmålet i den valgte grafen.", noSuggestions: "Ingen egenskapskandidater passet spørsmålet i den valgte grafen.", metadataCandidatesTitle: "Kildebaserte egenskapsmetadata", metadataCandidatesHelp: "Disse BM25-forslagene bruker bevarte CC0-etiketter og beskrivelser for Wikidata-egenskaper. De kobles bare til predikater som allerede finnes i den valgte grafen. Metadata er ikke fakta eller kildebevis.", metadataCandidatesEmpty: "Ingen bevarte egenskapsmetadata passet spørsmålet.", metadataProvenance: "Kilde, kobling og indeks for egenskapsmetadata", metadataLabelOrigin: "Egenskapsetikett fra bevarte kildemetadata; språk", metadataEvidence: "CC0-definisjonstekst og directClaim-kobling (ikke en datakant)", neighborhoodEntitiesTitle: "Kildebevitnede naboentiteter", neighborhoodEntitiesHelp: "Disse entitetene er endepunkter på lagrede kanter til BM25-entitetskandidater. Rekkefølgen viser ikke spørsmålsrelevans; noen ligger utenfor omfanget til denne demooperasjonen.", neighborhoodEntitiesClipped: "Naboforslagene for entiteter ble begrenset. Manglende entiteter er ukjent.", neighborhoodEntitiesEmpty: "Ingen andre entitetsendepunkter med entitetsrolle i den valgte grafen ble funnet.", neighborhoodCandidatesTitle: "Kildebevitnede egenskaper i nabolaget", neighborhoodHelp: "Disse egenskapene har lagrede kanter til en BM25-entitetskandidat. Rangeringen i nabolaget sier ikke hvilken egenskap som svarer på spørsmålet. Se på originalkanten og velg selv.", neighborhoodClipped: "Nabolagssøket ble avkortet. Manglende entiteter, egenskaper eller kanter er ukjent.", neighborhoodEmpty: "Ingen støttet SHACL-egenskap ble bevitnet nær de hentede entitetene.", neighborhoodRank: "Nabolagsrangering (ikke BM25)", bm25SeedRank: "BM25-frørangering", outgoingWitness: "Lagret utgående kildekant fra BM25-entiteten", incomingWitness: "Lagret inngående kildekant til BM25-entiteten", neighborhoodEvidence: "Opprinnelig RDF-bevis og BM25-entitetsfrø", neighborhoodProvenance: "Versjon, regler og pakke-ID for nabolagssøket", useEntity: "Bruk denne entiteten", unsupportedEntity: "Denne entiteten støttes ikke i den gjeldende operasjonen.", useProperty: "Bruk denne egenskapen", shapeOrigin: "Operatørforfattet SHACL-demodata — kun veiledning, ikke kildefakta eller valideringsresultat.",
    sourceLabel: "Ubetrodd etikett fra den valgte grafen", interfaceLabelOnly: "Kun grensesnittnavn; ingen etikett finnes på valgt språk.", noSourceLabel: "Ingen etikett på valgt språk; viser IRI-en.",
    score: "BM25-poengsum (ikke sannsynlighet)", rank: "Rangering", pathForward: "Forover SHACL-sti", pathInverse: "Invertert SHACL-sti", pathMismatch: "SHACL-stiens retning avviker fra den valgte spørringsretningen. Det manuelle spørringsvalget gjelder fortsatt.", noShapeGuidance: "Ingen støttet SHACL-veiledning for denne kandidaten; den er fortsatt tilgjengelig som BM25-forslag.", candidateEvidence: "Ubetrodd graftekst og observert RDF-bruksbevis", shapeMetadata: "Formkilde, lisens, øyeblikksbilder og SHA-256",
    preview: "Forhåndsvis valgt operasjon separat", review: "Se gjennom før godkjenning", relationForward: "Operasjonen følger relasjonen fra den valgte entiteten. Godkjenning kjører kun denne operasjonen.", relationReverse: "Operasjonen finner subjekter som peker på den valgte entiteten. Den oppretter ingen omvendte RDF-utsagn. Godkjenning kjører kun denne operasjonen.",
    unverified: "Originalspørsmål: ubekreftet og ikke tolket. Resultatet gjelder kun den manuelt valgte grafoperasjonen.",
    rust: "Autoritativ forhåndsvisning fra Rust", technical: "Eksakt plan, autorisasjon, øyeblikksbilde, kilde og grenser", approve: "Godkjenn denne eksakte operasjonen og kjør én gang", cancel: "Avbryt",
    results: "Resultater fra valgt operasjon", evidence: "Opprinnelige kildetripler, graf, øyeblikksbilde, proveniens, lisenser og kvittering", scope: "Autorisert lokalt omfang og begrensninger",
    limits: "Kun Universitetet i Tromsø (Q279724), offisielle nettsteder (P856) og offisielle navn (P1448), i den bevarte Wikidata-utviklingsgrafen. Manglende fakta beviser ikke fravær i virkeligheten. Kildeetiketter er ubekreftede. Menneskelig forståelse er ikke målt. Dette er ikke generell språkforståelse.",
    changed: "Valg eller spørsmål er endret. Be om en ny forhåndsvisning.", error: "Operasjonen er utilgjengelig, foreldet eller feilet. Intet svar hevdes. Be om ny forhåndsvisning eller åpne den private terminaladressen igjen.",
    building: "Bygger forhåndsvisningen i Rust; ingen svarspørring kjøres.", select: "Velg entitet, relasjon og retning først.", ready: "Se gjennom operasjonen, grafen, øyeblikksbildet og grensene. Godkjenning er en egen handling.",
    expired: "Godkjenningen er utløpt. Be om ny forhåndsvisning.", cancelled: "Avbrutt. Ventende godkjenning er ugyldig.", running: "Kjører den separat godkjente, skrivebeskyttede operasjonen…", done: "Valgt grafoperasjon ble kjørt etter separat godkjenning.",
    noQuestion: "Intet originalspørsmål oppgitt.", graph: "Autorisert graf", lease: "Engangsgodkjenning utløper innen", seconds: "sekunder.", values: "RDF-verdier", empty: "Ingen rader for denne operasjonen og dette øyeblikksbildet. Dette beviser ikke fravær i virkeligheten.",
    rows: "Rader", evidenceLabel: "Kildebevis", complete: "komplett", clipped: "avkortet", truth: "Kildekorrekthet beskriver det bevarte øyeblikksbildet; sannhet i virkeligheten er ikke fastslått.",
    languageTag: "Språk", datatype: "Datatype", iri: "Opprinnelig IRI", literal: "Opprinnelig RDF-literal", missing: "Opprinnelig kildebevis er avkortet; se kvitteringen."
  }
};
const t = key => words[$("language").value][key];
async function api(route, body, keepalive = false) {
  const response = await fetch(route, {method: "POST", headers: {"Content-Type": "application/json",
    Authorization: "Bearer " + credential, "X-Verity-Tab": tab || ""}, body: JSON.stringify(body),
    cache: "no-store", keepalive, signal: keepalive ? undefined : AbortSignal.timeout(50000)});
  if (!response.ok) throw new Error(t("error"));
  return response.json();
}
function invalidate(message = "", notify = true) {
  epoch++; approval = undefined; clearTimeout(timer);
  $("approve").disabled = true; $("review").hidden = $("results").hidden = true;
  $("status").textContent = message;
  if (notify && tab) api(prefix + "cancel", {}, true).catch(() => {});
}
function renderSuggestions(data = suggestions) {
  if (!data) return;
  const guidance = data.shape_guidance;
  const entities = data.entity_candidates, nearbyEntities = data.neighborhood_entity_candidates,
    predicates = data.candidates, metadataPredicates = data.property_metadata.candidates,
    neighbors = data.neighborhood_candidates;
  $("suggestion-summary").textContent = `${entities.length} ${t("entityCandidatesTitle").toLowerCase()} · ${nearbyEntities.length} ${t("neighborhoodEntitiesTitle").toLowerCase()} · ${predicates.length} ${t("propertyCandidatesTitle").toLowerCase()} · ${metadataPredicates.length} ${t("metadataCandidatesTitle").toLowerCase()} · ${neighbors.length} ${t("neighborhoodCandidatesTitle").toLowerCase()} · ${t("graph")}: ${guidance.data_graph} · ${guidance.data_snapshot_id}`;
  $("shape-provenance").textContent = JSON.stringify({
    origin: guidance.origin, source: guidance.source, license: guidance.source.license,
    shape_graph: guidance.shape_graph, shape_snapshot_id: guidance.shape_snapshot_id,
    shape_sha256: guidance.shape_sha256, data_graph: guidance.data_graph,
    data_snapshot_id: guidance.data_snapshot_id, unsupported_property_shapes: guidance.unsupported_property_shapes,
    semantics: guidance.semantics
  }, null, 2);
  json("neighborhood-provenance", data.neighborhood);
  json("property-metadata-provenance", data.property_metadata);
  function renderCandidate(item, role, source = "bm25") {
    const candidate = item.candidate, article = document.createElement("article");
    const heading = document.createElement("h3"), labelOrigin = document.createElement("p"), detail = document.createElement("p");
    const evidence = document.createElement("details"), code = Object.keys(session.predicates).find(key => session.predicates[key] === candidate.iri);
    const sourceLabel = candidate.texts.find(text => text.field === "label" && text.value.language === data.request.language && text.value.text);
    const interfaceLabel = role === "entity" ? (candidate.iri === session.entity ? t("name") : null) : (code ? t(code) : null);
    heading.textContent = sourceLabel?.value.text || interfaceLabel || candidate.iri;
    labelOrigin.textContent = source === "property_metadata" ?
      `${t("metadataLabelOrigin")}: ${sourceLabel?.value.language || candidate.texts.find(text => text.field === "label")?.value.language || "—"}` :
      sourceLabel ? t("sourceLabel") : interfaceLabel ? t("interfaceLabelOnly") : t("noSourceLabel");
    detail.textContent = source === "neighborhood_entity" ?
      `${t("bm25SeedRank")}: ${item.witness.entity.rank} · ${candidate.graph}\n${candidate.iri}` :
      source === "neighborhood" ?
        `${t("neighborhoodRank")}: ${item.neighborhood_rank} · ${candidate.graph}\n${candidate.iri}` :
        `${t("rank")} ${item.rank} · ${t("score")}: ${candidate.ranking_score} · ${candidate.graph}\n${candidate.iri}`;
    const evidenceSummary = document.createElement("summary"), evidenceText = document.createElement("pre");
    evidenceSummary.textContent = source === "property_metadata" ? t("metadataEvidence") :
      source !== "bm25" ? t(item.witness.direction === "outgoing" ? "outgoingWitness" : "incomingWitness") : t("candidateEvidence");
    evidenceText.textContent = JSON.stringify(source === "property_metadata" ?
      {metadata: item.metadata, texts: candidate.texts} : source !== "bm25" ?
        {entity: item.witness.entity, statement: item.witness.statement, texts: candidate.texts} :
        {texts: candidate.texts, usage: candidate.usage}, null, 2);
    evidence.append(evidenceSummary, evidenceText);
    article.append(heading, labelOrigin, detail, evidence);
    if (role === "property" && source !== "property_metadata") {
      for (const property of item.shape_properties) {
        const p = document.createElement("p");
        const shapeDirection = property.path_direction === "inverse" ? "reverse" : "forward";
        p.textContent = `${property.path_direction === "inverse" ? t("pathInverse") : t("pathForward")}: ${property.predicate_iri}\n` +
          JSON.stringify({target_classes: property.target_classes, datatype: property.datatype, class: property.class,
            node_kind: property.node_kind, min_count: property.min_count, max_count: property.max_count});
        if ($("direction").value && shapeDirection !== $("direction").value) p.textContent += `\n${t("pathMismatch")}`;
        article.append(p);
      }
      if (!item.shape_properties.length) {
        const p = document.createElement("p"); p.textContent = t("noShapeGuidance"); article.append(p);
      }
    }
    const supported = role === "entity" ? candidate.iri === session.entity : Object.values(session.predicates).includes(candidate.iri);
    if (supported) {
      const use = document.createElement("button"); use.type = "button"; use.textContent = t(role === "entity" ? "useEntity" : "useProperty");
      use.addEventListener("click", () => {
        const select = $(role === "entity" ? "entity" : "predicate");
        select.value = candidate.iri;
        select.dispatchEvent(new Event("change"));
      });
      article.append(use);
    } else if (role === "entity") {
      const p = document.createElement("p"); p.textContent = t("unsupportedEntity"); article.append(p);
    }
    return article;
  }
  $("entity-suggestion-list").replaceChildren(...entities.map(item => renderCandidate(item, "entity")));
  $("neighborhood-entity-suggestion-list").replaceChildren(...nearbyEntities.map(item => renderCandidate(item, "entity", "neighborhood_entity")));
  $("suggestion-list").replaceChildren(...predicates.map(item => renderCandidate(item, "property")));
  $("metadata-suggestion-list").replaceChildren(...metadataPredicates.map(item => renderCandidate(item, "property", "property_metadata")));
  $("neighborhood-suggestion-list").replaceChildren(...neighbors.map(item => renderCandidate(item, "property", "neighborhood")));
  $("entity-suggestion-empty").hidden = entities.length > 0;
  $("neighborhood-entities-empty").hidden = nearbyEntities.length > 0;
  $("neighborhood-entities-clipped").hidden = !data.neighborhood_entities_clipped;
  $("suggestion-empty").hidden = predicates.length > 0;
  $("metadata-suggestion-empty").hidden = metadataPredicates.length > 0;
  $("neighborhood-empty").hidden = neighbors.length > 0;
  $("neighborhood-clipped").hidden = !data.neighborhood.clipped;
  $("suggestions").hidden = false;
}
function operation(request) {
  const step = request ? request.template.steps[0] : null;
  const predicate = step ? step.predicate : $("predicate").value;
  const direction = step ? step.direction : $("direction").value;
  const code = Object.keys(session.predicates).find(k => session.predicates[k] === predicate);
  return direction === "reverse" ? `${t("all")} ← ${t(code)} — ${t("name")}` : `${t("name")} → ${t(code)} → ${t("all")}`;
}
function translate() {
  document.documentElement.lang = $("language").value;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  if (session) {
    const entity = $("entity").value, predicate = $("predicate").value, direction = $("direction").value;
    $("entity").replaceChildren(new Option(t("choose"), ""), new Option(t("name") + " — Q279724", session.entity));
    $("predicate").replaceChildren(new Option(t("choose"), ""), ...Object.entries(session.predicates).map(([code, iri]) => new Option(t(code), iri)));
    $("direction").replaceChildren(new Option(t("choose"), ""), ...session.directions.map(value => new Option(t(value), value)));
    $("entity").value = entity; $("predicate").value = predicate; $("direction").value = direction;
  }
  selection();
}
function selection() {
  $("selected").textContent = session && $("entity").value && $("predicate").value && $("direction").value ? operation() : t("select");
  if (suggestions) renderSuggestions();
}
$("suggest").addEventListener("click", async () => {
  invalidate("", false);
  suggestions = undefined; $("suggestions").hidden = true;
  if (!$("question").value.trim()) { $("status").textContent = t("noQuestionForSuggestions"); return; }
  const generation = epoch;
  $("status").textContent = t("suggesting");
  try {
    const data = await api(prefix + "suggestions", {question: $("question").value, language: $("language").value});
    if (generation !== epoch) return;
    suggestions = data; renderSuggestions(data); $("suggestion-heading").focus(); $("status").textContent = t("suggestionsReady");
  } catch { if (generation === epoch) invalidate(t("error")); }
});
$("preview").addEventListener("click", async () => {
  invalidate(t("building"), false);
  if (!$("entity").value || !$("predicate").value || !$("direction").value) { $("status").textContent = t("select"); return; }
  const generation = epoch;
  try {
    const data = await api(prefix + "preview", {entity: $("entity").value, predicate: $("predicate").value, direction: $("direction").value,
      question: $("question").value, language: $("language").value});
    if (generation !== epoch) return;
    approval = data;
    const request = data.resolved.request;
    $("operation").textContent = operation(request);
    $("relation").textContent = t(request.template.steps[0].direction === "reverse" ? "relationReverse" : "relationForward");
    $("original").textContent = data.provenance.original_question || t("noQuestion");
    $("graph").textContent = `${t("graph")}: ${request.scope.join(", ")}\nSnapshot: ${request.snapshot_id}`;
    $("rust-summary").replaceChildren(...data.resolved.preview.summary.map(line => {
      const li = document.createElement("li"); li.textContent = line; return li;
    }));
    json("rust-preview", data.resolved.preview); json("sources", data.sources);
    $("expiry").textContent = `${t("lease")} ${Math.floor(data.review_seconds)} ${t("seconds")}`;
    $("review").hidden = false; $("review-heading").focus(); $("approve").disabled = false; $("status").textContent = t("ready");
    timer = setTimeout(() => invalidate(t("expired")), data.review_seconds * 1000);
  } catch { if (generation === epoch) invalidate(t("error")); }
});
$("approve").addEventListener("click", async () => {
  if (!approval) return;
  const token = approval.token;
  invalidate(t("running"), false);
  const generation = epoch;
  try {
    const data = await api(prefix + "confirm", {token, decision: "approve"});
    if (generation !== epoch) return;
    const result = data.outcome.result;
    $("result-operation").textContent = operation(data.provenance.selected_operation);
    $("result-question").textContent = data.provenance.original_question || t("noQuestion");
    $("result-status").textContent = (data.answers.length ? `${data.answers.length} ${t("values")}. ` : t("empty") + " ") +
      `${t("rows")}: ${t(result.complete_within_scope ? "complete" : "clipped")}; ${t("evidenceLabel")}: ${t(result.evidence_complete_for_returned_rows ? "complete" : "clipped")}. ${t("truth")}`;
    $("answers").replaceChildren();
    for (const answer of data.answers) {
      const article = document.createElement("article"), heading = document.createElement("h3"), meta = document.createElement("p");
      const value = answer.value;
      heading.textContent = value.value;
      meta.textContent = value.kind === "iri" ? `${t("iri")}: ${value.value}` :
        `${t("literal")} · ${t("languageTag")}: ${value.language || "—"} · ${t("datatype")}: ${value.datatype}`;
      const labels = document.createElement("p"); labels.textContent = answer.observed_labels.map(l => l.value.text).join(" / ");
      article.append(heading, meta, labels);
      if (!answer.evidence_complete) { const p = document.createElement("p"); p.textContent = t("missing"); article.append(p); }
      $("answers").append(article);
    }
    json("evidence", {snapshot_id: result.snapshot_id, graph: result.scope, triples: result.evidence, sources: data.sources});
    json("receipt", data); $("results").hidden = false; $("status").textContent = t("done");
  } catch { if (generation === epoch) invalidate(t("error")); }
});
for (const id of ["entity", "predicate", "direction", "language", "question"]) $(id).addEventListener(id === "question" ? "input" : "change", () => {
  invalidate(t("changed"));
  if (id === "language" || id === "question") { suggestions = undefined; $("suggestions").hidden = true; }
  if (id === "language") translate(); else selection();
});
$("cancel").addEventListener("click", () => { invalidate(t("cancelled")); $("preview").focus(); });
document.addEventListener("keydown", event => { if (event.key === "Escape") invalidate(t("cancelled")); });
document.addEventListener("visibilitychange", () => { if (document.hidden) invalidate(t("cancelled")); });
window.addEventListener("pagehide", () => invalidate(t("cancelled")));
window.addEventListener("popstate", () => invalidate(t("cancelled")));
(async () => {
  try {
    session = await api("/api/session", {}); tab = session.tab;
    json("scope", {scope: session.scope, snapshot_id: session.snapshot_id, receipt: session.receipt});
    translate(); $("entity").disabled = $("predicate").disabled = $("direction").disabled = $("suggest").disabled = $("preview").disabled = false;
    setTimeout(() => { invalidate(t("expired")); $("preview").disabled = true; }, session.session_seconds * 1000);
  } catch { invalidate(t("error")); }
})();
