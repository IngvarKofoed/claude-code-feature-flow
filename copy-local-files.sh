#!/bin/sh
# Copy local, git-ignored files from a main checkout into one of its worktrees.
#
# Usage: copy-local-files.sh <main-checkout> <worktree> <repo-relative-path>...
#
# Each path is copied from <main-checkout>/<path> to <worktree>/<path>,
# creating parent folders. Files that already exist in the worktree are left
# alone (a restarted builder keeps its copy). Directories are copied whole.
# Nothing in the main checkout is changed.
#
# It refuses paths that are tracked by git (those come with the branch),
# paths that escape the checkout, and the worktrees folder itself.

set -eu

if [ "$#" -lt 3 ]; then
  echo "usage: copy-local-files.sh <main-checkout> <worktree> <path>..." >&2
  exit 2
fi

main=$(cd "$1" && pwd -P)
wt=$(cd "$2" && pwd -P)
shift 2

case "$wt" in
  "$main"/*) ;;
  *) echo "refusing: $wt is not inside $main" >&2; exit 2 ;;
esac

for p in "$@"; do
  case "$p" in
    /*|*..*|.claude/worktrees*|.git|.git/*)
      echo "skip (not allowed): $p" >&2; continue ;;
  esac
  src="$main/$p"
  dst="$wt/$p"
  if [ ! -e "$src" ]; then
    echo "skip (missing in main checkout): $p" >&2; continue
  fi
  # Tracked status is the same in every worktree of the repo; ask the
  # worktree's own git, so nothing here runs git against the main checkout.
  if git -C "$wt" ls-files --error-unmatch -- "$p" >/dev/null 2>&1; then
    echo "skip (tracked by git): $p" >&2; continue
  fi
  if [ -e "$dst" ]; then
    echo "keep (already in worktree): $p"; continue
  fi
  mkdir -p "$(dirname "$dst")"
  cp -Rp "$src" "$dst"
  echo "copied: $p"
done
