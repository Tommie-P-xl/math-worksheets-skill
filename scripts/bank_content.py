"""Turn saved text/LaTeX fragments into safe browser content nodes."""
import re

PICTURE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)
INLINE_FIGURE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}|<svg\b.*?</svg>", re.S)
ANSWER_ENV = re.compile(r"\\begin\{([^}]+)\}")
ANSWER_MARKER = re.compile(r"（[1-9][0-9]*）")
MATH_RUN = re.compile(r"[A-Za-z0-9\\∠△Δ√πθ][A-Za-z0-9\\{}_^=+*/().,'′<>|±≥≤≠∥⊥∠△Δ√πθ°²³−-]*")
TEXT_COMMANDS = {"textbf": "strong", "emph": "em", "textit": "em", "underline": "underline",
                 "text": "group", "textrm": "group", "textnormal": "group", "problem": "group"}
SPACING = {"par", "smallskip", "medskip", "bigskip", "newpage"}
IGNORED = {"centering", "noindent", "small", "scriptsize", "footnotesize", "normalsize", "protect", "noansline"}


def group_at(text, pos, opening="{", closing="}"):
    if pos >= len(text) or text[pos] != opening:
        return "", pos
    start, depth = pos + 1, 1
    pos += 1
    while pos < len(text):
        if text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in (opening, closing):
            pos += 2
            continue
        if text[pos] == opening:
            depth += 1
        elif text[pos] == closing:
            depth -= 1
            if not depth:
                return text[start:pos], pos + 1
        pos += 1
    return text[start:], pos


def plain_nodes(text):
    """Recognize legacy, undelimited maths without rewriting its arithmetic."""
    result, last = [], 0
    for match in MATH_RUN.finditer(text):
        value = match.group()
        if not value or value == "\\" or re.fullmatch(r"[A-Za-z]+", value) and not (len(value) == 1 or value.isupper() and len(value) <= 8):
            continue
        if match.start() > last:
            result.append({"type": "text", "text": text[last:match.start()]})
        value = re.sub(r"(?<![A-Za-z\\])(sqrt|sin|cos|tan|log|ln)(?=[{(0-9])", r"\\\1", value)
        value = value.translate(str.maketrans({"∠": r"\angle ", "△": r"\triangle ", "Δ": r"\triangle ",
                                              "∥": r"\parallel ", "⊥": r"\perp ", "≥": r"\ge ", "≤": r"\le ", "≠": r"\ne ",
                                              "−": "-", "°": r"^\circ ", "²": "^2", "³": "^3"}))
        # sqrt(…) is common in older plain-text records; retain nested arguments.
        while r"\sqrt(" in value:
            start = value.index(r"\sqrt(") + 5
            body, end = group_at(value, start, "(", ")")
            value = value[:start] + "{" + body + "}" + value[end:]
        result.append({"type": "math", "text": value, "display": False})
        last = match.end()
    if last < len(text):
        result.append({"type": "text", "text": text[last:]})
    return result


