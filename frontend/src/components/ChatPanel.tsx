import { useRef, useEffect } from 'react'
import { Send, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@components/button'
import type { Message } from '@/hooks/useChat'
import { useTypingEffect } from '@/hooks/useTypingEffect'
import Markdown from 'react-markdown'
import clsx from 'clsx'

interface ChatPanelProps {
  messages: Message[]
  input: string
  setInput: (value: string) => void
  isLoading: boolean
  error: string | null
  onSubmit: () => void
}

function MessageBubble({ message, isStreaming }: { message: Message; isStreaming?: boolean }) {
  const isUser = message.role === 'user'
  const displayedContent = useTypingEffect(message.content, !!isStreaming)

  // Empty assistant message while waiting for first token
  if (!isUser && !displayedContent && isStreaming) {
    return (
      <div className="flex justify-start">
        <div className="flex items-center gap-2 rounded-2xl bg-zinc-100 px-4 py-3 text-sm text-zinc-500">
          <Loader2 className="size-4 animate-spin" />
          Thinking...
        </div>
      </div>
    )
  }

  if (!displayedContent) return null

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm/6',
          isUser
            ? 'bg-primary text-white rounded-br-md'
            : 'bg-zinc-100 text-zinc-900 rounded-bl-md'
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-zinc max-w-none">
            <Markdown>{displayedContent}</Markdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPanel({
  messages,
  input,
  setInput,
  isLoading,
  error,
  onSubmit,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, isLoading])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <h2 className="font-heading text-xl font-semibold text-primary">
                Portfolio Strategy Assistant
              </h2>
              <p className="mt-2 text-sm text-zinc-500">
                Ask about portfolio evaluation, initiative prioritization, or strategic planning.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const isLastMessage = i === messages.length - 1
          return (
            <MessageBubble
              key={msg.id}
              message={msg}
              isStreaming={isLoading && isLastMessage}
            />
          )
        })}

        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-zinc-200 p-4">
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about portfolio strategy..."
            rows={1}
            className={clsx(
              'flex-1 resize-none rounded-lg border border-zinc-300 bg-white px-4 py-3',
              'text-sm text-zinc-900 placeholder:text-zinc-400',
              'focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20',
              'max-h-32'
            )}
            style={{
              height: 'auto',
              minHeight: '44px',
            }}
            onInput={e => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = Math.min(target.scrollHeight, 128) + 'px'
            }}
          />
          <Button
            color="dark"
            onClick={() => onSubmit()}
            disabled={!input.trim() || isLoading}
            className="shrink-0"
          >
            <Send className="size-4" data-slot="icon" />
          </Button>
        </div>
        <p className="mt-2 text-xs text-zinc-400">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
