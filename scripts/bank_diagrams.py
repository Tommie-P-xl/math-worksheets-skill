"""Render stored TikZ/pgfplots into embedded browser previews with existing TeX tools."""
import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from geometry_labels import place_labels

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def preview_picture(picture):
    """Give numeric geometry a readable preview scale and unobstructed point labels."""
    coordinates = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(
        r"\\coordinate\s*\(([^)]+)\)\s*at\s*\(\s*(" + NUMBER + r")\s*,\s*(" + NUMBER + r")\s*\)", picture)}
    opening = re.match(r"\\begin\{tikzpicture\}(\[[^\n]*?\])?", picture)
    options = opening[1] or ""
    if not coordinates or any(token in options for token in ("xscale", "yscale", "rotate", "transform shape", "x=", "y=")):
        return picture
    scale_match = re.search(r"\bscale\s*=\s*(" + NUMBER + ")", options)
    scale = float(scale_match[1]) if scale_match else 1.0
    extent = max(max(p[i] for p in coordinates.values()) - min(p[i] for p in coordinates.values()) for i in (0, 1))
    if extent > 0 and 0 < scale * extent < 4.5:
        scale = 6.0 / extent
        if scale_match:
            options = options[:scale_match.start()] + f"scale={scale:.7f}" + options[scale_match.end():]
        else:
            options = "[scale=" + str(scale) + ("," + options[1:-1] if options else "") + "]"
        picture = r"\begin{tikzpicture}" + options + picture[opening.end():]
    if scale <= 0:
        return picture
    labels = list(re.finditer(r"\\node(?:\[([^\n]*?)\])?\s*at\s*\(([^)]+)\)\s*\{\s*(\$[^$]+\$)\s*\}\s*;", picture))
    def point_label(match):
        return (match[2] in coordinates and re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", match[2])
                and re.fullmatch(r"\$[A-Za-z](?:_\{?\d+\}?|\d+)?(?:['′]|\\prime)*\$", match[3])
                and match[3][1] == match[2][0])
    points = {m[2]: coordinates[m[2]] for m in labels if point_label(m)}
    segments = []
    for path in re.finditer(r"\\(?:draw|path)(?:\[[^\n]*?\])?([^;]*);", picture):
        vertices = list(re.finditer(r"\(([^)]+)\)", path[1]))
        for a, b in zip(vertices, vertices[1:]):
            if a[1] in coordinates and b[1] in coordinates and "--" in path[1][a.end():b.start()]:
                segments.append((coordinates[a[1]], coordinates[b[1]]))
        if vertices and "cycle" in path[1] and vertices[-1][1] in coordinates and vertices[0][1] in coordinates:
            segments.append((coordinates[vertices[-1][1]], coordinates[vertices[0][1]]))
    if not points or not segments:
        return picture
    placed = place_labels(points, segments, scale_cm=scale, font_pt=11)

    def replace(match):
        if not point_label(match) or match[2] not in placed:
            return match[0]
        x, y = placed[match[2]]["center"]
        font = re.search(r"font\s*=\s*\\[A-Za-z]+", match[1] or "")
        style = "," + font[0] if font else ""
        return f"\\node[anchor=center,fill=none,inner sep=0pt,outer sep=0pt{style}] at ({x:.7f},{y:.7f}) {{{match[3]}}};"

    return re.sub(r"\\node(?:\[([^\n]*?)\])?\s*at\s*\(([^)]+)\)\s*\{\s*(\$[^$]+\$)\s*\}\s*;", replace, picture)


def render_diagram(diagram, enabled=True):
    """Return all saved question figures; never compile answer_overlay into the stem."""
    code = diagram.get("code", "")
    if not code or diagram.get("format", "tikz") not in ("tikz", "pgfplots"):
        return [], ""
    if not enabled:
        return [], "已关闭 TikZ/pgfplots 预览；题干与解答文字仍可查看。"
    engine = shutil.which("xelatex") or shutil.which("pdflatex")
    converter = shutil.which("pdftoppm")
    if not engine or not converter:
        return [], "未生成题图：需要 XeLaTeX（或 pdfLaTeX）及 Poppler 的 pdftoppm；安装后重新生成浏览页。"
    unicode_text = bool(re.search(r"[^\x00-\x7f]", code))
    if unicode_text and Path(engine).stem.lower() != "xelatex":
        return [], "未生成题图：图中文字含 Unicode，需要 XeLaTeX 与相应字体；安装后重新生成浏览页。"
    # Bank code may contain worksheet minipage/center wrappers. Each original
    # tikzpicture becomes one page/image, preserving the drawings and their order.
    pictures = re.findall(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", code, re.S)
    if not pictures:
        pictures = ["\\begin{tikzpicture}\n" + code + "\n\\end{tikzpicture}"]
    try:
        pictures = [preview_picture(picture) for picture in pictures]
    except ValueError as exc:
        return [], "题图标签布局失败：" + str(exc)[:240]
    cjk = r"\usepackage[UTF8,fontset=fandol]{ctex}" if unicode_text else ""
    source = r"""\documentclass[multi=tikzpicture,border=5pt]{standalone}
\usepackage{amsmath,amssymb,tikz,pgfplots}
\usetikzlibrary{calc,angles,quotes,arrows.meta,positioning,intersections,patterns,backgrounds,decorations.pathreplacing,decorations.markings}
\pgfplotsset{compat=1.18}
""" + cjk + "\n\\begin{document}\n" + "\n".join(pictures) + "\n\\end{document}\n"
    environment = dict(os.environ, openout_any="p", openin_any="p")
    try:
        with tempfile.TemporaryDirectory(prefix="mws-diagram-") as tmp:
            work = Path(tmp)
            (work / "figure.tex").write_text(source, encoding="utf-8")
            result = subprocess.run([engine, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "figure.tex"],
                                    cwd=work, env=environment, capture_output=True, timeout=60)
            if result.returncode or not (work / "figure.pdf").is_file():
                log = result.stdout.decode("utf-8", errors="replace")
                error = next((line.strip() for line in log.splitlines() if line.startswith("!")), "检查保存的绘图代码及 LaTeX 依赖。")
                return [], "题图编译失败：" + error[:240]
            result = subprocess.run([converter, "-png", "-r", "240", "figure.pdf", "preview"],
                                    cwd=work, capture_output=True, timeout=60)
            images = sorted(work.glob("preview-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
            if result.returncode or len(images) != len(pictures):
                return [], "题图转换失败：生成的预览数量与保存的图形不一致。"
            return ["data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii") for p in images], ""
    except subprocess.TimeoutExpired:
        return [], "题图渲染超时；题干与解答文字仍可查看。"
    except OSError as exc:
        return [], "题图渲染工具不可用：" + str(exc)[:240]
