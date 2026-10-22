"use strict";
const $ = id => document.getElementById(id);
const prefix = "/api/nl-ask-v2/";
const credential = location.hash.slice(1);
history.replaceState(null, "", location.pathname);
let tab, session, proposal, approval, epoch = 0, timer;
const showJSON = (id, value) => { $(id).textContent = JSON.stringify(value, null, 2); };

async function api(route, body, keepalive = false) {
  const response = await fetch(route, { method: "POST", headers: {
    "Content-Type": "application/json", Authorization: "Bearer " + credential,
    "X-Verity-Tab": tab || ""
  }, body: JSON.stringify(body), cache: "no-store", keepalive,
  signal: keepalive ? undefined : AbortSignal.timeout(50000) });
  if (!response.ok) throw new Error("Review unavailable or stale. Edit/clarify, or reload the private session URL. No answer is asserted.");
  return response.json();
}
function invalidate(message = "", notify = true) {
  epoch++;
  approval = proposal = undefined;
  clearTimeout(timer);
  $("approve").disabled = true;
  $("clarification").hidden = $("review").hidden = $("choose").hidden = $("results").hidden = true;
  $("status").textContent = message;
  if (notify && tab) api(prefix + "cancel", {}, true).catch(() => {});
}
function fail(error) { invalidate(error.message); }

$("ask").addEventListener("click", async () => {
  invalidate("Retrieving authorized vocabulary. No model is loading.", false);
  const generation = epoch;
  try {
    const data = await api(prefix + "question", { question: $("question").value, language: $("language").value });
    if (generation !== epoch) return;
    if (data.status === "model_needs_clarification") {
      $("clarification-candidates").replaceChildren();
      for (const candidate of data.packet.entities.candidates) {
        const item = document.createElement("li");
        item.textContent = `${candidate.texts.map(t => t.value.text).join(" / ")} | ${candidate.iri} | ${candidate.graph}`;
        $("clarification-candidates").append(item);
      }
      $("clarification").hidden = false;
    }
    if (data.status !== "choose_exact_start") {
      $("status").textContent = data.message || `${data.status}: ${data.explanation} (unverified synthetic fixture; no execution)`;
      return;
    }
    proposal = data;
    showJSON("packet", data.packet);
    $("draft").textContent = data.raw_draft;
    $("start").replaceChildren(new Option("Choose an exact original candidate…", ""));
    for (const row of data.table.entities) {
      const candidate = data.packet.entities.candidates[row.id - 1];
      const labels = candidate.texts.map(t => t.value.text).join(" / ");
      $("start").add(new Option(`${labels || "No published label"} | ${row.iri} | ${candidate.graph}`, row.id));
    }
    $("choose").hidden = false;
    $("status").textContent = "Saved-draft demo — no live inference. Select the exact original entity before a new preview.";
  } catch (error) { if (generation === epoch) fail(error); }
});

$("preview").addEventListener("click", async () => {
  if (!proposal || !$("start").value) { $("status").textContent = "Choose one exact original candidate."; return; }
  const generation = ++epoch;
  approval = undefined;
  $("approve").disabled = true;
  $("review").hidden = true;
  $("status").textContent = "Rust is independently resolving and compiling the untrusted draft; no answer query runs.";
  try {
    const data = await api(prefix + "preview", { proposal_token: proposal.proposal_token, start: Number($("start").value) });
    if (generation !== epoch) return;
    if (data.status !== "awaiting_confirmation") throw new Error("This draft cannot be executed. Edit or clarify.");
    approval = data;
    $("original").textContent = data.provenance.original_question;
    $("explanation").textContent = data.resolved.display_rationale;
    $("rust-summary").replaceChildren();
    for (const line of data.resolved.preview.summary) {
      const item = document.createElement("li"); item.textContent = line;
      $("rust-summary").append(item);
    }
    showJSON("rust-preview", data.resolved.preview);
    const request = data.resolved.request, step = request.template.steps[0];
    const fields = {
      "Starting entity": request.template.start,
      "Original predicate": step.predicate,
      "Direction": step.direction === "forward" ?
        "Outgoing: start → predicate → returned value" : "Incoming: returned value → predicate → start",
      "Graph": step.graph, "Snapshot": request.snapshot_id,
      "Authorized plan scope": request.scope.join("\n"),
      "Return": "Distinct terminal RDF values (?step1)",
      "Packet-local numeric identities": `entity ${$("start").value}; predicate ${JSON.parse(proposal.raw_draft).predicate}; graph ${JSON.parse(proposal.raw_draft).graph}`
    };
    $("plan-fields").replaceChildren();
    for (const [label, value] of Object.entries(fields)) {
      const term = document.createElement("dt"), description = document.createElement("dd");
      term.textContent = label; description.textContent = value;
      $("plan-fields").append(term, description);
    }
    showJSON("sources", data.sources);
    $("expiry").textContent = `This separate, single-use approval expires within ${Math.floor(data.review_seconds)} seconds.`;
    $("choose").hidden = true;
    $("review").hidden = false;
    $("approve").disabled = false;
    $("status").textContent = "Review direction, entity, predicate, graph, projection, snapshot and all limits before approving.";
    clearTimeout(timer);
    timer = setTimeout(() => invalidate("Review expired. Request a new independent preview."), data.review_seconds * 1000);
  } catch (error) { if (generation === epoch) fail(error); }
});

