---
name: alias-of-betrayal
description: Restore test fixtures with Python file operations instead of shell cp, requiring explicit overwrite authorisation, rejecting self-copies and symlinks, replacing atomically and verifying the restored bytes with SHA-256.
---

# Alias of Betrayal

**Mission:** make sure that "restore the original file" restores the original file, even when `cp` has quietly become `cp -i`.

## Use when
- A test mutates a fixture or snapshot and has to put the original bytes back.
- A shell `cp`, `mv` or `rm` behaved differently from what you expected, for example it prompted, declined, went to the trash or did nothing.
- You are about to write "restored" in a report without checking the restored bytes.

## Background: CO-LIVE-001
In the first live gauntlet, `cp original.snap work.snap` ran in a shell where `cp` was aliased to `cp -i`. There was no terminal to answer the prompt, so nothing was overwritten. The next parity check failed, and the failure was nearly blamed on the tool under test. `tests/test_alias_of_betrayal.py` reproduces the incident with a real bash.

## Procedure
1. Keep a pristine copy of the fixture before you mutate it, and record its SHA-256, for example with `receipts-or-it-didnt-happen`.
2. Restore it from this repository's root:

       python3 tools/obvious.py restore --source /tmp/fixtures/original.snap --dest /tmp/fixtures/work/tick-0600.snap --overwrite --expected-sha256 "$PRISTINE_SHA256"

   Here `PRISTINE_SHA256` holds the digest you recorded in step 1.

   Leave out `--overwrite` when the destination should not exist yet. The command then refuses to replace anything.
3. Check `"status": "RESTORED_AND_VERIFIED"` and compare `sha256` with the digest you recorded. Exit 2 with a `FAIL:` line means nothing was restored. Read the reason.
4. Re-run the check that depends on the fixture, such as `pin verify`. Report both commands and both exit codes.
5. If a shell command misbehaved, inspect the shell **that ran it** (see below) and report the finding as a harness issue, separate from defects in the code under test.

## Inspecting aliases and functions in your actual shell
Python cannot discover aliases or functions defined in another shell process. Aliases and functions live in that shell's memory and come from its startup files. A subprocess launched from Python never sees them. Run these in the same interactive shell, or the same agent Bash tool session, that ran the surprising command:

    type cp            # bash/zsh: alias, function, builtin or file
    alias cp           # prints the alias definition, if any
    command -V cp      # POSIX description of what 'cp' resolves to
    declare -f cp      # bash: prints a shell function named cp, if any
    type -a cp         # bash: every candidate, in lookup order

To bypass an alias or function for a single command, use `command cp …` or `\cp …`. For startup files, look in `~/.bashrc`, `~/.bash_aliases`, `~/.zshrc` and `~/.profile`. Editing them is the operator's decision, not the agent's.

## Utility contract
- Uses Python file operations only. No shell, alias or function is consulted.
- Refuses to replace an existing destination unless `--overwrite` is given.
- Refuses self-copy, detected by filesystem identity, including `..` spellings and hard links.
- Rejects symlinks in any component of the source or destination path, and destinations that are not regular files.
- Writes to a temporary file in the destination directory, fsyncs it and copies the source's permission bits.
- With `--overwrite`, the existing entry is replaced atomically with `os.replace`. Other hard links to the old file keep their old bytes.
- Without `--overwrite`, the file is created with `os.link`, which never clobbers a destination that appeared concurrently. If hard links are unsupported, it falls back to a final existence check followed by `os.replace`.
- Hashes the bytes read, the temporary copy and the final destination. Fails if they differ or if `--expected-sha256` does not match.
- Leaves no `.obvious-*` temporary files behind, whether the restore succeeds or fails.

## Limitations
- Ownership, timestamps, ACLs and extended attributes are not preserved. Only permission bits are.
- The checks are practical guards, not a defence against a hostile process racing the filesystem (TOCTOU).
- On filesystems without hard-link support, the no-overwrite guarantee is check-then-replace rather than atomic.

## Captain's report
> "I instructed the computer to copy the file. The computer politely asked whether I was sure. Nobody was there to answer. The file remained profoundly uncopied."
