# Graph Verity

**Ask naturally. Verify against the graph.**

Graph Verity is an open-source, **local-first RDF search and question-answering engine** being designed to turn everyday questions into answers backed by actual knowledge-graph facts.

It combines **semantic search to understand what you're looking for** with **SPARQL to check what the graph really says**. For multi-part questions, a small local language model helps build a query plan—but a deterministic Rust compiler, not the model, produces the SPARQL.

> **Project status: design / early development.** The implementation plan is available; the APIs, CLI and model integrations shown below are **planned**, not yet runnable.

## Why build it?

A normal search engine matches words. A semantic search engine understands similar meanings. A **knowledge graph** also records *relationships*—who owns what, which contract belongs to which supplier, or which regulation applies to a service.

Imagine this (fictional) RDF dataset:

~~~text
Oslo Municipality ──owns──────────> North Energy AS
North Energy AS ────supplies───────> Public Agency
North Energy AS ────hasContract────> Contract A (active)
North Energy AS ────hasContract────> Contract B (active)
North Energy AS ────hasContract────> Contract C (active)
~~~

You ask in Norwegian or English:

> **Which municipality-owned companies have at least three active contracts?**

Finding words that resemble the question is not enough. The engine must identify the right concepts and directed relationships, traverse the RDF graph, **count distinct contracts**, and show why each result qualifies.

That's what Graph Verity aims to do—without requiring every user to write SPARQL.

## Two ways to use Graph Verity

| Mode | Ask | What it does |
| --- | --- | --- |
| **Find** | “Which company operates district heating in Oslo?” | Find likely entities, predicates, classes or SHACL shapes using multilingual semantic and keyword search. Optionally verify specific graph facts. |
| **Ask** | “Which municipality-owned suppliers have more than 50 employees and at least three active contracts?” | Interpret supported conditions, build a **typed query plan**, then execute exact, read-only SPARQL over the requested graph scope. |

**The distinction matters:** a vector search result is a *candidate*, not proof. And checking only the top 20 candidates does not establish that every matching entity has been found. For structured questions, the engine must run a formal graph query rather than limit the answer to vector hits.

## How it works

~~~mermaid
flowchart TD
    Q["Question in natural language"] --> R["Discover RDF entities and vocabulary<br/>EmbeddingGemma 2 + BM25"]
    R --> D{"Find or Ask?"}
    D -->|Find| C["Candidate ranking<br/>optional local reranker"]
    D -->|Ask| P["Small local semantic parser<br/>grammar-constrained JSON"]
    P --> T["Typed IR validation<br/>ontology + permissions + scope"]
    T --> S["Deterministic IR → SPARQL"]
    C --> V["Evidence / constraint checks"]
    S --> O[("Oxigraph · local RDF graph")]
    O --> V
    V --> A["Answer + RDF evidence + provenance"]
~~~

### Understanding the question

**EmbeddingGemma 2** maps questions and RDF descriptions into vectors for multilingual retrieval. **BM25** adds exact matches for organization names, identifiers and technical terms. The resulting catalog helps the engine find the *actual* predicates, entity IDs, classes and shapes in your RDF dataset.

For a complex question, a **small, quantized local generative model** (the first integration to evaluate is llama.cpp) receives a restricted selection of those ontology terms. It proposes structured JSON such as *traverse this relation, filter by this number, count those contracts*.

The generative model **never writes raw SPARQL**. Rust validates the proposed **typed intermediate representation (IR)**, checks permissions, types and edge directions, and compiles only supported operations into a read-only query.

Grammar-constrained JSON is not automatically correct: the model can still choose the wrong operator or relationship. Graph Verity will test its *semantic* accuracy against expert-authored RDF queries and explicitly reject questions it cannot interpret safely.

### Checking the answer

**Oxigraph** executes the compiled SPARQL over the selected graph scope. **SHACL** describes formal RDF constraints such as required fields, allowed value types and cardinalities. Graph Verity will **reuse an existing SHACL library where possible**, with a carefully tested subset as a fallback—not reimplement the whole SHACL standard.

Results should include their source graph, snapshot and supporting facts, and distinguish **verified**, **not conformant**, **unsupported**, **ambiguous**, and **unknown** cases. Missing RDF data does not automatically mean a claim is false.

## Guiding principles

- **Evidence before confidence.** Similarity is useful for finding things; RDF, SPARQL and applicable SHACL rules determine what is actually supported.
- **Local-first.** One Rust serving process, local models, local indexes and Oxigraph—no hosted inference API or separate database server.
- **Ontology-aware, not ontology-inventing.** The parser selects from real, authorized graph vocabulary instead of hallucinating predicate names.
- **Multilingual.** Initially focus on Norwegian questions over Norwegian- and English-labeled RDF graphs.
- **Safe by construction.** Strict query IR, read-only SPARQL, permission-aware graph scopes and resource limits.
- **Honest uncertainty.** Unsupported questions and incomplete graphs must not result in fabricated certainty.
- **Benchmark before complexity.** Prefer a strong text+keyword baseline, with optional reranking; postpone graph-neural-network research until it demonstrates measurable value.

## Planned technology stack

