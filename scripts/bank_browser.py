"""Generate a portable offline question picker using only Python's standard library."""
import base64
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from question_bank import BankError, now
from bank_diagrams import render_diagram
from bank_content import content_nodes, answer_layout, answer_paragraphs, PICTURE, INLINE_FIGURE

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
SVG_TAGS = {"svg", "g", "path", "line", "polyline", "polygon", "rect", "circle", "ellipse", "text", "tspan", "title", "desc"}
SVG_ATTRS = {"xmlns", "viewBox", "width", "height", "x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "r", "rx", "ry",
             "d", "points", "transform", "fill", "fill-opacity", "stroke", "stroke-width", "stroke-dasharray",
             "stroke-linecap", "stroke-linejoin", "stroke-opacity", "opacity", "font-family", "font-size",
             "font-style", "font-weight", "text-anchor", "dominant-baseline", "dx", "dy", "role", "aria-label"}


def svg_preview(diagram):
    """Preview the supported static SVG subset; leave other code visible as source."""
    if diagram.get("format") != "svg" or not diagram.get("code"):
        return None
    code = diagram["code"]
    if "<!" in code:
        return None
    try:
        root = ET.fromstring(code)
    except ET.ParseError:
        return None
    if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        return None
    for element in root.iter():
        tag = element.tag.removeprefix("{http://www.w3.org/2000/svg}")
        if tag not in SVG_TAGS or any(key not in SVG_ATTRS or re.search(r"url\s*\(", value, re.I)
                                    for key, value in element.attrib.items()):
            return None
    if root.tag == "svg":
        root.set("xmlns", "http://www.w3.org/2000/svg")
        code = ET.tostring(root, encoding="unicode")
    # An image context cannot run scripts; CSP additionally forbids network access.
    return "data:image/svg+xml;base64," + base64.b64encode(code.encode("utf-8")).decode("ascii")


def math_assets():
    """Inline WOFF2 fonts so moving the HTML never breaks offline formula rendering."""
    vendor = TEMPLATES / "katex"
    css = (vendor / "katex.min.css").read_text(encoding="utf-8")

    def font(match):
        path = re.search(r"url\((?:['\"])?(fonts/[^)'\"]+\.woff2)(?:['\"])?\)", match.group())
        if not path:
            raise BankError("KaTeX CSS has an unsupported font source")
        data = base64.b64encode((vendor / path[1]).read_bytes()).decode("ascii")
        return f'src:url(data:font/woff2;base64,{data}) format("woff2")'

    css = re.sub(r"src:[^;}]+", font, css)
    scripts = "\n".join((vendor / name).read_text(encoding="utf-8")
                        for name in ("katex.min.js", "contrib/auto-render.min.js"))
    return css, scripts


def render_content(text, enabled=True, paragraphs=False):
    blocks = INLINE_FIGURE.findall(text)
    tikz = [block for block in blocks if not block.startswith("<svg")]
    compiled, note = render_diagram({"format": "tikz", "code": "\n".join(tikz)}, enabled=enabled) if tikz else ([], "")
    images, index = [], 0
    for block in blocks:
        if block.startswith("<svg"):
            image = svg_preview({"format": "svg", "code": block})
            if image is None:
                note = note or "此 SVG 含不支持的元素，未预览。"
        else:
            image = compiled[index] if index < len(compiled) else None
            index += 1
        images.append(image)
    nodes = content_nodes(text, images, note)
    return answer_paragraphs(nodes) if paragraphs else nodes, sum(bool(image) for image in images), note


def answer_overlay(diagram, solution):
    overlay = diagram.get("answer_overlay")
    if isinstance(overlay, dict):
        overlay = overlay.get("code", "")
    if not isinstance(overlay, str) or not overlay.strip() or "".join(overlay.split()) == "".join(solution.split()):
        return ""
    existing = set(INLINE_FIGURE.findall(solution))
    pictures = INLINE_FIGURE.findall(overlay)
    if pictures:
        return "\n".join(p for p in pictures if p not in existing)
    if re.search(r"\\(?:draw|node|coordinate)\b", overlay):
        original = PICTURE.findall(diagram.get("code", ""))
        if len(original) == 1:
            return original[0].replace(r"\end{tikzpicture}", overlay + "\n" + r"\end{tikzpicture}")
    return overlay


