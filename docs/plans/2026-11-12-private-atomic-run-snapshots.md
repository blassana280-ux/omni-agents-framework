# Private Atomic Run Snapshots Implementation Plan

## Goal

Repair the run snapshot persistence boundary inherited by OmniBrain PRs #29 and #30. A run snapshot must be valid JSON after concurrent writers, must never be exposed with group/other permissions on POSIX, and must preserve the previous complete snapshot if a write fails.

## Architecture

Keep snapshot serialization at `Orchestrator._persist`. Serialize the complete redacted `RunRecord` before opening a file, write it to a unique temporary file in the destination directory, set POSIX mode `0600`, flush and fsync the file, atomically replace the destination, then fsync the parent directory on POSIX. Clean up the temporary file on every failure path. A unique same-directory temporary file plus `os.replace` prevents readers from observing partial JSON and avoids collisions between concurrent writers.

## Tech stack

- Python 3.11 standard library only
- `tempfile`, `os`, `json`, `pathlib`
- Existing unittest suite and GitHub Actions Core CI

## Global constraints

- Work only on `omnibrain/private-atomic-run-snapshots-v1`, based on PR #33 head.
- Never modify `main`, rewrite existing PR branches, or merge anything.
- Do not call Mistral or enable paid inference.
- Preserve recursive secret redaction before persistence.
- POSIX snapshot and temporary files must be mode `0600`.
- No new runtime dependency.

## Tasks

### Task 1 — Pin the failing persistence contract with regression tests

1. Inspect the existing `tests/test_persistence_redaction.py` and `tests/test_orchestration.py` cases that failed in CI on PR #29 and #30.
2. Add a focused test that starts multiple threads writing different `RunRecord` snapshots to the same run path, then asserts the final file parses as one complete JSON object and contains one complete writer's snapshot.
3. Keep the existing POSIX mode assertion and add an assertion that no temporary snapshot files remain after successful persistence.
4. Run the focused tests on Python 3.11. Expected pre-fix result: the permission test fails because the current writer creates mode `0644`; the concurrent-write test must demonstrate the non-atomic writer can expose malformed JSON under contention. If the race is nondeterministic, use a deterministic barrier/patch around the current write path rather than sleeps.

### Task 2 — Implement private atomic snapshot persistence

1. Add a same-directory temporary-file write in `Orchestrator._persist`.
2. Apply `os.fchmod(fd, 0o600)` on POSIX before writing.
3. Serialize `redact(record.to_dict())` as UTF-8 JSON; flush and `os.fsync` the temporary file.
4. Use `os.replace` to atomically publish the complete snapshot.
5. On POSIX, fsync the parent directory after replacement.
6. Close descriptors and remove the temporary file on all failure paths.
7. Do not weaken redaction, change the snapshot schema, or alter run orchestration behavior.

### Task 3 — Verify the focused and full suites

1. Run the focused persistence and traceability tests on Python 3.11.
2. Run the complete unit/integration suite and all existing offline CLI/registry checks.
3. Confirm the report file mode is `0600` on POSIX and that the JSON parses after concurrent writes.
4. Record exact test counts, skips, CI run IDs, and commit SHAs. Do not claim a test passed unless its output is available.

### Task 4 — Publish a reviewable correction PR

1. Commit the plan, regression tests, and implementation as separate commits where the GitHub workflow permits.
2. Open a draft PR from `omnibrain/private-atomic-run-snapshots-v1` targeting `omnibrain/mistral-secret-verify-workflow-v1`.
3. Do not merge the PR or change any existing PR.
4. Report the PR URL, exact base/head SHAs, CI status, and any remaining limitations.

## Acceptance criteria

- Snapshot output is always complete parseable JSON, including under concurrent writers.
- Existing snapshot data is not truncated before the replacement is ready.
- POSIX snapshot file mode is exactly `0600`.
- Temporary files are cleaned up after success and failure.
- Secret redaction remains in force.
- Full CI passes, or any failure is reported with its exact evidence.
