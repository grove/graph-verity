//! Indexed proposals contain no executable text or authority. Expansion always compiles v1 IR.
use crate::{
    catalog::{Label, Policy, Profile},
    ir::{self, Compare, Direction, Plan, RDF_TYPE, XSD},
    parser::{preflight, PreflightBlock, Proposal},
    reject, Result, Snapshot,
};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    Entity,
    Predicate,
    Class,
}

impl Role {
    fn name(self) -> &'static str {
        match self {
            Self::Entity => "entity",
            Self::Predicate => "predicate",
            Self::Class => "class",
        }
    }
}

#[derive(Debug, Serialize)]
pub struct Reference {
    pub id: u16,
    pub graph: String,
    pub role: Role,
    pub iri: String,
    pub labels: BTreeSet<Label>,
}

/// Created by Snapshot only; never deserialize a model-supplied context or index table.
#[derive(Debug, Serialize)]
pub struct CompactContext {
    question: String,
    snapshot_id: String,
    scope: Vec<String>,
    references: Vec<Reference>,
    profiles: BTreeMap<String, BTreeMap<String, Profile>>,
    limit: u32,
    #[serde(skip)]
    block: Option<PreflightBlock>,
}

impl CompactContext {
    pub fn references(&self) -> &[Reference] {
        &self.references
    }

    fn resolve(&self, id: u16, role: Role, graph: Option<&str>) -> Result<&Reference> {
        self.references
            .get(usize::from(id))
            .filter(|r| r.id == id && r.role == role && graph.is_none_or(|g| r.graph == g))
            .ok_or_else(|| {
                reject(
                    "compact_reference",
                    "Unknown, wrong-role or cross-graph index",
                )
            })
    }

