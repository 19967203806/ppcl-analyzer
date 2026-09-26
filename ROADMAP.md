# PPCL Code Analysis Roadmap

## Phase 1: Stabilize The Analysis Loop

- Track each analysis with status, language, model provider, input hash, token usage, and error details.
- Reject empty uploads and cleaned files before calling the model.
- Make repeated analysis explicit: uploading the same filename replaces the previous result only after the user clicks Start Analysis.
- Keep historical results selectable, but never auto-display them as if they were fresh analysis.

## Phase 2: Harden Generated Artifacts

- Validate Graphviz DOT before rendering or saving it as a chart source.
- Normalize DOT layout for readable Streamlit rendering.
- Normalize Mermaid sequence diagrams before browser rendering.
- Mark partial pipeline failures as `completed_with_warnings` instead of silently reporting success.

## Phase 3: Add A Structured PPCL Layer

- Parse PPCL line numbers, `GOTO`, `GOSUB`, `RETURN`, `SAMPLE`, `IF`, and assignment statements into an intermediate representation.
- Generate baseline flowcharts from parsed structure instead of relying entirely on model-authored DOT.
- Let the model explain logic and summarize blocks, while deterministic code owns graph topology.

## Phase 4: Improve Product UX

- Show current file, language, status, model provider, input hash, created time, and token usage in the UI.
- Add clear retry actions for failed analyses.
- Add artifact health checks for flowchart, sequence chart, logic blocks, data points, and logic document.
- Improve download controls so the main view stays focused on previewing results.

## Phase 5: Test And Release Discipline

- Add unit tests for upload validation, graph normalization, Mermaid normalization, and pipeline status handling.
- Add integration tests for file upload, duplicate replacement, preview endpoints, and delete behavior.
- Add a release checklist covering backend health, frontend launch, analysis verification, and GitHub push.
