"""v0.3.0 documentation contract: the site and README feature all six skills."""
import html
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "wrong-repository-preflight", "receipts-or-it-didnt-happen", "no-ghosts-in-the-tick",
    "repository-archaeologist", "alias-of-betrayal", "skill-that-audits-skills",
)


class SixSkillDocumentationTests(unittest.TestCase):
    def setUp(self):
        self.site = (ROOT / "index.html").read_text(encoding="utf-8")
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_every_skill_is_linked_from_site_and_readme(self):
        for name in SKILLS:
            self.assertIn(f"/.claude/skills/{name}/SKILL.md", self.site, name)
            self.assertIn(f".claude/skills/{name}/SKILL.md", self.readme, name)
            self.assertIn(f"/{name}", self.readme, name)
        self.assertEqual(self.site.count('<article class="skill">'), 6)
        self.assertIn("<strong>06</strong><span>Executable skills</span>", self.site)

    def test_new_site_command_examples_survive_copy_and_paste(self):
        labels = ("Repository search command", "Fixture restore command", "Skill audit command")
        expected = [
            [["tools/obvious.py", "find-repo", "--expected",
              "QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS", "--search", "..", "--max-depth", "2"]],
            [["tools/obvious.py", "restore", "--source", "fixtures/original.snap",
              "--dest", "work/tick-0600.snap", "--overwrite"]],
            [["tools/obvious.py", "audit-skills", "--root", "."]],
        ]
        for label, calls_expected in zip(labels, expected):
            match = re.search(rf'<pre aria-label="{label}">(.*?)</pre>', self.site, re.DOTALL)
            self.assertIsNotNone(match, label)
            script = ('python3() { printf "CALL\\n"; printf "ARG:%s\\n" "$@"; }\n'
                      + html.unescape(match.group(1)))
            result = subprocess.run(["sh", "-c", script], text=True, capture_output=True,
                                    timeout=5, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [[line.removeprefix("ARG:") for line in chunk.splitlines() if line]
                     for chunk in result.stdout.split("CALL\n") if chunk]
            self.assertEqual(calls, calls_expected, label)

    def test_readme_keeps_loaded_versus_discoverable_distinction(self):
        self.assertIn("DISCOVERABLE_ON_DISK", self.readme)
        self.assertIn("ACTUALLY_LOADED_BY_CLAUDE", self.readme)
        self.assertNotIn("invented Markdown", self.readme + self.site)


if __name__ == "__main__":
    unittest.main()