def export_browser(bank, out, demo=False, render_diagrams=True):
    out = Path(out).expanduser().resolve()
    skill = TEMPLATES.parent.resolve()
    if out.suffix.lower() != ".html" or out.is_relative_to(bank.home) or out.is_relative_to(skill):
        raise BankError("browse output must be an .html file outside bank storage and the skill installation")
    numbers = bank.short_ids()
    questions = []
    for row in bank.rows():
        item = json.loads(row["payload"])
        short_id = numbers.get(item["id"])
        if short_id is None:
            raise BankError(f"question {item['id']} has no archival event; use its full ID and inspect bank integrity")
        diagram = item.get("diagram", {})
        previews, preview_note = render_diagram(diagram, enabled=render_diagrams)
        content, answer_images, content_notes = {}, 0, []
        content["title"] = content_nodes(item["title"])
        content["summary"] = content_nodes(item["summary"])
        for field in ("stem", "answer", "solution"):
            text = answer_layout(item[field])
            content[field], count, note = render_content(text, render_diagrams, paragraphs=True)
            answer_images += count
            if note:
                content_notes.append({"field": field, "note": note})
        content["alternative_solutions"] = []
        for index, alternative in enumerate(item.get("alternative_solutions", []), 2):
            nodes, count, note = render_content(answer_layout(alternative["solution"]), render_diagrams, paragraphs=True)
            content["alternative_solutions"].append({"title": alternative["title"], "nodes": nodes})
            answer_images += count
            if note:
                content_notes.append({"field": f"alternative_solutions[{index - 2}]", "note": note})
        all_solutions = "\n".join([item["solution"], *(s["solution"] for s in item.get("alternative_solutions", []))])
        extra = answer_overlay(diagram, all_solutions)
        content["answer_extra"], count, note = render_content(answer_layout(extra), render_diagrams, paragraphs=True)
        answer_images += count
        if note:
            content_notes.append({"field": "answer_extra", "note": note})
        questions.append({"short_id": short_id, "revision": row["revision"], "updated": row["updated"],
                          "item": item, "preview": svg_preview(diagram), "previews": previews, "preview_note": preview_note,
                          "content": content, "content_images": answer_images, "content_notes": content_notes})
    questions.sort(key=lambda row: int(row["short_id"][1:]))
    packet = {"home": "演示题库（示例题号，非个人题库）" if demo else str(bank.home),
              "created": "示例数据" if demo else now(), "demo": demo,
              "limit": bank.config()["reference_limit"], "questions": questions}
    # Bank text is data, including literal </script> or HTML. Never interpolate it as markup.
    data = json.dumps(packet, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    css, scripts = math_assets()
    template = (TEMPLATES / "bank-browser.html").read_text(encoding="utf-8")
    # One substitution pass prevents bank content from being treated as another template token.
    replacements = {"MWS_DATA": data, "MWS_MATH_CSS": css, "MWS_MATH_JS": scripts,
                    "MWS_IMAGE_JS": (TEMPLATES / "html-to-image/html-to-image.js").read_text(encoding="utf-8"),
                    "MWS_BROWSER_JS": (TEMPLATES / "bank-browser.js").read_text(encoding="utf-8")}
    html = re.sub(r"@@(MWS_DATA|MWS_MATH_CSS|MWS_MATH_JS|MWS_IMAGE_JS|MWS_BROWSER_JS)@@", lambda match: replacements[match[1]], template)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"html": str(out), "questions": len(questions), "bytes": out.stat().st_size,
            "diagram_images": sum(len(q["previews"]) + bool(q["preview"]) for q in questions),
            "content_images": sum(q["content_images"] for q in questions),
            "diagram_warnings": ([{"short_id": q["short_id"], "note": q["preview_note"]} for q in questions if q["preview_note"]]
                                 + [{"short_id": q["short_id"], **note} for q in questions for note in q["content_notes"]]),
            "home": str(bank.home), "snapshot": True, "bank_changed": False}
