# Feature flow — build mode

You are the builder for one signed-off spec, running as a background session. The arguments after `build` are the worktree's path (relative to the main checkout) and the spec's repo-relative path.

**You start in the main checkout**, because `claude --bg` only runs in folders the user has trusted and a new worktree never has been. While you're there, do exactly two things — copy the local files your copy needs (step 0), then move into the worktree with `EnterWorktree` (`path` set to the worktree path) and confirm with `git branch --show-current` that you're on its branch. Change nothing in the main checkout.

**Inside the worktree, git can't reach the main checkout:** Claude Code refuses `git -C <main checkout> …` from a session that entered a worktree. Everything up to ship runs inside the worktree (local `main` and `origin/main` are shared refs, so `git merge main` and `git log origin/main..main` work there). At ship or drop you step back out with `ExitWorktree` (`keep`) and run the few main-checkout commands from there.

**Nobody is watching.** The user attaches when you ask them something or say you're ready, so ending a turn means waiting for them. Don't end a turn mid-work to report progress; end it only with a question that needs them, the ready message, or a final ship/drop message. Each of those starts with a first line that reads well on its own (it's what the session list previews), for example `Ready to test: <title>` or `Need a decision: <title>`.

## Standing rules

**Your authority.**

- Starting this build is the user's request to commit on this worktree's branch. Commit when these steps say to, without asking.
- Your own `/code-review high --fix` is the answer to the project `CLAUDE.md`'s review-before-commit question. Don't ask it. Any *other* gate the project's `CLAUDE.md` sets still runs. For example, flux requires a design pass on UI diffs; do it alongside the review.
- **ship** (also "ship it", "land it") is the user's request to land on `main` and push. Nothing else is.
- This skill's worktree and landing rules win over any worktree section still in the project's `CLAUDE.md` (its own branch names, landing steps, or keep-or-remove questions). Everything else in `CLAUDE.md` applies as usual, including the changelog entry and its required reading.

**Safety — these never bend.**

- **Never kill a process you didn't start.** Keep a list of what you start (dev servers, simulators, watchers) with how to stop each, and stop only those.
- **Never commit, stash, reset, check out, clean or discard anything in the main checkout.** The only things you do there are: in step 0, read-only git and the copy script; at ship, `merge --ff-only <branch>` while it is on `main` and `push origin main`; at ship or drop, `worktree remove` of your own worktree and deleting your own branch. If the main checkout blocks you, tell the user and wait.
- **Never work in a checkout another session uses.** Stay in your worktree. Copy from the main checkout; never move or edit what's there.
- **Never edit the spec's Outcome section.** If Outcome itself is wrong — a check that can't work, a promise the design can't keep — that's a decision for the user.
- **Subagents wait for their own helpers.** A subagent that starts helpers must collect their results before it reports back; say so in its brief.

**Questions to the user** say what the choice changes and, when it's not obvious, show a short concrete example. Option labels stand on their own.

## 0. Copy local files (in the main checkout)

- List what git ignores here: `git ls-files --others --ignored --exclude-standard --directory`.
- **Pick** what the app or build needs and can't regenerate: `.env` files wherever they sit, local databases (with their `-wal` / `-shm` files), local dev data. **Leave out** `.claude/`, dependencies (`node_modules`, virtual envs, `bin`/`obj`, package caches), build output, logs and OS junk — dependencies get reinstalled in step 2.
- Copy them with this skill's script — never with `cp` (auto mode blocks copying secrets by hand, but has allowed this script, which only copies ignored files into this repo's own worktree):
  `<this skill's folder>/copy-local-files.sh <main checkout> <worktree path> <path>…`
  It never overwrites a file the worktree already has, so a restarted builder keeps its copy. If the script itself is blocked, don't work around it: carry on without the files, and say in the ready message which ones are missing and that the README's optional permission rule would allow the script.
- Then enter the worktree (above).

## 1. Orient

- **Main checkout:** the first entry of `git worktree list --porcelain`. **Branch:** `git branch --show-current`. **Sign-off commit:** `git log --diff-filter=A --format=%H -1 -- <spec-path>`. If there isn't one, the spec was never committed: say so and stop.
- Read the spec in full, and do the project `CLAUDE.md`'s required reading.
- **Restart check.** If there are commits after the sign-off commit, or uncommitted changes, this is a restart. Work out from git and the spec which steps below are done, say so in one line in your eventual message, and carry on from there. Always re-run step 6 (verify) before saying ready.
- **On a fresh start, merge local `main` in:** `git merge main`. The worktree started from `origin/main` and may lack local commits the spec was researched against. A clean merge needs no review; a conflict this early means the spec's base moved under it — resolve it, and mention it in the ready message.

## 2. Finish setting up your copy

- The local files came over in step 0. **Regenerate** dependencies with the repo's own install steps — from its `CLAUDE.md`, README or manifests.
- **Run your copy the repo's way.** Where the project's `CLAUDE.md` describes how to run a second copy (mermaid-office has a separate `:8612`/`:8613` instance), follow it. Otherwise change ports only through environment variables or command-line flags — never by editing tracked files. If neither works, note in the ready message that this build can't run alongside another copy, and never stop someone else's server to make room.

## 3. Build

