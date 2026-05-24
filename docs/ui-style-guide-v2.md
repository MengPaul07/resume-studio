# UI Style Guide v2 — Structured Studio

## 1) Brand Direction
- Name: `Structured Studio`
- Tone: Professional, editorial, systems-oriented
- Principle: Information-first, interaction-as-identity

## 2) Core Tokens
- `--brand-paper`: main canvas
- `--brand-surface`: panel surface
- `--brand-surface-soft`: secondary panel
- `--brand-ink`: primary text/strokes
- `--brand-ink-muted`: secondary text
- `--brand-signal`: primary interactive accent
- `--brand-signal-soft`: selected/hover soft background
- `--status-running / --status-done / --status-failed / --status-warning`

## 3) Component Semantics
- Buttons: action priority via variant (`default`, `running`, `success`, `destructive`, `outline`)
- Status: always render with `StatusBadge` (no free-form status colors)
- Inputs: always use `.ui-input` for focus/contrast consistency
- Panels: use 4-layer hierarchy only: `paper -> surface -> surface-soft -> highlight`

## 4) Layout Grammar
- App shell: top utility rail + compact nav cluster
- Workspaces: left operation lane + right content lane
- Dashboard: workflow console (steps) + data feeds (imports/resumes), not module card wall
- Floating tools (DAG/debug): secondary plane, must not block primary actions

## 5) Don’ts
- Do not use legacy color literals (`blue-700`, `bg-[#E5E5E0]`) in new code
- Do not stack heavy black borders/shadows on every element
- Do not represent status with plain text only; use semantic badge/state visuals

