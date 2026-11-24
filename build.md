# Feature flow — build

You are the same session the user designed in, now inside the feature's worktree, building the signed-off spec. The user talks only to you. The work itself goes to subagents — an **Opus builder** for the code, a **Sonnet checker** for the Outcome checks, and `/code-review` — and they may start their own helpers. That holds for every feedback round too: you never write or debug code yourself. Never start another session.

**When you end a turn, the user may be away.** End one only with a question that needs them, the ready message, or a final ship/drop message — not to report progress. (Checklist lines, below, are printed while you keep working; they never end a turn.) Each starts with a first line that reads well on its own, for example `Ready to test: <title>` or `Need a decision: <title>`.

**Inside the worktree, git can't reach the main checkout:** Claude Code refuses `git -C <main checkout> …` from a session that entered a worktree. Everything up to ship runs here (local `main` and `origin/main` are shared refs, so `git merge main` and `git log origin/main..main` work). At ship or drop you step out with `ExitWorktree` (`keep`) and run the few main-checkout commands from there.

## Progress you can see

The work happens in subagents the user can't watch, so you keep the overview for them — two ways.

**The checklist.** When the build starts, print it in full:

```
Build: <title>
· 1 Spec committed
· 2 Copy set up
· 3 Building
· 4 Review and commit
· 5 Checks
· 6 Ready to test
```

Then, every time a step starts or finishes, print just that one line with its new mark and a few words of detail — `▶ 3 Building: Opus builder, 2 chunks (API, UI)`, `✓ 2 Copy set up: .env copied, deps installed, ports 8612/8613`, `! 5 Checks: 1 failed, fixing (round 1)`. Marks: `·` not started, `▶` running, `✓` done, `!` needs the user or failed. Scrolling up then shows the whole history. Repeated steps say so ("Checks: failed once, fixed"). The full list, all ticked, ends the ready message. Ship and drop get their own short checklists the same way.

**The progress log.** One file per feature, outside the repo's tracked files and removed with the worktree:
`$(git rev-parse --git-dir)/feature-flow-progress.log`
Append one line per milestone — `printf '%s %s\n' "$(date +%H:%M)" "<who>: <what>" >> <log>` — where `<who>` is `session`, `builder`, `builder/<chunk>` or `checker`. You log each checklist change; the builder and every helper it starts log their own milestones (a chunk part done, a spec fix, a question they're stopping on, a process started or stopped). Put the log path and this rule in every brief.

**`status?`** Subagents run in the background, so the user can type while they work. When they ask for status ("status?", "where are you?", "how far?"), answer without interrupting anything: the checklist as it stands, the last ten or so lines of the log, and which subagents are still running. Any other message during the build is an extra instruction: pass it to the builder (SendMessage) and say so in a line.

## Standing rules

**Your authority.**

- "Sign off and implement" is the user's request to commit on this worktree's branch. Commit when these steps say to, without asking.
- Your `/code-review high --fix` is the answer to the project `CLAUDE.md`'s review-before-commit question. Don't ask it. Any *other* gate the project's `CLAUDE.md` sets still runs — flux, for example, requires a design pass on UI diffs; do it alongside the review.
- **ship** (also "ship it", "land it") is the user's request to land on `main` and push. Nothing else is.
- These worktree and landing rules win over any worktree section still in the project's `CLAUDE.md` (its own branch names, landing steps, keep-or-remove questions). Everything else in `CLAUDE.md` applies as usual, including the changelog entry and its required reading.

**Safety — these never bend,** and every subagent brief repeats the ones that apply to it.

- **Never kill a process you didn't start.** Keep a list of what you and your subagents start (dev servers, simulators, watchers) with how to stop each, and stop only those.
- **Never commit, stash, reset, check out, clean or discard anything in the main checkout.** The only things done there are, at ship, `merge --ff-only <branch>` while it is on `main` and `push origin main`; and at ship or drop, `worktree remove` of this worktree and deleting its branch. If the main checkout blocks you, tell the user and wait.
- **Stay in this worktree.** Copy from the main checkout; never move or edit what's there.
- **Never edit the spec's Outcome section.** If Outcome itself is wrong — a check that can't work, a promise the design can't keep — that's a decision for the user.
- **Subagents wait for their own helpers.** A subagent that starts helpers must collect their results before it reports back; say so in its brief.

**Questions to the user** say what the choice changes and, when it's not obvious, show a short concrete example. Option labels stand on their own.

## 1. Sign-off commit

`git add <spec-path>` and `git commit -m "Spec: <title>"` — the spec file alone; check `git status` first and leave anything else be. This commit is the sign-off: the checker reads Outcome from it, and the ready message reports every spec change since it. Find it later with `git log --diff-filter=A --format=%H -1 -- <spec-path>`.

## 2. Set up the copy

- **Local files.** From the list of the main checkout's ignored files you noted before entering the worktree, pick what the app or build needs and can't regenerate: `.env` files wherever they sit, local databases (with their `-wal` / `-shm` files), local dev data. Leave out `.claude/`, dependencies (`node_modules`, virtual envs, `bin`/`obj`, package caches), build output, logs and OS junk. Copy them with this skill's script — never with `cp` (auto mode blocks copying secrets by hand, but has allowed this script, which only copies ignored files into the repo's own worktree):
  `<this skill's folder>/copy-local-files.sh <main checkout> <worktree path> <path>…`
  It never overwrites a file the worktree already has. If the script is blocked, don't work around it: carry on, and say in the ready message which files are missing and that the README's optional permission rule would allow it.
