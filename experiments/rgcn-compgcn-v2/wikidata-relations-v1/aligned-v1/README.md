# Direction and language alignment ablations, v1

This experiment revisits the preserved v3 R-GCN/CompGCN results without
changing their receipts, the frozen Wikidata graph, benchmark questions,
references, or splits. Read [`DIAGNOSIS.md`](DIAGNOSIS.md) for the code-based
failure analysis. New outputs live under this version directory.

## Fixed evidence

- Dataset export manifest: `8814fd107b756f2f6a38decf293b9cf918a22232901665057752a1b928cb9616`.
- Frozen bilingual benchmark has 236 questions in 56 source-lineage groups;
  its test split has 28 relevant questions. References are agent-authored,
  source-checked development evidence, not independent expert gold.
- The separate unseen-entity evaluation has 42 relevant test questions over
  16 entities. All 206 incident edges are excluded from message passing.
- Preserved v3 scores on the 28 relevant test questions: BM25 R@10 0.107,
  EmbeddingGemma 0.286, R-GCN 0.298, CompGCN 0.321, QV2 0.393. V3 concluded
  STOP for product adoption; no new score exists in this version yet.
- Five of 84 predicates account for 72.1% of the original 5,756 edges. The
  source snapshot contains predicate labels but no source-authored aliases or
  descriptions in the exported predicate vocabulary.

## Preprocessing and feature meaning

The deterministic directional export contains 2,157 entities, 5,756 original
edges, 5,756 derived reverse navigation rows, and 168 direction-specific
relation IDs. Every reverse row keeps the original source quad, uses a
different relation ID, and is marked as a navigation edge rather than an RDF
assertion. No `owl:inverseOf` axiom is added.

The vocabulary retains original predicate IRIs, graph scope, source labels,
label languages, and source quads. Bilingual direction templates use those
labels but are generated and marked `unreviewed`; they do not claim
source-authored definitions or silently assert inverse semantics. The pinned
EmbeddingGemma model is `google/embeddinggemma-2` at revision
`914f7f89142e33e77833254d9c9b90c3cef7303b`. Its existing upstream metadata
declares Apache-2.0; this experiment uses only locally present, hash-verified
assets and disables downloads.

## Ablations and scoring

| Variant | R-GCN and CompGCN change |
|---|---|
| A | Reuse the original v3 scores and predictions; no retraining. |
| B | Add distinct forward/reverse navigation relations; duplicate existing predicate text vectors for the two directions. |
| C | B plus separately encoded bilingual navigation templates. |
| D | C plus deterministic cap of 32 original source edges per predicate, retaining both directional rows for every sampled source edge, and source-backed wrong-direction contrastives. |
| E | D plus question-to-anchor and question-to-predicate/direction alignment losses, added to the same sampled question-ranking objective. |

B–E use seeds 117–119, the existing frozen question and entity vectors,
128-dimensional two-layer models, AdamW at 0.001, at most 100 epochs, and
patience 10. The four variants × two models × two partitions × three seeds
produce 48 sequential fits. R-GCN and CompGCN share features, sampled source
edges, negative candidates, splits, and budgets. E adds auxiliary losses by
design; that difference is registered as the alignment treatment.

Validation and test witness edges are absent from message passing, and each
derived inverse row is filtered with its original source edge. Unseen-entity
fits also remove every edge incident to the 16 held-out entities. The graph's
known triples are used only to keep them out of link-prediction negative
samples. Unobserved query distractors remain ranking contrasts, not RDF
false-fact claims.

Gold-free end-to-end outputs contain entity/predicate rankings and paths
generated from each model's top five predicted anchors and top ten predicted
predicate-direction pairs against the authorized source graph. Predicted
paths preserve ordered source quads and traversal direction. Oracle-assisted
structural results, which receive gold anchor and path relation directions,
are written separately. Shared-pool reranking only reorders the QV2 top-50
pool and cannot add candidates. Oracle results do not enter end-to-end scores.

The historical promotion criterion is unchanged: at least +0.10 absolute
Recall@10 over the strongest matched text baseline and positive paired lift
over QV2. Uncertainty will be reported descriptively because the primary test
has only 28 relevant questions. The four no-match cases and all source-witness
coverage measures remain visible.

## Commands and authorization gates

Run model-free preparation and the deterministic tests in the pinned research
environment:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python \
  tools/rgcn_compgcn_aligned_run_v1.py prepare --study-dir \
  experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1

PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python -m unittest \
  tools/test_rgcn_compgcn_alignment.py tools/test_rgcn_compgcn_directional.py
```

The next two commands do not load model assets or train. The preflight is a
fresh, read-only check bound to the preregistration:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python \
  tools/rgcn_compgcn_aligned_run_v1.py preflight \
  --manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/experiment-manifest-aligned-v1.json \
  --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/host-preflight-aligned-v1.json
```

Before running `features`, the owner must separately authorize the exact
preregistration SHA-256, dataset and benchmark hashes, directional export,
input and operation hashes, passing preflight receipt, and the pinned model
revision. The operation encodes 168 direction-aware predicate descriptions to
float32 `[168, 768]` vectors, CPU with 4 intra-op / 1 inter-op threads, local
verified assets only, no network downloads, 30-minute wall limit, 6 GiB sampled
process RSS ceiling, and at least 21,000,000,000 available bytes. No feature
inference has been run for this version.

After that operation, freeze its archive and manifest with:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python \
  tools/rgcn_compgcn_aligned_run_v1.py finalize \
  --preregistration experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/experiment-manifest-aligned-v1.json \
  --features experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/directional-relation-features.npz \
  --feature-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/directional-relation-features.manifest.json \
  --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/experiment-manifest-final-aligned-v1.json
```

Scored training requires a second authorization bound to the final run
manifest, feature manifest, and fresh training preflight. The measured
18-GiB admission/RSS ceiling, 12-GiB early warning, four-intra-op / one-inter-op
CPU configuration, and six-hour total limit are observational safeguards,
not OS-level isolation:

```sh
PYTHONPATH=tools /private/tmp/graph-verity-rgcn-env/bin/python \
  tools/rgcn_compgcn_aligned_run_v1.py train \
  --manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/experiment-manifest-final-aligned-v1.json \
  --features experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/directional-relation-features.npz \
  --feature-manifest experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/directional-relation-features.manifest.json \
  --preflight experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/host-preflight-training-aligned-v1.json \
  --authorization /approved/aligned-training-authorization.json \
  --out experiments/rgcn-compgcn-v2/wikidata-relations-v1/aligned-v1/training-run-aligned-v1
```

Both authorization files must be owner-provided, exact-run-bound records.
There are no synthetic approvals, model downloads, feature inference, or
scored fits in this commit.
