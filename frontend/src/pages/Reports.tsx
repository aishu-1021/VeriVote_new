import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './Reports.css'

interface FraudAlert {
  id: number
  alert_type: string
  alert_type_display: string
  voter_id: string
  booth_id: string
  description: string
  severity: 'low' | 'medium' | 'high'
  is_resolved: boolean
  created_at: string
}

export default function Reports() {
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState<FraudAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'low' | 'unresolved'>('all')
  const [currentTime, setCurrentTime] = useState(new Date())

  const officer = JSON.parse(localStorage.getItem('booth_officer') || '{}')
  const token = localStorage.getItem('booth_token')
  const headers = { Authorization: `Token ${token}` }

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    fetchAlerts()
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAlerts, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchAlerts = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/fraud/alerts/', { headers })
      setAlerts(res.data)
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  const resolveAlert = async (id: number) => {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/fraud/alerts/${id}/resolve/`, {}, { headers })
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, is_resolved: true } : a))
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  const filtered = alerts.filter(a => {
    if (filter === 'all') return true
    if (filter === 'unresolved') return !a.is_resolved
    return a.severity === filter
  })

  const counts = {
    total: alerts.length,
    high: alerts.filter(a => a.severity === 'high').length,
    unresolved: alerts.filter(a => !a.is_resolved).length,
  }

  const severityColor = (s: string) => {
    if (s === 'high') return '#dc2626'
    if (s === 'medium') return '#d97706'
    return '#16a34a'
  }

  const alertIcon = (type: string) => {
    if (type === 'duplicate_vote') return '🔁'
    if (type === 'fingerprint_mismatch') return '👆'
    if (type === 'duplicate_aadhaar') return '🪪'
    if (type === 'dead_voter') return '⚠️'
    if (type === 'cross_constituency') return '📍'
    return '🚨'
  }

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  })

  return (
    <div className="booth-verify-page">
      {/* Top bar */}
      <div className="booth-top-bar">
        <span>Government of India - Election Commission of India</span>
        <div className="polling-live-badge">
          <span className="live-dot"></span> POLLING LIVE
        </div>
        <span>{currentTime.toLocaleTimeString('en-IN')}</span>
      </div>

      {/* Header */}
      <header className="booth-header">
        <div className="booth-header-left">
          <div className="ashoka-chakra">⊕</div>
          <div>
            <h1 className="booth-site-title">VeriVote</h1>
            <p className="booth-site-subtitle">Polling Booth Interface - Election Day</p>
          </div>
        </div>
        <div className="booth-header-right">
          <div className="booth-date">{today}</div>
          <div className="booth-election">General Elections 2026</div>
        </div>
      </header>

      {/* Nav */}
      <nav className="booth-navbar">
        <a href="#" onClick={() => navigate('/booth/dashboard')}>Booth Dashboard</a>
        <a href="#" onClick={() => navigate('/booth/verify')}>Voter Verification</a>
        <a href="#" className="active">Reports</a>
        <button className="booth-logout-btn" onClick={() => navigate('/booth/dashboard')}>← Dashboard</button>
      </nav>

      {/* Status bar */}
      <div className="booth-status-bar">
        <span>📍 Booth: {officer.booth_id}</span>
        <span>🏛 {officer.constituency} Assembly Constituency</span>
        <span>👤 Officer: {officer.name}</span>
        <span className="live-indicator">● LIVE</span>
      </div>

      {/* Main content */}
      <main className="verify-main">
        <div className="verify-header">
          <div>
            <h2 className="verify-title">Fraud & Alert Reports</h2>
            <p className="verify-sub">Auto-updated every 30 seconds - all flagged events at this booth</p>
          </div>
        </div>

        {/* Summary cards */}
        <div className="reports-summary-row">
          <div className="reports-summary-card">
            <div className="reports-summary-number">{counts.total}</div>
            <div className="reports-summary-label">Total Alerts</div>
          </div>
          <div className="reports-summary-card reports-summary-danger">
            <div className="reports-summary-number">{counts.high}</div>
            <div className="reports-summary-label">High Severity</div>
          </div>
          <div className="reports-summary-card reports-summary-warn">
            <div className="reports-summary-number">{counts.unresolved}</div>
            <div className="reports-summary-label">Unresolved</div>
          </div>
        </div>

        {/* Filter buttons */}
        <div className="reports-filter-row">
          {(['all', 'unresolved', 'high', 'medium', 'low'] as const).map(f => (
            <button
              key={f}
              className={`reports-filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Alert list */}
        {loading ? (
          <div className="verify-card" style={{ textAlign: 'center', padding: '2rem' }}>
            Loading alerts...
          </div>
        ) : filtered.length === 0 ? (
          <div className="verify-card" style={{ textAlign: 'center', padding: '2rem' }}>
            <div style={{ fontSize: '2rem' }}>✅</div>
            <p style={{ marginTop: '0.5rem', color: '#6b7280' }}>No alerts in this category.</p>
          </div>
        ) : (
          <div className="reports-alert-list">
            {filtered.map(alert => (
              <div
                key={alert.id}
                className={`reports-alert-card ${alert.is_resolved ? 'resolved' : ''}`}
              >
                <div className="reports-alert-left">
                  <span className="reports-alert-icon">{alertIcon(alert.alert_type)}</span>
                  <div>
                    <div className="reports-alert-type">{alert.alert_type_display}</div>
                    <div className="reports-alert-desc">{alert.description}</div>
                    <div className="reports-alert-meta">
                      <span>Voter: {alert.voter_id}</span>
                      {alert.booth_id && <span>Booth: {alert.booth_id}</span>}
                      <span>{alert.created_at}</span>
                    </div>
                  </div>
                </div>
                <div className="reports-alert-right">
                  <span
                    className="reports-severity-badge"
                    style={{ background: severityColor(alert.severity) }}
                  >
                    {alert.severity.toUpperCase()}
                  </span>
                  {!alert.is_resolved ? (
                    <button
                      className="reports-resolve-btn"
                      onClick={() => resolveAlert(alert.id)}
                    >
                      Mark Resolved
                    </button>
                  ) : (
                    <span className="reports-resolved-tag">✓ Resolved</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="booth-footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>🔒 All booth activity is encrypted and logged</span>
        <span>Booth ID: {officer.booth_id}</span>
      </footer>
    </div>
  )
}