# Frozen #58 review: operator and reviewer handoff

Engineering handoff complete **does not mean two independent consenting people
have completed the study**. Actual human reviewers and judgments remain **0**.
Keep #58 open. This does not complete #57's separate gate, authorize an opt-in
feature or promote hybrid retrieval. Shipping BM25 and Confirmed Ask are unchanged.

The source is pinned to completed #64 main commit
`ba9e57f8574ebf2c28797a98004dd6fbda61abfe`; protocol ID:
`6223e88dbca50cbc9e09b3eb8c0fa4034fe4f55ba8405e66318b37a633c84354`.
The launcher exports a **content-equivalent, checksummed offline kit**, then runs
only that read-only source in an isolated Python process. Evolving main is never
imported. All 30 original freeze inputs remain byte-for-byte unchanged. Any hash
failure stops the handoff: investigate, never repair a frozen file in place. A
changed protocol requires a separately versioned preregistration.

## Operator: prepare once, without enrolling anyone

Requirements: Python **3.11+ on macOS/Linux**, a local graphical browser and about
15 MiB of additional disk space. Windows is unsupported because the frozen code
imports Unix `resource`. No pip, package manager, Rust build, model weights,
Torch, login, remote service or new inference is needed. Git and the pinned commit's
objects must be available locally for the **first export only**. A normal fresh
clone containing that commit suffices; a shallow clone that lacks it fails with
a precise blocker. Obtain missing source before going offline.

From the repository root, with networking disabled:

```sh
python3 tools/hybrid_review_launcher.py prepare
```

This creates ignored `study-private/hybrid/source/` (directories 0500, files 0400)
and decompresses the **committed** `saved-results.json.gz` into
`study-private/hybrid/results.json` (0600). Private directories are 0700. Existing
private directories with broader permissions cause a stop: inspect them, then
explicitly `chmod 700 study-private study-private/hybrid` if appropriate. No
capture or participant file is replaced. Missing captures alongside existing
sessions also stop. Interrupted exports remain untrusted and are not resumed.

[manifest.json](manifest.json) records 39 exact paths, sizes and SHA256 hashes:
14,368,653 bytes (13.70 MiB), plus the 354,075-byte decompressed capture. The
launcher pins the manifest's own SHA256. Besides the 30 verification-required
inputs, the export contains the freeze file, archived capture, repository license
EEA/W3C attribution/license notices and the three existing Local Find assets
loaded by the shared server before the reviewer assets replace them. Original graph-qualified RDF and the
historical document/index export are retained. Frozen vectors/rank regressions are
included because the original verifier hashes them; they are not model weights
and are not used for new inference. No AI analysis/source-anchor report is added.

Capture archive SHA256:
`d1b62739104c107ed1096f956183625b0f7ffaafa35b26227517cc234f746467`.
Decompressed capture SHA256:
`35cc76babe8e3ba0d24379cbcc6c02ac6d8b0c733021e5f317fc3cae475cc6d4`.
The frozen verifier also checks the source/task lineage and replays the saved
ranks against the pinned snapshot, index manifest, scope and authorized catalog.

For an **offline handoff without Git**, copy only these prepared paths to the
same relative locations in a fresh directory, preserving permissions:

```text
tools/hybrid_review_launcher.py
studies/hybrid-review-handoff/manifest.json
studies/hybrid-review-handoff/README.md
study-private/hybrid/source/
```

Do this **before any participant session**. Do not copy `results.json`, reviewer
files, reports or locks; the launcher recreates the capture from the verified
archive. These public inputs contain no participant records. Run the same
`prepare` command on the recipient machine, offline. Copy the launcher from the
reviewed PR/revision through a trusted handoff; hashes detect content changes,
not malicious replacement of both the launcher and its manifest. Do not execute
code from the frozen kit directly or change its permissions to update it.

## Operator: one launch per actual person

First explain the reviewer instructions below and obtain actual informed consent.
Independence is a human requirement: software cannot establish that two IDs are
two distinct people. Do not create two sessions for one person or generate ratings.
Keep the operator's seeds, saved ranks, task anchors and reports away from reviewers
until they submit; do not expose the repository as a way to review the sources.

```sh
# Person 1, only after their consent:
python3 tools/hybrid_review_launcher.py launch --reviewer 01 --kind independent --consent
# Stop with Ctrl-C; then person 2, only after their separate consent:
python3 tools/hybrid_review_launcher.py launch --reviewer 02 --kind independent --consent
```

Each command opens the browser locally and creates a fresh random ID/seed in
`reviewer-01.json` or `reviewer-02.json`. Existing session files cannot be reopened,
replayed or overwritten. The operator lock permits only one launcher at a time.
After an abrupt process crash, remove `.operator-lock` **only after confirming
that no launcher/worker remains running**. Preserve partial sessions and report
missing tasks; do not manufacture completion or relaunch an unblinded reviewer.

Optional owner review is explicitly separate:

```sh
python3 tools/hybrid_review_launcher.py launch --reviewer owner --kind owner --consent
```

