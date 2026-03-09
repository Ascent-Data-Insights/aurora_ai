import { motion } from 'motion/react'

interface RingDonutProps {
  confidence: number
  color: string
  size?: number
}

const STROKE_WIDTH = 8

export default function RingDonut({ confidence, color, size = 72 }: RingDonutProps) {
  const radius = (size - STROKE_WIDTH) / 2
  const circumference = 2 * Math.PI * radius
  const dashoffset = circumference * (1 - confidence / 100)
  const center = size / 2

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background track */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={color}
        strokeOpacity="0.15"
        strokeWidth={STROKE_WIDTH}
      />
      {/* Confidence fill */}
      <motion.circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
        strokeDasharray={circumference}
        animate={{ strokeDashoffset: dashoffset }}
        transition={{ type: 'spring', stiffness: 60, damping: 15 }}
        transform={`rotate(-90 ${center} ${center})`}
      />
    </svg>
  )
}
