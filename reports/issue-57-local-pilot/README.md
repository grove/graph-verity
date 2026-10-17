# Issue #57 — local pilot status

**Stage A: frozen study kit. Stage B: BLOCKED pending real volunteers; #57 stays open.**

Actual participants **0 / proposed 5–8**. Human task attempts **0**; planned
participant-task assignments **0** (no enrollment). There are **20 task templates**,
not 20 human attempts. Completed/abandoned human tasks **0 / 0**. Independent
human task reviewers **0**. No recruitment or observation has occurred.
Human success, selection errors, misunderstanding, confident wrong interpretations
and relevance are **unmeasured**, not measured zero. There are no observed human
failures or qualitative findings to summarize, and no per-language/experience
human comparisons can be made yet.

The [preregistered protocol, task/source lineage and operator checklist](../../studies/pilot-v1/README.md)
cover Wikidata, GeoNames-derived Schema.org and separately identified synthetic
ambiguity/shared-path fixtures. GEMET is outside this first bounded pilot.
All judgments are AI-authored exploratory references with null human reviewers.
Real operator assessments must carry truthful local owner/independent attribution;
source witnesses and passing software tests cannot substitute for human assessment.

The model-free offline rehearsal creates **1 synthetic session**, with 20 planned
task slots, 2 synthetic attempts, 1 abandonment, 1 missing record and 1 deliberately
confident wrong interpretation. It reports **0 human participants and 0 human
attempts**. These numbers validate form/rubric/report behavior only. Reproduce with:

```sh
python3 tools/pilot_study.py verify
python3 tools/pilot_study.py rehearse --out artifacts/pilot-rehearsal.json
python3 -m unittest discover -s tools -p 'test_pilot_study.py' -v
```

Choose a fresh output filename on repeat; existing files are not overwritten.
Full verification uses `.venv/bin/python tools/verify_pre_llm.py`, including the
application HTTP/browser security regressions. CI receipts belong to the PR and
are engineering evidence, not user observations. No model inference or private
Ask holdout access is part of these commands. Earlier #37–#53 reports and phase-0
decisions are unchanged.

**Recommendation: defer any proposed product release decision pending actual
consenting sessions and investigation of observed problems.** Keep BM25 default,
the local UI experimental and #57 open. After real observations, report actual
task/participant denominators, exclusions, assistance, language/experience/task-type
breakdowns and actionable UI/vocabulary problems, then separately recommend UX
changes, expert scope, retrieval iteration or stopping a proposed release. Do not
retrospectively change the preregistered hypotheses or infer safety from no observed
error. No unattended Ask, hybrid rollout or production GO is authorized.

Local forms and reports stay in Git-ignored `study-private/`; raw queries, quotes,
recordings, private RDF, tokens and individual sensitive data cannot enter the
strict form schema. Only disclosure-reviewed nonidentifying aggregates may later
be published. Retention/deletion and withdrawal procedures are in the consent kit.
