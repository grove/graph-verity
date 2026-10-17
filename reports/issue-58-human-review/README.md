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
| New-query inference / paired relevance metrics | Not run / unmeasured |
| New-query latency, RAM, cold startup | Unmeasured |
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
