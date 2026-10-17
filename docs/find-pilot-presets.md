# Offline corpus presets for local Find (#67)

Start a retained public corpus with one explicit operator command. The launcher
composes the existing **frozen v1 Find interface**, Rust BM25 and graph evidence;
it loads no model. Search results remain candidates. This is an engineering
pilot, with **no documented successful human participant tasks and no
product-release GO**.

## Prepare once, then launch offline

Use Python **3.11+** (on macOS the system `python3` may be too old), rustup and the
repository's pinned Rust toolchain. Acquire the toolchain/dependencies once while
online; the launcher itself needs only Python's standard library:

```sh
rustup install
cargo fetch --locked
# Offline from here; build once:
cargo build --locked --offline -p verity_cli
# Choose one corpus (run from the repository root):
python3 tools/launch_find_pilot.py wikidata-development
python3 tools/launch_find_pilot.py worldcities-norway
python3 tools/launch_find_pilot.py gemet-4.2.3
```

Run one command at a time, open its private terminal URL in a modern browser, and
stop with **Ctrl-C** before choosing another corpus. Shutdown closes the socket,
removes the private temporary bundle and revokes the session. Restart gets a new
port/credential. Changing an input (including source witnesses or manifests)
revokes the running session; restore the pinned inputs and restart. No data
refresh, URL ingestion, remote request or dependency download occurs at launch.

An optional role subset is operator-only:
`python3 tools/launch_find_pilot.py gemet-4.2.3 --roles entity predicate`.
`--index /local/index.json` selects a persisted index that Rust fully rebuilds and
compares; it is not a trusted cache. `--binary /local/verity` selects the local
built CLI. `--port 0` (default) chooses an ephemeral port; `--host ::1` explicitly
selects IPv6. Only literal `127.0.0.1` and `::1` binds are accepted. There are no
RDF, format, policy, scope, config, authorization-override or UI-version options.
The separate [v2 prototype](local-find-ui-v2.md) has its own launcher/tests; these
presets never silently substitute it for the frozen participant UI.

## Exact identity and attribution

[The operator mapping](../tools/find_pilot_presets.json) pins the existing
manifests, snapshots, importers, discovery configuration, policies, scopes, and
retained source/license/revision witnesses by SHA-256. It verifies these bytes
before invoking the existing Rust validators, without adding an RDF parser.
The mapping is trusted operator code in the reviewed checkout, not a browser
upload or a signed attestation. Changing a source release needs a separately
reviewed mapping and source verification, not an automatic hash refresh.

| Preset | Authorized graph (importer-assigned) | Retained source and license |
| --- | --- | --- |
| `wikidata-development` | `urn:graph-verity:wikidata:development` | [Wikidata structured RDF](../data/wikidata/README.md), **CC0-1.0**; 600 quads in the full release, development entities Q20/Q585/Q26793/Q25804/Q25416 plus property metadata. Entity-specific revisions and original CC0 statements are in the hashed raw Turtle and manifest. |
| `worldcities-norway` | `urn:graph-verity:worldcities:transfer:NO` only | [GeoNames / datasets/world-cities](../data/worldcities-transfer/README.md), **CC BY 4.0**, upstream commit `73c9f54ab9f305168c76d0802db151e30a157b28`; Graph Verity filters and maps the CSV to Schema.org. Full release: 328 Nordic city records / 1,508 quads; this scope authorizes **42 Norwegian city records**, their regions/country and vocabulary. |
| `gemet-4.2.3` | `urn:graph-verity:gemet:4.2.3` | [EEA GEMET 4.2.3 / W3C SKOS Reference](../data/gemet/README.md): **CC BY 4.0 AND W3C Software and Document License (2023)**. Credit EEA; W3C, Alistair Miles, Sean Bechhofer and the Semantic Web Deployment Working Group. Release timestamp `2021-12-06T13:37:25.364764+00:00`; dated SKOS schema 18 August 2009. Fixed 2,200-concept selection, **2,215 resources / 10,839 quads**. Original export, download/license pages and W3C schema/license are retained and hashed. |

The WorldCities policy contains other country graphs, but the new fixed
[Norway scope](../configs/find-pilot-worldcities-norway-scope.json) never authorizes
them. Browser requests cannot widen it. The Wikidata transfer graph is likewise
excluded. GEMET and SKOS originally have unnamed source graphs; the importer
explicitly unions selected original statements into the named release graph.
None of these release graph names is an upstream named-graph assertion.

Startup prints the corpus, exact snapshot, authorized graph and source/license/
revision attribution locally. In the existing interface choose a graph/role,
search, deliberately **Select candidate**, then expand **Graph / source /
license** in graph evidence to inspect authorized provenance. The browser gets
only the authorized scope and source metadata, never operator paths or the
policy's wider graph menu. Original language tags and datatypes remain visible.
Wikidata and the GeoNames-derived mapping have different vocabularies; similar
names do not establish shared facts or identities.

## Three bounded walkthroughs

Set maximum candidates/edges to **50**. Keep the single preset graph checked.
Do not infer truth, completeness or a correct question interpretation from rank,
an exact label, a graph edge or an empty page.

