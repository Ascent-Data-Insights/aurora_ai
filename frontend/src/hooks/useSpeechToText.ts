import { useState, useRef, useCallback, useEffect } from 'react'

const WS_BASE = import.meta.env.VITE_WS_BASE ?? ''

export function useSpeechToText() {
  const [sttActive, setSttActive] = useState(false)
  const [isListening, setIsListening] = useState(false)

  const sttActiveRef = useRef(false)
  const mutedRef = useRef(false)
  const wsRef = useRef<WebSocket | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const accumFinalRef = useRef('')

  // Callback refs — set by the consumer so they can close over current state
  const onInterimRef = useRef<((text: string) => void) | null>(null)
  const onFinalRef = useRef<((text: string) => void) | null>(null)

  const stopRecording = useCallback(() => {
    // Close our backend WebSocket (which closes Deepgram upstream)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    // Stop audio processing
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    // Stop mic stream
    mediaStreamRef.current?.getTracks().forEach(t => t.stop())
    mediaStreamRef.current = null

    accumFinalRef.current = ''
    setIsListening(false)
  }, [])

  const startRecording = useCallback(async () => {
    // Get mic access
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      console.error('Mic access denied:', err)
      return
    }
    mediaStreamRef.current = stream

    // If user toggled off while we were awaiting, abort
    if (!sttActiveRef.current || mutedRef.current) {
      stream.getTracks().forEach(t => t.stop())
      mediaStreamRef.current = null
      return
    }

    // Use the mic's native sample rate — resampling across contexts isn't supported
    const audioContext = new AudioContext()
    audioContextRef.current = audioContext
    const nativeSampleRate = audioContext.sampleRate

    // Connect to our backend STT proxy, telling it our actual sample rate
    const ws = new WebSocket(`${WS_BASE}/api/stt/ws?sample_rate=${nativeSampleRate}`)
    wsRef.current = ws

    ws.onopen = () => {
      const source = audioContext.createMediaStreamSource(stream)

      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return
        const float32 = e.inputBuffer.getChannelData(0)
        const int16 = new Int16Array(float32.length)
        for (let i = 0; i < float32.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, Math.round(float32[i] * 32768)))
        }
        ws.send(int16.buffer)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsListening(true)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      // Handle errors from backend
      if (data.type === 'error') {
        console.error('STT error:', data.message)
        stopRecording()
        return
      }

      // Deepgram results (proxied through backend)
      if (data.type !== 'Results') return

      const alt = data.channel?.alternatives?.[0]
      if (!alt) return

      const transcript = alt.transcript || ''
      if (!transcript) return

      const isFinal = data.is_final
      const speechFinal = data.speech_final

      if (isFinal) {
        accumFinalRef.current += transcript
        onInterimRef.current?.(accumFinalRef.current)

        if (speechFinal) {
          onFinalRef.current?.(accumFinalRef.current)
          accumFinalRef.current = ''
        }
      } else {
        onInterimRef.current?.(accumFinalRef.current + transcript)
      }
    }

    ws.onclose = () => {
      wsRef.current = null
      setIsListening(false)
    }

    ws.onerror = () => {
      console.error('STT WebSocket error')
      stopRecording()
    }
  }, [stopRecording])

  const toggle = useCallback(() => {
    if (sttActive) {
      sttActiveRef.current = false
      setSttActive(false)
      stopRecording()
    } else {
      sttActiveRef.current = true
      setSttActive(true)
      if (!mutedRef.current) {
        startRecording()
      }
    }
  }, [sttActive, startRecording, stopRecording])

  const mute = useCallback(() => {
    mutedRef.current = true
    stopRecording()
  }, [stopRecording])

  const unmute = useCallback(() => {
    mutedRef.current = false
    if (sttActiveRef.current) {
      startRecording()
    }
  }, [startRecording])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  return {
    sttActive,
    isListening,
    toggle,
    mute,
    unmute,
    onInterimRef,
    onFinalRef,
  }
}
