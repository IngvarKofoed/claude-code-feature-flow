# Feature flow — build

You are the same session the user designed in, now inside the feature's worktree, building the signed-off spec. The user talks only to you. The work itself goes to subagents — a **builder** for the code, on the model the spec's Implementation strategy chose, a **Sonnet validator** that compares the code with the spec, a **Sonnet checker** for the Outcome checks, and `/code-review` — and they may start their own helpers. That holds for every feedback round too: you never write or debug code yourself. Never start another session.

**When you end a turn, the user may be away.** End one only with a question that needs them, a ready message with its picker, or a final ship/drop message — not to report progress. (Checklist lines, below, are printed while you keep working; they never end a turn.) Each starts with a first line that reads well on its own, for example `Ready to test: <title>` or `Need a decision: <title>`.

**Inside the worktree, git can't reach the main checkout:** Claude Code refuses `git -C <main checkout> …` from a session that entered a worktree. Everything up to ship runs here (local `main` and `origin/main` are shared refs, so `git merge main` and `git log origin/main..main` work). At ship or drop you step out with `ExitWorktree` (`keep`) and run the few main-checkout commands from there.

## Progress you can see

The work happens in subagents the user can't watch, so you keep the overview for them — two ways.

**The checklist.** When the build starts, print it in full:

```
Build: <title>
· 1 Spec committed
· 2 Copy set up
· 3 Building
· 4 Validating against the spec
· 5 Review and commit
· 6 Checks
· 7 Ready to test
```

Then, every time a step starts or finishes, print just that one line with its new mark and a few words of detail — `▶ 3 Building: builder on Sonnet, 2 chunks (API, UI)`, `✓ 2 Copy set up: .env copied, deps installed, ports 8612/8613`, `! 6 Checks: 1 failed, fixing (round 1)`. Marks: `·` not started, `▶` running, `✓` done, `!` needs the user or failed. Scrolling up then shows the whole history. Repeated steps say so ("Checks: failed once, fixed"). The full list, all ticked, ends the ready message. Ship and drop get their own short checklists the same way.

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

## Keeping the spec in sync

The spec ships with the code, so whenever you hand the user something to test, the spec must describe what they're testing. You own the spec and keep it true; the builder reports, you decide. The user is asked only about what's important.

**In sync means** nothing in the spec is false about the build, and every choice the builder made where the spec was silent, and that a user or a later reader would notice (behavior, look, data, an interface), has a line in the spec: in Design, or in Key decisions if it's load-bearing. Internal details such as names, structure and how it's done stay out; the spec isn't the implementation.

