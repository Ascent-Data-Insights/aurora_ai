import { useState } from 'react'
import type { DebugInfo } from '@/hooks/useChat'

const PHASE_LABELS: Record<string, string> = {
  context_gathering: 'Context Gathering',
  initiative_framing: 'Initiative Framing',
  value_deep_dive: 'Value Deep Dive',
  feasibility_deep_dive: 'Feasibility Deep Dive',
  scalability_deep_dive: 'Scalability Deep Dive',
  synthesis: 'Synthesis',
}

const PHASE_COLORS: Record<string, string> = {
  context_gathering: 'bg-amber-100 text-amber-800',
  initiative_framing: 'bg-blue-100 text-blue-800',
  value_deep_dive: 'bg-emerald-100 text-emerald-800',
  feasibility_deep_dive: 'bg-purple-100 text-purple-800',
  scalability_deep_dive: 'bg-rose-100 text-rose-800',
  synthesis: 'bg-zinc-100 text-zinc-800',
}

interface DebugPanelProps {
  debug: DebugInfo | null
}

export default function DebugPanel({ debug }: DebugPanelProps) {
  const [expanded, setExpanded] = useState(false)

  if (!debug) return null

  const phaseLabel = PHASE_LABELS[debug.phase] ?? debug.phase
  const phaseColor = PHASE_COLORS[debug.phase] ?? 'bg-zinc-100 text-zinc-800'

  const state = debug.state as Record<string, Record<string, unknown>>

  return (
    <div className="border-t border-zinc-200 bg-zinc-50 text-xs font-mono">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-2 hover:bg-zinc-100 transition-colors"
      >
        <span className="text-zinc-400 select-none">{expanded ? '▼' : '▶'}</span>
        <span className="text-zinc-500">DEBUG</span>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${phaseColor}`}>
          {phaseLabel}
        </span>
        <FieldCounts state={state} />
      </button>

      {expanded && (
        <div className="border-t border-zinc-200 px-4 py-3 space-y-3 max-h-80 overflow-y-auto">
          <Section title="Guidance" value={debug.guidance} />
          <StateSection title="Organization" data={state.organization} />
          <StateSection title="User" data={state.user} />
          <StateSection title="Initiative" data={state.initiative} />
          <StateSection title="Value Assessment" data={state.value_assessment} />
          <StateSection title="Feasibility Assessment" data={state.feasibility_assessment} />
          <StateSection title="Scalability Assessment" data={state.scalability_assessment} />
          <ScoresSection scores={state.scores} />
        </div>
      )}
    </div>
  )
}

function FieldCounts({ state }: { state: Record<string, Record<string, unknown>> }) {
  const sections = ['organization', 'user', 'initiative', 'value_assessment', 'feasibility_assessment', 'scalability_assessment']
  let filled = 0
  let total = 0
  for (const key of sections) {
    const obj = state[key]
    if (!obj || typeof obj !== 'object') continue
    for (const v of Object.values(obj)) {
      total++
      if (v != null) filled++
    }
  }
  return (
    <span className="ml-auto text-zinc-400">
      {filled}/{total} fields
    </span>
  )
}

function Section({ title, value }: { title: string; value: string }) {
  return (
    <div>
      <div className="text-zinc-400 mb-1">{title}</div>
      <div className="text-zinc-600 whitespace-pre-wrap">{value}</div>
    </div>
  )
}

function StateSection({ title, data }: { title: string; data?: Record<string, unknown> }) {
  if (!data) return null
  const entries = Object.entries(data)
  const hasAny = entries.some(([, v]) => v != null)

  return (
    <div>
      <div className="text-zinc-400 mb-1">{title}</div>
      {hasAny ? (
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
          {entries.map(([key, val]) => (
            <div key={key} className="contents">
              <span className="text-zinc-400">{key}:</span>
              <span className={val != null ? 'text-zinc-700' : 'text-zinc-300'}>
                {val != null ? String(val) : '—'}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <span className="text-zinc-300 italic">empty</span>
      )}
    </div>
  )
}

function ScoresSection({ scores }: { scores?: Record<string, unknown> }) {
  if (!scores) return null
  const rings = ['value', 'feasibility', 'scalability'] as const

  return (
    <div>
      <div className="text-zinc-400 mb-1">Scores</div>
      <div className="grid grid-cols-3 gap-2">
        {rings.map(ring => {
          const s = scores[ring] as { value: number; confidence: number } | undefined
          if (!s) return null
          return (
            <div key={ring} className="rounded bg-white border border-zinc-200 px-2 py-1">
              <div className="text-zinc-500 capitalize">{ring}</div>
              <div className="text-zinc-700">val: {s.value} / conf: {s.confidence}%</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
