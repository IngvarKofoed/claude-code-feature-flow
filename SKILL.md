---
name: feature-flow
description: One session per feature, from spec to main, in the user's own window. /feature-flow <topic> runs /spec inside a worktree of its own and offers "Sign off and implement"; on that click the same session builds the spec through subagents (an Opus builder, a Sonnet checker, /code-review), reports ready to test, takes feedback, and on "ship" lands on main and cleans up. /feature-flow resume <worktree-path> picks a feature back up in a new session. User-invoked only — run it when the user types /feature-flow. Do NOT auto-trigger on "write a spec" (that is /spec) or "implement this" (an ordinary request).
---

# Feature flow

**One feature, one session, one window.** The user designs the spec with you, clicks **Sign off and implement**, and you build it right here — delegating the work to subagents, which may start their own. The user tests, gives feedback, and says **ship**, all in this window. Never start another session for any of it (no `claude --bg`, no second window): the user talks to you and only you.

Between sign-off and "ready to test" you work without them, and pull them in only for decisions that are genuinely theirs.

**Modes, from the arguments:**

- `/feature-flow <topic>` (or no arguments) — start a feature: **design**, then **build**.
- `/feature-flow resume <worktree-path>` — pick up a feature whose session is gone. Call `EnterWorktree` with that `path`, then follow `build.md` from its "Picking up" section.

The design is recorded in `docs/specs/2026-11-23-feature-flow.md` in this skill's folder (see its revision note at the top). When this file and the spec disagree, this file wins; say so to the user.

## Design

### Before starting

Check, quietly:

- the current directory is inside a git repo, and it is the **main checkout**, not a linked worktree (`git rev-parse --path-format=absolute --git-dir --git-common-dir` prints two identical paths);
- a branch named `main` exists and is the default branch, and a remote named `origin` exists.

If any check fails, say in one line that the build half isn't available here and why, then run plain `/spec` on the topic and stop treating this as a feature flow.

### Run `/spec`, with these additions

Invoke the `spec` skill with the topic and follow it fully. You are its wrapper: everything below adds to `/spec`, and where it says something different, this wins for this session.

**Your side effects override `/spec`'s read-only rule, and only these:** `EnterWorktree`, the spec commit, and — after sign-off — the build. Until the user signs off, everything else stays read-only, exactly as `/spec` says.

**1. Enter the worktree when the draft is first written.** `/spec` picks the slug in phase 4. Right before it writes the draft:

- **note the main checkout's local files** while you're still in it: `git ls-files --others --ignored --exclude-standard --directory`. Keep the list for the build (`build.md` step 2) — from inside the worktree, git can't reach the main checkout;
- call `EnterWorktree` with `name` set to that slug, then write the spec inside the worktree at the usual `docs/specs/<date>-<slug>.md`.

Phases 1–3 only read, so they run in the main checkout. The worktree branches from `origin/main` (unless `worktree.baseRef` is `head`), so it may lack local unpushed `main` commits; the build merges local `main` first. Never call `EnterWorktree` twice.

**2. Questions first, sign-off last.** Sign-off is never offered next to a question that would still change the spec. At the draft handoff, keep `/spec`'s recap and markup instructions, then:

- **If the draft has open questions,** ask them in their own picker — up to four, each with its default first and tagged `(Recommended)`, no sign-off option — exactly as plain `/spec` does. **Start the fresh-eyes review (phase 7, on Fable, spec path only, hash noted) in the background in the same turn**, overriding `/spec`'s "no review at the handoff": if the answers only accept the defaults it stays valid (per `/spec`'s stale rule); any other answer or `////` markup makes it stale, and the sign-off step starts a fresh one. Integrate the answers and any markup per `/spec`, and loop until no open questions remain and the user has no more changes.
- **Then the sign-off step** — `/spec`'s phase 6, which shows **Here's what you get** (the final Outcome, the strategy headline, and what changed since the user last saw the spec) and then asks. Its options here are, in this order: **Sign off and implement (Recommended)**, **Sign off, build later**, **Not yet — more changes**. It is a sign-off ask, so start a review now unless one is running or done on this exact text.
- **Without open questions,** go from the recap straight to the sign-off step. The recap and markup instructions come first, so the user can still mark the draft up: `////` lines in the file, or "Not yet", mean another pass.

**3. After "Sign off and implement":**

- Re-read the spec and compare the hash, per `/spec`. `////` lines mean "not yet".
- Wait for the review. If it isn't back, say in one line that it's still running and the build starts when it's back with nothing to decide, then end the turn.
- **No decisions:** apply its fixes and "already decided" notes (per `/spec`), then **build** — read `build.md` in this skill's folder and follow it.
- **Decisions:** put them in one picker whose **last** question is *"Then:"* with **Build now (Recommended)** and **Hold**. At most three decisions per picker; more go in an earlier picker, and "Then:" is always the last question of the last one. On **Build now**, integrate the answers, do `/spec`'s quick check that the flagged items are resolved, and build — no second sign-off: the answers plus Build now are the sign-off on the revised text. On **Hold**, integrate the answers and wait; build when the user says so.

**4. After "Sign off, build later":** finish `/spec` normally (the review handled), commit the spec (`build.md` step 1), and tell the user that saying "build it" in this window starts the build, or `/feature-flow resume <worktree-path>` from a new session in the main checkout.

**5. No closing offer before the review is handled** — `/spec`'s rule, and it covers the build: never start building a spec whose review hasn't returned.

## Notes

- **Picker wording.** Every question you put to the user says what the choice changes and, when it's not obvious, shows a short concrete example. Option labels stand on their own.
- **Overview.** During the build the session prints a checklist line at every step and keeps a progress log the builder and its helpers write to; the user can type `status?` at any time (see `build.md`, "Progress you can see").
- **Several features at once** means several windows, one session each. Each session works only in its own worktree.
- **If this window dies,** `claude --resume` brings the session back; failing that, `/feature-flow resume <worktree-path>` in a new session picks the feature up from git.
