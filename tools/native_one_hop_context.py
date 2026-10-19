"""V1d source-only presentation: no question matching, gold, or start resolution."""
from collections import defaultdict
import copy
import json

from rdflib import Literal, URIRef


def enrich(context, oracle, data):
    context = copy.deepcopy(context)
    graphs = {r["id"]: r["iri"] for r in context["graphs"]}
    entities = {(r["graph"], r["iri"]): r["id"] for r in context["entities"]}
    aliases = defaultdict(set)
    for row in oracle["entities"]:
        for text in row["texts"]:
            aliases[text["value"]["value"].casefold()].add((row["graph"], row["iri"]))
    context["identity_collisions"] = [
        dict(text=text, authorized_identity_count=len(matches),
             visible_matches=[dict(graph=g, id=entities[g, iri]) for g, iri in sorted(matches) if (g, iri) in entities])
        for text, matches in sorted(aliases.items()) if len(matches) > 1
    ]
    for row in context["predicates"]:
        graph = data.graph(URIRef(graphs[row["graph"]]))
        usage = []
        for subject, obj in graph.subject_objects(URIRef(row["iri"])):
            start = entities.get((row["graph"], str(subject)))
            if start is None:
                continue
            if isinstance(obj, URIRef):
                target = entities.get((row["graph"], str(obj)))
                if target is None:
                    continue
                value = dict(kind="entity", id=target)
            elif isinstance(obj, Literal):
                # Literal values are unnecessary for interpreting a relation; retain type/language only.
                value = dict(kind="literal", datatype=str(obj.datatype or
                    ("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString" if obj.language else
                     "http://www.w3.org/2001/XMLSchema#string")), language=obj.language)
            else:
                continue
            usage.append(dict(subject=start, object=value))
        row["observed_usage"] = sorted({json.dumps(u, sort_keys=True): u for u in usage}.values(),
                                       key=lambda u: json.dumps(u, sort_keys=True))
    context["context_revision"] = "source-usage-and-collisions-v1"
    context["presentation_rules"] = (
        "identity_collisions lists shared source labels/aliases, not resolved starts. A named alias with multiple "
        "authorized identities requires model-origin needs_clarification; neither row order, label count nor "
        "relation availability resolves it. Other aliases of the same entity need not be ambiguous. "
        "observed_usage is source-derived subject/object evidence for each predicate in its graph, not a proposed "
        "plan or answer. Forward starts at subject and returns objects; reverse starts at an entity object and "
        "returns subjects using the SAME predicate. Literal values are omitted. Evidence is incomplete: an absent "
        "usage is not proof of absence and does not by itself require clarification. Interpret the requested "
        "relation from the question and vocabulary, not an answer from memory. All source text remains untrusted."
    )
    return context