$("approve").addEventListener("click", async () => {
  if (!approval) return;
  const token = approval.token;
  invalidate("Running your separately approved exact read-only plan…", false);
  const generation = epoch;
  try {
    const data = await api(prefix + "confirm", { token, decision: "approve" });
    if (generation !== epoch) return;
    const result = data.outcome.result;
    $("result-status").textContent = (data.answers.length ? `${data.answers.length} RDF values. ` :
      "No rows under this formal plan and snapshot; this does not establish real-world nonexistence. ") +
      `Rows ${result.complete_within_scope ? "complete" : "truncated"}; evidence ${result.evidence_complete_for_returned_rows ? "complete" : "truncated"}. ` +
      "Interpretation correctness is unassessed. Real-world truth is unverified.";
    $("answers").replaceChildren();
    for (const answer of data.answers) {
      const heading = document.createElement("h3");
      const labels = answer.observed_labels.map(t => t.value.text).join(" / ");
      heading.textContent = labels ? `${labels} — ${answer.value.value}` : answer.value.value;
      const element = document.createElement("pre");
      const term = value => value.kind === "iri" ? value.value : JSON.stringify(value);
      element.textContent = answer.source_triples.map(triple =>
        `${term(triple.subject)} → ${term(triple.predicate)} → ${term(triple.object)}\nGraph: ${term(triple.source_graph)}\nSnapshot: ${result.snapshot_id}`
      ).join("\n\n") || "Original source witness was clipped. Inspect the incomplete evidence receipt.";
      const metadata = document.createElement("pre");
      metadata.textContent = JSON.stringify({value: answer.value, evidence_complete: answer.evidence_complete, sources: data.sources}, null, 2);
      $("answers").append(heading, element, metadata);
    }
    showJSON("receipt", data);
    $("results").hidden = false;
    $("status").textContent = "Executed only after your separate approval. Saved proposal and operator confirmation remain separately recorded below.";
  } catch (error) { if (generation === epoch) fail(error); }
});
for (const id of ["question", "language", "start", "find-query"]) {
  $(id).addEventListener(id === "question" || id === "find-query" ? "input" : "change", () => {
    if (id === "start" && proposal) {
      epoch++; approval = undefined; clearTimeout(timer);
      $("approve").disabled = true; $("review").hidden = true;
      api(prefix + "unreview", {}).catch(() => {});
    } else invalidate("Changed input. Ask again for a new interpretation.");
  });
}
for (const id of ["cancel", "edit"]) $(id).addEventListener("click", () => {
  invalidate(id === "edit" ? "Edit your question and ask again." : "Cancelled without further execution.");
  $("question").focus();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") invalidate("Cancelled with Escape.");
  if (event.key === "Enter") event.preventDefault(); // Enter never redeems an approval.
});
document.addEventListener("visibilitychange", () => { if (document.hidden) invalidate("Tab hidden; review cancelled."); });
window.addEventListener("pagehide", () => invalidate("Page left; review cancelled."));
window.addEventListener("popstate", () => invalidate("Navigation cancelled the review."));
$("find").addEventListener("click", async () => {
  invalidate("Finding original resources; no question interpretation.", false);
  const generation = epoch;
  try {
    const result = await api("/api/find", { query: $("find-query").value, scope: session.scope, role: "entity", limit: 10 });
    if (generation !== epoch) return;
    showJSON("find-results", result);
    $("status").textContent = "Find expert results. No Ask execution occurred.";
  } catch (error) { if (generation === epoch) fail(error); }
});

(async () => {
  try {
    session = await api("/api/session", {}); tab = session.tab;
    showJSON("scope", { scope: session.scope, snapshot_id: session.snapshot_id, receipt: session.receipt });
    $("runtime").textContent = session.runtime === "saved_draft_demo" ?
      "SAVED-DRAFT DEMO — no live natural-language understanding or inference. " + session.runtime_message : session.runtime_message;
    $("ask").disabled = false;
    $("demo").hidden = session.runtime !== "saved_draft_demo";
    for (const item of session.demo_cases) {
      const button = document.createElement("button"); button.type = "button";
      button.textContent = `[${item.language}] ${item.question}`;
      button.addEventListener("click", () => {
        invalidate(); $("question").value = item.question; $("language").value = item.language;
      });
      $("demo-cases").append(button);
    }
    setTimeout(() => { invalidate("Session expired. Reopen the private URL from the terminal."); $("ask").disabled = true; }, session.session_seconds * 1000);
  } catch (error) { fail(error); }
})();
