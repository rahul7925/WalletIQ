import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter your username/email and password.');
      return;
    }

    setError('');
    setIsSubmitting(true);
    try {
      await login(username.trim(), password, remember);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
        background: 'radial-gradient(circle at top, #1a1a28 0%, #0a0a0f 70%)',
      }}
    >
      <div
        className="glass-card animate-fade"
        style={{
          maxWidth: '420px',
          width: '100%',
          padding: '2.5rem 2rem',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.7)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              margin: '0 auto 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--accent-gold) 0%, #8f6c2c 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 15px rgba(200, 169, 110, 0.35)',
            }}
          >
            <ShieldCheck size={26} color="#0a0a0f" strokeWidth={2.5} />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Welcome to Wallet<span className="gold-text">IQ</span>
          </h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Sign in to access your intelligent wealth command center
          </p>
        </div>

        {error && (
          <div
            style={{
              marginBottom: '1.25rem',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent-red-dim)',
              border: '1px solid rgba(255, 100, 100, 0.3)',
              color: 'var(--accent-red)',
              fontSize: '0.8125rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username or Email</label>
            <div style={{ position: 'relative' }}>
              <span
                style={{
                  position: 'absolute',
                  left: '0.75rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                }}
              >
                <User size={16} />
              </span>
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: '2.25rem' }}
                placeholder="e.g. rahul or user@example.com"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Password</label>
              <Link to="/forgot-password" style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>
                Forgot?
              </Link>
            </div>
            <div style={{ position: 'relative' }}>
              <span
                style={{
                  position: 'absolute',
                  left: '0.75rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                }}
              >
                <Lock size={16} />
              </span>
              <input
                type="password"
                className="form-input"
                style={{ paddingLeft: '2.25rem' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', fontSize: '0.8125rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                style={{ accentColor: 'var(--accent-gold)' }}
              />
              <span>Remember this device</span>
            </label>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>
            Create one
          </Link>
        </div>
      </div>
    </div>
  );
}
