use sha2::{Digest, Sha256};
use verity_core::{
    catalog::Policy,
    discovery::{DiscoveryConfig, DiscoveryIndex, Source},
    vocabulary::{VocabularyBudget, VocabularyPacket, VocabularyRequest},
    Result, Snapshot,
};
use verity_shacl::{
    build_shape_guidance, PathDirection, RdfSource, ShapeConfig, ShapeGuidanceIndex, ShapeOrigin,
};

const DATA_GRAPH: &str = "https://example.org/public";
const SHAPE_GRAPH: &str = "https://example.org/shapes";
const DATA_BYTES: &[u8] = include_bytes!("../../../tests/fixtures/smoke.trig");
const SHAPE_BYTES: &[u8] = include_bytes!("../../../tests/fixtures/shacl-guidance.trig");

fn build(
    shape_bytes: &[u8],
    data_bytes: &[u8],
    config: &ShapeConfig,
    discovery: &DiscoveryIndex,
    packet: &VocabularyPacket,
    policy: &Policy,
) -> Result<ShapeGuidanceIndex> {
    build_shape_guidance(
        RdfSource {
            bytes: shape_bytes,
            format: "trig",
        },
        RdfSource {
            bytes: data_bytes,
            format: "trig",
        },
        config,
        discovery,
        packet,
        policy,
    )
}

fn fixtures() -> (
    Snapshot,
    Snapshot,
    Policy,
    DiscoveryConfig,
    ShapeConfig,
    VocabularyRequest,
    VocabularyBudget,
) {
    let data = Snapshot::from_bytes(DATA_BYTES, "trig").unwrap();
    let shapes = Snapshot::from_bytes(SHAPE_BYTES, "trig").unwrap();
    let policy = Policy {
        version: 1,
        graphs: vec![DATA_GRAPH.into()],
        max_rows: 100,
        max_evidence: 100,
        timeout_ms: 5000,
    };
    let source = Source {
        source: "Graph Verity synthetic fixture".into(),
        license: "Apache-2.0".into(),
        source_revision: "smoke-v1".into(),
        importer_revision: "test-fixture-v1".into(),
    };
    let discovery = DiscoveryConfig {
        version: 1,
        snapshot_id: data.id().into(),
        graphs: [(DATA_GRAPH.into(), source.clone())].into(),
    };
    let shape_config = ShapeConfig {
        version: 1,
        shape_snapshot_id: shapes.id().into(),
        data_snapshot_id: data.id().into(),
        shape_graph: SHAPE_GRAPH.into(),
        data_graph: DATA_GRAPH.into(),
        origin: ShapeOrigin::OperatorAuthoredDemo,
        source: Source {
            source: "Graph Verity authored demo shapes".into(),
            license: "Apache-2.0".into(),
            source_revision: "shacl-guidance-fixture-v1".into(),
            importer_revision: "direct-rdf-fixture-v1".into(),
        },
    };
    let index = data
        .build_discovery(&[DATA_GRAPH.into()], &policy, &discovery)
        .unwrap();
    let request = VocabularyRequest {
        question: "owns".into(),
        language: "en".into(),
        snapshot_id: data.id().into(),
        index_revision: index.manifest().index_revision.clone(),
        scope: vec![DATA_GRAPH.into()],
    };
    let budget = VocabularyBudget {
        per_role_top_k: 10,
        max_packet_bytes: 262_144,
        texts_per_candidate: 8,
        max_text_bytes: 2048,
        evidence_per_page: 3,
        max_source_bytes: 4096,
    };
    (
        data,
        shapes,
        policy,
        discovery,
        shape_config,
        request,
        budget,
    )
}