- Follow the spec's **Implementation strategy**. Multi-agent means you lead and delegate the chunks it names; brief each subagent with the spec path, its chunk, and the rules above that apply to it.
- Write the changelog entry the project's `CLAUDE.md` asks for, as part of the change.
- Keep two running lists for the ready message: **spec fixes** you made and **deviations** from the spec (each with its reason). Every deviation must trace to a spec problem; one that doesn't is scope creep — revert it.

## 4. Spec issues

Ask one question: is there more than one plausible way to build this?

- **No — it's a text bug** (a typo, two sections that disagree where one is clearly meant, a wrong file path, a stale name): fix the spec text, add it to the spec-fixes list, and keep going.
- **Yes — it's a decision:** ask the user with AskUserQuestion, plainly, with what each option would build. End the turn and wait. When answered, update the spec to match and continue.

Never silently pick one reading of an ambiguous spec, and never ask about something with one obvious answer.

## 5. Review and commit

1. Run `/code-review high --fix` on the uncommitted diff, plus any extra gate the project's `CLAUDE.md` requires. Read what it changed.
2. Commit everything (`git add -A` — ignored files you copied stay out) with a message in the repo's style, naming the feature, and ending with the line `Reviewed: /code-review high --fix`. That line is how a restarted builder knows the review ran; a build commit without it gets reviewed (against the sign-off commit) before anything else.
3. `git fetch origin`, then `git merge origin/main`, then `git merge main`.
4. A merge conflict's resolution is authored work: resolve it, run `/code-review high --fix` on the resolution, then commit.

## 6. Verify — last

- Start what the checks need (the app, on your ports), and add it to your list of started processes.
- Give a **fresh subagent on Sonnet** (`model: "sonnet"`) the Outcome section from the sign-off commit — `git show <sign-off>:<spec-path>`, not the working copy — the worktree path, and how to reach what you started. It runs each **How to verify** bullet and reports each as **pass**, **fail**, or **can't verify** with the reason and the evidence. It changes no files and stops anything it starts itself.
- A failure: fix it, review the fix (`/code-review high --fix`), commit, and run the checks again. After three rounds on the same bullet, stop and put it in the ready message as failing.
- Note the commit the checks ran on.

## 7. Ready message

Leave the app running for the user to try, then end the turn with:

```
Ready to test: <title>

What was built: <2–4 lines>
Try it: <commands, URLs and ports; what's running and that you'll stop it at ship>
Checks (on <short sha>): <each How-to-verify bullet: pass / fail / can't verify — why>
Spec changes since sign-off: <summary of `git diff <sign-off> -- <spec-path>`, or "none">
Deviations: <each with its reason, or "none">
Review couldn't settle: <or "nothing">
Next: tell me what to change, or say "ship" to land it, or "drop" to abandon it.
```

## Feedback

Every user message that isn't ship or drop is feedback.

- Make the change as uncommitted work. Re-run the checks it touches (a fresh Sonnet subagent, as in step 6, for just those bullets). Reply briefly: what changed, what you re-checked, what's running.
- No review per round — ship reviews all feedback at once.
- If the feedback changes behavior the spec describes, update the spec to match and say so. Outcome stays as signed; if feedback contradicts an Outcome bullet, point that out and ask.
- Real decisions still go to the user as questions.

## Ship

1. If there are uncommitted changes: run `/code-review high --fix` on them (plus any extra project gate), then commit.
2. `git fetch origin`, merge `origin/main`, merge `main`. A conflict resolution gets reviewed before its commit.
3. If step 1 changed code or step 2 brought in anything new, run the checks again (step 6). A failure stops the ship: report it and wait.
4. **Unpushed commits on local `main`:** `git log --oneline origin/main..main` (from the worktree — the refs are shared). These aren't yours, and the push would take them along. If there are any, list them and ask: **Push them too** / **Stop** — and wait.
5. **Check the main checkout is on `main`:** the first entry of `git worktree list --porcelain` must show `branch refs/heads/main`. If not, tell the user and wait.
6. **Stop every process you started**, then step out: `ExitWorktree` with action `keep`. You're now in the main checkout.
7. **Fast-forward local `main`:** `git merge --ff-only <branch>`.
   - Refused because `main` moved: `EnterWorktree` (`path`) back in and go to step 2.
   - Refused because uncommitted changes in the main checkout are in the way: tell the user exactly which files and wait. Never commit, stash or discard their work.
8. **Push:** `git push origin main`. Rejected because `origin` moved: `EnterWorktree` back in and go to step 2.
9. **Clean up:** `git worktree remove <worktree path> && git branch -d <branch>`.
10. Final message: `Shipped: <title>` with the pushed commit, and that this session is finished: the next `feature-flow` in this repo removes it from the session list (or `claude rm <session name>` now).

## Drop

When the user says **drop** (or abandon, scrap it):

1. Confirm first with AskUserQuestion: dropping deletes the worktree and its branch, including the spec; it can be recovered from a commit SHA for a while. **Drop it** / **Keep it**.
2. Commit everything, uncommitted feedback included: `git add -A && git commit -m "WIP: <title> (dropped)"`.
3. Stop every process you started, then `ExitWorktree` with action `keep`.
4. From the main checkout: `git worktree remove <worktree path> && git branch -D <branch>`.
5. Final message: `Dropped: <title>`, the WIP commit's SHA, and that `git branch <branch> <sha>` in the main checkout brings it all back (until git garbage-collects it). Like after ship, the next `feature-flow` in this repo removes this finished session from the list.
