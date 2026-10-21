import React, { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { METRICS as STATIC_METRICS } from '../data'

const TOPIC_COLORS: Record<string, string> = {
  playback: '#e74c3c', usability: '#e67e22', billing: '#f39c12',
  access: '#3498db', downloads: '#9b59b6', catalog: '#1abc9c',
  support: '#2ecc71', other: '#95a5a6',
}

export default function Overview() {
  const [metrics, setMetrics] = useState(STATIC_METRICS)

  useEffect(() => {
    fetch('/api/metrics')
      .then(r => r.json())
      .then(d => { if (d && d.total) setMetrics(d) })
      .catch(() => {}) // silently use static fallback
  }, [])

  const topicData = Object.entries(metrics.topic_counts)
    .map(([topic, count]) => ({ topic, count }))
    .sort((a, b) => b.count - a.count)

  const intentData = Object.entries(metrics.intent_counts)
    .map(([intent, count]) => ({ intent, count }))
    .sort((a, b) => b.count - a.count)

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
        {[
          { label: 'Total Reviews', value: metrics.total.toLocaleString() },
          { label: 'Classified', value: metrics.completed.toLocaleString() },
          { label: 'Quarantined', value: metrics.quarantined.toLocaleString() },
          { label: 'Cache Hits (dedup)', value: metrics.cache_hits.toLocaleString() },
          { label: 'Cache Hit Rate', value: `${((metrics.cache_hits / metrics.completed) * 100).toFixed(1)}%` },
          { label: 'Topics', value: Object.keys(metrics.topic_counts).length.toString() },
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
          <YAxis tickFormatter={(v) => (v/1000).toFixed(0)+'K'} />
          <Tooltip formatter={(v: number) => v.toLocaleString()} />
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
          <YAxis tickFormatter={(v) => (v/1000).toFixed(0)+'K'} />
          <Tooltip formatter={(v: number) => v.toLocaleString()} />
          <Bar dataKey="count" fill="#3498db" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