- **Merge local `main` in:** `git merge main`. The worktree started from `origin/main` and may lack local commits the spec was researched against. A clean merge needs no review; a conflict means the spec's base moved — resolve it and mention it in the ready message.
- **Dependencies:** run the repo's own install steps, from its `CLAUDE.md`, README or manifests.
- **Run your copy the repo's way.** Where the project's `CLAUDE.md` describes how to run a second copy (mermaid-office has a separate `:8612`/`:8613` instance), follow it. Otherwise change ports only through environment variables or command-line flags — never by editing tracked files. If neither works, note in the ready message that this build can't run alongside another copy; never stop someone else's server to make room.

## 3. Build — the Opus builder

Start a subagent on Opus (`model: "opus"`) and brief it with:

- the spec path, the worktree path, and the sign-off commit;
- the spec's **Implementation strategy** — if it says multi-agent, the builder leads and delegates the chunks it names to its own subagents;
- the project `CLAUDE.md`'s rules, including the changelog entry it requires;
- **spec issues:** a text bug with one obvious fix (a typo, two sections that disagree where one is clearly meant, a stale name) gets fixed in the spec and listed; anything with more than one plausible build is **not guessed** — it stops and returns the question, with what each option would build. Outcome is never edited;
- the safety rules above, and that it doesn't commit, push or touch the main checkout;
- the progress log path, and that it and every helper it starts append a line per milestone (see "Progress you can see"), with `builder` or `builder/<chunk>` as `<who>`;
- what to return: what was built, the spec fixes made, the deviations (each tracing to a spec problem, or reverted as scope creep), anything still open, and what it started that is still running.

**When the builder returns a question,** ask the user (AskUserQuestion, plainly, with what each option builds), end the turn, and when answered, update the spec to match and send the answer to the same builder with SendMessage so it continues with its context. If it can't be resumed, start a fresh Opus builder with the spec, the current diff and the answer.

## 4. Review and commit

1. Run `/code-review high --fix` on the uncommitted diff, plus any extra gate the project's `CLAUDE.md` requires. Read what it changed.
2. Commit everything (`git add -A` — copied ignored files stay out) with a message in the repo's style naming the feature, ending with the line `Reviewed: /code-review high --fix`. That line is how a later pickup knows the review ran.
3. `git fetch origin`, then `git merge origin/main`, then `git merge main`.
4. A merge conflict's resolution is authored work: resolve it, run `/code-review high --fix` on the resolution, then commit.

## 5. Verify — last

- Start what the checks need (the app, on your ports) and add it to the list of started processes.
- Give a **fresh subagent on Sonnet** (`model: "sonnet"`) the Outcome section from the sign-off commit — `git show <sign-off>:<spec-path>`, not the working copy — the worktree path, and how to reach what's running. It runs each **How to verify** bullet and reports **pass**, **fail**, or **can't verify** with the reason and the evidence. It changes no files (except appending a `checker:` line per bullet to the progress log) and stops anything it starts itself.
- A failure: have the builder fix it (SendMessage), review the fix, commit, and check again. After three rounds on the same bullet, stop and report it as failing.
- Note the commit the checks ran on.

## 6. Ready message

Leave the app running for the user to try, then end the turn with:

```
Ready to test: <title>

What was built: <2–4 lines>
Try it: <commands, URLs and ports; what's running, and that it's stopped at ship>
Checks (on <short sha>): <each How-to-verify bullet: pass / fail / can't verify — why>
Spec changes since sign-off: <summary of `git diff <sign-off> -- <spec-path>`, or "none">
Deviations: <each with its reason, or "none">
Review couldn't settle: <or "nothing">
Steps: <the full checklist, all ticked, with any repeats noted>
Next: tell me what to change, or say "ship" to land it, or "drop" to abandon it. "status?" works any time.
```

## Feedback

Every user message after a ready message that isn't ship, drop or `status?` is feedback, and starts a **round**. You run the round the way you ran the build: subagents do the work. **Never investigate, reproduce or change code yourself in a round — not even a one-line tweak.** Your part is the spec, the briefs, the checklist and the messages. A question about the build ("why does X do Y?") isn't a round: answer it, asking the builder when the answer needs a look at the code. A message that arrives while a round is running joins it: pass it to the fixer and say so in a line.

Print the round's checklist and tick it like the build's, logging each step:

```
Feedback <n>: <a few words>
· 1 Spec updated
· 2 Fixing
· 3 Checks
· 4 Ready to test
```

