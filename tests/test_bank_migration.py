"""Text-only migration, live settings and guide coverage use isolated synthetic banks."""
import importlib.util
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bank_migration", ROOT / "scripts/question_bank.py")
qb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qb)


class NewBankTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mws-migration-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bank = qb.Bank(self.work / "中文 bank")
        self.proposal = self.work / "question.json"

    def save(self, item=None):
        self.proposal.write_text(qb.encoded(item or qb.example()), encoding="utf-8")
        return self.bank.commit(self.proposal, self.bank.preview(self.proposal)["receipt"], "synthetic consent")

    def guide(self):
        path = self.work / "guide.md"
        path.write_text("# 初中数学\n方程：核对等式变形。", encoding="utf-8")
        preview = self.bank.guide_preview("初中", "数学", path)
        return self.bank.guide_commit("初中", "数学", path, approved=preview["receipt"], note="synthetic consent")

    def test_live_config_caps_and_bools_are_enforced(self):
        self.assertEqual(self.bank.config()["backup_keep"], 1)
        self.assertFalse(self.bank.home.exists())
        self.bank.write_config({"reference_limit": 12, "reference_default": 6})
        self.assertEqual(self.bank.context("初中", "数学", limit=12)["limit"], 12)
        self.assertEqual(self.bank.context("初中", "数学")["limit"], 6)
        self.bank.write_config({"reference_limit": 3, "reference_default": 2, "quick_answers": True})
        self.assertEqual(self.bank.context("初中", "数学")["limit"], 2)
        with self.assertRaises(qb.BankError):
            self.bank.context("初中", "数学", limit=4)
        for invalid in ({"backup_keep": 0}, {"page_numbers": 1}, {"page_margin_left_mm": 99}, {"unrecognized": 1}):
            self.bank.write_config(invalid)
            with self.assertRaises(qb.BankError):
                self.bank.config()

    def test_default_comments_preserve_values_and_standard_json_compatibility(self):
        settings = self.bank.config()
        settings.update(backup_keep=2, reference_limit=12)
        self.bank.write_config(settings)
        path = self.bank.home / "config.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(raw["_comments"]), set(qb.DEFAULT_CONFIG))
        self.assertTrue(all(isinstance(note, str) and note.strip() for note in raw["_comments"].values()))
        self.assertEqual(self.bank.config(), settings)
        raw["_comments"]["backup_keep"] = "用户编辑的备注，不改变保留代数。"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(self.bank.config()["backup_keep"], 2)
        self.assertNotIn("_comments", self.bank.config())
        self.assertEqual(self.bank.context("初中", "数学", limit=12)["limit"], 12)

    def test_invalid_comment_metadata_is_reported(self):
        self.bank.home.mkdir(parents=True)
        for invalid in ([], {"unknown": "not a setting"}, {"backup_keep": 1}):
            (self.bank.home / "config.json").write_text(json.dumps({"_comments": invalid}), encoding="utf-8")
            with self.assertRaises(qb.BankError):
                self.bank.config()

    def test_comments_survive_backup_restore(self):
        self.save()
        self.bank.write_config(self.bank.config())
        archive = self.work / "annotated.zip"
        self.bank.backup(archive)
        restored = qb.Bank(self.work / "restored")
        restored.restore(archive)
        raw = json.loads((restored.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(set(raw["_comments"]), set(qb.DEFAULT_CONFIG))
        self.assertEqual(restored.config(), self.bank.config())
        self.assertTrue(restored.doctor()["ok"])

    def test_no_images_or_external_drawing_dependencies(self):
        for key, value in (("solution", r"See \includegraphics{answer.png}"), ("stem", "![diagram](q.png)")):
            item = qb.example()
            item[key] = value
            with self.assertRaisesRegex(qb.BankError, "text/code"):
                self.save(item)
        item = qb.example()
        item["diagram"] = {"givens": ["AB perpendicular BC"], "format": "svg", "code": '<svg><image href="q.png"/></svg>'}
        with self.assertRaises(qb.BankError):
            self.save(item)
        self.assertFalse(self.bank.home.exists())

    def test_guide_review_tracks_question_revisions_and_approved_updates(self):
        saved = self.save()
        self.assertEqual(saved["guide_reviews"][0]["pending_count"], 1)
        self.guide()
        self.assertEqual(self.bank.guide_status("初中", "数学")["pending_count"], 0)
        item = self.bank.get(saved["id"])["item"]
        item["solution"] += " 代回原方程验证。"
        self.save(item)
        self.assertEqual(self.bank.guide_status("初中", "数学")["pending_count"], 1)
        result = self.bank.review_guide("初中", "数学", "已核对修订解法，无需新增命题规则。")
        self.assertEqual(result["status"]["pending_count"], 0)

    def test_guide_preview_invalidated_by_new_question(self):
        self.save()
        path = self.work / "guide.md"
        path.write_text("# 已审阅\n方程与运算。", encoding="utf-8")
        receipt = self.bank.guide_preview("初中", "数学", path)["receipt"]
        item = qb.example()
        item.update(stem="求数值8与9的和。", answer="17", solution="8+9=17。", duplicate_decision={"action": "distinct"})
        self.save(item)
        with self.assertRaisesRegex(qb.BankError, "current preview"):
            self.bank.guide_commit("初中", "数学", path, approved=receipt, note="synthetic")

    def legacy(self, bad=False):
        saved = self.save()
        source = self.bank.home / "sources" / "fixture.png"
        source.parent.mkdir()
        source.write_bytes(b"synthetic opaque image")
        item = self.bank.get(saved["id"])["item"]
        item["sources"] = [{"blob": "sources/fixture.png", "name": "photo.png", "sha256": qb.digest(source.read_bytes()), "size": source.stat().st_size, "locator": "q1"}]
        if bad:
            item["solution"] = r"\includegraphics{answer.png}"
        with closing(sqlite3.connect(self.bank.db)) as con:
            con.execute("UPDATE problems SET payload=?", (qb.encoded(item),))
            con.execute("UPDATE events SET after_json=? WHERE kind='question'", (qb.encoded(item),))
            con.execute("PRAGMA user_version=1")
            con.execute("DROP TABLE guide_reviews")
            con.commit()
        self.bank.write_config({"backup_keep": 7, "guide_max_chars": 6000})
        return saved, source, item

    def test_migration_preserves_math_and_history_strips_blobs_and_restores(self):
        saved, source, old = self.legacy()
        before = self.bank.db.read_bytes()
        plan = self.bank.migrate(backup_keep=1)
        self.assertEqual(self.bank.db.read_bytes(), before)
        self.assertTrue(source.exists())
        self.assertEqual(plan["questions"], 1)
        report = self.bank.migrate(apply=True, backup_keep=1)
        self.assertTrue(report["doctor"]["ok"])
        self.assertFalse(source.exists())
        actual = self.bank.get(saved["id"])["item"]
        for key in ("stem", "answer", "solution", "tags", "diagram", "verification"):
            self.assertEqual(old[key], actual[key])
        self.assertEqual(self.bank.get(saved["id"])["revision"], 1)
        self.assertNotIn("blob", actual["sources"][0])
        with self.bank.connection() as con:
            self.assertFalse(any('"blob"' in r[0] for r in con.execute("SELECT after_json FROM events")))
        with zipfile.ZipFile(report["backup"]) as archive:
            self.assertFalse(any(n.startswith("sources/") for n in archive.namelist()))
        restored = qb.Bank(self.work / "restored")
        restored.restore(report["backup"])
        self.assertEqual(restored.get(saved["id"]), self.bank.get(saved["id"]))
        self.assertEqual(restored.config()["backup_keep"], 1)

    def test_incomplete_visual_solution_blocks_migration_without_mutation(self):
        _, source, _ = self.legacy(bad=True)
        before = self.bank.db.read_bytes()
        with self.assertRaises(qb.BankError):
            self.bank.migrate(apply=True)
        self.assertEqual(before, self.bank.db.read_bytes())
        self.assertTrue(source.exists())

    def test_migration_refuses_source_directory_link_without_deleting_target(self):
        self.save()
        keep = self.bank.home / "keep"
        keep.mkdir()
        marker = keep / "user.txt"
        marker.write_text("keep me", encoding="utf-8")
        link = self.bank.home / "sources"
        try:
            link.symlink_to(keep, target_is_directory=True)
        except OSError:
            self.skipTest("Creating a symlink needs a Windows privilege on this host")
        with self.assertRaisesRegex(qb.BankError, "links|junctions"):
            self.bank.migrate(apply=True)
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")

    def test_home_paths_for_windows_macos_linux(self):
        user_home = Path.home()
        for platform, env, expected in (("win32", {"LOCALAPPDATA": str(self.work)}, self.work / "MathWorksheets"),
                                        ("darwin", {}, Path.home() / "Library/Application Support/MathWorksheets"),
                                        ("linux", {"XDG_DATA_HOME": str(self.work)}, self.work / "math-worksheets")):
            with patch.object(qb.sys, "platform", platform), patch.dict(os.environ, env, clear=True), patch.object(qb.Path, "home", return_value=user_home):
                self.assertEqual(qb.resolve_home(), expected.resolve())


if __name__ == "__main__":
    unittest.main()
