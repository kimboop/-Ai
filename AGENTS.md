# Agent Collaboration Guide

Shared source of truth for any AI coding agent working in this repository
(Claude Code, Gemini CLI, or others). `CLAUDE.md` and `GEMINI.md` each
import this file with `@AGENTS.md` and add only tool-specific notes below
that import — project facts and workflow rules belong here, not duplicated
in both.

## Project facts

_(Empty repo so far — fill this in as the codebase grows: stack, build/test
commands, directory layout, conventions.)_

## Cross-agent workflow

- **Branch naming**: `<agent>/<short-task-slug>` (e.g. `claude/add-auth`,
  `gemini/fix-cache-bug`) so it's obvious which agent owns a branch.
- **Before starting work**, check open branches/PRs for one already in
  flight on the same area, from either agent, to avoid duplicate or
  conflicting work.
- **Handoff notes**: neither agent has memory of the other's session. Leave
  state, decisions, and open items in the PR description (or a scratch
  `HANDOFF.md` for mid-flight work) so whichever agent picks it up next —
  including a future instance of yourself — has full context.
- **Never force-push over another agent's branch.**
- **Commit messages**: imperative mood, explain why, not just what.

## Shared tooling

- MCP servers used by both agents should be declared once conceptually and
  configured identically in `.claude/settings.json` and
  `.gemini/settings.json`, so both see the same tools and data instead of
  drifting apart.
- Keep this file and the tool-specific files free of secrets — MCP server
  configs should reference environment variables, never hardcode tokens.
