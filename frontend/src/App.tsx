import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Enroll from './pages/Enroll'
import VoterList from './pages/VoterList'
import BoothLogin from './pages/BoothLogin'
import BoothDashboard from './pages/BoothDashboard'
import BoothVerify from './pages/BoothVerify'
import Reports from './pages/Reports'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/enroll" element={<Enroll />} />
        <Route path="/voters" element={<VoterList />} />
        <Route path="/booth/login" element={<BoothLogin />} />
        <Route path="/booth/dashboard" element={<BoothDashboard />} />
        <Route path="/booth/verify" element={<BoothVerify />} />
        <Route path="/booth/reports" element={<Reports />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App