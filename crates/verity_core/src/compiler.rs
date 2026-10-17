//! Only this module constructs executable query text from untrusted plans.
use crate::{
    catalog::{Catalog, Policy},
    ir::*,
    reject, Result, Snapshot,
};
use std::collections::{BTreeMap, BTreeSet};

type Types = BTreeSet<String>;

/// Fixed one-hop template; all resource and graph terms pass the existing IRI validator.
pub(crate) fn entity_query(request: &crate::navigation::EntityRequest) -> Result<String> {
    use crate::navigation::EdgeDirection;
    let entity = iri(&request.iri)?;
    let graphs = request
        .scope
        .iter()
        .map(|g| iri(g))
        .collect::<Result<Vec<_>>>()?
        .join(" ");
    let binding = match request.direction {
        EdgeDirection::Outgoing => format!("BIND({entity} AS ?__s)"),
        EdgeDirection::Incoming => format!("BIND({entity} AS ?__o)"),
    };
    let triple = match request.direction {
        EdgeDirection::Outgoing => format!("{entity} ?__p ?__o"),
        EdgeDirection::Incoming => format!("?__s ?__p {entity}"),
    };
    // Term keys keep equal-valued literals with different datatypes on stable pages.
    Ok(format!("SELECT ?__s ?__p ?__o ?__g WHERE {{ VALUES ?__g {{ {graphs} }} GRAPH ?__g {{ {triple} }} {binding} }} ORDER BY ?__g ?__s ?__p (isBlank(?__o)) (isIRI(?__o)) (STR(?__o)) (LANG(?__o)) (DATATYPE(?__o)) ?__o LIMIT {} OFFSET {}", request.limit + 1, request.offset))
}

/// Fields are private: callers cannot replace validated SPARQL before execution.
pub struct CompiledPlan {
    pub(crate) query: String,
    pub(crate) evidence_query: String,
    pub(crate) catalog_digest: String,
}

impl CompiledPlan {
    pub fn sparql(&self) -> &str {
        &self.query
    }
    pub fn catalog_digest(&self) -> &str {
        &self.catalog_digest
    }
}

fn bind(types: &mut BTreeMap<String, Types>, node: &Node, allowed: &Types) -> Result<()> {
    if let Node::Variable { name } = node {
        variable(name)?;
        let entry = types.entry(name.clone()).or_insert_with(|| allowed.clone());
        *entry = entry.intersection(allowed).cloned().collect();
        if entry.is_empty() {
            return Err(reject(
                "datatype",
                "Variable has incompatible binding positions",
            ));
        }
    }
    Ok(())
}

fn known(node: &Node, catalog: &Catalog, graph: &str) -> Result<()> {
    if let Node::Iri { iri: id } = node {
        iri(id)?;
        if !catalog
            .entries
            .get(id)
            .is_some_and(|entry| entry.roles.contains("entity") && entry.graphs.contains(graph))
        {
            return Err(reject(
                "unknown_identifier",
                "IRI is not an observed entity in the pattern graph",
            ));
        }
    }
    if let Node::Literal { value } = node {
        value.literal()?;
    }
    Ok(())
}

fn compatible(types: &Types, datatype: &str) -> bool {
    !types.is_empty()
        && types
            .iter()
            .all(|t| t == datatype || (numeric(t) && numeric(datatype)))
}

