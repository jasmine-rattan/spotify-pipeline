import React, { useEffect, useState } from 'react'
import { RANKING as STATIC_RANKING, ISSUE_NAMES as STATIC_NAMES } from '../data'

type SortKey = 'rank' | 'complaint_count' | 'severity_sum' | 'mean_severity' | 'priority_score'

export default function Rankings() {
  const [ranking, setRanking] = useState(STATIC_RANKING)
  const [issueNames, setIssueNames] = useState(STATIC_NAMES)
  const [sortKey, setSortKey] = useState<SortKey>('rank')
  const [sortAsc, setSortAsc] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/ranking').then(r => r.json()).catch(() => null),
      fetch('/api/issues').then(r => r.json()).catch(() => null),
    ]).then(([rankData, issueData]) => {
      if (rankData && rankData.length) setRanking(rankData)
      if (issueData && issueData.length) {
        const names: Record<string,string> = {}
        for (const row of issueData) names[row.issue_id] = row.issue_name
        setIssueNames(names)
      }
    })
  }, [])

  const sorted = [...ranking].sort((a, b) => {
    const av = sortKey === 'mean_severity' ? parseFloat(a[sortKey]) : parseInt(a[sortKey])
    const bv = sortKey === 'mean_severity' ? parseFloat(b[sortKey]) : parseInt(b[sortKey])
    return sortAsc ? av - bv : bv - av
  })

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(key === 'rank') }
  }

  const arrow = (key: SortKey) => sortKey === key ? (sortAsc ? ' ▲' : ' ▼') : ''

  return (
    <div>
      <h2>Issue Rankings</h2>
      <p style={{ color: '#666' }}>Ordered by priority score (severity_sum). Click headers to sort.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr style={{ background: '#1db954', color: '#fff' }}>
            {(['rank','issue_id','name','complaint_count','severity_sum','mean_severity','priority_score'] as const).map((col) => (
              <th key={col}
                onClick={() => col !== 'issue_id' && col !== 'name' ? handleSort(col as SortKey) : null}
                style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 'bold', fontSize: 14,
                         cursor: ['rank','complaint_count','severity_sum','mean_severity','priority_score'].includes(col) ? 'pointer' : 'default', whiteSpace: 'nowrap' }}>
                {col === 'name' ? 'Display Name' : col.replace(/_/g,' ')}{arrow(col as SortKey)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.issue_id} style={{ background: i % 2 === 0 ? '#fff' : '#f8f8f8' }}>
              <td style={td}>{row.rank}</td>
              <td style={{ ...td, fontFamily: 'monospace', fontSize: 13 }}>{row.issue_id}</td>
              <td style={td}>{issueNames[row.issue_id] ?? row.issue_id}</td>
              <td style={{ ...td, textAlign: 'right' }}>{parseInt(row.complaint_count).toLocaleString()}</td>
              <td style={{ ...td, textAlign: 'right' }}>{parseInt(row.severity_sum).toLocaleString()}</td>
              <td style={{ ...td, textAlign: 'right' }}>{row.mean_severity}</td>
              <td style={{ ...td, textAlign: 'right', fontWeight: 'bold' }}>{parseInt(row.priority_score).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
const td: React.CSSProperties = { padding: '9px 12px', borderBottom: '1px solid #eee', fontSize: 14 }
