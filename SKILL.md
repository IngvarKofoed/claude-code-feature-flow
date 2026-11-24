---
name: feature-flow
description: One session per feature, from spec to main. Design mode (/feature-flow <topic>) runs /spec inside a worktree of its own and offers "Sign off and implement"; that hands the signed spec to a background Opus builder session running build mode (/feature-flow build <spec-path>), which sets up its copy, builds, verifies, reviews, reports ready to test, takes feedback, and on "ship" lands on main and cleans up. User-invoked only — run it when the user types /feature-flow, or when a session is started with "/feature-flow build <spec-path>". Do NOT auto-trigger on "write a spec" (that is /spec) or "implement this" (an ordinary request).
---

# Feature flow

One session per feature. The user designs the spec with you in **design mode**; a background session builds it in **build mode**; the user tests, gives feedback, and says **ship**. Everything between sign-off and testing runs without them, and they are pulled in only for decisions that are genuinely theirs.

**Pick the mode from the arguments.** If the first word is `build`, you are the builder: the next two words are the worktree path and the spec path. Read `build.md` in this skill's folder now and follow it — the rest of this file is the design side and the shared contract. Otherwise you are in design mode, and the arguments (possibly empty) are the topic.

The design is recorded in `docs/specs/2026-11-23-feature-flow.md` in this skill's folder. When this file and the spec disagree, this file wins; say so to the user.

## The contract between the two modes

Both modes rely on these, so neither may change them alone:

- **One worktree per feature**, created by design mode with `EnterWorktree` and named after the spec's slug. Its branch is whatever `EnterWorktree` created (read it with `git branch --show-current`; don't assume a naming scheme).
- **The spec commit is the sign-off.** Design mode commits the spec file alone on the worktree branch, with the message `Spec: <title>`, before launching the builder. The builder finds it as the commit that added the spec (`git log --diff-filter=A --format=%H -1 -- <spec-path>`), reads Outcome from it, and reports every spec change since it.
- **The builder session** is started from the **main checkout** as
  `claude --bg -n ff-<repo>-<slug> --model opus "/feature-flow build <worktree-path> <spec-path>"`
  where the `ff-` prefix marks it as a feature-flow builder (so tidy-up can never touch another session, and `claude attach <repo>-<slug>` still finds it, since part of a name is enough), `<repo>` is the main checkout's folder name, `<worktree-path>` is the worktree's path relative to the main checkout (e.g. `.claude/worktrees/<slug>`), and `<spec-path>` is repo-relative. It starts in the main checkout because `claude --bg` refuses folders the user hasn't trusted, and a new worktree never has been; its first act is to move into the worktree with `EnterWorktree` (`path`). No `--effort`: the user's own settings apply. The same command, run again from the main checkout, restarts a builder that died.
- **One session per checkout.** Design mode leaves the worktree before it ends, and the builder does nothing until it has moved into it, so the builder is the only session working there.

## Design mode

### Before starting

Check, quietly:

- the current directory is inside a git repo, and it is the **main checkout**, not a linked worktree (`git rev-parse --path-format=absolute --git-dir --git-common-dir` prints two identical paths);
- a branch named `main` exists and is the default branch, and a remote named `origin` exists.

If any check fails, say in one line that the build half isn't available here and why, then run plain `/spec` on the topic and stop treating this as a feature flow.

**Tidy up finished builders.** A shipped or dropped builder stays in `claude agents` until removed, because a session can't remove itself. So, before invoking `/spec`, list background sessions with `claude agents --json --all` and pick those that meet **all** of these:

- the name starts with `ff-<repo>-` and the `cwd` is this main checkout;
- the worktree its name points to (`.claude/worktrees/<slug>` for `ff-<repo>-<slug>`) is not in `git worktree list` — it shipped or was dropped.

For each, `claude stop <id>` if it is still running, then `claude rm <id>`. Say it in one line ("Removed 2 finished builders: ff-flux-x, ff-flux-y") or say nothing when there were none. Never touch a session whose worktree still exists, whatever its state — it may be waiting for the user.

### Run `/spec`, with these additions

Invoke the `spec` skill with the topic and follow it fully. You are its wrapper: everything below adds to `/spec`, and where it says something different, this wins for this session.