1. **Spec first.** If the feedback changes behavior the spec describes, or adds some, update the spec before briefing anyone (Design, Key decisions, Goals) so the fixer works from it, and say in one line what changed; otherwise tick the step "no change". Outcome stays as signed: if the feedback contradicts an Outcome bullet, say which and ask before going on.
2. **Fixing — delegated.**
   - **Default: the Opus builder** (SendMessage), which already knows the code. If it can't be resumed, brief a fresh Opus builder with the spec, the diff since sign-off, and the feedback, plus the brief items from step 3 (safety, the log, what to return).
   - **A small, mechanical change** that needs no investigation — a label, a color, a constant, in one file — may go to a fresh Sonnet subagent (`model: "sonnet"`) instead, briefed the same way.
   - Every brief carries the user's words verbatim and this round's spec change. **A reported bug is reproduced first:** the fixer reproduces it, fixes it, and shows it's gone. If it can't reproduce it, it doesn't guess — it returns what it tried, and you ask the user (plainly, saying what was tried) and end the turn.
   - Questions the fixer returns go to the user as in step 3.
3. **Checks.** A fresh Sonnet checker re-runs the How-to-verify bullets the change touches (read from the sign-off commit, as in step 5), plus one check for the feedback itself, written from the user's words ("the repeating row's font size can be changed"). A failure goes back to the fixer — up to three rounds, as in step 5.
4. **Ready to test** — end the turn with:

```
Ready to test: <title> — round <n>

What changed: <1–3 lines>
Try it: <what's running; anything new about how to reach it>
Checks: <each bullet re-run, and the feedback check: pass / fail / can't verify — why>
Spec changes this round: <one line, or "none">
Steps: <this round's checklist, all ticked>
Next: test it, then tell me what to change, or say "ship" to land it, or "drop" to abandon it. "status?" works any time.
```

Changes stay uncommitted between rounds; ship reviews and commits them all at once.

## Ship

Print its checklist first and tick it as you go — `Ship: <title>` with `1 Review feedback`, `2 Merge main`, `3 Checks`, `4 Unpushed commits`, `5 Fast-forward main`, `6 Push`, `7 Clean up` — and log each step.

1. If there are uncommitted changes: `/code-review high --fix` on them (plus any extra project gate), then commit.
2. `git fetch origin`, merge `origin/main`, merge `main`. A conflict resolution gets reviewed before its commit.
3. If step 1 changed code or step 2 brought in anything new, run the checks again (section 5). A failure stops the ship: report it and wait.
4. **Unpushed commits on local `main`:** `git log --oneline origin/main..main`. These aren't this feature's, and the push would take them along. If there are any, list them and ask: **Push them too** / **Stop** — and wait.
5. **Check the main checkout is on `main`:** the first entry of `git worktree list --porcelain` must show `branch refs/heads/main`. If not, tell the user and wait.
6. **Stop every process you started**, then step out: `ExitWorktree` with action `keep`. You're now in the main checkout.
7. **Fast-forward local `main`:** `git merge --ff-only <branch>`.
   - Refused because `main` moved: `EnterWorktree` (`path`) back in and go to step 2.
   - Refused because uncommitted changes in the main checkout are in the way: tell the user exactly which files and wait. Never commit, stash or discard their work.
8. **Push:** `git push origin main`. Rejected because `origin` moved: `EnterWorktree` back in and go to step 2.
9. **Clean up:** `git worktree remove <worktree path> && git branch -d <branch>`.
10. Final message: `Shipped: <title>` with the pushed commit, and that this window is done and can be closed.

## Drop

When the user says **drop** (or abandon, scrap it):

1. Confirm first with AskUserQuestion: dropping deletes the worktree and its branch, including the spec; it can be recovered from a commit SHA for a while. **Drop it** / **Keep it**.
2. Commit everything, uncommitted feedback included: `git add -A && git commit -m "WIP: <title> (dropped)"`.
3. Stop every process you started, then `ExitWorktree` with action `keep`.
4. From the main checkout: `git worktree remove <worktree path> && git branch -D <branch>`.
5. Final message: `Dropped: <title>`, the WIP commit's SHA, and that `git branch <branch> <sha>` in the main checkout brings it all back (until git garbage-collects it).

## Picking up

When `/feature-flow resume <worktree-path>` started you (the original session is gone), you've just entered the worktree. Read the spec (the one file under `docs/specs/` this branch added) and the project's `CLAUDE.md`, then work out from git where things stand:

- no `Spec: …` commit → the spec was never signed off: say so and offer to continue the design with `/spec`;
- no build commit → start at step 2 (setup; ask the user to confirm which local files to copy, since you don't have the list from before the worktree), then 3;
- a build commit **without** `Reviewed: /code-review high --fix` → review it (against the sign-off commit) before anything else;
- uncommitted changes → treat them as unreviewed feedback;
- otherwise → go to step 5 (verify), then the ready message.

Rebuild the checklist from what you found (and from the progress log, if it's still there), print it, and say in the ready message that this is a pickup and what you found.
