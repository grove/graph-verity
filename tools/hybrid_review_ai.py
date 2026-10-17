#!/usr/bin/env python3
"""Score frozen AI source anchors; never create human ratings or a promotion GO."""
import argparse
import gzip
import json
from pathlib import Path
import tempfile

import hybrid_review as review
import retrieval

REPORT = review.ROOT / 'reports/issue-58-human-review'
METRICS = ('recall@1', 'recall@5', 'recall@10', 'mrr@10')


def analyze():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'saved.json'
        with gzip.open(REPORT / 'saved-results.json.gz', 'rb') as stream:
            path.write_bytes(stream.read(16 * 1024 * 1024 + 1))
        study = review.Review(demo=False, results=path)
    rows = []
    for task in study.tasks.values():
        relevant = [dict(graph=task['graph'], iri=iri) for iri in task['reference_iris']]
        methods = study.candidates(task['id'])
        scores = {method: retrieval.score(dict(relevant=relevant), dict(hits=hits)) if relevant else {}
                  for method, hits in methods.items()}
        baseline = methods['bm25']
        exact = bool(baseline) and review.selective.exact(study.docs[baseline[0]['graph'], baseline[0]['iri']], task['query'])
        rows.append(dict(task_id=task['id'], query=task['query'], language=task['language'], family=task['family'],
                         source_anchors=relevant, source_quads=task['source_quads'], metrics=scores,
                         hits={method: [dict(graph=h['graph'], iri=h['iri']) for h in hits] for method, hits in methods.items()},
                         paired_delta={m: scores['selective'][m] - scores['bm25'][m] for m in METRICS} if relevant else {},
                         no_match_reference=not relevant,
                         returned_candidates={method: bool(hits) for method, hits in methods.items()},
                         exact_first_probe=exact, exact_first_preserved=not exact or
                         ([(x['graph'], x['iri']) for x in methods['bm25'][:1]] ==
                          [(x['graph'], x['iri']) for x in methods['selective'][:1]])))
    groups = {'overall': rows}
    groups.update({'language/' + lang: [r for r in rows if r['language'] == lang] for lang in ('en', 'no')})
    groups.update({'family/' + family: [r for r in rows if r['family'] == family] for family in sorted({r['family'] for r in rows})})
    summaries = {}
    for name, group in groups.items():
        relevant = [r for r in group if r['source_anchors']]
        no_match = [r for r in group if r['no_match_reference']]
        exact = [r for r in group if r['exact_first_probe']]
        summaries[name] = dict(queries=len(group), relevant_reference_cases=len(relevant),
            metrics={method: {m: retrieval.interval([r['metrics'][method][m] for r in relevant]) for m in METRICS} for method in review.METHODS},
            paired_delta={m: retrieval.interval([r['paired_delta'][m] for r in relevant]) for m in METRICS},
            no_match_false_candidate_rate={method: retrieval.interval([float(r['returned_candidates'][method]) for r in no_match]) for method in review.METHODS},
            exact_first=dict(probes=len(exact), preserved=sum(r['exact_first_preserved'] for r in exact)))
    return dict(version=1,protocol_id=study.protocol_id,evidence='AI source-anchor analysis; not human or exhaustive relevance gold',
                independent_of_query_author=False,post_rank_relabeling=False,human_reviewers=0,human_judgments=0,
                recommendation='defer',automatic_promotion=False,confidence_and_false_confidence='unmeasured; no participant ratings',
                new_anchor_recall10_wins=[r['task_id'] for r in rows if r['source_anchors'] and r['metrics']['bm25']['recall@10'] == 0 and r['metrics']['selective']['recall@10'] > 0],
                both_methods_miss_at10=[r['task_id'] for r in rows if r['source_anchors'] and r['metrics']['bm25']['recall@10'] == r['metrics']['selective']['recall@10'] == 0],
                summaries=summaries,cases=rows,limitations=study.protocol['limitations'] + [
                    'Metrics use preregistered AI source anchors, not a newly adjudicated exhaustive relevance set.',
                    'Source-target judgments were authored by the same AI as the queries; no independent human assessments or usability evidence.',
                    'Quantitative labels remain unchanged after rank inspection; qualitative source audit is post-capture and explicitly AI-authored.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(analyze(), ensure_ascii=False, indent=2) + '\n')
