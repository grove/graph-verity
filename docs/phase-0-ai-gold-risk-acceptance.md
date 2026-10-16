# Phase 0 — owner-accepted AI gold, with explicit evidence limits

**Decision date:** 16 October 2026  
**Decision maker:** Graph Verity project owner (conversation authorization)  
**Decision:** Proceed with the *exploratory local semantic-parser development experiment* using existing AI-audited reference data **without commissioning a separate paid human gold review**.

This changes the **scope/exit condition for issue #5's benchmark-preparation engineering milestone**. It does **not** mean the original independent expert-review requirement has been performed, that `benchmarks/reviews.json` contains human decisions, or that Phase 0 feasibility has passed. The original review requirement is **explicitly waived for the exploratory spike**, not retroactively checked off. A publicly reported expert-reviewed accuracy claim still requires evidence the project does not have.

## Evidence retained

| Evidence | Observed or retained | What it cannot prove |
|---|---|---|
| Frozen Wikidata geography reference | 600 quads; 130 Norwegian candidates; 46 development cases (38 executable + 8 proposed abstentions) | Machine-authored gold and AI interpretation audit are not independent human ground truth |
| Additional Wikidata candidates | 76 development-template rephrasings; 8 same-ontology geography candidates | Neither represents an independent held-out test |
| AI semantic audit and owner acceptance | [Case-bound audit](../benchmarks/ai-semantic-audit.json), [corrections](issue-5-ai-semantic-review.md), [earlier owner sign-off](issue-5-owner-approval.md) | Agreement between AI-authored questions, plans, and AI review is potentially correlated |
| Separate real-data Schema.org transfer | [328 city records, 1,508 quads](../data/worldcities-transfer/README.md); 35 executable public transfer-development references + 5 proposed abstentions | This is a **different ontology** but its public development probes are not a hidden model-transfer evaluation |
| Private candidate holdout | [Checksum commitment](../configs/locked-holdout-commitment.json); 60 AI-authored Norwegian cases (50 executable + 10 proposed abstentions), outside the public repository | Not expert-reviewed; sequestering questions prevents direct exposure but does not make the authors' gold independent or establish statistical generalization |
| Clean-checkout CI | Rust tests, reference-SPARQL/RDFLib-vs-Oxigraph checks, source hashes and byte-identical graph rebuild | Compiler/reference agreement is not correct Norwegian interpretation, safe model abstention, or real-world truth |

The human-only `benchmarks/reviews.json` ledger intentionally contains zero approved cases. Existing `review --require-reviewed initial|final` checks **must continue to fail** until genuine case-by-case human records exist. Do not add fake human reviewers, rewrite a guard to label AI decisions as human approvals, or describe `review_candidate` as an untouched holdout.

## Revised issue #5 acceptance: engineering readiness, not audited-gold quality

For the owner's resource-constrained Phase 0 *development* milestone, the deliverables are:

- [x] Versioned, case-hash-bound questions/IR/reference SPARQL/results, scope, manifest and review guidance.
- [x] Norwegian development coverage and explicit ambiguity/unsupported outcomes.
- [x] Source-aware AI review, recorded corrections, and truthful review-provenance labeling.
- [x] Real second-source/second-ontology development fixture with separately reproducible oracle evaluation.
- [x] Externally held, checksum-committed candidate holdout; no questions or answer keys committed to public GitHub.
- [x] CI checks for read-only ingestion, scoped compiler, query evidence and reproducible reference bindings.
- [x] Owner explicitly accepted the remaining gold-quality and evaluation-independence risks for a **development-only** experiment.

**Waived / NOT completed:** 100–200 independently expert-reviewed cases; authenticated specialist adjudication; a scientifically independent, expert-validated final holdout. These are *limitations*, not satisfied checkboxes.

## Safe progression to issue #7

1. Work on **development/public transfer-development questions first**, with authorized vocabulary supplied to the model and every candidate IR revalidated by Rust. No free-form model-authored SPARQL.
2. Choose and pin the local runtime/model/tokenizer/grammar/prompt/hardware. Test the actual grammar, unsafe scopes, invalid data, wrong directions/operators and correct refusal.
3. **Freeze experimental numerical thresholds and configuration before opening the external holdout**. Keep the holdout ZIP outside project/public CI, prompts and coding-agent context, and do not leak its answers while optimizing.
4. Run the holdout only as a **one-shot, AI-reference comparison** after freezing. Report cases, denominators, wrong-but-valid plans, abstentions, per-family results, p50/p95/p99 and RSS. Clearly label results `AI-reference agreement — not expert-validated semantic accuracy`.
5. If the holdout is exposed to the coding agent or used in tuning, disclose contamination and do not reuse it for a final generalization claim.
6. Any authorization violation, arbitrary SPARQL execution, or scope/evidence leak is a **stop-and-fix** event, regardless of aggregate test accuracy.

## Decision boundary

**Permitted now:** exploratory local CPU semantic-parser engineering and honest AI-reference evaluation, with uncertainty disclosed.

**Not permitted to claim yet:** Phase 0 `GO` for reliable Norwegian question answering, independently verified semantic accuracy, effective prompt-injection resistance, a measured transfer gap, production readiness or real-world truth.

The numerical [Phase 0 thresholds](../configs/phase-0-gates.proposed.json) remain *proposed*, target model hardware is still unconfirmed, and the measured model metrics are unknown. Issue #8 must finalize the engineering budgets and report any waivers *before* testing the private candidate holdout. Issue #10's decision must distinguish `proceed with an experimental prototype` from `feasibility demonstrated`.

This waiver may be revisited if volunteer review becomes available later; it should not block an honest, clearly limited prototype.
