# v3.7.2

- Default to compact question layout; require an explicit spacious declaration for requested working areas.
- Apply workspace minimums only to spacious worksheets and remove implicit workspace/two-column assumptions from the page budget.
- Add a lightweight label-placement helper: try nearby candidates, reject line/text collisions, and emit transparent labels. Use it to rebuild all point labels in the photograph example, including O/H.
- Organize both READMEs by Function 1 and Function 2, with current layout guidance.

## v3.7.1

- Restore the upstream's original three-column output previews with attribution.
- Expand English/Chinese READMEs with installation steps and copyable prompts for original practice scenarios and new reproduction/explanation scenarios.
- Add a real uploaded Chinese geometry photograph example: original image, reviewed transcription, code-drawn figures, printable worksheet/key, previews and reproducible symbolic checks.
- Add automatic/explicit XeLaTeX support for CJK documents and test Chinese text through the complete gate chain.
- Keep documentation images and example PDFs outside the runtime-only CC Switch ZIP.

The example passes 10 machine checks and retains 2 manual geometric-reasoning entries. Its student PDF excludes handwritten answers and solution-only annotations.

## v3.7.0

- Trim historical evaluation data, scoring tools, sample images and redundant development files; retain mathematical verification, templates and references.
- Move mandatory runtime checks into scripts/checks and retain focused smoke/integration tests outside the installable package.
- Add faithful reproduction of questions from text/screenshots/photos, handwritten-interference handling, independently verified solutions and reviewed external-image support.
- Make study guides optional for reproduction; support worksheet-only requests while keeping internal answer verification.
- Prefer concise solutions and add programmatic explanation diagrams when they clarify difficult reasoning.
- Add concise English/Chinese READMEs and deterministic CC Switch ZIP assets with SHA256 checksums.
- Use one SymPy-capable Python consistently across build checks and compilation-log validation, including Windows Python selection.

Manual answers, source transcription and external image content remain review-dependent. No new claim of fully automated visual or proof correctness is made.
