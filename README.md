<div align="center">

# 🫡 CAPTAIN OBVIOUS

### The Claude Code skills that do the thing before announcing they will do the thing.

**Three real skills. One extremely unnecessary department. Zero imaginary test passes.**

[![Tests](https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/actions/workflows/ci.yml/badge.svg)](https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/actions/workflows/ci.yml)
![Claude Code](https://img.shields.io/badge/Claude_Code-project_skills-C47F55)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-648c38)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

[**🌐 LIVE PARODY SITE**](https://qsolkcb.github.io/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/) · [**⚙️ THE ACTUAL SKILLS**](.claude/skills/) · [**🧪 THE TESTS**](tests/test_obvious.py) · [**🔍 THE PYTHON**](tools/obvious.py)

---

> **BREAKING:** An AI assistant has examined a repository. It has confirmed that the repository contains files. Further developments are anticipated.

*Independent parody. Not affiliated with Anthropic or Claude. The utilities are real; the bureaucracy is entirely fictional.*

</div>

## 🚨 The problem nobody asked us to solve

You ask an AI agent to fix some code. It responds:

> "I'll inspect the repository, review the relevant files, assess the test infrastructure, establish a baseline, and then proceed with a carefully considered implementation."

You wait.

> "I have inspected the repository and identified that the files are present."

**Congratulations. Your task now has a press secretary.**

Captain Obvious was created to parody that behaviour. Then, in a regrettable outbreak of engineering discipline, the joke acquired a real Python CLI, offline regression tests and three usable Claude Code skills.

**The punchline:** a status update is not evidence. A green badge is not proof. Reading a SKILL.md file is not the same as having the skill loaded by Claude Code.

## 🏆 Enterprise-grade obviousness, consumer-grade price

| Marketing department says | Engineering department actually does |
| :--- | :--- |
| 🛡️ **Wrong-Repository Intelligence™** | Compares a checkout's GitHub origin with an expected owner/repository; optionally rejects a dirty worktree |
| 🧾 **Evidence-Driven Assurance Architecture™** | Hashes real evidence bytes with SHA-256 and labels the receipt <code>RECORDED_NOT_VERIFIED</code> |
| 👻 **Deterministic Reality Stabilisation™** | Pins and verifies snapshot-file hashes across changes; reports byte parity, **not** frame-rate correctness |
| 📡 **Zero-Friction Neural Compliance Fabric™** | A single Python standard-library script. There is no neural fabric. |
| 📣 **Executive Telemetry Dashboard™** | [A website](https://qsolkcb.github.io/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/) that can generate increasingly unnecessary updates, plus a real browser-side SHA-256 receipt station |

**Actual requirements:** Python 3.10+; Git for the repository guard; Claude Code only if you want to invoke the project skills through Claude Code. No Python packages, Node.js, NPM, Docker, remote model API or database required by the CLI.

## 📦 Installation — be inside the repository you claim to be inside

Clone the project and start a **new** Claude Code session from its root:

~~~bash
git clone https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS.git
cd CLAUDE-SKILLS-CAPTAIN-OBVIOUS
claude
~~~

The project skills live at <code>.claude/skills/&lt;name&gt;/SKILL.md</code>. Check that Claude Code actually discovers them. Invoking Claude from another directory and later opening this repository is **not evidence** that the skill machinery registered them.

To use these skills in another repository, review and copy the three relevant <code>.claude/skills/</code> directories and <code>tools/obvious.py</code> into that project's corresponding locations. Check for existing files before replacing anything, and start Claude Code from the destination project's root. The skill commands assume <code>tools/obvious.py</code> is available relative to the working directory.

**Offline?** The CLI and its tests work offline after checkout. Cloning and the optional GitHub status badge, naturally, do not.

### Invoke a skill

From inside Claude Code, invoke a command directly or ask Claude to use the relevant skill:

| Slash command | Sensible request | Captain's interpretation |
| --- | --- | --- |
| <code>/wrong-repository-preflight</code> | Check repo identity before changing code | "I have confirmed the repo is the repo." |
| <code>/receipts-or-it-didnt-happen</code> | Hash concrete test evidence | "This file contains a number of bytes." |
| <code>/no-ghosts-in-the-tick</code> | Compare deterministic snapshot outputs | "The before is the same as the after." |

[Read the official Claude Code skills documentation](https://code.claude.com/docs/en/skills) for skill discovery and invocation behaviour. Manual execution of the CLI is always possible even without Claude Code.

## 🧰 Skill catalogue — yes, the files contain more than one sentence

<details open>
<summary><strong>🛡️ Skill 001 — Wrong Repository Preflight</strong></summary>

**Real job:** check whether the GitHub remote matches the repository the operator actually intended.

~~~bash
python3 tools/obvious.py repo \
  --path . \
  --expected QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS \
  --require-clean
~~~

A mismatched origin or an unexpectedly dirty worktree exits nonzero. No remote is edited; no PR is merged.

**Not a claim:** correct origin identity does not authorise writes, deployments or merges.

[Read SKILL.md](.claude/skills/wrong-repository-preflight/SKILL.md)

</details>

<details open>
<summary><strong>🧾 Skill 002 — Receipts, Or It Didn't Happen</strong></summary>

**Real job:** record file size and SHA-256 for actual local evidence, not imagined console output.

~~~bash
python3 tools/obvious.py receipt \
  --claim "The README exists" \
  --evidence README.md
~~~

Results are JSON, with status <code>RECORDED_NOT_VERIFIED</code>. Missing files, symlinked path components and duplicate underlying file identities—including hard links where inode identifiers are available—are rejected.

**Not a claim:** a hash proves byte identity, not that a test passed, a benchmark is representative, or an agent's story is accurate.

[Read SKILL.md](.claude/skills/receipts-or-it-didnt-happen/SKILL.md)

</details>

<details open>
<summary><strong>👻 Skill 003 — No Ghosts in the Tick</strong></summary>

**Real job:** preserve a byte-level baseline for deterministic snapshot files during rendering or UI refactors.

~~~bash
python3 tools/obvious.py pin write \
  --root . \
  --manifest /tmp/captain-obvious-pins.json \
  README.md

python3 tools/obvious.py pin verify \
  --root . \
  --manifest /tmp/captain-obvious-pins.json
~~~

The README is a convenient **command demonstration**, not a simulation trace. For game-engine tests, replace it with real authoritative state snapshots generated from fixed seeds, input tapes and tick counts.

**Not a claim:** identical bytes do not, on their own, establish 60 FPS, render purity or correct simulation semantics.

[Read SKILL.md](.claude/skills/no-ghosts-in-the-tick/SKILL.md)

</details>

## 🖥️ Live demonstration: the Department of Evidence

Visit **[the Captain Obvious website](https://qsolkcb.github.io/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/)**.

The site includes a working SHA-256 receipt generator using browser Web Crypto. Select a file of up to **16 MiB**, enter a claim and produce a local receipt. Files are processed in the browser, without upload or analytics. It also contains an executive-grade status-update generator whose usefulness has not been independently established.

**Local receipt station output format (illustrative):**

~~~json
{
  "check": "browser-evidence-receipt",
  "status": "RECORDED_NOT_VERIFIED",
  "claim": "I have definitely finished the task.",
  "evidence": {
    "name": "evidence.txt",
    "bytes": 123,
    "sha256": "<computed by the browser, not invented here>"
  },
  "note": "File hashed locally. Byte identity is not proof of the claim."
}
~~~

If you just want the result and not the ceremony, run <code>python3 tools/obvious.py --help</code>.

## 🧪 Quality assurance — verified, not narrated

Run the tests without creating Python bytecode:

~~~bash
python3 -B -m unittest discover -s tests -v
~~~

The last documented CO-LIVE-001 follow-up CI run completed **23/23 offline tests** at commit <code>a9db3c19b34c32d800627c60f0a529c49f24a292</code>. For the **current** branch's result, consult the live [GitHub Actions badge and run history](https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/actions/workflows/ci.yml)—do not assume historical green remains current green.

Coverage includes repo identity, dirty-worktree handling, receipt hashing, missing evidence, symlinked parents, hard-linked duplicates, manifest self-inclusion, snapshot tampering and copyable shell command examples.

**Security boundary:** the filesystem checks are practical guards, **not** a proof of immunity to adversarial concurrent filesystem changes or TOCTOU attacks. The browser receipt is likewise an identity record, not semantic verification.

## 🧪 CO-LIVE-001 — Captain Obvious investigated Captain Obvious

The first Claude Code CLI gauntlet was particularly on-brand:

1. Claude could not locate the repository because it had not yet been cloned.
2. After the operator approved the clone, Claude manually followed the three skill procedures. The skills were **not loaded by its skill tool**, because that session began outside the project.
3. Claude reported all four experiments passed, then identified three genuine filesystem-identity defects.
4. Its first restoration attempt also failed because <code>cp</code> was aliased to interactive mode. Claude correctly identified **that** as a test-harness mistake, not a tool defect.
5. The defects were addressed in [PR #3](https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/pull/3), along with regression coverage and Python bytecode ignores.

**Lesson learned:** even a parody of unnecessary status reports benefits from an operator who asks for reproducible evidence.

> **Captain's official finding:** "We have inspected ourselves. During the inspection, we discovered that further inspection had been warranted."

## 🗂️ Architecture — the smallest possible bureaucracy

~~~text
CLAUDE-SKILLS-CAPTAIN-OBVIOUS/
├── .claude/skills/
│   ├── wrong-repository-preflight/SKILL.md
│   ├── receipts-or-it-didnt-happen/SKILL.md
│   └── no-ghosts-in-the-tick/SKILL.md
├── tools/obvious.py         # Real CLI, Python standard library
├── tests/test_obvious.py    # Offline unittest coverage
├── index.html               # Static site and browser Web Crypto
├── .github/workflows/
│   ├── ci.yml               # Tests on PRs and main
│   └── pages.yml            # Pages deployment restricted to main
└── README.md                # This magnificent administrative achievement
~~~

No production database. No microservices. No Kubernetes. No 14-step setup wizard. The project's greatest infrastructural dependency is the operator remembering which directory they are in.

## ❓ Frequently announced questions

<details>
<summary><strong>Is this an actual Claude Code skill project or just a joke?</strong></summary>

Both. The skills have discoverable <code>SKILL.md</code> files and invoke a real CLI with documented behaviours. The jokes are commentary. The checks are actual executable code.

</details>

<details>
<summary><strong>Why did Claude say it couldn't load the skills?</strong></summary>

In the first live gauntlet, Claude Code was started outside this project. It subsequently read skill files manually. Follow the project-root startup instructions and verify discovery instead of treating a file read as a loaded skill.

</details>

<details>
<summary><strong>Does a SHA-256 receipt prove my tests passed?</strong></summary>

No. It identifies the bytes in the evidence you supplied. You still need to inspect the results, execution command, exit status, environment and tested commit. That distinction is the whole point.

</details>

<details>
<summary><strong>Can I let Captain Obvious merge my pull requests?</strong></summary>

Not on the basis of a repository identity check. Review and authorise GitHub writes separately. Knowing which repo is open is not permission to deploy it.

</details>

<details>
<summary><strong>Does it require NPM, Docker, a database or a cloud API?</strong></summary>

No. The Python CLI uses only the standard library. Git is required for the repository identity check; the website is static. GitHub hosting and Claude Code itself are external services, not hidden CLI dependencies.

</details>

---

<div align="center">

### 🫡 THE CAPTAIN'S FINAL STATUS UPDATE

**"The README has been documented. The documentation confirms the existence of the README. This concludes the documentation phase."**

[**Open the live site**](https://qsolkcb.github.io/CLAUDE-SKILLS-CAPTAIN-OBVIOUS/) · [**Inspect the source**](https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS) · [**View the license**](LICENSE)

<sub>Apache-2.0 · Independent satire · Not affiliated with Anthropic · No claims of 110% test coverage were harmed in the making of this README.</sub>

</div>
