use serde_json::{json, Value};
use verity_core::{
    catalog::Policy,
    compact::{decode_intent, CompactContext, Role},
    execution::{Execution, PlanOrigin, RdfTerm, Row},
    ir::{self, Compare, Direction, RDF_TYPE, XSD},
    parser::Proposal,
    Error, Snapshot,
};

const PUBLIC: &str = "https://example.org/public";
const PRIVATE: &str = "https://example.org/private";
const EX: &str = "https://example.org/";

fn fixture() -> (Snapshot, Policy, CompactContext) {
    let graph =
        Snapshot::from_bytes(include_bytes!("../../../tests/fixtures/smoke.trig"), "trig").unwrap();
    let policy = Policy {
        version: 1,
        graphs: vec![PUBLIC.into()],
        max_rows: 100,
        max_evidence: 100,
        timeout_ms: 5000,
    };
    let context = graph
        .compact_context(
            "Vis de oppgitte relasjonene",
            &[PUBLIC.into()],
            &policy,
            100,
        )
        .unwrap();
    (graph, policy, context)
}

fn index(context: &CompactContext, graph: &str, iri: &str, role: Role) -> u16 {
    context
        .references()
        .iter()
        .find(|r| r.graph == graph && r.iri == iri && r.role == role)
        .unwrap()
        .id
}

fn edge(context: &CompactContext, from: Value, predicate: &str, to: Value) -> Value {
    edge_in(context, PUBLIC, from, &format!("{EX}{predicate}"), to)
}

fn edge_in(
    context: &CompactContext,
    graph: &str,
    from: Value,
    predicate: &str,
    to: Value,
) -> Value {
    json!({"from":from, "predicate":index(context,graph,predicate,Role::Predicate),"direction":"forward","to":to})
}

fn entity(context: &CompactContext, name: &str) -> Value {
    json!({"entity":index(context,PUBLIC,&format!("{EX}{name}"),Role::Entity)})
}

fn candidate(edges: Vec<Value>) -> Value {
    json!({"version":2,"proposal":{"status":"candidate","edges":edges,"filters":[],
        "projection":[{"var":0}],"group_by":[],"having":[]}})
}

fn expand(graph: &Snapshot, context: &CompactContext, policy: &Policy, input: &Value) -> ir::Plan {
    let intent = decode_intent(&serde_json::to_vec(input).unwrap()).unwrap();
    let Proposal::Candidate { plan } = graph.expand_compact(context, &intent, policy).unwrap()
    else {
        panic!("expected candidate");
    };
    plan
}

fn execute(
    graph: &Snapshot,
    context: &CompactContext,
    policy: &Policy,
    input: &Value,
) -> Execution {
    let plan = expand(graph, context, policy, input);
    let result = graph.execute(&plan, policy, PlanOrigin::Fixture).unwrap();
    assert_eq!(result.status, "executed");
    assert!(result.complete_within_scope);
    assert!(result.evidence_complete_for_returned_rows);
    assert_eq!(result.interpretation_correctness, "not_assessed");
    assert_eq!(result.real_world_truth, "not_established");
    for statement in &result.evidence {
        let RdfTerm::Iri { value } = &statement.source_graph else {
            panic!("named evidence required")
        };
        assert!(plan.scope.contains(value));
    }
    result
}

fn iri(value: &str) -> RdfTerm {
    RdfTerm::Iri {
        value: value.into(),
    }
}
fn integer(value: &str) -> RdfTerm {
    RdfTerm::Literal {
        value: value.into(),
        datatype: format!("{XSD}integer"),
        language: None,
    }
}
fn row(key: &str, value: RdfTerm) -> Row {
    Row::from([(key.into(), value)])
}
fn code(error: Error) -> &'static str {
    match error {
        Error::Rejected { code, .. } => code,
        other => panic!("unexpected error: {other}"),
    }
}

