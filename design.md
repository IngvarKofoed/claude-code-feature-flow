# Feature flow — design

You design the feature's spec with the user, in this session: what to build, which approach, then a draft they mark up until they sign it off. The spec is written inside a worktree of its own, and after sign-off this same session builds it (`build.md`). Revising prose is cheaper than revising a half-finished branch, so the load-bearing choices get made here, on purpose, before any code changes.

## Before starting

What a spec contains, and how its fresh-eyes review runs, live in two shared files, `format.md` and `review.md`, in the `spec-format` folder beside this skill's own folder, the one this file sits in (normally `~/.claude/skills/spec-format/`). Below, `format.md` and `review.md` mean those two files.

Check that both are there with `test -f` (normally `test -f ~/.claude/skills/spec-format/format.md && test -f ~/.claude/skills/spec-format/review.md`). If either is missing, say so in one line and stop:

> *"/feature-flow needs spec-format to design, and it's missing or incomplete. Install it with `/skill-manager:add https://github.com/IngvarKofoed/claude-code-spec-format.git --dir spec-format`, then tell me to go on."*

When they say go on, check again.

**Show the design from the start.** Right after the check, start the feature's state file, so the user's status line and `/feature-flow status` show this design while it's still a conversation (see `build.md`, "Progress you can see"). There's no worktree yet, so pass `--pending`: the file is kept in the repo's git folder under this window's session id.
`python3 <this skill's folder>/state.py set --pending --title "<the topic, in a few words>" --phase design --step "Understand" --doing "understanding the request"`
Keep it current with `--pending` through steps 1–3: `--waiting "answer my questions"` when you ask them, `--step "Research" --doing "reading the code"`, and `--step "Options" --waiting "pick an approach"`. The first `set` inside the worktree (step 4) takes it over, start time and all. If the design ends before there's a worktree (the user stops, or this turns into plain `/spec`), run `state.py clear`.

**Picking up an unfinished design.** When `build.md`'s "Picking up" sends you here (a resumed session found no `Spec: …` commit), you're already in the worktree and the draft exists. Run the check above, read `format.md`, and start at step 5 with the recap. You have no list of the main checkout's ignored files, so when the build reaches its step 3, ask the user to confirm which local files to copy.

## Read-only until sign-off

Until the user signs off, the only side effects are `EnterWorktree` (step 4) and writing the one spec file. After sign-off, `build.md` takes over, starting with the spec commit.

- Reading is fine: Read, Grep, Glob, `git log` / `blame` / `diff`, `ls`, `cat`, and any other read-only command (`date`, package inspection, a fetch).
- Creating and editing the spec file, and the folder it goes in, is fine.
- A mockup the user asked for ("Mockups", below): its subagent works in a scratch folder outside the repo and publishes a private Artifact page. Nothing of it lands in the repo.
- Nothing else: no source code, config, tests or scratch files, and no command with side effects (installs, commits, generators, migrations).

If a question can only be answered by trying something, put it in the spec's Open questions and let the user run it. Don't break the rule to "just check".

## 1. Understand

The question to answer before anything else: **what is the smallest interesting version of this feature?** If you can't name it in one sentence after the user's first message (or they gave no topic), ask 3–5 focused questions until you can. Scope creep is the main way specs go wrong, and a spec that ships less than the user first described is usually the better one.

Also pin down what's explicitly out of scope. That's the start of Non-goals.

## 2. Research

Read the code, docs and config the feature touches, so the spec names what's really there: file paths, functions, the data model, the invariants. Read the project's `CLAUDE.md`, and `docs/CONCEPT.md`, `docs/ARCHITECTURE.md` or other top-level docs where they're relevant. Read independent files in parallel.

Look hardest for **existing patterns the feature could reuse**. The most valuable thing a spec can say is "this reuses X"; the next is "this deliberately diverges from X because Y". Both need you to know X.

Steps 1–3 only read, so they run in the main checkout.

## 3. Options, then wait

Before writing anything, present 2–3 real approaches in chat. Each gets:

- a one-line name ("Approach A: server-authoritative, client renders speculatively");
- the shape of the change in 2–4 sentences;
- its main tradeoff against the others: complexity, performance, blast radius, future flexibility.

Then your recommendation, with the reason. Ask which to take, and **wait**: the user may pick one, mix them, or send you back for others. Don't draft until they've chosen.

A real option differs on a load-bearing decision (server- or client-authoritative, one table or two), not on naming or syntax. If the honest options share 90% of the design, or there's only one reasonable approach, say so plainly, justify it in a sentence or two, and confirm before drafting. Never pad the list with a weak alternative.

