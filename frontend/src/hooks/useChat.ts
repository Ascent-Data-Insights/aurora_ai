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

export interface UploadedFile {
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  error?: string
}

const API_BASE = 'http://localhost:8000'

const ACCEPTED_EXTENSIONS = ['.docx', '.pptx', '.xlsx']

export interface DebugInfo {
  phase: string
  guidance: string
  state: Record<string, unknown>
}

export type FlowNodeStatus = 'idle' | 'active' | 'done'

export interface FlowNodeState {
  route: FlowNodeStatus
  chat: FlowNodeStatus
  extract: FlowNodeStatus
  detect_regression: FlowNodeStatus
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scores, setScores] = useState<Scores>(INITIAL_SCORES)
  const [debug, setDebug] = useState<DebugInfo | null>(null)
  const [attachedFiles, setAttachedFiles] = useState<UploadedFile[]>([])
  const [flowNodes, setFlowNodes] = useState<FlowNodeState>({
    route: 'idle', chat: 'idle', extract: 'idle', detect_regression: 'idle',
  })
  const [regression, setRegression] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  const addFiles = useCallback((files: FileList | File[]) => {
    const newFiles: UploadedFile[] = []
    for (const file of Array.from(files)) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      if (ACCEPTED_EXTENSIONS.includes(ext)) {
        newFiles.push({ file, status: 'pending' })
      }
    }
    setAttachedFiles(prev => [...prev, ...newFiles])
  }, [])

  const removeFile = useCallback((index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  const uploadFiles = useCallback(async (sessionId: string): Promise<boolean> => {
    const pending = attachedFiles.filter(f => f.status === 'pending')
    if (pending.length === 0) return true

    setAttachedFiles(prev => prev.map(f => f.status === 'pending' ? { ...f, status: 'uploading' as const } : f))

    const formData = new FormData()
    for (const f of pending) {
      formData.append('files', f.file)
    }

    try {
      const res = await fetch(`${API_BASE}/api/chat/upload?session_id=${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`)

      const results: Array<{ filename: string; ok: boolean; error?: string }> = await res.json()
      setAttachedFiles(prev =>
        prev.map(f => {
          const result = results.find(r => r.filename === f.file.name)
          if (!result) return f
          return result.ok
            ? { ...f, status: 'done' as const }
            : { ...f, status: 'error' as const, error: result.error }
        })
      )
      return results.every(r => r.ok)
    } catch (err) {
      setAttachedFiles(prev =>
        prev.map(f => f.status === 'uploading' ? { ...f, status: 'error' as const, error: 'Upload failed' } : f)
      )
      return false
    }
  }, [attachedFiles])

  const sendMessage = useCallback(async (content?: string) => {
    const text = (content ?? input).trim()
    if ((!text && attachedFiles.length === 0) || isLoading) return

    setError(null)
    setInput('')
    setFlowNodes({ route: 'idle', chat: 'idle', extract: 'idle', detect_regression: 'idle' })
    setRegression(null)

    const fileNames = attachedFiles.filter(f => f.status === 'done' || f.status === 'pending').map(f => f.file.name)
    const displayContent = fileNames.length > 0
      ? `${text}\n\n📎 ${fileNames.join(', ')}`
      : text

    const messageToSend = text || `Please analyze the uploaded document${attachedFiles.length > 1 ? 's' : ''}.`

    // Add user message to UI immediately, before any async work
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: displayContent,
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setAttachedFiles([])

    // Ensure we have a session for file uploads
    if (!sessionIdRef.current) {
      try {
        const res = await fetch(`${API_BASE}/api/chat/sessions`, { method: 'POST' })
        const data = await res.json()
        sessionIdRef.current = data.session_id
      } catch {
        setError('Failed to create session')
        setIsLoading(false)
        return
      }
    }

    // Upload any pending files before sending the message
    const hasPending = attachedFiles.some(f => f.status === 'pending')
    if (hasPending) {
      const ok = await uploadFiles(sessionIdRef.current!)
      if (!ok) {
        setError('Some files failed to upload')
        setIsLoading(false)
        return
      }
    }

    let currentAssistantId = crypto.randomUUID()

    try {
      const res = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
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
        { id: currentAssistantId, role: 'assistant', content: '' },
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

          let event: Record<string, unknown>
          try {
            event = JSON.parse(json)
          } catch {
            // skip malformed SSE lines
            continue
          }

          if (event.type === 'session') {
            sessionIdRef.current = event.session_id as string
          } else if (event.type === 'message_start') {
            // Regression loop-back: the graph is running chat again
            currentAssistantId = crypto.randomUUID()
            setMessages(prev => [
              ...prev,
              { id: currentAssistantId, role: 'assistant', content: '' },
            ])
          } else if (event.type === 'delta') {
            setMessages(prev =>
              prev.map(m =>
                m.id === currentAssistantId
                  ? { ...m, content: m.content + (event.content as string) }
                  : m
              )
            )
          } else if (event.type === 'scores') {
            setScores({
              value: event.value as DimensionScore,
              feasibility: event.feasibility as DimensionScore,
              scalability: event.scalability as DimensionScore,
            })
          } else if (event.type === 'flow_node') {
            setFlowNodes(prev => ({ ...prev, [event.node as string]: event.status }))
          } else if (event.type === 'regression') {
            setRegression(event.ring as string)
          } else if (event.type === 'debug') {
            setDebug({
              phase: event.phase as string,
              guidance: event.guidance as string,
              state: event.state as Record<string, unknown>,
            })
          }
          // 'done' — nothing to do, loop will exit on reader.read()
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      // Remove empty assistant message if we errored before any content
      setMessages(prev => {
        const last = prev[prev.length - 1]
        if (last?.id === currentAssistantId && !last.content) {
          return prev.slice(0, -1)
        }
        return prev
      })
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, attachedFiles, uploadFiles])

  const addAssistantMessage = useCallback((content: string, role: 'user' | 'assistant', existingId?: string) => {
    const id = existingId ?? crypto.randomUUID()
    setMessages(prev => {
      // If updating an existing message, replace it
      if (existingId) {
        return prev.map(m => m.id === existingId ? { ...m, content } : m)
      }
      return [...prev, { id, role, content }]
    })
    return id
  }, [])

  const resetChat = useCallback(() => {
    setMessages([])
    setInput('')
    setError(null)
    setScores(INITIAL_SCORES)
    setDebug(null)
    setAttachedFiles([])
    sessionIdRef.current = null
  }, [])

  return { messages, input, setInput, isLoading, error, scores, debug, flowNodes, regression, sendMessage, resetChat, setScores, setDebug, addAssistantMessage, attachedFiles, addFiles, removeFile }
}
