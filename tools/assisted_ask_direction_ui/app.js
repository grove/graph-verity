"use strict";
const $ = id => document.getElementById(id);
const prefix = "/api/assisted-ask-v1-direction/";
const credential = location.hash.slice(1);
history.replaceState(null, "", location.pathname);
let tab, session, approval, suggestions, epoch = 0, timer;
const candidateOptions = {entity: new Map(), predicate: new Map()};
const json = (id, value) => { $(id).textContent = JSON.stringify(value, null, 2); };
const words = {
  en: {
    candidateTextsClipped: "Some source text was clipped or omitted; more labels or descriptions may exist.",
    outgoingUsageExamples: "Outgoing source statement examples in this packet", incomingUsageExamples: "Incoming source statement examples in this packet", predicateUsageExamples: "Source statement examples using this property in this packet", noUsageExamples: "No examples were returned; absence is unknown.", usageExamplesClipped: "This evidence page is capped; additional source statements may exist.",
    entityCandidatesClipped: "Entity candidates were capped by the retrieval limit; additional candidates are unknown.", predicateCandidatesClipped: "Property candidates were capped by the retrieval limit; additional candidates are unknown.", metadataCandidatesClipped: "Source metadata retrieval was capped; additional property candidates are unknown.",
    twoHopCandidatesTitle: "Source-witnessed two-hop IRI paths", twoHopCandidatesHelp: "Each IRI endpoint is reached through two original directed statements in the selected graph. Traversal order does not indicate question relevance; inspect both statements and their directions.", twoHopCandidatesEmpty: "No additional IRI endpoints were found through two-hop paths.", twoHopCandidatesClipped: "Two-hop path retrieval was incomplete or capped. Missing paths are unknown.", twoHopEvidence: "Two original directed RDF statements and the BM25 seed",
    title: "Select a graph operation", intro: "Choose an entity, relationship and direction. These choices define the query. No language model or question interpretation is used.",
    language: "Interface language", entity: "Entity", relationship: "Relationship", direction: "Direction", forward: "Forward", reverse: "Reverse (selected entity is the object)", choose: "Choose…", name: "University of Tromsø", P856: "Official websites", P1448: "Official names", all: "All stored values",
    contract: "Choose forward (entity → relationship → values) or reverse (values ← relationship — entity). No filtering, counting, joins, writes or raw SPARQL.",
    optional: "Optional original question — unverified user intent", question: "Original question (not interpreted)",
    warning: "This text can retrieve optional BM25 entity and property suggestions, but never selects an operation. Choose any suggestion yourself. A source-witnessed operation button fills all three choices only after your click; it does not preview or authorize. Requests such as ‘only English names’, counting or raw SPARQL are unsupported; the original question remains unverified.",
    suggest: "Retrieve BM25 entity and property suggestions", suggestionsTitle: "Optional graph suggestions", suggestionsHelp: "BM25 ranks text matches; scores are not probabilities. Candidate buttons add one selector at a time; source-witnessed operation buttons fill all three only after your click. Nothing previews or authorizes a query.", suggesting: "Retrieving BM25 candidates and shape guidance…", noQuestionForSuggestions: "Enter a question to retrieve graph suggestions.",
    suggestionsReady: "Suggestions loaded. Review the source evidence, then explicitly add any candidate that belongs to the authorized graph.", entityCandidatesTitle: "Entity candidates", propertyCandidatesTitle: "Property candidates", noEntityCandidates: "No entity candidates matched this question in the selected graph.", noSuggestions: "No property candidates matched this question in the selected graph.", metadataCandidatesTitle: "Source-backed property metadata", metadataCandidatesHelp: "These BM25 suggestions use retained CC0 Wikidata property labels and descriptions, mapped only to predicates already present in the selected graph. They are metadata, not data facts or source witnesses.", metadataCandidatesEmpty: "No retained property metadata matched this question.", metadataLanguageUnavailable: "No Norwegian text is available in the retained property metadata for this graph. Inspect each candidate’s source language.", metadataProvenance: "Property metadata source, mapping and index", metadataLabelOrigin: "Property label from retained source metadata; language", metadataEvidence: "CC0 property definition text and directClaim mapping (not a data edge)", neighborhoodEntitiesTitle: "Source-witnessed nearby entities", neighborhoodEntitiesHelp: "These entities are endpoints of stored edges connected to BM25 entity candidates. Their display order does not indicate question relevance. A Use button appears only when the IRI has the entity role in the authorized graph.", neighborhoodEntitiesClipped: "Nearby entity suggestions were capped. Missing entities are unknown.", neighborhoodEntitiesEmpty: "No additional entity endpoints with a selected-graph entity role were found.", neighborhoodCandidatesTitle: "Source-witnessed nearby properties", neighborhoodHelp: "These properties have stored edges to a BM25 entity candidate. Their neighborhood rank does not show which property answers the question. Inspect the original edge and choose manually.", neighborhoodClipped: "Neighborhood retrieval was clipped. Missing entities, properties or edges are unknown.", neighborhoodEmpty: "No additional source-witnessed property candidates were found near the retrieved entities.", neighborhoodRank: "Neighborhood rank (not BM25)", bm25SeedRank: "BM25 seed rank", outgoingWitness: "Stored outgoing source edge from the BM25 entity", incomingWitness: "Stored incoming source edge to the BM25 entity", neighborhoodEvidence: "Original RDF witness and BM25 entity seed", neighborhoodProvenance: "Neighborhood retrieval version, rules, and packet ID", useEntity: "Use this entity", notSelectable: "This candidate is not eligible in the authorized graph for this role.", useProperty: "Use this property", shapeOrigin: "SHACL origin", shapeOriginDemo: "Operator-authored demo SHACL metadata", shapeOriginPublished: "Source-published SHACL metadata", shapeProvenanceUnverified: "Source and license provenance are operator-provided and not independently verified; guidance only, not source facts or a validation result.",
    sourceLabel: "Untrusted label text from the selected graph", interfaceLabelOnly: "Interface label only; no label exists in the selected language.", noSourceLabel: "No label in the selected language; showing the IRI.",
    useWitnessedOperation: "Select source-witnessed operation", witnessedOperationSelected: "Source-witnessed choices filled. Review them, then preview separately.",
    score: "BM25 score (not probability)", rank: "Rank", pathForward: "Forward SHACL path", pathInverse: "Inverse SHACL path", pathMismatch: "SHACL path direction differs from your selected query direction. The manual query choice remains in force.", noShapeGuidance: "No supported SHACL guidance for this candidate; its retrieval source is shown above.", candidateEvidence: "Untrusted graph text and observed RDF usage evidence", shapeMetadata: "Shape source, license, snapshots, and SHA-256",
    preview: "Preview selected operation separately", review: "Review before approval", relationForward: "This operation follows the relationship from the selected entity. Approval executes this operation only.", relationReverse: "This operation finds subjects that point to the selected entity. It does not create inverse RDF statements. Approval executes this operation only.",
    unverified: "Original question: unverified and not interpreted. The result answers only the manually selected graph operation.",
    rust: "Authoritative Rust query preview", technical: "Exact plan, authorization, snapshot, source and limits", approve: "Approve this exact operation and run once", cancel: "Cancel",
    results: "Results of the selected operation", evidence: "Original source triples, graph, snapshot, provenance, licenses and receipt", scope: "Authorized local scope and limitations",
    limits: "One-hop operations use only entities and predicates observed in the retained Wikidata development graph. The user selects the exact IRIs and direction; the question remains unverified and is not interpreted. Missing facts do not establish real-world absence. Source labels are untrusted. Human comprehension is unmeasured.",
    changed: "Choices or question changed. Request a new preview.", error: "Operation unavailable, stale or failed. No answer is asserted. Request a new preview or reopen the private terminal URL.",
    building: "Building the Rust preview; no answer query executes.", select: "Choose the entity, relationship and direction first.", ready: "Inspect the operation, graph, snapshot and limits. Approval is a separate action.",
    expired: "Review expired. Request a new preview.", cancelled: "Cancelled. Pending approval invalidated.", running: "Running the separately approved read-only operation…", done: "Selected graph operation executed after separate approval.",
    noQuestion: "No original question supplied.", graph: "Authorized graph", lease: "Single-use approval expires within", seconds: "seconds.", values: "RDF values", empty: "No rows under this operation and snapshot. This does not establish real-world nonexistence.",
    rows: "Rows", evidenceLabel: "Evidence", complete: "complete", clipped: "clipped", truth: "Source correctness describes the retained snapshot; real-world truth is not established.",
    languageTag: "Language", datatype: "Datatype", iri: "Original IRI", literal: "Original RDF literal", missing: "Original source evidence clipped; inspect the receipt."
  },
  nb: {
    candidateTextsClipped: "Noe kildetekst er avkortet eller utelatt; det kan finnes flere etiketter eller beskrivelser.",
    outgoingUsageExamples: "Eksempler på utgående kildeutsagn i denne pakken", incomingUsageExamples: "Eksempler på innkommende kildeutsagn i denne pakken", predicateUsageExamples: "Eksempler på kildeutsagn som bruker denne egenskapen i pakken", noUsageExamples: "Ingen eksempler ble returnert; fravær er ukjent.", usageExamplesClipped: "Denne bevislisten er begrenset; det kan finnes flere kildeutsagn.",
    entityCandidatesClipped: "Entitetskandidatene ble begrenset av hentingsgrensen; flere kandidater er ukjente.", predicateCandidatesClipped: "Egenskapskandidatene ble begrenset av hentingsgrensen; flere kandidater er ukjente.", metadataCandidatesClipped: "Hentingen av kildemetadata ble begrenset; flere egenskapskandidater er ukjente.",
    twoHopCandidatesTitle: "Kildebevitnede IRI-stier med to kanter", twoHopCandidatesHelp: "Hvert IRI-endepunkt nås gjennom to opprinnelige, rettede utsagn i den valgte grafen. Traverseringsrekkefølgen viser ikke spørsmålsrelevans; se på begge utsagnene og retningene.", twoHopCandidatesEmpty: "Ingen ekstra IRI-endepunkter ble funnet gjennom stier med to kanter.", twoHopCandidatesClipped: "Hentingen av stier med to kanter var ufullstendig eller begrenset. Manglende stier er ukjent.", twoHopEvidence: "To opprinnelige, rettede RDF-utsagn og BM25-frøet",
    title: "Velg en grafoperasjon", intro: "Velg entitet, relasjon og retning. Valgene bestemmer spørringen. Ingen språkmodell eller tolkning av spørsmål brukes.",
    language: "Grensesnittspråk", entity: "Entitet", relationship: "Relasjon", direction: "Retning", forward: "Forover", reverse: "Bakover (valgt entitet er objektet)", choose: "Velg…", name: "Universitetet i Tromsø", P856: "Offisielle nettsteder", P1448: "Offisielle navn", all: "Alle lagrede verdier",
    contract: "Velg forover (entitet → relasjon → verdier) eller bakover (verdier ← relasjon — entitet). Ingen filtrering, telling, sammenkoblinger, skriving eller rå SPARQL.",
    optional: "Valgfritt originalspørsmål — ubekreftet brukerintensjon", question: "Originalspørsmål (tolkes ikke)",
    warning: "Teksten kan hente valgfrie BM25-forslag til entiteter og egenskaper, men velger aldri en operasjon. Velg forslagene selv. En knapp for kildebevitnet operasjon fyller alle tre valg først når du klikker; den forhåndsviser eller godkjenner ikke. Ønsker som «bare engelske navn», telling eller rå SPARQL støttes ikke; originalspørsmålet er fortsatt ubekreftet.",
    suggest: "Hent BM25-forslag til entiteter og egenskaper", suggestionsTitle: "Valgfrie grafkandidater", suggestionsHelp: "BM25 rangerer teksttreff; poengsummer er ikke sannsynligheter. Kandidatknapper legger til ett valg om gangen; knapper for kildebevitnede operasjoner fyller alle tre først når du klikker. Ingenting forhåndsviser eller godkjenner en spørring.", suggesting: "Henter BM25-kandidater og formveiledning…", noQuestionForSuggestions: "Skriv inn et spørsmål for å hente grafkandidater.",
    suggestionsReady: "Forslagene er hentet. Se gjennom kildebeviset og legg bare til kandidater fra den autoriserte grafen med et uttrykkelig klikk.", entityCandidatesTitle: "Entitetskandidater", propertyCandidatesTitle: "Egenskapskandidater", noEntityCandidates: "Ingen entitetskandidater passet spørsmålet i den valgte grafen.", noSuggestions: "Ingen egenskapskandidater passet spørsmålet i den valgte grafen.", metadataCandidatesTitle: "Kildebaserte egenskapsmetadata", metadataCandidatesHelp: "Disse BM25-forslagene bruker bevarte CC0-etiketter og beskrivelser for Wikidata-egenskaper. De kobles bare til predikater som allerede finnes i den valgte grafen. Metadata er ikke fakta eller kildebevis.", metadataCandidatesEmpty: "Ingen bevarte egenskapsmetadata passet spørsmålet.", metadataLanguageUnavailable: "Det finnes ingen norsk tekst i de bevarte egenskapsmetadataene for denne grafen. Se kildespråket for hver kandidat.", metadataProvenance: "Kilde, kobling og indeks for egenskapsmetadata", metadataLabelOrigin: "Egenskapsetikett fra bevarte kildemetadata; språk", metadataEvidence: "CC0-definisjonstekst og directClaim-kobling (ikke en datakant)", neighborhoodEntitiesTitle: "Kildebevitnede naboentiteter", neighborhoodEntitiesHelp: "Disse entitetene er endepunkter på lagrede kanter til BM25-entitetskandidater. Rekkefølgen viser ikke spørsmålsrelevans. Bruk-knappen vises bare når IRI-en har entitetsrollen i den autoriserte grafen.", neighborhoodEntitiesClipped: "Naboforslagene for entiteter ble begrenset. Manglende entiteter er ukjent.", neighborhoodEntitiesEmpty: "Ingen andre entitetsendepunkter med entitetsrolle i den valgte grafen ble funnet.", neighborhoodCandidatesTitle: "Kildebevitnede egenskaper i nabolaget", neighborhoodHelp: "Disse egenskapene har lagrede kanter til en BM25-entitetskandidat. Rangeringen i nabolaget sier ikke hvilken egenskap som svarer på spørsmålet. Se på originalkanten og velg selv.", neighborhoodClipped: "Nabolagssøket ble avkortet. Manglende entiteter, egenskaper eller kanter er ukjent.", neighborhoodEmpty: "Ingen ekstra kildebevitnede egenskaper ble funnet nær de hentede entitetene.", neighborhoodRank: "Nabolagsrangering (ikke BM25)", bm25SeedRank: "BM25-frørangering", outgoingWitness: "Lagret utgående kildekant fra BM25-entiteten", incomingWitness: "Lagret inngående kildekant til BM25-entiteten", neighborhoodEvidence: "Opprinnelig RDF-bevis og BM25-entitetsfrø", neighborhoodProvenance: "Versjon, regler og pakke-ID for nabolagssøket", useEntity: "Bruk denne entiteten", notSelectable: "Denne kandidaten er ikke gyldig for denne rollen i den autoriserte grafen.", useProperty: "Bruk denne egenskapen", shapeOrigin: "SHACL-opprinnelse", shapeOriginDemo: "Operatørforfattede SHACL-demodata", shapeOriginPublished: "Kildepubliserte SHACL-metadata", shapeProvenanceUnverified: "Kilde- og lisensproveniens er oppgitt av operatøren og ikke verifisert uavhengig; kun veiledning, ikke kildefakta eller en validering.",
    sourceLabel: "Ubetrodd etikett fra den valgte grafen", interfaceLabelOnly: "Kun grensesnittnavn; ingen etikett finnes på valgt språk.", noSourceLabel: "Ingen etikett på valgt språk; viser IRI-en.",
    useWitnessedOperation: "Velg kildebevitnet operasjon", witnessedOperationSelected: "Kildebevitnede valg er fylt inn. Se gjennom dem, og forhåndsvis separat.",
    score: "BM25-poengsum (ikke sannsynlighet)", rank: "Rangering", pathForward: "Forover SHACL-sti", pathInverse: "Invertert SHACL-sti", pathMismatch: "SHACL-stiens retning avviker fra den valgte spørringsretningen. Det manuelle spørringsvalget gjelder fortsatt.", noShapeGuidance: "Ingen støttet SHACL-veiledning for denne kandidaten; hentekilden vises ovenfor.", candidateEvidence: "Ubetrodd graftekst og observert RDF-bruksbevis", shapeMetadata: "Formkilde, lisens, øyeblikksbilder og SHA-256",
    preview: "Forhåndsvis valgt operasjon separat", review: "Se gjennom før godkjenning", relationForward: "Operasjonen følger relasjonen fra den valgte entiteten. Godkjenning kjører kun denne operasjonen.", relationReverse: "Operasjonen finner subjekter som peker på den valgte entiteten. Den oppretter ingen omvendte RDF-utsagn. Godkjenning kjører kun denne operasjonen.",
    unverified: "Originalspørsmål: ubekreftet og ikke tolket. Resultatet gjelder kun den manuelt valgte grafoperasjonen.",
    rust: "Autoritativ forhåndsvisning fra Rust", technical: "Eksakt plan, autorisasjon, øyeblikksbilde, kilde og grenser", approve: "Godkjenn denne eksakte operasjonen og kjør én gang", cancel: "Avbryt",
    results: "Resultater fra valgt operasjon", evidence: "Opprinnelige kildetripler, graf, øyeblikksbilde, proveniens, lisenser og kvittering", scope: "Autorisert lokalt omfang og begrensninger",
    limits: "Ettkantsoperasjoner bruker bare entiteter og predikater som er observert i den bevarte Wikidata-utviklingsgrafen. Brukeren velger eksakte IRI-er og retning; spørsmålet forblir ubekreftet og tolkes ikke. Manglende fakta beviser ikke fravær i virkeligheten. Kildeetiketter er ubekreftede. Menneskelig forståelse er ikke målt.",
    changed: "Valg eller spørsmål er endret. Be om en ny forhåndsvisning.", error: "Operasjonen er utilgjengelig, foreldet eller feilet. Intet svar hevdes. Be om ny forhåndsvisning eller åpne den private terminaladressen igjen.",
    building: "Bygger forhåndsvisningen i Rust; ingen svarspørring kjøres.", select: "Velg entitet, relasjon og retning først.", ready: "Se gjennom operasjonen, grafen, øyeblikksbildet og grensene. Godkjenning er en egen handling.",
    expired: "Godkjenningen er utløpt. Be om ny forhåndsvisning.", cancelled: "Avbrutt. Ventende godkjenning er ugyldig.", running: "Kjører den separat godkjente, skrivebeskyttede operasjonen…", done: "Valgt grafoperasjon ble kjørt etter separat godkjenning.",
    noQuestion: "Intet originalspørsmål oppgitt.", graph: "Autorisert graf", lease: "Engangsgodkjenning utløper innen", seconds: "sekunder.", values: "RDF-verdier", empty: "Ingen rader for denne operasjonen og dette øyeblikksbildet. Dette beviser ikke fravær i virkeligheten.",
    rows: "Rader", evidenceLabel: "Kildebevis", complete: "komplett", clipped: "avkortet", truth: "Kildekorrekthet beskriver det bevarte øyeblikksbildet; sannhet i virkeligheten er ikke fastslått.",
    languageTag: "Språk", datatype: "Datatype", iri: "Opprinnelig IRI", literal: "Opprinnelig RDF-literal", missing: "Opprinnelig kildebevis er avkortet; se kvitteringen."
  }
};
const t = key => words[$("language").value][key];
const selectedSourceLabel = texts => texts.find(text => text.field === "label" &&
  text.value.language === $("language").value && text.value.text);
