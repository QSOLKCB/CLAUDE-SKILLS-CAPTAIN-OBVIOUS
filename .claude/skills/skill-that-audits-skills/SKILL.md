---
name: skill-that-audits-skills
description: Statically audit this repository's .claude/skills for required frontmatter, matching names, real procedures and existing referenced utilities, without executing any Markdown, and keep "discoverable on disk" separate from "actually loaded by Claude".
---

# The Skill That Audits Skills

**Mission:** establish whether a skill directory contains a skill, or a Markdown file containing a wish.

## Use when
- A skill was added, renamed or edited and you are about to call it "working".
- Someone claims a repository has N skills, and you would like to count them, not admire them.
- An agent reports that it "used a skill" after reading that skill's file.

## Procedure
1. Run from the repository root:

       python3 tools/obvious.py audit-skills --root .

   Add `--allow-instruction-only` for repositories where skills legitimately contain only instructions. Without it, a skill that references no existing local script fails.
2. Read the top-level `status` and `summary`, then every skill's `findings`. Exit 0 means every skill passed. Exit 1 means at least one error, and the JSON says which. Exit 2 means the root does not exist.
3. Fix the reported problems through the normal review process. This audit never edits files.
4. Report each skill's `discovery` value exactly as printed. `DISCOVERABLE_ON_DISK` means the file is where Claude Code looks and has parsable frontmatter with a name. It does **not** mean ACTUALLY_LOADED_BY_CLAUDE.
5. To claim ACTUALLY_LOADED_BY_CLAUDE, collect separate evidence: start a new Claude Code session at the repository root and confirm the skill appears in the available skills, or invoke it as `/skill-name`. Record that observation separately. The JSON field `actually_loaded_by_claude` is always `null` because a file audit cannot observe it.

## What is checked
- Every directory under `.claude/skills/` contains a regular, non-symlink `SKILL.md`. Symlinked skill directories are reported, not followed.
- Frontmatter is present and closed, and contains a valid `name` (lowercase, digits, hyphens, at most 64 characters) that matches the directory name.
- `description` is present, non-empty, at least four words and at most 1024 characters.
- The body contains at least two numbered steps and 60 words. A body that is a short exhortation and nothing else is reported as `PLATITUDE_ONLY`.
- Placeholder markers such as `TODO`, `TBD`, `FIXME` and `lorem ipsum` outside inline code are reported.
- Scripts invoked as `python3 <script>`, `bash <script>`, `./<script>.sh` or `${CLAUDE_SKILL_DIR}/<script>` must exist inside the repository, must not pass through symlinks and, for `./` invocations, must be executable. Interpreter invocations are recognised anywhere in the body, including inline code. Write placeholders in angle brackets, as above, so that examples are not mistaken for references.

## Supported frontmatter syntax
This is **not** a YAML parser. It accepts only single-line `key: value` entries, blank lines and `#` comment lines. Values may be unquoted, double-quoted without backslash escapes, or single-quoted with `''` escapes. Lists, nested mappings, block scalars (`|`, `>`), anchors, tags, flow collections and unquoted values containing `: ` or ` #` are reported as `UNSUPPORTED_FRONTMATTER`. They are not guessed at. Valid YAML that Claude Code accepts can therefore fail this audit. When it does, the finding says so.

## Safety contract
- Reads text and checks paths. It never executes Markdown, code blocks, embedded commands or the referenced scripts. `commands_executed` is always 0, and a regression test plants a script that would create a marker file to prove it.
- Output is sorted and uses repository-relative paths, so identical trees produce identical JSON.

## Captain's report
> "I have audited the skills. One of them consisted entirely of the words 'Be useful.' It has been informed that it is not."