class ContentParser:
    def __init__(self, text, images=(), figure_note=""):
        self.text, self.pos = text, 0
        self.images, self.figure_note, self.figure_index = images, figure_note, 0

    def child(self, body):
        child = ContentParser(body, self.images, self.figure_note)
        child.figure_index = self.figure_index
        result = child.parse()
        self.figure_index = child.figure_index
        return result

    def parse(self, stop_list=False):
        nodes, buffer = [], []

        def flush():
            if buffer:
                nodes.extend(plain_nodes("".join(buffer)))
                buffer.clear()

        while self.pos < len(self.text):
            if stop_list and (self.text.startswith(r"\item", self.pos) or self.text.startswith(r"\end{enumerate}", self.pos) or self.text.startswith(r"\end{itemize}", self.pos)):
                break
            if self.text.startswith(r"\begin{tikzpicture}", self.pos) or self.text.startswith("<svg", self.pos):
                match = INLINE_FIGURE.match(self.text, self.pos)
                if match:
                    flush()
                    image = self.images[self.figure_index] if self.figure_index < len(self.images) else None
                    nodes.append({"type": "figure", "image": image, "index": self.figure_index + 1,
                                  "code": match.group(), "format": "svg" if match.group().startswith("<svg") else "tikz",
                                  "note": self.figure_note if not image else ""})
                    self.figure_index += 1
                    self.pos = match.end()
                    continue
            delimiter = next((pair for pair in (("$$", "$$", True), ("$", "$", False), (r"\[", r"\]", True), (r"\(", r"\)", False))
                              if self.text.startswith(pair[0], self.pos)), None)
            if delimiter:
                end = self.text.find(delimiter[1], self.pos + len(delimiter[0]))
                if end >= 0:
                    flush()
                    nodes.append({"type": "math", "text": self.text[self.pos + len(delimiter[0]):end], "display": delimiter[2]})
                    self.pos = end + len(delimiter[1])
                    continue
            if self.text.startswith("\\\\", self.pos):
                flush()
                nodes.append({"type": "break"})
                self.pos += 2
                continue
            if self.text[self.pos] == "{":
                if buffer and "".join(buffer).endswith(("_", "^")):
                    start = self.pos
                    _, self.pos = group_at(self.text, self.pos)
                    buffer.append(self.text[start:self.pos])
                    continue
                flush()
                body, self.pos = group_at(self.text, self.pos)
                nodes.extend(self.child(body))
                continue
            command = re.match(r"\\([A-Za-z]+)", self.text[self.pos:])
            if not command:
                buffer.append(self.text[self.pos])
                self.pos += 1
                continue
            name = command[1]
            start = self.pos
            after = self.pos + len(command[0])
            if name in ("begin", "end"):
                flush()
                environment, self.pos = group_at(self.text, after)
                options = ""
                if self.pos < len(self.text) and self.text[self.pos] == "[":
                    options, self.pos = group_at(self.text, self.pos, "[", "]")
                if name == "begin" and environment in ("enumerate", "itemize"):
                    items = []
                    while self.pos < len(self.text):
                        while self.pos < len(self.text) and self.text[self.pos].isspace():
                            self.pos += 1
                        if not self.text.startswith(r"\item", self.pos):
                            break
                        self.pos += 5
                        if self.pos < len(self.text) and self.text[self.pos] == "[":
                            _, self.pos = group_at(self.text, self.pos, "[", "]")
                        items.append(self.parse(stop_list=True))
                    closing = r"\end{" + environment + "}"
                    if self.text.startswith(closing, self.pos):
                        self.pos += len(closing)
                    nodes.append({"type": "list", "items": items, "style": "bullet" if environment == "itemize" else "circled" if "textcircled" in options else "number"})
                elif environment in ("align", "align*", "equation", "equation*", "gather", "gather*") and name == "begin":
                    closing = r"\end{" + environment + "}"
                    end = self.text.find(closing, self.pos)
                    if end >= 0:
                        body = self.text[self.pos:end]
                        nodes.append({"type": "math", "text": r"\begin{aligned}" + body + r"\end{aligned}", "display": True})
                        self.pos = end + len(closing)
                elif environment == "minipage" and name == "begin":
                    _, self.pos = group_at(self.text, self.pos)
                continue
            if name in TEXT_COMMANDS or name in ("ans", "textcircled"):
                flush()
                body, self.pos = group_at(self.text, after)
                if name == "ans":
                    nodes.append({"type": "math", "text": r"\boxed{" + body + "}", "display": True})
                elif name == "textcircled":
                    body = re.sub(r"\\(?:scriptsize|small|protect)\s*", "", body).strip()
                    nodes.append({"type": "text", "text": chr(0x245F + int(body)) if body.isdigit() and 1 <= int(body) <= 20 else "（" + body + "）"})
                else:
                    nodes.append({"type": TEXT_COMMANDS[name], "children": self.child(body)})
                continue
            if name in SPACING:
                flush()
                nodes.append({"type": "break"})
                self.pos = after
                continue
            if name in IGNORED or name in ("hfill", "quad", "qquad"):
                self.pos = after
                if name in ("hfill", "quad", "qquad"):
                    buffer.append(" ")
                continue
            if name in ("needspace", "vspace", "hspace", "ansblank"):
                flush()
                self.pos = after
                if self.pos < len(self.text) and self.text[self.pos] == "[":
                    _, self.pos = group_at(self.text, self.pos, "[", "]")
                _, self.pos = group_at(self.text, self.pos)
                if name == "ansblank":
                    nodes.append({"type": "text", "text": "______"})
                continue
            # Preserve complete math-command groups for the legacy math recognizer.
            self.pos = after
            while self.pos < len(self.text) and self.text[self.pos] == "{":
                _, self.pos = group_at(self.text, self.pos)
            buffer.append(self.text[start:self.pos])
        flush()
        return nodes


