"use strict";
const $ = id => document.getElementById(id);
const prefix = "/api/assisted-ask-v1/";
const credential = location.hash.slice(1);
history.replaceState(null, "", location.pathname);
let tab, session, approval, epoch = 0, timer;
const json = (id, value) => { $(id).textContent = JSON.stringify(value, null, 2); };
const words = {
  en: {
    title: "Select a graph operation", intro: "Choose an entity and relationship. These choices define the query. No language model or question interpretation is used.",
    language: "Interface language", entity: "Entity", relationship: "Relationship", choose: "Choose…", name: "University of Tromsø", P856: "Official websites", P1448: "Official names", all: "All stored values",
    contract: "Forward only: entity → relationship → all distinct stored values. No filtering, counting, reverse relationships, joins, writes or raw SPARQL.",
    optional: "Optional original question — unverified user intent", question: "Original question (not interpreted)",
    warning: "This text never selects or changes the operation. Requests such as ‘only English names’, counting or raw SPARQL are unsupported. You may separately select all unfiltered values; that result is not verified as an answer to this question.",
    preview: "Preview selected operation separately", review: "Review before approval", relation: "The displayed relationship is exactly what will be queried, in the forward direction. Approval executes this operation only.",
    unverified: "Original question: unverified and not interpreted. The result answers only the manually selected graph operation.",
    rust: "Authoritative Rust query preview", technical: "Exact plan, authorization, snapshot, source and limits", approve: "Approve this exact operation and run once", cancel: "Cancel",
    results: "Results of the selected operation", evidence: "Original source triples, graph, snapshot, provenance, licenses and receipt", scope: "Authorized local scope and limitations",
    limits: "Only University of Tromsø (Q279724), official websites (P856) and official names (P1448), in the retained Wikidata development graph. Missing facts do not establish real-world absence. Source labels are untrusted. Human comprehension is unmeasured. This is not general natural-language understanding.",
    changed: "Choices or question changed. Request a new preview.", error: "Operation unavailable, stale or failed. No answer is asserted. Request a new preview or reopen the private terminal URL.",
    building: "Building the Rust preview; no answer query executes.", select: "Choose the entity and relationship first.", ready: "Inspect the operation, graph, snapshot and limits. Approval is a separate action.",
    expired: "Review expired. Request a new preview.", cancelled: "Cancelled. Pending approval invalidated.", running: "Running the separately approved read-only operation…", done: "Selected graph operation executed after separate approval.",
    noQuestion: "No original question supplied.", graph: "Authorized graph (forward)", lease: "Single-use approval expires within", seconds: "seconds.", values: "RDF values", empty: "No rows under this operation and snapshot. This does not establish real-world nonexistence.",
    rows: "Rows", evidenceLabel: "Evidence", complete: "complete", clipped: "clipped", truth: "Source correctness describes the retained snapshot; real-world truth is not established.",
    languageTag: "Language", datatype: "Datatype", iri: "Original IRI", literal: "Original RDF literal", missing: "Original source evidence clipped; inspect the receipt."
  },
  nb: {
    title: "Velg en grafoperasjon", intro: "Velg en entitet og relasjon. Valgene bestemmer spørringen. Ingen språkmodell eller tolkning av spørsmål brukes.",
    language: "Grensesnittspråk", entity: "Entitet", relationship: "Relasjon", choose: "Velg…", name: "Universitetet i Tromsø", P856: "Offisielle nettsteder", P1448: "Offisielle navn", all: "Alle lagrede verdier",
    contract: "Kun forover: entitet → relasjon → alle distinkte lagrede verdier. Ingen filtrering, telling, omvendte relasjoner, sammenkoblinger, skriving eller rå SPARQL.",
    optional: "Valgfritt originalspørsmål — ubekreftet brukerintensjon", question: "Originalspørsmål (tolkes ikke)",
    warning: "Teksten velger eller endrer aldri operasjonen. Ønsker som «bare engelske navn», telling eller rå SPARQL støttes ikke. Du kan velge alle ufiltrerte verdier som en egen handling; resultatet er ikke bekreftet som svar på spørsmålet.",
    preview: "Forhåndsvis valgt operasjon separat", review: "Se gjennom før godkjenning", relation: "Den viste relasjonen er nøyaktig det som spørres etter, i retning forover. Godkjenning kjører kun denne operasjonen.",
    unverified: "Originalspørsmål: ubekreftet og ikke tolket. Resultatet gjelder kun den manuelt valgte grafoperasjonen.",
    rust: "Autoritativ forhåndsvisning fra Rust", technical: "Eksakt plan, autorisasjon, øyeblikksbilde, kilde og grenser", approve: "Godkjenn denne eksakte operasjonen og kjør én gang", cancel: "Avbryt",
    results: "Resultater fra valgt operasjon", evidence: "Opprinnelige kildetripler, graf, øyeblikksbilde, proveniens, lisenser og kvittering", scope: "Autorisert lokalt omfang og begrensninger",
    limits: "Kun Universitetet i Tromsø (Q279724), offisielle nettsteder (P856) og offisielle navn (P1448), i den bevarte Wikidata-utviklingsgrafen. Manglende fakta beviser ikke fravær i virkeligheten. Kildeetiketter er ubekreftede. Menneskelig forståelse er ikke målt. Dette er ikke generell språkforståelse.",
    changed: "Valg eller spørsmål er endret. Be om en ny forhåndsvisning.", error: "Operasjonen er utilgjengelig, foreldet eller feilet. Intet svar hevdes. Be om ny forhåndsvisning eller åpne den private terminaladressen igjen.",
    building: "Bygger forhåndsvisningen i Rust; ingen svarspørring kjøres.", select: "Velg entitet og relasjon først.", ready: "Se gjennom operasjonen, grafen, øyeblikksbildet og grensene. Godkjenning er en egen handling.",
    expired: "Godkjenningen er utløpt. Be om ny forhåndsvisning.", cancelled: "Avbrutt. Ventende godkjenning er ugyldig.", running: "Kjører den separat godkjente, skrivebeskyttede operasjonen…", done: "Valgt grafoperasjon ble kjørt etter separat godkjenning.",
    noQuestion: "Intet originalspørsmål oppgitt.", graph: "Autorisert graf (forover)", lease: "Engangsgodkjenning utløper innen", seconds: "sekunder.", values: "RDF-verdier", empty: "Ingen rader for denne operasjonen og dette øyeblikksbildet. Dette beviser ikke fravær i virkeligheten.",
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
function operation(request) {
  const predicate = request ? request.template.steps[0].predicate : $("predicate").value;
  const code = Object.keys(session.predicates).find(k => session.predicates[k] === predicate);
  return `${t("name")} → ${t(code)} → ${t("all")}`;
}
function translate() {
  document.documentElement.lang = $("language").value;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  if (session) {
    const entity = $("entity").value, predicate = $("predicate").value;
    $("entity").replaceChildren(new Option(t("choose"), ""), new Option(t("name") + " — Q279724", session.entity));
    $("predicate").replaceChildren(new Option(t("choose"), ""), ...Object.entries(session.predicates).map(([code, iri]) => new Option(t(code), iri)));
    $("entity").value = entity; $("predicate").value = predicate;
  }
  selection();
}
function selection() {
  $("selected").textContent = session && $("entity").value && $("predicate").value ? operation() : t("select");
}
$("preview").addEventListener("click", async () => {
  invalidate(t("building"), false);
  if (!$("entity").value || !$("predicate").value) { $("status").textContent = t("select"); return; }
  const generation = epoch;
  try {
    const data = await api(prefix + "preview", {entity: $("entity").value, predicate: $("predicate").value,
      question: $("question").value, language: $("language").value});
    if (generation !== epoch) return;
    approval = data;
    const request = data.resolved.request;
    $("operation").textContent = operation(request);
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
for (const id of ["entity", "predicate", "language", "question"]) $(id).addEventListener(id === "question" ? "input" : "change", () => {
  invalidate(t("changed")); if (id === "language") translate(); else selection();
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
    translate(); $("entity").disabled = $("predicate").disabled = $("preview").disabled = false;
    setTimeout(() => { invalidate(t("expired")); $("preview").disabled = true; }, session.session_seconds * 1000);
  } catch { invalidate(t("error")); }
})();
