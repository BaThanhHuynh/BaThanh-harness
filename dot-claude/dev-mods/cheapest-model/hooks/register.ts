import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { RouterMode, ModelTier } from '../types'

// Cheapest first. Price per 1M tokens in/out: haiku 0.10/0.50, sonnet 2/10, opus 4/20, fable 8/40.
const TIERS: readonly ModelTier[] = ['haiku', 'sonnet', 'opus', 'fable']
const MODES: readonly RouterMode[] = ['auto', 'off', ...TIERS]

const mode = atom<'cheapest-model', 'mode'>({ plugin: 'cheapest-model', key: 'mode' } as const, 'auto')
const last = atom<'cheapest-model', 'last'>({ plugin: 'cheapest-model', key: 'last' } as const, null)

const RUBRIC = `You route requests for a coding agent to the cheapest Claude model that can finish the job well.
Reply with exactly one word: haiku, sonnet, opus or fable.
haiku (quick): questions, explanations, lookups, reading or searching code, running a command, small mechanical edits (rename, format, typo, config value).
sonnet (medium): ordinary coding: a feature, a bug fix, a refactor, tests, scoped multi-file work with a clear plan.
opus (hard): architecture or design, subtle or concurrency debugging, security review, tricky algorithms, large multi-file changes, ambiguous requirements.
fable (hardest): long autonomous projects spanning many systems, novel research-grade problems, work a previous opus attempt got wrong, or work where a subtle mistake would be very costly.
A short reply such as "ok", "do it" or "continue" inherits the difficulty of the work in the recent conversation.
Pick the cheaper model when a mistake would be obvious and cheap to redo; the stronger one when it would be silent or costly.`

// Long contexts: stepping down (fable -> opus, opus -> sonnet) re-writes the whole prompt
// cache at the new model's full input price, more than cache reads on the current one.
// Haiku is cheaper even uncached, so only a step down to haiku goes through.
const STICKY_MESSAGES = 30
const ESCALATE_TOOL = 'mcp__cheapest-model__escalate'
const ERRORS_TO_ESCALATE = 2

const rank = (model: string | undefined) => {
  const i = TIERS.findIndex(t => model?.includes(t))
  return i === -1 ? Infinity : i
}

const pick = async ($: EngineInterface, text: string): Promise<ModelTier | undefined> => {
  const r = await $.model.complete({
    model: 'haiku',
    system: RUBRIC,
    prompt: text.slice(-6000),
    maxTokens: 512,
    effort: 'low',
    timeoutMs: 10000,
  })
  if (!r.isAnswered) return undefined
  const word = r.text.toLowerCase().match(/haiku|sonnet|opus|fable/)?.[0]
  return word as ModelTier | undefined
}

async function show($: EngineInterface, tier: ModelTier, why: string) {
  const before = await read($, last)
  await update($, last, () => tier)
  $.ui.status(`💸 ${tier} (${why})`)
  if (before !== null && before !== tier) $.ui.toast(`Model → ${tier} (${why})`)
}

