import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './BoothDashboard.css'

interface DashboardData {
  officer_name: string
  badge_number: string
  booth_id: string
  constituency: string
  total_registered: number
  votes_cast: number
  rejected_today: number
  remaining: number
  recent_activity: Activity[]
}

interface Activity {
  voter_id: string
  result: string
  timestamp: string
  match_score: number
  is_biometric_exempt: boolean
}

export default function BoothDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    fetchDashboard()
    const timer = setInterval(() => {
      setCurrentTime(new Date())
      fetchDashboard()
    }, 30000)
    return () => clearInterval(timer)
  }, [])

  const fetchDashboard = async () => {
    const token = localStorage.getItem('booth_token')
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/booth/dashboard/', {
        headers: { Authorization: `Token ${token}` }
      })
      setData(res.data)
    } catch {
      navigate('/booth/login')
    }
  }

  const handleLogout = async () => {
    const token = localStorage.getItem('booth_token')
    await axios.post('http://127.0.0.1:8000/api/booth/logout/', {}, {
      headers: { Authorization: `Token ${token}` }
    })
    localStorage.removeItem('booth_token')
    localStorage.removeItem('booth_officer')
    navigate('/booth/login')
  }

  const getResultLabel = (result: string) => {
    switch (result) {
      case 'approved': return { label: 'APPROVED', cls: 'result-approved' }
      case 'rejected_no_match': return { label: 'REJECTED', cls: 'result-rejected' }
      case 'rejected_already_voted': return { label: 'REJECTED', cls: 'result-rejected' }
      default: return { label: result.toUpperCase(), cls: 'result-rejected' }
    }
  }

  const getResultReason = (activity: Activity) => {
    if (activity.is_biometric_exempt) return 'OTP Fallback'
    switch (activity.result) {
      case 'approved': return 'Biometric'
      case 'rejected_already_voted': return 'Duplicate Vote'
      case 'rejected_no_match': return 'Fingerprint Mismatch'
      default: return activity.result
    }
  }

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  })

  const turnoutPct = data ? Math.round((data.votes_cast / Math.max(data.total_registered, 1)) * 100) : 0

  return (
    <div className="booth-dash-page">
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
        <a href="#" className="active">Booth Dashboard</a>
        <a href="#" onClick={() => navigate('/booth/verify')}>Voter Verification</a>
        <a href="#" onClick={() => navigate('/booth/reports')}>Reports</a>
        <button className="booth-logout-btn" onClick={handleLogout}>Logout</button>
      </nav>

      {/* Status bar */}
      <div className="booth-status-bar">
        <span>📍 Booth: {data?.booth_id || '—'}</span>
        <span>🏛 {data?.constituency} Assembly Constituency</span>
        <span>👤 Officer: {data?.officer_name || '—'}</span>
        <span>🗳 Votes Cast: {data?.votes_cast || 0}/{data?.total_registered || 0}</span>
        <span className="live-indicator">● LIVE</span>
      </div>

      <main className="booth-dash-main">
        {/* Booth info */}
        <div className="booth-info-row">
          <div>
            <h2 className="booth-name">Booth {data?.booth_id}</h2>
            <p className="booth-sub">Officer: {data?.officer_name} ({data?.badge_number})</p>
          </div>
          <div className="polling-status-badge">
            🗳 POLLING IN PROGRESS
          </div>
        </div>

        <p className="update-note">Updates every 30s</p>

        {/* Stats */}
        <div className="booth-stats-grid">
          <div className="booth-stat-card">
            <div className="booth-stat-top">
              <span className="booth-stat-label">TOTAL REGISTERED</span>
              <span className="booth-stat-icon">◈</span>
            </div>
            <div className="booth-stat-value">{data?.total_registered || 0}</div>
            <div className="booth-stat-sub">At this booth</div>
          </div>

          <div className="booth-stat-card stat-green-border">
            <div className="booth-stat-top">
              <span className="booth-stat-label">VOTES CAST</span>
              <span className="booth-stat-icon">✓</span>
            </div>
            <div className="booth-stat-value">{data?.votes_cast || 0}</div>
            <div className="booth-stat-sub">{turnoutPct}% turnout</div>
            <div className="booth-progress-bar">
              <div className="booth-progress-fill" style={{width: `${turnoutPct}%`}}></div>
            </div>
          </div>

          <div className="booth-stat-card">
            <div className="booth-stat-top">
              <span className="booth-stat-label">REMAINING</span>
              <span className="booth-stat-icon">◷</span>
            </div>
            <div className="booth-stat-value">{data?.remaining || 0}</div>
            <div className="booth-stat-sub">Yet to vote</div>
          </div>

          <div className="booth-stat-card stat-red-border">
            <div className="booth-stat-top">
              <span className="booth-stat-label">REJECTED TODAY</span>
              <span className="booth-stat-icon">✕</span>
            </div>
            <div className="booth-stat-value">{data?.rejected_today || 0}</div>
            <div className="booth-stat-sub">Fraud flags raised</div>
          </div>
        </div>

        {/* Start verification CTA */}
        <div className="start-verification-card" onClick={() => navigate('/booth/verify')}>
          <div className="start-icon">▶</div>
          <h3>Start Voter Verification</h3>
          <p>Click here when next voter arrives at the booth</p>
          <span className="start-sub">→ Proceed to Identity Check   →</span>
        </div>

        {/* Recent activity + Report */}
        <div className="booth-bottom-grid">
          <div className="activity-card">
            <div className="activity-header">
              <h3>Recent Activity</h3>
              <span className="privacy-note">Privacy: voter names hidden</span>
            </div>
            {!data?.recent_activity?.length ? (
              <div className="no-activity">No activity yet today.</div>
            ) : (
              data.recent_activity.map((a, i) => {
                const { label, cls } = getResultLabel(a.result)
                return (
                  <div key={i} className="activity-row">
                    <span className="activity-time">{a.timestamp}</span>
                    <span className="activity-reason">{getResultReason(a)}</span>
                    <span className={`activity-result ${cls}`}>{label}</span>
                  </div>
                )
              })
            )}
          </div>

          <div className="report-card">
            <div className="report-icon">⚠</div>
            <h3>Report an Issue</h3>
            <p>Scanner problems, suspicious activity, or voter complaints</p>
            <button className="report-btn">Report Issue   →</button>
          </div>
        </div>
      </main>

      <footer className="booth-footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>🔒 All booth activity is encrypted and logged</span>
        <span>Booth ID: {data?.booth_id}</span>
      </footer>
    </div>
  )
}