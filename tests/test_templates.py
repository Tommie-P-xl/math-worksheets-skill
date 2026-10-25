"""Check PDF margins, page numbers, neutral components and long-solution pagination."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
if os.name == "nt":
    BASH = next((p for p in ("C:/msys64/usr/bin/bash.exe", "C:/Git/usr/bin/bash.exe", "C:/Program Files/Git/bin/bash.exe") if Path(p).is_file()), BASH)


class TemplatePDF(unittest.TestCase):
    def test_compact_problem_allows_page_break_inside_long_solution(self):
        with tempfile.TemporaryDirectory(prefix="mws-long-") as tmp:
            work = Path(tmp)
            tex = work / "long.tex"
            tex.write_text(r"\documentclass{article}\input{worksheet-preamble}\begin{document}\problem{Firstmarker\newpage Lastmarker}\end{document}", encoding="utf-8")
            env = dict(os.environ, MWS_DATA_HOME=str(work / "data").replace("\\", "/"), PYTHONUTF8="1",
                       MWS_PYTHON=sys.executable.replace("\\", "/"), MWS_LATEX_ENGINE="pdflatex", MSYS2_PATH_TYPE="inherit")
            result = subprocess.run([BASH, "-l", str(ROOT / "scripts/compile.sh").replace("\\", "/"),
                                     str(tex).replace("\\", "/"), str(work).replace("\\", "/")],
                                    env=env, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = subprocess.run(["pdftotext", str(work / "long.pdf"), "-"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
            pages = text.split("\f")
            self.assertEqual(len(pages), 3)
            self.assertIn("Firstmarker", pages[0])
            self.assertIn("Lastmarker", pages[1])

    def test_live_margins_page_numbers_and_no_fixed_language(self):
        self.assertTrue(BASH and shutil.which("pdflatex") and shutil.which("pdftotext"), "PDF test dependencies required")
        with tempfile.TemporaryDirectory(prefix="mws-layout-") as tmp:
            work = Path(tmp)
            data = work / "data"
            data.mkdir()
            tex = work / "layout.tex"
            tex.write_text(r"""\documentclass[12pt,a4paper]{article}
\input{worksheet-preamble}
\input{figure-macros}
\begin{document}
\wstitleblock{Requested title}{}{}
Content marker.
\refrt
\begin{formulabox}Formula content.\end{formulabox}
\begin{examplebox}Example content.\end{examplebox}
\begin{tryitbox}Practice content.\end{tryitbox}
\begin{watchoutbox}Caution content.\end{watchoutbox}
\end{document}
""", encoding="utf-8")
            env = dict(os.environ, MWS_DATA_HOME=str(data).replace("\\", "/"), PYTHONUTF8="1",
                       MWS_PYTHON=sys.executable.replace("\\", "/"), MWS_LATEX_ENGINE="pdflatex", MSYS2_PATH_TYPE="inherit")
            positions = []
            for index, margin in enumerate((12, 20)):
                (data / "config.json").write_text(json.dumps({"page_margin_left_mm": margin, "page_numbers": index == 0}), encoding="utf-8")
                out = work / str(index)
                result = subprocess.run([BASH, "-l", str(ROOT / "scripts/compile.sh").replace("\\", "/"),
                                         str(tex).replace("\\", "/"), str(out).replace("\\", "/")],
                                        env=env, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                pdf = out / "layout.pdf"
                text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
                for unwanted in ("Name:", "Date:", "continued", "Answer Key", "Skills Summary", "RULE", "EXAMPLE", "TRY IT", "WATCH OUT", "Use this reference", "How every triangle"):
                    self.assertNotIn(unwanted, text)
                self.assertEqual(bool(re.search(r"(?m)^1$", text)), index == 0)
                bbox = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
                position = re.search(r'<word xMin="([\d.]+)"[^>]*>Content</word>', bbox)
                self.assertIsNotNone(position)
                positions.append(float(position[1]))
            self.assertAlmostEqual(positions[1] - positions[0], 8 * 72 / 25.4, delta=0.1)


if __name__ == "__main__":
    unittest.main()
