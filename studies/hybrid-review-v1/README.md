# Blinded selective-hybrid review — preregistered v1

This is the **reviewer-only research kit for #58**, separate from shipping Find.
BM25 and Confirmed Ask are unchanged. **Actual human reviewers: 0; owner reviews:
0; independent reviews: 0.** Recommendation: **defer**. Issue #58 must remain open
until genuine consenting reviewers assess the new cases. The
[product recommendation](../../reports/issue-58-human-review/README.md) is separate
from the engineering checks and historical AI judgments.

## Model-free demo

Python 3.11+ and a modern browser suffice; no model, Rust build or Python packages
are needed to review the retained ranks:

```sh
python3 tools/hybrid_review.py verify
python3 tools/hybrid_review.py serve --demo
```

Open the private loopback URL printed by the operator. Keep the URL/profile
private; stop with Ctrl-C. The server reuses #55's exact loopback binding, bounded
HTTP parser, Host/Origin/credential checks, expiring tab lease and restrictive
CSP. It serves only local assets and saved results. No free-form search, parser,
SPARQL, navigation to external IRIs, telemetry, Ask or model endpoint exists.
`--host ::1` is supported; public/LAN binds and tunnels are not supported.

The demo contains **exposed #50/#53 regression questions** and the original
historical-text BM25/selective ranks. Every demo session is a rehearsal, even if
a person clicks the controls. It cannot be relabeled as new independent evidence.
No saved result means no new-query result: an empty list is never substituted for
an unmeasured system.

1. Choose the frozen snapshot/graph, role, task and top-k. Operator `--scope` and
   `--roles` restrict the available authorized catalog; this kit has one public
   GEMET release graph and one snapshot. Scores and system labels stay hidden.
2. Inspect lists A/B, original graph-qualified IRIs, observed label predicates,
   literal language/datatype, source quads, predicate usage/direction and source
   license/revisions. Source text is inert, including markup/instructions. Lists
   are bounded to 1/5/10; only top 10 can be submitted. No candidate is selected
   automatically. The ordered witnesses cap at 20 and explicitly mark clipping.
3. Judge each unique candidate (shared identity across both lists). Check the
   authorized catalog for other relevant resources, inspect their sources and
   select missing relevant resources. Query source anchors are hidden during
   review: AI references are not relevance gold. Recall needs an exhaustive
   *retrievable* relevance set, not just the union of returned lists.
4. Assess exact-first correctness, false suggestions, scope, direction, ambiguity,
   helpful recovered paraphrases, preference and 1–5 confidence for both lists.
   No-match means no relevant retrievable resource in the authorized graph/role,
   not absence in the world. Any suggestion is a false candidate on a no-match
   case. If unable to assess, mark an exclusion; never guess gold.
5. Submit once. The server validates all judgments and atomically saves private
   data **before** revealing A/B. The seed is retained privately and determines
   order via HMAC over the task ID; do not expose it to reviewers. A submitted
   task cannot be rejudged in that session. New tabs revoke old leases. There is
   no server endpoint for editing, exporting or publishing participant data.

## New tasks, consent and frozen capture

[tasks.json](tasks.json) has 20 new English/Norwegian formulations, source quads,
AI authorship, null human reviewers and explicit target overlaps. The 8 paraphrase
formulations use 4 resource families outside #50/#53 target references; languages
share targets. Ambiguity/direction probes annotate exposed targets. No-match
anchors describe the source catalog, not proof of semantic absence. All targets
come from the same already-public CC BY 4.0/W3C GEMET/SKOS snapshot. No source,
license, graph, historical report or Ask holdout was changed or accessed.

This public, AI-authored source-audited set is **not a sealed holdout or new human
judgment**. Independent humans must adjudicate exhaustive relevance. The freeze
hashes protocol/tasks, exact export/index/source/model/runtime inputs and review
code before new inference or enrollment. No query ranks have been generated for
these 20 tasks in this PR. Changing a frozen file requires an explicit new
preregistration before collecting results; do not silently refresh a live study.

Optional offline capture reuses the original pinned historical-text resident
binary and saved document vectors, with the exact EmbeddingGemma 2 checkpoint and
runtime from #53. It never downloads weights. If the original binary/model/runtime
is unavailable, **defer capture**, keep using the demo, or preregister a separately
identified reproduction; a current SKOS-definition binary cannot stand in for
shipping historical-text BM25. Use the existing pinned embedding environment,
not normal CI. Paths below are operator-supplied local artifacts:

