#!/usr/bin/env python3
"""feature-flow state: one JSON file per feature, and an overview across features.

Each feature session keeps `feature-flow-state.json` in its worktree's git folder
(`<repo>/.git/worktrees/<name>/`, next to `feature-flow-progress.log`), so it is never
tracked and disappears with the worktree at ship or drop.

  state.py set --step STEP [--phase PHASE] [--title TITLE] [--spec PATH] [--waiting TEXT]
      Run inside the feature's worktree. Writes the state with a UTC timestamp.
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
import subprocess
import sys
import tempfile

STATE_NAME = "feature-flow-state.json"
LOG_NAME = "feature-flow-progress.log"
PHASES = ("design", "build", "feedback", "ship", "drop")
QUIET_AFTER_S = 60 * 60  # working, but no update for an hour: the session may be gone


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def iso(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text):
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )


def git(*args):
    return subprocess.check_output(("git",) + args, text=True).strip()


def cmd_set(a):
    try:
        git_dir = git("rev-parse", "--absolute-git-dir")
        common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
        worktree = git("rev-parse", "--show-toplevel")
        branch = git("branch", "--show-current")
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("state.py set: not inside a git worktree")
    if os.path.realpath(git_dir) == os.path.realpath(common):
        sys.exit("state.py set: this is the main checkout; run it inside the feature's worktree")

    path = os.path.join(git_dir, STATE_NAME)
    state = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}

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
            "version": 1,
            "title": title,
            "phase": phase,
            "step": a.step,
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
    s.add_argument("--step", required=True)
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
