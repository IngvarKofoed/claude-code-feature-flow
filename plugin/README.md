# feature-flow status line

The plugin half of [feature-flow](../README.md). It shows the feature this window is working on as its own status line under the prompt, for example:

```
⚠ feature-flow: ⎇ chip-cut · 4/10 Building · builder/API: endpoint and tests done · 42m
```

That is the worktree (or, before the draft, the design's topic), the step among the feature's ten overall steps, what the step is doing (the progress log's newest line, or "your turn: …" when the session needs you), and the time since the feature started.

Install it once (Claude Code 2.1.275 or later):

```
/plugin install feature-flow --marketplace IngvarKofoed/claude-code-feature-flow
```

It only reads the state file the feature-flow skill writes (`feature-flow-state.json`, or the pending one before a worktree exists) and never writes anything. It redraws right after each step update and every 30 seconds. Windows with no feature show nothing. It is independent of the `statusLine` setting, so it works next to any status line you already have.