const candidateOption = (iri, texts) => {
  const label = selectedSourceLabel(texts)?.value.text;
  return [label ? `${label} — ${iri}` : iri, iri];
};
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
  const shapeOrigin = guidance.origin === "operator_authored_demo" ? t("shapeOriginDemo") :
    guidance.origin === "source_published" ? t("shapeOriginPublished") : String(guidance.origin);
  $("shape-origin").textContent = `${t("shapeOrigin")}: ${shapeOrigin}. ${t("shapeProvenanceUnverified")}`;
  const entities = data.entity_candidates, nearbyEntities = data.neighborhood_entity_candidates,
    predicates = data.candidates, metadataPredicates = data.property_metadata.candidates,
    neighbors = data.neighborhood_candidates, twoHop = data.two_hop_candidates || [];
  const norwegianText = data.property_metadata.text_languages.some(language => ["no", "nb", "nn"].includes(language));
  $("metadata-language-note").hidden = !["no", "nb", "nn"].includes(data.request.language) || norwegianText;
  $("suggestion-summary").textContent = `${entities.length} ${t("entityCandidatesTitle").toLowerCase()} · ${nearbyEntities.length} ${t("neighborhoodEntitiesTitle").toLowerCase()} · ${twoHop.length} ${t("twoHopCandidatesTitle").toLowerCase()} · ${predicates.length} ${t("propertyCandidatesTitle").toLowerCase()} · ${metadataPredicates.length} ${t("metadataCandidatesTitle").toLowerCase()} · ${neighbors.length} ${t("neighborhoodCandidatesTitle").toLowerCase()} · ${t("graph")}: ${guidance.data_graph} · ${guidance.data_snapshot_id}`;
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
    article.append(heading, labelOrigin);
    detail.textContent = source === "two_hop" ?
      `${candidate.graph}\n${candidate.iri}` : source === "neighborhood_entity" ?
      `${t("bm25SeedRank")}: ${item.witness.entity.rank} · ${candidate.graph}\n${candidate.iri}` :
      source === "neighborhood" ?
        `${t("neighborhoodRank")}: ${item.neighborhood_rank} · ${candidate.graph}\n${candidate.iri}` :
        `${t("rank")} ${item.rank} · ${t("score")}: ${candidate.ranking_score} · ${candidate.graph}\n${candidate.iri}`;
    if (source === "bm25") for (const page of candidate.usage || []) {
      const label = ({outgoing: t("outgoingUsageExamples"), incoming: t("incomingUsageExamples"),
        predicate: t("predicateUsageExamples")})[page.direction];
      if (!label) continue;
      const usage = document.createElement("p");
      usage.textContent = page.evidence.length ? `${label}: ${page.evidence.length}` : `${label}. ${t("noUsageExamples")}`;
      article.append(usage);
      if (page.clipped) {
        const note = document.createElement("p");
        note.setAttribute("role", "note"); note.textContent = t("usageExamplesClipped"); article.append(note);
      }
    }
    const evidenceSummary = document.createElement("summary"), evidenceText = document.createElement("pre");
    evidenceSummary.textContent = source === "two_hop" ? t("twoHopEvidence") :
      source === "property_metadata" ? t("metadataEvidence") :
      source !== "bm25" ? t(item.witness.direction === "outgoing" ? "outgoingWitness" : "incomingWitness") : t("candidateEvidence");
    evidenceText.textContent = JSON.stringify(source === "two_hop" ?
      {path: item.witness, texts: candidate.texts} : source === "property_metadata" ?
      {metadata: item.metadata, texts: candidate.texts} : source !== "bm25" ?
        {entity: item.witness.entity, statement: item.witness.statement, texts: candidate.texts} :
      {texts: candidate.texts, usage: candidate.usage, witnessed_operations: item.witnessed_operations}, null, 2);
    evidence.append(evidenceSummary, evidenceText);
    if (candidate.texts_clipped) {
      const note = document.createElement("p");
      note.setAttribute("role", "note"); note.textContent = t("candidateTextsClipped"); article.append(note);
    }
    article.append(detail, evidence);
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
    if (item.selectable === true) {
      const use = document.createElement("button"); use.type = "button"; use.textContent = t(role === "entity" ? "useEntity" : "useProperty");
      use.addEventListener("click", () => selectCandidate(role, item));
      article.append(use);
    } else {
      const p = document.createElement("p"); p.textContent = t("notSelectable"); article.append(p);
    }
    if (role === "entity") for (const operation of item.witnessed_operations || []) {
      const use = document.createElement("button"); use.type = "button";
      use.textContent = `${t("useWitnessedOperation")}: ${operation.predicate} · ${t(operation.direction)}`;
      use.addEventListener("click", () => selectWitnessedOperation(item, operation));
      article.append(use);
    }
    return article;
  }
  $("entity-suggestion-list").replaceChildren(...entities.map(item => renderCandidate(item, "entity")));
  $("neighborhood-entity-suggestion-list").replaceChildren(...nearbyEntities.map(item => renderCandidate(item, "entity", "neighborhood_entity")));
  $("two-hop-suggestion-list").replaceChildren(...twoHop.map(item => renderCandidate(item, "entity", "two_hop")));
  $("suggestion-list").replaceChildren(...predicates.map(item => renderCandidate(item, "property")));
  $("metadata-suggestion-list").replaceChildren(...metadataPredicates.map(item => renderCandidate(item, "property", "property_metadata")));
  $("neighborhood-suggestion-list").replaceChildren(...neighbors.map(item => renderCandidate(item, "property", "neighborhood")));
  $("entity-suggestion-empty").hidden = entities.length > 0;
  $("neighborhood-entities-empty").hidden = nearbyEntities.length > 0;
  $("neighborhood-entities-clipped").hidden = !data.neighborhood_entities_clipped;
  $("two-hop-empty").hidden = twoHop.length > 0;
  $("two-hop-clipped").hidden = !data.two_hop_candidates_clipped;
  $("entity-candidates-clipped").hidden = !data.entity_candidates_clipped;
  $("predicate-candidates-clipped").hidden = !data.predicate_candidates_clipped;
  $("metadata-candidates-clipped").hidden = !data.property_metadata.clipped;
  $("suggestion-empty").hidden = predicates.length > 0;
  $("metadata-suggestion-empty").hidden = metadataPredicates.length > 0;
  $("neighborhood-empty").hidden = neighbors.length > 0;
  $("neighborhood-clipped").hidden = !data.neighborhood.clipped;
  $("suggestions").hidden = false;
}
function selectCandidate(role, item) {
  const candidate = item.candidate;
  const key = role === "entity" ? "entity" : "predicate";
  candidateOptions[key].set(candidate.iri, candidate.texts);
  translate();
  const select = $(role === "entity" ? "entity" : "predicate");
  select.value = candidate.iri;
  select.dispatchEvent(new Event("change"));
}
function selectWitnessedOperation(item, operation) {
  const candidate = item.candidate;
  candidateOptions.entity.set(candidate.iri, candidate.texts);
  candidateOptions.predicate.set(operation.predicate, candidateOptions.predicate.get(operation.predicate) || []);
  translate();
  for (const [id, value] of [["entity", candidate.iri], ["predicate", operation.predicate], ["direction", operation.direction]]) {
    const select = $(id); select.value = value; select.dispatchEvent(new Event("change"));
  }
  $("status").textContent = t("witnessedOperationSelected");
  $("preview").focus();
}
function operation(request) {
  const step = request ? request.template.steps[0] : null;
  const direction = step ? step.direction : $("direction").value;
  const entity = $("entity").selectedOptions[0]?.textContent || $("entity").value;
  const predicate = $("predicate").selectedOptions[0]?.textContent || $("predicate").value;
  return direction === "reverse" ? `${t("all")} ← ${predicate} — ${entity}` : `${entity} → ${predicate} → ${t("all")}`;
}
function translate() {
  document.documentElement.lang = $("language").value;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  if (session) {
    const entity = $("entity").value, predicate = $("predicate").value, direction = $("direction").value;
    const entities = [[t("name") + " — Q279724", session.entity], ...[...candidateOptions.entity]
      .filter(([iri]) => iri !== session.entity).map(([iri, texts]) => candidateOption(iri, texts))];
    const predicates = [...Object.entries(session.predicates).map(([code, iri]) => [t(code), iri]), ...[...candidateOptions.predicate]
      .filter(([iri]) => !Object.values(session.predicates).includes(iri)).map(([iri, texts]) => candidateOption(iri, texts))];
    $("entity").replaceChildren(new Option(t("choose"), ""), ...entities.map(([label, iri]) => new Option(label, iri)));
    $("predicate").replaceChildren(new Option(t("choose"), ""), ...predicates.map(([label, iri]) => new Option(label, iri)));
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
    json("rust-preview", data.resolved.preview);
    json("sources", {graphs: data.sources, shape_guidance: data.provenance.shape_guidance_context});
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
    json("evidence", {snapshot_id: result.snapshot_id, graph: result.scope, triples: result.evidence,
      sources: data.sources, shape_guidance: data.provenance.shape_guidance_context});
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
