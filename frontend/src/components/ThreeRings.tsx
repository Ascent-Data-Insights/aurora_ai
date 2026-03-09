import { motion } from 'motion/react'
import RingDetail from './RingDetail'
import type { Scores } from '@/hooks/useChat'

const DIMENSIONS = [
  { key: 'value' as const, label: 'Value', color: '#FB8500' },
  { key: 'feasibility' as const, label: 'Feasibility', color: '#4785BF' },
  { key: 'scalability' as const, label: 'Scalability', color: '#2EC4B6' },
]

interface ThreeRingsProps {
  scores: Scores
}

export default function ThreeRings({ scores }: ThreeRingsProps) {
  return (
    <div className="flex items-start gap-3">
      {DIMENSIONS.map((dim, i) => {
        const s = scores[dim.key]
        const isHighConfidence = s.confidence >= 90
        return (
          <motion.div
            key={dim.key}
            initial={{ opacity: 0, y: -8 }}
            animate={{
              opacity: 1,
              y: 0,
              filter: isHighConfidence
                ? [
                    `drop-shadow(0 0 0px ${dim.color})`,
                    `drop-shadow(0 0 6px ${dim.color})`,
                    `drop-shadow(0 0 0px ${dim.color})`,
                  ]
                : 'none',
            }}
            transition={{
              opacity: { delay: i * 0.1, duration: 0.3 },
              y: { delay: i * 0.1, type: 'spring', stiffness: 120, damping: 14 },
              filter: isHighConfidence
                ? { duration: 2, repeat: Infinity, ease: 'easeInOut' }
                : { duration: 0 },
            }}
          >
            <RingDetail
              label={dim.label}
              color={dim.color}
              confidence={s.confidence}
              value={s.value}
            />
          </motion.div>
        )
      })}
    </div>
  )
}