For software rehearsal, use `launch --reviewer rehearsal --kind rehearsal`.
This uses the saved new-task ranks, always labeled rehearsal. The old
`hybrid_review.py serve --demo` instead uses **exposed regressions** and cannot be
mixed into this handoff or counted as independent evidence. No independent or
owner record is created by `prepare` or by tests in the working study directory.

Only `127.0.0.1` is bound; there is no LAN/proxy/tunnel/public-URL option. The
existing Host/Origin/credentials, session lease, inert source display, blinded A/B,
validation and atomic save-before-reveal protections are reused. New tabs revoke
old leases; a submitted task cannot be judged again. The launcher opens the
capability URL directly in the local browser and never prints it. Keep the
browser/profile private: do not copy URLs/cookies/tokens into logs, Git, chat or
screenshots. There is no upload or analytics. If browser opening fails, preserve
the private session and diagnose locally; do not replace it with a new identity.

## Reviewer: consent and source interpretation

Participation is voluntary and exploratory. You may skip a case, stop or withdraw
without giving a reason. No similarity result establishes a fact. The local
operator retains only a random anonymous ID, structured ratings, consent and a
private randomization seed; no name, email or free text is requested. Before
consent, agree with the operator on a retention/deletion date and how to request
withdrawal. No date or approval is fabricated by the tool. Records stay on this
machine until that date or earlier withdrawal, and only human-approved anonymous
aggregates may later be disclosed.

For each task, before submitting:

1. Confirm the displayed snapshot, authorized graph, role, language and top 10.
   Inspect **original graph-qualified IRIs and predicates**, relation direction,
   label language/datatype and RDF witnesses. Clipped witnesses are explicitly
   marked; if they prevent assessment, exclude the case.
2. Mark relevance for **every unique displayed candidate** in A/B. Inspect shared
   identities once. Assess direction, scope, exact-first behavior and ambiguity;
   give honest confidence and preference. Do not infer relevance from list order.
3. Search the **authorized catalog**, inspect sources for plausible **off-list**
   resources, and select any additional relevant identities. Returned lists alone
   cannot establish the exhaustive retrievable relevance set.
4. Select no-match **only if no retrievable resource in that authorized role and
   graph is relevant**. Absence from the lists, missing real-world facts and lack
   of an exact label are not no-match evidence.
5. Distinguish uncertainty/exclusion from a negative result. Use an exclusion when
   unable to assess; do not guess. Incomplete forms fail validation. Submission
   saves once, then reveals A/B; neither method labels nor AI source anchors are
   disclosed beforehand. Do not discuss judgments with the other reviewer first.

For withdrawal: stop the server, close the private browser tabs/profile, delete
the person's `study-private/hybrid/reviewer-XX.json` and any local copies/backups,
and delete/recompute any report derived from it. Never reuse their ID/filename to
claim another independent person. Deletion is an explicit operator action, not a
server endpoint. Do not disclose anything until withdrawal/retention arrangements
and anonymization have been reviewed by a human.

## Operator: private report and disclosure

```sh
# Requires both named session files; never invents a missing reviewer:
python3 tools/hybrid_review_launcher.py report
# After withdrawal, or to inspect a partial/owner/rehearsal report, list only retained files:
python3 tools/hybrid_review_launcher.py report reviewer-01.json reviewer-owner.json
```

This invokes the frozen `hybrid_review.py report` and atomically writes only
`study-private/hybrid/report.json` (0600). The default requires both files; an
explicit list can represent incomplete participation. Duplicate reviewer IDs or
seeds, other protocols/captures and exposed-demo records fail. No participant
record, approval or publication is created. The raw report is private and
contains reviewer-linked judgments; **do not publish it**.

Before any separate human-approved disclosure:

- Separate independent, owner, rehearsal and historical AI evidence; state actual
  people/judgment counts truthfully. Two files alone are not proof of independence.
- Preserve missing tasks, exclusions, disagreements and uncertainty. Do not vote
  away disagreements or silently replace records. Lack of consensus stays unscored.
- Inspect consent/withdrawal/retention arrangements; remove withdrawn records and
  stale reports/backups. Keep random IDs, seeds, paths, forms and case-level linked
  ratings private. Approve a separately anonymized aggregate explicitly by a human.
- Disclose the small convenience sample, shared targets/languages, exploratory
  descriptive intervals and other frozen limitations. Keep #58 open until genuine
  adjudication; engineering tests and the #64 startup evidence do not satisfy it.
- No publication, opt-in release or default promotion is authorized here.

## Development verification

```sh
python3 -m unittest discover -s tools -p test_hybrid_review_launcher.py -v
REQUIRE_FIND_BROWSER=1 python3 -m unittest discover -s tools -p test_hybrid_review.py -v
# Existing reference dependencies/toolchain are needed for development CI only:
REQUIRE_FIND_BROWSER=1 .venv/bin/python tools/verify_pre_llm.py
```

Tests use temporary synthetic/rehearsal fixtures only. They exercise export hashes,
missing/changed sources, capture identity/protocol, isolated model-free/offline
loading, consent, fresh identities/seeds, replay protection, private permissions
and reporting. The unchanged frozen suite covers incomplete forms, catalog/no-match
validation, disagreements/exclusions, stale tabs, one-shot reveal, keyboard and
browser/no-external-request protections. These tests create no human evidence.