export const register: Register = on => {
  let pending: Promise<ModelTier | undefined> | undefined
  let turnTier: ModelTier | undefined
  let errors = 0

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'cheapest',
      description: 'Cheapest-model router: /cheapest [auto|off|haiku|sonnet|opus|fable]',
    })
    await $.tool.register({
      name: 'escalate',
      description:
        'Switch the rest of this turn to a stronger Claude model. Call it as soon as the work turns out ' +
        'harder than you can do well on the current model: repeated failed attempts, a subtle bug, ' +
        'design or security decisions, or a plan spanning many files. Do not call it for routine work. ' +
        'Requests after this call, within the same turn, run on the new model.',
      inputSchema: {
        type: 'object',
        properties: {
          to: { type: 'string', enum: ['sonnet', 'opus', 'fable'], description: 'Target model; default one step up.' },
          reason: { type: 'string', description: 'Why the current model is not enough, in one sentence.' },
        },
        required: ['reason'],
      },
      isDeferred: false,
    })
    return next(e)
  })

  on('command.run', { command: 'cheapest' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase() as RouterMode
    if (MODES.includes(arg)) await update($, mode, () => arg)
    const now = await read($, mode)
    if (now === 'off') $.ui.status(undefined)
    return { text: `cheapest-model: ${now}, last turn on ${(await read($, last)) ?? 'n/a'}` }
  })

  // Classify each new user prompt, with the recent conversation for context.
  on('prompt.submit', async ($, e, next) => {
    if (e.command || e.isMeta || e.turnId) return next(e)
    const m = await read($, mode)
    if (m === 'off') {
      pending = undefined
      return next(e)
    }
    if (m !== 'auto') {
      pending = Promise.resolve(m)
      return next(e)
    }
    const recent = (await $.session.messages())
      .slice(-4)
      .map(row => `${row.role}: ${row.text.slice(0, 1200)}`)
      .join('\n\n')
    pending = pick($, `Recent conversation:\n${recent}\n\nNew request:\n${e.text}`).catch(
      () => undefined,
    )
    return next(e)
  })

  // Main loop only: send each model request of the turn on the chosen tier.
  on('turn.step', async function* ($, e, next) {
    if (e.agentId !== undefined) return yield* next(e)

    if (e.index === 0) {
      errors = 0
      turnTier = await pending
      pending = undefined
      if (turnTier === undefined) return yield* next(e)

      const prev = await read($, last)
      const isPinned = (await read($, mode)) !== 'auto'
      const isLong = e.messageCount > STICKY_MESSAGES
      if (!isPinned && isLong && turnTier !== 'haiku' && prev !== null && rank(turnTier) < rank(prev)) {
        turnTier = prev
        await show($, turnTier, 'kept: cache')
      } else {
        await show($, turnTier, isPinned ? 'pinned' : 'auto')
      }
    }

    return turnTier === undefined ? yield* next(e) : yield* next({ ...e, model: turnTier })
  })

  // A cheap model that keeps failing is not "able to do the job": escalate one tier.
  // Tool errors are a weak signal (often the environment, not the model): they stop at opus.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId !== undefined || turnTier === undefined || ran.isError !== true) return ran
    errors += 1
    const up = TIERS[TIERS.indexOf(turnTier) + 1]
    if (errors >= ERRORS_TO_ESCALATE && up !== undefined && up !== 'fable' && (await read($, mode)) === 'auto') {
      errors = 0
      turnTier = up
      await show($, up, 'escalated')
    }
    return ran
  })

  // The working agent judges its own task: it may move itself up, never down.
  on('tool.call', { tool: ESCALATE_TOOL }, async ($, e) => {
    const say = (text: string) => ({ result: text })
    if (e.agentId !== undefined) return say('Subagents keep the model they were spawned with.')
    if ((await read($, mode)) !== 'auto') return say('The user pinned the model with /cheapest; not switching.')
    const current = turnTier ?? (await $.session.model())
    const asked = TIERS.find(t => t === (e as { to?: unknown }).to)
    const target = asked ?? TIERS[rank(current) + 1]
    if (target === undefined || rank(target) <= rank(current)) return say(`Already on ${current}; not switching.`)
    turnTier = target
    await show($, target, 'self-escalated')
    return say(`Switched to ${target} for the rest of this turn.`)
  })

  // Subagents: the cheaper of the caller's explicit choice and the classifier's.
  on('agent.spawn', async ($, e, next) => {
    const m = await read($, mode)
    if (m === 'off' || e.fork || e.isTeammate || e.workflow) return next(e)
    const tier = m === 'auto' ? await pick($, `Agent type: ${e.subagentType}\n\n${e.prompt}`) : m
    if (tier === undefined) return next(e)
    const model = rank(e.model) <= rank(tier) ? e.model : tier
    return next({ ...e, model })
  })
}
