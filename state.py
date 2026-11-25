#!/usr/bin/env python3
"""feature-flow state: one JSON file per feature, and an overview across features.

Each feature session keeps `feature-flow-state.json` in its worktree's git folder
(`<repo>/.git/worktrees/<name>/`, next to `feature-flow-progress.log`), so it is never
tracked and disappears with the worktree at ship or drop.

  state.py set --step NAME [--n N --of TOTAL] [--phase PHASE] [--round R] [--doing TEXT]
               [--title TITLE] [--spec PATH] [--waiting TEXT] [--worktree PATH]
      Run inside the feature's worktree, or name it with --worktree (after ExitWorktree),
      or pass --pending in the main checkout before the worktree exists (design steps
      1-3); the first `set` inside the worktree then adopts it, start time and all.

  state.py clear
      Forget this window's pending design (abandoned before it got a worktree).

  state.py times [--worktree PATH] [--json]
      Time spent per overall step, with the part spent waiting for the user, from the
      history every `set` appends. For the final ship or drop message.
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
PENDING_DIR = "feature-flow-pending"  # <repo>/.git/feature-flow-pending/<session id>.json
PENDING_HIDE_AFTER_S = 24 * 60 * 60
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


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".ff-state-")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def pending_path(common, sid):
    """Before the worktree exists (design steps 1-3, in the main checkout) the state lives
    in the repo's own git dir, under this window's session id."""
    return os.path.join(common, PENDING_DIR, "%s.json" % sid)


def cmd_set(a):
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    pending = None
    if a.pending:
        root = find_checkout(os.getcwd())
        common = os.path.join(root, ".git") if root else None
        if not common or not os.path.isdir(common):
            sys.exit("state.py set --pending: run it in the repo's main checkout")
        if not sid:
            sys.exit("state.py set --pending: needs CLAUDE_CODE_SESSION_ID to key the file")
        worktree, git_dir, branch = None, None, read_branch(common)
        path = pending_path(common, sid)
        state = load_json(path)
    else:
        worktree = os.path.abspath(a.worktree) if a.worktree else find_checkout(os.getcwd())
        git_dir = linked_git_dir(worktree) if worktree else None
        if not git_dir:
            sys.exit("state.py set: not in a feature worktree; run it inside one, pass --worktree, "
                     "or pass --pending before the worktree exists")
        common = os.path.dirname(os.path.dirname(git_dir))  # <repo>/.git/worktrees/<name> -> <repo>/.git
        branch = read_branch(git_dir)
        path = os.path.join(git_dir, STATE_NAME)
        state = load_json(path)
        # The design's early steps were kept under this session before the worktree
        # existed: adopt them (title, start time) and retire that file.
        if sid and not state:
            pending = pending_path(common, sid)
            state = load_json(pending)
            for k in ("pending", "state_file"):
                state.pop(k, None)

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
            "pending": bool(a.pending),
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
            "progress_log": os.path.join(git_dir, LOG_NAME) if git_dir else None,
        }
    )
    if a.waiting:
        state["waiting_since"] = waiting_since if (was_waiting and waiting_since) else ts
    else:
        state["waiting_since"] = None

    # One history entry per `set`: what `times` turns into time per step.
    history = state.get("history") if isinstance(state.get("history"), list) else []
    history.append({"at": ts, "n": a.n, "phase": phase, "round": a.round,
                    "waiting": bool(a.waiting)})
    state["history"] = history[-HISTORY_MAX:]
    write_json(path, state)
    if pending and os.path.exists(pending):
        os.remove(pending)


STEP_NAMES = {1: "Design", 2: "Spec committed", 3: "Copy set up", 4: "Building",
              5: "Validating", 6: "Review and commit", 7: "Checks", 8: "Ready to test",
              9: "Feedback", 10: "Ship"}
HISTORY_MAX = 2000


def short_time(seconds):
    m = int(seconds // 60)
    if m < 1:
        return "<1m"
    if m < 60:
        return "%dm" % m
    return "%dh %02dm" % (m // 60, m % 60)


def step_times(state, now):
    """Per overall step: total seconds, seconds waiting for the user, how many separate
    runs it had (steps 5-8 run again after feedback), and feedback rounds."""
    hist = sorted((h for h in state.get("history") or [] if h.get("at") and h.get("n")),
                  key=lambda h: h["at"])
    steps = {}
    prev_n, prev_round, rounds = None, None, 0
    for i, h in enumerate(hist):
        start = parse_iso(h["at"])
        end = parse_iso(hist[i + 1]["at"]) if i + 1 < len(hist) else now
        secs = max(0, (end - start).total_seconds())
        st = steps.setdefault(h["n"], {"total": 0, "waiting": 0, "runs": 0, "phase": h.get("phase")})
        st["total"] += secs
        if h.get("waiting"):
            st["waiting"] += secs
        if h["n"] != prev_n:
            st["runs"] += 1
        if h["n"] == 9 and (prev_n != 9 or h.get("round") != prev_round):
            rounds += 1
        prev_n, prev_round = h["n"], h.get("round")
    return steps, rounds


def cmd_times(a):
    """The time spent per overall step, for the ship or drop message."""
    worktree = os.path.abspath(a.worktree) if a.worktree else find_checkout(os.getcwd())
    git_dir = linked_git_dir(worktree) if worktree else None
    state = load_json(os.path.join(git_dir, STATE_NAME)) if git_dir else {}
    if not state.get("history"):
        sys.exit("state.py times: no step history (the feature started before it was recorded)")
    steps, rounds = step_times(state, now_utc())
    if a.json:
        json.dump({"steps": steps, "feedback_rounds": rounds}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    rows, total, waiting = [], 0, 0
    for n in range(1, OVERALL_STEPS + 1):
        name = STEP_NAMES[n]
        st = steps.get(n)
        if n == 10 and st and st.get("phase") == "drop":
            name = "Drop"
        if n == 9 and rounds:
            name = "Feedback (%d round%s)" % (rounds, "" if rounds == 1 else "s")
        if not st:
            rows.append((n, name, "skipped" if n == 9 else "-", "", ""))
            continue
        total += st["total"]
        waiting += st["waiting"]
        rows.append((n, name, short_time(st["total"]), "×%d" % st["runs"] if st["runs"] > 1 else "",
                     short_time(st["waiting"]) if st["waiting"] >= 60 else ""))
    print("Time per step                    total         waiting for you")
    for n, name, t, runs, w in rows:
        print("%2d %-26s %8s  %-4s %10s" % (n, name, t, runs, w))
    print("   %-26s %8s  %-4s %10s" % ("Total", short_time(total), "", short_time(waiting)))


def cmd_clear(a):
    """Forget this window's pending design (abandoned before it got a worktree)."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    root = find_checkout(os.getcwd())
    if not (sid and root and os.path.isdir(os.path.join(root, ".git"))):
        sys.exit("state.py clear: run it in the repo's main checkout, in the session that started the design")
    p = pending_path(os.path.join(root, ".git"), sid)
    if os.path.exists(p):
        os.remove(p)


