---
name: feature-flow
description: One session per feature, from spec to main, in the user's own window. /feature-flow <topic> designs the spec with the user inside a worktree of its own (the shared spec-format files set what a spec contains and how its review runs) and offers "Sign off and implement"; on that click the same session builds the spec through subagents (a builder on the model the spec chose, a Sonnet checker, /code-review), reports ready to test, takes feedback, and on "ship" lands on main and cleans up. /feature-flow resume <worktree-path> picks a feature back up in a new session; /feature-flow status lists every feature in flight and which need the user. User-invoked only — run it when the user types /feature-flow. Do NOT auto-trigger on "write a spec" (that is /spec) or "implement this" (an ordinary request).
---

# Feature flow

**One feature, one session, one window.** The user designs the spec with you, clicks **Sign off and implement**, and you build it right here — delegating the work to subagents, which may start their own. The user tests, gives feedback, and says **ship**, all in this window. Never start another session for any of it (no `claude --bg`, no second window): the user talks to you and only you.

Between sign-off and "ready to test" you work without them, and pull them in only for decisions that are genuinely theirs.

**Modes, from the arguments:**

- `/feature-flow <topic>` (or no arguments) — start a feature. Run the checks below, then follow `design.md`; after sign-off it hands over to `build.md`.
- `/feature-flow resume <worktree-path>` — pick up a feature whose session is gone. Call `EnterWorktree` with that `path`, then follow `build.md` from its "Picking up" section.
- `/feature-flow status` — an overview of every feature in flight, in any window. Run `python3 <this skill's folder>/state.py status` wherever you are and show its output as it is, in a code block. Nothing else: no checks, no worktree. (Agents and scripts can add `--json`.)

`design.md`, `build.md` and `state.py` sit in this skill's folder (the base directory Claude Code gave when it loaded the skill), next to `copy-local-files.sh`.

The design is recorded in `docs/specs/2026-11-23-feature-flow.md` in this skill's folder (see the revision notes at the top). When these files and the spec disagree, these files win; say so to the user.

## Before starting a feature

Check, quietly:

- the current directory is inside a git repo, and it is the **main checkout**, not a linked worktree (`git rev-parse --path-format=absolute --git-dir --git-common-dir` prints two identical paths);
- a branch named `main` exists and is the default branch, and a remote named `origin` exists.

If any check fails, say in one line that the build half isn't available here and why, then run plain `/spec` on the topic and stop treating this as a feature flow. That fallback is the only time this skill uses `/spec`.

## Notes

- **Picker wording.** Every question you put to the user says what the choice changes and, when it's not obvious, shows a short concrete example. Option labels stand on their own.
- **Overview.** Each session prints a checklist line at every step, keeps a progress log the builder and its helpers write to, and keeps a state file that `/feature-flow status` reads across all features; in a window, the user can type `status?` at any time (see `build.md`, "Progress you can see").
- **Several features at once** means several windows, one session each. Each session works only in its own worktree.
- **If this window dies,** `claude --resume` brings the session back; failing that, `/feature-flow resume <worktree-path>` in a new session picks the feature up from git.