**When the feature changes what someone sees,** offer a mockup with the options, in the same turn: one AskUserQuestion, *"Mock it up in the app's own style?"*, with **Each approach** (Recommended when the approaches differ in what the user sees), **Only the one I choose** (Recommended when they don't), and **No mockup**. Say in the question which screen it would show. Never offer it for work nobody sees (a refactor, a backend fix).

- **Each approach:** start one mockup subagent per approach ("Mockups", below), say in one line that they're running, and end the turn; when they're back, give the links and ask which approach to take.
- **Only the one I choose:** wait for the choice, then start the mockup in the background and go on to the draft; it doesn't wait for it.

## Mockups

A mockup shows the changed screen **in the app's real look**, never a sketch or a wireframe: the user knows the existing UI, so a mockup in the same style is the quickest to read. The user may also ask for one at any point in the design; same rules.

- **Delegated, in the background.** Start a subagent, on **Sonnet** (`model: "sonnet"`) by default, or **Opus** (`model: "opus"`) when the screen has several states or a flow, or must match a large design system closely. Never build it in this session: it's long HTML and CSS work that would fill the conversation. Set the state file's `--doing` to "mockup: <what>" while it runs.
- **Its brief:** the screen(s) it shows and what changes on them (the approach, or the chosen design); the repo path; and to build it from the app's own UI, reading only:
  - the components, stylesheets and design tokens behind those screens, plus any design-system skill the project's `CLAUDE.md` names (the FOSS design system in the work repos);
  - with the app's real class names, colors, spacing and fonts carried into one self-contained page, and real content (real names, plausible values), not lorem ipsum.

  It may look at the app if it's already running, but never starts, installs or changes anything in the repo, and works in its own scratch folder. It publishes the page as a private Artifact (following the Artifact tool's rules), with a visible "Mockup" label and a title naming the screen, and returns the link (the full URL, never just a title), the full path of the HTML file it published from (kept in its scratch folder, so the user can open it locally), and a line on what it shows.
- **Showing it to the user is your job, not the subagent's,** and it happens as soon as the subagent is back, before any check of your own. The user can't see anything the subagent does, including an Artifact it "opens". So every time a mockup is published or republished, you, the main session:
  1. **open its local copy in the user's browser** (`open <file>` on macOS, `xdg-open` on Linux, `start` on Windows). This always works; a claude.ai link can show "Page not found" when the browser is signed in to another account, and private pages open only for the account that made them;
  2. **put both in your message,** each on its own line, starting with the screen it shows: `Mockup, chip settings: https://claude.ai/artifact/...` and `Local copy: /path/to/mockup.html`, plus one line on what to look at. With several mockups, one pair per mockup. If the user says the link shows "Page not found", say it's probably the other account, and point to the local copy or `/artifacts` in the terminal.

  Never write that a mockup was opened or is ready without its link and local copy in that same message. If the subagent returned neither, say so and ask it for them (SendMessage); don't describe a mockup you can't show.
- **Feedback on it** goes to the same subagent (SendMessage), which republishes to the same link; show it again as above, saying what changed.
- **Into the spec:** the chosen design's mockup link goes in Design ("Mockup: <link>, the look to match"); a rejected approach's link goes beside it in Alternatives considered. A mockup that's still running when the spec reaches sign-off is waited for, since the user signs what they can see: say so in one line.

## 4. Draft, in the worktree

1. **Read `format.md`.** It sets the spec's path and slug, its length, the template, the worked example and how to call the Implementation strategy. Follow it on this pass and every later one.
2. **Note the main checkout's local files** while you're still in it: `git ls-files --others --ignored --exclude-standard --directory`. Keep the list for `build.md` step 3; from inside the worktree, git can't reach the main checkout.
3. **`EnterWorktree`** with `name` set to the slug. Once per feature, never twice. The worktree branches from `origin/main` (unless `worktree.baseRef` is `head`), so it may lack unpushed local `main` commits; the build merges local `main` in later.
4. **Move the state file into the worktree**: `python3 <this skill's folder>/state.py set --title "<the spec's title>" --phase design --step "Draft" --doing "drafting the spec" --spec <spec path>`, now without `--pending`; it takes over the pending one from steps 1–3. The design is overall step 1 of ten (`1/10 Design`; see `build.md`, "Progress you can see"); keep its `--step` and `--doing` current: `--step "Markup and questions" --waiting "answer the open questions or mark up the draft"` when you hand the draft over, `--step "Revising" --doing "revising: your answers and markup"` while you integrate, `--step "Sign-off" --waiting "sign off on the spec"` with the sign-off picker, `--step "Review" --doing "fresh-eyes review running"` while it runs after sign-off, with `--waiting "decide the review's findings"` when its decisions come to you.
5. **Write the spec** at the path `format.md` gives, inside the worktree. Every draft carries Outcome and the Implementation strategy from the start: the user signs off on both, the build is checked against Outcome, and the builder runs on the model the strategy names.