#[test]
fn direct_and_inverse_shape_metadata_join_to_the_exact_bm25_predicate_candidate() {
    let (data, _, policy, discovery, config, request, budget) = fixtures();
    let discovery = data
        .build_discovery(&request.scope, &policy, &discovery)
        .unwrap();
    let packet = data
        .vocabulary_packet(&discovery, &request, &policy, &budget)
        .unwrap();
    let candidate = packet
        .candidates("predicate")
        .unwrap()
        .iter()
        .find(|candidate| candidate.iri == "https://example.org/owns")
        .unwrap();
    let guidance = build(
        SHAPE_BYTES,
        DATA_BYTES,
        &config,
        &discovery,
        &packet,
        &policy,
    )
    .unwrap();
    let properties = guidance
        .for_candidate(&packet, &candidate.id, DATA_GRAPH)
        .unwrap();
    let source_hash = format!(
        "{:x}",
        Sha256::digest(include_bytes!(
            "../../../tests/fixtures/shacl-guidance.trig"
        ))
    );

    assert_eq!(properties.len(), 2);
    assert_eq!(properties[0].predicate_iri, candidate.iri);
    assert_eq!(properties[0].path_direction, PathDirection::Forward);
    assert_eq!(properties[1].predicate_iri, candidate.iri);
    assert_eq!(properties[1].path_direction, PathDirection::Inverse);
    assert_eq!(
        properties[1].target_classes,
        ["https://example.org/Company"]
    );
    assert_eq!(
        properties[1].class.as_deref(),
        Some("https://example.org/Municipality")
    );
    assert_eq!(
        properties[0].target_classes,
        ["https://example.org/Municipality"]
    );
    assert_eq!(
        properties[0].class.as_deref(),
        Some("https://example.org/Company")
    );
    assert_eq!(
        properties[0].node_kind.as_deref(),
        Some("http://www.w3.org/ns/shacl#IRI")
    );
    assert_eq!(properties[0].min_count, Some(1));
    assert_eq!(properties[0].max_count, Some(1));
    assert_eq!(guidance.unsupported_property_shapes(), 1);
    assert_eq!(guidance.shape_sha256(), source_hash);
    let packet_json = serde_json::to_value(&guidance).unwrap();
    assert_eq!(packet_json["origin"], "operator_authored_demo");
    assert!(packet_json["properties"]
        .as_array()
        .unwrap()
        .iter()
        .any(|property| {
            property["predicate_iri"] == candidate.iri && property["path_direction"] == "forward"
        }));
    assert!(packet_json["properties"]
        .as_array()
        .unwrap()
        .iter()
        .any(|property| {
            property["predicate_iri"] == candidate.iri && property["path_direction"] == "inverse"
        }));
    assert_eq!(packet_json["source"]["license"], "Apache-2.0");

    let employees_request = VocabularyRequest {
        question: "employees".into(),
        language: "en".into(),
        snapshot_id: data.id().into(),
        index_revision: discovery.manifest().index_revision.clone(),
        scope: vec![DATA_GRAPH.into()],
    };
    let employees_packet = data
        .vocabulary_packet(&discovery, &employees_request, &policy, &budget)
        .unwrap();
    let employees = employees_packet
        .candidates("predicate")
        .unwrap()
        .iter()
        .find(|candidate| candidate.iri == "https://example.org/employees")
        .unwrap();
    let employees_guidance = guidance
        .for_candidate(&employees_packet, &employees.id, DATA_GRAPH)
        .unwrap();
    assert_eq!(employees_guidance.len(), 1);
    assert_eq!(
        employees_guidance[0].datatype.as_deref(),
        Some("http://www.w3.org/2001/XMLSchema#integer")
    );
}

#[test]
fn complex_inverse_paths_are_omitted_without_dropping_supported_guidance() {
    let (data, _, policy, discovery_config, mut config, request, budget) = fixtures();
    let discovery = data
        .build_discovery(&request.scope, &policy, &discovery_config)
        .unwrap();
    let packet = data
        .vocabulary_packet(&discovery, &request, &policy, &budget)
        .unwrap();
    let mut shapes = SHAPE_BYTES.to_vec();
    shapes.extend_from_slice(
        br#"
ex:shapes {
          ex:ComplexShape a sh:NodeShape ;
            sh:targetClass ex:Company ;
            sh:property [ sh:path [ sh:inversePath ex:owns ; sh:alternativePath (ex:owns) ] ] .
        }
"#,
    );
    config.shape_snapshot_id = Snapshot::from_bytes(&shapes, "trig").unwrap().id().into();
    config.source.source_revision = "test-malformed-inverse-extension-v1".into();

    let guidance = build(&shapes, DATA_BYTES, &config, &discovery, &packet, &policy).unwrap();
    let candidate = packet
        .candidates("predicate")
        .unwrap()
        .iter()
        .find(|candidate| candidate.iri == "https://example.org/owns")
        .unwrap();

    assert_eq!(guidance.unsupported_property_shapes(), 2);
    assert_eq!(
        guidance
            .for_candidate(&packet, &candidate.id, DATA_GRAPH)
            .unwrap()
            .len(),
        2
    );
}

