import { useState, useCallback, useRef } from 'react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface DimensionScore {
  value: number
  confidence: number
}

export interface Scores {
  value: DimensionScore
  feasibility: DimensionScore
  scalability: DimensionScore
}

const INITIAL_SCORES: Scores = {
  value: { value: 0, confidence: 0 },
  feasibility: { value: 0, confidence: 0 },
  scalability: { value: 0, confidence: 0 },
}

const API_BASE = 'http://localhost:8000'

export interface DebugInfo {
  phase: string
  guidance: string
  state: Record<string, unknown>
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scores, setScores] = useState<Scores>(INITIAL_SCORES)
  const [debug, setDebug] = useState<DebugInfo | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  const sendMessage = useCallback(async (content?: string) => {
    const text = (content ?? input).trim()
    if (!text || isLoading) return

    setError(null)
    setInput('')

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    const assistantId = crypto.randomUUID()

    try {
      const res = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionIdRef.current,
        }),
      })

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`)
      }

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      // Add empty assistant message that we'll stream into
      setMessages(prev => [
        ...prev,
        { id: assistantId, role: 'assistant', content: '' },
      ])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // Keep the last (possibly incomplete) line in the buffer
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const json = line.slice(6)

          try {
            const event = JSON.parse(json)

            if (event.type === 'session') {
              sessionIdRef.current = event.session_id
            } else if (event.type === 'delta') {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.content }
                    : m
                )
              )
            } else if (event.type === 'scores') {
              setScores({
                value: event.value,
                feasibility: event.feasibility,
                scalability: event.scalability,
              })
            } else if (event.type === 'debug') {
              setDebug({
                phase: event.phase,
                guidance: event.guidance,
                state: event.state,
              })
            }
            // 'done' — nothing to do, loop will exit on reader.read()
          } catch {
            // skip malformed lines
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      // Remove empty assistant message if we errored before any content
      setMessages(prev => {
        const last = prev[prev.length - 1]
        if (last?.id === assistantId && !last.content) {
          return prev.slice(0, -1)
        }
        return prev
      })
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading])

  const resetChat = useCallback(() => {
    setMessages([])
    setInput('')
    setError(null)
    setScores(INITIAL_SCORES)
    setDebug(null)
    sessionIdRef.current = null
  }, [])

  return { messages, input, setInput, isLoading, error, scores, debug, sendMessage, resetChat }
}