#[test]
fn directions_two_hops_and_exact_v1_expansion() {
    let (g, p, c) = fixture();
    let direct = candidate(vec![edge(
        &c,
        entity(&c, "municipality"),
        "owns",
        json!({"var":0}),
    )]);
    let plan = expand(&g, &c, &p, &direct);
    assert_eq!(
        plan,
        ir::Plan {
            version: 1,
            snapshot_id: g.id().into(),
            scope: vec![PUBLIC.into()],
            patterns: vec![ir::Pattern {
                graph: PUBLIC.into(),
                from: ir::Node::Iri {
                    iri: format!("{EX}municipality")
                },
                predicate: format!("{EX}owns"),
                direction: Direction::Forward,
                to: ir::Node::Variable { name: "v0".into() }
            }],
            filters: vec![],
            projection: vec![ir::Projection::Variable { name: "v0".into() }],
            group_by: vec![],
            having: vec![],
            limit: 100,
        }
    );
    assert_eq!(
        execute(&g, &c, &p, &direct).bindings,
        vec![row("v0", iri(&format!("{EX}company")))]
    );
    let mut reverse = candidate(vec![edge(
        &c,
        entity(&c, "company"),
        "owns",
        json!({"var":0}),
    )]);
    reverse["proposal"]["edges"][0]["direction"] = json!("reverse");
    assert_eq!(
        execute(&g, &c, &p, &reverse).bindings,
        vec![row("v0", iri(&format!("{EX}municipality")))]
    );
    let mut two_hop = direct;
    two_hop["proposal"]["edges"]
        .as_array_mut()
        .unwrap()
        .push(edge(&c, json!({"var":0}), "contract", json!({"var":1})));
    two_hop["proposal"]["projection"] = json!([{"var":1}]);
    let result = execute(&g, &c, &p, &two_hop);
    assert_eq!(
        result.bindings,
        vec![
            row("v1", iri(&format!("{EX}c1"))),
            row("v1", iri(&format!("{EX}c2")))
        ]
    );
    assert_eq!(result.evidence.len(), 3);
    assert_eq!(expand(&g, &c, &p, &two_hop), expand(&g, &c, &p, &two_hop));
}

#[test]
fn typed_boundaries_counts_and_grouped_having() {
    let (g, p, c) = fixture();
    for (predicate, datatype, lexical, expected) in [
        (
            "employees",
            "integer",
            "51",
            vec![row("v0", iri(&format!("{EX}company")))],
        ),
        (
            "value",
            "decimal",
            "12.50",
            vec![row("v0", iri(&format!("{EX}c1")))],
        ),
        (
            "start",
            "date",
            "2025-01-01",
            vec![row("v0", iri(&format!("{EX}c2")))],
        ),
    ] {
        let mut input = candidate(vec![edge(
            &c,
            json!({"var":0}),
            predicate,
            json!({"var":1}),
        )]);
        input["proposal"]["filters"] =
            json!([{"var":1,"op":"ge","datatype":datatype,"lexical":lexical}]);
        let result = execute(&g, &c, &p, &input);
        assert_eq!(result.bindings, expected);
        assert!(!result.evidence.is_empty());
        assert_eq!(result.plan.filters[0].op, Compare::Ge);
        input["proposal"]["filters"][0]["op"] = json!("gt");
        assert!(execute(&g, &c, &p, &input).bindings.is_empty());
    }
    let mut count = candidate(vec![edge(
        &c,
        json!({"var":0}),
        "contract",
        json!({"var":1}),
    )]);
    count["proposal"]["projection"] = json!([{"count_distinct":1}]);
    assert_eq!(
        execute(&g, &c, &p, &count).bindings,
        vec![row("c0", integer("2"))]
    );
    count["proposal"]["projection"] = json!([{"var":0},{"count_distinct":1}]);
    count["proposal"]["group_by"] = json!([0]);
    count["proposal"]["having"] = json!([{"count":1,"op":"ge","value":2}]);
    let result = execute(&g, &c, &p, &count);
    assert_eq!(
        result.bindings,
        vec![Row::from([
            ("v0".into(), iri(&format!("{EX}company"))),
            ("c1".into(), integer("2"))
        ])]
    );
    assert_eq!(result.evidence.len(), 2);
    count["proposal"]["having"][0]["op"] = json!("gt");
    assert!(execute(&g, &c, &p, &count).bindings.is_empty());
}

