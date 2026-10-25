"""Release identity has one source; artifacts use fixed names and a runtime allowlist."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
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

    def fixture(self, number=None):
        value = version.get_version(ROOT) if number is None else number
        (self.work / "VERSION").write_text(value + "\n", encoding="utf-8")
        (self.work / "SKILL.md").write_text("---\nname: fixture\n---\nUnrelated metadata.\n", encoding="utf-8")
        return value

    def execute(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools/version.py"), *map(str, args)],
                              cwd=self.work, capture_output=True, encoding="utf-8")

    def test_reads_only_version_file_and_rejects_invalid_values(self):
        expected = self.fixture()
        self.assertEqual(version.get_version(self.work), expected)
        parts = expected.split(".")
        for invalid in ("0" + expected, ".".join(parts[:2]), "invalid", expected + "\n" + expected):
            self.fixture(invalid)
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                version.get_version(self.work)
        (self.work / "VERSION").unlink()
        with self.assertRaises(OSError):
            version.get_version(self.work)

    def test_release_notes_remain_unnumbered(self):
        value = self.fixture()
        notes = "# Current release\n\n- Current feature.\n"
        (self.work / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
        self.assertEqual(version.release_notes(self.work), notes)
        self.assertNotIn(value, version.release_notes(self.work))

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
        self.assertTrue(notes.read_text(encoding="utf-8").startswith("# Current release\n"))
        self.assertNotIn(expected, notes.read_text(encoding="utf-8"))

    def test_fixed_package_name_checksum_and_single_identity_source(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/package_skill.py"), "--outdir", str(self.work)],
                                cwd=self.work, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        archive = self.work / "math-worksheets.zip"
        self.assertTrue(archive.is_file())
        checksum = archive.with_suffix(archive.suffix + ".sha256").read_text(encoding="ascii").split()[0]
        self.assertEqual(checksum, hashlib.sha256(archive.read_bytes()).hexdigest())
        expected = version.get_version(ROOT).encode()
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(package.read("math-worksheets/VERSION").strip(), expected)
            for name in package.namelist():
                if name != "math-worksheets/VERSION":
                    self.assertNotIn(expected, package.read(name), name)
                self.assertFalse(any(p in name.split("/") for p in ("tests", "tools", "docs", "__pycache__")), name)
            self.assertIsNone(package.testzip())

    def test_allowlist_ignores_nested_tests_caches_and_personal_files(self):
        source = self.work / "source"
        source.mkdir()
        for name in ("VERSION", "SKILL.md", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        for name in ("scripts", "templates", "references", "tools"):
            shutil.copytree(ROOT / name, source / name)
        unwanted = ("scripts/test_accidental.py", "scripts/checks/tests/private.py", "references/test_notes.md",
                    "templates/personal.json", "scripts/__pycache__/cached.pyc", "tests/test_extra.py", "bank.sqlite")
        for name in unwanted:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"must not ship")
        result = subprocess.run([sys.executable, str(source / "tools/package_skill.py"), "--outdir", str(self.work / "out")],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.work / "out/math-worksheets.zip") as package:
            for name in unwanted:
                self.assertNotIn("math-worksheets/" + name, package.namelist())


if __name__ == "__main__":
    unittest.main()
