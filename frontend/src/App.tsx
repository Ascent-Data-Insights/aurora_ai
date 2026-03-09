import { useChat } from '@/hooks/useChat'
import ChatPanel from '@/components/ChatPanel'
import logo from '@/assets/logo.png'

export default function App() {
  const { messages, input, setInput, isLoading, error, scores, sendMessage } = useChat()

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

      {/* Chat */}
      <div className="flex min-h-0 flex-1 flex-col">
        <ChatPanel
          messages={messages}
          input={input}
          setInput={setInput}
          isLoading={isLoading}
          error={error}
          scores={scores}
          onSubmit={sendMessage}
        />
      </div>
    </div>
  )
}