```sh
# Before ANY new model query or reviewer enrollment:
/path/to/pinned/python tools/hybrid_review.py prepare \
  --model-dir /path/to/pinned/embeddinggemma-2 \
  --session /path/to/original/bm25-46/retrieval_session \
  --hardware 'CPU, RAM, OS, scheduler, caches, power conditions; CPU-only 4/1 threads' \
  --out study-private/hybrid/capture-receipt.json
# Separate explicit inference opt-in, after recording that receipt:
/path/to/pinned/python tools/hybrid_review.py capture --allow-inference \
  --receipt study-private/hybrid/capture-receipt.json \
  --out study-private/hybrid/results.json
```

Capture validates upstream weight hashes, pinned package versions, exact lexical
binary and full export manifest, then reuses fixed document vectors. One cold
pass plus three resident passes retain paired query times, model load, first
cold query, checkpoint size and a conservative process-plus-lexical-child RSS
bound with a process-tree sampler. One cold observation is **not** a cold p95;
historical vector building is reused. Receipt checks precede new queries. Input
and output paths stay operator-side and cannot be supplied through the browser.
This optional inference path is not exercised by CI; CI never imports Torch.

Before a real session, explain: participation is voluntary; the participant may
skip a case, stop or withdraw; only structured ratings and a random anonymous ID
are retained locally; the study is exploratory; no answer or similarity verifies
facts. Obtain explicit consent, then start one session for one actual reviewer:

```sh
python3 tools/hybrid_review.py serve --results study-private/hybrid/results.json \
  --kind independent --consent --out study-private/hybrid/reviewer-01.json
# Use --kind owner for the operator/owner. Never count the owner as independent.
# A fresh output filename and seed are needed for each actual consenting person.
python3 tools/hybrid_review.py report --results study-private/hybrid/results.json \
  --out study-private/hybrid/report.json \
  study-private/hybrid/reviewer-01.json study-private/hybrid/reviewer-02.json
```

Random IDs represent real consenting people; software cannot attest their physical
identity or independence. The operator must not create multiple identities for
one person, use simulated responses or present AI ratings as human. Keep sessions,
seeds, runtime paths and reports in ignored `study-private/` with private file
permissions. No free text, names, email addresses or sensitive RDF is collected.
For withdrawal remove that person's local session and recompute the report. Share
only a separately reviewed aggregate, never raw forms or reviewer-linked ratings.
No public export is performed automatically.

## Reporting and promotion rule

[protocol.json](protocol.json) freezes the rubric, candidate universe, exact and
no-match policies, metrics and rule. Reports separate rehearsal/AI, owner and
independent IDs/counts. Repeated IDs fail. At least two independent consenting
reviewers must agree on a complete relevance set per case; disagreements remain
visible and are excluded from scored consensus, without majority voting or silent
adjudication. Rubric disagreements and missing/excluded cases remain explicit.

The report contains case-level paired identities, Recall@1/5/10, MRR@10,
exact-first preservation, no-match suggestion rates, language/family aggregates,
preferences, confidence, and false confidence (confidence >=4 with an irrelevant
top hit). Bootstrap intervals are fixed-seed **descriptive query-level** intervals;
shared targets/languages and a small convenience sample limit independence/power.
They are not population confidence bounds. Owner-only or AI evidence cannot pass
the human gate.

Defer while full independent consensus, both-language relevant/no-match coverage,
unresolved exact/scope/direction/ambiguity assessments,
or comparable new-query resource evidence is missing. With complete evidence,
continue BM25 if any gate fails: no exact-first regression, no no-match increase,
Recall@10 gain >=.05 or MRR@10 gain >=.03 with descriptive lower bound >0, positive
Recall@10 benefit in each language and MRR regression no worse than .02, warm p95
<=1 s and conservative RSS <=4 GiB. Passing only proposes a further opt-in trial.
The owner must separately authorize any user-facing opt-in feature, and separately
any default rollout. This tool never changes a product default.

## Verification

```sh
REQUIRE_FIND_BROWSER=1 python3 -m unittest discover -s tools -p test_hybrid_review.py -v
# Entire existing model-free pipeline, from a clean commit:
.venv/bin/python tools/verify_pre_llm.py
```

Model-free tests exercise frozen lineage/source integrity, blinded/reproducible
order, submission/reveal, stale sessions, graph/source/count canaries, inert HTML,
private atomic saves, recall/no-match/conflict arithmetic, owner/rehearsal
separation and a real keyboard/accessibility/browser walkthrough. Synthetic test
ratings are never enrollment or validation evidence. No additional dependency,
shipping ranking change, Ask integration or model download is introduced.
