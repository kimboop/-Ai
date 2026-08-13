@AGENTS.md

# Gemini CLI notes

Everything shared between agents lives in `AGENTS.md` (imported above).
This file is only for notes specific to Gemini CLI.

- Config lives in `.gemini/settings.json` (project-scoped) — see that file
  for the context-file and MCP server setup that keeps Gemini CLI aligned
  with Claude Code.
- Non-interactive runs (e.g. from CI or from Claude Code shelling out for a
  second opinion): `gemini -p "<prompt>"`. Keep prompts self-contained —
  a fresh Gemini CLI invocation has no memory of prior turns unless you
  pass `--checkpointing` or explicitly feed it prior context.
- Before editing, re-read `AGENTS.md` for the branch-naming and handoff
  conventions — they apply to Gemini the same as to Claude.
