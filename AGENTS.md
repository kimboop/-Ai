# Agent Collaboration Guide

Shared source of truth for any AI coding agent working in this repository
(Claude Code, Gemini CLI, or others). `CLAUDE.md` and `GEMINI.md` each
import this file with `@AGENTS.md` and add only tool-specific notes below
that import — project facts and workflow rules belong here, not duplicated
in both.

## Project facts

_(Empty repo so far — fill this in as the codebase grows: stack, build/test
commands, directory layout, conventions.)_

## Roles (strength-based split)

- **Claude Code**: owns the GitHub lifecycle end-to-end — opening and
  driving PRs, monitoring CI, responding to review comments, merges. Also
  the default for multistep refactors and changes that need architectural
  judgment calls, since it stays subscribed to a PR until it's merged or
  closed.
- **Gemini CLI**: handles tasks that lean on its very large context window
  or multimodal input — whole-repo or whole-log analysis in one pass,
  working from images/video/audio assets, bulk first-draft generation
  (tests, docs, boilerplate). Also used as a second opinion: Claude can
  shell out non-interactively (`gemini -p "<prompt>"`) to cross-check a
  design or diff before finalizing it.
- This is a default, not a hard rule — either agent can pick up any task
  when the other is unavailable or the task doesn't fit the split. When in
  doubt, follow the branch-ownership and handoff rules below rather than
  the role split.

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
