# omni-agents-framework

OmniBrain: the orchestrator of the `blassana280-ux` agent network.

It classifies a request, picks the specialists that must handle it, dispatches
them **in parallel**, verifies their output against gates, arbitrates
contradictions, asks for corrections, and assembles one deliverable — with a
trace of every decision.

Pure Python 3.11 standard library. No third-party dependency, no committed
secret, no hidden network call.

```bash
python3 -m omni registry                      # is the network coherent?
python3 -m omni providers                     # what can actually execute? (truthful PATH probe)
python3 -m omni plan "Ajoute un endpoint REST et une interface React"
python3 -m omni run  "Ajoute un endpoint REST" --workspace /tmp/demo
python3 -m unittest discover -s tests -t .    # 63 tests, no network needed
```

## What really works today

Every line below is backed by an executed test or a real command output, not by
an intention.

| Capability | Status | Evidence |
|---|---|---|
| Registry integrity (agents ↔ skills ↔ specialties ↔ permissions) | **works** | `python3 -m omni registry` → *no dangling reference*; `test_routing.py::TestRegistryIntegrity` |
| Deterministic classification (simple / medium / complex) | **works** | `test_routing.py` scenarios 1–2 |
| Squad formation + wave ordering (review after work) | **works** | `test_orchestration.py::TestParallelExecution` |
| Real parallel dispatch (`ThreadPoolExecutor`, measured wall time) | **works** | wave trace `wall_s` vs `serial_s` in `test_wave_is_parallel_not_sequential` |
| Failure handling: retry → reassign to fallback → escalate | **works** | `TestFailureRecovery` (3 tests) |
| Arbitration of contradictory results | **works** | `TestArbitration` (2 tests, incl. unresolved tie → `NEEDS_WORK`) |
| Correction loop for incomplete deliverables | **works** | `TestCorrectionLoop` (2 tests) |
| Traceability (run JSON + JSONL trace + shared verdict) | **works** | `TestTraceability` |
| Controlled shared memory with secret redaction + TTL | **works** | `test_policy_memory_messaging.py` |
| Agent-to-agent message bus (run-scoped, validated peers) | **works** | `test_policy_memory_messaging.py::TestMessageBus` |
| Permission model (tool grants, deny paths, dangerous actions) | **works** | `TestPolicy` |
| Git: work branch + commit without touching `main` | **works** | real temp repo, `test_gitops.py::TestGitWorkflow` |
| GitHub: PR command construction/execution via `gh` | **works** | `TestPullRequestCommands` + the PR that introduced this file |
| Branch-protection **probe** | **works but limited** | returns `insufficient_permission` for this token (real `gh api` output, `OMNI_LIVE=1`) |
| Branch-protection **apply** | **blocked** | needs `Administration: write`; the CLI prints the exact `gh api` call to run |
| Account-wide `AGENTS.md` repair (`omni overlays`) | **plan works, apply blocked** | live plan: 10 `restore+overlay` + 28 `refresh` on 41 repos (`docs/OVERLAYS-PLAN.md`, with sha256 of each planned file); `--apply` → `blocked: cannot create blob (write access missing)` |
| Write pipeline itself | **works** | commit `76b281f8cb` created through `omni.overlays.apply` on the one writable repo, throwaway branch deleted afterwards |
| AI agent **execution** | **not configured** | no agent CLI found on PATH; `OMNI_PROVIDER_CMD` unset → briefs are handed to a human (`pending_human`, `executed=False`) |

Two limits are environmental, not architectural: this session's GitHub token can
write to **one** repository only (see `docs/INTEGRATIONS.md` §4), and no AI CLI is
installed here.

The provider line is the important one: this repository orchestrates *real* work only
when a real provider is attached. Until then a run ends in `NEEDS_WORK` and says
so. Nothing here pretends an agent ran.

## Attaching a real provider

```bash
export OMNI_PROVIDER_CMD='claude -p {prompt}'   # or codex, gemini, kilo, aider…
export OMNI_PROVIDER_NAME=claude
python3 -m omni providers                       # verify the CLI is actually found
python3 -m omni run "…"                         # now executed=True
```

`{prompt}` and `{brief_file}` are substituted with the agent's brief. The exit
code decides success; stdout/stderr are captured as evidence. Credentials stay
in your environment — never in this repository.

## Layout

```
registry/            agents.json · skills.json · routing.json · permissions.json
omni/
  models.py          dataclasses for tasks, briefs, results, runs
  registry.py        loading + integrity validation
  routing.py         classification, agent selection, squad + wave planning
  orchestrator.py    waves, failures, corrections, arbitration, assembly
  executor.py        SubprocessProvider (real) · ManualProvider (honest no-op)
  policy.py          tool grants, deny paths, dangerous-action confirmation
  memory.py          namespaced shared memory, redaction, TTL
  messaging.py       run-scoped agent mailbox
  validation.py      the six gates and the final verdict
  gitops.py          git/PR operations with safety rails
  audit.py           reproducible GitHub account audit
  cli.py             python3 -m omni …
tests/               63 tests: orchestration, gitops, policy, memory, audit
docs/                architecture · GitHub audit · integrations
OMNIBRAIN.md         the orchestrator's authoritative specification (FR)
```

## Design rules

1. **No fake integration.** A capability is either measured or reported missing.
2. **No secrets in the repo.** Environment only; delivered text is scanned and redacted.
3. **No writes to `main`.** GitOps refuses; `main` is always reached through a PR.
4. **Evidence over assertion.** A result without evidence fails the gate.
5. **Reuse before creation.** 20 agent profiles, 30 skills, all pointing at
   existing repositories (`provenance` field), verified against the live API.

## License

Apache-2.0 (see `LICENSE`).
