import { useState, useCallback, useRef } from 'react'
import type { Scores, DebugInfo } from './useChat'

const WS_BASE = import.meta.env.VITE_WS_BASE ?? ''
const SAMPLE_RATE = 24000

export function useVoiceChat(
  onScores: (scores: Scores) => void,
  onDebug?: (debug: DebugInfo) => void,
) {
  const [isPlaying, setIsPlaying] = useState(false)
  const sessionIdRef = useRef<string | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const nextPlayTimeRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)
  const scheduledSourcesRef = useRef<AudioBufferSourceNode[]>([])

  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE })
    }
    return audioContextRef.current
  }, [])

  const sendVoiceMessage = useCallback(
    async (
      text: string,
      onTranscript: (content: string) => void,
    ) => {
      const ctx = getAudioContext()
      if (ctx.state === 'suspended') await ctx.resume()

      // Reset playback scheduling
      nextPlayTimeRef.current = ctx.currentTime

      setIsPlaying(true)

      return new Promise<void>((resolve, reject) => {
        let accumulated = ''
        const ws = new WebSocket(`${WS_BASE}/api/voice/ws`)
        ws.binaryType = 'arraybuffer'
        wsRef.current = ws

        ws.onopen = () => {
          ws.send(
            JSON.stringify({
              message: text,
              session_id: sessionIdRef.current,
            }),
          )
        }

        ws.onmessage = (event) => {
          if (event.data instanceof ArrayBuffer) {
            // PCM s16le audio chunk — schedule for gapless playback
            const pcm16 = new Int16Array(event.data)
            const float32 = new Float32Array(pcm16.length)
            for (let i = 0; i < pcm16.length; i++) {
              float32[i] = pcm16[i] / 32768
            }

            const buffer = ctx.createBuffer(1, float32.length, SAMPLE_RATE)
            buffer.copyToChannel(float32, 0)

            const source = ctx.createBufferSource()
            source.buffer = buffer
            source.connect(ctx.destination)

            // Schedule this chunk right after the previous one
            const startTime = Math.max(nextPlayTimeRef.current, ctx.currentTime)
            source.start(startTime)
            nextPlayTimeRef.current = startTime + buffer.duration

            // Track for stop functionality
            scheduledSourcesRef.current.push(source)
            source.onended = () => {
              scheduledSourcesRef.current = scheduledSourcesRef.current.filter((s: AudioBufferSourceNode) => s !== source)
            }
          } else {
            // JSON text message
            const data = JSON.parse(event.data)

            if (data.type === 'session') {
              sessionIdRef.current = data.session_id
            } else if (data.type === 'delta') {
              accumulated += data.content
              onTranscript(accumulated)
            } else if (data.type === 'transcript') {
              onTranscript(data.content)
            } else if (data.type === 'scores') {
              onScores({
                value: data.value,
                feasibility: data.feasibility,
                scalability: data.scalability,
              })
            } else if (data.type === 'debug' && onDebug) {
              onDebug({
                phase: data.phase,
                guidance: data.guidance,
                state: data.state,
              })
            } else if (data.type === 'done') {
              ws.close()
            }
          }
        }

        ws.onclose = () => {
          // Wait for audio to finish playing before resolving
          const remaining = nextPlayTimeRef.current - ctx.currentTime
          if (remaining > 0) {
            setTimeout(() => {
              setIsPlaying(false)
              resolve()
            }, remaining * 1000)
          } else {
            setIsPlaying(false)
            resolve()
          }
        }

        ws.onerror = () => {
          setIsPlaying(false)
          reject(new Error('Voice WebSocket connection failed'))
        }
      })
    },
    [getAudioContext, onScores, onDebug],
  )

  const stopPlayback = useCallback(() => {
    // Close WebSocket to stop receiving more audio
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Stop all scheduled audio sources
    for (const source of scheduledSourcesRef.current) {
      try {
        source.stop()
      } catch {
        // Already stopped
      }
    }
    scheduledSourcesRef.current = []
    nextPlayTimeRef.current = 0

    setIsPlaying(false)
  }, [])

  return { isPlaying, sendVoiceMessage, stopPlayback, sessionIdRef }
}
