"""Check readable content, safe nodes and preview layout without changing saved data."""
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bank_content import content_nodes, answer_layout, answer_paragraphs
from bank_browser import render_content, answer_overlay
from bank_diagrams import preview_picture
from geometry_labels import segment_hits_box, boxes_overlap


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))
        for item in node.get("items", []):
            yield from walk(item)


class ContentTests(unittest.TestCase):
    def test_answer_paragraphs_preserve_math_code_and_inline_references(self):
        source = r"（1）由条件得 $x=1$。结合（1）可知结论。（2）计算\[f(1)=2\]。"
        formatted = answer_layout(source)
        self.assertIn("\n\n（2）", formatted)
        self.assertIn("结合（1）", formatted)
        self.assertIn(r"\[f(1)=2\]", formatted)
        self.assertEqual(re.sub(r"\s", "", source), re.sub(r"\s", "", formatted))
        self.assertEqual(answer_layout(formatted), formatted)
        figure = r"\begin{tikzpicture}\node at (0,0){中文。标签};\end{tikzpicture}"
        self.assertIn(figure, answer_layout("作图。" + figure))
        nodes = content_nodes("第一步。\n\n\n第二步。\n" + r"\[x=1\]" + "\n结论。")
        paragraphs = answer_paragraphs(nodes)
        self.assertEqual([node["type"] for node in paragraphs], ["paragraph", "paragraph", "math", "paragraph"])
        self.assertEqual([node["text"] for node in walk(paragraphs) if node["type"] == "math"], ["x=1"])

    def test_nested_questions_and_answer_macros_become_readable_content(self):
        source = r"\textbf{题目}\begin{enumerate}[label=（\arabic*）,leftmargin=2em]\item 求 $x$。\begin{enumerate}[label=\protect\textcircled{\scriptsize\arabic*}]\item 解方程；\item 验算。\end{enumerate}\item 写结论。\end{enumerate}\par\ans{x=\frac{3}{2}}"
        nodes = content_nodes(source)
        lists = [node for node in walk(nodes) if node["type"] == "list"]
        self.assertEqual([len(node["items"]) for node in lists], [2, 2])
        self.assertEqual([node["style"] for node in lists], ["number", "circled"])
        self.assertIn(r"\boxed{x=\frac{3}{2}}", [node["text"] for node in walk(nodes) if node["type"] == "math"])
        text = "".join(node["text"] for node in walk(nodes) if node["type"] == "text")
        self.assertIn("验算", text)
        self.assertNotRegex(text, r"\\(?:begin|item|ans|textbf|par)")

    def test_undelimited_legacy_maths_keep_expressions_and_subscripts(self):
        nodes = content_nodes(r"AC=2\sqrt{21}，CP=9sqrt5/5，S_{ABC}=18，\textbf{结论}：$x=\frac{1}{2}$。")
        maths = [node["text"] for node in walk(nodes) if node["type"] == "math"]
        self.assertIn(r"AC=2\sqrt{21}", maths)
        self.assertIn(r"CP=9\sqrt5/5", maths)
        self.assertIn(r"S_{ABC}=18", maths)
        self.assertIn(r"x=\frac{1}{2}", maths)

    def test_question_text_is_never_interpreted_as_html(self):
        source = '<script>alert(1)</script><img src="x" onerror="alert(1)">'
        nodes = content_nodes(source)
        self.assertFalse(any(node["type"] in ("html", "script", "img") for node in walk(nodes)))
        self.assertIn("<", "".join(node.get("text", "") for node in walk(nodes)))

    def test_solution_figures_remain_in_place_and_duplicate_overlays_are_not_repeated(self):
        picture = r"\begin{tikzpicture}\draw (0,0)--(2,1);\end{tikzpicture}"
        source = r"\textbf{作辅助线}：$AB\perp CD$。" + picture + r"\ans{x=2}"
        with patch("bank_browser.render_diagram", return_value=(["data:image/png;base64,fixture"], "")):
            nodes, count, note = render_content(source)
        figures = [node for node in walk(nodes) if node["type"] == "figure"]
        self.assertEqual(count, 1)
        self.assertEqual(note, "")
        self.assertTrue(figures[0]["image"])
        self.assertEqual(figures[0]["code"], picture)
        self.assertEqual(figures[0]["format"], "tikz")
        self.assertLess(next(i for i, node in enumerate(nodes) if node["type"] == "figure"), next(i for i, node in enumerate(nodes) if node.get("text") == r"\boxed{x=2}"))
        self.assertEqual(answer_overlay({"answer_overlay": source}, source), "")
        self.assertEqual(answer_overlay({"answer_overlay": picture}, source), "")

    def test_svg_solution_figures_use_the_same_safe_image_preview(self):
        source = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="3"/></svg>'
        nodes, count, note = render_content(source)
        self.assertEqual(count, 1)
        self.assertEqual(note, "")
        self.assertTrue(nodes[0]["image"].startswith("data:image/svg+xml;base64,"))
        self.assertEqual(nodes[0]["code"], source)
        self.assertEqual(nodes[0]["format"], "svg")

    def test_tiny_geometry_is_enlarged_and_labels_clear_segments(self):
        source = r"\begin{tikzpicture}[scale=.55]\coordinate(A)at(0,1);\coordinate(B)at(0,0);\coordinate(C)at(1,0);\coordinate(D)at(1,1);\draw(A)--(B)--(C)--(D)--cycle;\draw(A)--(C);\node[above left]at(A){$A$};\node[above left]at(B){$B$};\node[above left]at(C){$C$};\node[above left]at(D){$D$};\end{tikzpicture}"
        preview = preview_picture(source)
        scale = float(re.search(r"scale=([0-9.]+)", preview)[1])
        self.assertGreaterEqual(scale, 4.5)
        self.assertIn(r"\coordinate(A)at(0,1)", preview)
        self.assertNotIn("fill=white", preview)
        centers = re.findall(r"at \(([-0-9.]+),([-0-9.]+)\) \{\$([A-D])\$\}", preview)
        self.assertEqual(len(centers), 4)
        unit = scale * 72.27 / 2.54
        boxes = [(float(x) * unit - 4.4, float(y) * unit - 4.675, float(x) * unit + 4.4, float(y) * unit + 4.675) for x, y, _ in centers]
        points = {"A": (0, unit), "B": (0, 0), "C": (unit, 0), "D": (unit, unit)}
        for box in boxes:
            for a, b in (("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("A", "C")):
                self.assertFalse(segment_hits_box(points[a], points[b], box, margin=1.4))
        for index, box in enumerate(boxes):
            self.assertFalse(any(boxes_overlap(box, other, 1.4) for other in boxes[index + 1:]))

    def test_numeric_angle_annotations_are_not_repositioned_as_point_names(self):
        annotation = r"\node[below]at(A){$30^\circ$};"
        source = r"\begin{tikzpicture}\coordinate(A)at(0,1);\coordinate(B)at(0,0);\coordinate(C)at(1,0);\draw(A)--(B)--(C)--cycle;\node[left]at(A){$A$};" + annotation + r"\end{tikzpicture}"
        self.assertIn(annotation, preview_picture(source))


if __name__ == "__main__":
    unittest.main()
