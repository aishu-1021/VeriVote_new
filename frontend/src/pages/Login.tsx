import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [badgeNumber, setBadgeNumber] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
  if (!badgeNumber || !password) {
    setError('Please fill in all fields.')
    return
  }
  setLoading(true)
  setError('')
  try {
    const res = await api.post('/voters/login/', {
      badge_number: badgeNumber,
      password: password,
    })
    // Store token and officer info
    localStorage.setItem('auth_token', res.data.token)
    localStorage.setItem('officer', JSON.stringify(res.data.officer))
    navigate('/dashboard')
  } catch (err: any) {
    setError(err.response?.data?.error || 'Login failed. Please try again.')
  } finally {
    setLoading(false)
  }
}

  return (
    <div className="login-page">
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
          Ministry of Law and Justice | Election Commission of India &nbsp;<strong>IN</strong>
        </div>
      </header>

      {/* Nav */}
      <nav className="navbar">
        <a href="#" className="active">Enrollment Login</a>
        <a href="#">Help</a>
      </nav>

      {/* Main content */}
      <main className="login-main">
        <div className="login-card">
          <div className="login-card-header">
            <div className="shield-icon">🛡</div>
            <h2>Enrollment Officer Login</h2>
            <p>Authorized Personnel Only</p>
          </div>

          <div className="login-card-body">
            {error && <div className="error-banner">{error}</div>}

            <div className="field-group">
              <label>Officer ID / Badge Number <span className="required">*</span></label>
              <div className="input-wrapper">
                <span className="input-icon">👤</span>
                <input
                  type="text"
                  placeholder="ECI/KA/OFF/2024/0042"
                  value={badgeNumber}
                  onChange={e => setBadgeNumber(e.target.value)}
                />
              </div>
            </div>

            <div className="field-group">
              <label>Password <span className="required">*</span></label>
              <div className="input-wrapper">
                <span className="input-icon">🔒</span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleLogin()}
                />
                <span
                  className="input-icon-right"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? '🙈' : '👁'}
                </span>
              </div>
            </div>

            <div className="field-group">
              <label>Assigned Constituency</label>
              <div className="input-wrapper">
                <input
                  type="text"
                  placeholder="Auto-filled from Officer ID"
                  disabled
                />
              </div>
              <span className="field-hint">As per your ECI appointment letter</span>
            </div>

            <button
              className="login-btn"
              onClick={handleLogin}
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Login to Enrollment Portal →'}
            </button>

            <p className="forgot-link">Forgot credentials?</p>
          </div>
        </div>

        <div className="security-notice">
          ⚠ This is a restricted government terminal. All login attempts are recorded
          and monitored. Unauthorized access is punishable under IT Act 2000.
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