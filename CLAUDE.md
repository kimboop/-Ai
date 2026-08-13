@AGENTS.md

# Claude Code notes

Everything shared between agents lives in `AGENTS.md` (imported above).
This file is only for notes specific to Claude Code.

- The designated development branch for automated tasks in this repo is
  whatever the current task's instructions say — it changes per task, so
  don't hardcode a specific branch name here.
- MCP servers available to Claude Code in this environment are managed at
  the platform/session level, not via a local `.claude/settings.json` — if
  you add a project-scoped MCP server here, mirror it in
  `.gemini/settings.json` (and Codex's config, for ChatGPT) so every agent
  has the same access.
- Before starting work, skim `AGENTS.md` for the current role split and
  branch/handoff conventions shared with Gemini CLI and ChatGPT/Codex —
  it's the single source of truth, not this file.
