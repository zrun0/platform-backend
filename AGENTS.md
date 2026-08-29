# AGENTS.md

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default canonical triage roles (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Doc routing

Where new content goes — one home per kind:

- Process docs (plans, checklists, acceptance records): `.scratch/<feature-slug>/` — deleted when the feature is done
- Decisions: `docs/adr/` — append-only, numbered (see `docs/adr/README.md` for template and writing guidelines)
- Terminology / architecture: `CONTEXT.md`
- Living operating docs (workflows, troubleshooting): `docs/*.md` — keep current; git history is the archive, no `docs/archive/`
- Dependency changes: see `docs/dependencies.md` (constraints live at the workspace root; members declare bare names)
