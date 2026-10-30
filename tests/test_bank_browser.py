"""Reference selection, portable snapshots and ZIP browsing use synthetic banks only."""
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import question_bank as qb
import bank_browser as browser
from bank_diagrams import render_diagram


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mws-browser-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bank = qb.Bank(self.work / "中文 bank")
        self.file = self.work / "proposal.json"

    def save(self, **changes):
        item = qb.example()
        item.update(changes)
        self.file.write_text(qb.encoded(item), encoding="utf-8")
        return self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic fixture consent")

    def packet(self, file):
        html = file.read_text(encoding="utf-8")
        data = re.search(r'<script type="application/json" id="bank-data">(.*?)</script>', html, re.S)[1]
        return json.loads(data)

    def cli(self, *args, script=None):
        return subprocess.run([sys.executable, str(script or ROOT / "scripts/question_bank.py"),
                               "--home", str(self.bank.home), *map(str, args)],
                              cwd=self.work, capture_output=True, encoding="utf-8")

    def test_numbers_survive_guides_updates_inserts_and_backup_restore(self):
        first = self.save()
        self.assertEqual(first["short_id"], "Q1")
        guide = self.work / "guide.md"
        guide.write_text("# 初中数学\n方程先检查等式变形。", encoding="utf-8")
        preview = self.bank.guide_preview("初中", "数学", guide)
        self.bank.guide_commit("初中", "数学", guide, approved=preview["receipt"], note="synthetic consent")
        update = self.bank.get("q1")["item"]
        update["summary"] = "修订摘要"
        self.file.write_text(qb.encoded(update), encoding="utf-8")
        revised = self.bank.commit(self.file, self.bank.preview(self.file)["receipt"], "synthetic revision consent")
        self.assertEqual(revised["short_id"], "Q1")
        self.assertEqual(self.bank.get(first["id"]), self.bank.get("Q1"))
        later = self.save(stem="计算 $7+8$。", answer="15", solution="相加得15。")
        self.assertEqual(later["short_id"], "Q4")  # guide and revision events occupy 2 and 3
        snapshot = self.work / "backup.zip"
        self.bank.backup(snapshot)
        restored = qb.Bank(self.work / "restored")
        restored.restore(snapshot)
        self.assertEqual(restored.get("Q1"), self.bank.get("Q1"))
        self.assertEqual(restored.get("Q4"), self.bank.get("Q4"))

    def test_selected_references_preserve_order_deduplicate_aliases_and_enforce_cap(self):
        first = self.save()
        second = self.save(stem="计算 $9-4$。", answer="5", solution="相减得5。")
        result = self.bank.select([second["short_id"], "Q1", first["id"]], ["title", "stem", "solution"])
        self.assertEqual([r["id"] for r in result["references"]], [second["id"], first["id"]])
        self.assertEqual(result["reference_count"], 2)
        self.assertIn("solution", result["references"][0])
        for identity in ("Q999", "Q0", "Q01"):
            with self.assertRaisesRegex(qb.BankError, "unknown question"):
                self.bank.select(["Q1", identity], ["stem"])
        with self.assertRaisesRegex(qb.BankError, "unknown show field"):
            self.bank.select(["Q1"], ["bogus"])
        self.bank.write_config({"reference_limit": 1, "reference_default": 1})
        with self.assertRaisesRegex(qb.BankError, "reference_limit"):
            self.bank.select(["Q1", second["short_id"]], ["stem"])
        self.assertEqual(self.bank.select(["Q1", first["id"]], ["stem"])["reference_count"], 1)

    def test_show_and_select_cli_resolve_short_numbers_to_canonical_ids(self):
        saved = self.save()
        result = self.cli("show", "q1", "--fields", "stem,solution")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record["id"], saved["id"])
        self.assertEqual(record["short_id"], "Q1")
        selected = self.cli("select", "Q1", saved["id"], "--fields", "stem")
        self.assertEqual(json.loads(selected.stdout)["reference_count"], 1)
        self.assertNotEqual(self.cli("select", "Q1", "Q999").returncode, 0)

    def test_empty_browse_never_creates_bank_and_errors_are_json(self):
        output = self.work / "browse 空题库.html"
        result = self.cli("browse", "--out", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.packet(output)["questions"], [])
        self.assertFalse(self.bank.home.exists())
        invalid = self.cli("browse", "--out", self.bank.home / "bank.sqlite")
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("error", json.loads(invalid.stderr))
        self.assertFalse(self.bank.home.exists())

    def test_named_alternative_solutions_survive_storage_backup_and_browser(self):
        alternative = {"title": "几何法", "solution": r"由相似关系，\[x=2.\]" + '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" stroke="black"/></svg>'}
        saved = self.save(alternative_solutions=[alternative])
        self.assertEqual(self.bank.get(saved["short_id"])["item"]["alternative_solutions"], [alternative])
        selected = self.bank.select([saved["short_id"]], ["solution", "alternative_solutions"])
        self.assertEqual(selected["references"][0]["alternative_solutions"], [alternative])
        backup = self.work / "with-methods.zip"
        self.bank.backup(backup)
        restored = qb.Bank(self.work / "restored")
        restored.restore(backup)
        self.assertEqual(restored.get(saved["short_id"])["item"]["alternative_solutions"], [alternative])
        out = self.work / "methods.html"
        browser.export_browser(restored, out)
        method = self.packet(out)["questions"][0]["content"]["alternative_solutions"][0]
        self.assertEqual(method["title"], "几何法")
        self.assertTrue(any(n["type"] == "figure" and n["image"] for n in method["nodes"]))
        with self.assertRaises(qb.BankError):
            self.save(alternative_solutions=[{"title": "无解答"}])
        with self.assertRaises(qb.BankError):
            self.save(alternative_solutions=[{"title": "外部图", "solution": r"\includegraphics{x.png}"}])

    def test_legacy_stem_preview_uses_paragraphs_and_keeps_original_record(self):
        source = "已知直线l1。（1）若角ACD=角B，求证。（2）在（1）的条件下计算。"
        self.save(stem=source)
        out = self.work / "legacy.html"
        browser.export_browser(self.bank, out, render_diagrams=False)
        question = self.packet(out)["questions"][0]
        self.assertEqual(question["item"]["stem"], source)
        self.assertEqual(self.bank.get("Q1")["item"]["stem"], source)
        self.assertEqual([n["type"] for n in question["content"]["stem"]], ["paragraph"]*3)
        self.assertIn("并不代表漏题", out.read_text(encoding="utf-8"))

    def test_snapshot_is_read_only_moveable_and_treats_question_markup_as_data(self):
        stem = '文字 </script><script>alert(1)</script> @@MWS_MATH_JS@@ $\\frac{1}{2}$'
        self.save(stem=stem)
        before = {p.relative_to(self.bank.home).as_posix(): p.read_bytes()
                  for p in self.bank.home.rglob("*") if p.is_file()}
        output = self.work / "offline.html"
        report = browser.export_browser(self.bank, output)
        self.assertFalse(report["bank_changed"])
        self.assertEqual(before, {p.relative_to(self.bank.home).as_posix(): p.read_bytes()
                                 for p in self.bank.home.rglob("*") if p.is_file()})
        moved = self.work / "移动到新目录" / "题库.html"
        moved.parent.mkdir()
        output.rename(moved)
        html = moved.read_text(encoding="utf-8")
        self.assertEqual(self.packet(moved)["questions"][0]["item"]["stem"], stem)
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertIn("data:font/woff2;base64,", html)
        self.assertNotRegex(html, r'<script[^>]+src=|<link[^>]+href=|src:url\(fonts/')
        self.assertEqual(self.packet(moved)["questions"][0]["short_id"], "Q1")

    def test_diagrams_preview_static_svg_and_keep_tikz_and_overlays_as_code(self):
        svg = {"format": "svg", "givens": ["AB=3"], "code": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M0 0 L100 100" stroke="black"/></svg>'}
        self.assertTrue(browser.svg_preview(svg).startswith("data:image/svg+xml;base64,"))
        self.assertIsNotNone(browser.svg_preview({**svg, "code": '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="3"/></svg>'}))
        for code in ('<svg><script>alert(1)</script></svg>', '<svg onload="alert(1)"/>',
                     '<svg><image href="https://example.org/x.svg"/></svg>', '<svg><path fill="url(https://example.org)"/></svg>',
                     '<!DOCTYPE svg [<!ENTITY x "text">]><svg/>', '<svg'):
            self.assertIsNone(browser.svg_preview({**svg, "code": code}))
        diagram = {"format": "tikz", "givens": ["AB=3"], "code": r"\draw (0,0)--(1,1);", "answer_overlay": r"\draw[dashed] (0,1)--(1,0);"}
        self.save(diagram=diagram)
        out = self.work / "code.html"
        browser.export_browser(self.bank, out, render_diagrams=False)
        row = self.packet(out)["questions"][0]
        self.assertIsNone(row["preview"])
        self.assertEqual(row["item"]["diagram"], diagram)

    def test_missing_tex_tools_leave_clear_fallback_without_changing_source(self):
        diagram = {"format": "tikz", "givens": ["AB=3"], "code": r"\draw (0,0)--(1,1);"}
        self.save(diagram=diagram)
        with patch("bank_diagrams.shutil.which", return_value=None):
            report = browser.export_browser(self.bank, self.work / "missing-tools.html")
        row = self.packet(self.work / "missing-tools.html")["questions"][0]
        self.assertEqual(row["previews"], [])
        self.assertIn("pdftoppm", row["preview_note"])
        self.assertEqual(report["diagram_warnings"][0]["short_id"], "Q1")
        self.assertEqual(row["item"]["diagram"], diagram)

    @unittest.skipUnless(shutil.which("xelatex") and shutil.which("pdftoppm"), "TikZ preview needs XeLaTeX and Poppler")
    def test_default_browse_renders_all_tikz_parts_but_excludes_answer_overlay(self):
        diagram = {"format": "tikz", "givens": ["AB=3"],
                   "code": r"\par\begin{center}\begin{minipage}{.48\linewidth}\begin{tikzpicture}\draw (0,0)--(2,0)--(0,1)--cycle;\node[above] at (0,1){甲};\end{tikzpicture}\end{minipage}\begin{minipage}{.48\linewidth}\begin{tikzpicture}\draw (0,0) circle (1);\end{tikzpicture}\end{minipage}\end{center}",
                   "answer_overlay": r"\begin{tikzpicture}\draw[dashed] (0,0)--(1,1);\end{tikzpicture}"}
        self.save(diagram=diagram)
        before = self.bank.db.read_bytes()
        output = self.work / "rendered.html"
        report = browser.export_browser(self.bank, output)
        row = self.packet(output)["questions"][0]
        self.assertEqual(report["diagram_images"], 2)
        self.assertEqual(report["diagram_warnings"], [])
        self.assertEqual(len(row["previews"]), 2)
        self.assertEqual(report["content_images"], 1)
        self.assertTrue(row["content"]["answer_extra"][0]["image"])
        import base64
        for image in row["previews"]:
            png = base64.b64decode(image.split(",", 1)[1])
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertTrue(all(n > 20 for n in struct.unpack("!II", png[16:24])))
        self.assertEqual(self.bank.db.read_bytes(), before)
        self.assertEqual(row["item"]["diagram"], diagram)
        skipped = self.cli("browse", "--out", self.work / "no-images.html", "--no-diagrams")
        self.assertEqual(skipped.returncode, 0, skipped.stderr)
        self.assertEqual(self.packet(self.work / "no-images.html")["questions"][0]["previews"], [])

    @unittest.skipUnless(shutil.which("xelatex") and shutil.which("pdftoppm"), "TikZ preview needs XeLaTeX and Poppler")
    def test_pgfplots_render_and_invalid_tikz_is_reported_without_blank_image(self):
        images, note = render_diagram({"format": "pgfplots", "code": r"\begin{tikzpicture}\begin{axis}[width=5cm,height=4cm]\addplot {x^2};\end{axis}\end{tikzpicture}"})
        self.assertEqual(len(images), 1, note)
        images, note = render_diagram({"format": "tikz", "code": r"\begin{tikzpicture}\InvalidDrawingCommand\end{tikzpicture}"})
        self.assertEqual(images, [])
        self.assertIn("编译失败", note)

    def test_extracted_runtime_zip_can_browse_without_repository_or_packages(self):
        self.save(diagram={"format": "tikz", "givens": ["AB=3"],
                           "code": r"\begin{tikzpicture}\draw (0,0)--(3,0)--(0,2)--cycle;\end{tikzpicture}"})
        build = subprocess.run([sys.executable, str(ROOT / "tools/package_skill.py"), "--outdir", str(self.work)],
                               capture_output=True, encoding="utf-8")
        self.assertEqual(build.returncode, 0, build.stderr)
        with zipfile.ZipFile(self.work / "math-worksheets.zip") as archive:
            archive.extractall(self.work / "install")
            names = archive.namelist()
            self.assertIn("math-worksheets/templates/bank-browser.html", names)
            self.assertIn("math-worksheets/templates/katex/LICENSE", names)
            self.assertNotIn("math-worksheets/bank.sqlite", names)
        result = self.cli("browse", "--out", self.work / "from-zip.html",
                          script=self.work / "install/math-worksheets/scripts/question_bank.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.packet(self.work / "from-zip.html")["questions"][0]["short_id"], "Q1")
        if shutil.which("xelatex") and shutil.which("pdftoppm"):
            self.assertEqual(json.loads(result.stdout)["diagram_images"], 1)


if __name__ == "__main__":
    unittest.main()
