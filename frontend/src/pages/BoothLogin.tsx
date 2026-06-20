import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './BoothLogin.css'

export default function BoothLogin() {
  const navigate = useNavigate()
  const [badgeNumber, setBadgeNumber] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const handleLogin = async () => {
    if (!badgeNumber || !password) {
      setError('Please fill in all fields.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/booth/login/', {
        badge_number: badgeNumber,
        password: password,
      })
      localStorage.setItem('booth_token', res.data.token)
      localStorage.setItem('booth_officer', JSON.stringify(res.data.officer))
      navigate('/booth/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Login failed.')
    } finally {
      setLoading(false)
    }
  }

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  })

  return (
    <div className="booth-login-page">
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
        <a href="#" className="active">Home</a>
        <a href="#">Booth Dashboard</a>
        <a href="#">Voter Verification</a>
        <a href="#">Reports</a>
      </nav>

      {/* Election day banner */}
      <div className="election-banner">
        🗳 ELECTION DAY - General Elections 2026
        <span>Polling hours: 7:00 AM to 6:00 PM</span>
      </div>

      {/* Login card */}
      <main className="booth-login-main">
        <div className="booth-login-card">
          <div className="booth-card-header">
            <div className="shield-icon">🛡</div>
            <h2>Polling Booth Officer Login</h2>
            <p>Authorized Polling Officers Only</p>
            <div className="date-badge">📅 {today}</div>
          </div>

          <div className="booth-card-body">
            <div className="election-info-box">
              <div className="election-info-label">Election Day</div>
              <div className="election-info-date">{today}</div>
              <div className="election-info-sub">General Elections — Karnataka</div>
            </div>

            {error && <div className="booth-error">{error}</div>}

            <div className="booth-field">
              <label>Officer ID / Badge Number <span className="req">*</span></label>
              <div className="booth-input-wrap">
                <span className="booth-input-icon">👤</span>
                <input
                  type="text"
                  placeholder="e.g. ECI/KA/OFF/2024/0089"
                  value={badgeNumber}
                  onChange={e => setBadgeNumber(e.target.value)}
                />
              </div>
            </div>

            <div className="booth-field">
              <label>Password <span className="req">*</span></label>
              <div className="booth-input-wrap">
                <span className="booth-input-icon">🔒</span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleLogin()}
                />
                <span
                  className="booth-input-icon-right"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? '🙈' : '👁'}
                </span>
              </div>
            </div>

            <button
              className="booth-login-btn"
              onClick={handleLogin}
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Begin Polling →'}
            </button>
          </div>
        </div>

        <div className="booth-security-notice">
          ⚠ Restricted terminal. Your officer ID, location, and timestamp have been
          recorded. All actions during this session are logged in real-time to ECI servers.
        </div>
      </main>

      <footer className="booth-footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>🔒 All booth activity is encrypted and logged</span>
        <span>Booth ID: KA-147-007</span>
      </footer>
    </div>
  )
}