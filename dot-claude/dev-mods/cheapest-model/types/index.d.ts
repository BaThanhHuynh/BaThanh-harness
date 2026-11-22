export type ModelTier = 'haiku' | 'sonnet' | 'opus' | 'fable'
export type RouterMode = 'auto' | 'off' | ModelTier

declare module 'claude-code' {
  interface PluginState {
    'cheapest-model': { mode: RouterMode; last: ModelTier | null }
  }
}
