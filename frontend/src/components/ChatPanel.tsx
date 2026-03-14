import { useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, AlertCircle, Volume2, VolumeX, Mic, MicOff, Square, Paperclip, X } from 'lucide-react'
import { Button } from '@components/button'
import type { Message, UploadedFile } from '@/hooks/useChat'
import { useTypingEffect } from '@/hooks/useTypingEffect'
import { useSpeechToText } from '@/hooks/useSpeechToText'
import Markdown from 'react-markdown'
import clsx from 'clsx'

const ACCEPT = '.docx,.pptx,.xlsx'

interface ChatPanelProps {
  messages: Message[]
  input: string
  setInput: (value: string) => void
  isLoading: boolean
  error: string | null
  onSubmit: () => void
  voiceEnabled: boolean
  onToggleVoice: () => void
  isPlaying: boolean
  onStopPlayback: () => void
  attachedFiles: UploadedFile[]
  onAddFiles: (files: FileList | File[]) => void
  onRemoveFile: (index: number) => void
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
  voiceEnabled,
  onToggleVoice,
  isPlaying,
  onStopPlayback,
  attachedFiles,
  onAddFiles,
  onRemoveFile,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // STT state for tracking insertion position
  const anchorRef = useRef(0)
  const interimLenRef = useRef(0)
  const inputValueRef = useRef(input)
  inputValueRef.current = input

  const {
    sttActive,
    isListening,
    toggle: toggleStt,
    mute: muteStt,
    unmute: unmuteStt,
    onInterimRef,
    onFinalRef,
  } = useSpeechToText()

  // Resize textarea to fit content
  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [])

  // Wire up STT callbacks
  onInterimRef.current = (text: string) => {
    const currentInput = inputValueRef.current
    const anchor = anchorRef.current
    const oldLen = interimLenRef.current

    // Safety: if anchor + oldLen exceeds input length, reset
    const safeOldLen = anchor + oldLen > currentInput.length ? 0 : oldLen

    // New utterance — capture cursor position
    if (safeOldLen === 0 && oldLen === 0) {
      anchorRef.current = textareaRef.current?.selectionStart ?? currentInput.length
    }

    const a = anchorRef.current
    const before = currentInput.slice(0, a)
    const after = currentInput.slice(a + safeOldLen)
    const newInput = before + text + after

    interimLenRef.current = text.length
    inputValueRef.current = newInput
    setInput(newInput)

    // Position cursor after interim text
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        const pos = a + text.length
        textareaRef.current.selectionStart = pos
        textareaRef.current.selectionEnd = pos
      }
      resizeTextarea()
    })
  }

  onFinalRef.current = (text: string) => {
    const currentInput = inputValueRef.current
    const anchor = anchorRef.current
    const oldLen = interimLenRef.current

    // Safety check
    const safeOldLen = anchor + oldLen > currentInput.length ? 0 : oldLen

    const before = currentInput.slice(0, anchor)
    const after = currentInput.slice(anchor + safeOldLen)
    const finalText = text + ' '
    const newInput = before + finalText + after

    anchorRef.current = anchor + finalText.length
    interimLenRef.current = 0
    inputValueRef.current = newInput
    setInput(newInput)

    requestAnimationFrame(() => {
      if (textareaRef.current) {
        const pos = anchor + finalText.length
        textareaRef.current.selectionStart = pos
        textareaRef.current.selectionEnd = pos
      }
      resizeTextarea()
    })
  }

  // Reset STT tracking when input is externally cleared (e.g. on submit)
  useEffect(() => {
    if (input === '') {
      anchorRef.current = 0
      interimLenRef.current = 0
    }
  }, [input])

  // Mute/unmute mic when TTS plays/stops
  useEffect(() => {
    if (isPlaying) {
      muteStt()
    } else {
      unmuteStt()
    }
  }, [isPlaying, muteStt, unmuteStt])

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, isLoading])

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  // Determine mic button state
  const micMuted = sttActive && isPlaying // STT on but muted due to TTS

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div ref={scrollRef} className="relative flex-1 overflow-y-auto p-6 space-y-4">
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
        {/* Attached file chips */}
        {attachedFiles.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachedFiles.map((f, i) => (
              <span
                key={i}
                className={clsx(
                  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium',
                  f.status === 'error'
                    ? 'bg-red-100 text-red-700'
                    : f.status === 'uploading'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-zinc-100 text-zinc-700'
                )}
              >
                <Paperclip className="size-3" />
                {f.file.name}
                {f.status === 'uploading' && <Loader2 className="size-3 animate-spin" />}
                <button
                  onClick={() => onRemoveFile(i)}
                  className="ml-1 rounded-full p-0.5 hover:bg-zinc-200"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={e => {
            if (e.target.files) onAddFiles(e.target.files)
            e.target.value = ''
          }}
        />

        <div className="flex items-end gap-3">
          <textarea
            ref={textareaRef}
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

          {/* Attach files */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 rounded-lg bg-zinc-100 p-3 text-zinc-400 transition-colors hover:text-zinc-600"
            title="Attach documents (.docx, .pptx, .xlsx)"
          >
            <Paperclip className="size-4" />
          </button>

          {/* Mic button — STT toggle */}
          <button
            onClick={toggleStt}
            className={clsx(
              'relative shrink-0 rounded-lg p-3 transition-colors',
              sttActive
                ? micMuted
                  ? 'bg-zinc-300 text-zinc-500'
                  : 'bg-red-500 text-white'
                : 'bg-zinc-100 text-zinc-400 hover:text-zinc-600'
            )}
            title={
              sttActive
                ? micMuted
                  ? 'Mic muted (TTS playing)'
                  : 'Speech-to-text on — click to turn off'
                : 'Click to enable speech-to-text'
            }
          >
            {sttActive && !micMuted ? (
              <>
                <Mic className="size-4" />
                {/* Pulsing indicator when actively listening */}
                {isListening && (
                  <span className="absolute -top-0.5 -right-0.5 flex size-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                    <span className="relative inline-flex size-2.5 rounded-full bg-red-300" />
                  </span>
                )}
              </>
            ) : sttActive && micMuted ? (
              <MicOff className="size-4" />
            ) : (
              <Mic className="size-4" />
            )}
          </button>

          {/* Voice (TTS) toggle */}
          <button
            onClick={onToggleVoice}
            className={clsx(
              'shrink-0 rounded-lg p-3 transition-colors',
              voiceEnabled
                ? 'bg-secondary text-white'
                : 'bg-zinc-100 text-zinc-400 hover:text-zinc-600'
            )}
            title={voiceEnabled ? 'Voice mode on' : 'Voice mode off'}
          >
            {voiceEnabled ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
          </button>

          {/* Stop / Send button */}
          {isPlaying ? (
            <Button
              color="dark"
              onClick={onStopPlayback}
              className="shrink-0"
              title="Stop playback"
            >
              <Square className="size-4" data-slot="icon" />
            </Button>
          ) : (
            <Button
              color="dark"
              onClick={() => onSubmit()}
              disabled={(!input.trim() && attachedFiles.length === 0) || isLoading}
              className="shrink-0"
            >
              <Send className="size-4" data-slot="icon" />
            </Button>
          )}
        </div>
        <p className="mt-2 text-xs text-zinc-400">
          {isPlaying
            ? 'Speaking... click stop to interrupt'
            : sttActive && isListening
              ? 'Listening... speak to add text'
              : 'Press Enter to send, Shift+Enter for new line'}
        </p>
      </div>
    </div>
  )
}
