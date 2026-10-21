import React from 'react'
import ReactMarkdown from 'react-markdown'
import { MEMO } from '../data'

export default function Memo() {
  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{
        background: '#f8f8f8',
        borderRadius: 8,
        padding: '8px 16px',
        marginBottom: 20,
        fontSize: 13,
        color: '#666',
        borderLeft: '3px solid #1db954',
      }}>
        AI-generated product memo by Claude Haiku (claude-haiku-4-5-20251001).
        Claim IDs (e.g. claim-001) are traceable to <code>grading/claims.csv</code>.
      </div>
      <div style={{ lineHeight: 1.7 }}>
        <ReactMarkdown>{MEMO}</ReactMarkdown>
      </div>
    </div>
  )
}
