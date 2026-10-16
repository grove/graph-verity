//! Version 1 is deliberately small: graph-scoped conjunctions and distinct counts.
use crate::{reject, Result};
use oxigraph::model::{Literal, NamedNode};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

pub const XSD: &str = "http://www.w3.org/2001/XMLSchema#";
pub const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
pub const LANG_STRING: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub version: u32,
    pub snapshot_id: String,
    pub scope: Vec<String>,
    pub patterns: Vec<Pattern>,
    pub filters: Vec<Filter>,
    pub projection: Vec<Projection>,
    pub group_by: Vec<String>,
    pub having: Vec<Having>,
    pub limit: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Pattern {
    pub graph: String,
    pub from: Node,
    pub predicate: String,
    pub direction: Direction,
    pub to: Node,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Direction { Forward, Reverse }

impl Pattern {
    pub fn ends(&self) -> (&Node, &Node) {
        match self.direction {
            Direction::Forward => (&self.from, &self.to),
            Direction::Reverse => (&self.to, &self.from),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Node {
    Variable { name: String },
    Iri { iri: String },
    Literal { value: Value },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Value {
    pub lexical: String,
    pub datatype: String,
    pub language: Option<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Compare { Eq, Ne, Lt, Le, Gt, Ge }

impl Compare {
    pub fn sparql(self) -> &'static str {
        match self {
            Self::Eq => "=", Self::Ne => "!=", Self::Lt => "<",
            Self::Le => "<=", Self::Gt => ">", Self::Ge => ">=",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Filter { pub variable: String, pub op: Compare, pub value: Value }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Projection {
    Variable { name: String },
    CountDistinct { variable: String, alias: String },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Having { pub alias: String, pub op: Compare, pub value: u32 }

pub fn decode_plan(bytes: &[u8]) -> Result<Plan> {
    if bytes.len() > 65_536 { return Err(reject("input_limit", "IR exceeds 64 KiB")); }
    Ok(serde_json::from_slice(bytes)?)
}

pub(crate) fn variable(name: &str) -> Result<String> {
    let mut chars = name.chars();
    if name.len() > 32 || !chars.next().is_some_and(|c| c.is_ascii_alphabetic())
        || !chars.all(|c| c.is_ascii_alphanumeric() || c == '_') {
        return Err(reject("variable", "Variables must match [A-Za-z][A-Za-z0-9_]{0,31}"));
    }
    Ok(format!("?{name}"))
}

pub(crate) fn iri(value: &str) -> Result<String> {
    if value.len() > 2048 { return Err(reject("iri", "IRI exceeds 2048 bytes")); }
    NamedNode::new(value).map(|n| n.to_string()).map_err(|_| reject("iri", "Invalid absolute IRI"))
}

pub(crate) fn numeric(datatype: &str) -> bool {
    ["integer", "decimal", "double"].iter().any(|t| datatype == format!("{XSD}{t}"))
}

impl Value {
    /// Conservative lexical subset. Unsupported or ill-typed values never enter SPARQL text.
    pub fn literal(&self) -> Result<Literal> {
        if self.lexical.len() > 4096 { return Err(reject("literal", "Literal exceeds 4096 bytes")); }
        if self.datatype == LANG_STRING {
            let language = self.language.as_deref().ok_or_else(|| reject("datatype", "Language required"))?;
            return Literal::new_language_tagged_literal(&self.lexical, language)
                .map_err(|_| reject("datatype", "Invalid language tag"));
        }
        if self.language.is_some() { return Err(reject("datatype", "Language requires rdf:langString")); }
        let local = self.datatype.strip_prefix(XSD).ok_or_else(|| reject("datatype", "Unsupported datatype"))?;
        let s = self.lexical.as_str();
        let valid = match local {
            "string" => true,
            "boolean" => matches!(s, "true" | "false" | "1" | "0"),
            "integer" => s.parse::<i64>().is_ok(),
            "decimal" => {
                let digits = s.strip_prefix('-').or_else(|| s.strip_prefix('+')).unwrap_or(s);
                !digits.is_empty() && digits.chars().any(|c| c.is_ascii_digit())
                    && digits.chars().all(|c| c.is_ascii_digit() || c == '.')
                    && digits.matches('.').count() <= 1 && digits.len() <= 18
            }
            "double" => s.parse::<f64>().is_ok_and(f64::is_finite),
            "date" => s.len() == 10 && chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d").is_ok(),
            "dateTime" => chrono::DateTime::parse_from_rfc3339(s).is_ok(),
            _ => false,
        };
        if !valid { return Err(reject("datatype", "Unsupported or ill-typed literal")); }
        let datatype = NamedNode::new(&self.datatype).map_err(|_| reject("datatype", "Invalid datatype IRI"))?;
        Ok(Literal::new_typed_literal(&self.lexical, datatype))
    }
}

impl Node {
    pub(crate) fn sparql(&self) -> Result<String> {
        match self {
            Self::Variable { name } => variable(name),
            Self::Iri { iri: value } => iri(value),
            Self::Literal { value } => Ok(value.literal()?.to_string()),
        }
    }
}
