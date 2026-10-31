# Architecture

## Components

```
                    ┌──────────────────────────────┐
   request ────────▶│        Orchestrator          │
                    │  (omni/orchestrator.py)      │
                    └───┬───────────┬──────────┬───┘
                        │           │          │
             classify+plan          │          └──────────────┐
                        │       dispatch                     │
                        ▼           ▼                        ▼
                ┌──────────────┐ ┌──────────────┐   ┌────────────────┐
                │    Router    │ │   Provider   │   │ ValidationEngine│
                │ routing.py   │ │ executor.py  │   │ validation.py   │
                └──────┬───────┘ └──────┬───────┘   └────────┬───────┘
                       │                │                    │
                       ▼                ▼                    ▼
                ┌──────────────┐ ┌──────────────┐   ┌────────────────┐
                │  Registry    │ │ Subprocess / │   │  6 gates       │
                │ registry.py  │ │ Manual       │   │  → verdict     │
                └──────┬───────┘ └──────────────┘   └────────────────┘
                       │
        ┌──────────────┼───────────────┬───────────────┐
        ▼              ▼               ▼               ▼
   agents.json   routing.json    skills.json    permissions.json

   cross-cutting: Policy · SharedMemory · MessageBus · Trace · GitOps
```

## Data flow of one run

1. `Orchestrator.run(request)` creates a `RunRecord` (`run_id`), a `Trace`
   (JSONL file) and opens memory + mailbox scoped to that run.
2. `Router.classify()` scores specialties from `routing.json` triggers and picks
   a size; `Router.plan()` builds tasks, chooses one agent per specialty, assigns
   waves from task dependencies and renders a self-contained `Brief` per agent
   (objective, acceptance criteria, allowed tools, boundaries, shared context).
3. Each wave goes through `ThreadPoolExecutor`. Every brief goes through
   `Policy.check(agent, "execute_task")` first; a denial becomes a recorded
   failure, never a silent skip.
4. `Provider.execute(brief)` is the only place where real work happens
   (`SubprocessProvider`) — or it explicitly refuses to pretend
   (`ManualProvider` → `pending_human`).
5. Failures trigger retry → fallback agent → escalation, each event traced.
6. Incomplete deliverables trigger a `Correction` with the missing criteria.
7. Contradictory claims are arbitrated by evidence weight; a perfect tie stays
   unresolved.
8. `ValidationEngine` runs the six gates; `verdict_for()` returns `READY` only if
   all pass.
9. `Orchestrator.deliverable()` renders one document; `RunRecord` and the trace
   are persisted under `.omni/runs/`; the verdict is published to shared memory.

## Extension points

| Goal | Where |
|---|---|
| Add a specialty | `registry/routing.json` (+ agent declaring it, else validation fails) |
| Add an agent profile | `registry/agents.json` + explicit entry in `permissions.json` |
| Add a skill / new source | `registry/skills.json` with an honest `verification` level |
| Add a squad template | `registry/routing.json` → `squad_templates` |
| Attach an LLM backend | implement `Provider` (`available` + `execute`) or set `OMNI_PROVIDER_CMD` |
| Change the gates | `omni/validation.py` (`GATES` tuple) |
| Change arbitration policy | `omni/orchestrator.py::_arbitrate` |

## Invariants enforced by code and tests

- a routing entry pointing to an unknown agent is a **validation error**
  (`test_validation_catches_broken_agent_reference`);
- an agent without an explicit permission entry is a **validation error**;
- `main`/`master` can never be committed to or pushed from the toolkit;
- `READY` without a real provider is impossible (`execution` gate);
- delivered text containing a credential-looking string fails the run;
- every task must have both a `dispatch` and a `result` trace event.

## Concurrency model

One thread pool per wave; `max_parallel` bounds it. Shared state is guarded:
`Trace.emit` takes a lock, the memory store writes atomically via
`os.replace`, the mailbox appends. Results are collected only after the pool
drains, so no result is observed half-written.
