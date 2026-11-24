#!/usr/bin/env python3
"""feature-flow state: one JSON file per feature, and an overview across features.

Each feature session keeps `feature-flow-state.json` in its worktree's git folder
(`<repo>/.git/worktrees/<name>/`, next to `feature-flow-progress.log`), so it is never
tracked and disappears with the worktree at ship or drop.

  state.py set --step NAME [--n N --of TOTAL] [--phase PHASE] [--round R] [--doing TEXT]
               [--title TITLE] [--spec PATH] [--waiting TEXT] [--worktree PATH]
      Run inside the feature's worktree, or name it with --worktree (after ExitWorktree).
      Writes the state with a UTC timestamp and this window's session id
      (CLAUDE_CODE_SESSION_ID), and composes the display step from the feature's ten
      overall steps: "4/10 Building", "9/10 Feedback round 2", "10/10 Ship". Design,
      feedback, ship and drop fill in their own number; build and wrapup pass --n.
      --waiting says what the user needs to do; a `set` without it means "working".

  state.py status [--json] [--roots DIR:DIR]
      Lists every feature in flight under the roots (default: ~/work and ~/private,
      or FEATURE_FLOW_ROOTS, colon-separated). Reads only.

Timestamps are RFC 3339 in UTC, e.g. 2026-11-24T13:02:11Z.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import tempfile

STATE_NAME = "feature-flow-state.json"
LOG_NAME = "feature-flow-progress.log"
PHASES = ("design", "build", "feedback", "wrapup", "ship", "drop")
PHASE_LABEL = {"design": "Design", "build": "Build", "feedback": "Feedback",
               "wrapup": "Wrap-up", "ship": "Ship", "drop": "Drop"}
QUIET_AFTER_S = 60 * 60  # working, but no update for an hour: the session may be gone


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text):
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )


def find_checkout(start):
    """Nearest directory at or above `start` holding a `.git` entry, or None."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def linked_git_dir(worktree):
    """The git dir of a linked worktree, read from its `.git` file (no git subprocess,
    so it works from anywhere, including the main checkout after ExitWorktree)."""
    dot_git = os.path.join(worktree, ".git")
    if not os.path.isfile(dot_git):
        return None  # a .git directory: the main checkout, not a feature worktree
    with open(dot_git) as f:
        for line in f:
            if line.startswith("gitdir:"):
                p = line[len("gitdir:"):].strip()
                return os.path.normpath(p if os.path.isabs(p) else os.path.join(worktree, p))
    return None


def read_branch(git_dir):
    try:
        with open(os.path.join(git_dir, "HEAD")) as f:
            head = f.read().strip()
        return head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else None
    except OSError:
        return None


def phase_label(phase, rnd):
    label = PHASE_LABEL.get(phase, phase.capitalize())
    return "%s %d" % (label, rnd) if rnd else label


# The feature's ten overall steps, the only numbers anyone sees:
#   1 Design · 2 Spec committed · 3 Copy set up · 4 Building · 5 Validating ·
#   6 Review and commit · 7 Checks · 8 Ready to test · 9 Feedback · 10 Ship (or Drop)
# Build and wrap-up name their step (--n required); the other phases are one step each.
OVERALL_STEPS = 10
PHASE_STEP = {"design": 1, "feedback": 9, "ship": 10, "drop": 10}


def overall_name(phase, name, rnd):
    if phase == "feedback":
        return "Feedback round %d" % rnd if (rnd and rnd > 1) else "Feedback"
    if phase in ("build", "wrapup"):
        return name
    return PHASE_LABEL.get(phase, phase.capitalize())


def display_step(phase, name, n, total, rnd):
    """The step as people read it: "4/10 Building", "9/10 Feedback round 2", "10/10 Ship".
    Finer detail (a design or ship sub-step) belongs in `doing`."""
    label = overall_name(phase, name, rnd)
    return ("%d/%d %s" % (n, total, label)) if (n and total) else label


