# feature-flow

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that takes one feature from spec to `main`, with you involved only where you're needed.

1. **Design.** `feature-flow <topic>` opens a session in `/spec` on that topic. The spec is written in a git worktree of its own, so several features can be in flight at once.
2. **Sign off and implement.** The fresh-eyes review runs while you read. If it finds nothing for you to decide, a background Opus session starts building and the design session is done.
3. **Build.** The builder sets up its copy (it copies your ignored `.env` files and local data from the main checkout and reinstalls dependencies), builds, fixes spec typos itself, asks you only real decisions, reviews with `/code-review high --fix`, merges `main`, verifies the spec's Outcome checks, and tells you it's ready to test.
4. **Test.** `claude attach <repo>-<slug>`, try it, type feedback.
5. **Ship.** Type `ship`: it lands on `main` by fast-forward, pushes, and removes the worktree and branch. Or type `drop` to abandon it.

The design and its reasoning are in [`docs/specs/2026-11-23-feature-flow.md`](docs/specs/2026-11-23-feature-flow.md).

## Requirements

- Claude Code with background sessions (`claude --bg`, `claude agents`, `claude attach`).
- The [`spec`](https://github.com/IngvarKofoed/claude-code-spec) skill (2026-11-23 or later).
- A git repo whose default branch is `main` with an `origin` remote. Elsewhere it runs as plain `/spec`.

## Install

Clone it into your user skills folder:

```bash
git clone git@github.com:IngvarKofoed/claude-code-feature-flow.git ~/.claude/skills/feature-flow
```

Then add a shell function so you can start a feature from any repo:

```bash
# ~/.zshrc or ~/.bashrc
feature-flow() { claude "/feature-flow $*"; }
```

**Optional permission rule.** A builder copies your git-ignored local files (`.env`, local databases) into its worktree with `copy-local-files.sh`. Auto mode blocks copying secrets with a plain `cp`, but has allowed this script, which only copies ignored files into the same repo's own worktree. If it ever blocks the script too, the builder says which files it couldn't copy; this rule in `~/.claude/settings.json` allows the script and nothing else:

```json
{ "permissions": { "allow": ["Bash(/Users/<you>/.claude/skills/feature-flow/copy-local-files.sh *)"] } }
```

## Use

| You | What happens |
|---|---|
| `feature-flow add rate limiting to the login endpoint` | `/spec` starts on that topic in the current repo |
| Pick **Sign off and implement** | Review runs; the builder starts as `<repo>-<slug>` |
| `claude agents` | See which builders are working, waiting for you, or ready |
| `claude attach <repo>-<slug>` | Answer its question, read its ready message, give feedback |
| `ship` | Land on `main`, push, clean up |
| `drop` | Abandon it (asks first; recoverable from the printed SHA) |

**A builder died?** Restart it from the main checkout; it moves into its worktree and works out from git where it was:

```bash
cd <repo>
claude --bg -n <repo>-<slug> --model opus "/feature-flow build .claude/worktrees/<slug> docs/specs/<date>-<slug>.md"
```

Builders start in the main checkout rather than the worktree because `claude --bg` only runs in folders you've trusted, and a fresh worktree never has been. The builder moves itself into the worktree first thing.
