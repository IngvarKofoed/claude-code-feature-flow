# Feature flow: one session per spec, a background builder per build

`/feature-flow` replaces the spec-role / implementer-role pair with one
session per spec. You drive the design in `/spec` as today, inside a worktree
of its own. Clicking **Sign off and implement** hands the spec to a background
Opus session, which:

- sets up its own copy;
- builds;
- fixes spec text bugs itself and asks you only real decisions;
- verifies, reviews, merges main;
- and says it's ready to test.

You attach, test, give feedback, and say **ship**. It lands on `main` and
cleans up after itself.

One skill covers both halves, so the contract between them lives in one
file. Your project `CLAUDE.md` files need nothing new.

## Outcome

**What you get:**

- `feature-flow <topic>` in a terminal opens a session already in `/spec` on
  that topic. Its spec is written in a worktree of its own, so several specs
  can run side by side.
- **Sign off and implement** is offered:
  - at the draft, including next to any open questions;
  - at the sign-off question.

  The review runs while you read. When it raises nothing to decide, a builder
  starts in the background and the design session is done.
- **The builder pulls you in only for decisions only you can make.**
  Otherwise it ends with a ready-to-test message: what was built, how to try
  it, which Outcome bullets passed, and how the spec changed since you signed
  it.
- **Feedback, ship or drop, all in the builder session.**
  - Type feedback and it makes the changes.
  - **ship** lands the work on `main`, pushes it, and removes the worktree and
    branch.
  - **drop** abandons the spec after you confirm.

**How to verify** (in a throwaway repo whose `origin` is a local bare repo,
so nothing reaches GitHub):

- Run `feature-flow add a hello endpoint`. `/spec` starts on that topic. When
  the draft is written, `git worktree list` shows it under
  `.claude/worktrees/<slug>`.
- Pick **Sign off and implement** on a spec whose review raises nothing.
  - The spec is committed on the worktree branch.
  - `claude agents` lists `<repo>-<slug>`.
  - The design session says it's done and has left the worktree.
- When the builder is idle, `claude attach <repo>-<slug>` shows the ready
  message. It includes `git diff <sign-off commit> -- <spec>`, or "no spec
  changes".
- Type **ship**.
  - `git log origin/main` contains the build.
  - The main checkout's `main` equals `origin/main`.
  - `git worktree list` and `git branch` no longer show the worktree or its
    branch.
- Commit something on local `main` without pushing it, then ship a build.
  Before pushing, ship lists that commit and asks.
- Start two specs and implement both, in a repo whose ports can be set
  through environment variables or flags. The two builders run at once with
  no port clash, and each one's dev server answers on its own port.
  - In mermaid-office, the second builder uses the `:8612`/`:8613` instance
    its `CLAUDE.md` describes.

## Key decisions

- **One skill, two modes** (new).
  - `/feature-flow <topic>` is design mode.
  - `/feature-flow build <spec>` is build mode. The design session launches
    it, and you can run it yourself to restart a build.

  It wraps `/spec` and changes nothing in `/spec`, spec-role,
  implementer-role, or any project `CLAUDE.md`.
- **The worktree is entered when the draft is first written** (diverges from
  the earlier "after your first message"). That's the moment `/spec` picks the
  slug, so the worktree, its branch (`worktree-<slug>`) and the spec file
  share one name. Phases 1–3 only read, so they run fine in the main
  checkout.
