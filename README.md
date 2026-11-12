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
python3 -m unittest discover -s tests -t .    # offline unit and integration suite
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
| AI provider **code** | **integrated; credential not provisioned here** | native Mistral provider is available, but paid inference remains locked until `OMNI_MISTRAL_ALLOW_PAID=1`; without credentials the provider remains unavailable |

Two limits are environmental, not architectural: this session's GitHub token can
write to **one** repository only (see `docs/INTEGRATIONS.md` §4), and no AI CLI is
installed here.

The provider line is the important one: this repository orchestrates *real* work only
when a real provider is attached. Until then a run ends in `NEEDS_WORK` and says
so. Nothing here pretends an agent ran.

## External skill catalog and trust controls

The external-skill catalog is separate from the legacy registry/skills.json
index. Existing skills remain usable through the existing registry API, but are
not implicitly treated as pinned, scanned, or approved.

Read-only commands:

- `python3 -m omni skills catalog`
- `python3 -m omni skills inspect <skill-id>`
- `python3 -m omni skills scan <skill-id> --snapshot-dir /path/to/local/snapshot`

The scan command accepts a local snapshot only: it does not fetch repositories,
run scripts, launch MCP servers, or change lifecycle state. A snapshot must
contain a root SKILL.md; the lock file SHA-256 must match its normalized UTF-8
file set. The default registry/skill-policy.json allows MIT and Apache-2.0,
caps snapshots at 128 files / 1 MiB, and blocks high- and critical-severity static findings.
Static pattern checks are heuristic indicators, not a malware certification.

A skill follows the explicit lifecycle:

discovered → pinned → metadata_validated → scanned → evaluated → approved → available → active

The approved transition requires a human approver, a review reference, and the
exact content digest. Only then can a record become available or active. No
catalog command can approve, install, activate, or execute a skill.

## Attaching a real provider

```bash
export OMNI_PROVIDER_CMD='claude -p {prompt}'   # or codex, gemini, kilo, aider…
export OMNI_PROVIDER_NAME=claude
python3 -m omni providers                       # verify the CLI is actually found
python3 -m omni run "…"                         # now executed=True
```

`{prompt}` and `{brief_file}` are substituted with the agent's brief.
Prefer `{brief_file}`: the randomly named temporary brief is created with
private POSIX permissions (`0600`) and removed after the provider exits,
including timeout/error paths. Do not rely on that file as a persistent
artifact. `{prompt}` passes the complete brief in the child process argument
list, which may be visible to local process-inspection tools; use the file
placeholder when that exposure is undesirable.

Provider stdout/stderr and error strings are redacted before they are returned.
Custom providers are redacted again at result ingestion, and the final assembled
deliverable is redacted before display. These controls are heuristic secret
pattern checks, not a substitute for keeping credentials out of prompts and
provider output. Credentials stay in your environment — never in this repository.

## Native Mistral API provider

OmniBrain can use Mistral directly without installing an agent CLI or adding an SDK dependency. Select it explicitly:

```bash
export OMNI_PROVIDER=mistral
export MISTRAL_API_KEY_FILE="$HOME/.config/omnibrain/mistral.key"
chmod 600 "$MISTRAL_API_KEY_FILE"
python3 -m omni providers --verify mistral   # local check only; no network request
python3 -m omni run "…"                       # remains pending_human by default
```

The key file must be a regular, non-symlink file and, on POSIX, must not grant group/other permissions. For CI or hosted execution, `MISTRAL_API_KEY` may be supplied as a protected environment secret; the private file takes precedence. Never commit either credential.

Paid inference is locked by default. Only for a run you explicitly authorize, set `OMNI_MISTRAL_ALLOW_PAID=1` in that command's environment; remove it afterwards. Each request is capped at 1,024 output tokens by default and uses `MISTRAL_MODEL` (default `mistral-small-latest`). The verification command never contacts Mistral. No API key, GitHub Actions secret, or payment setting is provisioned by this repository change.

The provider uses Mistral's official `POST /v1/chat/completions` endpoint with Bearer authentication and JSON-mode structured output. Because the model cannot independently prove its own claims, its reported evidence, criteria, claims, and artifacts are stored only as explicitly unverified model output; `met_criteria` and actual artifacts remain empty and the provider returns `incomplete`. A Mistral-only run therefore cannot reach `READY`; an independent tool provider or human verification must complete the work. Every Mistral result (`failed`, `incomplete`, `pending_human`, or `effect_unknown`) is excluded from automatic retries, fallback reassignments, and correction rounds; each Mistral task receives at most one attempt per run; a multi-task run may therefore make multiple separate Mistral calls. Any further attempt requires a new operator-started run. `effect_unknown` means the request may have produced an external effect before an interruption, so repeating it in the same run is unsafe. Custom endpoints must be HTTPS and cannot embed credentials, query strings, or fragments. Exact credentials and known secret patterns are redacted, and request/model/token metadata is recorded. HTTP retries are disabled. See the [Mistral API reference](https://docs.mistral.ai/api).

## Layout

```
registry/            legacy registries + skill-sources.json · skills.lock.json · skill-policy.json
omni/
  models.py          dataclasses for tasks, briefs, results, runs
  registry.py        loading + integrity validation
  routing.py         classification, agent selection, squad + wave planning
  orchestrator.py    waves, failures, corrections, arbitration, assembly
  executor.py        SubprocessProvider · MistralProvider (paid inference gated) · ManualProvider
  policy.py          tool grants, deny paths, dangerous-action confirmation
  memory.py          namespaced shared memory, redaction, TTL
  messaging.py       run-scoped agent mailbox
  validation.py      the six gates and the final verdict
  gitops.py          git/PR operations with safety rails
  audit.py           reproducible GitHub account audit
  skill_catalog.py   pinned provenance, ingestion, static scan, trust lifecycle
  skill_catalog_cli.py read-only catalog / inspect / scan command handlers
  cli.py             python3 -m omni …
tests/               orchestration, catalog, ingestion, trust, CLI and policy tests
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
