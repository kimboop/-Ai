@AGENTS.md

# Claude Code notes

Everything shared between agents lives in `AGENTS.md` (imported above).
This file is only for notes specific to Claude Code.

- Designated development branch for this repo's automated tasks:
  `claude/gemini-collaboration-setup-by3aea` (see repo task instructions).
- MCP servers available to Claude Code in this environment are managed at
  the platform/session level, not via a local `.claude/settings.json` — if
  you add a project-scoped MCP server here, mirror it in
  `.gemini/settings.json` so Gemini CLI has the same access.
