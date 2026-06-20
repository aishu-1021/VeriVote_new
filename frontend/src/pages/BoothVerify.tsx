import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './BoothVerify.css'

interface VoterData {
  voter_id: string
  full_name: string
  assembly_constituency: string
  assigned_booth: string
  has_voted: boolean
  status: string
  fingerprint_template: string
}

type VerifyStep = 'search' | 'found' | 'scanning' | 'result'
type VerifyResult = 'approved' | 'rejected_no_match' | 'rejected_already_voted' | 'rejected_not_found' | null

export default function BoothVerify() {
  const navigate = useNavigate()
  const [voterId, setVoterId] = useState('')
  const [voter, setVoter] = useState<VoterData | null>(null)
  const [step, setStep] = useState<VerifyStep>('search')
  const [result, setResult] = useState<VerifyResult>(null)
  const [matchScore, setMatchScore] = useState(0)
  const [error, setError] = useState('')
  const [searching, setSearching] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  const officer = JSON.parse(localStorage.getItem('booth_officer') || '{}')
  const token = localStorage.getItem('booth_token')

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const headers = { Authorization: `Token ${token}` }

  const searchVoter = async () => {
    if (!voterId.trim()) return
    setSearching(true)
    setError('')
    try {
      const res = await axios.get(
        `http://127.0.0.1:8000/api/booth/voter/${voterId.trim().toUpperCase()}/`,
        { headers }
      )
      const v = res.data

      if (v.has_voted) {
        setVoter(v)
        setResult('rejected_already_voted')
        setStep('result')

        // Auto log fraud alert
        await axios.post('http://127.0.0.1:8000/api/booth/record-vote/', {
          voter_id: v.voter_id,
          match_score: 0,
        }, { headers }).catch(() => {})

        return
      }

      setVoter(v)
      setStep('found')
    } catch (err: any) {
      if (err.response?.status === 404) {
        setResult('rejected_not_found')
        setStep('result')
      } else {
        setError('Could not connect to server.')
      }
    } finally {
      setSearching(false)
    }
  }

  const startFingerprint = async () => {
    if (!voter) return
    setStep('scanning')
    try {
      const res = await axios.post(
        'http://127.0.0.1:8000/api/booth/verify-fingerprint/',
        {
          voter_id: voter.voter_id,
          stored_template_b64: voter.fingerprint_template,
        },
        { headers }
      )

      const verifyResult = res.data
      setMatchScore(verifyResult.match_score || 0)

      if (verifyResult.result === 'APPROVED') {
        // Record the vote
        await axios.post(
          'http://127.0.0.1:8000/api/booth/record-vote/',
          { voter_id: voter.voter_id, match_score: verifyResult.match_score },
          { headers }
        )
        setResult('approved')
      } else {
        setResult('rejected_no_match')
      }
      setStep('result')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Verification failed.')
      setStep('found')
    }
  }

  const reset = () => {
    setVoterId('')
    setVoter(null)
    setStep('search')
    setResult(null)
    setMatchScore(0)
    setError('')
  }

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  })

  return (
    <div className="booth-verify-page">
      <div className="booth-top-bar">
        <span>Government of India - Election Commission of India</span>
        <div className="polling-live-badge">
          <span className="live-dot"></span> POLLING LIVE
        </div>
        <span>{currentTime.toLocaleTimeString('en-IN')}</span>
      </div>

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

      <nav className="booth-navbar">
        <a href="#" onClick={() => navigate('/booth/dashboard')}>Booth Dashboard</a>
        <a href="#" className="active">Voter Verification</a>
        <a href="#" onClick={() => navigate('/booth/reports')}>Reports</a>
        <button className="booth-logout-btn" onClick={() => navigate('/booth/dashboard')}>← Dashboard</button>
      </nav>

      <div className="booth-status-bar">
        <span>📍 Booth: {officer.booth_id}</span>
        <span>🏛 {officer.constituency} Assembly Constituency</span>
        <span>👤 Officer: {officer.name}</span>
        <span className="live-indicator">● LIVE</span>
      </div>

      <main className="verify-main">
        <div className="verify-header">
          <div>
            <h2 className="verify-title">Voter Identity Check</h2>
            <p className="verify-sub">
              {step === 'search' && 'Step 1 of 2 — Confirm voter identity before fingerprint scan'}
              {step === 'found' && 'Step 2 of 2 — Voter found. Proceed to fingerprint scan.'}
              {step === 'scanning' && 'Scanning fingerprint...'}
              {step === 'result' && 'Verification complete.'}
            </p>
          </div>
        </div>

        {/* STEP: SEARCH */}
        {step === 'search' && (
          <div className="verify-card">
            <div className="voter-id-label">VOTER ID (EPIC NUMBER)</div>
            <input
              className="voter-id-input"
              type="text"
              placeholder="ENTER VOTER ID"
              value={voterId}
              onChange={e => setVoterId(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && searchVoter()}
            />
            <div className="voter-id-hint">💡 Tip: Voter ID is on the EPIC card</div>
            {error && <div className="verify-error">{error}</div>}
            <div className="verify-btn-row">
              <button className="verify-clear-btn" onClick={() => setVoterId('')}>Clear</button>
              <button
                className="verify-search-btn"
                onClick={searchVoter}
                disabled={searching || !voterId.trim()}
              >
                {searching ? 'Searching...' : 'Search Voter →'}
              </button>
            </div>
          </div>
        )}

        {/* STEP: FOUND */}
        {step === 'found' && voter && (
          <div className="verify-card">
            <div className="voter-found-box">
              <div className="voter-found-title">✓ Voter Found</div>
              <div className="voter-found-name">{voter.full_name}</div>
              <div className="voter-found-details">
                <span>ID: {voter.voter_id}</span>
                <span>Constituency: {voter.assembly_constituency}</span>
                <span>Booth: {voter.assigned_booth || 'Not assigned'}</span>
              </div>
            </div>
            <p className="fp-instruction">
              Ask the voter to place their RIGHT index finger on the MFS100 scanner.
            </p>
            {error && <div className="verify-error">{error}</div>}
            <div className="verify-btn-row">
              <button className="verify-clear-btn" onClick={reset}>← Back</button>
              <button className="verify-search-btn" onClick={startFingerprint}>
                Scan Fingerprint →
              </button>
            </div>
          </div>
        )}

        {/* STEP: SCANNING */}
        {step === 'scanning' && (
          <div className="verify-card scanning-card">
            <div className="scanning-animation">
              <div className="scan-ring ring1"></div>
              <div className="scan-ring ring2"></div>
              <div className="scan-ring ring3"></div>
            </div>
            <div className="scanning-text">Scanning fingerprint...</div>
            <div className="scanning-sub">Ask voter to keep finger flat and still on scanner</div>
          </div>
        )}

        {/* STEP: RESULT */}
        {step === 'result' && (
          <div className={`result-card ${result === 'approved' ? 'result-approved-card' : 'result-rejected-card'}`}>
            {result === 'approved' && (
              <>
                <div className="result-icon">✅</div>
                <h2 className="result-title">APPROVED TO VOTE</h2>
                <p className="result-name">{voter?.full_name}</p>
                <p className="result-detail">Biometric match score: {matchScore}</p>
                <p className="result-instruction">Please proceed to the EVM.</p>
              </>
            )}
            {result === 'rejected_no_match' && (
              <>
                <div className="result-icon">❌</div>
                <h2 className="result-title">REJECTED - FINGERPRINT MISMATCH</h2>
                <p className="result-name">{voter?.full_name}</p>
                <p className="result-detail">Match score: {matchScore} (Required: 40+)</p>
                <p className="result-instruction">Possible impersonation. Fraud alert logged automatically.</p>
              </>
            )}
            {result === 'rejected_already_voted' && (
              <>
                <div className="result-icon">❌</div>
                <h2 className="result-title">REJECTED - ALREADY VOTED</h2>
                <p className="result-name">{voter?.full_name}</p>
                <p className="result-instruction">This voter has already cast their vote. Duplicate attempt flagged.</p>
              </>
            )}
            {result === 'rejected_not_found' && (
              <>
                <div className="result-icon">❌</div>
                <h2 className="result-title">REJECTED - NOT ENROLLED</h2>
                <p className="result-instruction">This Voter ID is not in the system. Contact the election officer.</p>
              </>
            )}
            <button className="next-voter-btn" onClick={reset}>
              Next Voter →
            </button>
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