1. **Wikidata capital:** choose Entity; search `Norge` or `Norway`, deliberately
   select `http://www.wikidata.org/entity/Q20`. In outgoing evidence inspect
   Q20 → `http://www.wikidata.org/prop/direct/P36` → Q585. Open P36 for predicate
   usage and Q585 for incoming evidence: the triple still has country as subject
   and Oslo as object. Predicate search `capital` / `hovedstad` uses the actual
   `wikibase:directClaim` mapping from property entity P36, not a fabricated label
   on the direct-property IRI. Q20 labels retain `nb`/`nn`/`en`; Oslo population
   retains `xsd:decimal`. Search `zzznomatchzzz` for unmatched candidates; no match
   does not establish real-world absence.
2. **GeoNames identity versus mapped edges:** choose Entity; search `Oslo`.
   This is **ambiguous exact**: both the city and importer-minted region share
   that name. Deliberately select the city **`https://sws.geonames.org/3143244/`**,
   not `urn:graph-verity:worldcities:admin:NO:Oslo`. Its original GeoNames numeric
   identity comes from the retained CSV; its `schema:City` classification and
   `https://schema.org/containedInPlace` edge are importer transformations:
   city → region → `urn:graph-verity:worldcities:country:NO`. Follow the region,
   inspect incoming city and outgoing country edges. `schema:identifier` is
   `"3143244"^^xsd:integer`; `schema:name` is untagged `xsd:string`, not Norwegian
   text invented by the interface. Search `zzznomatchzzz` for no-match. Neither
   this mapping nor Wikidata proves the other source's capital/population claims.
3. **GEMET SKOS direction:** choose Entity; search `animal life` or `dyreliv`;
   deliberately select `http://www.eionet.europa.eu/gemet/concept/10003` (original
   labels `@en` and `@no`, respectively). Outgoing source statements include
   `10003 → skos:broader → 867` and `10003 → skos:narrower → 5161`, where the SKOS
   namespace is `http://www.w3.org/2004/02/skos/core#`. Open 867 and inspect its
   incoming broader edge: the original subject is still 10003, not 867. This
   retained release also explicitly states `867 → skos:narrower → 10003`; that
   is a separate source triple, not inferred by reversing the first one. Choose
   Predicate and search `broader` then `narrower`, select the original SKOS IRI
   and inspect usage and original W3C text. No translated definitions or predicate
   labels are fabricated. Search `zzznomatchzzz` for no-match. These demos work
   on the pinned 2,215-resource bundle within the unchanged limits; the complete
   5,573-concept release's historical allocation blocker remains unchanged.

## Bounds, failures and tests

[The existing adapter's security contract](local-find-ui.md#architecture-and-trust-boundary)
remains in force: private session credential, exact Host/Origin, tab lease,
anti-CSRF checks, text-only source rendering, bounded evidence and responses.
The immutable copies, Rust snapshot/policy/scope/index validators, 16 MiB import
cap, 64 MiB conservative discovery allocation, 45-second subprocess deadline,
8 MiB responses and policy query caps are unchanged. No LAN/public serving,
analytics, external assets, network RDF loading or automatic Ask is added.
The existing optional Confirmed Ask remains a separate explicit interaction.

Missing/corrupt files fail with an operator-only diagnostic. Restore them from
the retained checkout; do not regenerate frozen study inputs. A failed Rust
validator reports its operation/exit status and an exact local diagnostic
command using the original operator inputs. Run that command to see its stderr
(e.g. allocation budget, authorization or stale-index error). Keep resource
blockers and input identities; do not trim records, widen scope or raise limits
for a demo. Browser failures always use the existing generic error, without
stderr, source canaries or local file paths.

```sh
# No extra Python packages; actual Rust CLI + HTTP, all three corpora:
python3 -m unittest discover -s tools -p test_launch_find_pilot.py -v
# Full reference pipeline needs the existing pinned tools/requirements.txt venv,
# Chrome/Chromium and Node >=22; run from a clean commit:
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

The normal unittest discovery in Linux CI includes the new preset tests. They
exercise actual subprocess launches, BM25 search/selection/directed source
witnesses, language/datatype metadata, integrity failures, scope widening,
stale indexes, role subsets, authentication, session invalidation and Ctrl-C
cleanup/restart. The HTTP test rejects non-loopback Python connections and DNS
hostnames; existing headless-browser tests check inert injection text and no
third-party page requests. Rust uses the existing embedded offline engine; no
new network client or executor is introduced. Frozen #57/#58 assets and
historical ranking/reports are unchanged.

| Environment | Actual coverage / boundary |
| --- | --- |
| macOS 26.6.2 / Apple Silicon (M1 Pro), Python 3.12.14, Rust 1.99.1 | Preset CLI + real loopback/Rust tests on this development host; use a Python 3.11+ executable, not an older system Python. Browser checks use separately installed Chrome and Node; no GUI/package installer is provided. |
| Ubuntu 24.04 x86-64, Python 3.12, pinned Rust, Node 22, runner Chrome | Model-free CI runs the complete reference/browser pipeline and preset integration tests; check the PR's actual CI result for this revision. |
| Other macOS/Linux versions, Windows, packaged desktop applications | Not tested by this change; no support claim. Historical local-model measurements do not demonstrate GUI or package support. |

A sensible next step for an interested pilot user: try one of these public
corpora, then write down one real question, the deliberately chosen IRI and
original directed evidence, including any mismatch or missing match. Discuss
that concrete task with the maintainer before planning a separately consented
user study or a new licensed data release. No participant success or release
readiness is inferred from this engineering demo.