def content_nodes(text, images=(), figure_note=""):
    return ContentParser(text, images, figure_note).parse()


def answer_paragraphs(nodes):
    """Make real paragraphs, instead of rendering source blank lines as spacing."""
    result, paragraph = [], []

    def flush():
        if any(node.get("type") != "text" or node["text"].strip() for node in paragraph):
            result.append({"type": "paragraph", "children": list(paragraph)})
        paragraph.clear()

    for node in nodes:
        if node["type"] == "text":
            for index, part in enumerate(re.split(r"\n+", node["text"])):
                if index:
                    flush()
                if part:
                    paragraph.append({"type": "text", "text": part})
        elif node["type"] == "break":
            flush()
        elif node["type"] in ("figure", "list") or node["type"] == "math" and node.get("display"):
            flush()
            result.append(node)
        else:
            paragraph.append(node)
    flush()
    return result


def answer_layout(text):
    """Separate prose/subparts, preserving every math, figure and TeX group byte.

    This is a layout fallback for legacy records, not a mathematical rewrite.
    Newly authored solutions should already use paragraphs and display equations.
    """
    parts, pos, depth = [], 0, 0
    while pos < len(text):
        protected = INLINE_FIGURE.match(text, pos)
        if protected:
            parts.append(protected.group())
            pos = protected.end()
            continue
        delimiter = next((pair for pair in (("$$", "$$"), ("$", "$"), (r"\[", r"\]"), (r"\(", r"\)"))
                          if text.startswith(pair[0], pos)), None)
        if delimiter:
            end = text.find(delimiter[1], pos + len(delimiter[0]))
            if end >= 0:
                end += len(delimiter[1])
                parts.append(text[pos:end])
                pos = end
                continue
        # Preserve whole mathematical/list environments; their own structure
        # determines line breaks. Layout wrappers remain traversable.
        environment = ANSWER_ENV.match(text, pos)
        if environment and environment[1] not in ("center", "minipage"):
            end_marker = r"\end{" + environment[1] + "}"
            end = text.find(end_marker, environment.end())
            if end >= 0:
                end += len(end_marker)
                parts.append(text[pos:end]); pos = end
                continue
        marker = (ANSWER_MARKER.match(text, pos) or '\u2460' <= text[pos] <= '\u2473') and (pos == 0 or text[pos - 1].isspace() or text[pos - 1] in "。；;" or text[max(0, pos - 4):pos] == r"\par")
        if depth == 0 and (text.startswith(r"\textbf{", pos) or marker):
            if parts and not "".join(parts[-2:]).endswith("\n\n"):
                parts.append("\n" if "".join(parts[-2:]).endswith("\n") else "\n\n")
        char = text[pos]
        if char == "{" and (pos == 0 or text[pos - 1] != "\\"):
            depth += 1
        elif char == "}" and (pos == 0 or text[pos - 1] != "\\"):
            depth = max(0, depth - 1)
        if char != "\n" or not "".join(parts[-2:]).endswith("\n\n"):
            parts.append(char)
        if depth == 0 and char == "。" and not text.startswith("\n", pos + 1):
            parts.append("\n")
        pos += 1
    return "".join(parts).strip()