def cmd_set(a):
    worktree = os.path.abspath(a.worktree) if a.worktree else find_checkout(os.getcwd())
    git_dir = linked_git_dir(worktree) if worktree else None
    if not git_dir:
        sys.exit("state.py set: not in a feature worktree; run it inside one, or pass --worktree")
    common = os.path.dirname(os.path.dirname(git_dir))  # <repo>/.git/worktrees/<name> -> <repo>/.git
    branch = read_branch(git_dir)

    path = os.path.join(git_dir, STATE_NAME)
    state = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}

    if a.n is None:
        a.n = PHASE_STEP.get(a.phase or state.get("phase"))
    if a.of is None:
        a.of = OVERALL_STEPS
    if (a.phase or state.get("phase")) in ("build", "wrapup") and not a.n:
        sys.exit("state.py set: build and wrapup steps need --n (their overall step number)")
    ts = iso(now_utc())
    was_waiting, waiting_since = state.get("waiting_for_user"), state.get("waiting_since")
    title = a.title or state.get("title")
    if not title:
        sys.exit("state.py set: --title is required the first time")
    phase = a.phase or state.get("phase") or "design"
    if phase not in PHASES:
        sys.exit("state.py set: --phase must be one of " + ", ".join(PHASES))

    repo = os.path.dirname(common) if os.path.basename(common) == ".git" else common
    state.update(
        {
            "version": 2,
            "title": title,
            "phase": phase,
            "step": display_step(phase, a.step, a.n, a.of, a.round),
            "step_name": a.step,
            "phase_label": phase_label(phase, a.round),
            "doing": a.doing or None,
            "step_number": a.n,
            "step_total": a.of,
            "round": a.round,
            "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID") or state.get("session_id"),
            "waiting_for_user": bool(a.waiting),
            "waiting_for": a.waiting or None,
            "updated_at": ts,
            "started_at": state.get("started_at") or ts,
            "repo": repo,
            "worktree": worktree,
            "branch": branch,
            "spec": a.spec or state.get("spec"),
            "progress_log": os.path.join(git_dir, LOG_NAME),
        }
    )
    if a.waiting:
        state["waiting_since"] = waiting_since if (was_waiting and waiting_since) else ts
    else:
        state["waiting_since"] = None

    fd, tmp = tempfile.mkstemp(dir=git_dir, prefix=".ff-state-")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def find_states(roots):
    seen = set()
    for root in roots:
        root = os.path.expanduser(root)
        for pattern in (
            os.path.join(root, ".git", "worktrees", "*", STATE_NAME),
            os.path.join(root, "*", ".git", "worktrees", "*", STATE_NAME),
        ):
            for path in glob.glob(pattern):
                real = os.path.realpath(path)
                if real not in seen:
                    seen.add(real)
                    yield path


def load_states(roots):
    out = []
    now = now_utc()
    for path in find_states(roots):
        try:
            with open(path) as f:
                s = json.load(f)
            updated = parse_iso(s["updated_at"])
        except (OSError, ValueError, KeyError):
            continue
        if s.get("worktree") and not os.path.isdir(s["worktree"]):
            continue  # worktree removed by hand; nothing to show
        s["state_file"] = path
        s["age_seconds"] = int((now - updated).total_seconds())
        since = s.get("waiting_since") if s.get("waiting_for_user") else None
        try:
            s["waiting_seconds"] = int((now - parse_iso(since)).total_seconds()) if since else None
        except ValueError:
            s["waiting_seconds"] = None
        s["quiet"] = (not s.get("waiting_for_user")) and s["age_seconds"] > QUIET_AFTER_S
        out.append(s)
    # Waiting for the user first (longest waiting first), then working (most recent first).
    out.sort(key=lambda s: (0, -(s["waiting_seconds"] or s["age_seconds"])) if s.get("waiting_for_user")
             else (1, s["age_seconds"]))
    return out


def age_text(seconds):
    if seconds < 60:
        return "now"
    minutes = seconds // 60
    if minutes < 60:
        return "%d min" % minutes
    hours = minutes // 60
    if hours < 48:
        return "%d h %02d" % (hours, minutes % 60)
    return "%d days" % (hours // 24)


def clip(text, width):
    text = text or ""
    return text if len(text) <= width else text[: width - 1] + "…"


def cmd_status(a):
    roots = (a.roots or os.environ.get("FEATURE_FLOW_ROOTS") or "~/work:~/private").split(":")
    states = load_states(roots)
    if a.json:
        json.dump(states, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    if not states:
        print("No features in flight under " + ", ".join(roots) + ".")
        return
    rows = []
    for s in states:
        if s.get("waiting_for_user"):
            mark, step = "!", "%s: your turn (%s)" % (s.get("step"), s.get("waiting_for"))
        elif s["quiet"]:
            mark, step = "?", "%s: quiet; session gone? /feature-flow resume %s" % (s.get("step"), s.get("worktree"))
        else:
            mark, step = "▶", s.get("step")
        since = s["waiting_seconds"] if s.get("waiting_seconds") is not None else s["age_seconds"]
        rows.append((mark, clip(s.get("title"), 34), clip(os.path.basename(s.get("repo") or ""), 16),
                     step, age_text(since)))
    print("   %-34s  %-16s  %-7s  %s" % ("Feature", "Repo", "Since", "Step"))
    for mark, title, repo, step, since in rows:
        print("%s  %-34s  %-16s  %-7s  %s" % (mark, title, repo, since, step))


def main():
    p = argparse.ArgumentParser(description="feature-flow state and overview")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("set")
    s.add_argument("--step", required=True, help="the step's name, e.g. 'Review and commit'")
    s.add_argument("--n", type=int, help="the overall step number (1-10); build and wrapup only")
    s.add_argument("--of", type=int, help="overall steps (default 10)")
    s.add_argument("--round", type=int, help="feedback round number")
    s.add_argument("--worktree", help="the feature's worktree, when not running inside it")
    s.add_argument("--doing", help="what the step is doing, in a few words (the checklist line's detail)")
    s.add_argument("--phase", choices=PHASES)
    s.add_argument("--title")
    s.add_argument("--spec")
    s.add_argument("--waiting", help="what the user needs to do; omit when working")
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true")
    st.add_argument("--roots")
    a = p.parse_args()
    if a.cmd == "set":
        cmd_set(a)
    elif a.cmd == "status":
        cmd_status(a)
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
