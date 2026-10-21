import React, { useState } from 'react'
import { RANKING, ISSUE_NAMES } from '../data'

type SortKey = 'rank' | 'complaint_count' | 'severity_sum' | 'mean_severity' | 'priority_score'

export default function Rankings() {
  const [sortKey, setSortKey] = useState<SortKey>('rank')
  const [sortAsc, setSortAsc] = useState(true)

  const sorted = [...RANKING].sort((a, b) => {
    const av = sortKey === 'mean_severity' ? parseFloat(a[sortKey]) : parseInt(a[sortKey])
    const bv = sortKey === 'mean_severity' ? parseFloat(b[sortKey]) : parseInt(b[sortKey])
    return sortAsc ? av - bv : bv - av
  })

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(key === 'rank') }
  }

  const thStyle = (key: SortKey): React.CSSProperties => ({
    padding: '10px 12px',
    textAlign: 'left',
    fontWeight: 'bold',
    fontSize: 14,
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
  })

  const arrow = (key: SortKey) => sortKey === key ? (sortAsc ? ' ▲' : ' ▼') : ''

  return (
    <div>
      <h2>Issue Rankings</h2>
      <p style={{ color: '#666' }}>Ordered by priority score (severity_sum). Click column headers to sort.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr style={{ background: '#1db954', color: '#fff' }}>
            <th style={thStyle('rank')} onClick={() => handleSort('rank')}>Rank{arrow('rank')}</th>
            <th style={{ ...thStyle('rank'), cursor: 'default' }}>Issue</th>
            <th style={{ ...thStyle('rank'), cursor: 'default' }}>Display Name</th>
            <th style={thStyle('complaint_count')} onClick={() => handleSort('complaint_count')}>Complaints{arrow('complaint_count')}</th>
            <th style={thStyle('severity_sum')} onClick={() => handleSort('severity_sum')}>Severity Sum{arrow('severity_sum')}</th>
            <th style={thStyle('mean_severity')} onClick={() => handleSort('mean_severity')}>Mean Severity{arrow('mean_severity')}</th>
            <th style={thStyle('priority_score')} onClick={() => handleSort('priority_score')}>Priority Score{arrow('priority_score')}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.issue_id} style={{ background: i % 2 === 0 ? '#fff' : '#f8f8f8' }}>
              <td style={td}>{row.rank}</td>
              <td style={{ ...td, fontFamily: 'monospace', fontSize: 13 }}>{row.issue_id}</td>
              <td style={td}>{ISSUE_NAMES[row.issue_id] ?? row.issue_id}</td>
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

const td: React.CSSProperties = {
  padding: '9px 12px',
  borderBottom: '1px solid #eee',
  fontSize: 14,
}
