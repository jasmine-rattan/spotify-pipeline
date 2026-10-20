import React, { useEffect, useState } from 'react'

interface RankRow {
  rank: string
  issue_id: string
  complaint_count: string
  severity_sum: string
  mean_severity: string
  priority_score: string
}

interface IssueRow {
  issue_id: string
  issue_name: string
  complaint_count: string
}

export default function Rankings() {
  const [ranking, setRanking] = useState<RankRow[]>([])
  const [issues, setIssues] = useState<IssueRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/ranking').then(r => r.json()),
      fetch('/api/issues').then(r => r.json()),
    ]).then(([rankData, issueData]) => {
      setRanking(rankData)
      setIssues(issueData)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const issueNames: Record<string, string> = {}
  for (const issue of issues) {
    issueNames[issue.issue_id] = issue.issue_name
  }

  if (loading) return <p>Loading rankings...</p>
  if (!ranking.length) return <p>No ranking data yet. Run the pipeline first.</p>

  return (
    <div>
      <h2>Issue Rankings</h2>
      <p style={{ color: '#666' }}>Ordered by priority score (severity_sum), descending. All 8 issue groups shown.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr style={{ background: '#1db954', color: '#fff' }}>
            <th style={th}>Rank</th>
            <th style={th}>Issue</th>
            <th style={th}>Display Name</th>
            <th style={th}>Complaints</th>
            <th style={th}>Severity Sum</th>
            <th style={th}>Mean Severity</th>
            <th style={th}>Priority Score</th>
          </tr>
        </thead>
        <tbody>
          {ranking.map((row, i) => (
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

const th: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'left',
  fontWeight: 'bold',
  fontSize: 14,
}

const td: React.CSSProperties = {
  padding: '9px 12px',
  borderBottom: '1px solid #eee',
  fontSize: 14,
}
