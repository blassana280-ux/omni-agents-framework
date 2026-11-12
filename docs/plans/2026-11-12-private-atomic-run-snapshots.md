# Atomic Run Snapshot Regression Test Plan

## Goal

Add a deterministic regression test for the private, atomic run-snapshot writer already present in the current PR #33 head.

## Scope

- Test only; do not modify the existing writer or any upstream PR branch.
- Verify that the previous snapshot remains readable until replacement.
- Verify that the temporary snapshot is valid JSON and mode `0600` on POSIX before publication.
- Verify that publication uses `os.replace` and removes the temporary file.
- Keep all work on `omnibrain/private-atomic-run-snapshots-v2`, based on the current PR #33 head.
- Do not touch `main`, merge, or call Mistral.

## Verification

Run the focused persistence test and the complete Python 3.11 Core CI suite. Record the exact commit, test count, skipped count, and workflow result.

## Acceptance criteria

The test passes against the atomic writer in PR #33 and fails against the former direct-write implementation that truncated or exposed the destination before a complete private snapshot was ready.
