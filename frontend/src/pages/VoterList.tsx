import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import './Dashboard.css'

interface Voter {
  voter_id: string
  full_name: string
  assembly_constituency: string
  created_at: string
  status: string
}

export default function VoterList() {
  const navigate = useNavigate()
  const [voters, setVoters] = useState<Voter[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    api.get('/voters/list/').then(res => {
      setVoters(res.data)
      setLoading(false)
    }).catch(() => {
      navigate('/login')
    })
  }, [])

  const filtered = voters.filter(v =>
    v.full_name.toLowerCase().includes(search.toLowerCase()) ||
    v.voter_id.toLowerCase().includes(search.toLowerCase())
  )

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'enrolled': return '✅ Enrolled'
      case 'pending': return '⏳ Pending'
      case 'rejected': return '❌ Rejected'
      default: return status
    }
  }

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'enrolled': return 'status-enrolled'
      case 'pending': return 'status-pending'
      case 'rejected': return 'status-rejected'
      default: return ''
    }
  }

  return (
    <div className="dashboard-page">
      <div className="top-bar">
        <span>Government of India - Election Commission of India</span>
        <span>Help | Contact | English ▾</span>
      </div>

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
            {localStorage.getItem('officer') ? JSON.parse(localStorage.getItem('officer')!).name : ''} | Booth KA-04
          </span>
        </div>
      </header>

      <nav className="navbar">
        <a href="#" onClick={() => navigate('/dashboard')}>Enrollment</a>
        <a href="#">Help</a>
        <button className="logout-btn" onClick={() => navigate('/dashboard')}>← Back to Dashboard</button>
      </nav>

      <main className="dashboard-main">
        <div className="table-header" style={{marginBottom: '16px'}}>
          <h2 style={{fontSize: '20px', fontWeight: 700}}>Enrolled Voters</h2>
          <input
            type="text"
            placeholder="Search by name or voter ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              padding: '8px 14px',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              fontSize: '13px',
              width: '260px',
              outline: 'none'
            }}
          />
        </div>

        <div className="table-section">
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">No voters found.</div>
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
                {filtered.map(v => (
                  <tr key={v.voter_id}>
                    <td className="voter-id">{v.voter_id}</td>
                    <td>{v.full_name}</td>
                    <td>{v.assembly_constituency}</td>
                    <td>{new Date(v.created_at).toLocaleString('en-IN')}</td>
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

      <footer className="footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>Powered by Biometric Authentication Technology</span>
        <span>🔧 Demo Mode - No real data submitted</span>
      </footer>
    </div>
  )
}