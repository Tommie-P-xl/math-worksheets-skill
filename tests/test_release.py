"""Release metadata derives from one source; tests use disposable fixtures."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_version", ROOT / "tools/version.py")
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)


class ReleaseMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mws-release-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    def fixture(self, number="8.1.2", extra=""):
        (self.work / "SKILL.md").write_text(
            "---\nname: fixture\nmetadata:\n  version: " + number + "\n" + extra
            + "  author: example\n---\nBody version: 99.99.99\n", encoding="utf-8")

    def execute(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools/version.py"), *map(str, args)],
                              cwd=self.work, capture_output=True, encoding="utf-8")

    def test_reads_only_metadata_and_rejects_invalid_or_duplicate_versions(self):
        self.fixture()
        self.assertEqual(version.get_version(self.work), "8.1.2")
        for number, extra in (("8.01.2", ""), ("8.1", ""), ("bad", ""), ("8.1.2", "  version: 9.2.3\n")):
            self.fixture(number, extra)
            with self.subTest(number=number, extra=extra), self.assertRaises(ValueError):
                version.get_version(self.work)

    def test_release_notes_use_source_heading_and_exclude_history(self):
        self.fixture()
        (self.work / "RELEASE_NOTES.md").write_text(
            "# Current release\n\n- Current feature.\n\n## v1.0.0\n\n- Historical feature.\n", encoding="utf-8")
        text = version.release_notes(self.work)
        self.assertTrue(text.startswith("# v8.1.2\n"))
        self.assertIn("Current feature", text)
        self.assertNotIn("Historical feature", text)

    def test_cli_outputs_and_mismatch_guard_work_from_other_directories(self):
        expected = version.get_version(ROOT)
        tag = "v" + expected
        self.assertEqual(self.execute("--tag").stdout.strip(), tag)
        notes, outputs = self.work / "notes.md", self.work / "actions.txt"
        result = self.execute("--check-tag", "wrong-tag", "--notes-out", notes)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(notes.exists())
        result = self.execute("--check-tag", tag, "--notes-out", notes, "--github-output", outputs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(outputs.read_text(encoding="utf-8"), f"version={expected}\ntag={tag}\n")
        self.assertTrue(notes.read_text(encoding="utf-8").startswith("# " + tag + "\n"))

    def test_packaged_metadata_filename_and_checksum_agree(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/package_skill.py"), "--outdir", str(self.work)],
                                cwd=self.work, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.work / f"math-worksheets-v{version.get_version(ROOT)}.zip"
        self.assertTrue(archive.is_file())
        checksum = archive.with_suffix(archive.suffix + ".sha256").read_text(encoding="ascii").split()[0]
        self.assertEqual(checksum, hashlib.sha256(archive.read_bytes()).hexdigest())
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(package.read("math-worksheets/SKILL.md").replace(b"\r\n", b"\n"),
                             (ROOT / "SKILL.md").read_bytes().replace(b"\r\n", b"\n"))
            self.assertIsNone(package.testzip())


if __name__ == "__main__":
    unittest.main()
