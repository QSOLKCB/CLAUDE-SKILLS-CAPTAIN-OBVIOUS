---
name: wrong-repository-preflight
description: Verify GitHub origin identity and worktree status before changing repositories. Stop an agent from confidently reviewing the wrong project.
---

# Wrong Repository Preflight

**Mission:** determine whether this checkout is the repository the operator named. Not whether it merely looks interesting.

## Use when
- The task names an OWNER/REPO, especially after switching between multiple projects.
- An agent is about to edit, release, merge, or publish.
- Someone says "sorry, wrong repo" and the agent still has 15 paragraphs of status updates queued.

## Procedure
1. Ask for the intended OWNER/REPO if it is not already explicit.
2. Run this **read-only** command from the repository root:

       python3 tools/obvious.py repo --path . --expected QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS

   Add --require-clean when the operation requires a clean worktree.
3. Inspect the JSON fields: status, expected, observed, and worktree_dirty.
4. If the check fails, **stop**. Do not guess, silently alter remotes, or switch directories.
5. Treat PASS as an identity check, **not** consent for edits, pushes, merges, or deploys.

## Behaviours verified by the utility
- Recognises GitHub HTTPS and SSH origins, including .git suffixes.
- Rejects non-GitHub origins and malformed repository identifiers.
- Compares requested and observed repository identifiers without executing a shell.
- Inspects status using git status --porcelain on request.
- Makes no repository mutations.

## Captain's report
> "I verified that the repository is the repository. This prevented me from accidentally proving that a different repository is also a repository."

**Failure is actionable:** correct the path, expectation, or remote through an explicitly approved process, then re-run the guard.