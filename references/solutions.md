# Concise solutions and explanatory figures

For crowded geometric point labels, use `scripts/geometry_labels.py`:
`tikz_labels(points, segments, scale_cm=..., font_pt=...)` tries eight directions
with small gap/tangential offsets. It checks conservative text boxes against
segments and other labels, then emits transparent TikZ nodes in nearby clear
positions. Include all construction lines and right-angle marks; approximate arcs
with short segments. Supply the actual print scale and font size. If no local
position fits, enlarge/reframe the drawing and retry. Font-box estimates still
need final PDF inspection; they are not a pixel-level guarantee.

Default to compact stems with no reserved writing area. Add working space only
when requested and declare `\worksheetlayout{spacious}`. Geometry labels must
be transparent and displaced into a free sector: no text crossing lines and no
white boxes erasing linework. Keep original inline blanks and mathematical content.

Default to a short, readable answer: the method or essential equation, the
decisive calculation and a boxed result. Include units, domains, excluded values,
all solutions and rounding where they matter. Show enough reasoning to verify
the result; avoid restating the stem, long conversational prose and repetitive
algebra. Expand only when the user asks or the reasoning needs it.

Add a program-generated explanation figure when it makes a difficult spatial
or abstract step easier to understand: an auxiliary line in geometry, intersections
or tangency on a function plot, a shaded integration region, a limiting process,
or a compact sign/variation chart. Simple algebra does not need a picture.

- Prefer TikZ/pgfplots and the shipped styles. Another deterministic plotting
  program may export an image when appropriate; visually verify it and, for
  reproduction, record it as an `answer-key` asset in the source manifest.
- Use the same function, data, units, axes and geometry conventions as the question.
  Distinguish givens, auxiliary constructions and computed results using labels,
  dashes or hatching that survive grayscale printing.
- Keep computed coordinates and special points tied to verification entries.
  Do not infer a root, angle or equality merely from a graph's appearance.
- Put answer-specific intersections, auxiliary lines and annotations in the key,
  not the student worksheet. An explanation figure must not reveal a solution
  in a problem that asks the student to construct it.
- Label a schematic as not to scale when needed. Never change relative order,
  topology, asymptotes, domains or endpoint inclusion to make a prettier picture.
- Explain the figure's purpose in one short sentence, then give the decisive step.
  Avoid multiple near-identical figures; use several only for a meaningful sequence.

For an abstract proof, use a figure as intuition and still state the necessary
logical argument. A diagram is not a proof. Mark non-CAS reasoning as `manual`
and machine-check any numeric/symbolic subparts separately.
