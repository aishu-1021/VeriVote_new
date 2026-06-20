import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import { karnatakaData, parliamentaryMap } from '../data/karnataka'
import './Enroll.css'

interface Step1Data {
  full_name: string
  date_of_birth: string
  gender: string
  relative_name: string
  relation: string
  mobile_number: string
  email: string
}

interface Step2Data {
  house_number: string
  street: string
  city: string
  pincode: string
  state: string
  district: string
  assembly_constituency: string
  parliamentary_constituency: string
  assigned_booth: string
}

interface Step3Data {
  aadhaar_number: string
  passport_photo: File | null
  fingerprint_b64: string
}

const INITIAL_STEP1: Step1Data = {
  full_name: '', date_of_birth: '', gender: '',
  relative_name: '', relation: '', mobile_number: '', email: ''
}

const INITIAL_STEP2: Step2Data = {
  house_number: '', street: '', city: '', pincode: '',
  state: 'Karnataka', district: '', assembly_constituency: '',
  parliamentary_constituency: '', assigned_booth: ''
}

const INITIAL_STEP3: Step3Data = {
  aadhaar_number: '', passport_photo: null, fingerprint_b64: ''
}

export default function Enroll() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [step1, setStep1] = useState<Step1Data>(INITIAL_STEP1)
  const [step2, setStep2] = useState<Step2Data>(INITIAL_STEP2)
  const [step3, setStep3] = useState<Step3Data>(INITIAL_STEP3)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [aadhaarStatus, setAadhaarStatus] = useState<'idle'|'checking'|'ok'|'duplicate'>('idle')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [captureStatus, setCaptureStatus] = useState<'idle'|'capturing'|'done'|'failed'>('idle')

  // ── Age calculation ─────────────────────────────────────────────────────
  const calculateAge = (dob: string) => {
    if (!dob) return ''
    const today = new Date()
    const birth = new Date(dob)
    let age = today.getFullYear() - birth.getFullYear()
    const m = today.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
    return age >= 0 ? String(age) : ''
  }

  const isAdult = (dob: string) => {
    const age = Number(calculateAge(dob))
    return age >= 18
  }

  // ── Max date for DOB (must be 18+) ──────────────────────────────────────
  const maxDOB = () => {
    const d = new Date()
    d.setFullYear(d.getFullYear() - 18)
    return d.toISOString().split('T')[0]
  }

  // ── District change → reset constituency ────────────────────────────────
  const handleDistrictChange = (district: string) => {
    setStep2(prev => ({
      ...prev,
      district,
      assembly_constituency: '',
      parliamentary_constituency: '',
      assigned_booth: ''
    }))
  }

  // ── Constituency change → auto-fill parliamentary ───────────────────────
  const handleConstituencyChange = (ac: string) => {
    const pc = parliamentaryMap[ac] || 'To be assigned'
    const booth = ac ? `Booth ${ac.substring(0, 3).toUpperCase()}-001` : ''
    setStep2(prev => ({
      ...prev,
      assembly_constituency: ac,
      parliamentary_constituency: pc,
      assigned_booth: booth
    }))
  }

  // ── Aadhaar duplicate check ──────────────────────────────────────────────
  const checkAadhaar = async (value: string) => {
    const clean = value.replace(/\s|-/g, '')
    if (clean.length !== 12) return
    setAadhaarStatus('checking')
    try {
      const res = await api.post('/voters/check-aadhaar/', { aadhaar_number: clean })
      setAadhaarStatus(res.data.duplicate ? 'duplicate' : 'ok')
    } catch {
      setAadhaarStatus('idle')
    }
  }

  // ── Fingerprint capture ──────────────────────────────────────────────────
  const captureFingerprint = async () => {
    setCaptureStatus('capturing')
    try {
      // Calls your biometric engine Django endpoint
      const res = await api.post('/booth/capture-fingerprint/')
      setStep3(prev => ({ ...prev, fingerprint_b64: res.data.descriptor_b64 }))
      setCaptureStatus('done')
    } catch {
      setCaptureStatus('failed')
    }
  }

  // ── Validation ───────────────────────────────────────────────────────────
  const validateStep1 = () => {
    const e: Record<string, string> = {}
    if (!step1.full_name.trim()) e.full_name = 'Full name is required'
    if (!step1.date_of_birth) e.date_of_birth = 'Date of birth is required'
    else if (!isAdult(step1.date_of_birth)) e.date_of_birth = 'Voter must be at least 18 years old'
    if (!step1.gender) e.gender = 'Please select gender'
    if (!step1.relative_name.trim()) e.relative_name = 'This field is required'
    if (!step1.relation) e.relation = 'Please select relation'
    if (!step1.mobile_number || step1.mobile_number.length < 10) e.mobile_number = 'Valid mobile number required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const validateStep2 = () => {
    const e: Record<string, string> = {}
    if (!step2.house_number.trim()) e.house_number = 'Required'
    if (!step2.street.trim()) e.street = 'Required'
    if (!step2.city.trim()) e.city = 'Required'
    if (!step2.pincode || step2.pincode.length !== 6) e.pincode = 'Valid 6-digit pincode required'
    if (!step2.district) e.district = 'Please select district'
    if (!step2.assembly_constituency) e.assembly_constituency = 'Please select constituency'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const validateStep3 = () => {
    const e: Record<string, string> = {}
    const clean = step3.aadhaar_number.replace(/\s|-/g, '')
    if (clean.length !== 12) e.aadhaar_number = 'Valid 12-digit Aadhaar required'
    if (aadhaarStatus === 'duplicate') e.aadhaar_number = 'This Aadhaar is already enrolled'
    if (!step3.passport_photo) e.passport_photo = 'Passport photo is required'
    if (!step3.fingerprint_b64) e.fingerprint_b64 = 'Fingerprint scan is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  // ── Navigation ───────────────────────────────────────────────────────────
  const nextStep = () => {
    if (currentStep === 1 && validateStep1()) setCurrentStep(2)
    if (currentStep === 2 && validateStep2()) setCurrentStep(3)
  }

  const prevStep = () => setCurrentStep(prev => prev - 1)

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!validateStep3()) return
    setSubmitting(true)
    setSubmitError('')

    const formData = new FormData()
    // Step 1
    Object.entries(step1).forEach(([k, v]) => formData.append(k, v))
    // Step 2
    Object.entries(step2).forEach(([k, v]) => formData.append(k, v))
    // Step 3
    formData.append('aadhaar_number', step3.aadhaar_number.replace(/\s|-/g, ''))
    if (step3.passport_photo) formData.append('passport_photo', step3.passport_photo)
    formData.append('fingerprint_b64', step3.fingerprint_b64)

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://127.0.0.1:8000/api/voters/enroll/', {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}` },
        body: formData,
      })
      const data = await res.json()
      if (res.ok) {
        navigate('/dashboard', {
          state: { success: true, voter_id: data.voter_id }
        })
      } else {
        setSubmitError(JSON.stringify(data))
      }
    } catch {
      setSubmitError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step indicator ───────────────────────────────────────────────────────
  const StepIndicator = () => (
    <div className="step-indicator">
      {[1, 2, 3].map(n => (
        <div key={n} className="step-item">
          <div className={`step-circle ${currentStep === n ? 'active' : currentStep > n ? 'done' : ''}`}>
            {currentStep > n ? '✓' : n}
          </div>
          <span className={`step-label ${currentStep === n ? 'active' : ''}`}>
            {n === 1 ? 'Personal Details' : n === 2 ? 'Address & Constituency' : 'Documents & Biometrics'}
          </span>
          {n < 3 && <div className={`step-line ${currentStep > n ? 'done' : ''}`}></div>}
        </div>
      ))}
    </div>
  )

  return (
    <div className="enroll-page">
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
            {localStorage.getItem('officer') ? JSON.parse(localStorage.getItem('officer')!).name : ''} | Booth KA-04
          </span>
        </div>
      </header>

      {/* Nav */}
      <nav className="navbar">
        <a href="#" onClick={() => navigate('/dashboard')}>Enrollment</a>
        <a href="#">Help</a>
      </nav>

      <main className="enroll-main">
        <StepIndicator />

        <h2 className="enroll-title">New Voter Registration - Step {currentStep} of 3</h2>

        {/* ── STEP 1 ── */}
        {currentStep === 1 && (
          <div className="enroll-card">
            <div className="section-header">
              <span className="section-icon">👤</span>
              <h3>Part A: Personal Identity</h3>
            </div>

            <div className="field-group">
              <label>Full Name <span className="required">*</span></label>
              <input
                type="text"
                placeholder="Exactly as printed on Aadhaar card"
                value={step1.full_name}
                onChange={e => setStep1(p => ({ ...p, full_name: e.target.value }))}
              />
              <span className="hint">Do not use initials - write full name as on Aadhaar</span>
              {errors.full_name && <span className="error">{errors.full_name}</span>}
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>Date of Birth <span className="required">*</span></label>
                <input
                  type="date"
                  max={maxDOB()}
                  value={step1.date_of_birth}
                  onChange={e => setStep1(p => ({ ...p, date_of_birth: e.target.value }))}
                />
                {errors.date_of_birth && <span className="error">{errors.date_of_birth}</span>}
              </div>
              <div className="field-group">
                <label>Age</label>
                <input
                  type="text"
                  value={calculateAge(step1.date_of_birth)}
                  disabled
                  placeholder="Auto-calculated"
                />
              </div>
            </div>

            <div className="field-group">
              <label>Gender <span className="required">*</span></label>
              <div className="gender-row">
                {[['M', '♂ Male'], ['F', '♀ Female'], ['O', '⚧ Transgender / Other']].map(([val, label]) => (
                  <button
                    key={val}
                    className={`gender-btn ${step1.gender === val ? 'selected' : ''}`}
                    onClick={() => setStep1(p => ({ ...p, gender: val }))}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {errors.gender && <span className="error">{errors.gender}</span>}
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>Father's / Husband's Name <span className="required">*</span></label>
                <input
                  type="text"
                  value={step1.relative_name}
                  onChange={e => setStep1(p => ({ ...p, relative_name: e.target.value }))}
                />
                {errors.relative_name && <span className="error">{errors.relative_name}</span>}
              </div>
              <div className="field-group">
                <label>Relation <span className="required">*</span></label>
                <select
                  value={step1.relation}
                  onChange={e => setStep1(p => ({ ...p, relation: e.target.value }))}
                >
                  <option value="">Select</option>
                  <option value="father">Father</option>
                  <option value="husband">Husband</option>
                  <option value="mother">Mother</option>
                  <option value="guardian">Guardian</option>
                </select>
                {errors.relation && <span className="error">{errors.relation}</span>}
              </div>
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>Mobile Number <span className="required">*</span></label>
                <div className="input-prefix">
                  <span className="prefix">+91</span>
                  <input
                    type="tel"
                    maxLength={10}
                    value={step1.mobile_number}
                    onChange={e => setStep1(p => ({ ...p, mobile_number: e.target.value.replace(/\D/g, '') }))}
                  />
                </div>
                <span className="hint">OTP alerts will be sent to this number</span>
                {errors.mobile_number && <span className="error">{errors.mobile_number}</span>}
              </div>
              <div className="field-group">
                <label>Email Address</label>
                <input
                  type="email"
                  placeholder="Optional - for e-EPIC card delivery"
                  value={step1.email}
                  onChange={e => setStep1(p => ({ ...p, email: e.target.value }))}
                />
              </div>
            </div>

            <div className="btn-row">
              <button className="btn-secondary" onClick={() => navigate('/dashboard')}>← Back to Dashboard</button>
              <button className="btn-primary" onClick={nextStep}>Save & Next →</button>
            </div>
          </div>
        )}

        {/* ── STEP 2 ── */}
        {currentStep === 2 && (
          <div className="enroll-card">
            <div className="info-banner">
              ℹ In India, your registered address determines your constituency.
              Voters can only cast their ballot at the polling booth assigned to their residential address.
            </div>

            <div className="section-header">
              <span className="section-icon">📍</span>
              <h3>Part B: Address & Constituency Details</h3>
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>House No. / Flat No. <span className="required">*</span></label>
                <input
                  type="text"
                  value={step2.house_number}
                  onChange={e => setStep2(p => ({ ...p, house_number: e.target.value }))}
                />
                {errors.house_number && <span className="error">{errors.house_number}</span>}
              </div>
              <div className="field-group">
                <label>Street / Area / Mohalla <span className="required">*</span></label>
                <input
                  type="text"
                  value={step2.street}
                  onChange={e => setStep2(p => ({ ...p, street: e.target.value }))}
                />
                {errors.street && <span className="error">{errors.street}</span>}
              </div>
            </div>

            <div className="field-group">
              <label>Village / Town / City <span className="required">*</span></label>
              <input
                type="text"
                value={step2.city}
                onChange={e => setStep2(p => ({ ...p, city: e.target.value }))}
              />
              {errors.city && <span className="error">{errors.city}</span>}
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>Pincode <span className="required">*</span></label>
                <input
                  type="text"
                  maxLength={6}
                  value={step2.pincode}
                  onChange={e => setStep2(p => ({ ...p, pincode: e.target.value.replace(/\D/g, '') }))}
                />
                {errors.pincode && <span className="error">{errors.pincode}</span>}
              </div>
              <div className="field-group">
                <label>State <span className="required">*</span></label>
                <input type="text" value="Karnataka" disabled />
              </div>
            </div>

            <div className="field-row">
              <div className="field-group">
                <label>District <span className="required">*</span></label>
                <select
                  value={step2.district}
                  onChange={e => handleDistrictChange(e.target.value)}
                >
                  <option value="">Select District</option>
                  {Object.keys(karnatakaData).sort().map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                {errors.district && <span className="error">{errors.district}</span>}
              </div>
              <div className="field-group">
                <label>Assembly Constituency <span className="required">*</span></label>
                <select
                  value={step2.assembly_constituency}
                  onChange={e => handleConstituencyChange(e.target.value)}
                  disabled={!step2.district}
                >
                  <option value="">Select Constituency</option>
                  {(karnatakaData[step2.district] || []).map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                {errors.assembly_constituency && <span className="error">{errors.assembly_constituency}</span>}
              </div>
            </div>

            <div className="field-group">
              <label>Parliamentary Constituency</label>
              <input
                type="text"
                value={step2.parliamentary_constituency}
                disabled
                placeholder="Auto-assigned based on Assembly Constituency"
              />
              <span className="hint">Auto-assigned based on Assembly Constituency</span>
            </div>

            <div className="field-group">
              <label>Assigned Polling Booth</label>
              <input
                type="text"
                value={step2.assigned_booth}
                disabled
                placeholder="Auto-assigned"
              />
              <span className="hint">Polling booth is automatically assigned based on your registered address</span>
            </div>

            <div className="btn-row">
              <button className="btn-secondary" onClick={prevStep}>← Back</button>
              <button className="btn-primary" onClick={nextStep}>Save & Next →</button>
            </div>
          </div>
        )}

        {/* ── STEP 3 ── */}
        {currentStep === 3 && (
          <div className="step3-grid">
            {/* Left — Documents */}
            <div className="enroll-card">
              <div className="section-header">
                <span className="section-icon">📄</span>
                <h3>Part D: Identity Documents</h3>
              </div>

              <div className="field-group">
                <label>Aadhaar Number <span className="required">*</span></label>
                <input
                  type="text"
                  placeholder="XXXX-XXXX-XXXX"
                  maxLength={14}
                  value={step3.aadhaar_number}
                  onChange={e => {
                    const val = e.target.value
                    setStep3(p => ({ ...p, aadhaar_number: val }))
                    setAadhaarStatus('idle')
                    checkAadhaar(val)
                  }}
                />
                <div className="privacy-notice">
                  🔒 Privacy Notice: Your Aadhaar number is converted to an irreversible SHA-256
                  hash on this device. The raw number is never transmitted or stored by VeriVote systems.
                </div>
                {aadhaarStatus === 'checking' && <span className="hint">Checking...</span>}
                {aadhaarStatus === 'ok' && <span className="success-text">✓ Aadhaar is unique</span>}
                {aadhaarStatus === 'duplicate' && <span className="error">⚠ This Aadhaar is already enrolled</span>}
                {errors.aadhaar_number && <span className="error">{errors.aadhaar_number}</span>}
              </div>

              <div className="field-group">
                <label>Upload Aadhaar Card <span className="required">*</span></label>
                <div
                  className="upload-zone"
                  onClick={() => document.getElementById('aadhaar-upload')?.click()}
                >
                  <span className="upload-icon">📄</span>
                  <span>Click to upload or drag & drop</span>
                  <span className="hint">JPG, PNG - max 5MB</span>
                  <input id="aadhaar-upload" type="file" accept="image/*" style={{ display: 'none' }} />
                </div>
              </div>

              <div className="field-group">
                <label>Passport Photo <span className="required">*</span></label>
                <div
                  className={`upload-zone ${step3.passport_photo ? 'uploaded' : ''}`}
                  onClick={() => document.getElementById('photo-upload')?.click()}
                >
                  {step3.passport_photo ? (
                    <span className="success-text">✓ {step3.passport_photo.name}</span>
                  ) : (
                    <>
                      <span className="upload-icon">🖼</span>
                      <span>Click to upload passport photo</span>
                      <span className="hint">JPG, PNG - max 5MB</span>
                    </>
                  )}
                  <input
                    id="photo-upload"
                    type="file"
                    accept="image/*"
                    style={{ display: 'none' }}
                    onChange={e => setStep3(p => ({ ...p, passport_photo: e.target.files?.[0] || null }))}
                  />
                </div>
                {errors.passport_photo && <span className="error">{errors.passport_photo}</span>}
              </div>

              <div className="declaration-box">
                <div className="declaration-title">📋 Enrollment Officer Declaration</div>
                <label className="declaration-check">
                  <input type="checkbox" />
                  <span>
                    I, the undersigned Enrollment Officer, hereby certify that:<br />
                    • I have verified the voter's identity documents in person<br />
                    • The voter is an Indian citizen above 18 years of age<br />
                    • All information entered is accurate to the best of my knowledge<br />
                    • The biometric data belongs to the voter present before me
                  </span>
                </label>
              </div>
            </div>

            {/* Right — Biometric */}
            <div className="enroll-card biometric-card">
              <div className="section-header">
                <span className="section-icon">👆</span>
                <h3>Part E: Biometric</h3>
              </div>
              <p className="biometric-instruction">
                Ask the voter to place their RIGHT index finger flat and still on the MFS100 scanner below.
              </p>

              <div className={`fingerprint-display ${captureStatus === 'done' ? 'captured' : captureStatus === 'failed' ? 'failed' : ''}`}>
                {captureStatus === 'idle' && <div className="fp-rings"><div></div><div></div><div></div></div>}
                {captureStatus === 'capturing' && <div className="fp-scanning">Scanning...</div>}
                {captureStatus === 'done' && <div className="fp-success">✓ Captured</div>}
                {captureStatus === 'failed' && <div className="fp-failed">✕ Failed — Retry</div>}
              </div>

              <div className="checklist">
                <div className="checklist-title">CAPTURE CHECKLIST</div>
                <div className={`checklist-item ${aadhaarStatus === 'ok' ? 'done' : ''}`}>
                  <span>🔷 Aadhaar Hash</span>
                  <span className={aadhaarStatus === 'ok' ? 'status-done' : 'status-pending'}>
                    {aadhaarStatus === 'ok' ? '✓ Ready' : '◷ Pending'}
                  </span>
                </div>
                <div className={`checklist-item ${step3.passport_photo ? 'done' : ''}`}>
                  <span>🖼 Passport Photo</span>
                  <span className={step3.passport_photo ? 'status-done' : 'status-pending'}>
                    {step3.passport_photo ? '✓ Ready' : '◷ Pending'}
                  </span>
                </div>
                <div className={`checklist-item ${captureStatus === 'done' ? 'done' : ''}`}>
                  <span>👆 Fingerprint</span>
                  <span className={captureStatus === 'done' ? 'status-done' : 'status-pending'}>
                    {captureStatus === 'done' ? '✓ Ready' : '◷ Pending'}
                  </span>
                </div>
              </div>

              <button
                className={`capture-btn ${captureStatus === 'done' ? 'capture-done' : ''}`}
                onClick={captureFingerprint}
                disabled={captureStatus === 'capturing'}
              >
                {captureStatus === 'capturing' ? 'Scanning...' :
                 captureStatus === 'done' ? '✓ Fingerprint Captured — Rescan' :
                 '👆 Capture Fingerprint (MFS100)'}
              </button>

              {errors.fingerprint_b64 && <span className="error">{errors.fingerprint_b64}</span>}

              {submitError && <div className="error-banner">{submitError}</div>}
            </div>

            {/* Full width submit row */}
            <div className="step3-btn-row">
              <button className="btn-secondary" onClick={prevStep}>← Back</button>
              <button
                className="btn-primary"
                onClick={handleSubmit}
                disabled={submitting || captureStatus !== 'done' || aadhaarStatus === 'duplicate'}
              >
                {submitting ? 'Submitting...' : 'Complete Registration →'}
              </button>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <span>VeriVote © 2026 | Election Commission of India</span>
        <span>Powered by Biometric Authentication Technology</span>
        <span>🔧 Demo Mode - No real data submitted</span>
      </footer>
    </div>
  )
}