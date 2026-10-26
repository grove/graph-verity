"use strict";
const $ = id => document.getElementById(id);
const prefix = "/api/document-ask/";
const credential = location.hash.slice(1);
history.replaceState(null, "", location.pathname);

const reasonText = {
  generation_not_authorized: "Generation was not authorized. The retrieved passages are shown as sources only.",
  no_document_evidence: "No matching passage was retrieved in this scope. This does not prove the fact is absent.",
  conflicting_evidence: "The selected passages contain conflicting evidence.",
  ambiguous_question: "The question is ambiguous under the supported checks.",
  insufficient_source_support: "The retrieved passages do not provide sufficient support.",
  unsupported_answer_type: "This question needs a count or multi-document synthesis that this version does not support.",
  untrusted_instructions: "The selected evidence contains a targeted untrusted-instruction risk.",
  retrieval_coverage_incomplete: "Retrieval was clipped, so coverage is incomplete; a conflict may remain undetermined.",
  unable_to_establish_relevance: "The supported checks could not establish a direct question-to-passage match.",
  model_unavailable: "The local model registration is unavailable. No model was started.",
  invalid_model_response: "The saved model response or citation did not pass current source checks.",
  source_changed: "The source changed. Its passages and any saved answer were withheld.",
  source_unavailable: "The selected source could not be verified. No passage was returned."
};
const languageNames = {en: "English", nb: "Norwegian Bokmål", no: "Norwegian", nn: "Norwegian Nynorsk"};

async function api(action, body) {
  const response = await fetch(prefix + action, {
    method: "POST", headers: {"Content-Type": "application/json", Authorization: "Bearer " + credential},
    body: JSON.stringify(body), cache: "no-store", signal: AbortSignal.timeout(10000)
  });
  if (!response.ok) throw new Error("Local Ask is unavailable or the source bundle changed. Restart it with a valid operator bundle.");
  return response.json();
}

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function renderPassages(packet) {
  $("passages").replaceChildren();
  const passages = packet?.document_evidence || [];
  $("passage-section").hidden = passages.length === 0;
  for (const item of passages) {
    const details = node("details", undefined, "passage");
    const language = languageNames[item.language] || item.language;
    const title = node("summary", `${item.document_id} · ${language} (${item.language}) · ${item.citation_id}`);
    const text = node("p", item.text);
    const metadata = node("p", `Source: ${item.source}\nVersion: ${item.version_digest}\nOriginal bytes: ${item.span.start_byte}–${item.span.end_byte}\nLicense: ${item.license}\nRetrieval incomplete: ${packet.completeness?.documents_clipped ? "yes" : "no"}`);
    metadata.className = "citation";
    details.append(title, text, metadata);
    $("passages").append(details);
  }
}

function render(data, preparing) {
  const view = data.view || {};
  const packet = data.packet;
  $("answer").replaceChildren();
  $("answer").hidden = true;
  $("preparation").hidden = true;
  $("coverage").hidden = !packet;
  renderPassages(packet);
  if (!packet) {
    $("status").textContent = `${view.reason === "source_changed" ? "Source changed" : "Source unavailable"} — ${reasonText[view.reason] || "source verification failed"}`;
    return;
  }

  if (view.status === "no_evidence") {
    $("status").textContent = `No matching source passages — model not invoked. ${reasonText[view.reason] || "This does not establish absence."}`;
  }

  else if (data.execution === "native_authorized_cli" && view.status === "generated_checked_extractive" && view.model_invoked === true) {
    $("status").textContent = "Generated — original source quotation and citation verified";
    $("answer").append(node("h2", "Generated answer"), node("p", view.answer),
      node("p", `Citation: ${view.citation_id}`, "citation"),
      node("p", "Source and citation verified. Independent semantic correctness is not guaranteed."));
    $("answer").hidden = false;
  } else if (data.execution === "saved_replay" && view.status === "checked_saved_output_only" && view.model_invoked === false) {
    $("status").textContent = "Saved replay checked — model not invoked";
    $("answer").append(node("h2", "Checked saved answer"), node("p", view.answer),
      node("p", `Citation: ${view.citation_id}`, "citation"),
      node("p", "This is a checked saved output, not a native model run."));
    $("answer").hidden = false;
  } else if (data.execution === "synthetic_test_fixture" && view.status === "generated_checked_extractive") {
    $("status").textContent = "Synthetic generated-answer fixture — no native model run";
    $("answer").append(node("h2", "Synthetic checked answer"), node("p", view.answer),
      node("p", `Citation: ${view.citation_id}`, "citation"),
      node("p", "Test fixture only. No model was invoked."));
    $("answer").hidden = false;
  } else {
    const reason = view.reason || "generation_not_authorized";
    $("status").textContent = `Sources only — model not invoked. ${reasonText[reason] || reason}`;
  }

  const completeness = packet.completeness || {};
  $("coverage-content").textContent = JSON.stringify({
    document_scope: packet.document_scope,
    retriever: packet.retrieval?.kind,
    retrieved_passages: packet.document_evidence.length,
    documents_status: completeness.documents_status,
    documents_clipped: completeness.documents_clipped,
    grounding_risk: view.grounding_risk?.classification || "not_assessed",
    graph_execution: "not invoked",
    source_truth: packet.limits?.source_truth,
    retrieval_is_exhaustive: packet.limits?.retrieval_is_exhaustive,
    claim_entailment: packet.limits?.claim_entailment,
    semantic_entailment: view.semantic_entailment || "not assessed"
  }, null, 2);

  if (preparing) {
    const prep = data.preparation || {};
    $("preparation").hidden = false;
    $("prepare-message").textContent = prep.message ||
      (prep.status === "unavailable" ? `Preparation unavailable: ${reasonText[prep.reason] || prep.reason}` :
       "No inference request was prepared. The source-only result remains available.");
    $("prepare-content").textContent = JSON.stringify(prep, null, 2);
  }
}

async function submit(action) {
  const body = {question: $("question").value, language: $("language").value};
  $("ask").disabled = $("prepare").disabled = true;
  $("status").textContent = action === "ask" ?
    "Retrieving current source passages. No model will be invoked." :
    "Preparing the exact prospective request. No model will be invoked.";
  try {
    render(await api(action, body), action === "prepare");
  } catch (error) {
    $("status").textContent = error.message;
    $("answer").hidden = $("passage-section").hidden = $("coverage").hidden = $("preparation").hidden = true;
  } finally {
    $("ask").disabled = $("prepare").disabled = false;
  }
}

$("ask-form").addEventListener("submit", event => { event.preventDefault(); submit("ask"); });
$("prepare").addEventListener("click", () => submit("prepare"));