**Your side effects override `/spec`'s read-only rule, and only these:** `EnterWorktree`, the spec commit, launching the builder, and `ExitWorktree`. Everything else in this session stays read-only, exactly as `/spec` says.

**1. Enter the worktree when the draft is first written.** `/spec` picks the slug in phase 4. Right before it writes the draft, call `EnterWorktree` with `name` set to that slug, then write the spec inside the worktree at the usual `docs/specs/<date>-<slug>.md`. Phases 1–3 only read, so they run in the main checkout. The worktree branches from `origin/main` (unless `worktree.baseRef` is `head`), so it may lack local unpushed `main` commits; the builder merges local `main` first, so that's fine. Never call `EnterWorktree` twice.

**2. The draft handoff becomes a sign-off picker.** Keep `/spec`'s recap and markup instructions, but end with one AskUserQuestion instead of "reply when you're done":

- one question per open question, default first and tagged `(Recommended)` — **at most three**. With more than three, ask the open questions first in a picker of their own (plain `/spec` behavior), integrate the answers, and show this picker after;
- then: *"Sign off on it as it stands, or mark it up first?"* with **Sign off and implement**, **Sign off, build later**, and **I've marked it up**. No `(Recommended)` tag on these — the user may not have read the draft yet.

This picker offers sign-off, so under `/spec`'s rules it **is** a sign-off ask: start the fresh-eyes review (phase 7, on Fable, spec path only, hash noted) in the same turn, just before showing it.

**3. The sign-off question** (`/spec` phase 6) gets three options, in this order: **Sign off and implement (Recommended)**, **Sign off, build later**, **Not yet — more changes**.

**4. After "Sign off and implement":**

- Re-read the spec and compare the hash, per `/spec`. `////` lines mean "not yet".
- **Changed answers:** if an open question in the same picker was answered with anything other than its default, fold the answers into the spec and start a fresh review on the new text. Defaults alone keep the running review valid.
- Wait for the review. If it isn't back, say in one line that it's still running and the build starts when it's back with nothing to decide, then end the turn.
- **No decisions:** apply its fixes and "already decided" notes (per `/spec`), then **launch**.
- **Decisions:** put them in one picker whose **last** question is *"Then:"* with **Build now (Recommended)** and **Hold**. At most three decisions per picker; more go in an earlier picker, and "Then:" is always the last question of the last one. On **Build now**, integrate the answers, do `/spec`'s quick check that the flagged items are resolved, and launch — no second sign-off: the answers plus Build now are the sign-off on the revised text. On **Hold**, integrate the answers and stay; launch later when the user says so.

**5. After "Sign off, build later":** finish `/spec` normally (the review handled), then commit the spec (launch step 1), leave the worktree (`ExitWorktree`, keep), and print the launch command with the `cd` into the main checkout. If the user later asks in this session to build it, run the launch from step 2.

**6. No closing offer before the review is handled** — `/spec`'s rule, and it covers the launch: never launch on a spec whose review hasn't returned.

### Launch

1. In the worktree: `git add <spec-path>` and `git commit -m "Spec: <title>"`. Only the spec file — check `git status` first and leave anything else alone. This is a docs-only commit the user asked for by clicking; it takes no review question.
2. Run the builder command from the contract **in the main checkout**: `cd <main checkout> && claude --bg …` in one Bash call (the main checkout is the first entry of `git worktree list --porcelain`).
3. Confirm it started: `claude agents --json` lists `ff-<repo>-<slug>`, or the command printed a session id. If it failed, show the error and the exact command with its `cd`, and stay in the worktree until the user says it's running; then continue with step 4. A "workspace not trusted" error means the main checkout itself was never trusted: the user runs `claude` there once.
4. `ExitWorktree` with action `keep`. The worktree must stay: the builder is in it.
5. Tell the user, in three lines: it's building in the background as `ff-<repo>-<slug>`; `claude attach <repo>-<slug>` shows it, and it will say when it's ready to test or needs them; this session is done and can be closed.

## Notes

- **Picker wording.** Every question you put to the user says what the choice changes and, when it's not obvious, shows a short concrete example. Option labels stand on their own.
- **Restarting a dead builder:** `cd <main checkout> && claude --bg -n ff-<repo>-<slug> --model opus "/feature-flow build <worktree-path> <spec-path>"`. Build mode works out where it was from git.
