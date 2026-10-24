# Assisted Ask v1 validation

Decision remains **INCONCLUSIVE_REVISE**. No model, weights, consumed trial or
sealed holdout is accessed. Human comprehension remains unmeasured.

The implementation reuses the unchanged Rust engine and exact-approval bridge.
The focused suite uses the real Rust binary and loopback HTTP server, with eight
headless Chrome sessions: bilingual journeys/security, review expiry, empty
results, row clipping, evidence clipping, hostile source labels, timeout and
execution failure. Timeout/failure exceptions are injected at the execution
boundary; they are failure-path checks, not observed Rust timeouts. Empty and
hostile data and reduced policies exist only in isolated temporary fixtures.
Production has no source/snapshot override.

Focused run 4 passed **10/10 Python tests**, including all eight Chrome sessions.
It checks original website IRIs, en/nb/nn names, RDF datatypes, source witnesses,
manual origin, provenance/license, filtered/count/SPARQL text remaining unverified,
no execution before approval, missing/expired/replayed/edited/cancelled approvals,
new tabs, unknown/numeric entities, unauthorized predicates, direction/graph/scope
substitution, changed snapshot/source/policy/config/scope/binary, old routes,
Host/Origin/credential/tab checks, disconnect preflight, and consumed failures.
Keyboard preview and deliberate Space approval, Escape cancellation, and 390px
responsive layout are browser-checked. No synthetic human review is claimed.

Recorded development failures:

1. Focused run 1: all ten tests could not bind loopback inside the sandbox.
   Reran with host execution for local server/Chrome; no application change.
2. Focused run 2: the new isolated fixture retained the original config snapshot
   ID, a source-audit key was wrong, and the keyboard driver omitted Enter text.
   Corrected fixture metadata, audit lookup and actual key dispatch.
3. Focused run 3: the source assertion compared serialized N-Triples with Turtle
   bytes instead of RDF triples; corrected with the existing RDF parser. Keyboard
   testing also exposed that focus stayed on Preview: a second Enter rebuilt the
   preview. Review now focuses its accessible heading, preserving a deliberate
   separate keyboard approval action. No validator or approval check was relaxed.
4. Focused run 4: all checks passed. Earlier logs remain retained separately.

Full model-free pipeline and preservation receipts are recorded below after the
isolated validation run. Launch and exact scope: [Assisted Ask v1](../assisted-ask-v1.md).
