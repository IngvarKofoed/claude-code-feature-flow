# feature-flow

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that takes one feature from spec to `main` in **one session, in one window** — with you involved only where you're needed.

1. **Design.** `/feature-flow <topic>` designs the spec with you: a few approaches to pick from, then a draft you mark up, with open questions as clicks. The spec is written in a git worktree of its own, so several features can be in flight at once, one window each. What a spec contains and how its review runs come from the shared [`spec-format`](https://github.com/IngvarKofoed/claude-code-spec-format) files.
2. **Sign off and implement.** The fresh-eyes review runs while you read. If it finds nothing for you to decide, the same session starts building.
3. **Build.** The session hands the coding to a subagent on the model the spec's strategy chose (which may start its own helpers), copies your git-ignored local files (`.env`, local databases) into the worktree, reinstalls dependencies, keeps the spec in sync with what it builds (writing its choices into the spec) and asks you only the important calls. A fresh Sonnet validator compares the code with the spec (missing, different, extra), then it reviews with `/code-review high --fix`, merges `main`, has a Sonnet checker run the spec's Outcome checks, and tells you it's ready to test.
4. **Test.** Try it, then pick **Feedback**, **Ship** or **Drop**. Feedback rounds are quick and stay uncommitted; when you pick **Done**, it reviews and commits them all, re-checks, and you try it once more before **Ship**.
5. **Ship.** Pick **Ship**: it lands on `main` by fast-forward, pushes, and removes the worktree and branch. Or pick **Drop** to abandon it.

No extra sessions are started: everything you see and answer is in the window you began in. While it builds, it prints a checklist line at every step (`✓ 2 Copy set up …`, `▶ 3 Building …`), and the builder and its helpers keep a progress log — type `status?` to see where things stand without interrupting.

The design and its reasoning are in [`docs/specs/2026-11-23-feature-flow.md`](docs/specs/2026-11-23-feature-flow.md).

## Requirements

- Claude Code with `EnterWorktree` / `ExitWorktree`.
- [`spec-format`](https://github.com/IngvarKofoed/claude-code-spec-format), the shared spec format and review. Without it, design stops with the install command: `/skill-manager:add https://github.com/IngvarKofoed/claude-code-spec-format.git --dir spec-format`.
- A git repo whose default branch is `main` with an `origin` remote. Elsewhere it runs as plain `/spec`, which needs the [`spec`](https://github.com/IngvarKofoed/claude-code-spec) skill.

## Install

```bash
git clone git@github.com:IngvarKofoed/claude-code-feature-flow.git ~/.claude/skills/feature-flow
```

**Optional permission rule.** Local files are copied into the worktree with `copy-local-files.sh`. Auto mode blocks copying secrets with a plain `cp`, but has allowed this script, which only copies ignored files into the same repo's own worktree. If it ever blocks the script too, the session tells you which files it couldn't copy; this rule in `~/.claude/settings.json` allows the script and nothing else:

```json
{ "permissions": { "allow": ["Bash(/Users/<you>/.claude/skills/feature-flow/copy-local-files.sh *)"] } }
```

## Use

| You type | What happens |
|---|---|
| `/feature-flow add rate limiting to the login endpoint` | Design starts on that topic in the current repo: approaches to pick from, then a draft spec in its own worktree |
| Pick **Sign off and implement** | Review runs; then the same session builds |
| Your answers to its questions | It carries on |
| `status?`, any time during the build | The step checklist so far, the latest progress-log lines from the builder and its helpers, and what's still running |
| **Feedback** (type it in Other), after **Ready to test** | It updates the spec if needed, has a subagent make the change (uncommitted), re-checks, and reports **Ready to test — round n** |
| **Done — review and commit**, after a round | Reviews and commits all rounds, re-runs every check, and reports a full **Ready to test** |
| **Ship** | Land on `main`, push, clean up |
| `/feature-flow status`, in any window | One table of every feature in flight: which need you (first, with how long they've waited), which are working and on which step, and which have gone quiet |
| **Drop** | Abandon it (asks first; recoverable from the printed SHA) |

**For other agents and scripts.** Each feature in flight has a JSON state file at `<repo>/.git/worktrees/<name>/feature-flow-state.json`, next to its progress log. It holds the title; the phase (`design`, `build`, `feedback`, `wrapup`, `ship`, `drop`); the step as display text, numbered among the feature's ten overall steps (`1/10 Design`, `4/10 Building`, `9/10 Feedback round 2`, `10/10 Ship`) and as `step_name` / `step_number` / `step_total` / `phase_label` (plus `round` in feedback); `doing`, the session's few words on what the step is doing; whether it's waiting for the user and for what; the session id of the window running it; the repo, worktree, branch and spec paths; and `started_at` / `updated_at` / `waiting_since` as UTC timestamps (`2026-11-24T13:02:11Z`). `python3 ~/.claude/skills/feature-flow/state.py status --json` returns them all, plus each file's path and age. It looks in `~/work/*` and `~/private/*`; set `FEATURE_FLOW_ROOTS` (colon-separated) to look elsewhere. Progress-log lines start with the same kind of timestamp.

**Window closed or crashed?** `claude --resume` brings the session back. If that's not possible, start a new session in the main checkout and run `/feature-flow resume .claude/worktrees/<slug>`; it works out from git where the feature was.