#[test]
fn rejects_bad_bindings_types_indexes_and_aggregation_with_stable_codes() {
    let (g, p, c) = fixture();
    let base = candidate(vec![edge(
        &c,
        json!({"var":0}),
        "employees",
        json!({"var":1}),
    )]);
    let mutations = [
        (
            "/proposal/edges/0/predicate",
            json!(65535),
            "compact_reference",
        ),
        (
            "/proposal/edges/0/predicate",
            json!(index(&c, PUBLIC, &format!("{EX}company"), Role::Entity)),
            "compact_reference",
        ),
        (
            "/proposal/edges/0/from",
            json!({"entity":65535}),
            "compact_reference",
        ),
        ("/proposal/edges/0/to", entity(&c, "company"), "datatype"),
        (
            "/proposal/edges/0/to",
            json!({"class":index(&c,PUBLIC,&format!("{EX}Company"),Role::Class)}),
            "class",
        ),
        ("/proposal/edges/0/from", json!({"var":12}), "complexity"),
        ("/proposal/projection", json!([{"var":2}]), "projection"),
        (
            "/proposal/projection",
            json!([{"var":0},{"var":0}]),
            "projection",
        ),
        (
            "/proposal/filters",
            json!([{"var":2,"op":"gt","datatype":"integer","lexical":"1"}]),
            "variable",
        ),
        (
            "/proposal/filters",
            json!([{"var":1,"op":"gt","datatype":"date","lexical":"2025-01-01"}]),
            "datatype",
        ),
        (
            "/proposal/filters",
            json!([{"var":1,"op":"ge","datatype":"integer","lexical":"NaN"}]),
            "datatype",
        ),
        (
            "/proposal/filters",
            json!([{"var":1,"op":"eq","datatype":"integer","lexical":"1 OR true"}]),
            "datatype",
        ),
        ("/proposal/group_by", json!([0]), "aggregation"),
        (
            "/proposal/having",
            json!([{"count":0,"op":"ge","value":1}]),
            "aggregation",
        ),
        ("/proposal/edges", json!([]), "complexity"),
        ("/proposal/projection", json!([]), "complexity"),
    ];
    for (path, value, expected) in mutations {
        let mut input = base.clone();
        *input.pointer_mut(path).unwrap() = value;
        let intent = decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap();
        assert_eq!(
            code(g.expand_compact(&c, &intent, &p).unwrap_err()),
            expected,
            "{path}: {input}"
        );
    }
    let mut duplicate = base.clone();
    duplicate["proposal"]["edges"] =
        json!([base["proposal"]["edges"][0], base["proposal"]["edges"][0]]);
    let intent = decode_intent(&serde_json::to_vec(&duplicate).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&c, &intent, &p).unwrap_err()),
        "compact_duplicate"
    );
    let mut disconnected = base.clone();
    disconnected["proposal"]["edges"]
        .as_array_mut()
        .unwrap()
        .push(edge(&c, json!({"var":2}), "contract", json!({"var":3})));
    let intent = decode_intent(&serde_json::to_vec(&disconnected).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&c, &intent, &p).unwrap_err()),
        "complexity"
    );
    let mut too_many = base.clone();
    too_many["proposal"]["edges"] = json!(vec![base["proposal"]["edges"][0].clone(); 9]);
    let intent = decode_intent(&serde_json::to_vec(&too_many).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&c, &intent, &p).unwrap_err()),
        "complexity"
    );
}

#[test]
fn strict_decode_rejects_injection_missing_duplicate_and_extra_fields() {
    let (_, _, c) = fixture();
    let base = candidate(vec![edge(
        &c,
        json!({"var":0}),
        "employees",
        json!({"var":1}),
    )]);
    for (path, value) in [
        ("/proposal/edges/0/direction", json!("undirected")),
        (
            "/proposal/edges/0/from",
            json!({"iri":"https://evil.invalid/"}),
        ),
        ("/proposal/edges/0/from", json!({"var":0,"entity":1})),
        ("/proposal/edges/0/from", json!({"var":-1})),
        ("/proposal/projection", json!([{"sum":1}])),
        ("/proposal/status", json!("negation")),
    ] {
        let mut input = base.clone();
        *input.pointer_mut(path).unwrap() = value;
        assert_eq!(
            code(decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap_err()),
            "compact_json"
        );
    }
    for extra in [
        "scope",
        "snapshot_id",
        "sparql",
        "limit",
        "negation",
        "references",
        "command",
        "traversal",
    ] {
        let mut input = base.clone();
        input["proposal"][extra] = json!("untrusted");
        assert_eq!(
            code(decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap_err()),
            "compact_json"
        );
    }
    let mut missing = base.clone();
    missing["proposal"]
        .as_object_mut()
        .unwrap()
        .remove("projection");
    assert_eq!(
        code(decode_intent(&serde_json::to_vec(&missing).unwrap()).unwrap_err()),
        "compact_json"
    );
    let raw = serde_json::to_string(&base).unwrap().replacen(
        "\"version\":2",
        "\"version\":2,\"version\":2",
        1,
    );
    assert_eq!(
        code(decode_intent(raw.as_bytes()).unwrap_err()),
        "compact_json"
    );
    assert_eq!(
        code(decode_intent(&vec![b' '; 65_537]).unwrap_err()),
        "input_limit"
    );
    let mut old = base;
    old["version"] = json!(1);
    assert_eq!(
        code(decode_intent(&serde_json::to_vec(&old).unwrap()).unwrap_err()),
        "compact_version"
    );
}

