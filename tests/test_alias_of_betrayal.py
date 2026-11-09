"""Skill 005: alias-of-betrayal. Restore fixtures with Python, not whatever `cp` means today."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UTILITY = ROOT / "tools" / "obvious.py"
ORIGINAL = b"tick=0600 x=17 y=29\n" + bytes(range(256))
MUTATED = b"tick=0600 x=17 y=30\n" + bytes(range(256))


class AliasOfBetrayalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "original.snap"
        self.source.write_bytes(ORIGINAL)
        self.work = self.root / "work"
        self.work.mkdir()
        self.dest = self.work / "tick-0600.snap"

    def call(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(UTILITY), *map(str, args)],
            text=True, capture_output=True, check=False, timeout=10,
        )

    def restore(self, *extra, source=None, dest=None):
        return self.call("restore", "--source", source or self.source,
                         "--dest", dest or self.dest, *extra)

    def assert_refused(self, result, fragment="FAIL:"):
        """A refusal from the tool itself, not an argparse usage error."""
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertTrue(result.stderr.startswith("FAIL:"), result.stderr)
        self.assertIn(fragment, result.stderr)

    def assert_no_temporary_files(self):
        leftovers = [p.name for p in self.work.iterdir() if p.name.startswith(".obvious-")]
        self.assertEqual(leftovers, [])

    def test_restore_to_new_destination_verifies_sha256(self):
        result = self.restore()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "RESTORED_AND_VERIFIED")
        self.assertEqual(data["sha256"], hashlib.sha256(ORIGINAL).hexdigest())
        self.assertEqual(data["bytes"], len(ORIGINAL))
        self.assertFalse(data["overwritten"])
        self.assertEqual(self.dest.read_bytes(), ORIGINAL)
        self.assert_no_temporary_files()

    def test_existing_destination_requires_explicit_overwrite(self):
        self.dest.write_bytes(MUTATED)
        result = self.restore()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--overwrite", result.stderr)
        self.assertEqual(self.dest.read_bytes(), MUTATED)
        self.assert_no_temporary_files()

    def test_overwrite_restores_and_records_previous_digest(self):
        self.dest.write_bytes(MUTATED)
        result = self.restore("--overwrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["overwritten"])
        self.assertEqual(data["previous_sha256"], hashlib.sha256(MUTATED).hexdigest())
        self.assertEqual(self.dest.read_bytes(), ORIGINAL)
        self.assert_no_temporary_files()

    def test_overwrite_replaces_entry_atomically_without_writing_through_hardlinks(self):
        bystander = self.root / "bystander.snap"
        self.dest.write_bytes(MUTATED)
        bystander.hardlink_to(self.dest)
        self.assertEqual(self.restore("--overwrite").returncode, 0)
        self.assertEqual(self.dest.read_bytes(), ORIGINAL)
        self.assertEqual(bystander.read_bytes(), MUTATED)

    def test_cp_aliased_to_cp_dash_i_regression(self):
        """CO-LIVE-001: `cp` was aliased to `cp -i`, so the shell 'restore' did nothing."""
        bash, cp = shutil.which("bash"), shutil.which("cp")
        if not bash or not cp:
            self.skipTest("bash and cp are required to reproduce the alias incident")
        self.dest.write_bytes(MUTATED)
        script = (
            "shopt -s expand_aliases\n"
            "alias cp='cp -i'\n"
            'cp "$1" "$2" </dev/null\n'
            "exit 0\n"
        )
        subprocess.run([bash, "--noprofile", "--norc", "-c", script, "bash",
                        str(self.source), str(self.dest)],
                       capture_output=True, timeout=10, check=False)
        self.assertEqual(self.dest.read_bytes(), MUTATED,
                         "the aliased cp should have declined to overwrite")
        result = self.restore("--overwrite")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.dest.read_bytes(), ORIGINAL)
        self.assertEqual(json.loads(result.stdout)["sha256"],
                         hashlib.sha256(ORIGINAL).hexdigest())

    def test_self_copy_is_rejected(self):
        result = self.restore("--overwrite", dest=self.source)
        self.assertEqual(result.returncode, 2)
        self.assertIn("same file", result.stderr)
        self.assertEqual(self.source.read_bytes(), ORIGINAL)

    def test_self_copy_through_dotdot_spelling_is_rejected(self):
        alias = self.work / ".." / "original.snap"
        result = self.restore("--overwrite", dest=alias)
        self.assert_refused(result, "same file")
        self.assertEqual(self.source.read_bytes(), ORIGINAL)

    def test_self_copy_through_hard_link_is_rejected(self):
        self.dest.hardlink_to(self.source)
        result = self.restore("--overwrite")
        self.assertEqual(result.returncode, 2)
        self.assertIn("same file", result.stderr)

    def test_symlinked_source_is_rejected(self):
        link = self.root / "link.snap"
        link.symlink_to(self.source)
        result = self.restore(source=link)
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse(self.dest.exists())

    def test_symlinked_destination_is_not_written_through(self):
        victim = self.root / "victim.txt"
        victim.write_bytes(b"do not touch\n")
        self.dest.symlink_to(victim)
        result = self.restore("--overwrite")
        self.assert_refused(result, "symlink")
        self.assertEqual(victim.read_bytes(), b"do not touch\n")
        self.assertTrue(self.dest.is_symlink())

    def test_symlinked_destination_parent_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.work, target_is_directory=True)
        result = self.restore(dest=alias / "tick-0600.snap")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse(self.dest.exists())

    def test_missing_source_directory_source_and_directory_destination_fail(self):
        self.assert_refused(self.restore(source=self.root / "missing"))
        self.assert_refused(self.restore(source=self.work))
        self.assert_refused(self.restore("--overwrite", dest=self.work))
        self.assert_refused(self.restore(dest=self.root / "nope" / "x.snap"))

    def test_expected_digest_mismatch_leaves_destination_untouched(self):
        self.dest.write_bytes(MUTATED)
        wrong = hashlib.sha256(b"something else").hexdigest()
        result = self.restore("--overwrite", "--expected-sha256", wrong)
        self.assertEqual(result.returncode, 2)
        self.assertIn("expected", result.stderr.lower())
        self.assertEqual(self.dest.read_bytes(), MUTATED)
        self.assert_no_temporary_files()

    def test_expected_digest_match_and_malformed_digest(self):
        good = hashlib.sha256(ORIGINAL).hexdigest()
        self.assertEqual(self.restore("--expected-sha256", good).returncode, 0)
        malformed = self.restore("--overwrite", "--expected-sha256", "abc")
        self.assertEqual(malformed.returncode, 2)

    def test_explicitly_empty_expected_digest_is_rejected(self):
        """Review on PR #5: an unset "$PRISTINE_SHA256" must not disable verification."""
        self.dest.write_bytes(MUTATED)
        result = self.restore("--overwrite", "--expected-sha256", "")
        self.assert_refused(result, "--expected-sha256")
        self.assertEqual(self.dest.read_bytes(), MUTATED)

    def test_backslash_bypasses_aliases_but_only_command_bypasses_functions(self):
        """Review on PR #5: the documented bypass must work for shell functions too."""
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is required")
        script = 'cp() { :; }\n\\cp "$1" "$2"\ncmp -s "$1" "$2" && echo BACKSLASH_COPIED\n' \
                 'command cp "$1" "$2"\ncmp -s "$1" "$2" && echo COMMAND_COPIED\n'
        result = subprocess.run([bash, "--noprofile", "--norc", "-c", script, "bash",
                                 str(self.source), str(self.dest)],
                                text=True, capture_output=True, timeout=10, check=False)
        self.assertNotIn("BACKSLASH_COPIED", result.stdout)
        self.assertIn("COMMAND_COPIED", result.stdout)
        text = (ROOT / ".claude" / "skills" / "alias-of-betrayal" / "SKILL.md").read_text(
            encoding="utf-8")
        self.assertIn("`\\cp` bypasses aliases only", text)

    def test_file_mode_is_copied(self):
        os.chmod(self.source, 0o640)
        self.assertEqual(self.restore().returncode, 0)
        self.assertEqual(self.dest.stat().st_mode & 0o777, 0o640)

    def test_skill_document_explains_shell_inspection_honestly(self):
        doc = ROOT / ".claude" / "skills" / "alias-of-betrayal" / "SKILL.md"
        text = doc.read_text(encoding="utf-8")
        self.assertIn("name: alias-of-betrayal", text)
        self.assertIn("python3 tools/obvious.py restore", text)
        for probe in ("type cp", "alias cp", "command -V cp", "command cp"):
            self.assertIn(probe, text)
        self.assertIn("cannot discover", text)


if __name__ == "__main__":
    unittest.main()
