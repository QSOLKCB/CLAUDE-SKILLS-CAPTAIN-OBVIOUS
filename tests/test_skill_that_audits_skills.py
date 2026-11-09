"""Skill 006: skill-that-audits-skills. Static, offline, and it never runs your Markdown."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
UTILITY = ROOT / "tools" / "obvious.py"

GOOD_BODY = """
# Helpful Helper

**Mission:** run the helper and report what it actually printed, not what it intended.

## Procedure
1. Confirm the operator has named the input file and that the file exists locally.
2. Run the helper from the repository root:

       python3 tools/helper.py --input data.txt

3. Read the JSON output and quote the status field, the exit code and the digest.
4. Stop and ask the operator if the helper exits nonzero; do not retry with guessed flags.

## Limitations
The helper only checks byte identity. It does not judge whether the contents are correct.
"""


def skill_text(name="helpful-helper", description="Run the helper and report real output.",
               body=GOOD_BODY, extra=""):
    return f"---\nname: {name}\ndescription: {description}\n{extra}---\n{body}"


class SkillAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.skills = self.root / ".claude" / "skills"
        self.skills.mkdir(parents=True)
        (self.root / "tools").mkdir()
        (self.root / "tools" / "helper.py").write_text("print('helped')\n", encoding="utf-8")

    def call(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(UTILITY), *map(str, args)],
            text=True, capture_output=True, check=False, timeout=10,
        )

    def add(self, directory, text):
        folder = self.skills / directory
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(text, encoding="utf-8")
        return folder

    def audit(self, *extra, root=None):
        result = self.call("audit-skills", "--root", root or self.root, *extra)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def skill(self, data, directory):
        rows = [row for row in data["skills"] if row["directory"] == directory]
        self.assertEqual(len(rows), 1, data["skills"])
        return rows[0]

    def codes(self, data, directory):
        return {finding["code"] for finding in self.skill(data, directory)["findings"]}

    def test_good_skill_passes_and_is_only_discoverable_not_loaded(self):
        self.add("helpful-helper", skill_text())
        code, data = self.audit()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "PASS")
        row = self.skill(data, "helpful-helper")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["discovery"], "DISCOVERABLE_ON_DISK")
        self.assertIsNone(row["actually_loaded_by_claude"])
        self.assertEqual(row["referenced_executables"], ["tools/helper.py"])
        self.assertIn("ACTUALLY_LOADED_BY_CLAUDE", data["claude_loading"])
        self.assertEqual(data["commands_executed"], 0)

    def test_be_useful_is_not_a_skill(self):
        """The comedy requirement: an entire implementation of 'Be useful.' is rejected."""
        self.add("be-useful", "---\nname: be-useful\ndescription: Be useful.\n---\nBe useful.\n")
        code, data = self.audit()
        self.assertEqual((code, data["status"]), (1, "FAIL"))
        codes = self.codes(data, "be-useful")
        self.assertTrue({"PLATITUDE_ONLY", "INSUFFICIENT_PROCEDURE",
                         "NO_LOCAL_EXECUTABLE", "SHORT_DESCRIPTION"} <= codes, codes)

    def test_name_must_match_directory(self):
        self.add("helpful-helper", skill_text(name="someone-else"))
        self.assertIn("NAME_MISMATCH", self.codes(self.audit()[1], "helpful-helper"))

    def test_invalid_name_is_rejected(self):
        self.add("Helpful_Helper", skill_text(name="Helpful_Helper"))
        self.assertIn("INVALID_NAME", self.codes(self.audit()[1], "Helpful_Helper"))

    def test_missing_and_unterminated_frontmatter(self):
        self.add("no-front", GOOD_BODY)
        self.add("open-front", "---\nname: open-front\ndescription: never closed\n" + GOOD_BODY)
        code, data = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("MISSING_FRONTMATTER", self.codes(data, "no-front"))
        self.assertIn("UNTERMINATED_FRONTMATTER", self.codes(data, "open-front"))
        self.assertEqual(self.skill(data, "no-front")["discovery"], "NOT_DISCOVERABLE")

    def test_missing_and_empty_description(self):
        self.add("no-desc", f"---\nname: no-desc\n---\n{GOOD_BODY}")
        self.add("empty-desc", f"---\nname: empty-desc\ndescription:\n---\n{GOOD_BODY}")
        data = self.audit()[1]
        self.assertIn("MISSING_DESCRIPTION", self.codes(data, "no-desc"))
        self.assertIn("EMPTY_DESCRIPTION", self.codes(data, "empty-desc"))

    def test_unsupported_yaml_is_reported_not_guessed(self):
        self.add("listy", skill_text(name="listy", extra="allowed-tools:\n  - Bash\n"))
        self.add("blocky", skill_text(name="blocky", description="|"))
        data = self.audit()[1]
        self.assertIn("UNSUPPORTED_FRONTMATTER", self.codes(data, "listy"))
        self.assertIn("UNSUPPORTED_FRONTMATTER", self.codes(data, "blocky"))

    def test_quoted_scalar_values_are_supported(self):
        self.add("quoted", skill_text(name="quoted",
                                      description='"Run the helper: then report output."'))
        self.add("single", skill_text(name="single",
                                      description="'It''s a helper that reports output.'"))
        code, data = self.audit()
        self.assertEqual(code, 0, data)
        self.assertEqual(self.skill(data, "quoted")["description"],
                         "Run the helper: then report output.")
        self.assertEqual(self.skill(data, "single")["description"],
                         "It's a helper that reports output.")

    def test_duplicate_frontmatter_key(self):
        self.add("helpful-helper", skill_text(extra="name: helpful-helper\n"))
        self.assertIn("DUPLICATE_KEY", self.codes(self.audit()[1], "helpful-helper"))

    def test_missing_utility_is_detected(self):
        self.add("helpful-helper", skill_text(body=GOOD_BODY.replace("helper.py", "gone.py")))
        data = self.audit()[1]
        row = self.skill(data, "helpful-helper")
        self.assertIn("MISSING_UTILITY", self.codes(data, "helpful-helper"))
        self.assertTrue(any("tools/gone.py" in f["message"] for f in row["findings"]))

    def test_reference_escaping_the_repository_is_unsafe(self):
        self.add("helpful-helper", skill_text(
            body=GOOD_BODY.replace("tools/helper.py", "../../outside.py")))
        self.assertIn("UNSAFE_REFERENCE", self.codes(self.audit()[1], "helpful-helper"))

    def test_skill_dir_relative_scripts_are_resolved(self):
        folder = self.add("helpful-helper", skill_text(
            body=GOOD_BODY.replace("tools/helper.py", "${CLAUDE_SKILL_DIR}/scripts/run.py")))
        (folder / "scripts").mkdir()
        (folder / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")
        code, data = self.audit()
        self.assertEqual(code, 0, data)
        self.assertEqual(self.skill(data, "helpful-helper")["referenced_executables"],
                         [".claude/skills/helpful-helper/scripts/run.py"])

    def test_interpreter_argument_with_dot_slash_does_not_need_execute_bit(self):
        """Review on PR #5: python3 ./script.py runs without the script's execute bit."""
        self.add("helpful-helper", skill_text(
            body=GOOD_BODY.replace("tools/helper.py", "./tools/helper.py")))
        code, data = self.audit()
        self.assertEqual(code, 0, data)
        self.assertEqual(self.skill(data, "helpful-helper")["referenced_executables"],
                         ["tools/helper.py"])

    def test_direct_dot_slash_invocation_still_needs_execute_bit(self):
        (self.root / "tools" / "run.sh").write_text("echo hi\n", encoding="utf-8")
        self.add("helpful-helper", skill_text(
            body=GOOD_BODY.replace("python3 tools/helper.py", "./tools/run.sh")))
        self.assertIn("NOT_EXECUTABLE", self.codes(self.audit()[1], "helpful-helper"))

    def test_symlink_component_before_dotdot_is_not_collapsed_away(self):
        """Review on PR #5: tools/link/../helper.py must not be validated as tools/helper.py."""
        outside = self.root.parent / (self.root.name + "-outside") / "child"
        outside.mkdir(parents=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(outside.parent))
        (outside.parent / "helper.py").write_text("print('elsewhere')\n", encoding="utf-8")
        (self.root / "tools" / "link").symlink_to(outside, target_is_directory=True)
        self.add("helpful-helper", skill_text(
            body=GOOD_BODY.replace("tools/helper.py", "tools/link/../helper.py")))
        code, data = self.audit()
        self.assertEqual(code, 1, data)
        self.assertIn("UNSAFE_REFERENCE", self.codes(data, "helpful-helper"))
        self.assertEqual(self.skill(data, "helpful-helper")["referenced_executables"], [])

    def test_directory_without_skill_md_is_malformed(self):
        (self.skills / "empty-shell").mkdir()
        (self.skills / "empty-shell" / "README.md").write_text("hi\n", encoding="utf-8")
        code, data = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("MISSING_SKILL_MD", self.codes(data, "empty-shell"))
        self.assertEqual(self.skill(data, "empty-shell")["discovery"], "NOT_DISCOVERABLE")

    def test_placeholder_text_is_incomplete(self):
        self.add("helpful-helper", skill_text(body=GOOD_BODY + "\nTODO: write the rest.\n"))
        self.assertIn("PLACEHOLDER_TEXT", self.codes(self.audit()[1], "helpful-helper"))

    def test_symlinked_skill_directory_is_not_followed(self):
        real = self.root / "elsewhere" / "helpful-helper"
        real.mkdir(parents=True)
        (real / "SKILL.md").write_text(skill_text(), encoding="utf-8")
        (self.skills / "helpful-helper").symlink_to(real, target_is_directory=True)
        code, data = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("SYMLINKED_SKILL", self.codes(data, "helpful-helper"))

    def test_instruction_only_skill_needs_explicit_allowance(self):
        body = GOOD_BODY.replace("python3 tools/helper.py --input data.txt",
                                 "read data.txt and summarise it")
        self.add("helpful-helper", skill_text(body=body))
        code, data = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("NO_LOCAL_EXECUTABLE", self.codes(data, "helpful-helper"))
        code, data = self.audit("--allow-instruction-only")
        self.assertEqual(code, 0, data)

    def test_embedded_commands_are_never_executed(self):
        marker = self.root / "PWNED"
        (self.root / "tools" / "evil.py").write_text(
            f"open({str(marker)!r}, 'w').write('ran')\n", encoding="utf-8")
        body = GOOD_BODY.replace("tools/helper.py", "tools/evil.py") + (
            f"\n    $(touch {marker})\n    `touch {marker}`\n")
        self.add("helpful-helper", skill_text(body=body))
        self.audit()
        self.assertFalse(marker.exists())

    def test_output_is_deterministic_sorted_and_relative(self):
        self.add("zeta", skill_text(name="zeta"))
        self.add("alpha", skill_text(name="alpha"))
        first = self.call("audit-skills", "--root", self.root)
        second = self.call("audit-skills", "--root", self.root)
        self.assertEqual(first.stdout, second.stdout)
        self.assertNotIn(str(self.root), first.stdout)
        names = [row["directory"] for row in json.loads(first.stdout)["skills"]]
        self.assertEqual(names, ["alpha", "zeta"])

    def test_missing_skills_directory_and_missing_root(self):
        empty = self.root / "empty-project"
        empty.mkdir()
        code, data = self.audit(root=empty)
        self.assertEqual(code, 1)
        self.assertIn("SKILLS_DIR_MISSING", {f["code"] for f in data["findings"]})
        missing = self.call("audit-skills", "--root", self.root / "nope")
        self.assertEqual(missing.returncode, 2)
        self.assertTrue(missing.stderr.startswith("FAIL:"), missing.stderr)

    def test_this_repository_passes_its_own_audit(self):
        code, data = self.audit(root=ROOT)
        self.assertEqual(code, 0, json.dumps(data, indent=2))
        self.assertEqual([row["directory"] for row in data["skills"]], [
            "alias-of-betrayal", "no-ghosts-in-the-tick", "receipts-or-it-didnt-happen",
            "repository-archaeologist", "skill-that-audits-skills",
            "wrong-repository-preflight",
        ])
        for row in data["skills"]:
            self.assertEqual(row["referenced_executables"], ["tools/obvious.py"])
            self.assertIsNone(row["actually_loaded_by_claude"])

    def test_skill_document_exists_and_uses_the_cli(self):
        doc = ROOT / ".claude" / "skills" / "skill-that-audits-skills" / "SKILL.md"
        text = doc.read_text(encoding="utf-8")
        self.assertIn("name: skill-that-audits-skills", text)
        self.assertIn("python3 tools/obvious.py audit-skills", text)
        self.assertIn("DISCOVERABLE_ON_DISK", text)
        self.assertIn("ACTUALLY_LOADED_BY_CLAUDE", text)


if __name__ == "__main__":
    unittest.main()
