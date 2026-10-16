# Reproduce questions from text or images

For each uploaded question, offer optional global-bank archival separately from
reproduction: show proposed stage/grade/exam, knowledge/type tags and ask whether
to save and whether metadata is correct. Default is no save. Follow
[question-bank.md](question-bank.md) for preview/approval; never archive an upload
or a guide update merely because the user requested a worksheet.

Default to compact stems with no reserved writing area. Add working space only
when requested and declare `\worksheetlayout{spacious}`. Geometry labels must
be transparent and displaced into a free sector: no text crossing lines and no
white boxes erasing linework. Keep original inline blanks and mathematical content.

Use this workflow when the user already supplies the questions. These rules
override new-question authoring defaults.

## Recover the original question

1. Read the complete source, including directions, answer choices, subparts,
   units, interval endpoints, diagram labels and mathematical constraints.
   Agent vision is preferred for screenshots/photos; OCR is an aid, not truth.
2. Separate printed content and original hand-drawn givens from later solving:
   pencil calculations, circled choices, correction marks and teacher annotations.
   A handwritten graph may be an original given or a student's answer: decide
   from context, not simply from whether it is handwritten.
3. Exclude later answers and working from the student worksheet. Retain them
   privately if useful for checking. Never copy them into the answer key unchecked.
4. Preserve original notation, numbers, options, question order, language and
   graph conventions. Improve typography and work space without changing meaning.
5. Zoom/crop for inspection where supported. Do not guess a symbol, bound, tick,
   hidden condition or obscured label from what makes the problem solvable.
   If an important item remains uncertain, ask a targeted question identifying
   the problem and alternatives, or request a clearer close-up. Continue other
   clear problems while waiting; do not finalize the affected problem.

Keep an internal transcription/review record. `uncertainties: []` means all
material ambiguities were resolved, not that the agent merely chose a guess.
The source-review flag records agent review; it does not require user approval
when the original is clear.

## Rebuild figures

For mathematical content, use TikZ/pgfplots or another deterministic plotting
program when practical. Copy the actual function, domain, coordinate scale,
geometry relations, open/closed endpoints, labels and data from the source.
Use [latex-templates.md](latex-templates.md) and shipped figure macros. Geometry
can be schematic when the source is not to scale; preserve all relevant relations
and state that it is not to scale if needed. Do not encode an unsolved answer in
the worksheet drawing. A graph supplied without a formula must not gain an
invented function: reproduce its observable shape/features or preserve the crop.

For real photos or complex illustrations (train, scene, textured object) that
cannot be faithfully reconstructed with simple drawing, explain which part is
needed and ask how the user wants it handled, in this preference order:

1. **User supplies a clean crop/image.** If the supplied original already has a
   clear, usable figure, offer to use that crop; do not request a duplicate upload.
   Preserve proportions and resolution; do not crop away givens. Do not erase
   handwriting across unknown printed information and pretend to recover it.
2. **Image generation, if supported.** Use the host's image-generation tool only
   after the user chooses this method. Treat the result as an illustration;
   verify dimensions, objects and spatial relationships, and add exact math labels
   programmatically. Avoid generative reconstruction when pixel evidence is the
   question (photo measurement, object counting, etc.).
3. **Programmatic schematic approximation.** Suggest a simplified train/scene
   when appearance is incidental. The approximation must preserve all solving
   information, including length, motion direction and relative positions; obtain
   the user's choice before replacing the original complex image.

Offer a better equivalent if the context supports it, such as omitting a purely
decorative photo with the user's agreement. If the image contains indispensable
unreadable information, a clean original/clarification is required; image
generation is not a way to invent those givens.

Use external images through literal `\includegraphics[width=...]{assets/name.png}`
inside the owning problem, not a float between unrelated questions. Also include
`\usepackage{graphicx}` when needed. Prefer exact TikZ/pgfplots for mathematics;
program-generated PNG/PDF is allowed but still needs visual review because its
labels are opaque to source-based math checkers. Do not distort aspect ratio.

## Independently solve and build

Solve the recovered original before writing the answer key. Compare provided
working with your independent result and check all machine-checkable responses
with `verify.py`. Preserve a wrong printed premise rather than silently repairing
it: explain the issue and ask which version the user wants if it prevents a
well-defined question. See [solutions.md](solutions.md) for compact explanations.

If the solution introduces auxiliary constructions, the answer must show the
resulting labeled diagram. Typeset every mathematical quotient in the answer
with fully braced `\frac`, `\dfrac` or `\tfrac`, including coordinates and
intermediate steps. Keep original question text unchanged by these answer rules.

Default: worksheet + key; do not produce a guide unless requested. A worksheet-only
request still needs internal verification JSON. Omit pedagogical ramp/interleave
tags when reproducing a source; retain original order. Use `manual` honestly for
non-CAS parts; a completely manual set needs the verifier's explicit acknowledgement.

Write a separate `sources_STEM.json` beside the LaTeX, not extra fields inside
the verifier's strict JSON schema:

```json
{
  "mode": "reproduce",
  "problems": [
    {
      "id": 1,
      "source": "User screenshot 1, upper question",
      "transcription_reviewed": true,
      "uncertainties": [],
      "block_sha256": "SHA256 of the reviewed worksheet problem block"
    }
  ],
  "assets": [
    {
      "problem_id": 1,
      "role": "worksheet",
      "path": "assets/train.png",
      "method": "user-crop",
      "sha256": "SHA256 of the image file bytes",
      "visual_reviewed": true,
      "mathematical_content": true,
      "givens_reviewed": true
    }
  ]
}
```

One problem record per top-level problem, in document order. For no external
images, use `"assets": []`. Each image use has one asset record; `role` is
`worksheet` or `answer-key`. Set `mathematical_content: false` only for a genuinely
decorative picture; otherwise review image givens against the original AND
verification data and set `givens_reviewed: true`. This is a review record, not
automated visual proof. Allowed method descriptions include `user-crop`,
`image-generation`, `program-schematic` and `program-plot`.

After inspecting transcription and drawing, calculate `block_sha256` with the
same parser the gate uses (adjust paths as needed):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(SKILL_DIR) / "scripts" / "checks"))
from _tex_segments import blank_comments, segment_spans
from check_sources import digest
tex = blank_comments(Path(WS_TEX).read_text(encoding="utf-8"))
hashes = [digest(tex[a:b]) for a, b in segment_spans(tex)]
# Assign hashes in order to already-reviewed problem records.
```

The gate binds records to the current document and image bytes, catching stale
reviews after changes. Hashes cannot prove transcription accuracy. Review again
before updating hashes; do not auto-stamp unseen content just to satisfy a gate.

```bash
bash "$SKILL_DIR/scripts/build.sh" WORK/verify_STEM.json \
  --reproduce --sources WORK/sources_STEM.json --outdir OUTPUT
# Add --worksheet-only when no answer PDF is requested.
```

External images produce exit 2 for transparent review status. All CAS, units,
answer-slot and PDF layout gates still run. Mixed illustrated and text-only
questions are allowed in this mode because source review binds each figure to
its owning numbered problem. Inspect the rendered page to ensure that placement
is visually clear. A requested study guide can be built separately with
`--study-guide-only` and its own verification data.
