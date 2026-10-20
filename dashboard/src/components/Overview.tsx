import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface Metrics {
  total: number
  completed: number
  quarantined: number
  topic_counts: Record<string, number>
  intent_counts: Record<string, number>
}

const TOPIC_COLORS: Record<string, string> = {
  playback: '#e74c3c',
  usability: '#e67e22',
  billing: '#f39c12',
  access: '#3498db',
  downloads: '#9b59b6',
  catalog: '#1abc9c',
  support: '#2ecc71',
  other: '#95a5a6',
}

export default function Overview() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/metrics')
      .then(r => r.json())
      .then(d => { setMetrics(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading metrics...</p>
  if (!metrics || !metrics.total) return <p>No data yet. Run the pipeline first.</p>

  const topicData = Object.entries(metrics.topic_counts || {})
    .map(([topic, count]) => ({ topic, count }))
    .sort((a, b) => b.count - a.count)

  const intentData = Object.entries(metrics.intent_counts || {})
    .map(([intent, count]) => ({ intent, count }))
    .sort((a, b) => b.count - a.count)

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { label: 'Total Reviews', value: metrics.total?.toLocaleString() ?? '—' },
          { label: 'Completed', value: metrics.completed?.toLocaleString() ?? '—' },
          { label: 'Quarantined', value: metrics.quarantined?.toLocaleString() ?? '—' },
          { label: 'Cache Hits', value: ((metrics.total ?? 0) - (metrics.completed ?? 0) - (metrics.quarantined ?? 0)).toLocaleString() },
          { label: 'Completion Rate', value: metrics.total ? `${((metrics.completed / metrics.total) * 100).toFixed(2)}%` : '—' },
          { label: 'Topics', value: Object.keys(metrics.topic_counts ?? {}).length.toString() },
        ].map(card => (
          <div key={card.label} style={{ background: '#f8f8f8', borderRadius: 8, padding: 16 }}>
            <div style={{ fontSize: 13, color: '#888' }}>{card.label}</div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1db954' }}>{card.value}</div>
          </div>
        ))}
      </div>

      <h2>Reviews by Topic</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={topicData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
          <XAxis dataKey="topic" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count">
            {topicData.map(entry => (
              <Cell key={entry.topic} fill={TOPIC_COLORS[entry.topic] ?? '#1db954'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <h2 style={{ marginTop: 32 }}>Reviews by Intent</h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={intentData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
          <XAxis dataKey="intent" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" fill="#3498db" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
