'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { SetDetailPanel } from '@/components/tracker/SetDetailPanel'
import { formatGBP, formatPct, formatRatio, boxPctColor, scoreColor, recColor, parseDateReleased } from '@/lib/format'
import { getSetMomentum } from '@/lib/api'

interface TCGSet {
  id: number
  name: string
  era: string
  date_released: string
  print_status: string
  bb_price_gbp: number | null
  set_value_gbp: number | null
  top3_chase: string | null
  box_pct: number | null
  chase_pct: number | null
  recommendation: string | null
  scarcity: number | null
  liquidity: number | null
  mascot_power: number | null
  set_depth: number | null
  decision_score: number | null
  logo_url?: string
  booster_img_url?: string
  etb_img_url?: string
  chase_cards_json?: string
}

interface User {
  authenticated: boolean
  email?: string
  role?: string
}

interface MomentumData {
  d7_pct: number | null
  d30_pct: number | null
}

type MomentumMap = Record<number, MomentumData | null>

type SortKey = 'name' | 'era' | 'date_released' | 'bb_price_gbp' | 'set_value_gbp' | 'box_pct' | 'chase_pct' | 'decision_score'

const ERA_OPTIONS = ['All', 'S&V', 'SWSH', 'SM', 'XY', 'BW', 'MEGA', 'EX']

type HeatScoreMap = Record<string, { heat_score: number } | null>

