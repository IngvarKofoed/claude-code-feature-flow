import type { EngineInterface, Register, Timer } from 'claude-code'

// The feature-flow plugin: shows this window's /feature-flow feature on its own status line, e.g.
//   ⎇ chip-cut · 4/10 Building · builder/API: endpoint done · 42m
// It reads the state file the feature-flow skill writes (state.py) and never writes
// anything. Where it looks, for the session's directory:
//   - in a feature worktree: <git dir>/feature-flow-state.json (the `.git` FILE's gitdir);
//   - otherwise this session's design before it has a worktree:
//     <repo>/.git/feature-flow-pending/<session id>.json;
//   - otherwise a feature this session is finishing from the main checkout (ship, drop):
//     <repo>/.git/worktrees/*/feature-flow-state.json whose session_id is this session's.
// It redraws when a Bash call runs state.py, and every 30 s so the time spent ticks.

const STATE = 'feature-flow-state.json'
const PENDING = 'feature-flow-pending'
const LOG = 'feature-flow-progress.log'
const TICK_MS = 30_000

type FeatureState = {
  step?: string
  doing?: string | null
  waiting_for_user?: boolean
  waiting_for?: string | null
  started_at?: string
  updated_at?: string
  worktree?: string | null
  title?: string
  branch?: string | null
  session_id?: string | null
  progress_log?: string | null
}

type Api = EngineInterface

const dirname = (p: string) => p.slice(0, Math.max(1, p.lastIndexOf('/')))
const basename = (p: string) => p.slice(p.lastIndexOf('/') + 1)
const join = (...parts: string[]) => parts.join('/').replace(/\/+/g, '/')

async function readJson($: Api, path: string): Promise<FeatureState | null> {
  try {
    if (!(await $.fs.exists(path))) return null
    const st = JSON.parse(await $.fs.read(path)) as FeatureState
    return st && typeof st.step === 'string' && st.step ? st : null
  } catch {
    return null
  }
}

// The checkout holding `dir`: its root, the git dir its HEAD lives in, and the repo's
// common git dir (where worktrees/ and feature-flow-pending/ live).
async function findGit($: Api, dir: string) {
  let d = dir
  for (;;) {
    const dotGit = join(d, '.git')
    if (await $.fs.exists(dotGit)) {
      const kind = (await $.fs.stat(dotGit)).kind
      if (kind === 'dir') return { root: d, gitDir: dotGit, common: dotGit, linked: false }
      const m = /^gitdir:\s*(.+)$/m.exec(await $.fs.read(dotGit))
      if (!m) return null
      const p = (m[1] ?? '').trim()
      const gitDir = p.startsWith('/') ? p : join(d, p)
      return { root: d, gitDir, common: dirname(dirname(gitDir)), linked: true }
    }
    const up = dirname(d)
    if (up === d) return null
    d = up
  }
}

async function findFeature($: Api, dir: string, sid: string) {
  const g = await findGit($, dir)
  if (!g) return null
  if (g.linked) {
    const st = await readJson($, join(g.gitDir, STATE))
    if (st) return { st, name: basename(g.root), gitDir: g.gitDir }
  }
  if (sid && !/[\\/]/.test(sid)) {
    const pending = await readJson($, join(g.common, PENDING, `${sid}.json`))
    // No worktree yet: the session works on the main checkout's branch, so name that
    // (the design's title can be long and isn't a branch; it's in /feature-flow status).
    if (pending) return { st: pending, name: pending.branch || basename(g.root), gitDir: null }
    try {
      for (const entry of await $.fs.list(join(g.common, 'worktrees'))) {
        const wtGit = join(g.common, 'worktrees', entry.name)
        const st = await readJson($, join(wtGit, STATE))
        if (st && st.session_id === sid) {
          return { st, name: st.worktree ? basename(st.worktree) : entry.name, gitDir: wtGit }
        }
      }
    } catch {
      /* no worktrees */
    }
  }
  return null
}

// The progress log's newest line, without its timestamp, if written at or after `since`.
async function lastLogLine($: Api, file: string, since: string | undefined) {
  try {
    if (!(await $.fs.exists(file))) return null
    const { size } = await $.fs.stat(file)
    const offset = Math.max(0, size - 2048)
    const text: string = await $.fs.read(file, { offset, length: size - offset })
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
    const m = /^(\S+)\s+(.+)$/.exec(lines[lines.length - 1] ?? '')
    if (!m) return null
    const at = Date.parse(m[1] ?? '')
    const from = Date.parse(since ?? '')
    return !isNaN(at) && !isNaN(from) && at >= from ? (m[2] ?? null) : null
  } catch {
    return null
  }
}

function spent(iso: string | undefined) {
  const t = Date.parse(iso ?? '')
  if (isNaN(t)) return null
  const min = Math.floor((Date.now() - t) / 60000)
  if (min < 0) return null
  if (min < 1) return '<1m'
  if (min < 60) return `${min}m`
  const h = Math.floor(min / 60)
  if (h < 48) return `${h}h ${String(min % 60).padStart(2, '0')}m`
  return `${Math.floor(h / 24)}d ${h % 24}h`
}

const clip = (s: string, n: number) => (s.length <= n ? s : s.slice(0, n - 1) + '…')

async function refresh($: Api) {
  try {
    const [dir, sid] = await Promise.all([$.session.cwd(), $.session.id()])
    const found = await findFeature($, dir, sid)
    if (!found) return $.ui.status(undefined)
    const { st, name, gitDir } = found
    let doing: string | null = null
    if (st.waiting_for_user) doing = 'your turn' + (st.waiting_for ? `: ${st.waiting_for}` : '')
    else {
      const log = st.progress_log || (gitDir ? join(gitDir, LOG) : null)
      doing = (log && (await lastLogLine($, log, st.updated_at))) || st.doing || null
    }
    const parts = [`⎇ ${name}`, st.step as string]
    if (doing) parts.push(clip(doing, 70))
    const time = spent(st.started_at)
    if (time) parts.push(time)
    $.ui.status(parts.join(' · '))
  } catch {
    $.ui.status(undefined)
  }
}

let tick: Timer | null = null

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    tick?.cancel()
    tick = $.clock.every(TICK_MS, () => void refresh($))
    void refresh($)
    return result
  })

  // feature-flow records every step with a Bash call to state.py: redraw right after.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const result = await next(e)
    if (e.command.includes('state.py')) void refresh($)
    return result
  })
}
