import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Key, Lock, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';

export default function ForgotPasswordPage() {
  const [formData, setFormData] = useState({
    username: '',
    recovery_pin: '',
    new_password: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!formData.username.trim() || !formData.recovery_pin || !formData.new_password) {
      setError('Please fill in all fields.');
      return;
    }

    setError('');
    setIsSubmitting(true);
    try {
      await api.forgotPassword(formData);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.message || 'Failed to reset password. Please check your credentials.');
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
            <Key size={24} color="#0a0a0f" strokeWidth={2.5} />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Account Recovery
          </h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Reset your password using your secure 4-digit PIN
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

        {success && (
          <div
            style={{
              marginBottom: '1.25rem',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent-green-dim)',
              border: '1px solid rgba(0, 214, 143, 0.3)',
              color: 'var(--accent-green)',
              fontSize: '0.8125rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <CheckCircle size={16} />
            <span>Password updated! Redirecting to sign in...</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              name="username"
              className="form-input"
              placeholder="Your username"
              value={formData.username}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Recovery PIN (4 Digits)</label>
            <input
              type="password"
              name="recovery_pin"
              maxLength="4"
              className="form-input num-mono"
              placeholder="••••"
              value={formData.recovery_pin}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">New Password</label>
            <input
              type="password"
              name="new_password"
              className="form-input"
              placeholder="••••••••"
              value={formData.new_password}
              onChange={handleChange}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }}
            disabled={isSubmitting || success}
          >
            {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          Remember your credentials?{' '}
          <Link to="/login" style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
