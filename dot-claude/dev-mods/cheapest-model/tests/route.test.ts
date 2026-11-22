import { expect, test } from 'claude-code/testing'

const SPAWN = {
  tool_use_id: 't1',
  prompt: 'Find where the config file is loaded',
  description: 'search',
  subagentType: 'Explore',
  provider: { plugin: 'engine', tier: 'core' },
  parentModel: 'claude-opus-5-5',
  background: false,
  fork: false,
} as const

const classifierSays = (word: string) => () => ({
  value: { isAnswered: true, text: word, usage: { input_tokens: 1, output_tokens: 1, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } } as const,
})

test('a subagent goes to the classifier tier when that is cheaper', async ($, on) => {
  on('model.complete', classifierSays('haiku'))
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'inherited' }))
  const r = await $.agent.spawn({ ...SPAWN, model: 'opus' })
  expect(r.model).toBe('haiku')
})

test('an explicit cheaper model is kept', async ($, on) => {
  on('model.complete', classifierSays('opus'))
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'inherited' }))
  const r = await $.agent.spawn({ ...SPAWN, model: 'haiku' })
  expect(r.model).toBe('haiku')
})

test('the hardest work goes to fable', async ($, on) => {
  on('model.complete', classifierSays('fable'))
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'inherited' }))
  const r = await $.agent.spawn({ ...SPAWN })
  expect(r.model).toBe('fable')
})

test('the working agent can escalate itself, never down', async ($, on) => {
  on('session.model', () => ({ value: 'claude-sonnet-5-5' }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  const up = await $.tool.call({ tool: 'mcp__cheapest-model__escalate', reason: 'subtle race' })
  expect(up.result).toBe('Switched to opus for the rest of this turn.')
  const top = await $.tool.call({ tool: 'mcp__cheapest-model__escalate', to: 'fable', reason: 'opus failed' })
  expect(top.result).toBe('Switched to fable for the rest of this turn.')
  const down = await $.tool.call({ tool: 'mcp__cheapest-model__escalate', to: 'sonnet', reason: 'x' })
  expect(down.result).toBe('Already on fable; not switching.')
})

test('a fork is left alone', async ($, on) => {
  on('model.complete', classifierSays('haiku'))
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'inherited' }))
  const r = await $.agent.spawn({ ...SPAWN, fork: true })
  expect(r.model).toBe('inherited')
})
