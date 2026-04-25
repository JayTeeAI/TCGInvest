'use client'

import { formatGBP } from '@/lib/format'

interface ChaseMover {
  id: number
  card_name: string
  card_number: string | null
  set_name: string
  era: string
  raw_gbp: number
  prev_raw_gbp: number
  psa10_gbp: number | null
  raw_delta_pct: number
  grade_mult: number | null
}

interface Props {
  movers: ChaseMover[]
  latest: string
  previous: string | null
}

export function ChaseMoversPanel({ movers, latest, previous }: Props) {
  if (!previous || !movers.length) return (
    <div className='mb-8 bg-slate-900 border border-slate-800 rounded-xl px-5 py-4 flex items-center gap-3'>
      <span className='text-slate-500 text-sm'>📊 Week-on-week price movers will appear once a second weekly snapshot has been collected.</span>
    </div>
  )

  const rises = [...movers]
    .filter(m => m.raw_delta_pct > 0)
    .sort((a, b) => b.raw_delta_pct - a.raw_delta_pct)
    .slice(0, 3)

  const drops = [...movers]
    .filter(m => m.raw_delta_pct < 0)
    .sort((a, b) => a.raw_delta_pct - b.raw_delta_pct)
    .slice(0, 3)

  const highestGradeMult = [...movers]
    .filter(m => m.grade_mult != null)
    .sort((a, b) => (b.grade_mult ?? 0) - (a.grade_mult ?? 0))
    .slice(0, 3)

  function MoverRow({ m, showMult }: { m: ChaseMover; showMult?: boolean }) {
    const isRise = m.raw_delta_pct > 0
    const shortName = m.card_name.length > 28 ? m.card_name.slice(0, 26) + '…' : m.card_name
    const shortSet = m.set_name.length > 22 ? m.set_name.slice(0, 20) + '…' : m.set_name
    return (
      <div className='flex items-center justify-between py-2.5 border-b border-slate-800 last:border-0'>
        <div className='min-w-0'>
          <div className='text-slate-200 text-sm font-medium truncate'>{shortName}</div>
          <div className='text-slate-500 text-xs'>{shortSet}</div>
        </div>
        <div className='text-right shrink-0 ml-2'>
          {showMult ? (
            <>
              <div className='text-blue-400 font-bold text-sm'>{m.grade_mult?.toFixed(1)}x</div>
              <div className='text-slate-500 text-xs'>{formatGBP(m.raw_gbp)} raw</div>
            </>
          ) : (
            <>
              <div className={isRise ? 'text-emerald-400 font-bold text-sm' : 'text-red-400 font-bold text-sm'}>
                {isRise ? '+' : ''}{m.raw_delta_pct.toFixed(1)}%
              </div>
              <div className='text-slate-500 text-xs'>{formatGBP(m.raw_gbp)} now</div>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className='grid grid-cols-1 md:grid-cols-3 gap-4 mb-8'>
      {rises.length > 0 && (
        <div className='bg-slate-900 border border-slate-800 rounded-xl p-4'>
          <div className='mb-3'>
            <p className='text-white font-semibold text-sm'>Biggest price rises</p>
            <p className='text-slate-500 text-xs'>Raw price up most this week</p>
          </div>
          {rises.map(m => <MoverRow key={m.id} m={m} />)}
        </div>
      )}
      {drops.length > 0 && (
        <div className='bg-slate-900 border border-slate-800 rounded-xl p-4'>
          <div className='mb-3'>
            <p className='text-white font-semibold text-sm'>Biggest price drops</p>
            <p className='text-slate-500 text-xs'>Raw price down most this week</p>
          </div>
          {drops.map(m => <MoverRow key={m.id} m={m} />)}
        </div>
      )}
      {highestGradeMult.length > 0 && (
        <div className='bg-slate-900 border border-slate-800 rounded-xl p-4'>
          <div className='mb-3'>
            <p className='text-white font-semibold text-sm'>Highest above raw</p>
            <p className='text-slate-500 text-xs'>PSA 10 vs raw price multiplier</p>
          </div>
          {highestGradeMult.map(m => <MoverRow key={m.id} m={m} showMult />)}
        </div>
      )}
    </div>
  )
}
