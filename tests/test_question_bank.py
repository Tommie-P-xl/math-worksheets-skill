"""Behavioral checks use synthetic questions and isolated, disposable data homes."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/question_bank.py"
spec = importlib.util.spec_from_file_location("question_bank", SCRIPT)
qb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qb)


class BankTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mws-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bank = qb.Bank(self.work / "global-data")
        self.file = self.work / "proposal.json"

    def proposal(self, **changes):
        item = qb.example()
        item.update(changes)
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        return item

    def save(self, **changes):
        self.proposal(**changes)
        preview = self.bank.preview(self.file)
        return self.bank.commit(self.file, preview["receipt"], "test fixture consent, never a user approval")

    def guide(self, text="# 初中数学\n## 方程\n先确定所学范围，求解后设计题面。", subject="数学"):
        file = self.work / "guide.md"
        file.write_text(text, encoding="utf-8")
        preview = self.bank.guide_preview("初中", subject, file)
        return self.bank.guide_commit("初中", subject, file, approved=preview["receipt"], note="synthetic test approval")

    def test_reads_previews_and_unapproved_commits_do_not_create_storage(self):
        self.proposal()
        self.assertEqual(self.bank.stats()["questions"], 0)
        self.assertTrue(self.bank.context("初中", "数学")["needs_research"])
        self.bank.preview(self.file)
        with self.assertRaisesRegex(qb.BankError, "approval"):
            self.bank.commit(self.file)
        guide = self.work / "guide.md"
        guide.write_text("# 草稿\n未批准", encoding="utf-8")
        self.bank.guide_preview("初中", "数学", guide)
        with self.assertRaises(qb.BankError):
            self.bank.guide_commit("初中", "数学", guide)
        self.assertFalse(self.bank.home.exists())

    def test_approval_is_bound_to_text_and_attached_bytes(self):
        original = self.work / "source.txt"
        original.write_text("original", encoding="utf-8")
        item = self.proposal(sources=[{"file": str(original), "locator": "q1"}])
        receipt = self.bank.preview(self.file)["receipt"]
        original.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "current preview"):
            self.bank.commit(self.file, receipt, "synthetic")
        receipt = self.bank.preview(self.file)["receipt"]
        item["tags"]["grades"].append("八年级")
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        with self.assertRaises(qb.BankError):
            self.bank.commit(self.file, receipt, "synthetic")
        self.assertFalse(self.bank.home.exists())

    def test_cross_grade_same_question_merges_tags_and_sources(self):
        original = self.work / "source.txt"
        original.write_text("synthetic original", encoding="utf-8")
        item = self.proposal(sources=[{"file": str(original), "locator": "q1"}])
        first = self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic")
        item["tags"]["grades"] = ["八年级", "九年级"]
        item["tags"]["exams"] = ["中考"]
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        preview = self.bank.preview(self.file)
        self.assertEqual(preview["mode"], "merge")
        second = self.bank.commit(self.file, preview["receipt"], "synthetic")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(self.bank.stats()["questions"], 1)
        saved = self.bank.get(first["id"])["item"]
        self.assertEqual(saved["tags"]["grades"], ["七年级", "八年级", "九年级"])
        self.assertEqual(len(saved["sources"]), 1)
        self.assertFalse((self.bank.home / "sources").exists())
        self.assertNotIn("blob", saved["sources"][0])
        self.assertTrue(self.bank.doctor()["ok"])

    def test_each_tag_category_has_five_label_cap_including_merged_tags(self):
        item = self.proposal()
        item["tags"]["topics"] = [str(n) for n in range(6)]
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "at most 5"):
            self.bank.preview(self.file)
        item["tags"]["topics"] = [str(n) for n in range(5)]
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic")
        item["tags"]["topics"] = ["new"]
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "at most 5"):
            self.bank.preview(self.file)
        self.assertEqual(self.bank.stats()["questions"], 1)

    def test_changed_answer_requires_explicit_revision_and_stale_preview_fails(self):
        first = self.save()
        item = self.proposal(answer="x=9")
        with self.assertRaisesRegex(qb.BankError, "answer differs"):
            self.bank.preview(self.file)
        item["id"] = first["id"]
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        preview = self.bank.preview(self.file)
        self.assertIn("answer", preview["changed_fields"])
        self.bank.commit(self.file, preview["receipt"], "explicit synthetic revision")
        with self.assertRaisesRegex(qb.BankError, "current preview"):
            self.bank.commit(self.file, preview["receipt"], "stale synthetic revision")
        self.assertEqual(self.bank.get(first["id"])["revision"], 2)

    def test_near_duplicate_requires_review_instead_of_silent_copy(self):
        self.save(stem="已知一元一次方程 $3x+7=22$，请说明每一步依据并求出未知数x的值。")
        self.proposal(stem="已知一元一次方程 $3x+8=23$，请说明每一步依据并求出未知数x的值。")
        preview = self.bank.preview(self.file)
        self.assertTrue(preview["possible_duplicates"])
        self.assertFalse(preview["can_commit"])
        with self.assertRaisesRegex(qb.BankError, "duplicates"):
            self.bank.commit(self.file, preview["receipt"], "synthetic")
        item = qb.load_json(self.file)
        item["duplicate_decision"] = {"action": "distinct"}
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "user reviewed distinct variant in synthetic fixture")
        self.assertEqual(self.bank.stats()["questions"], 2)

    def test_uncertain_givens_block_archival_even_with_digest(self):
        self.proposal(uncertainties=["plus or minus obscured"])
        preview = self.bank.preview(self.file)
        self.assertFalse(preview["can_commit"])
        with self.assertRaises(qb.BankError):
            self.bank.commit(self.file, preview["receipt"], "synthetic")
        self.assertFalse(self.bank.home.exists())

    def test_guide_unique_per_stage_subject_and_external_edits_are_immediate(self):
        first = self.guide()
        self.guide("# 初中数学\n## 方程\n用户批准的精简更新。")
        with self.bank.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM guides").fetchone()[0], 1)
        path = Path(first["path"])
        path.write_text("# 用户规则\n本班没有学过消元法。", encoding="utf-8")
        guide = self.bank.read_guide("初中", "数学")
        self.assertTrue(guide["external_edit"])
        self.assertIn("没有学过", self.bank.context("初中", "数学")["references"][0]["text"])
        self.assertTrue(self.bank.doctor()["ok"])
        self.assertEqual(self.bank.doctor()["user_edited_guides"], [str(path)])

    def test_guide_cap_for_approved_write_and_manual_edit_and_concurrent_change(self):
        saved = self.guide()
        file = self.work / "proposal.md"
        file.write_text("长" * 6001, encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "maximum"):
            self.bank.guide_preview("初中", "数学", file)
        file.write_text("# 更新\n已核对的草稿", encoding="utf-8")
        receipt = self.bank.guide_preview("初中", "数学", file)["receipt"]
        Path(saved["path"]).write_text("# 用户改写\n保留我的规则", encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "current preview"):
            self.bank.guide_commit("初中", "数学", file, approved=receipt, note="synthetic")
        Path(saved["path"]).write_text("长" * 6001, encoding="utf-8")
        with self.assertRaisesRegex(qb.BankError, "no text was discarded"):
            self.bank.context("初中", "数学")
        self.assertFalse(self.bank.doctor()["ok"])

    def test_retrieval_filters_and_combined_reference_character_caps(self):
        for n in range(12):
            item = self.proposal(stem=f"求不同的数值 {n * 271 + 19}", title=f"fixture {n}", duplicate_decision={"action": "distinct"})
            self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic")
        self.guide()
        context = self.bank.context("初中", "数学", limit=10)
        self.assertEqual(context["reference_count"], len(context["references"]))
        self.assertLessEqual(context["reference_count"], 10)
        self.assertEqual(sum(r["kind"] == "guide" for r in context["references"]), 1)
        context = self.bank.context("初中", "数学", limit=10, max_chars=1200)
        self.assertLessEqual(len(qb.encoded(context)), 1200)
        self.assertEqual(self.bank.context("高中", "数学")["references"], [])
        self.assertEqual(self.bank.context("初中", "数学", grades=["九年级"])["reference_count"], 1)
        self.assertEqual(self.bank.context("初中", "物理")["references"], [])
        with self.assertRaisesRegex(qb.BankError, "1..10"):
            self.bank.context("初中", "数学", limit=11)

    def test_diagram_givens_define_identity_but_layout_coordinates_do_not(self):
        one = self.save(diagram={"givens": ["AB perpendicular BC"], "layout_coordinates": {"A": [0, 1]}})
        self.proposal(diagram={"givens": ["AB perpendicular BC"], "layout_coordinates": {"A": [0, 2]}})
        self.assertEqual(self.bank.preview(self.file)["target"], one["id"])
        self.proposal(diagram={"givens": ["AB parallel CD"]}, duplicate_decision={"action": "distinct"})
        two = self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic")
        self.assertNotEqual(one["id"], two["id"])

    def test_unrelated_general_guide_does_not_suppress_needed_research(self):
        self.save()
        self.guide("# 初中数学\n一般要求：认真检查。")
        result = self.bank.context("初中", "数学", topics=["三角形全等"], query="三角形全等")
        self.assertEqual(result["reference_count"], 1)
        self.assertTrue(result["needs_research"])
        self.assertFalse(result["references"][0]["topic_match"])

    def test_backup_restore_preserves_text_sources_guides_and_history(self):
        original = self.work / "upload.txt"
        original.write_text("synthetic raw input", encoding="utf-8")
        saved = self.save(sources=[{"file": str(original), "locator": "1"}])
        self.guide()
        archive = self.work / "backup.zip"
        self.bank.backup(archive)
        recovered = qb.Bank(self.work / "recovered")
        recovered.restore(archive)
        self.assertEqual(recovered.get(saved["id"]), self.bank.get(saved["id"]))
        self.assertEqual(recovered.read_guide("初中", "数学")["text"], self.bank.read_guide("初中", "数学")["text"])
        self.assertTrue(recovered.doctor()["ok"])
        self.assertEqual(recovered.stats()["bytes"]["sources"], 0)
        self.assertEqual(recovered.get(saved["id"])["item"]["sources"][0]["sha256"], qb.digest(original.read_bytes()))
        with recovered.connection() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM events").fetchone()[0], 2)
        with self.assertRaisesRegex(qb.BankError, "existing bank left intact"):
            recovered.restore(archive)

    def test_tampered_or_unsafe_archive_is_rejected_without_replacing_bank(self):
        self.save()
        source = self.work / "backup.zip"
        self.bank.backup(source)
        for name in ("bank.sqlite", "../escape"):
            tampered = self.work / ("bad" + str(len(name)) + ".zip")
            with zipfile.ZipFile(source) as old, zipfile.ZipFile(tampered, "w") as new:
                for entry in old.namelist():
                    new.writestr(entry, b"corrupt" if entry == name else old.read(entry))
                if name == "../escape":
                    new.writestr(name, b"outside")
            with self.assertRaises(qb.BankError):
                qb.Bank(self.work / "target").restore(tampered)
            self.assertFalse((self.work / "target").exists())
        self.assertFalse((self.work / "escape").exists())

    def test_no_attachment_dependency_and_incompatible_schema_are_reported(self):
        source = self.work / "source.txt"
        source.write_text("raw", encoding="utf-8")
        saved = self.save(sources=[{"file": str(source), "locator": "1"}])
        source.unlink()
        self.assertTrue(self.bank.doctor()["ok"])
        self.assertIn("sha256", self.bank.get(saved["id"])["item"]["sources"][0])
        con = sqlite3.connect(self.bank.db)
        try:
            con.execute("PRAGMA user_version=99")
            con.commit()
        finally:
            con.close()
        with self.assertRaisesRegex(qb.BankError, "incompatible"):
            self.bank.stats()

    def test_file_source_needs_question_locator_to_avoid_merging_a_whole_page(self):
        source = self.work / "page.txt"
        source.write_text("two synthetic questions on one page", encoding="utf-8")
        self.proposal(sources=[{"file": str(source)}])
        with self.assertRaisesRegex(qb.BankError, "locator"):
            self.bank.preview(self.file)
        one = self.save(sources=[{"file": str(source), "locator": "q1"}])
        self.proposal(stem="计算两个数的和：12与19。", answer="31", sources=[{"file": str(source), "locator": "q2"}])
        two = self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic distinct question")
        self.assertNotEqual(one["id"], two["id"])

    def test_automatic_snapshot_preserves_prior_state_and_manual_backups(self):
        self.save()
        manual = self.bank.home / "backups" / "my-manual.zip"
        self.bank.backup(manual)
        self.guide()
        automatic = list((self.bank.home / "backups").glob("auto-*.zip"))
        self.assertEqual(len(automatic), 1)
        restored = qb.Bank(self.work / "pre-change")
        restored.restore(automatic[0])
        self.assertEqual(restored.stats()["questions"], 1)
        self.assertIsNone(restored.read_guide("初中", "数学"))
        config = self.bank.config()
        config["backup_keep"] = 1
        (self.bank.home / "config.json").write_text(qb.encoded(config), encoding="utf-8")
        # Copy an authentic older auto snapshot to exercise bounded retention.
        older = automatic[0].with_name("auto-2000-01-01-abcdef12.zip")
        older.write_bytes(automatic[0].read_bytes())
        os.utime(older, (1, 1))
        self.guide("# 初中数学\n每次写入均保存上一代，默认只留一份。")
        self.assertEqual(len(list((self.bank.home / "backups").glob("auto-*.zip"))), 1)
        self.assertTrue(manual.exists())
        newest = list((self.bank.home / "backups").glob("auto-*.zip"))[0]
        restored_latest = qb.Bank(self.work / "latest")
        restored_latest.restore(newest)
        self.assertIsNotNone(restored_latest.read_guide("初中", "数学"))

    def test_global_path_independent_of_workdir_and_skill_reinstallation(self):
        env = dict(os.environ, MWS_DATA_HOME=str(self.bank.home), PYTHONUTF8="1")
        self.save()
        for directory in (self.work, self.work.parent):
            p = subprocess.run([sys.executable, str(SCRIPT), "stats"], cwd=directory, env=env, capture_output=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["questions"], 1)
        installed = self.work / "reinstalled-skill" / "scripts"
        installed.mkdir(parents=True)
        copied = installed / "question_bank.py"
        copied.write_bytes(SCRIPT.read_bytes())
        p = subprocess.run([sys.executable, str(copied), "stats"], cwd=self.work, env=env, capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["questions"], 1)

    def test_export_is_text_and_cli_has_no_unconditional_yes_switch(self):
        self.save()
        self.guide()
        out = self.work / "export.jsonl"
        self.bank.export(out)
        records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual({r["kind"] for r in records}, {"question", "guide"})
        self.proposal()
        p = subprocess.run([sys.executable, str(SCRIPT), "commit", "--file", str(self.file), "--home", str(self.work / "denied")], capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1)
        self.assertIn("approval", p.stderr)
        self.assertFalse((self.work / "denied").exists())


if __name__ == "__main__":
    unittest.main()
