import { useState, useCallback } from 'react'
import { useChat } from '@/hooks/useChat'
import { useVoiceChat } from '@/hooks/useVoiceChat'
import ChatPanel from '@/components/ChatPanel'
import DebugPanel from '@/components/DebugPanel'
import ThreeRings from '@/components/ThreeRings'
import logo from '@/assets/logo.png'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEBUG = import.meta.env.VITE_DEBUG === 'true'

export default function App() {
  const { messages, input, setInput, isLoading, error, setError, scores, debug, flowNodes, regression, sendMessage, setScores, setDebug, addAssistantMessage, removeMessage, attachedFiles, addFiles, removeFile, sessionIdRef: chatSessionIdRef, uploadFiles, clearFiles } = useChat()
  const [voiceEnabled, setVoiceEnabled] = useState(false)

  const { isPlaying, sendVoiceMessage, stopPlayback, sessionIdRef: voiceSessionIdRef } = useVoiceChat(
    setScores,
    DEBUG ? setDebug : undefined,
  )

  const handleSubmit = useCallback(async (content?: string) => {
    const text = (content ?? input).trim()
    if (!text && attachedFiles.length === 0) return

    if (voiceEnabled) {
      setInput('')

      const fileNames = attachedFiles.filter(f => f.status === 'done' || f.status === 'pending').map(f => f.file.name)
      const messageToSend = text || `Please analyze the uploaded document${attachedFiles.length > 1 ? 's' : ''}.`
      const displayContent = fileNames.length > 0
        ? `${messageToSend}\n\n📎 ${fileNames.join(', ')}`
        : messageToSend

      addAssistantMessage(displayContent, 'user')
      const assistantId = addAssistantMessage('', 'assistant')

      if (!chatSessionIdRef.current) {
        try {
          const res = await fetch(`${API_BASE}/api/chat/sessions`, { method: 'POST' })
          const data = await res.json()
          chatSessionIdRef.current = data.session_id
        } catch {
          removeMessage(assistantId)
          await sendMessage(text)
          return
        }
      }

      if (attachedFiles.some(f => f.status === 'pending')) {
        const ok = await uploadFiles(chatSessionIdRef.current!)
        if (!ok) {
          addAssistantMessage('Some files failed to upload.', 'assistant', assistantId)
          setError('Some files failed to upload')
          return
        }
      }

      voiceSessionIdRef.current = chatSessionIdRef.current
      clearFiles()

      try {
        await sendVoiceMessage(messageToSend, (transcript) => {
          addAssistantMessage(transcript, 'assistant', assistantId)
        })
      } catch {
        removeMessage(assistantId)
        await sendMessage(messageToSend)
      }

      if (voiceSessionIdRef.current) {
        chatSessionIdRef.current = voiceSessionIdRef.current
      }
    } else {
      await sendMessage(content)
    }
  }, [input, voiceEnabled, sendMessage, sendVoiceMessage, setInput, setError, addAssistantMessage, removeMessage, attachedFiles, uploadFiles, clearFiles, chatSessionIdRef, voiceSessionIdRef])

  return (
    <div className="flex h-screen flex-col font-body bg-zinc-50">
      {/* Header */}
      <header className="flex items-center gap-4 border-b border-zinc-200 bg-white px-6 py-3">
        <a href="https://ascentdi.com" target="_blank" rel="noopener noreferrer">
          <img src={logo} alt="Ascent Data Insights" className="h-8" />
        </a>
        <div className="h-6 w-px bg-zinc-200" />
        <h1 className="font-heading text-lg font-semibold text-primary">Portfolio Strategy</h1>
      </header>

      {/* Score rings strip */}
      <div className="flex justify-end border-b border-zinc-200 bg-white px-6 py-3">
        <ThreeRings scores={scores} />
      </div>

      {/* Chat */}
      <div className="flex min-h-0 flex-1 flex-col">
        <ChatPanel
          messages={messages}
          input={input}
          setInput={setInput}
          isLoading={isLoading || isPlaying}
          error={error}
          onSubmit={handleSubmit}
          voiceEnabled={voiceEnabled}
          onToggleVoice={() => setVoiceEnabled(v => !v)}
          isPlaying={isPlaying}
          onStopPlayback={stopPlayback}
          attachedFiles={attachedFiles}
          onAddFiles={addFiles}
          onRemoveFile={removeFile}
        />
      </div>

      {/* Debug panel — dev mode only */}
      {DEBUG && <DebugPanel debug={debug} flowNodes={flowNodes} regression={regression} />}
    </div>
  )
}
