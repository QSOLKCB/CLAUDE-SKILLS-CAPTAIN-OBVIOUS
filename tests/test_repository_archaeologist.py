"""Skill 004: repository-archaeologist. Offline, bounded discovery of local checkouts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UTILITY = ROOT / "tools" / "obvious.py"
TARGET = "QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS"


class RepositoryArchaeologistTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.search = self.root / "search"
        self.search.mkdir()

    def call(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(UTILITY), *map(str, args)],
            text=True, capture_output=True, check=False, timeout=20,
        )

    def checkout(self, relative, origin=None):
        path = self.search / relative
        path.mkdir(parents=True)
        subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
        if origin is not None:
            subprocess.run(["git", "-C", str(path), "remote", "add", "origin", origin],
                           check=True)
        return path

    def find(self, *extra, expected=TARGET):
        result = self.call("find-repo", "--expected", expected,
                           "--search", self.search, *extra)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_single_match_reports_path_and_evidence(self):
        repo = self.checkout("projects/captain", f"https://github.com/{TARGET}.git")
        code, data = self.find()
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "MATCH")
        self.assertEqual(data["matches"], [str(repo)])
        self.assertEqual(data["expected"], TARGET)
        self.assertGreaterEqual(data["checkouts_inspected"], 1)
        self.assertIn("network", data["note"].lower())

    def test_ssh_origin_and_case_insensitive_match(self):
        self.checkout("x", "git@github.com:qsolkcb/claude-skills-captain-obvious.git")
        code, data = self.find()
        self.assertEqual((code, data["status"]), (0, "MATCH"))

    def test_not_cloned_is_reported_as_not_found_with_hint(self):
        """The comedy requirement: the missing repository was simply never cloned."""
        self.checkout("other", "https://github.com/QSOLKCB/SOMETHING-ELSE.git")
        code, data = self.find()
        self.assertEqual(code, 1)
        self.assertEqual(data["status"], "NOT_FOUND")
        self.assertTrue(data["probably_not_cloned"])
        self.assertIn("git clone https://github.com/" + TARGET + ".git", data["hint"])
        self.assertIn("approval", data["hint"].lower())

    def test_empty_search_root_is_not_found(self):
        code, data = self.find()
        self.assertEqual((code, data["status"]), (1, "NOT_FOUND"))
        self.assertEqual(data["checkouts_inspected"], 0)

    def test_directory_named_like_target_with_other_origin_is_wrong_remote(self):
        self.checkout("CLAUDE-SKILLS-CAPTAIN-OBVIOUS",
                      "https://github.com/SOMEONE-ELSE/CLAUDE-SKILLS-CAPTAIN-OBVIOUS.git")
        code, data = self.find()
        self.assertEqual((code, data["status"]), (1, "WRONG_REMOTE"))
        self.assertEqual(len(data["wrong_remotes"]), 1)
        self.assertEqual(data["wrong_remotes"][0]["observed"],
                         "SOMEONE-ELSE/CLAUDE-SKILLS-CAPTAIN-OBVIOUS")
        self.assertFalse(data["probably_not_cloned"])

    def test_checkout_without_origin_named_like_target_is_wrong_remote(self):
        self.checkout("claude-skills-captain-obvious")
        code, data = self.find()
        self.assertEqual((code, data["status"]), (1, "WRONG_REMOTE"))
        self.assertIsNone(data["wrong_remotes"][0]["observed"])

    def test_multiple_matches_are_ambiguous(self):
        self.checkout("one", f"https://github.com/{TARGET}")
        self.checkout("two", f"git@github.com:{TARGET}.git")
        code, data = self.find()
        self.assertEqual((code, data["status"]), (1, "AMBIGUOUS"))
        self.assertEqual(len(data["matches"]), 2)
        self.assertEqual(data["matches"], sorted(data["matches"]))

    def test_same_checkout_under_two_search_roots_is_not_ambiguous(self):
        repo = self.checkout("a/captain", f"https://github.com/{TARGET}.git")
        result = self.call("find-repo", "--expected", TARGET, "--search", self.search,
                           "--search", self.search / "a")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["matches"], [str(repo)])

    def test_depth_limit_is_enforced_and_reported(self):
        self.checkout("a/b/c/d/deep", f"https://github.com/{TARGET}.git")
        code, data = self.find("--max-depth", "2")
        self.assertEqual((code, data["status"]), (1, "NOT_FOUND"))
        self.assertTrue(data["depth_limit_reached"])
        code, data = self.find("--max-depth", "6")
        self.assertEqual((code, data["status"]), (0, "MATCH"))

    def test_directory_symlinks_are_not_followed(self):
        outside = self.root / "outside"
        outside.mkdir()
        subprocess.run(["git", "-C", str(outside), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(outside), "remote", "add", "origin",
                        f"https://github.com/{TARGET}.git"], check=True)
        (self.search / "shortcut").symlink_to(outside, target_is_directory=True)
        code, data = self.find()
        self.assertEqual((code, data["status"]), (1, "NOT_FOUND"))
        self.assertIn(str(self.search / "shortcut"), data["symlinks_skipped"])

    def test_non_github_origin_is_recorded_but_never_matches(self):
        self.checkout("mirror", f"https://example.org/{TARGET}.git")
        code, data = self.find()
        self.assertEqual(code, 1)
        self.assertNotEqual(data["status"], "MATCH")
        self.assertEqual(data["checkouts"][0]["observed"], None)
        self.assertIn("not an explicitly GitHub-hosted", data["checkouts"][0]["reason"])

    def test_missing_search_root_and_malformed_expected_fail_with_usage_error(self):
        missing = self.call("find-repo", "--expected", TARGET,
                            "--search", self.root / "nope")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("FAIL", missing.stderr)
        malformed = self.call("find-repo", "--expected", "not a repo",
                              "--search", self.search)
        self.assertEqual(malformed.returncode, 2)
        no_roots = self.call("find-repo", "--expected", TARGET)
        self.assertEqual(no_roots.returncode, 2)

    def test_git_metadata_directories_are_not_descended(self):
        repo = self.checkout("captain", f"https://github.com/{TARGET}.git")
        code, data = self.find()
        paths = [row["path"] for row in data["checkouts"]]
        self.assertEqual(paths, [str(repo)])
        self.assertFalse(any("/.git" in path for path in paths))

    def test_output_is_deterministic(self):
        self.checkout("b", "https://github.com/QSOLKCB/B.git")
        self.checkout("a", "https://github.com/QSOLKCB/A.git")
        first = self.call("find-repo", "--expected", TARGET, "--search", self.search)
        second = self.call("find-repo", "--expected", TARGET, "--search", self.search)
        self.assertEqual(first.stdout, second.stdout)
        rows = json.loads(first.stdout)["checkouts"]
        self.assertEqual([row["path"] for row in rows],
                         sorted(row["path"] for row in rows))

    def test_does_not_modify_inspected_checkouts(self):
        repo = self.checkout("captain", f"https://github.com/{TARGET}.git")
        before = sorted(str(p.relative_to(repo)) for p in repo.rglob("*"))
        config = (repo / ".git" / "config").read_bytes()
        self.find()
        after = sorted(str(p.relative_to(repo)) for p in repo.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(config, (repo / ".git" / "config").read_bytes())

    def test_skill_document_exists_and_uses_the_cli(self):
        doc = ROOT / ".claude" / "skills" / "repository-archaeologist" / "SKILL.md"
        text = doc.read_text(encoding="utf-8")
        self.assertIn("name: repository-archaeologist", text)
        self.assertIn("python3 tools/obvious.py find-repo", text)
        self.assertIn("NOT_FOUND", text)


if __name__ == "__main__":
    unittest.main()
