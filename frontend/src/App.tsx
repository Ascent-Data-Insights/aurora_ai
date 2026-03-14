import { useState, useCallback } from 'react'
import { useChat } from '@/hooks/useChat'
import { useVoiceChat } from '@/hooks/useVoiceChat'
import ChatPanel from '@/components/ChatPanel'
import DebugPanel from '@/components/DebugPanel'
import ThreeRings from '@/components/ThreeRings'
import logo from '@/assets/logo.png'

const DEBUG = import.meta.env.VITE_DEBUG === 'true'

export default function App() {
  const { messages, input, setInput, isLoading, error, scores, debug, flowNodes, regression, sendMessage, setScores, setDebug, addAssistantMessage, attachedFiles, addFiles, removeFile } = useChat()
  const [voiceEnabled, setVoiceEnabled] = useState(false)

  const { isPlaying, sendVoiceMessage, stopPlayback } = useVoiceChat(
    setScores,
    DEBUG ? setDebug : undefined,
  )

  const handleSubmit = useCallback(async (content?: string) => {
    const text = (content ?? input).trim()
    if (!text) return

    if (voiceEnabled) {
      setInput('')
      addAssistantMessage(text, 'user')
      const assistantId = addAssistantMessage('', 'assistant')

      try {
        await sendVoiceMessage(text, (transcript) => {
          addAssistantMessage(transcript, 'assistant', assistantId)
        })
      } catch {
        await sendMessage(text)
      }
    } else {
      await sendMessage(content)
    }
  }, [input, voiceEnabled, sendMessage, sendVoiceMessage, setInput, addAssistantMessage])

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