#[test]
fn context_authority_graph_local_roles_and_policy_are_independent_checks() {
    let (g, mut p, c) = fixture();
    assert!(c
        .references()
        .iter()
        .all(|r| r.graph == PUBLIC && !r.iri.ends_with("secret")));
    assert_eq!(
        code(
            g.compact_context("question", &[PRIVATE.into()], &p, 1)
                .unwrap_err()
        ),
        "scope"
    );
    assert_eq!(
        code(
            g.compact_context("question", &[PUBLIC.into(), PUBLIC.into()], &p, 1)
                .unwrap_err()
        ),
        "scope"
    );
    for limit in [0, 101] {
        assert_eq!(
            code(
                g.compact_context("question", &[PUBLIC.into()], &p, limit)
                    .unwrap_err()
            ),
            "complexity"
        );
    }
    p.graphs.push(PRIVATE.into());
    let scope = vec![PUBLIC.into(), PRIVATE.into()];
    let both = g.compact_context("question", &scope, &p, 100).unwrap();
    let reversed = g
        .compact_context("question", &[PRIVATE.into(), PUBLIC.into()], &p, 100)
        .unwrap();
    assert_eq!(
        serde_json::to_value(&both).unwrap(),
        serde_json::to_value(&reversed).unwrap()
    );
    for (i, r) in both.references().iter().enumerate() {
        assert_eq!(usize::from(r.id), i);
    }
    let cross = candidate(vec![edge_in(
        &both,
        PUBLIC,
        json!({"entity":index(&both,PRIVATE,&format!("{EX}company"),Role::Entity)}),
        &format!("{EX}employees"),
        json!({"var":0}),
    )]);
    let intent = decode_intent(&serde_json::to_vec(&cross).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&both, &intent, &p).unwrap_err()),
        "compact_reference"
    );
    // A role observed elsewhere is insufficient even when the IRI occurs in both graphs.
    assert!(!both
        .references()
        .iter()
        .any(|r| r.graph == PRIVATE && r.role == Role::Class));
    let partial = candidate(vec![edge_in(
        &both,
        PUBLIC,
        json!({"var":0}),
        &format!("{EX}employees"),
        json!({"var":1}),
    )]);
    let intent = decode_intent(&serde_json::to_vec(&partial).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&both, &intent, &p).unwrap_err()),
        "scope"
    );
    let connected = candidate(vec![
        edge_in(
            &both,
            PUBLIC,
            json!({"var":0}),
            &format!("{EX}employees"),
            json!({"var":1}),
        ),
        edge_in(
            &both,
            PRIVATE,
            json!({"var":0}),
            &format!("{EX}secret"),
            json!({"var":2}),
        ),
    ]);
    let result = execute(&g, &both, &p, &connected);
    assert_eq!(
        result.bindings,
        vec![row("v0", iri(&format!("{EX}company")))]
    );
    assert_eq!(result.evidence.len(), 2);
    assert_eq!(result.scope, vec![PRIVATE.to_string(), PUBLIC.to_string()]);
    let base = candidate(vec![edge(
        &c,
        json!({"var":0}),
        "employees",
        json!({"var":1}),
    )]);
    let intent = decode_intent(&serde_json::to_vec(&base).unwrap()).unwrap();
    p.max_rows = 1;
    assert_eq!(
        code(g.expand_compact(&c, &intent, &p).unwrap_err()),
        "complexity"
    );
    let changed = Snapshot::from_bytes(b"<urn:other> { <urn:a> <urn:p> <urn:b> }", "trig").unwrap();
    assert_eq!(
        code(changed.expand_compact(&c, &intent, &p).unwrap_err()),
        "snapshot"
    );
    p.graphs.clear();
    assert_eq!(
        code(g.expand_compact(&c, &intent, &p).unwrap_err()),
        "scope"
    );
}

