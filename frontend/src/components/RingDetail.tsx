import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react'
import RingDonut from './RingDonut'

interface RingDetailProps {
  label: string
  color: string
  confidence: number
  value: number
}

export default function RingDetail({ label, color, confidence, value }: RingDetailProps) {
  return (
    <Popover className="relative flex flex-col items-center gap-1">
      <PopoverButton className="cursor-pointer focus:outline-none">
        <RingDonut confidence={confidence} color={color} />
      </PopoverButton>
      <span className="text-[11px] font-medium text-zinc-500">{label}</span>
      <span className="text-[10px] tabular-nums text-zinc-400">{confidence}%</span>

      <PopoverPanel
        anchor="bottom"
        className="z-50 mt-2 rounded-lg border border-zinc-200 bg-white p-3 shadow-lg"
      >
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-6">
            <span className="text-zinc-500">Confidence</span>
            <span className="font-medium text-zinc-900">{confidence}%</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-zinc-500">Assessed Value</span>
            <span className="font-medium text-zinc-900">{value}/100</span>
          </div>
        </div>
      </PopoverPanel>
    </Popover>
  )
}