    fn node(&self, node: &CompactNode, graph: &str) -> Result<ir::Node> {
        Ok(match node {
            CompactNode::Var(id) => ir::Node::Variable {
                name: variable(*id)?,
            },
            CompactNode::Entity(id) | CompactNode::Class(id) => ir::Node::Iri {
                iri: self
                    .resolve(
                        *id,
                        if matches!(node, CompactNode::Class(_)) {
                            Role::Class
                        } else {
                            Role::Entity
                        },
                        Some(graph),
                    )?
                    .iri
                    .clone(),
            },
        })
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CompactIntentV2 {
    pub version: u32,
    pub proposal: CompactProposal,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "status", rename_all = "snake_case", deny_unknown_fields)]
pub enum CompactProposal {
    Candidate {
        edges: Vec<CompactEdge>,
        filters: Vec<CompactFilter>,
        projection: Vec<CompactProjection>,
        group_by: Vec<u8>,
        having: Vec<CompactHaving>,
    },
    NeedsClarification {
        reason: String,
    },
    Unsupported {
        reason: String,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CompactEdge {
    pub from: CompactNode,
    pub predicate: u16,
    pub direction: Direction,
    pub to: CompactNode,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum CompactNode {
    Var(u8),
    Entity(u16),
    Class(u16),
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Datatype {
    Integer,
    Decimal,
    Double,
    Date,
    DateTime,
    Boolean,
    String,
}

impl Datatype {
    fn iri(self) -> String {
        let local = match self {
            Self::Integer => "integer",
            Self::Decimal => "decimal",
            Self::Double => "double",
            Self::Date => "date",
            Self::DateTime => "dateTime",
            Self::Boolean => "boolean",
            Self::String => "string",
        };
        format!("{XSD}{local}")
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CompactFilter {
    pub var: u8,
    pub op: Compare,
    pub datatype: Datatype,
    pub lexical: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum CompactProjection {
    Var(u8),
    CountDistinct(u8),
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CompactHaving {
    /// Zero-based projection position, which must be a distinct-count output.
    pub count: u8,
    pub op: Compare,
    pub value: u32,
}

fn variable(id: u8) -> Result<String> {
    if id >= 12 {
        return Err(reject("complexity", "Variable IDs must be in 0..12"));
    }
    Ok(format!("v{id}"))
}

pub fn decode_intent(bytes: &[u8]) -> Result<CompactIntentV2> {
    if bytes.len() > 65_536 {
        return Err(reject("input_limit", "Compact intent exceeds 64 KiB"));
    }
    let intent: CompactIntentV2 =
        serde_json::from_slice(bytes).map_err(|e| reject("compact_json", e.to_string()))?;
    if intent.version != 2 {
        return Err(reject(
            "compact_version",
            "Only compact version 2 is supported",
        ));
    }
    Ok(intent)
}

pub fn schema() -> serde_json::Value {
    serde_json::to_value(schemars::schema_for!(CompactIntentV2)).expect("serializable schema")
}

impl Snapshot {
    pub fn compact_context(
        &self,
        question: &str,
        scope: &[String],
        policy: &Policy,
        limit: u32,
    ) -> Result<CompactContext> {
        let request = self.parser_request(question, scope, policy)?;
        if limit == 0 || limit > policy.max_rows {
            return Err(reject("complexity", "Trusted limit exceeds policy"));
        }
        let mut references = Vec::new();
        for graph in &request.catalog.scope {
            // Roles, not just occurrence, must be local to this exact graph.
            for (iri, entry) in self.catalog(std::slice::from_ref(graph), policy)?.entries {
                for role in [Role::Entity, Role::Predicate, Role::Class] {
                    if entry.roles.contains(role.name()) {
                        references.push(Reference {
                            id: u16::try_from(references.len())
                                .map_err(|_| reject("context_limit", "Too many indexes"))?,
                            graph: graph.clone(),
                            role,
                            iri: iri.clone(),
                            labels: entry.labels.clone(),
                        });
                    }
                }
            }
        }
        let context = CompactContext {
            block: preflight(&request),
            question: request.question,
            snapshot_id: request.catalog.snapshot_id,
            scope: request.catalog.scope,
            profiles: request.catalog.profiles,
            references,
            limit,
        };
        if serde_json::to_vec(&context)?.len() > 131_072 {
            return Err(reject(
                "context_limit",
                "Compact context exceeds 128 KiB; narrow scope",
            ));
        }
        Ok(context)
    }

    /// Returns v1 data only after the independent policy/validator/compiler accepts it.
    pub fn expand_compact(
        &self,
        context: &CompactContext,
        intent: &CompactIntentV2,
        policy: &Policy,
    ) -> Result<Proposal> {
        policy.authorize(&context.scope)?;
        if context.snapshot_id != self.id() {
            return Err(reject("snapshot", "Context belongs to another snapshot"));
        }
        if intent.version != 2 {
            return Err(reject(
                "compact_version",
                "Only compact version 2 is supported",
            ));
        }
        let (edges, filters, projection, group_by, having) = match &intent.proposal {
            CompactProposal::Unsupported { reason }
            | CompactProposal::NeedsClarification { reason } => {
                if reason.is_empty() || reason.len() > 4096 {
                    return Err(reject(
                        "compact_reason",
                        "Abstention reason must contain 1..4096 bytes",
                    ));
                }
                return Ok(
                    if matches!(intent.proposal, CompactProposal::Unsupported { .. }) {
                        Proposal::Unsupported {
                            reason: reason.clone(),
                        }
                    } else {
                        Proposal::NeedsClarification {
                            reason: reason.clone(),
                        }
                    },
                );
            }
            CompactProposal::Candidate {
                edges,
                filters,
                projection,
                group_by,
                having,
            } => (edges, filters, projection, group_by, having),
        };
        if let Some(block) = context.block {
            return Err(reject(
                block.code(),
                "Trusted question preflight requires abstention",
            ));
        }
        if edges.is_empty()
            || edges.len() > 8
            || filters.len() > 8
            || projection.is_empty()
            || projection.len() > 8
            || group_by.len() > 8
            || having.len() > 4
        {
            return Err(reject(
                "complexity",
                "Compact candidate exceeds v1 structural limits",
            ));
        }
        let mut patterns = Vec::new();
        for (i, edge) in edges.iter().enumerate() {
            if edges[..i].contains(edge) {
                return Err(reject("compact_duplicate", "Duplicate edge"));
            }
            let predicate = context.resolve(edge.predicate, Role::Predicate, None)?;
            let (subject, object) = match edge.direction {
                Direction::Forward => (&edge.from, &edge.to),
                Direction::Reverse => (&edge.to, &edge.from),
            };
            if matches!(subject, CompactNode::Class(_))
                || (matches!(object, CompactNode::Class(_)) && predicate.iri != RDF_TYPE)
                || (matches!(object, CompactNode::Entity(_)) && predicate.iri == RDF_TYPE)
            {
                return Err(reject(
                    "class",
                    "Class constants require the object position of rdf:type",
                ));
            }
            patterns.push(ir::Pattern {
                graph: predicate.graph.clone(),
                from: context.node(&edge.from, &predicate.graph)?,
                predicate: predicate.iri.clone(),
                direction: edge.direction,
                to: context.node(&edge.to, &predicate.graph)?,
            });
        }
        let plan = Plan {
            version: 1,
            snapshot_id: context.snapshot_id.clone(),
            scope: context.scope.clone(),
            patterns,
            filters: filters
                .iter()
                .map(|f| {
                    Ok(ir::Filter {
                        variable: variable(f.var)?,
                        op: f.op,
                        value: ir::Value {
                            lexical: f.lexical.clone(),
                            datatype: f.datatype.iri(),
                            language: None,
                        },
                    })
                })
                .collect::<Result<_>>()?,
            projection: projection
                .iter()
                .enumerate()
                .map(|(i, p)| {
                    Ok(match p {
                        CompactProjection::Var(id) => ir::Projection::Variable {
                            name: variable(*id)?,
                        },
                        CompactProjection::CountDistinct(id) => ir::Projection::CountDistinct {
                            variable: variable(*id)?,
                            alias: format!("c{i}"),
                        },
                    })
                })
                .collect::<Result<_>>()?,
            group_by: group_by
                .iter()
                .map(|id| variable(*id))
                .collect::<Result<_>>()?,
            having: having
                .iter()
                .map(|h| {
                    if !matches!(
                        projection.get(usize::from(h.count)),
                        Some(CompactProjection::CountDistinct(_))
                    ) {
                        return Err(reject(
                            "aggregation",
                            "HAVING must index a projected distinct count",
                        ));
                    }
                    Ok(ir::Having {
                        alias: format!("c{}", h.count),
                        op: h.op,
                        value: h.value,
                    })
                })
                .collect::<Result<_>>()?,
            limit: context.limit,
        };
        self.compile(&plan, policy)?;
        Ok(Proposal::Candidate { plan })
    }
}
