import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Check } from 'lucide-react';
import { auth } from '../lib/api';
import { jwtDecode } from 'jwt-decode';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  // Role detection
  let roleBadge = null;
  if (email.includes('@blrtraffic.gov.in')) {
    if (email.startsWith('officer_')) {
      roleBadge = <div className="role-badge patrol animate-slide-up">PATROL OFFICER ACCESS</div>;
    } else {
      roleBadge = <div className="role-badge control animate-slide-up">CONTROL ROOM ACCESS</div>;
    }
  }

  const doLogin = async (u, p) => {
    setLoading(true);
    setError('');

    try {
      const res = await auth.login(u, p);
      const decoded = jwtDecode(res.data.access_token);
      
      login(res.data.access_token, decoded.role);
      setSuccess(true);
      
      setTimeout(() => {
        if (decoded.role === 'officer') {
          navigate('/officer');
        } else {
          navigate('/command');
        }
      }, 800);
      
    } catch (err) {
      setError('Access denied · Check credentials');
      setLoading(false);
    }
  };

  const handleLogin = (e) => {
    e.preventDefault();
    doLogin(email, password);
  };

  const handleQuickAccess = (type) => {
    let u = '', p = '';
    if (type === 'superadmin') { u = 'superadmin@blrtraffic.gov.in'; p = 'admin123'; }
    if (type === 'control') { u = 'cr_central@blrtraffic.gov.in'; p = 'central123'; }
    if (type === 'officer') { u = 'officer_t001@blrtraffic.gov.in'; p = 'cop001'; }
    
    setEmail(u);
    setPassword(p);
    doLogin(u, p);
  };

  return (
    <div className="login-page-root">
      <div className="login-bg"></div>
      <div className="grid-layer grid-bg"></div>

      <div className="login-card animate-slide-up">
        <div className="sys-identity">
          <div className="eyebrow">BENGALURU TRAFFIC POLICE</div>
          <div className="title-wrap">
            <div className="main-title">GRIDLOCK 2.0</div>
            <div className="title-underline"></div>
          </div>
          <div className="subtitle">ASTRaM Enforcement Intelligence</div>
        </div>

        <div className="divider"></div>

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Email / Officer ID</label>
            <div className="input-wrapper">
              <input 
                type="email" 
                className={`form-input ${error ? 'has-error' : ''}`}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>
            {roleBadge}
          </div>

          <div className="form-group">
            <label className="form-label">Authentication Key</label>
            <div className="input-wrapper">
              <input 
                type={showPassword ? "text" : "password"} 
                className={`form-input ${error ? 'has-error' : ''}`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button 
                type="button" 
                className="pwd-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && <div className="error-msg animate-fade">{error}</div>}

          <button 
            type="submit" 
            className={`login-btn ${success ? 'success' : ''}`}
            disabled={loading || success}
          >
            {success ? (
              <Check size={24} />
            ) : loading ? (
              <div className="dots-loader">
                <span></span><span></span><span></span>
              </div>
            ) : (
              "AUTHENTICATE"
            )}
          </button>
        </form>

        <div className="quick-access">
          <div className="qa-divider">
            <span className="qa-text">Quick access for demo</span>
          </div>
          <div className="qa-row">
            <button type="button" className="qa-pill" onClick={() => handleQuickAccess('superadmin')}>System Admin</button>
            <button type="button" className="qa-pill" onClick={() => handleQuickAccess('control')}>Control Room</button>
            <button type="button" className="qa-pill" onClick={() => handleQuickAccess('officer')}>Patrol Officer</button>
          </div>
        </div>
      </div>
    </div>
  );
}
