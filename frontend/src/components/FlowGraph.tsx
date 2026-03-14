import type { FlowNodeState, FlowNodeStatus } from '@/hooks/useChat'

const NODES = [
  { id: 'route', label: 'Route', description: 'Determine phase' },
  { id: 'chat', label: 'Chat', description: 'Run chat agent' },
  { id: 'extract', label: 'Extract', description: 'Update state' },
  { id: 'detect_regression', label: 'Detect Regression', description: 'Check scores' },
] as const

const STATUS_STYLES: Record<FlowNodeStatus, string> = {
  idle: 'border-zinc-300 bg-white text-zinc-400',
  active: 'border-secondary bg-blue-50 text-secondary ring-2 ring-secondary/30',
  done: 'border-emerald-400 bg-emerald-50 text-emerald-700',
}

const STATUS_DOT: Record<FlowNodeStatus, string> = {
  idle: 'bg-zinc-300',
  active: 'bg-secondary animate-pulse',
  done: 'bg-emerald-400',
}

interface FlowGraphProps {
  flowNodes: FlowNodeState
  regression: string | null
}

export default function FlowGraph({ flowNodes, regression }: FlowGraphProps) {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {NODES.map((node, i) => {
        const status = flowNodes[node.id]
        const isLast = i === NODES.length - 1

        return (
          <div key={node.id} className="flex items-center gap-1">
            {/* Node */}
            <div
              className={`relative rounded-lg border px-3 py-1.5 transition-all duration-300 ${STATUS_STYLES[status]}`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[status]}`} />
                <span className="text-[11px] font-semibold whitespace-nowrap">{node.label}</span>
              </div>
              <div className="text-[9px] opacity-60">{node.description}</div>
            </div>

            {/* Edge arrow */}
            {!isLast && (
              <svg width="28" height="20" viewBox="0 0 28 20" className="shrink-0">
                <line x1="0" y1="10" x2="20" y2="10" stroke="#d4d4d8" strokeWidth="1.5" />
                <polygon points="20,6 28,10 20,14" fill="#d4d4d8" />
              </svg>
            )}

            {/* Regression loop arrow (from detect_regression back to chat) */}
            {isLast && regression && (
              <div className="ml-1 flex items-center gap-1 text-[10px] text-amber-600 font-medium">
                <svg width="20" height="20" viewBox="0 0 20 20" className="shrink-0">
                  <path d="M16 14 C16 4, 4 4, 4 10" fill="none" stroke="#d97706" strokeWidth="1.5" />
                  <polygon points="2,7 4,12 7,8" fill="#d97706" />
                </svg>
                {regression}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