impl Snapshot {
    pub fn compile(&self, plan: &Plan, policy: &Policy) -> Result<CompiledPlan> {
        policy.authorize(&plan.scope)?;
        if plan.version != 1 {
            return Err(reject("ir_version", "Only IR version 1 is supported"));
        }
        if plan.snapshot_id != self.id {
            return Err(reject("snapshot", "Plan references another release"));
        }
        if plan.patterns.is_empty()
            || plan.patterns.len() > 8
            || plan.filters.len() > 8
            || plan.projection.is_empty()
            || plan.projection.len() > 8
            || plan.having.len() > 4
            || plan.group_by.len() > 8
            || plan.limit == 0
            || plan.limit > policy.max_rows
        {
            return Err(reject(
                "complexity",
                "Plan exceeds the supported complexity or row limits",
            ));
        }
        let used: BTreeSet<_> = plan.patterns.iter().map(|p| &p.graph).collect();
        if used != plan.scope.iter().collect() {
            return Err(reject(
                "scope",
                "Declared scope must exactly match pattern graphs",
            ));
        }
        let catalog = self.catalog(&plan.scope, policy)?;
        let mut types = BTreeMap::new();
        let mut ill_typed = BTreeSet::new();
        let mut pattern_variables = Vec::new();
        let mut triples = Vec::new();
        let mut body = String::new();
        for pattern in &plan.patterns {
            let (subject, object) = pattern.ends();
            if matches!(subject, Node::Literal { .. }) {
                return Err(reject(
                    "direction",
                    "A literal cannot be the subject of an RDF edge",
                ));
            }
            known(subject, &catalog, &pattern.graph)?;
            known(object, &catalog, &pattern.graph)?;
            let profile = catalog
                .profiles
                .get(&pattern.graph)
                .and_then(|p| p.get(&pattern.predicate))
                .ok_or_else(|| {
                    reject(
                        "predicate",
                        "Predicate is not in the selected graph vocabulary",
                    )
                })?;
            if pattern.predicate == RDF_TYPE {
                if let Node::Iri { iri: id } = object {
                    if !catalog
                        .entries
                        .get(id)
                        .is_some_and(|e| e.roles.contains("class"))
                    {
                        return Err(reject("class", "Type object is not an observed class"));
                    }
                }
            }
            if matches!(object, Node::Iri { .. }) && !profile.object_types.contains("resource") {
                return Err(reject(
                    "datatype",
                    "IRI object is incompatible with the scoped predicate range",
                ));
            }
            bind(&mut types, subject, &BTreeSet::from(["resource".into()]))?;
            bind(&mut types, object, &profile.object_types)?;
            if let Node::Literal { value } = object {
                if !profile.object_types.iter().any(|t| t == &value.datatype) {
                    return Err(reject(
                        "datatype",
                        "Literal type does not occur for this scoped predicate",
                    ));
                }
            }
            if profile.ill_typed {
                if let Node::Variable { name } = object {
                    ill_typed.insert(name.clone());
                }
            }
            let vars: BTreeSet<String> = [subject, object]
                .iter()
                .filter_map(|node| {
                    if let Node::Variable { name } = node {
                        Some(name.clone())
                    } else {
                        None
                    }
                })
                .collect();
            if vars.is_empty() {
                return Err(reject("complexity", "Every pattern must bind a variable"));
            }
            pattern_variables.push(vars);
            let s = subject.sparql()?;
            let p = iri(&pattern.predicate)?;
            let o = object.sparql()?;
            let g = iri(&pattern.graph)?;
            body.push_str(&format!("GRAPH {g} {{ {s} {p} {o} . }}\n"));
            triples.push((s, p, o, g));
        }
        if types.len() > 12 {
            return Err(reject("complexity", "More than 12 variables"));
        }
        let mut connected = pattern_variables[0].clone();
        for _ in 0..pattern_variables.len() {
            for vars in &pattern_variables {
                if !connected.is_disjoint(vars) {
                    connected.extend(vars.iter().cloned());
                }
            }
        }
        if pattern_variables.iter().any(|v| connected.is_disjoint(v)) {
            return Err(reject(
                "complexity",
                "Disconnected Cartesian products are not supported",
            ));
        }
        for filter in &plan.filters {
            let var = variable(&filter.variable)?;
            let possible = types
                .get(&filter.variable)
                .ok_or_else(|| reject("variable", "Filter variable is unbound"))?;
            if !compatible(possible, &filter.value.datatype) || ill_typed.contains(&filter.variable)
            {
                return Err(reject(
                    "datatype",
                    "Filter has mixed, incompatible or ill-typed graph values",
                ));
            }
            if !matches!(filter.op, Compare::Eq | Compare::Ne)
                && !numeric(&filter.value.datatype)
                && ![format!("{XSD}date"), format!("{XSD}dateTime")]
                    .contains(&filter.value.datatype)
            {
                return Err(reject(
                    "operator",
                    "Ordering is limited to numeric and temporal literals",
                ));
            }
            body.push_str(&format!(
                "FILTER ({var} {} {})\n",
                filter.op.sparql(),
                filter.value.literal()?
            ));
        }
        let mut outputs = BTreeSet::new();
        let mut plain = BTreeSet::new();
        let mut aggregates = BTreeMap::new();
        let mut selection = Vec::new();
        for projection in &plan.projection {
            let (input, output, expression) = match projection {
                Projection::Variable { name } => {
                    plain.insert(name.clone());
                    (name, name, variable(name)?)
                }
                Projection::CountDistinct {
                    variable: name,
                    alias,
                } => {
                    if types.contains_key(alias) {
                        return Err(reject(
                            "aggregation",
                            "Aggregate alias overlaps a bound variable",
                        ));
                    }
                    let count = format!("COUNT(DISTINCT {})", variable(name)?);
                    aggregates.insert(alias.clone(), count.clone());
                    (name, alias, format!("({count} AS {})", variable(alias)?))
                }
            };
            if !types.contains_key(input) || !outputs.insert(output.clone()) {
                return Err(reject(
                    "projection",
                    "Unbound projection or duplicate output name",
                ));
            }
            selection.push(expression);
        }
        let groups: BTreeSet<_> = plan.group_by.iter().cloned().collect();
        if groups.len() != plan.group_by.len()
            || aggregates.len() > 4
            || (aggregates.is_empty() && (!groups.is_empty() || !plan.having.is_empty()))
            || (!aggregates.is_empty() && groups != plain)
        {
            return Err(reject(
                "aggregation",
                "GROUP BY must exactly match nonaggregated projections",
            ));
        }
        let mut tail = String::new();
        if !groups.is_empty() {
            let groups = groups
                .iter()
                .map(|v| variable(v))
                .collect::<Result<Vec<_>>>()?;
            tail.push_str(&format!("GROUP BY {}\n", groups.join(" ")));
        }
        let mut having_conditions = Vec::new();
        for having in &plan.having {
            let count = aggregates.get(&having.alias).ok_or_else(|| {
                reject("aggregation", "HAVING requires a projected distinct count")
            })?;
            having_conditions.push(format!("({count} {} {})", having.op.sparql(), having.value));
        }
        if !having_conditions.is_empty() {
            tail.push_str(&format!("HAVING {}\n", having_conditions.join(" ")));
        }
        let order = outputs
            .iter()
            .map(|v| variable(v))
            .collect::<Result<Vec<_>>>()?
            .join(" ");
        tail.push_str(&format!("ORDER BY {order}\n"));
        let base = format!(
            "SELECT DISTINCT {} WHERE {{\n{body}}}\n{tail}",
            selection.join(" ")
        );
        let query = format!("{base}LIMIT {}", plan.limit + 1);
        // Restrict witnesses to actually selected rows/groups, then recover contributing BGP matches.
        let selected = format!("{{ {base}LIMIT {} }}", plan.limit);
        let branches: Vec<_> = triples.iter().map(|(s, p, o, g)| {
            format!("{{ {selected}\n{body}BIND({s} AS ?__s) BIND({p} AS ?__p) BIND({o} AS ?__o) BIND({g} AS ?__g) }}")
        }).collect();
        let evidence_query = format!(
            "SELECT DISTINCT ?__s ?__p ?__o ?__g WHERE {{ {} }} ORDER BY ?__g ?__s ?__p ?__o LIMIT {}",
            branches.join(" UNION "), policy.max_evidence + 1);
        Ok(CompiledPlan {
            query,
            evidence_query,
            catalog_digest: catalog.digest,
        })
    }
}
