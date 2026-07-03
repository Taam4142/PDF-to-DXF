# Project Working Process

Last updated: 2026-07-03

This document records the way we are building this project together. It should
guide future work so decisions, risks, tests, and next steps do not live only in
chat history.

## Codex Skill

This process has also been installed as a local Codex skill:

- Skill name: `project-working-process`
- Explicit invocation: `$project-working-process`
- Local path: `%USERPROFILE%\.codex\skills\project-working-process`

Use the skill when continuing this project or when another project should follow
the same plan, implement, risk-review, test, document, commit, and push loop.

## Core Loop

1. Plan the next useful chunk of work.
2. Implement the requested job.
3. Review what changed for improvements, risks, and possible bugs.
4. Reduce the highest practical risks before moving on.
5. Test enough for the size and impact of the change.
6. Commit and push when the work forms a meaningful, clean checkpoint.
7. Update project docs when the plan, reasoning, workflow, or risk picture is
   useful enough that we should not lose it.

## Planning

Before code changes, identify the smallest useful goal and the files or systems
likely involved. For broad work, keep a short task plan and update it as steps
move from pending to done.

Planning should answer:

- What problem are we solving now?
- What is intentionally out of scope for this chunk?
- What could break if we are wrong?
- What is the minimum verification needed before commit?

## Implementation

Prefer conservative changes that fit the existing codebase. Reuse existing
converter, app, test, and packaging patterns before introducing new tools or
architecture.

For this project, that usually means:

- Keep PDF-to-DXF conversion logic in `pdf_to_dxf/`.
- Keep native Windows app behavior in `windows_native_app.py`.
- Keep packaging behavior in PyInstaller spec files.
- Keep release automation in `.github/workflows/`.
- Keep planning and risk notes in `docs/`.

## Risk And Bug Reduction

After each meaningful implementation, explicitly look for:

- File-loss risks, such as overwriting or partial writes.
- Windows-specific behavior, such as locked files, hidden windows, paths, and
  subprocess argument quoting.
- Large or malformed PDF behavior.
- Error visibility in the windowed app.
- Packaging differences between source Python and the built `.exe`.
- User confusion, especially around raster-heavy PDFs that cannot become real
  editable CAD geometry without tracing.

When risks are found, fix the highest-value ones first. If a risk is important
but not fixed in the current chunk, write it down in the risk plan.

## Testing Expectations

Testing should scale with impact.

For documentation-only changes:

- Run markdown/diff sanity checks when useful.
- No full test suite is required unless docs affect automation commands.

For converter or API changes:

- Run `python -m unittest discover -s tests`.
- Add or update unit tests for the changed behavior.

For native Windows app changes:

- Run the unit suite.
- Run native helper or worker tests.
- Rebuild the `.exe` when packaging behavior may be affected.
- Smoke-test the packaged `.exe` with `scripts/smoke_native_app.py`.
- Initialize the UI in hidden mode when widget startup behavior changed.

For CI or packaging changes:

- Run local smoke scripts where possible.
- Push and check the GitHub Actions workflow result.

## Commit And Push Rhythm

Commit and push when the work is a coherent checkpoint, for example:

- A feature works and has verification.
- A risk-reduction batch is complete.
- A workflow or release automation step is added.
- Important project planning docs are updated.

Avoid committing half-finished experiments unless they are intentionally saved
as documentation or a branch checkpoint.

## Documentation Rules

Write or update markdown when an idea is important enough to reuse later, such
as:

- Risk and quality plans.
- Release process steps.
- Manual QA checklists.
- Deployment constraints.
- Packaging or installer decisions.
- Code-signing decisions.
- Known product limits.
- Future architecture choices.

Use an existing doc when the topic already has a home. Create a new doc when the
topic would make an existing file noisy or hard to scan.

Current documentation homes:

- `docs/native-app-risk-quality-plan.md`: risk status, quality improvements,
  and next work order for the native Windows app.
- `docs/project-working-process.md`: the collaboration and engineering process
  for this project.
- `README.md`: user-facing setup, usage, build, and major doc links.

## Current Preferred Next-Step Order

When the user says to continue without specifying a task, use this order unless
new evidence changes the priority:

1. Continue from `docs/native-app-risk-quality-plan.md`.
2. Prefer release metadata and installer work next.
3. Keep reducing user-facing and file-safety risks before adding large new
   features.
4. Keep tests, smoke checks, commit, and push as the normal close-out for a
   meaningful work chunk.