def find_states(roots):
    seen = set()
    for root in roots:
        root = os.path.expanduser(root)
        for pattern in (
            os.path.join(root, ".git", "worktrees", "*", STATE_NAME),
            os.path.join(root, "*", ".git", "worktrees", "*", STATE_NAME),
            os.path.join(root, ".git", PENDING_DIR, "*.json"),
            os.path.join(root, "*", ".git", PENDING_DIR, "*.json"),
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
        if s.get("pending") and s["age_seconds"] > PENDING_HIDE_AFTER_S:
            continue  # a design abandoned before its worktree; not worth listing
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
        elif s["quiet"] and s.get("pending"):
            mark, step = "?", "%s: quiet; session gone? (no worktree yet)" % s.get("step")
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
    s.add_argument("--pending", action="store_true",
                   help="before the worktree exists: keep the state under this session in the main checkout")
    s.add_argument("--doing", help="what the step is doing, in a few words (the checklist line's detail)")
    s.add_argument("--phase", choices=PHASES)
    s.add_argument("--title")
    s.add_argument("--spec")
    s.add_argument("--waiting", help="what the user needs to do; omit when working")
    sub.add_parser("clear", help="forget this window's pending design")
    t = sub.add_parser("times", help="time spent per overall step (for the ship or drop message)")
    t.add_argument("--worktree", help="the feature's worktree, when not running inside it")
    t.add_argument("--json", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true")
    st.add_argument("--roots")
    a = p.parse_args()
    if a.cmd == "set":
        cmd_set(a)
    elif a.cmd == "status":
        cmd_status(a)
    elif a.cmd == "clear":
        cmd_clear(a)
    elif a.cmd == "times":
        cmd_times(a)
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
