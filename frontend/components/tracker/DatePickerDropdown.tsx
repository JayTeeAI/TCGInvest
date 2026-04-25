'use client'

import { useRouter } from 'next/navigation'

interface DatePickerDropdownProps {
  runDates: string[]
  selectedMonth: string | undefined
  isPremium: boolean
  isLoggedIn: boolean
}

function fmtDate(d: string) {
  const [y, m] = d.split('-')
  const months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[parseInt(m)]} ${y}`
}

export function DatePickerDropdown({ runDates, selectedMonth, isPremium, isLoggedIn }: DatePickerDropdownProps) {
  const router = useRouter()

  if (runDates.length <= 1) return null

  const latestDate = runDates[0]
  const currentValue = selectedMonth || latestDate

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    if (!val) return
    if (val === latestDate) {
      router.push('/tools/tracker')
    } else {
      router.push(`/tools/tracker?month=${val}`)
    }
  }

  // Auth gate: unauthed or free users can only select the latest date
  const canSelectAll = isPremium

  return (
    <div className="flex flex-col items-end gap-1.5">
      <select
        value={currentValue}
        onChange={handleChange}
        className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-slate-500 cursor-pointer min-w-[130px]"
      >
        {runDates.map((d: string, i: number) => {
          const isLatest = i === 0
          const isLocked = !isLatest && !canSelectAll
          return (
            <option
              key={d}
              value={d}
              disabled={isLocked}
              className={isLocked ? 'text-slate-600' : ''}
            >
              {isLocked ? `🔒 ${fmtDate(d)}` : fmtDate(d)}
            </option>
          )
        })}
      </select>
      {!isLoggedIn && runDates.length > 1 && (
        <span className="text-slate-600 text-xs">
          <a href="/auth/google" className="text-blue-400 hover:text-blue-300">Sign in free</a> to unlock historical months
        </span>
      )}
      {isLoggedIn && !isPremium && runDates.length > 1 && (
        <span className="text-slate-600 text-xs">
          <a href="/premium" className="text-yellow-400 hover:text-yellow-300">Upgrade to Premium</a> to access all months
        </span>
      )}
    </div>
  )
}
