# Issue #58 — product recommendation: defer

**Continue shipping BM25. Defer any user-facing hybrid trial pending genuine
human relevance review and owner approval.** This is an explicit product proposal,
separate from the [reviewer tool and preregistration](../../studies/hybrid-review-v1/README.md).
Issue #58 remains **open/blocked for actual participants**, not completed by this PR.

| Evidence | New #58 study |
|---|---|
| Prepared tasks | 20, 10 English / 10 Norwegian; AI-authored source anchors |
| Actual consenting human reviewers / judgments | 0 / 0 |
| Independent reviewers / owner reviewers | 0 / 0 |
| Reviewer IDs / disagreements | None / unmeasured |
| New-query inference / paired relevance metrics | 20 frozen queries captured / human relevance unmeasured |
| New-query selective warm p95 / conservative RSS | 110.34 ms / 1.947 GiB |
| Recommendation | `defer`; BM25 stays default |

The tool's saved-result demo replays exposed #50/#53 regressions, never new held-out
evidence. Historical text Recall@10 0.319 → 0.750, 61/61 exact first matches,
no-match returns 8/12 → 9/12 and the missed Norwegian `overfishing` paraphrase remain
historical AI-reference results. The SKOS-definition ablation's numeric screen,
79.36 ms warm p95 and corrected 2.813 GiB conservative RSS are also **historical**;
its text representation differs from shipping BM25. No old observation is credited
to the new study or to human usability. See the unchanged
[#53 report](../issue-53-selective-hybrid/README.md).

The new formulations are public and AI-authored. Paraphrase resource families are
separate from exposed target references; ambiguity/predicate target overlaps are
annotated, and the whole corpus was already public. Source anchors are not final
relevance gold. No-match means no relevant *retrievable* resource in the authorized
role/graph. Bilingual target sharing and small samples limit descriptive intervals.
There are no real reviewer IDs to publish, no human judgments to fabricate, and
no private Ask-holdout access. The graph and source license remain unchanged.

To propose a further opt-in trial, preregister the local hardware/runtime receipt,
explicitly capture new ranks with the pinned checkpoint/binary, recruit at least
two genuine consenting independent reviewers, collect complete source-backed
relevance including missed resources, and resolve/report disagreements without
hiding exclusions. Apply the frozen rule to case-level paired Recall@1/5/10,
MRR@10, both languages/families, exact-first, ambiguity, no-match suggestions,
preference and confidence/false-confidence. Require no exact/no-match regression,
meaningful retrieval benefit in both languages, <=1 s warm p95 and <=4 GiB
conservative RSS under declared comparable conditions. Retain cold startup and
resource limitations separately. Any failed gate means continue BM25; missing
human/resource evidence means defer.

Even a passing research result requires a **separate owner decision** on an
explicit user-facing opt-in proposal (scope, privacy, runtime, risks and rollback).
It grants neither default promotion nor an automatic connection to Confirmed Ask.
This PR supplies the research infrastructure and an honest pending decision;
engineering tests establish behavior, not human relevance or product readiness.

## Executed pinned capture (after preregistration)

The owner subsequently authorized the real offline run. The original checkpoint,
Python runtime and exact historical-text lexical binary were available and passed
the frozen checks. [Capture summary](capture-summary.json) and
[saved model-free results](saved-results.json.gz) record 20 unique queries: one
cold/warmup pass followed by three resident passes (60 paired warm samples).
The frozen study README describes the pre-capture state at its preregistration;
this section records the subsequent run without changing that freeze.

| Measurement | BM25 | Selective hybrid |
|---|---:|---:|
| Warm p50 | 0.95 ms | 75.05 ms |
| Warm p95 | 5.82 ms | 110.34 ms |
| Warm p99 | 11.55 ms | 161.20 ms |

Conservative process-plus-lexical-child RSS: **2,091,040,768 bytes (1.947 GiB)**;
sampled process-tree peak: 2,029,404,160 bytes; sampler errors: none. Hardware was
verified as Apple M1 Pro / 32 GiB, macOS 26.6.2, CPU-only 4/1 threads. Scheduler,
OS caches and concurrent desktop workload were uncontrolled. The checkpoint tree
occupied 1,525,808,822 bytes. Historical pinned document vectors were reused.

The single first-query observation is **6.994 s**, including model/index/vector
initialization from the capture timer; it excludes earlier interpreter/runtime
initialization and pinned asset verification. Model load is 6.347 s. This is not
a full process-start distribution or a cold p95. These resource observations pass
the declared warm/RSS screen, but do not satisfy any human-relevance gate.

**Human reviewers/judgments remain 0/0 until the owner supplies actual ratings.**
No AI assessment is attributed to the owner. Owner assessments will be separate
from independent human assessments, and any participant data stays local.

## AI-only analysis of the executed capture

[Reproducible anchor scores](ai-analysis.json) use the **unchanged preregistered
AI source anchors**, not human or exhaustive relevance judgments. The
[unblinded AI source audit](ai-source-audit.json) records all 20 cases and explicit
judgment limitations. Both were performed by Codex AI, which also authored the
queries. **Actual human assessments remain zero.** No owner or participant
confidence, preference or false-confidence score is imputed from these results.

| Frozen AI-anchor metric (16 relevant-reference cases) | BM25 | Selective |
|---|---:|---:|
| Recall@1 | 0.2813 | 0.2813 |
| Recall@5 | 0.4375 | 0.7813 |
| Recall@10 | 0.4375 | 0.8125 |
| MRR@10 | 0.3646 | 0.4583 |
| English Recall@10 (8 cases) | 0.3750 | 0.8750 |
| Norwegian Recall@10 (8 cases) | 0.5000 | 0.7500 |
| Exact-first probes preserved | 4/4 | 4/4 |
| No-match references receiving false candidates | 4/4 | 4/4 |

Six cases gain a previously missed top-ten source anchor: HR-01/02 earthquake
engineering, HR-05 natural risk analysis, HR-07/08 judicial system, and HR-13
both graph-qualified climate-zone identities. The lexical head remains first,
so those gains do not improve Recall@1. Both lists still miss HR-03 historic
centre, HR-06 Norwegian natural-risk wording and HR-20 Norwegian predicate
direction. Their anchor dense scores (0.704642, 0.693826, 0.687337) remain below
the frozen 0.73 threshold; no post-hoc cutoff or relevance-label change is made.

The English direction probe HR-19 ranks the opposite `broader` relation first
and the desired `narrower` relation second in both methods. Both identities of
the climate-zone ambiguity survive, but shared labels still need deliberate
selection. All four fictional no-match probes receive misleading suggestions.
Human confidence and usability remain unmeasured; the AI audit is not a proxy.

The audit also identifies reference weaknesses rather than hiding them: the
historic-centre definition does not explicitly say oldest neighbourhood, and
general `rate` may be over-credited by the physical-speed query's two-anchor
reference. Human adjudication may change the final relevance sets, with changes
and reasons reported separately. These exploratory numbers cannot establish an
independent effect or satisfy #58's human gate. **Recommendation remains defer;
continue shipping BM25.**

Reproduce without models or participant data:

```sh
.venv/bin/python tools/hybrid_review_ai.py --out artifacts/issue-58-ai-analysis.json
.venv/bin/python -m unittest discover -s tools -p test_hybrid_review_capture.py -v
```