## 5. Recap and markup

Once the draft is on disk, send one handoff message: a short recap of what the spec proposes, then how to mark it up. The recap is the substance; it's the last thing the user reads about the proposal before opening the file, so it should let them sanity-check the design and see which parts deserve a close look.

**The recap** starts with *"The short version of what it proposes:"* and renders the spec's Key decisions as consequences, meaning what changes and what to watch, in 3–5 bullets rather than a table of contents:

- the load-bearing change, and what cascades from it;
- the concrete edits or new pieces, with real paths and names;
- what deliberately stays the same, where a reader might worry;
- any consequence worth watching (performance, throughput, blast radius).

If the spec won't compress into bullets like these, Key decisions is usually missing the load-bearing choice or padded with detail, so fix the spec. Close the recap with the Implementation strategy's headline in one line; it's part of what the user signs. If open questions remain, add one line saying you'll put each to them next with its default pre-selected. For example:

> *"The short version of what it proposes:*
> - *One source of truth — bump `WELLS_PER_STRIP` and `SAMPLES_PER_STRIP` 8→12; scheduler durations, queue/tray math, and the operator-card pills all cascade.*
> - *Two manual edits — the lone hardcoded `repeat(8, …)` at `continuous.css:1082`, and extending the SVG strip template `#STICK_1` with `HOLE_9..12` plus a longer body rect.*
> - *No structural scheduler change — it's parameterized; the real consequence is longer loading (80→120 s) and reagent-add (20→30 s) steps, a throughput thing to watch.*
> - *Tray stays 24 samples → now 2 strips/tray instead of 3.*
>
> *Implementation strategy: **single agent on Opus 5.5** — one constant drives the cascade, and both manual edits sit on the same strip layout.*
>
> *Two open questions remain (the longer arm-work; tray = 2 strips) — I'll put each to you next with its default pre-selected, so a click accepts or you can override."*

**The markup instructions** close the message, with the spec's path inside the worktree:

> *"Draft is at `<spec path>`. If you want changes, add inline comments anywhere in the file by prefixing a line with `////` — e.g., `//// this section should also cover the migration case`. You can also rewrite or restructure as you like."*

**Open questions get their own picker,** right after the handoff: one AskUserQuestion, one question per open question, up to four, with the spec's `Default:` as the first option tagged `(Recommended)` and the realistic alternatives after it. A click accepts a default; Other takes their own answer. No sign-off option goes in this picker, and no review starts: the answers may still change the spec.

- More than four open questions is a smell. Ask the four that shape the design most and fold the rest into the next pass.
- A question with no real alternative to its default isn't open. Settle it in the draft instead.
- The picker doesn't stop the user marking up the file too, so check for `////` lines when the answers come back.

Then wait. Don't revise ahead of their answers.

**Without open questions,** go from the handoff straight to step 6, in the same turn. The markup instructions still come first, so the user can mark the draft up and pick **Not yet**.

### Revising

When the answers come back, or the user says they've marked the file up ("I've added comments", "take another pass", "look at the file again"):

1. Re-read the spec from disk.
2. Integrate every line starting with `////` into its section, as feedback on the text around it, then **delete the `////` line**. It's scaffolding, not part of the spec.
3. Fold in the open-question answers, from the picker or edited in the file (a replaced default, a rewritten or deleted question), and remove the resolved questions.
4. **The user's own edits win.** Where they rewrote or restructured text, their words are the source of truth: make the rest of the spec consistent with them, and never revert them to yours. This is the most important rule of the pass.
5. Surface any new questions the changes raise, as open questions in the spec or in chat.
6. Re-derive Outcome and the Implementation strategy from the design. If either moved, say so in one line before the next sign-off ask, so the user never signs a change they didn't see.

Loop, with new open questions in a new picker, until none remain and the user has no more changes. Then go to step 6.

## 6. Sign-off

Sign-off is explicit, or it hasn't happened. When the spec is ready (every question answered and folded in), ask for it with **Here's what you get** inside the picker, read from the spec on disk, so the user signs what they can see:

- Outcome's **What you get** and **How to verify** bullets;
- the Implementation strategy's headline;
- one line on what changed since the user last saw the spec (their answers, their markup, your fixes), or "nothing changed".

