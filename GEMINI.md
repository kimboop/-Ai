@AGENTS.md

# Gemini CLI notes

Everything shared between agents lives in `AGENTS.md` (imported above).
This file is only for notes specific to Gemini CLI.

- Config lives in `.gemini/settings.json` (project-scoped) — currently sets
  `context.fileName` only. `mcpServers` is intentionally empty: a server
  entry with a bad/slow command (e.g. `npx` needing a first-time download,
  or an unresolved token) can hang `gemini` startup entirely with no error
  message, since the CLI waits on MCP servers before it's ready. Verified
  locally — adding the obvious `npx -y @modelcontextprotocol/server-github`
  example reproducibly hung the CLI. If you add an MCP server here, test
  `gemini -p "hi"` right after to confirm it still starts, and mirror the
  same server in `.claude/settings.json` per `AGENTS.md`.
- Non-interactive runs (e.g. from CI or from Claude Code shelling out for a
  second opinion): `gemini -p "<prompt>"`. Keep prompts self-contained —
  a fresh Gemini CLI invocation has no memory of prior turns unless you
  pass `--checkpointing` or explicitly feed it prior context.
- Before editing, re-read `AGENTS.md` for the branch-naming and handoff
  conventions — they apply to Gemini the same as to Claude.
