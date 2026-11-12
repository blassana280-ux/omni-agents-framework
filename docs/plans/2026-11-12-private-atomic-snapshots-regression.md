# Atomic Run Snapshot Regression Test Plan

## Goal
Add deterministic regression coverage for the private, atomic run-snapshot writer already present in the current PR #33 head.

## Scope
- Test only; do not modify the existing writer or upstream PR branches.
- Verify that the previous snapshot remains readable until replacement.
- Verify that the temporary snapshot is valid JSON and mode `0600` on POSIX before publication.
- Verify that publication uses `os.replace` and removes the temporary file.
- Work only on `omnibrain/private-atomic-snapshot-regression-v1`, based on the current PR #33 head.
- Do not touch `main`, merge, or call Mistral.

## Verification
Run the focused persistence test and the complete Python 3.11 Core CI suite. Record exact test counts, skips, commit SHAs, and workflow results.

## Acceptance
The test passes against the atomic writer and fails against the former direct-write implementation that truncated or exposed the destination before a complete private snapshot was ready.
