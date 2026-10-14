# Concise solutions and explanatory figures

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
