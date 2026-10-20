import React, { useState } from 'react'
import Overview from './components/Overview'
import Rankings from './components/Rankings'
import Memo from './components/Memo'

const TABS = ['Overview', 'Rankings', 'Memo'] as const
type Tab = typeof TABS[number]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('Overview')

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 1100, margin: '0 auto', padding: '0 20px' }}>
      <header style={{ borderBottom: '2px solid #1db954', paddingBottom: 12, marginBottom: 24 }}>
        <h1 style={{ color: '#1db954', margin: 0 }}>Spotify Review Pipeline</h1>
        <p style={{ color: '#666', margin: '4px 0 0' }}>660,622 reviews · 6-stage multi-agent analysis</p>
      </header>

      <nav style={{ marginBottom: 24, display: 'flex', gap: 8 }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 20px',
              borderRadius: 6,
              border: 'none',
              cursor: 'pointer',
              background: activeTab === tab ? '#1db954' : '#eee',
              color: activeTab === tab ? '#fff' : '#333',
              fontWeight: activeTab === tab ? 'bold' : 'normal',
              fontSize: 15,
            }}
          >
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === 'Overview' && <Overview />}
      {activeTab === 'Rankings' && <Rankings />}
      {activeTab === 'Memo' && <Memo />}
    </div>
  )
}
