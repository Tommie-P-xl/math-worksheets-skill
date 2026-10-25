# Current release

- Upgrade the global bank to schema 2: complete text/code solutions and semantic
  diagrams, provenance metadata without uploaded attachment storage. Add an
  explicit, validated legacy-schema migration preserving question ids and revisions.
- Centralize live settings in global config.json; default to one previous-state
  automatic snapshot, with configurable retention and retrieval caps.
- Track guide review coverage per question revision and bind approved guide
  updates to the pending references they reviewed.
- Use compact 12 mm PDF margins and language-neutral shared components; disable
  name/date fields, automatic quick answers and report appendices by default.
- Document Windows/MSYS2/Git Bash, macOS and Linux use; add cross-platform core CI,
  explicit UTF-8 file IO, migration/restore and live-configuration regression tests.

- Read release identity exclusively from root VERSION. Keep package and source
  filenames independent of release identity; publish a fixed runtime-only archive
  using an explicit file allowlist, excluding tests and maintainer resources.
- Generate concise per-parameter descriptions and defaults in config.json using
  a standard-JSON _comments object. Preserve runtime values and backup/restore
  compatibility, and document every setting in both READMEs.