Ask in one AskUserQuestion, *"Do you sign off on this spec?"*, with exactly these options, in this order. Give every option the same `preview`: the block above, as short markdown lines, since it sits in a narrow box beside the options. The same preview on all three keeps it in view whichever one is highlighted.

- **Sign off and build (Recommended)**: "Builds it here once the fresh-eyes review is back with nothing for you to decide."
- **Sign off, build later**: "Commits the spec once the review is handled; you start the build when you want."
- **Not yet — more changes**: "Mark the file up with `////`, or type what to change in Other."

Text typed in Other is a change request. Never put this picker next to a question that's still open.

- **The preview is where the block goes,** not chat text before the picker: that text may be off screen while the picker is open.
- **Keep the question to that one line.** A summary of the design in the question is not What you get, and doesn't replace the preview.

**Start the review in the same turn,** in the background, just before the picker goes out, so it runs while the user reads. Start it per `review.md`'s "Starting a review", and note the spec's hash. Skip the launch only if a review is already running, or has finished, on this exact text.

Never infer sign-off from:

- answering the last open question, or clicking through the defaults;
- praise for part of the spec ("nice", "that section looks good"), especially next to another change;
- silence, or the user moving on to something else.

**On every answer,** re-read the spec from disk and compare the hash first, since the user may have edited it while reading. `////` lines mean **Not yet**, whatever they clicked. Any other change means the sign-off stands on the new text, but the review read the old one.

**Which text a review vouches for** is `review.md`'s "When a review counts". Apply it whenever the spec changes or a review ends. When a review goes stale, stop it (TaskStop) and say so in one line naming what changed, since an unexplained stop looks like a failure. Start a fresh one at the next sign-off ask, or straight away if the user has already signed off on the new text. One exception: your edits that settle a returned review's findings get the quick check from "Handling the findings", not a fresh review, unless an answer brought in something the review never saw (`review.md`, "When a review counts", Settling its decisions; steps 7 and 8).

**Hold findings** that arrive before the user answers, and handle them after.

**Not yet** goes back to step 5's revising pass: with what they typed, or once they've marked the file up (if they gave nothing, ask in one line what should change). Then on to this step again.

## 7. After "Sign off and build"

1. **Wait for the review.** If it isn't back, say in one line that it's still running and the build starts once it's back with nothing for you to decide, then end the turn. Its completion notice resumes the work.
2. **Handle it** per `review.md`'s "Handling the findings".
3. **No decisions:** apply its fixes and "already decided" notes, then read `build.md` in this skill's folder and follow it from step 2.
4. **Decisions:** put them in one picker whose **last** question is *"Then:"* with **Build now (Recommended)** and **Hold**. At most three decisions per picker; more go in an earlier picker, and "Then:" is always the last question of the last one.
   - **Build now:** integrate the answers, do the quick check that the flagged items are resolved, and build (`build.md` from step 2). No second sign-off: the answers plus Build now are the sign-off on the revised text.
   - **An answer that brings in something new** (free text beyond the offered options, a "chat about this" that reshapes the design, a new requirement): per `review.md`'s "Settling its decisions", the revised text gets a fresh review before anything is built. Say so in one line, start it, and handle it like the first one. Build now then means "build once it's back with nothing to decide"; its decisions come in a new picker, again ending with "Then:".
   - **Hold:** integrate the answers and wait. When the user says build, follow `build.md` from step 2.

## 8. After "Sign off, build later"

Handle the review as in step 7: wait for it (if it isn't back, say so in one line and end the turn), apply its fixes and notes, and put any decisions to the user in a picker of up to four, with no "Then:" question; then integrate the answers and do the quick check, or run a fresh review when an answer brought in something new, as in step 7. Then commit the spec as `build.md` step 2 says, and tell the user that saying "build it" in this window starts the build, or `/feature-flow resume <worktree-path>` from a new session in the main checkout. On "build it", follow `build.md` from step 3.

## No closing offer before the review is handled

Until a review has returned on the text the user signed and its decisions are settled, the spec may still change. So before that point there's no offer to build, no "build it" hint, and never a build start.

## Mistakes to avoid

- **Drafting before the user has picked an approach.** Step 3 forks the conversation early; a draft written first is wasted and biases the choice.
- **Manufacturing options.** If there's only one reasonable approach, say so.
- **Editing code "to verify".** Read-only means read-only; make it an open question.
- **Asking for sign-off with a question still open.** The spec is ready only when Open questions is empty or gone.
- **Inferring sign-off.** Only the user picking a sign-off option, or saying so in as many words, counts.
