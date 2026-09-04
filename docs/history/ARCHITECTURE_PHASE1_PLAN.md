# Architecture Phase 1 Work Order

## Goal

Reduce the highest-risk coupling and contract drift while preserving the current
Streamlit/PyWebView user experience and existing workspace compatibility.

## Work

1. Introduce a versioned, dict-compatible analysis result envelope and a single
   method catalog used to resolve canonical IDs and aliases across execution,
   result-card, table, and exposure routing.
2. Add contract validation and regression tests covering every registered
   analysis method and every result-card builder.
3. Introduce a session-state port with Streamlit and plain-dict adapters; make
   workspace snapshot/restore accept an injected session state while preserving
   the existing no-argument API.
4. Make project index and workspace JSON writes atomic and retain the existing
   on-disk schema and migration behavior.
5. Consolidate the active LLM configuration path, make `.env.local` discovery
   portable/configurable, and remove the unused YAML provider catalog.
6. Replace silent failure in touched critical paths with structured logging.
7. Harden Git hygiene for runtime databases, fetched literature, performance
   history, secrets, generated reports, and coverage artifacts. Keep templates,
   demo data, and literature weighting configuration versioned.
8. Document the resulting architecture and migration boundaries.

## Bounds

- No UI redesign, FastAPI split, microservices, or cloud deployment.
- No intentional change to statistical calculations or visible user workflows.
- Existing workspace JSON files must continue to load.
- Existing public function signatures remain compatible; new injection points
  use optional keyword parameters or dict-compatible return types.
- Do not delete local runtime data merely to exclude it from GitHub.
- Do not commit or push until the human reviews the completed diff.

## Proof

```powershell
python -m pytest -m "not online and not benchmark and not e2e and not playwright" -q
```

Additionally run focused contract, workspace, project-manager, LLM, and delivery
tests while iterating.
