# Changelog

## 0.4.0 — Round 11 improvements

### Added

- **Step constraint enforcement** — `INT`/`FLOAT` widget values are now validated against the `step` field exposed by `/object_info`. Misaligned values produce warning-level findings with two-sided float tolerance.
- **Subgraph definition editing** — `edit_workflow` now supports six ops for modifying inner subgraph definitions without unwrapping the parent workflow:
  - `add_node_to_definition`
  - `remove_node_from_definition`
  - `set_title_in_definition`
  - `set_mode_in_definition`
  - `connect_in_definition`
  - `set_widget_in_definition`
  Nested definitions remain unsupported and raise `NotImplementedError`.
- **Subgraph materialization diagnostics** — `subgraph.flatten()` returns a third `diagnostics` element that reports boundary links dropped during flattening, and `validate()` warns when inner nodes lack an `inputs` array.
- **`view_output` metadata** — the tool now returns `{"image": <Image>, "meta": {...}}` so text-only or metadata-bearing outputs can carry filename, format, dimensions, and subfolder alongside the image bytes.
- **Comfy Org API key support** — when `COMFY_API_KEY` is set in the environment, `run_workflow` injects it into the prompt payload as `extra_data.api_key_comfy_org`. Omitting the variable leaves the payload unchanged.

### Changed

- **Version bump** — `0.3.0` → `0.4.0`.
- **Documentation** — updated `ARCHITECTURE.md` TODOs and tightened `.gitignore` hygiene.

### Fixed

- Removed a duplicate handler for `add_node_to_definition`.
- Corrected integration-test assertions to match the new `view_output` return shape.
- Cleaned up unused test variables and trailing-newline lint.

### Tests

- Added unit coverage for step constraints, subgraph definition edits, dropped boundary links, and missing inner inputs.
- Integration tests pass against a live ComfyUI instance: **9 passed, 1 skipped** (Depth-Anything-3 nodes not installed on the test instance).
- Full suite: **291 unit tests passed**, **10 integration tests deselected**, `ruff check .` clean.