export function TrackerTable({ sets, user, heatScores = {} }: { sets: TCGSet[]; user: User | null; heatScores?: HeatScoreMap }) {
  const [sortKey, setSortKey]     = useState<SortKey>('date_released')
  const [sortDir, setSortDir]     = useState<'asc' | 'desc'>('desc')
  const [eraFilter, setEraFilter] = useState('All')
  const [search, setSearch]       = useState('')
  const [selected, setSelected]   = useState<TCGSet | null>(null)
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set())
  const [bought, setBought]       = useState<Set<string>>(new Set())
  const [loginNudge, setLoginNudge] = useState(false)
  const [momentum, setMomentum] = useState<MomentumMap>({})

  const isLoggedIn = !!user
  const isPremium  = user?.role === 'premium' || user?.role === 'admin'

  useEffect(() => {
    if (!isLoggedIn) return
    fetch('/api/watchlist', { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        if (data.watchlist) {
          setWatchlist(new Set(data.watchlist.map((i: {set_name: string}) => i.set_name)))
          setBought(new Set(
            data.watchlist
              .filter((i: {set_name: string; bought: boolean}) => i.bought)
              .map((i: {set_name: string}) => i.set_name)
          ))
        }
      })
      .catch(() => {})
  }, [isLoggedIn])

  useEffect(() => {
    // Fetch momentum for all sets in background — non-blocking
    const fetchAll = async () => {
      const results: MomentumMap = {}
      await Promise.allSettled(
        sets.map(async (s) => {
          try {
            const data = await fetch(`/api/internal?path=${encodeURIComponent('/api/sets/' + s.id + '/momentum')}`).then(r => r.json())
            results[s.id] = {
              d7_pct:  data?.bb?.d7_pct  ?? null,
              d30_pct: data?.bb?.d30_pct ?? null,
            }
          } catch {
            results[s.id] = null
          }
        })
      )
      setMomentum(results)
    }
    fetchAll()
  }, [sets])

  function handleRowClick(set: TCGSet) {
    if (!isLoggedIn) { setLoginNudge(true); return }
    setSelected(set)
  }

  async function handleWatchlist(e: React.MouseEvent, set: TCGSet) {
    e.stopPropagation()
    if (!isLoggedIn) { setLoginNudge(true); return }
    const inList = watchlist.has(set.name)
    if (inList) {
      const res = await fetch(`/api/watchlist/${encodeURIComponent(set.name)}`, { method: 'DELETE', credentials: 'include' })
      if (res.ok) {
        setWatchlist(prev => { const n = new Set(prev); n.delete(set.name); return n })
        setBought(prev => { const n = new Set(prev); n.delete(set.name); return n })
      }
    } else {
      if (!isPremium && watchlist.size >= 5) { alert('Free accounts can save up to 5 sets. Upgrade to Premium for unlimited.'); return }
      const res = await fetch(`/api/watchlist/${encodeURIComponent(set.name)}`, { method: 'POST', credentials: 'include' })
      if (res.ok) setWatchlist(prev => new Set([...prev, set.name]))
      else if (res.status === 403) alert('Free accounts can save up to 5 sets. Upgrade to Premium for unlimited.')
    }
  }

  async function handleBought(e: React.MouseEvent, set: TCGSet) {
    e.stopPropagation()
    if (!isLoggedIn) return
    const isBought = bought.has(set.name)
    if (isBought) {
      // Optimistic unmark
      setBought(prev => { const n = new Set(prev); n.delete(set.name); return n })
      const res = await fetch(`/api/watchlist/${encodeURIComponent(set.name)}/bought`, { method: 'DELETE', credentials: 'include' })
      if (!res.ok) setBought(prev => new Set([...prev, set.name])) // rollback
    } else {
      // Optimistic mark + remove star visually (watchlist stays in DB, just bought flag)
      setBought(prev => new Set([...prev, set.name]))
      const res = await fetch(`/api/watchlist/${encodeURIComponent(set.name)}/bought`, { method: 'POST', credentials: 'include' })
      if (!res.ok) setBought(prev => { const n = new Set(prev); n.delete(set.name); return n }) // rollback
    }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const filtered = useMemo(() => {
    return sets
      .filter(s => eraFilter === 'All' || s.era === eraFilter)
      .filter(s => !search || s.name.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => {
        if (sortKey === 'date_released') {
          const av = parseDateReleased(a.date_released)
          const bv = parseDateReleased(b.date_released)
          return sortDir === 'asc' ? av - bv : bv - av
        }
        const av = a[sortKey], bv = b[sortKey]
        if (av == null && bv == null) return 0
        if (av == null) return 1
        if (bv == null) return -1
        if (typeof av === 'string' && typeof bv === 'string')
          return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
        return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
      })
  }, [sets, sortKey, sortDir, eraFilter, search])

  function MomentumPill({ setId }: { setId: number }) {
    const m = momentum[setId]
    if (m === undefined) return <span className='text-slate-600 text-xs'>…</span>
    if (m === null) return <span className='text-slate-600 text-xs'>—</span>
    const fmt = (v: number | null) => {
      if (v === null) return '—'
      const sign = v > 0 ? '+' : ''
      return `${sign}${v.toFixed(1)}%`
    }
    const color7  = m.d7_pct  == null ? 'text-slate-500' : m.d7_pct  > 0 ? 'text-emerald-400' : m.d7_pct  < 0 ? 'text-red-400' : 'text-slate-400'
    const color30 = m.d30_pct == null ? 'text-slate-500' : m.d30_pct > 0 ? 'text-emerald-400' : m.d30_pct < 0 ? 'text-red-400' : 'text-slate-400'
    return (
      <div className='flex flex-col gap-0.5'>
        <span className={`text-xs font-medium ${color7}`}>{fmt(m.d7_pct)}</span>
        <span className={`text-xs ${color30}`}>{fmt(m.d30_pct)}</span>
      </div>
    )
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className='text-slate-600 ml-1'>&#x21D5;</span>
    return <span className='text-slate-300 ml-1'>{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
  }

  function Th({ col, label }: { col: SortKey; label: string }) {
    return (
      <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 select-none whitespace-nowrap' onClick={() => toggleSort(col)}>
        {label}<SortIcon col={col} />
      </th>
    )
  }

  const setSlug = (name: string) =>
    name.toLowerCase().replace(/s&v/gi, 'sandv').replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')

  return (
    <div>
      {loginNudge && (
        <div className='fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4' onClick={() => setLoginNudge(false)}>
          <div className='bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-sm w-full text-center' onClick={e => e.stopPropagation()}>
            <p className='text-2xl mb-3'>&#x1F512;</p>
            <h3 className='text-white font-bold text-lg mb-2'>Sign in to unlock</h3>
            <p className='text-slate-400 text-sm mb-5'>Create a free account to access set detail analysis, historical months, and your personal watchlist.</p>
            <a href='/auth/google' className='block w-full bg-white text-slate-900 font-medium py-2.5 rounded-lg hover:bg-slate-100 transition-colors mb-3'>Sign in with Google</a>
            <button onClick={() => setLoginNudge(false)} className='text-slate-500 text-sm hover:text-slate-300'>Maybe later</button>
          </div>
        </div>
      )}

      <div className='flex flex-wrap gap-3 mb-4'>
        <input type='text' placeholder='Search sets...' value={search} onChange={e => setSearch(e.target.value)}
          className='bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-500 w-full sm:w-48' />
        <select value={eraFilter} onChange={e => setEraFilter(e.target.value)}
          className='bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-500'>
          {ERA_OPTIONS.map(e => <option key={e}>{e}</option>)}
        </select>
        <span className='text-slate-500 text-sm self-center sm:ml-auto'>{filtered.length} of {sets.length} sets</span>
      </div>

      {isLoggedIn && !isPremium && watchlist.size > 0 && (
        <div className='mb-3 text-xs text-slate-500 flex items-center gap-2'>
          <span>&#x2605; {watchlist.size}/5 sets saved</span>
          {watchlist.size >= 4 && <a href='/premium' className='text-yellow-500 hover:text-yellow-400'>Upgrade for unlimited &#x2192;</a>}
        </div>
      )}

      {/* Premium upsell banner for non-premium users */}
      {!isPremium && (
        <div className='mb-4 flex items-center gap-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl px-4 py-3'>
          <span className='text-yellow-400 text-lg'>&#x1F512;</span>
          <p className='text-sm text-yellow-200/80 flex-1'>
            AI Scores and Buy/Sell Signals are available to{' '}
            <a href='/premium' className='text-yellow-400 font-semibold hover:text-yellow-300 underline underline-offset-2'>
              Premium members (£3/month)
            </a>.
          </p>
          <a href='/premium' className='shrink-0 text-xs font-semibold text-yellow-400 hover:text-yellow-300 whitespace-nowrap transition-colors'>
            Find out more &#x2192;
          </a>
        </div>
      )}

      {/* Mobile card view */}
      <div className='block sm:hidden space-y-3'>
        {filtered.map((set: TCGSet) => {
          const isStarred = watchlist.has(set.name)
          const isBought  = bought.has(set.name)
          const showCheck = isStarred || isBought
          return (
            <div key={set.id} className={'border rounded-xl p-4 transition-colors ' + (isBought ? 'bg-emerald-900/60 border-emerald-700/50' : isStarred ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-slate-900 border-slate-800')}>
              <div className='flex items-start justify-between gap-2 mb-3'>
                <div className='flex items-center gap-2 flex-1 min-w-0'>
                  {set.logo_url ? (
                    <img
                      src={set.logo_url}
                      alt={set.name + ' logo'}
                      loading='lazy'
                      width={56}
                      height={24}
                      className='object-contain h-6 w-14 shrink-0'
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                  ) : (
                    <div className='w-14 h-6 bg-slate-800 rounded shrink-0' />
                  )}
                  <div className='min-w-0'>
                    <Link href={'/sets/' + setSlug(set.name)} className='font-semibold text-white text-sm hover:text-blue-400 transition-colors block truncate'>
                      {set.name}
                    </Link>
                    <div className='text-slate-400 text-xs mt-0.5'>{set.era} &middot; {set.date_released || '\u2014'}</div>
                  </div>
                </div>
                <div className='flex items-center gap-3 shrink-0'>
                  <span onClick={e => handleWatchlist(e, set)} className={'text-xl cursor-pointer ' + (isStarred ? 'text-yellow-400' : 'text-slate-700')}>&#x2605;</span>
                  {showCheck && (
                    <span
                      onClick={e => handleBought(e, set)}
                      title={isBought ? 'Unmark as bought' : 'Mark as bought'}
                      className={'text-sm font-bold cursor-pointer transition-colors select-none px-1.5 py-0.5 rounded ' + (isBought ? 'text-emerald-300 bg-emerald-800/60' : 'text-emerald-500/60 hover:text-emerald-300 hover:bg-emerald-900/40')}
                    >&#x2713;</span>
                  )}
                </div>
              </div>
              <div className='flex items-center justify-between mb-3'>
                <div>
                  <div className='text-slate-500 text-xs mb-0.5'>BB Price</div>
                  <div className='text-white font-bold text-base'>{formatGBP(set.bb_price_gbp)}</div>
                </div>
                <div className='text-center'>
                  <div className='text-slate-500 text-xs mb-0.5'>Set Value</div>
                  <div className='text-slate-200 text-sm font-medium'>{formatGBP(set.set_value_gbp)}</div>
                </div>
                <div className='text-right'>
                  <div className='text-slate-500 text-xs mb-0.5'>Box %</div>
                  <span className={'text-xs font-medium px-2 py-0.5 rounded inline-block ' + boxPctColor(set.box_pct)}>{formatPct(set.box_pct)}</span>
                </div>
              </div>
              <div className='flex items-center gap-4 mb-3 px-1'>
                <div className='text-slate-500 text-xs shrink-0'>Momentum</div>
                {isPremium ? (
                  <MomentumPill setId={set.id} />
                ) : (
                  <div className='flex items-center gap-1.5'>
                    <div className='relative'>
                      <span className='blur-sm text-xs text-emerald-400 select-none'>+2.4%</span>
                    </div>
                    <a href='/premium' onClick={e => e.stopPropagation()} className='text-yellow-500/70 text-xs'>🔒 Premium</a>
                  </div>
                )}
              </div>
              {isPremium ? (
                <div className='flex items-center justify-between mb-3'>
                  <div>
                    <div className='text-slate-500 text-xs mb-0.5'>AI Score</div>
                    <span className={'text-xs font-bold px-2 py-1 rounded ' + scoreColor(set.decision_score)}>{set.decision_score ?? '\u2014'}</span>
                  </div>
                  <div className='text-right'>
                    <div className='text-slate-500 text-xs mb-0.5'>Signal</div>
                    <Badge className={'text-xs ' + recColor(set.recommendation)}>{set.recommendation ?? '\u2014'}</Badge>
                  </div>
                </div>
              ) : (
                <div className='mb-3'>
                  <a href='/premium' className='flex items-center justify-center gap-2 w-full text-xs font-semibold text-yellow-400 hover:text-yellow-300 py-2 rounded-lg border border-yellow-500/30 hover:border-yellow-500/60 bg-yellow-500/5 hover:bg-yellow-500/10 transition-colors'>
                    &#x1F512; Find out more &#x2192;
                  </a>
                </div>
              )}
              <div className='flex gap-2 pt-2 border-t border-slate-800'>
                <Link href={'/sets/' + setSlug(set.name)} className='flex-1 text-center text-xs text-slate-400 hover:text-white py-1.5 rounded-lg border border-slate-800 hover:border-slate-600 transition-colors'>
                  View page &#x2192;
                </Link>
                {isLoggedIn ? (
                  <button onClick={() => handleRowClick(set)} className='flex-1 text-center text-xs text-blue-400 hover:text-white py-1.5 rounded-lg border border-blue-500/20 hover:border-blue-500/50 transition-colors'>
                    Price history &#x2192;
                  </button>
                ) : (
                  <button onClick={() => setLoginNudge(true)} className='flex-1 text-center text-xs text-yellow-500/60 hover:text-yellow-400 py-1.5 rounded-lg border border-yellow-500/20 hover:border-yellow-500/40 transition-colors'>
                    &#x1F512; History &amp; analysis
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Desktop table */}
      <div className='hidden sm:block bg-slate-900 rounded-xl border border-slate-800 overflow-hidden'>
        <div className='overflow-x-auto'>
          <table className='w-full'>
            <thead className='border-b border-slate-800'>
              <tr>
                <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider w-16'>&#x2605;</th>
                <Th col='name' label='Set' />
                <Th col='bb_price_gbp' label='BB Price' />
                <Th col='set_value_gbp' label='Set Value' />
                <Th col='box_pct' label='Box %' />
                <Th col='chase_pct' label='Chase %' />
                <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap'>
                  <div>7d %</div>
                  <div className='text-slate-600 font-normal normal-case tracking-normal'>30d %</div>
                </th>
                {isPremium && (
                  <>
                    <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap'>AI Score</th>
                    <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap'>Buy/Sell Signal</th>
                    <th className='px-3 py-3 text-left text-xs font-medium text-orange-400/80 uppercase tracking-wider whitespace-nowrap'>🔥 Heat</th>
                  </>
                )}
                {!isPremium && (
                  <>
                    <th className='px-3 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap'></th>
                    <th className='px-3 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider whitespace-nowrap'>🔥 Heat</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody className='divide-y divide-slate-800'>
              {filtered.map((set: TCGSet) => {
                const isStarred = watchlist.has(set.name)
                const isBought  = bought.has(set.name)
                const showCheck = isStarred || isBought
                return (
                  <tr key={set.id} className={'hover:bg-slate-800/60 cursor-pointer transition-colors ' + (isBought ? 'bg-emerald-900/60' : isStarred ? 'bg-yellow-500/10' : '')} onClick={() => handleRowClick(set)}>
                    <td className='px-3 py-3' onClick={e => e.stopPropagation()}>
                      <div className='flex items-center gap-2'>
                        <span
                          onClick={e => handleWatchlist(e, set)}
                          className={'text-lg leading-none transition-colors cursor-pointer ' + (isStarred ? 'text-yellow-400' : 'text-slate-700 hover:text-slate-400')}
                        >&#x2605;</span>
                        {showCheck && (
                          <span
                            onClick={e => handleBought(e, set)}
                            title={isBought ? 'Unmark as bought' : 'Mark as bought'}
                            className={'text-sm font-bold leading-none transition-colors cursor-pointer select-none px-1 py-0.5 rounded ' + (isBought ? 'text-emerald-300 bg-emerald-800/60' : 'text-emerald-500/60 hover:text-emerald-300 hover:bg-emerald-900/40')}
                          >&#x2713;</span>
                        )}
                      </div>
                    </td>
                    <td className='px-3 py-3'>
                      <div className='flex items-center gap-3'>
                        {set.logo_url ? (
                          <img
                            src={set.logo_url}
                            alt={set.name + ' Pokemon TCG set logo'}
                            loading='lazy'
                            width={64}
                            height={28}
                            className='object-contain h-7 w-16 shrink-0'
                            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                          />
                        ) : (
                          <div className='w-16 h-7 bg-slate-800 rounded shrink-0' />
                        )}
                        <div className='min-w-0 overflow-hidden'>
                          <Link href={'/sets/' + setSlug(set.name)} className='font-medium text-white text-sm hover:text-blue-400 transition-colors block truncate max-w-[180px]' onClick={e => e.stopPropagation()} title={set.name}>
                            {set.name}
                          </Link>
                          <div className='text-slate-500 text-xs mt-0.5'>{set.era} &middot; {set.date_released || '\u2014'}</div>
                        </div>
                      </div>
                    </td>
                    <td className='px-3 py-3 text-slate-200 text-sm font-medium whitespace-nowrap'>{formatGBP(set.bb_price_gbp)}</td>
                    <td className='px-3 py-3 text-slate-200 text-sm'>{formatGBP(set.set_value_gbp)}</td>
                    <td className='px-3 py-3'>
                      <span className={'text-xs font-medium px-2 py-1 rounded ' + boxPctColor(set.box_pct)}>{formatPct(set.box_pct)}</span>
                    </td>
                    <td className='px-3 py-3 text-slate-300 text-sm'>{formatRatio(set.chase_pct)}</td>
                    <td className='px-3 py-3'>
                      {isPremium ? (
                        <MomentumPill setId={set.id} />
                      ) : (
                        <div className='relative select-none' title='Premium feature'>
                          <div className='blur-sm pointer-events-none text-xs font-medium text-emerald-400'>
                            <div>+2.4%</div>
                            <div className='text-slate-400'>-1.1%</div>
                          </div>
                          <div className='absolute inset-0 flex items-center justify-center'>
                            <span className='text-yellow-500/70 text-xs'>🔒</span>
                          </div>
                        </div>
                      )}
                    </td>
                    {isPremium ? (
                      <>
                        <td className='px-3 py-3'>
                          <span className={'text-xs font-bold px-2 py-1 rounded ' + scoreColor(set.decision_score)}>{set.decision_score ?? '\u2014'}</span>
                        </td>
                        <td className='px-3 py-3'>
                          <Badge className={'text-xs ' + recColor(set.recommendation)}>{set.recommendation ?? '\u2014'}</Badge>
                        </td>
                        <td className='px-3 py-3'>
                          {heatScores[String(set.id)] ? (
                            <span className='text-xs font-bold text-orange-300 px-2 py-1 rounded bg-orange-950/60 border border-orange-700/40'>
                              {heatScores[String(set.id)]!.heat_score.toFixed(0)}
                            </span>
                          ) : (
                            <span className='text-slate-600 text-xs'>—</span>
                          )}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className='px-3 py-3'>
                          <a href='/premium' onClick={e => e.stopPropagation()}
                            className='inline-flex items-center gap-1.5 text-xs font-semibold text-yellow-400 hover:text-yellow-300 px-3 py-1.5 rounded-lg border border-yellow-500/30 hover:border-yellow-500/60 bg-yellow-500/5 hover:bg-yellow-500/10 transition-colors whitespace-nowrap'>
                            &#x1F512; Find out more &#x2192;
                          </a>
                        </td>
                        <td className='px-3 py-3'>
                          <div className='relative select-none' title='Premium feature — Heat Score'>
                            <span className='text-xs font-bold text-orange-900 blur-sm pointer-events-none px-2 py-1 rounded bg-orange-950/40'>77</span>
                            <div className='absolute inset-0 flex items-center justify-center'>
                              <span className='text-yellow-500/60 text-xs'>🔒</span>
                            </div>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      {selected && <SetDetailPanel set={selected} onClose={() => setSelected(null)} user={user} />}
    </div>
  )
}