#[test]
fn abstention_and_preflight_never_invent_plans() {
    let (g, p, c) = fixture();
    for status in ["unsupported", "needs_clarification"] {
        let input =
            json!({"version":2,"proposal":{"status":status,"reason":"Need more information"}});
        let intent = decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap();
        let proposal = g.expand_compact(&c, &intent, &p).unwrap();
        assert_eq!(serde_json::to_value(proposal).unwrap(), input["proposal"]);
        for reason in [String::new(), "x".repeat(4097)] {
            let input = json!({"version":2,"proposal":{"status":status,"reason":reason}});
            let intent = decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap();
            assert_eq!(
                code(g.expand_compact(&c, &intent, &p).unwrap_err()),
                "compact_reason"
            );
        }
    }
    let negation = g
        .compact_context(
            "Hvilke selskaper har ingen kontrakter?",
            &[PUBLIC.into()],
            &p,
            100,
        )
        .unwrap();
    let input = candidate(vec![edge(
        &negation,
        json!({"var":0}),
        "contract",
        json!({"var":1}),
    )]);
    let intent = decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap();
    assert_eq!(
        code(g.expand_compact(&negation, &intent, &p).unwrap_err()),
        "unsupported_negation"
    );
    let mut bytes = include_bytes!("../../../tests/fixtures/smoke.trig").to_vec();
    bytes.extend_from_slice(b"\n<https://example.org/public> { <https://example.org/company> <http://www.w3.org/2000/01/rdf-schema#label> \"Felles navn\" . <https://example.org/municipality> <http://www.w3.org/2000/01/rdf-schema#label> \"Felles navn\" . }");
    let ambiguous = Snapshot::from_bytes(&bytes, "trig").unwrap();
    let context = ambiguous
        .compact_context("Vis Felles navn", &[PUBLIC.into()], &p, 100)
        .unwrap();
    let input = candidate(vec![edge(
        &context,
        json!({"var":0}),
        "employees",
        json!({"var":1}),
    )]);
    let intent = decode_intent(&serde_json::to_vec(&input).unwrap()).unwrap();
    assert_eq!(
        code(ambiguous.expand_compact(&context, &intent, &p).unwrap_err()),
        "ambiguous_entity_label"
    );
}

#[test]
fn schema_is_separate_and_pinned() {
    assert_eq!(
        verity_core::compact::schema(),
        serde_json::from_slice::<Value>(include_bytes!("../../../schemas/compact-intent-v2.json"))
            .unwrap()
    );
    assert_eq!(
        verity_core::schemas(),
        serde_json::from_slice::<Value>(include_bytes!("../../../schemas/contracts-v1.json"))
            .unwrap()
    );
}

