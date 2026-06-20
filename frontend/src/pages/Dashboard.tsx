import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import './Dashboard.css'

interface DashboardStats {
  officer_name: string
  constituency: string
  badge_number: string
  enrollments_today: number
  pending_today: number
  rejected_today: number
  total_this_week: number
  recent_enrollments: RecentEnrollment[]
}

interface RecentEnrollment {
  voter_id: string
  full_name: string
  assembly_constituency: string
  created_at: string
  status: string
  status_display: string
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const res = await api.get('/voters/dashboard/')
      setStats(res.data)
    } catch (err: any) {
      if (err.response?.status === 401) {
        navigate('/login')
      } else {
        setError('Failed to load dashboard.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await api.post('/voters/logout/')
    localStorage.removeItem('officer')
    navigate('/login')
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good Morning'
    if (hour < 17) return 'Good Afternoon'
    return 'Good Evening'
  }

  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
  }

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'enrolled': return 'status-enrolled'
      case 'pending': return 'status-pending'
      case 'rejected': return 'status-rejected'
      default: return ''
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'enrolled': return '✅ Enrolled'
      case 'pending': return '⏳ Pending'
      case 'rejected': return '❌ Rejected'
      default: return status
    }
  }

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  })

  if (loading) return (
    <div className="dashboard-loading">
      <div className="spinner"></div>
      <p>Loading dashboard...</p>
    </div>
  )

  if (error) return (
    <div className="dashboard-loading">
      <p style={{color: 'red'}}>{error}</p>
    </div>
  )

  return (
    <div className="dashboard-page">

      {/* Top bar */}
      <div className="top-bar">
        <span>Government of India - Election Commission of India</span>
        <span>Help | Contact | English ▾</span>
      </div>

      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="ashoka-wheel">⊕</div>
          <div>
            <h1 className="site-title">VeriVote</h1>
            <p className="site-subtitle">National Voter Registration Portal</p>
          </div>
        </div>
        <div className="header-right">
          <span className="officer-badge">
            {stats?.officer_name} | Booth KA-04
          </span>
        </div>
      </header>

      {/* Nav */}
      <nav className="navbar">
        <a href="#" className="active">Enrollment</a>
        <a href="#">Help</a>
        <button className="logout-btn" onClick={handleLogout}>Logout</button>
      </nav>

      {/* Main */}
      <main className="dashboard-main">

        {/* Welcome row */}
        <div className="welcome-row">
          <div>
            <h2 className="welcome-title">
              {getGreeting()}, {stats?.officer_name?.split(' ')[0]}
            </h2>
            <p className="welcome-sub">
              Enrollment Drive - {stats?.constituency} | {today}
            </p>
          </div>
          <div className="session-badge">
            <span className="session-dot"></span>
            Session Active | {stats?.constituency}
          </div>
        </div>

        {/* Stats cards */}
        <div className="stats-grid">
          <div className="stat-card stat-blue">
            <div className="stat-top">
              <span className="stat-label">ENROLLMENTS TODAY</span>
              <span className="stat-icon">👥</span>
            </div>
            <div className="stat-value">{stats?.enrollments_today}</div>
            <div className="stat-sub">+{stats?.enrollments_today} today</div>
          </div>

          <div className="stat-card stat-orange">
            <div className="stat-top">
              <span className="stat-label">PENDING VERIFICATION</span>
              <span className="stat-icon">⏳</span>
            </div>
            <div className="stat-value">{stats?.pending_today}</div>
            <div className="stat-sub">Awaiting biometric</div>
          </div>

          <div className="stat-card stat-red">
            <div className="stat-top">
              <span className="stat-label">REJECTED TODAY</span>
              <span className="stat-icon">⊗</span>
            </div>
            <div className="stat-value">{stats?.rejected_today}</div>
            <div className="stat-sub">Duplicate Aadhaar</div>
          </div>

          <div className="stat-card stat-green">
            <div className="stat-top">
              <span className="stat-label">TOTAL THIS WEEK</span>
              <span className="stat-icon">📊</span>
            </div>
            <div className="stat-value">{stats?.total_this_week}</div>
            <div className="stat-sub">Target: 200</div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{width: `${Math.min((stats?.total_this_week || 0) / 200 * 100, 100)}%`}}
              ></div>
            </div>
          </div>
        </div>

        {/* Action cards */}
        <div className="action-grid">
          <div className="action-card action-dark" onClick={() => navigate('/enroll')}>
            <div className="action-icon">👤+</div>
            <h3>Enroll New Voter</h3>
            <p>Start new Form 6 voter registration</p>
            <span className="action-arrow">→</span>
          </div>

          <div className="action-card action-light" onClick={() => navigate('/voters')}>
            <div className="action-icon">📋</div>
            <h3>View Enrolled Voters</h3>
            <p>Browse today's enrollment records</p>
          </div>
        </div>

        {/* Recent enrollments table */}
        <div className="table-section">
          <div className="table-header">
            <h3>Recent Enrollments</h3>
            <a href="#" onClick={() => navigate('/voters')}>View All →</a>
          </div>

          {stats?.recent_enrollments.length === 0 ? (
            <div className="empty-state">
              No enrollments yet today. Click "Enroll New Voter" to get started.
            </div>
          ) : (
            <table className="enrollments-table">
              <thead>
                <tr>
                  <th>VOTER ID</th>
                  <th>FULL NAME</th>
                  <th>CONSTITUENCY</th>
                  <th>ENROLLED AT</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recent_enrollments.map(v => (
                  <tr key={v.voter_id}>
                    <td className="voter-id">{v.voter_id}</td>
                    <td>{v.full_name}</td>
                    <td>{v.assembly_constituency}</td>
                    <td>{formatTime(v.created_at)}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(v.status)}`}>
                        {getStatusLabel(v.status)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </main>

      {/* Footer */}
      <footer className="footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>Powered by Biometric Authentication Technology</span>
        <span>🔧 Demo Mode - No real data submitted</span>
      </footer>

    </div>
  )
}