- **Sign-off pickers come from the wrapper** (reuses `/spec`'s wrapper rule).
  - The draft handoff becomes one picker: any open questions, plus "Sign off
    and implement / Sign off, build later / I've marked it up".
  - The sign-off question gets "Sign off and implement (Recommended)" first.
  - Under `/spec`'s rules the review starts when either picker is shown. If
    you accept open-question defaults, the review stays valid.
- **The spec commit is the sign-off reference** (new).
  - The design session commits the spec on the worktree branch before
    launching the builder.
  - The builder may fix spec text, but its verifier reads Outcome from that
    commit, so the builder can't move its own finish line.
  - The ready message shows the spec diff since that commit.
- **The builder is a background Opus session at your usual effort** (new).
  - It is launched as `claude --bg -n <repo>-<slug> --model opus
    "/feature-flow build <spec>"` from inside the worktree.
  - No `--effort` flag, so your settings apply (xhigh).
  - The design session leaves the worktree (`ExitWorktree` keep) before it
    ends, so two sessions never share one checkout.
- **The builder sets up its own copy** (new).
  - It copies the files git ignores and that can't be regenerated, from your
    main checkout: `.env` files, local databases, `.claude/settings.local.json`.
  - It reruns the repo's own install steps for everything else.
  - It runs its own copy the repo's way.
    - Where the project's `CLAUDE.md` describes a second copy, it follows
      that, as with mermaid-office's `:8612`/`:8613` instance.
    - Otherwise it changes ports only through environment variables or
      command-line flags, never by editing tracked files.
    - If neither works, the ready message says it can't run alongside
      another copy.
  - It never moves or edits anything in the main checkout.
- **Commit and land rules live in the skill** (reuses `/commitandpush`'s
  pattern).
  - Starting a build is your request to commit on its branch.
  - Its own `/code-review high --fix` answers `CLAUDE.md`'s
    review-before-commit question. Any extra gate the project adds, such as
    a design pass on UI diffs, still runs.
  - **ship** is your request to land and push. Landing is a fast-forward of
    local `main` driven by `git -C`, then a push. There's no squash and no PR.
- **The builder carries the safety rules the scaffold change removed from
  `CLAUDE.md`** (new).
  - Never kill a server it didn't start.
  - Never commit, stash or discard anything in the main checkout.
  - Never work in a checkout another session uses.
- **Recovery by inspection, not a status file** (new). Restarting build mode
  in the worktree reads where things stand from git: the sign-off commit, any
  build commit, uncommitted changes. It carries on from there.

## Goals

- You touch a spec only to design it, answer real decisions, test it, and say
  ship.
- Several specs in flight at once, each in its own session and worktree.
- Nothing to set up or document per repo before using it.

## Non-goals

- **Notifying you when a builder needs you.** `claude agents` shows its
  state, and notifications are yours to arrange.
- **PRs, squash commits, or landing anywhere but `main`.**
- **Specs that span several repos.**
- **Changing `/spec`, spec-role, implementer-role or any project
  `CLAUDE.md`.**
- **Running the scaffold audits** that remove the old worktree sections in
  flux and mermaid-office. That's the separate step this skill unblocks.

## Design

### Starting

- A shell function, `feature-flow() { claude "/feature-flow $*"; }`, goes in
  your `~/.zshrc`. The repo's README shows it; the skill never edits your
  shell files.
- **Design mode first checks** that the repo is a git repo whose default
  branch is `main` and that has an `origin`. If it isn't, it says the build
  half is unavailable and runs plain `/spec`.
- **Then it invokes `/spec` with the topic.** Right before `/spec` writes the
  draft, it calls `EnterWorktree` with the slug and writes the spec there.
  - The worktree branches from `origin/main` (unless `worktree.baseRef` is
    `head`), so local `main` commits that haven't been pushed aren't in it.
  - The builder merges local `main` in as its first step (Build step 1), so
    it builds on what the spec was researched against.
- **Design mode's own side effects override `/spec`'s read-only rule.** That
  covers `EnterWorktree`, the spec commit and launching the builder. Nothing
  else in the design session writes outside the spec file.

### Sign-off

- **The draft picker.** The draft handoff ends with one AskUserQuestion
  instead of "reply when done":
  - one question per open question, each with its default;
  - "Sign off on it as it stands, or mark it up first?", with the options
    **Sign off and implement**, **Sign off, build later** and **I've marked
    it up**.

  None of these is tagged Recommended, because you may not have read the
  draft yet. AskUserQuestion holds four questions, so the picker carries at
  most three open questions. Any more are asked first, in a picker of their
  own, and the sign-off picker follows.
- **The sign-off question** (`/spec` phase 6) gets **Sign off and implement
  (Recommended)** first. **Sign off, build later** and **Not yet** follow.
- **On "implement", the session waits for the review.**
  - **Changed answers:** if you answered an open question with something
    other than its default in the same picker, the answers go into the spec
    and a fresh review runs on the new text. The rest is the same as below.
  - **No decisions:** fixes and "already decided" notes are applied, then it
    launches.
  - **Decisions:** they go in one picker whose last question is "Then:
    **Build now** (Recommended) / **Hold**". Build now integrates the answers
    and launches, with no second sign-off; the answers plus **Build now** are
    the sign-off on the revised text. Hold keeps the session open. With more
    than three decisions, the rest come in an earlier picker, and
    "Then:" is always the last question of the last one.
- **On "build later":** it commits the spec and leaves the worktree. It prints
  the launch command, and you can also ask it to launch later.

### Launch

1. In the worktree: `git add <spec>` and `git commit -m "Spec: <title>"`.
   This commit is the sign-off reference. It is a docs-only commit, made at
   your click, so no review question.
2. `claude --bg -n <repo>-<slug> --model opus "/feature-flow build <spec>"`,
   run from the worktree.
3. `ExitWorktree` (keep). Then tell you the session name and
   `claude attach <repo>-<slug>`, and that this session is done.
4. If the launch fails, print the command for you to run, and stay in the
   worktree until you do.

### Build mode: to "ready"

1. **Orient.**
   - Read the spec and the project's `CLAUDE.md`.
   - The sign-off commit is the commit that added the spec on this branch.
   - Any later commits or uncommitted changes mean this is a restart:
     continue from that state rather than starting over.
   - On a fresh start, merge local `main` in before building. A clean merge
     needs no review.
   - **Precedence.** This skill's worktree and landing rules win over any
     worktree section still in the project's `CLAUDE.md`, such as
     mermaid-office's `wt/<slug>` naming or flux's landing steps.
     - Every other gate in the project's `CLAUDE.md` still runs. For example,
       flux's design pass on UI diffs (`CLAUDE.md:131`) runs alongside
       `/code-review high --fix`.
2. **Set up the copy** as in Key decisions.
   - `git ls-files --others --ignored --exclude-standard` in the main
     checkout lists the candidates. Leave out `.claude/worktrees/`, and
     regenerate dependencies and build output rather than copying them.
   - Copy a database together with its `-wal` / `-shm` files.
3. **Build** per the spec's Implementation strategy, writing the changelog
   entry the project's `CLAUDE.md` asks for. Subagents must wait for their
   own helpers before reporting.
4. **Spec issues.**
   - A text bug with one obvious fix gets fixed in the spec and listed in the
     ready message.
   - A question with more than one plausible build goes to you through
     AskUserQuestion. The session then waits until you attach.
5. **Review and commit.**
   - Run `/code-review high --fix` on the uncommitted diff, then commit it.
   - `git fetch`, then merge `origin/main` and local `main`.
   - A conflict resolution is authored work: it gets its own
     `/code-review high --fix` before its commit.
6. **Verify, last.**
   - A fresh Sonnet subagent gets the Outcome section from the sign-off
     commit (`git show <sha>:<spec>`). It runs each verify bullet against the
     merged, reviewed result: pass, fail, or can't verify, with the reason.
   - A failure gets fixed, the fix is reviewed and committed, and the checks
     run again.
   - The results in the ready message are for the commit it names.
7. **Ready message.**
   - What was built, and how to try it: commands, URLs, ports.
   - Every Outcome bullet with its result.
   - Spec changes since sign-off.
   - Deviations, and anything the review couldn't settle.

### Feedback, ship, drop

- **Feedback.** Each round is made as uncommitted changes, and the Outcome
  bullets it touches are re-run.
  - No review per round. Ship reviews them all at once.
  - If feedback changes behaviour the spec describes, the spec is updated
    too, and that's said in the reply.
- **ship** (also "ship it" or "land it"):
  1. Review the uncommitted feedback changes, if any, with
     `/code-review high --fix`, then commit.
  2. Fetch, then merge `origin/main` and `main`. A conflict resolution gets
     reviewed before its commit.
  3. If the review changed code or the merge brought in anything new, rerun
     the Outcome checks. A failure stops the ship: tell you and wait.
  4. List what local `main` holds that isn't on `origin` yet: `git -C <main
     checkout> log origin/main..main`. Those commits aren't the builder's,
     and the push would take them along. If there are any, list them and ask
     before going on.
  5. Fast-forward local `main` with `git -C <main checkout> merge --ff-only
     <branch>`.
     - Refused because main moved: merge again and retry.
     - Refused because the main checkout has changes in the way, or isn't on
       `main`: tell you and wait.
  6. `git -C <main checkout> push origin main`. If it's rejected: fetch,
     merge, retry.
  7. Stop what it started, then `git -C <main checkout> worktree remove
     <path>` and `branch -d <branch>`.
  8. A final line with the commit and a reminder that `claude rm <name>`
     clears the finished session from the list.

  A permission prompt along the way is fine, because you're attached.
- **drop.** Confirm first.
  1. Commit everything, uncommitted feedback included, as one WIP commit on
     the branch.
  2. Stop anything it started.
  3. Remove the worktree and `git branch -D` its branch.
  4. Print the WIP commit's SHA. The spec goes too, and `git branch <branch>
     <sha>` recovers all of it.
- **Before removing a worktree,** on ship or drop, stop every process the
  builder started from it: dev servers, simulators, watchers.

## Alternatives considered

- **Sign off again after the review's decisions are answered**, before the
  build starts. That's safer, but it adds a round on 35 of every 63 advance
  sign-offs, going by spec-role's record. The user chose to let the answers
  plus **Build now** start the build.

- **Two skills (a design skill and a builder skill).** One skill keeps the
  contract between them in one file: launch command, sign-off commit,
  ready-message shape.
- **A "fresh checkout setup" section in each `CLAUDE.md`.** It would go stale
  and need the scaffold run first. Discovering setup from the main checkout
  has neither problem.
- **A status file for recovery.** Git already records the sign-off commit,
  the build commit and uncommitted work. A file would be a second source that
  can disagree with it.
- **Squash at ship, pushing `HEAD:main` directly.** It had a race that could
  revert another spec's landing. Fast-forwarding local `main` through `git -C`
  has none.

## Implementation strategy

*Not part of the design — a starting point for whoever builds this.*

- **Single agent, Opus 5.5.** One `SKILL.md`, with build mode perhaps split
  into a reference file that only builders load, plus a README with the shell
  function. The two modes share the launch contract, so there's no chunk a
  subagent could take without re-reading the rest.
