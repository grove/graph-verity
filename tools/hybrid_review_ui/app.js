"use strict";
const $ = id => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem("hybrid-review-token");
history.replaceState(null, "", location.pathname);
if (token) sessionStorage.setItem("hybrid-review-token", token);
let session, pair, busy = false;
const checks = {
  exact_first: "Exact identifier/label first hit correct?",
  false_candidates: "Any convincing false-positive suggestions (especially no-match)?",
  graph_suitable: "Graph and scope suitable?",
  direction_suitable: "Source predicate/direction suitable for the task?",
  ambiguity_clear: "Ambiguous identities treated clearly without choosing automatically?",
  paraphrase_helpful: "Recovered paraphrases helpful?"
};
function node(tag, text) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; return element; }
function options(select, values) { select.replaceChildren(); for (const [value, text] of values) { const option = node("option", text); option.value = value; select.append(option); } }
async function api(route, body) {
  const response = await fetch(route, {method: "POST", headers: {"Content-Type": "application/json", Authorization: "Bearer " + token, "X-Verity-Tab": session?.tab || ""}, body: JSON.stringify(body), cache: "no-store", credentials: "omit", redirect: "error"});
  if (!response.ok) throw new Error("Review unavailable. Check judgments and selection, or restart the private session.");
  return response.json();
}
function fail(error) { $("status").textContent = error.message; $("review").hidden = true; pair = null; }
function refreshTasks() {
  options($("task"), session.tasks.filter(t => t.role === $("role").value).map(t => [t.id, t.language + " · " + t.query]));
  $("review").hidden = true; pair = null;
}
$("role").addEventListener("change", refreshTasks);
for (const id of ["task", "limit", "snapshot", "graph"]) $(id).addEventListener("change", () => { $("review").hidden = true; pair = null; });
$("selection").addEventListener("submit", async event => {
  event.preventDefault(); if (busy) return; busy = true; $("controls").disabled = true;
  $("review").hidden = true; pair = null;
  try {
    pair = await api("/api/pair", {task_id: $("task").value, snapshot_id: $("snapshot").value, scope: session.scope, role: $("role").value, limit: Number($("limit").value)});
    $("query").textContent = pair.task.query;
    $("context").textContent = pair.task.language + " · " + pair.task.role + " · " + pair.scope.join(", ") + " · " + pair.snapshot_id + " · Top " + pair.limit + "; longer rankings may exist. Exact identities before clipping: " + pair.exact_identities + (pair.ambiguous_exact ? ". Ambiguous: deliberate disambiguation required." : ".");
    $("lists").replaceChildren(); $("ratings").replaceChildren(); $("rubric").replaceChildren(); $("reveal").textContent = "";
    $("judgments").querySelectorAll("input,select,button").forEach(control => { control.disabled = false; });
    $("judgments").reset(); $("source-text").textContent = ""; $("submit").disabled = pair.limit !== 10;
    const union = new Map();
    for (const side of ["A", "B"]) {
      const list = node("section"); list.append(node("h3", "List " + side));
      if (!pair.lists[side].length) list.append(node("p", "No candidates returned."));
      pair.lists[side].forEach((hit, rank) => {
        union.set(JSON.stringify([hit.graph, hit.iri]), hit);
        const article = node("article"); article.append(node("h4", (rank + 1) + ". " + hit.iri));
        article.append(node("p", hit.graph));
        const evidence = node("details"); evidence.append(node("summary", "Observed labels, predicates, direction, source and license"));
        evidence.append(node("pre", JSON.stringify(hit, null, 2))); article.append(evidence); list.append(article);
      });
      $("lists").append(list);
      const rubric = node("fieldset"); rubric.append(node("legend", "List " + side + " assessment"));
      for (const [key, text] of Object.entries(checks)) {
        const label = node("label", text + " "); const select = node("select"); select.id = side + "-" + key; select.required = true;
        options(select, [["", "Choose"], ["yes", "Yes"], ["no", "No"], ["not_applicable", "Not applicable"], ["uncertain", "Uncertain"]]); label.append(select); rubric.append(label);
      }
      const label = node("label", "Confidence in this list's suitability (1 low, 5 high) "); const confidence = node("select"); confidence.id = side + "-confidence"; confidence.required = true;
      options(confidence, [["", "Choose"], ...[1,2,3,4,5].map(n => [String(n), String(n)])]); label.append(confidence); rubric.append(label); $("rubric").append(rubric);
    }
    for (const [key, hit] of union) {
      const label = node("label", hit.graph + " · " + hit.iri + " "); const select = node("select"); select.dataset.identity = key; select.required = true;
      options(select, [["", "Judge candidate"], ["relevant", "Relevant"], ["irrelevant", "Irrelevant"], ["uncertain", "Uncertain"]]); label.append(select); $("ratings").append(label);
    }
    options($("offlist"), pair.catalog.filter(d => !union.has(JSON.stringify([d.graph,d.iri]))).map(d => [JSON.stringify([d.graph,d.iri]), d.iri + " · " + d.texts.map(t => t.value.text).join(" / ")]));
    $("status").textContent = session.demo ? "Exposed #50/#53 regression demo · rehearsal only · no human validation" : "New preregistered study · judgments remain blinded until submission";
    $("review").hidden = false; $("query").focus();
  } catch (error) { fail(error); }
  finally { busy = false; $("controls").disabled = false; }
});
$("catalog-filter").addEventListener("input", () => {
  const query = $("catalog-filter").value.toLocaleLowerCase();
  for (const option of $("offlist").options) option.hidden = !option.textContent.toLocaleLowerCase().includes(query);
});
$("source").addEventListener("click", async () => {
  if (!pair) return;
  const values = [...$("offlist").selectedOptions]; if (!values.length) return;
  try { const [graph, iri] = JSON.parse(values[0].value); $("source-text").textContent = JSON.stringify(await api("/api/source", {graph, iri, task_id: pair.task.id}), null, 2); }
  catch (error) { fail(error); }
});
$("judgments").addEventListener("submit", async event => {
  event.preventDefault(); if (busy || !pair || pair.limit !== 10) return;
  busy = true; $("submit").disabled = true;
  try {
    const judgment = {
      ratings: [...$("ratings").querySelectorAll("select")].map(s => { const [graph,iri] = JSON.parse(s.dataset.identity); return {graph,iri,relevance:s.value}; }),
      offlist: [...$("offlist").selectedOptions].map(s => { const [graph,iri] = JSON.parse(s.value); return {graph,iri}; }),
      universe_reviewed: $("universe").checked, no_match: $("no-match").checked,
      checks: Object.fromEntries(["A","B"].map(side => [side, Object.fromEntries(Object.keys(checks).map(key => [key, $(side + "-" + key).value]))])),
      confidence: Object.fromEntries(["A","B"].map(side => [side, Number($(side + "-confidence").value)])),
      preference: $("preference").value, excluded: $("excluded").value || null
    };
    const result = await api("/api/judge", {task_id:pair.task.id, judgment});
    $("reveal").textContent = (result.saved ? "Saved privately. " : "Unsaved rehearsal. ") + JSON.stringify(result.labels);
    $("judgments").querySelectorAll("input,select,button").forEach(control => { control.disabled = true; });
  } catch (error) { $("status").textContent = error.message; $("submit").disabled = false; }
  finally { busy = false; }
});
(async () => {
  try {
    if (!token) throw new Error("Open the private session URL printed by the operator.");
    session = await api("/api/session", {});
    options($("snapshot"), [[session.snapshot_id,session.snapshot_id]]);
    options($("graph"), [[session.scope.join(","), session.scope.join(", ")]]);
    options($("role"), session.roles.filter(r => session.tasks.some(t => t.role === r)).map(r => [r,r]));
    refreshTasks(); $("controls").disabled = false; $("status").textContent = "Choose a task. " + (session.demo ? "Rehearsal only; exposed questions." : "Consenting reviewer " + session.reviewer);
  } catch (error) { fail(error); }
})();