| Component | Technology | Why |
| --- | --- | --- |
| RDF and SPARQL | [Oxigraph](https://github.com/oxigraph/oxigraph) | Embedded RDF quad store and exact graph querying. |
| Semantic retrieval | **EmbeddingGemma 2** | Multilingual text embeddings, initially truncated to 256 dimensions. |
| Keyword retrieval | **BM25** | Exact identifiers and technical vocabulary. |
| Retrieval reranking | **Optional** local multilingual cross-encoder | Improve ranking *if* tests justify its CPU latency and RAM. |
| Semantic parsing | Small local generative model; evaluate [llama.cpp](https://github.com/ggml-org/llama.cpp) | Grammar-constrained proposals for typed JSON IR. |
| Query compiler | Rust typed-IR validator + compiler | Produce safe, scoped, read-only SPARQL—not free-form model-generated queries. |
| SHACL validation | Evaluate [Rudof](https://github.com/rudof-project/rudof) / Rust `shacl` first | Reuse established parsing/validation; test supported semantics against reference fixtures. |
| Serving runtime | **Rust**, two initial crates (`verity_core` and `verity_cli`) | Local, simple deployment without premature workspace fragmentation. |
| Text inference | [ONNX Runtime](https://onnxruntime.ai/) | Local CPU embedding inference, with model/runtime parity tests. |
| Graph ML | CompGCN / R-GCN **after MVP, if justified** | Optional research; not required for the first working product. |

**Scope for the first release:** a clearly defined RDF domain with approximately **10,000–100,000 searchable resources**, backed by a reproducible benchmark. Inference times and reranking gains are **not guaranteed** until tested on the target CPU.

## Planned developer experience

A future exploratory search could look like:

~~~http
POST /v1/search
Content-Type: application/json

{
  "question": "Who owns North Energy?",
  "k": 10
}
~~~

And a structured question could look like:

~~~http
POST /v1/ask
Content-Type: application/json

{
  "question": "Which suppliers have at least three active contracts with Oslo Municipality?"
}
~~~

The proposed responses include resolved RDF identifiers, the scope/snapshot queried, a readable plan summary, evidence and a clear completeness status **when a full formal query supports it**.

**These are illustrative API designs, not implemented endpoints.** Installation, CLI examples and a hands-on tutorial will follow the first executable milestone.

## Roadmap

- [ ] **Phase 0 — Benchmark and query contract:** choose a domain; build Norwegian questions and gold SPARQL; define typed IR and target hardware.
- [ ] **Phase 1 — RDF ingestion:** load Oxigraph, preserve provenance, discover predicates/classes/shapes and evaluate existing SHACL tooling.
- [ ] **Phase 2 — Hybrid search:** EmbeddingGemma 2, BM25, 256-dimensional vector index and `/v1/search`.
- [ ] **Phase 3 — Verification:** graph evidence, supported SHACL rules and differential conformance tests.
- [ ] **Phase 4 — Natural-language query planning:** local constrained semantic parser, ontology-aware context, validated IR, safe SPARQL and `/v1/ask`.
- [ ] **Phase 5 — Optional reranking:** benchmark a local cross-encoder on top 10/20/50 candidates; adopt it only if quality justifies cost.
- [ ] **Phase 6 — Pilot and hardening:** coherent versioned bundles, graph updates, offline packaging, limits, authorization and rollback.

**CompGCN/R-GCN are deliberately deferred to post-MVP research**, not scheduled as the fifth MVP phase.

Read the **[detailed implementation plan](docs/implementation-plan.md)** for architecture, query IR, data provenance, testing, phase gates, SHACL semantics and design trade-offs.

## Repository layout (planned)

~~~text
graph-verity/
├── README.md
├── LICENSE
├── docs/
│   └── implementation-plan.md
├── crates/
│   ├── verity_core/       # Engine library and internal modules
│   └── verity_cli/        # CLI and optional HTTP server
├── ml/                    # Offline model export and evaluation
├── tests/                 # RDF/SHACL fixtures and golden queries
└── configs/               # Planned runtime and evaluation configuration
~~~

The runtime code directories above are **planned**, not necessarily present in the repository yet.

## Correctness and limitations

Graph Verity does **not** claim that embedding similarity proves a fact, that local language models understand every question, or that RDF data is complete.

- **Find** offers ranked candidates; these results may omit valid matches.
- **Ask** aims to produce a complete result **within an explicitly defined graph scope and supported query semantics**, after validated query planning and SPARQL execution.
- **SHACL** checks constraints. Violating a rule may itself be a relevant answer to a data-quality question.
- **Unsupported or ambiguous questions** should produce explicit statuses, not plausible but unverified answers.

This is a core design principle—not just an implementation detail.

## Contributing

Graph Verity is at the design stage. Contributions are welcome around RDF example datasets, ontology vocabulary resolution, Norwegian↔English retrieval tests, local semantic parsing, SHACL conformance, safe SPARQL compilation, performance and developer experience.

Please read the [implementation plan](docs/implementation-plan.md) and open a GitHub issue to discuss substantial architecture changes before implementing them.

## License

See [LICENSE](LICENSE) for the repository license. Models, datasets and native runtime dependencies may have separate license terms.

---

**Graph Verity** · *Ask naturally. Verify against the graph.*