// Hand-authored operations and answers from retained public RDF, never benchmark/gold loading.
#[test]
fn public_schema_source_operations_preserve_bindings_and_named_evidence() {
    let graph = Snapshot::from_bytes(
        include_bytes!("../../../data/worldcities-transfer/snapshot.nq"),
        "nquads",
    )
    .unwrap();
    let policy: Policy = serde_json::from_slice(include_bytes!(
        "../../../data/worldcities-transfer/policy.json"
    ))
    .unwrap();
    let scope = "urn:graph-verity:worldcities:transfer:NO";
    let context = graph
        .compact_context(
            "Vis de eksplisitte utviklingsrelasjonene",
            &[scope.into()],
            &policy,
            100,
        )
        .unwrap();
    let oslo = "https://sws.geonames.org/3143244/";
    let region = "urn:graph-verity:worldcities:admin:NO:Oslo";
    let country = "urn:graph-verity:worldcities:country:NO";
    let containment = "https://schema.org/containedInPlace";
    let oslo_node = json!({"entity":index(&context,scope,oslo,Role::Entity)});
    let direct = candidate(vec![edge_in(
        &context,
        scope,
        oslo_node.clone(),
        containment,
        json!({"var":0}),
    )]);
    let result = execute(&graph, &context, &policy, &direct);
    assert_eq!(result.bindings, vec![row("v0", iri(region))]);
    assert_eq!(result.evidence.len(), 1);
    assert_eq!(result.evidence[0].subject, iri(oslo));
    assert_eq!(result.evidence[0].predicate, iri(containment));
    assert_eq!(result.evidence[0].object, iri(region));
    let mut reverse = candidate(vec![edge_in(
        &context,
        scope,
        json!({"entity":index(&context,scope,region,Role::Entity)}),
        containment,
        json!({"var":0}),
    )]);
    reverse["proposal"]["edges"][0]["direction"] = json!("reverse");
    assert_eq!(
        execute(&graph, &context, &policy, &reverse).bindings,
        vec![row("v0", iri(oslo))]
    );
    let mut two_hop = direct;
    two_hop["proposal"]["edges"]
        .as_array_mut()
        .unwrap()
        .push(edge_in(
            &context,
            scope,
            json!({"var":0}),
            containment,
            json!({"var":1}),
        ));
    two_hop["proposal"]["projection"] = json!([{"var":1}]);
    let result = execute(&graph, &context, &policy, &two_hop);
    assert_eq!(result.bindings, vec![row("v1", iri(country))]);
    assert_eq!(result.evidence.len(), 2);
    let mut numeric = candidate(vec![edge_in(
        &context,
        scope,
        oslo_node,
        "https://schema.org/identifier",
        json!({"var":0}),
    )]);
    numeric["proposal"]["filters"] =
        json!([{"var":0,"op":"ge","datatype":"integer","lexical":"3143244"}]);
    assert_eq!(
        execute(&graph, &context, &policy, &numeric).bindings,
        vec![row("v0", integer("3143244"))]
    );
    numeric["proposal"]["filters"][0]["op"] = json!("gt");
    assert!(execute(&graph, &context, &policy, &numeric)
        .bindings
        .is_empty());
    let typed = edge_in(
        &context,
        scope,
        json!({"var":0}),
        RDF_TYPE,
        json!({"class":index(&context,scope,"https://schema.org/City",Role::Class)}),
    );
    let mut count = candidate(vec![typed.clone()]);
    count["proposal"]["projection"] = json!([{"count_distinct":0}]);
    let result = execute(&graph, &context, &policy, &count);
    assert_eq!(result.bindings, vec![row("c0", integer("42"))]);
    assert_eq!(result.evidence.len(), 42);
    let mut groups = candidate(vec![
        typed,
        edge_in(
            &context,
            scope,
            json!({"var":0}),
            containment,
            json!({"var":1}),
        ),
    ]);
    groups["proposal"]["projection"] = json!([{"var":1},{"count_distinct":0}]);
    groups["proposal"]["group_by"] = json!([1]);
    groups["proposal"]["having"] = json!([{"count":1,"op":"ge","value":5}]);
    let result = execute(&graph, &context, &policy, &groups);
    assert_eq!(
        result.bindings,
        vec![Row::from([
            (
                "v1".into(),
                iri("urn:graph-verity:worldcities:admin:NO:Rogaland")
            ),
            ("c1".into(), integer("5"))
        ])]
    );
    assert_eq!(result.evidence.len(), 10);
    // A second authorized named graph has its own indexes and exactly its own six cities.
    let island = "urn:graph-verity:worldcities:transfer:IS";
    let c = graph
        .compact_context("Tell byer på Island", &[island.into()], &policy, 100)
        .unwrap();
    let mut count = candidate(vec![edge_in(
        &c,
        island,
        json!({"var":0}),
        RDF_TYPE,
        json!({"class":index(&c,island,"https://schema.org/City",Role::Class)}),
    )]);
    count["proposal"]["projection"] = json!([{"count_distinct":0}]);
    assert_eq!(
        execute(&graph, &c, &policy, &count).bindings,
        vec![row("c0", integer("6"))]
    );
}