**The sync pass** runs whenever a builder or fixer returns (after step 4's validation, when one runs), and again if the code review's fixes change behavior the spec describes. Its input is what the builder returned (the spec fixes it made, every place it chose where the spec was silent or unclear, every deviation), the validator's findings, and what the review couldn't settle. Take the items that matter: anything that blocked, forced a deviation, needed a choice between readings that build different things, shows the spec contradicting itself or the code, or leaves an Outcome bullet unverifiable, and every silent choice a user would notice. Leave out wording, typos, and details filled the obvious way with no real risk. Sort each into one of three:

1. **The spec was silent or wrong, and the build's choice is sensible.** Write the choice into the spec so it reads true, and list it. Most items land here. *Example: the "10" on the ten planks is 16 px, because 13 px read too small next to the icon — one line in Design.*
2. **The build is wrong and the spec is right.** Back to the builder to fix (SendMessage), then the pass again on what it returns.
3. **Your call.** Only when it's important: the build contradicts or changes an Outcome bullet; an Outcome bullet can't be verified as written; the choice goes against something the user said or the spec states and the intent is unclear; or it's hard to undo (saved data, a public contract, deleting something). Meanwhile keep what was built and write it into the spec as it stands, so code and spec agree even if the user never answers. *Example: the "10" is cream, but the spec says "gold is the color for controls" — was the label meant to be gold too?*

**Asking.** Your-call items go to the user with the next ready message, never mid-build (a builder that's blocked asks at once, as step 3 says). They get **their own picker**, right after the ready message and before its usual question, so "ship?" is never asked next to a question that might still change the build. Each question gives what's at stake in a sentence and a concrete example, then **Keep as built (Recommended)** first and the real alternatives after it. Up to four per picker; more go in a second one. Then:

- **Every answer is Keep as built:** nothing changes. In the same turn, ask the ready message's usual question (Feedback / Ship / Drop, or Feedback / Done / Drop).
- **Any other answer:** that's feedback. Say in one line which answer changes the build, start a round with it (spec first, then the fixer), and skip the usual question: the round ends with its own ready message and picker.

Outcome changes only on the user's answer.

**The checklist** shows the pass on the line that ran it, for example `✓ 3 Building: builder on Sonnet; spec: 2 lines added, 1 your call`.

## 1. Sign-off commit

`git add <spec-path>` and `git commit -m "Spec: <title>"` — the spec file alone; check `git status` first and leave anything else be. This commit is the sign-off: the checker reads Outcome from it, and the ready message reports every spec change since it. Find it later with `git log --diff-filter=A --format=%H -1 -- <spec-path>`.

## 2. Set up the copy

- **Local files.** From the list of the main checkout's ignored files you noted before entering the worktree, pick what the app or build needs and can't regenerate: `.env` files wherever they sit, local databases (with their `-wal` / `-shm` files), local dev data. Leave out `.claude/`, dependencies (`node_modules`, virtual envs, `bin`/`obj`, package caches), build output, logs and OS junk. Copy them with this skill's script — never with `cp` (auto mode blocks copying secrets by hand, but has allowed this script, which only copies ignored files into the repo's own worktree):
  `<this skill's folder>/copy-local-files.sh <main checkout> <worktree path> <path>…`
  It never overwrites a file the worktree already has. If the script is blocked, don't work around it: carry on, and say in the ready message which files are missing and that the README's optional permission rule would allow it.
- **Merge local `main` in:** `git merge main`. The worktree started from `origin/main` and may lack local commits the spec was researched against. A clean merge needs no review; a conflict means the spec's base moved — resolve it and mention it in the ready message.
- **Dependencies:** run the repo's own install steps, from its `CLAUDE.md`, README or manifests.
- **Run your copy the repo's way.** Where the project's `CLAUDE.md` describes how to run a second copy (mermaid-office has a separate `:8612`/`:8613` instance), follow it. Otherwise change ports only through environment variables or command-line flags — never by editing tracked files. If neither works, note in the ready message that this build can't run alongside another copy; never stop someone else's server to make room.

## 3. Build — the builder

**Its model is the one the spec's Implementation strategy names** — the design session chose it, and the user signed off on it. Pass it as `model` (`"sonnet"`, `"opus"`, `"fable"`, …) and name it in the checklist line. Only if the strategy names no model, use Opus. The same model serves the builder for the whole feature, fresh builders included.

Start the builder subagent and brief it with:

- the spec path, the worktree path, and the sign-off commit;
- the spec's **Implementation strategy** — if it says multi-agent, the builder leads and delegates the chunks it names to its own subagents, on the models it names;
- the project `CLAUDE.md`'s rules, including the changelog entry it requires;
- **spec issues:** a text bug with one obvious fix (a typo, two sections that disagree where one is clearly meant, a stale name) gets fixed in the spec and listed; anything with more than one plausible build is **not guessed** — it stops and returns the question, with what each option would build. Outcome is never edited;
- the safety rules above, and that it doesn't commit, push or touch the main checkout;
- the progress log path, and that it and every helper it starts append a line per milestone (see "Progress you can see"), with `builder` or `builder/<chunk>` as `<who>`;
- what to return: what was built; the spec fixes made; every place the spec was silent or unclear, what it chose and why; the deviations (each tracing to a spec problem, or reverted as scope creep); anything still open; and what it started that is still running.

**When the builder is done,** validate (step 4), then run the sync pass ("Keeping the spec in sync") on its report and the validator's findings, all before the review, so fixes get reviewed and the spec's new lines are committed with the code.

**When the builder returns a question,** ask the user (AskUserQuestion, plainly, with what each option builds), end the turn, and when answered, update the spec to match and send the answer to the same builder with SendMessage so it continues with its context. If it can't be resumed, start a fresh builder on the same model with the spec, the current diff and the answer.

## 4. Validate against the spec

The builder's report is its own account; a builder that drifted without noticing won't list the drift. So before the review, a **fresh subagent on Sonnet** (`model: "sonnet"`), with no builder context, reads the spec next to the code.

Brief it with: the spec path (the working copy, with the fixes and answers made since sign-off), the worktree path, and the sign-off commit; the code to read is `git diff <sign-off>` plus any untracked files `git status --short` shows. It reads only: it changes no files except appending a `validator:` line per finding to the progress log, and it runs nothing; the checker covers behavior, and the review covers bugs. It answers three questions, each finding with the spec section, the code (`file:line`), and what's off:

- **Missing:** is every part of Design and every Key decision actually in the code? (The spec says plants already growing keep the 0.9 they were planted with: does the code leave them alone?)
- **Different:** is something built another way than the spec says? (Key decisions says "reuses the existing stepper", but the diff adds a new component.)
- **Extra:** is there anything the spec doesn't ask for? (The spec says the brew sheet is unchanged: does the diff touch it?)

It also lists the choices it sees where the spec is silent and a user would notice the result. If it finds nothing, it says so in one line; an empty reply counts as a failed check, so run it again once.

Its findings go into the sync pass with the builder's report. Missing and different work usually goes back to the builder; extra work is reverted as scope creep unless the build needs it, and then the spec gets a line. When the builder has fixed what was sent back, have the same validator (SendMessage) re-check just those items, not the whole build. Print the result on the checklist line, for example `✓ 4 Validating: 1 missing (fixed), 2 silent choices written into the spec`.

## 5. Review and commit

1. Run `/code-review high --fix` on the uncommitted diff, plus any extra gate the project's `CLAUDE.md` requires. Read what it changed. If its fixes change behavior the spec describes, run the sync pass on them now.
2. Commit everything (`git add -A` — copied ignored files stay out) with a message in the repo's style naming the feature, ending with the line `Reviewed: /code-review high --fix`. That line is how a later pickup knows the review ran.
3. `git fetch origin`, then `git merge origin/main`, then `git merge main`.
4. A merge conflict's resolution is authored work: resolve it, run `/code-review high --fix` on the resolution, then commit.

## 6. Verify — last

- Start what the checks need (the app, on your ports) and add it to the list of started processes.
- Give a **fresh subagent on Sonnet** (`model: "sonnet"`) the Outcome section from the sign-off commit — `git show <sign-off>:<spec-path>`, not the working copy — the worktree path, and how to reach what's running. It runs each **How to verify** bullet and reports **pass**, **fail**, or **can't verify** with the reason and the evidence. It changes no files (except appending a `checker:` line per bullet to the progress log) and stops anything it starts itself.
- A failure: have the builder fix it (SendMessage), review the fix, commit, and check again. After three rounds on the same bullet, stop and report it as failing.
- A **can't verify** caused by the bullet's wording rather than the build is a Your-call item ("Keeping the spec in sync"): Outcome changes only on the user's answer.
- Note the commit the checks ran on.

## 7. Ready message

Leave the app running for the user to try, then end the turn with the message below and the **Feedback / Ship / Drop** picker after it. **Try it** sits near the end, just above Steps, so the user finds it without scrolling up.

```
Ready to test: <title>

What was built: <2–4 lines>
Feedback folded in: <each round since the build, in a few words — leave the line out before any feedback>
Checks (on <short sha>): <each How-to-verify bullet: pass / fail / can't verify — why>
Spec changes since sign-off: <summary of `git diff <sign-off> -- <spec-path>`, or "none">
Spec issues: <each item from the sync pass and what was done: written into the spec / fixed in the code / your call below — or "none">
Not settled: <what's left that isn't a spec issue, e.g. untested on a real phone — or "nothing">
Try it: <commands, URLs and ports; what's running, and that it's stopped at ship>
Steps: <the full checklist, all ticked, with any repeats noted>
"status?" works any time.
```

If the sync pass left Your-call items, ask them first, in their own picker ("Keeping the spec in sync", Asking). Then, unless an answer started a round, ask with AskUserQuestion — *"Tried it? Change something, ship, or drop?"*:

- **Feedback** — "Type what to change in Other, or pick this and tell me next."
- **Ship** — "Lands it on main and pushes."
- **Drop** — "Abandons it: deletes the worktree and branch (asks first)."

Text typed in Other is the feedback (or "status?"). **Feedback** picked with no text: ask "What should change?" in one line and end the turn.

## Feedback

**The loop.** A ready message's work is reviewed and committed. Feedback after it runs in **rounds** that stay uncommitted and unreviewed, so each one is quick; after each, the user tests and picks more **Feedback** or **Done**. **Done** validates, reviews and commits all the rounds at once, re-runs every check, and ends with a full ready message (step 7) — back where the build ended, with Feedback / Ship / Drop. So what ships is always reviewed code the user has tried. Rounds are numbered from 1 after each full ready message.

Feedback is anything the user sends from a picker's Other box, or after picking Feedback, that isn't ship, drop, done or `status?`. Each one starts a round. You run the round the way you ran the build: subagents do the work. **Never investigate, reproduce or change code yourself in a round — not even a one-line tweak.** Your part is the spec, the briefs, the checklist and the messages. A question about the build ("why does X do Y?") isn't a round: answer it, asking the builder when the answer needs a look at the code. A message that arrives while a round is running joins it: pass it to the fixer and say so in a line.

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
   - **Default: the builder** (SendMessage), which already knows the code. If it can't be resumed, brief a fresh builder on the same model with the spec, the diff since sign-off, and the feedback, plus the brief items from step 3 (safety, the log, what to return).
   - **A small, mechanical change** that needs no investigation — a label, a color, a constant, in one file — may go to a fresh Sonnet subagent (`model: "sonnet"`) instead, briefed the same way.
   - Every brief carries the user's words verbatim and this round's spec change. **A reported bug is reproduced first:** the fixer reproduces it, fixes it, and shows it's gone. If it can't reproduce it, it doesn't guess — it returns what it tried, and you ask the user (plainly, saying what was tried) and end the turn.
   - Questions the fixer returns go to the user as in step 3.
   - Ask the fixer to return what step 3 asks of the builder, and when it's done, run the sync pass ("Keeping the spec in sync").
3. **Checks.** A fresh Sonnet checker re-runs the How-to-verify bullets the change touches (read from the sign-off commit, as in step 6), plus one check for the feedback itself, written from the user's words ("the repeating row's font size can be changed"). A failure goes back to the fixer — up to three rounds, as in step 6.
4. **Ready to test** — end the turn with this message and the **Feedback / Done / Drop** picker after it:

```
Ready to test: <title> — round <n>

What changed: <1–3 lines>
Checks: <each bullet re-run, and the feedback check: pass / fail / can't verify — why>
Spec changes this round: <the feedback's spec change and what the sync pass wrote in, or "none">
Spec issues: <each sync-pass item and what was done, or "none">
Try it: <what's running and where; anything new about how to reach it>
Steps: <this round's checklist, all ticked>
Not reviewed or committed yet. "status?" works any time.
```

If the sync pass left Your-call items, ask them first, in their own picker, as after the full ready message. Then, unless an answer started a round, ask with AskUserQuestion — *"Tried it? More to change, done, or drop?"*:

- **Feedback** — "Type what to change in Other, or pick this and tell me next."
- **Done — review and commit** — "Checks all the feedback so far against the spec, reviews and commits it, and re-runs every check; then you try it once more before shipping."
- **Drop** — "Abandons it: deletes the worktree and branch (asks first)."

**Ship** typed during the rounds skips that last try: ship's step 1 validates, reviews and commits the rounds, and its checks run as usual.

### Done with feedback

When the user picks **Done** (or says "done", "that's it"), print `Wrap-up: <title>` with `· 1 Validate`, `· 2 Review and commit`, `· 3 Checks`, `· 4 Ready to test`, and tick it as usual:

1. **Validate** — step 4, on everything since sign-off, then the sync pass.
2. **Review and commit** — step 5 on the uncommitted diff: `/code-review high --fix` plus any project gate (and the sync pass if its fixes change behavior the spec describes), a commit in the repo's style naming the feature and the feedback, ending with the `Reviewed: /code-review high --fix` line, then fetch and merge `origin/main` and `main`.
3. **Checks** — step 6 in full: every How-to-verify bullet, plus each round's feedback check.
4. **Ready to test** — step 7's full message, with **Feedback folded in** filled, and its Feedback / Ship / Drop picker. Feedback from there starts at round 1 again.

## Ship

Print its checklist first and tick it as you go — `Ship: <title>` with `1 Validate and review feedback`, `2 Merge main`, `3 Checks`, `4 Unpushed commits`, `5 Fast-forward main`, `6 Push`, `7 Clean up` — and log each step.

1. If there are uncommitted changes: validate them (step 4, then the sync pass), then `/code-review high --fix` on them (plus any extra project gate, and the sync pass if its fixes change behavior the spec describes), then commit.
2. `git fetch origin`, merge `origin/main`, merge `main`. A conflict resolution gets reviewed before its commit.
3. If step 1 changed code or step 2 brought in anything new, run the checks again (step 6). A failure stops the ship: report it and wait.
4. **Unpushed commits on local `main`:** `git log --oneline origin/main..main`. These aren't this feature's, and the push would take them along. If there are any, list them and ask: **Push them too** / **Stop** — and wait.
5. **Check the main checkout is on `main`:** the first entry of `git worktree list --porcelain` must show `branch refs/heads/main`. If not, tell the user and wait.
6. **Stop every process you started**, then step out: `ExitWorktree` with action `keep`. You're now in the main checkout.
7. **Fast-forward local `main`:** `git merge --ff-only <branch>`.
   - Refused because `main` moved: `EnterWorktree` (`path`) back in and go to step 2.
   - Refused because uncommitted changes in the main checkout are in the way: tell the user exactly which files and wait. Never commit, stash or discard their work.
8. **Push:** `git push origin main`. Rejected because `origin` moved: `EnterWorktree` back in and go to step 2.
9. **Clean up:** `git worktree remove <worktree path> && git branch -d <branch>`.
10. Final message: `Shipped: <title>` with the pushed commit, and that this feature is finished: the session is back in the main checkout, so `/clear` and a new `/feature-flow` start the next feature in this same window.

## Drop

When the user picks **Drop**, or says drop (or abandon, scrap it):

1. Confirm first with AskUserQuestion: dropping deletes the worktree and its branch, including the spec; it can be recovered from a commit SHA for a while. **Drop it** / **Keep it**.
2. Commit everything, uncommitted feedback included: `git add -A && git commit -m "WIP: <title> (dropped)"`.
3. Stop every process you started, then `ExitWorktree` with action `keep`.
4. From the main checkout: `git worktree remove <worktree path> && git branch -D <branch>`.
5. Final message: `Dropped: <title>`, the WIP commit's SHA, and that `git branch <branch> <sha>` in the main checkout brings it all back (until git garbage-collects it). Like ship, it ends with `/clear` and a new `/feature-flow` starting the next feature in this window.

## Picking up

When `/feature-flow resume <worktree-path>` started you (the original session is gone), you've just entered the worktree. Read the spec (the one spec file this branch added, normally under `docs/specs/`) and the project's `CLAUDE.md`, then work out from git where things stand:

- no `Spec: …` commit → the spec was never signed off: say so and continue the design with `design.md` from step 5 (the draft exists), after its spec-format check;
- no build commit → start at step 2 (setup; ask the user to confirm which local files to copy, since you don't have the list from before the worktree), then 3;
- a build commit **without** `Reviewed: /code-review high --fix` → validate it (step 4) and review it (against the sign-off commit) before anything else;
- uncommitted changes → feedback rounds not yet reviewed: say so, re-run the checks they touch, and end with the round's Feedback / Done / Drop picker;
- otherwise → go to step 6 (verify), then the ready message.

Rebuild the checklist from what you found (and from the progress log, if it's still there), print it, and say in the ready message that this is a pickup and what you found.
