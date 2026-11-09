---
name: receipts-or-it-didnt-happen
description: Record SHA-256 receipts for real evidence files without mistaking artifact identity for a verified claim.
---

# Receipts, Or It Didn't Happen

**Mission:** replace a warm feeling of certainty with a cold, reproducible description of bytes.

## Use when
- A test report, benchmark, build artifact, or review record needs a stable identifier.
- The operator wants to know what files were actually produced.
- An agent is about to say "CI is green" based on having considered the idea of CI.

## Procedure
1. Write down the precise claim. This utility does **not** prove that claim.
2. Locate existing log, report, test output, or other evidence files.
3. Run from the repository root:

       python3 tools/obvious.py receipt --claim "The test run passed" --evidence README.md tests/test_obvious.py

4. Preserve the resulting JSON, the tested commit SHA, test command, runtime and exit code (supplied separately).
5. Recompute hashes before relying on transferred artifacts.
6. Read and evaluate the evidence before saying the claim has been verified.

## Result contract
- Status RECORDED_NOT_VERIFIED means the tool hashed files and produced a deterministic JSON record.
- Each evidence row has path, byte length, and SHA-256 digest.
- Missing files, symlinks in any evidence path component, and duplicate file identities (including hard links on filesystems with inode identifiers) fail closed.
- No tests are run and no evidence is interpreted semantically.

## Captain's report
> "I have confirmed that the test report exists. Whether its contents say PASS is a separate investigative expedition."

**Do not** describe a receipt as proof that tests passed or that an AI's narrative is true.