#[test]
fn public_wikidata_temporal_and_decimal_boundaries() {
    let graph = Snapshot::from_bytes(
        include_bytes!("../../../data/wikidata/snapshot.nq"),
        "nquads",
    )
    .unwrap();
    let policy: Policy =
        serde_json::from_slice(include_bytes!("../../../data/wikidata/policy.json")).unwrap();
    let scope = "urn:graph-verity:wikidata:development";
    let context = graph
        .compact_context(
            "Vis de oppgitte Oslo-grensene",
            &[scope.into()],
            &policy,
            100,
        )
        .unwrap();
    for (predicate, datatype, lexical, expected) in [
        (
            "P571",
            "date_time",
            "1048-01-01T00:00:00Z",
            "1048-01-01T00:00:00Z",
        ),
        ("P1082", "decimal", "717710", "717710"),
    ] {
        let mut input = candidate(vec![edge_in(
            &context,
            scope,
            json!({"entity":index(&context,scope,"http://www.wikidata.org/entity/Q585",Role::Entity)}),
            &format!("http://www.wikidata.org/prop/direct/{predicate}"),
            json!({"var":0}),
        )]);
        input["proposal"]["filters"] =
            json!([{"var":0,"op":"ge","datatype":datatype,"lexical":lexical}]);
        let result = execute(&graph, &context, &policy, &input);
        assert_eq!(
            result.bindings,
            vec![row(
                "v0",
                RdfTerm::Literal {
                    value: expected.into(),
                    datatype: format!(
                        "{XSD}{}",
                        if datatype == "date_time" {
                            "dateTime"
                        } else {
                            datatype
                        }
                    ),
                    language: None
                }
            )]
        );
        assert_eq!(result.evidence.len(), 1);
        input["proposal"]["filters"][0]["op"] = json!("gt");
        assert!(execute(&graph, &context, &policy, &input)
            .bindings
            .is_empty());
    }
}

