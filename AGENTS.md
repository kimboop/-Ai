# Agent Collaboration Guide

Shared source of truth for any AI coding agent working in this repository
(Claude Code, Gemini CLI, ChatGPT/Codex, or others). `CLAUDE.md` and
`GEMINI.md` each import this file with `@AGENTS.md` and add only
tool-specific notes below that import — project facts and workflow rules
belong here, not duplicated across tool files. ChatGPT (Codex CLI / Codex
cloud) needs no separate import shim: `AGENTS.md` is the format it reads
natively, so this file alone is enough to brief it.

## Project facts

- **Purpose**: YouTube channel growth/expansion project — analytics,
  metadata/SEO, and content-ops tooling built on the YouTube Data API v3.
- **Stack**: Python 3.11+, packaged via `pyproject.toml` (hatchling build
  backend). This is a starting default (most broadly-used stack for
  scripting + YouTube API automation), not a final choice — revisit once
  actual feature needs are clearer.
- **Layout**: source in `src/channel_toolkit/`, tests in `tests/`.
- **Commands**:
  - `pip install -e ".[dev]"` — install package + dev dependencies
  - `pytest` — run tests
  - `ruff check .` / `ruff format .` — lint / format
- **Conventions**: keep YouTube API credentials out of the repo — copy
  `.env.example` to `.env` for local secrets, never commit `.env` or
  `client_secret.json` (both are gitignored).

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
- **ChatGPT (Codex CLI / Codex cloud)**: independent second opinion on
  design and code review — different lab, different training data, so it
  catches blind spots the other two share. Also good for open-web
  research/grounding on current best practices or library docs, and for
  picking up autonomous coding tasks when Claude Code and Gemini CLI are
  both unavailable. Claude or Gemini can shell out non-interactively
  (`codex exec "<prompt>"`, or the equivalent for whatever Codex CLI
  version is installed) to get a quick cross-check without a full session.
- This is a default, not a hard rule — any agent can pick up any task when
  the others are unavailable or the task doesn't fit the split. When in
  doubt, follow the branch-ownership and handoff rules below rather than
  the role split.

## Cross-agent workflow

- **Branch naming**: `<agent>/<short-task-slug>` (e.g. `claude/add-auth`,
  `gemini/fix-cache-bug`, `chatgpt/update-readme`) so it's obvious which
  agent owns a branch.
- **Before starting work**, check open branches/PRs for one already in
  flight on the same area, from any agent, to avoid duplicate or
  conflicting work.
- **Handoff notes**: neither agent has memory of the other's session. Leave
  state, decisions, and open items in the PR description (or a scratch
  `HANDOFF.md` for mid-flight work) so whichever agent picks it up next —
  including a future instance of yourself — has full context.
- **Never force-push over another agent's branch.**
- **Commit messages**: imperative mood, explain why, not just what.

## Shared tooling

- MCP servers used by multiple agents should be declared once conceptually
  and configured identically across each tool's config — `.claude/settings.json`,
  `.gemini/settings.json`, and Codex's `~/.codex/config.toml` (or the
  project-scoped Codex config, if one is added to this repo) — so every
  agent sees the same tools and data instead of drifting apart. Codex's
  config format is TOML, not JSON, so mirror the *server list and access*,
  not the file syntax.
- Keep this file and the tool-specific files free of secrets — MCP server
  configs should reference environment variables, never hardcode tokens.
