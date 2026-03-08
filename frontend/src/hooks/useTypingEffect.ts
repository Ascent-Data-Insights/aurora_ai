import { useState, useEffect, useRef } from 'react'

/**
 * Gradually reveals `content` character by character.
 * Returns the portion of content visible so far.
 * When `content` grows (new chunks), the reveal continues from where it left off.
 * When `isActive` is false, returns the full content immediately.
 */
export function useTypingEffect(
  content: string,
  isActive: boolean,
  charsPerTick = 3,
  intervalMs = 12,
): string {
  const [displayed, setDisplayed] = useState('')
  const indexRef = useRef(0)

  // When not actively streaming, show full content immediately
  useEffect(() => {
    if (!isActive) {
      setDisplayed(content)
      indexRef.current = content.length
    }
  }, [isActive, content])

  useEffect(() => {
    if (!isActive) return

    const timer = setInterval(() => {
      if (indexRef.current >= content.length) {
        return // wait for more content
      }

      const nextIndex = Math.min(indexRef.current + charsPerTick, content.length)
      indexRef.current = nextIndex
      setDisplayed(content.slice(0, nextIndex))
    }, intervalMs)

    return () => clearInterval(timer)
  }, [content, isActive, charsPerTick, intervalMs])

  return displayed
}