#[test]
fn compact_model_scoring_preserves_raw_bytes_and_distinguishes_guards() {
    use verity_core::{
        evaluation::{Benchmark, Case},
        parser::{ParserRequest, SemanticParser},
    };
    struct Model(Vec<u8>);
    impl SemanticParser for Model {
        fn origin(&self) -> PlanOrigin {
            PlanOrigin::LocalModel
        }
        fn model(&self) -> Option<String> {
            Some("mock_compact_not_inference".into())
        }
        fn compact_v2(&self) -> bool {
            true
        }
        fn propose(&self, _: &ParserRequest) -> verity_core::Result<Vec<u8>> {
            panic!("v1 path used")
        }
        fn propose_compact(&self, context: &CompactContext) -> verity_core::Result<Vec<u8>> {
            assert!(context.references().iter().all(|r| r.graph == PUBLIC));
            Ok(self.0.clone())
        }
    }
    let (graph, policy, context) = fixture();
    let proposal = candidate(vec![edge(
        &context,
        entity(&context, "municipality"),
        "owns",
        json!({"var": 0}),
    )]);
    let mut gold = expand(&graph, &context, &policy, &proposal);
    gold.patterns[0].to = ir::Node::Variable {
        name: "company".into(),
    };
    gold.projection = vec![ir::Projection::Variable {
        name: "company".into(),
    }];
    let mut benchmark = Benchmark { version: 1, name: "compact-scoring-control".into(), snapshot_id: graph.id().into(), cases: vec![Case {
        id: "candidate".into(), question: "Vis de oppgitte relasjonene".into(), interpretation: "control".into(), family: "control".into(),
        split: "dev".into(), review_status: "synthetic".into(), provenance: "test_not_model_accuracy".into(), scope: vec![PUBLIC.into()],
        expected_status: "executed".into(), gold: Some(gold),
        reference_sparql: Some(format!("SELECT ?company WHERE {{ GRAPH <{PUBLIC}> {{ <{EX}municipality> <{EX}owns> ?company }} }}")),
        expected_bindings: Some(vec![Row::from([("company".into(), iri(&format!("{EX}company")))])]),
    }] };
    let raw = serde_json::to_vec(&proposal).unwrap();
    let report = graph
        .evaluate(&benchmark, "dev", &policy, Some(&Model(raw.clone())))
        .unwrap();
    let score = &report.cases[0];
    assert!(score.passed);
    assert_eq!(
        score.raw_response.as_deref(),
        Some(std::str::from_utf8(&raw).unwrap())
    );
    assert_eq!(score.exact_result_set, Some(true));
    assert_eq!(score.structural_ir_exact, Some(true));
    assert!(score.expanded_plan.is_some());
    assert!(matches!(
        score.execution.as_ref().unwrap().origin,
        PlanOrigin::LocalModel
    ));

    // Group/count aliases and HAVING positions are normalized without changing operations.
    let mut grouped = candidate(vec![
        edge(
            &context,
            entity(&context, "municipality"),
            "owns",
            json!({"var": 0}),
        ),
        edge(&context, json!({"var": 0}), "contract", json!({"var": 1})),
    ]);
    grouped["proposal"]["projection"] = json!([{"var": 0}, {"count_distinct": 1}]);
    grouped["proposal"]["group_by"] = json!([0]);
    grouped["proposal"]["having"] = json!([{"count": 1, "op": "ge", "value": 2}]);
    let mut case = benchmark.cases[0].clone();
    let mut gold = expand(&graph, &context, &policy, &grouped);
    gold.projection[1] = ir::Projection::CountDistinct {
        variable: "v1".into(),
        alias: "total".into(),
    };
    gold.having[0].alias = "total".into();
    case.gold = Some(gold);
    case.reference_sparql = Some(format!("SELECT ?v0 (COUNT(DISTINCT ?v1) AS ?total) WHERE {{ GRAPH <{PUBLIC}> {{ <{EX}municipality> <{EX}owns> ?v0 . ?v0 <{EX}contract> ?v1 }} }} GROUP BY ?v0 HAVING(COUNT(DISTINCT ?v1) >= 2)"));
    case.expected_bindings = Some(vec![Row::from([
        ("v0".into(), iri(&format!("{EX}company"))),
        ("total".into(), integer("2")),
    ])]);
    let grouped_benchmark = Benchmark {
        version: 1,
        name: "grouped-control".into(),
        snapshot_id: graph.id().into(),
        cases: vec![case],
    };
    let report = graph
        .evaluate(
            &grouped_benchmark,
            "dev",
            &policy,
            Some(&Model(serde_json::to_vec(&grouped).unwrap())),
        )
        .unwrap();
    assert!(report.cases[0].passed, "{}", report.cases[0].detail);
    grouped["proposal"]["having"][0]["op"] = json!("gt");
    let report = graph
        .evaluate(
            &grouped_benchmark,
            "dev",
            &policy,
            Some(&Model(serde_json::to_vec(&grouped).unwrap())),
        )
        .unwrap();
    assert!(!report.cases[0].passed);
    assert_eq!(report.cases[0].structural_ir_exact, Some(false));
    assert!(report.cases[0].wrong_plan_successful_execution);

    let mut wrong = proposal.clone();
    wrong["proposal"]["edges"][0]["predicate"] = json!(index(
        &context,
        PUBLIC,
        &format!("{EX}contract"),
        Role::Predicate
    ));
    let report = graph
        .evaluate(
            &benchmark,
            "dev",
            &policy,
            Some(&Model(serde_json::to_vec(&wrong).unwrap())),
        )
        .unwrap();
    assert!(report.cases[0].wrong_plan_successful_execution);
    assert_eq!(report.cases[0].exact_result_set, Some(false));

    for (raw, contract, code) in [
        (b"{\"version\":2".to_vec(), false, "compact_json"),
        (
            serde_json::to_vec(&{
                let mut p = proposal.clone();
                p["proposal"]["edges"][0]["predicate"] = json!(65535);
                p
            })
            .unwrap(),
            true,
            "compact_reference",
        ),
    ] {
        let report = graph
            .evaluate(&benchmark, "dev", &policy, Some(&Model(raw.clone())))
            .unwrap();
        let score = &report.cases[0];
        assert!(!score.passed);
        assert_eq!(score.contract_valid, Some(contract));
        assert_eq!(score.error_code.as_deref(), Some(code));
        assert_eq!(
            score.raw_response.as_deref(),
            Some(std::str::from_utf8(&raw).unwrap())
        );
        assert!(score.execution.is_none());
    }
    benchmark.cases[0].question = "Hvilke selskaper har ingen kontrakter?".into();
    benchmark.cases[0].expected_status = "unsupported".into();
    benchmark.cases[0].gold = None;
    benchmark.cases[0].reference_sparql = None;
    benchmark.cases[0].expected_bindings = None;
    // The model is still invoked; blocking a candidate must not become model abstention.
    let report = graph
        .evaluate(&benchmark, "dev", &policy, Some(&Model(raw)))
        .unwrap();
    let score = &report.cases[0];
    assert!(!score.passed);
    assert!(score.preflight_would_block.is_some());
    assert_eq!(score.stage, "compact_expansion");
    assert_eq!(score.proposal_status.as_deref(), Some("candidate"));
    assert!(score.execution.is_none());
    let abstention =
        br#"{"version":2,"proposal":{"status":"unsupported","reason":"Negation"}}"#.to_vec();
    let report = graph
        .evaluate(&benchmark, "dev", &policy, Some(&Model(abstention)))
        .unwrap();
    assert!(report.cases[0].passed);
    assert_eq!(
        report.cases[0].proposal_status.as_deref(),
        Some("unsupported")
    );
    assert!(report.cases[0].expanded_plan.is_none());
}
