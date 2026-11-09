"""Offline contract tests for Captain Obvious' inconveniently real utilities."""
import hashlib
import html
import re
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UTILITY = ROOT / "tools" / "obvious.py"


class CaptainObviousTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "snapshot.txt").write_text("seed=17 tick=2000\n", encoding="utf-8")

    def call(self, *args):
        return subprocess.run(
            [sys.executable, str(UTILITY), *map(str, args)],
            text=True, capture_output=True, check=False, timeout=10,
        )

    def make_repo(self, origin):
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.root), "remote", "add", "origin", origin], check=True)

    def test_correct_repo_passes_and_reports_dirty_state(self):
        self.make_repo("https://github.com/QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS.git")
        result = self.call("repo", "--path", self.root,
                           "--expected", "QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "PASS")
        self.assertTrue(data["worktree_dirty"])

    def test_wrong_repo_fails_closed(self):
        self.make_repo("git@github.com:QSOLKCB/OTHER.git")
        result = self.call("repo", "--path", self.root, "--expected", "QSOLKCB/TARGET")
        self.assertEqual(result.returncode, 2)
        self.assertIn("WRONG REPOSITORY", result.stderr)

    def test_non_github_origin_rejected(self):
        self.make_repo("https://example.org/QSOLKCB/TARGET.git")
        self.assertEqual(self.call("repo", "--path", self.root,
                                   "--expected", "QSOLKCB/TARGET").returncode, 2)

    def test_require_clean_rejects_untracked_file(self):
        self.make_repo("git@github.com:QSOLKCB/TARGET.git")
        result = self.call("repo", "--path", self.root, "--expected",
                           "QSOLKCB/TARGET", "--require-clean")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not clean", result.stderr)

    def test_receipt_hashes_real_bytes_without_claiming_verification(self):
        result = self.call("receipt", "--claim", "a test passed",
                           "--evidence", self.root / "snapshot.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "RECORDED_NOT_VERIFIED")
        self.assertEqual(data["evidence"][0]["sha256"],
                         hashlib.sha256(b"seed=17 tick=2000\n").hexdigest())

    def test_receipt_missing_evidence_fails(self):
        result = self.call("receipt", "--claim", "green", "--evidence", self.root / "missing")
        self.assertEqual(result.returncode, 2)

    def test_receipt_duplicate_evidence_fails(self):
        item = self.root / "snapshot.txt"
        result = self.call("receipt", "--claim", "green", "--evidence", item, item)
        self.assertEqual(result.returncode, 2)

    def test_pin_roundtrip(self):
        manifest = self.root / "manifest.json"
        created = self.call("pin", "write", "--root", self.root,
                            "--manifest", manifest, "snapshot.txt")
        self.assertEqual(created.returncode, 0, created.stderr)
        record = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], 1)
        self.assertEqual(record["files"][0]["path"], "snapshot.txt")
        checked = self.call("pin", "verify", "--root", self.root, "--manifest", manifest)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('"status": "PASS"', checked.stdout)

    def test_pin_detects_tampering(self):
        manifest = self.root / "manifest.json"
        self.assertEqual(self.call("pin", "write", "--root", self.root,
                                   "--manifest", manifest, "snapshot.txt").returncode, 0)
        (self.root / "snapshot.txt").write_text("seed=29 tick=2000\n")
        checked = self.call("pin", "verify", "--root", self.root, "--manifest", manifest)
        self.assertEqual(checked.returncode, 2)
        self.assertIn("PARITY FAILURE", checked.stderr)

    def test_pin_rejects_traversal(self):
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", self.root / "pins.json", "../secret.txt")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe relative path", result.stderr)

    def test_pin_rejects_symlink(self):
        (self.root / "alias.txt").symlink_to(self.root / "snapshot.txt")
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", self.root / "pins.json", "alias.txt")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlinks are not accepted", result.stderr)

    def test_pin_rejects_duplicate_paths(self):
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", self.root / "pins.json",
                           "snapshot.txt", "snapshot.txt")
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate", result.stderr)

    def test_pin_rejects_manifest_through_symlinked_parent(self):
        """A manifest reached through an alias must not replace a pinned input."""
        original = self.root / "snapshot.txt"
        before = original.read_bytes()
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", alias / "snapshot.txt", "snapshot.txt")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("symlink", result.stderr.lower())
        self.assertEqual(original.read_bytes(), before)

    def test_pin_rejects_verification_through_symlinked_parent(self):
        manifest = self.root / "pins.json"
        self.assertEqual(self.call("pin", "write", "--root", self.root,
                                   "--manifest", manifest, "snapshot.txt").returncode, 0)
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        result = self.call("pin", "verify", "--root", self.root,
                           "--manifest", alias / "pins.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr.lower())

    def test_pin_rejects_existing_hardlinked_manifest(self):
        """Even a different pathname must not identify the pinned file itself."""
        original = self.root / "snapshot.txt"
        manifest = self.root / "hardlink-to-snapshot"
        manifest.hardlink_to(original)
        before = original.read_bytes()
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", manifest, "snapshot.txt")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("itself", result.stderr)
        self.assertEqual(original.read_bytes(), before)

    def test_receipt_rejects_symlinked_parent_directory(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        result = self.call("receipt", "--claim", "looks fine",
                           "--evidence", alias / "snapshot.txt")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("symlink", result.stderr.lower())

    def test_receipt_rejects_hardlinked_duplicate_file(self):
        original = self.root / "snapshot.txt"
        duplicate = self.root / "hardlink.txt"
        duplicate.hardlink_to(original)
        result = self.call("receipt", "--claim", "two pieces of evidence",
                           "--evidence", original, duplicate)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("duplicate evidence file", result.stderr)

    def test_receipt_accepts_distinct_files_with_identical_bytes(self):
        original = self.root / "snapshot.txt"
        duplicate_content = self.root / "independent-copy.txt"
        duplicate_content.write_bytes(original.read_bytes())
        result = self.call("receipt", "--claim", "same bytes, different files",
                           "--evidence", original, duplicate_content)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)["evidence"]
        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0]["sha256"], evidence[1]["sha256"])

    def test_pin_rejects_corrupt_manifest(self):
        manifest = self.root / "manifest.json"
        manifest.write_text('{"schema": 1, "algorithm": "sha256", "files": []}')
        result = self.call("pin", "verify", "--root", self.root, "--manifest", manifest)
        self.assertEqual(result.returncode, 2)

    def test_pin_cannot_hash_itself(self):
        manifest = self.root / "snapshot.txt"
        result = self.call("pin", "write", "--root", self.root,
                           "--manifest", manifest, "snapshot.txt")
        self.assertEqual(result.returncode, 2)

    def test_site_command_examples_survive_copy_and_paste(self):
        """Run exact visible command blocks in a shell with a no-side-effect python3 stub."""
        site = (ROOT / "index.html").read_text(encoding="utf-8")
        commands = re.findall(
            r'<pre aria-label="(?:Repository check command|Evidence receipt command|File parity command)">'
            r'(.*?)</pre>', site, re.DOTALL,
        )
        self.assertEqual(len(commands), 3)
        examples = [
            [
                ["tools/obvious.py", "repo", "--path", ".",
                 "--expected", "QSOLKCB/CLAUDE-SKILLS-CAPTAIN-OBVIOUS"],
            ],
            [
                ["tools/obvious.py", "receipt", "--claim", "README exists",
                 "--evidence", "README.md"],
            ],
            [
                ["tools/obvious.py", "pin", "write", "--root", ".",
                 "--manifest", "/tmp/captain-pins.json", "README.md"],
                ["tools/obvious.py", "pin", "verify", "--root", ".",
                 "--manifest", "/tmp/captain-pins.json"],
            ],
        ]
        for example, expected in zip(commands, examples):
            script = (
                'python3() { printf "CALL\n"; printf "ARG:%s\n" "$@"; }\n'
                + html.unescape(example)
            )
            result = subprocess.run(
                ["sh", "-c", script], text=True, capture_output=True, timeout=5,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [
                [line.removeprefix("ARG:") for line in chunk.splitlines() if line]
                for chunk in result.stdout.split("CALL\n") if chunk
            ]
            self.assertEqual(calls, expected)

    def test_browser_hash_results_are_guarded_after_async_boundaries(self):
        """Older reads, digests and errors must not replace newer submit results."""
        site = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("const submissionId = ++latestSubmission;", site)
        self.assertRegex(
            site,
            r'await file\.arrayBuffer\(\);\s*'
            r'if \(submissionId !== latestSubmission\) return;\s*'
            r'const hash = await crypto\.subtle\.digest\("SHA-256", content\);\s*'
            r'if \(submissionId !== latestSubmission\) return;',
        )
        self.assertRegex(
            site,
            r'catch \(error\) \{\s*'
            r'if \(submissionId !== latestSubmission\) return;',
        )

    def test_site_is_standalone_and_docs_are_real(self):
        site = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="receipt-form"', site)
        self.assertIn("crypto.subtle.digest", site)
        for name in ("wrong-repository-preflight", "receipts-or-it-didnt-happen",
                     "no-ghosts-in-the-tick"):
            doc = ROOT / ".claude" / "skills" / name / "SKILL.md"
            self.assertTrue(doc.is_file())
            self.assertIn("python3 tools/obvious.py", doc.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