#[test]
fn stale_or_unauthorized_mappings_fail_closed_and_unknown_ids_do_not_join() {
    let (data, _, policy, discovery_config, mut config, request, budget) = fixtures();
    let discovery = data
        .build_discovery(&request.scope, &policy, &discovery_config)
        .unwrap();
    let packet = data
        .vocabulary_packet(&discovery, &request, &policy, &budget)
        .unwrap();
    let changed_source = Source {
        source: "Graph Verity synthetic fixture".into(),
        license: "Apache-2.0".into(),
        source_revision: "changed-source-revision".into(),
        importer_revision: "test-fixture-v1".into(),
    };
    let changed_config = DiscoveryConfig {
        version: 1,
        snapshot_id: data.id().into(),
        graphs: [(DATA_GRAPH.into(), changed_source)].into(),
    };
    let changed_index = data
        .build_discovery(&request.scope, &policy, &changed_config)
        .unwrap();
    let changed_packet = data
        .vocabulary_packet(&changed_index, &request, &policy, &budget)
        .unwrap();
    let guidance = build(
        SHAPE_BYTES,
        DATA_BYTES,
        &config,
        &discovery,
        &packet,
        &policy,
    )
    .unwrap();
    let changed_candidate = changed_packet
        .candidates("predicate")
        .unwrap()
        .iter()
        .find(|candidate| candidate.iri == "https://example.org/owns")
        .unwrap();
    assert!(guidance
        .for_candidate(&changed_packet, &changed_candidate.id, DATA_GRAPH)
        .is_err());
    let mut stale = config.clone();
    stale.data_snapshot_id = "sha256:stale".into();
    assert!(build(
        SHAPE_BYTES,
        DATA_BYTES,
        &stale,
        &discovery,
        &packet,
        &policy
    )
    .is_err());

    let mut unauthorized = policy.clone();
    unauthorized.graphs = vec!["https://example.org/private".into()];
    assert!(build(
        SHAPE_BYTES,
        DATA_BYTES,
        &config,
        &discovery,
        &packet,
        &unauthorized
    )
    .is_err());

    config.shape_graph = "https://example.org/missing".into();
    assert!(build(
        SHAPE_BYTES,
        DATA_BYTES,
        &config,
        &discovery,
        &packet,
        &policy
    )
    .is_err());

    let mut extra_graph = include_bytes!("../../../tests/fixtures/shacl-guidance.trig").to_vec();
    extra_graph.extend_from_slice(
        b"\n<https://example.org/unmapped> { <https://example.org/s> <https://example.org/p> <https://example.org/o> . }\n",
    );
    let extra_shapes = Snapshot::from_bytes(&extra_graph, "trig").unwrap();
    let mut incomplete_mapping = fixtures().4;
    incomplete_mapping.shape_snapshot_id = extra_shapes.id().into();
    assert!(build(
        &extra_graph,
        DATA_BYTES,
        &incomplete_mapping,
        &discovery,
        &packet,
        &policy
    )
    .is_err());

    config.shape_graph = SHAPE_GRAPH.into();
    let guidance = build(
        SHAPE_BYTES,
        DATA_BYTES,
        &config,
        &discovery,
        &packet,
        &policy,
    )
    .unwrap();
    assert!(guidance
        .for_candidate(&packet, "unknown-id", DATA_GRAPH)
        .is_err());
}
