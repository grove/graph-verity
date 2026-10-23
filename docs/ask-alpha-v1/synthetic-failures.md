# Retained Ask draft evaluation

Origin: **synthetic_fixture**. INCONCLUSIVE_REVISE.
No model invoked; no draft executed. Human comprehension unmeasured.

## synthetic_five_field

```json
{
  "scheduled": 60,
  "completed_latency": {
    "samples": 0,
    "p50_ms": null,
    "p95_ms": null,
    "p99_ms": null
  },
  "outcomes": {
    "completed": 58,
    "timed_out": 1,
    "unattempted": 1
  },
  "five_field_scheduled": {
    "numerator": 24,
    "denominator": 29
  },
  "five_field_completed": {
    "numerator": 24,
    "denominator": 28
  },
  "fields": {
    "start": {
      "numerator": 26,
      "denominator": 29
    },
    "predicate": {
      "numerator": 25,
      "denominator": 29
    },
    "graph": {
      "numerator": 26,
      "denominator": 29
    },
    "direction": {
      "numerator": 26,
      "denominator": 29
    },
    "output": {
      "numerator": 27,
      "denominator": 29
    }
  },
  "clarification": {
    "numerator": 19,
    "denominator": 23
  },
  "unsupported": {
    "numerator": 8,
    "denominator": 8
  },
  "false_clarification": 1,
  "false_unsupported": 0,
  "wrong_but_executable": {
    "numerator": 2,
    "denominator": 27
  },
  "wrong_but_executable_scheduled": {
    "numerator": 2,
    "denominator": 60
  },
  "unresolved_candidates": 1,
  "unjustified_relationship_selections": 3,
  "retrieval": {
    "numerator": 28,
    "denominator": 29
  },
  "rust": {
    "accepted": 55,
    "not_measured": 2,
    "rejected": 3
  },
  "source_evidence": {
    "numerator": 1,
    "denominator": 1
  }
}
```

| Case | Outcome | Problem |
|---|---|---|
| alpha-01 | completed | fields: predicate; WRONG BUT EXECUTABLE |
| alpha-02 | timed_out | timed_out |
| alpha-04 | unattempted | unattempted |
| alpha-05 | completed | invalid draft; Rust rejected |
| alpha-06 | completed | invalid draft; Rust rejected |
| alpha-07 | completed | fields: direction; WRONG BUT EXECUTABLE |
| alpha-08 | completed | unexpected model status; missing numeric start |
| alpha-25 | completed | fields: start, predicate, graph; Rust rejected |
| alpha-47 | completed | unexpected model status; guess on unresolved intent |
## synthetic_assembly

```json
{
  "scheduled": 60,
  "completed_latency": {
    "samples": 0,
    "p50_ms": null,
    "p95_ms": null,
    "p99_ms": null
  },
  "outcomes": {
    "completed": 58,
    "failed": 1,
    "unattempted": 1
  },
  "five_field_scheduled": {
    "numerator": 25,
    "denominator": 29
  },
  "five_field_completed": {
    "numerator": 25,
    "denominator": 28
  },
  "fields": {
    "start": {
      "numerator": 27,
      "denominator": 29
    },
    "predicate": {
      "numerator": 26,
      "denominator": 29
    },
    "graph": {
      "numerator": 27,
      "denominator": 29
    },
    "direction": {
      "numerator": 26,
      "denominator": 29
    },
    "output": {
      "numerator": 27,
      "denominator": 29
    }
  },
  "clarification": {
    "numerator": 19,
    "denominator": 23
  },
  "unsupported": {
    "numerator": 8,
    "denominator": 8
  },
  "false_clarification": 1,
  "false_unsupported": 0,
  "wrong_but_executable": {
    "numerator": 2,
    "denominator": 28
  },
  "wrong_but_executable_scheduled": {
    "numerator": 2,
    "denominator": 60
  },
  "unresolved_candidates": 1,
  "unjustified_relationship_selections": 2,
  "retrieval": {
    "numerator": 28,
    "denominator": 29
  },
  "rust": {
    "accepted": 56,
    "not_measured": 2,
    "rejected": 2
  },
  "source_evidence": {
    "numerator": 1,
    "denominator": 1
  }
}
```

| Case | Outcome | Problem |
|---|---|---|
| alpha-01 | completed | fields: predicate; WRONG BUT EXECUTABLE |
| alpha-03 | failed | failed |
| alpha-04 | unattempted | unattempted |
| alpha-05 | completed | invalid draft; Rust rejected |
| alpha-06 | completed | invalid draft; Rust rejected |
| alpha-07 | completed | fields: direction; WRONG BUT EXECUTABLE |
| alpha-08 | completed | unexpected model status; missing numeric start |
| alpha-47 | completed | unexpected model status; guess on unresolved intent |

Full row JSON retains raw drafts, resolved fields and exact Rust rejection text.
Unresolved dispositions are automation targets, not definitive semantic gold. Rationale claims require source audit.
Source-evidence agreement is snapshot-only; schema validity and Rust acceptance do not prove interpretation.
