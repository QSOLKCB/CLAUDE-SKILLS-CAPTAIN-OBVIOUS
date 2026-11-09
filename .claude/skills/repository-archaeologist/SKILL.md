---
name: repository-archaeologist
description: Find an existing local Git checkout of an explicitly named GitHub OWNER/REPO by scanning only operator-authorised directories, offline and bounded, and report MATCH, NOT_FOUND, WRONG_REMOTE or AMBIGUOUS with evidence.
---

# Repository Archaeologist

**Mission:** before declaring a repository "missing", find out whether it was ever cloned. Then stop and ask, instead of cloning on impulse.

## Use when
- The operator names an OWNER/REPO but the current directory is not that checkout.
- An agent is about to say "I could not find the repository" after looking in exactly one place.
- An agent is about to clone a repository that may already exist locally, or may need approval to fetch.

## Procedure
1. Confirm the exact OWNER/REPO. If the operator has not named one, ask. Do not infer it from directory names.
2. Ask which local directories you may search, unless they are already stated. Do not scan `/` or a whole home directory without permission.
3. Run from this repository's root, with one `--search` per authorised directory:

       python3 tools/obvious.py find-repo --expected QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS --search ~/src --search /tmp --max-depth 4

4. Read `status`, `matches`, `wrong_remotes`, `caveats` and `hint` in the JSON output:
   - `MATCH` (exit 0): exactly one checkout has a matching GitHub origin. Next, run `wrong-repository-preflight` inside that path.
   - `AMBIGUOUS` (exit 1): several distinct checkouts match. Ask the operator which one is intended.
   - `WRONG_REMOTE` (exit 1): a checkout with a similar name points somewhere else, such as a fork or a missing origin. Report it. Do not edit remotes.
   - `NOT_FOUND` (exit 1): nothing matched, and `probably_not_cloned` is true. Read `caveats` first: if the depth or directory limit was reached, the scan was incomplete.
   - Exit 2 means invalid input, for example a malformed OWNER/REPO or a missing search directory.
5. If the repository has not been cloned, **stop and ask** for approval before running the `git clone` command printed in `hint`. This tool never clones, fetches or contacts the network.
6. Quote the JSON evidence in your report: the paths inspected, the observed origins and any caveats.

## Utility contract
- Scans only the `--search` directories supplied. At least one is required.
- Respects `--max-depth` (default 4, maximum 32) and `--max-directories` (default 50000) and reports when either limit truncated the scan.
- Never follows directory symlinks. Skipped symlinks are listed in `symlinks_skipped`.
- Never descends into `.git` metadata directories.
- Reads `remote.origin.url` with `git config --get`. It does not run fetch, status or hooks.
- Recognises only explicitly GitHub-hosted HTTPS and SSH origins. Comparison is case-insensitive.
- Redacts credentials embedded in origin URLs before printing them.
- Deduplicates a checkout reached through overlapping search roots, by filesystem identity.
- Output is sorted and deterministic for the same filesystem state.

## Limitations
- Bare repositories and checkouts without a `.git` entry are not detected.
- Only the `origin` remote is inspected. A checkout whose matching remote is named `upstream` is reported as `WRONG_REMOTE` or `NOT_FOUND`.
- A repository outside the authorised roots is, correctly, not found.

## Captain's report
> "I searched the authorised directories and found no repository. I have deduced that the repository is not in the places where it is not."

**Important:** `NOT_FOUND` says the checkout is not in the directories you were allowed to search. It is not permission to clone.
