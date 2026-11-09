# CLAUDE-SKILLS-CAPTAIN-OBVIOUS

**The world's first department of obvious statements that occasionally does something measurable.**

[Live site](https://qsolkcb.github.io/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/) | [Skills](.claude/skills) | [Tool](tools/obvious.py)

This project parodies verbose AI development status updates while providing three real, inspectable Claude Code skills. The joke is that Captain Obvious was asked to stop announcing preflights and started running them.

## The actual skills

| Skill | Real function | What it does **not** prove |
| --- | --- | --- |
| [Wrong Repository Preflight](.claude/skills/wrong-repository-preflight/SKILL.md) | Verify a GitHub origin and optionally a clean worktree | Authorization to edit or merge |
| [Receipts, Or It Didn't Happen](.claude/skills/receipts-or-it-didnt-happen/SKILL.md) | Record SHA-256, size, and path for real evidence files | That the attached claim is true |
| [No Ghosts in the Tick](.claude/skills/no-ghosts-in-the-tick/SKILL.md) | Create and verify deterministic file-hash baselines | 60 FPS timing or simulation correctness |

Skills follow Claude Code's .claude/skills/skill-name/SKILL.md convention. Their actual work is performed by tools/obvious.py using **Python standard library only**. The site uses native HTML, CSS, JavaScript and browser Web Crypto—no build step, dependencies, analytics, or network requests for receipts.

## Try it without installing anything

    python3 tools/obvious.py repo --path . --expected QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS
    python3 tools/obvious.py receipt --claim "README exists" --evidence README.md
    python3 tools/obvious.py pin write --root . --manifest /tmp/captain-pins.json README.md
    python3 tools/obvious.py pin verify --root . --manifest /tmp/captain-pins.json
    python3 -m unittest discover -s tests -v

Requires Python 3.10+ and Git for the repository guard. No Python packages need to be installed.

To make the skills discoverable in **another** Claude Code project, copy the desired skill directory into that project's .claude/skills/ and copy tools/obvious.py into its tools/ directory. Command examples in the skill files assume this layout.

## How to interpret the evidence

The three utilities intentionally separate **observed** facts from **inferred** claims. A PASS on origin identity means the remote matches the expected slug. A SHA-256 receipt identifies bytes; it cannot certify semantic correctness. A parity manifest compares bytes; it does not prove a tick rate.

The browser receipt station hashes selected files **locally** using Web Crypto. It does not upload files and it does not prove the submitted claim. Inputs are capped at 16 MiB to bound browser memory use.

## The inspiration

The supplied Claude Code transcript about ARCADE 2, VANILLAJS, and OPT features repeated progress narration while also describing serious checks: a reported 207-test baseline and deterministic state-hash pins. These are **statements in a supplied transcript**, not independently rerun results in this project. The site satirises the commentary style, not the value of the checks.

The transcript is **not** published.

## CI and publishing

.github/workflows/ci.yml tests the Python utility on pull requests and pushes to main. .github/workflows/pages.yml deploys the static site only from main, including when manually dispatched. Branch builds do not publish the site.

**Parody notice:** independent project, not affiliated with Anthropic or Claude. Copyright and licensing: see [LICENSE](LICENSE).