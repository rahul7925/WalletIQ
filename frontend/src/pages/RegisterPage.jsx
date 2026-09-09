import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, User, Mail, DollarSign, Key, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    monthly_income: '',
    monthly_budget: '',
    language: 'en',
    recovery_pin: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!formData.username.trim() || !formData.password) {
      setError('Username and password are required.');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setError('');
    setIsSubmitting(true);
    try {
      await register({
        ...formData,
        monthly_income: formData.monthly_income ? parseFloat(formData.monthly_income) : 0.0,
        monthly_budget: formData.monthly_budget ? parseFloat(formData.monthly_budget) : 0.0,
      });
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Registration failed. Please check your inputs.');
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
        padding: '2rem 1.5rem',
        background: 'radial-gradient(circle at top, #1a1a28 0%, #0a0a0f 70%)',
      }}
    >
      <div
        className="glass-card animate-fade"
        style={{
          maxWidth: '520px',
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
            Create your Wallet<span className="gold-text">IQ</span> Account
          </h1>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Start managing expenses, budgets, and AI wealth intelligence
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Username *</label>
              <input
                type="text"
                name="username"
                className="form-input"
                placeholder="e.g. rahul_dev"
                value={formData.username}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                name="full_name"
                className="form-input"
                placeholder="Rahul Kumar"
                value={formData.full_name}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              name="email"
              className="form-input"
              placeholder="rahul@example.com"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password * (Min 6 chars, Upper, Lower, Num, Symbol)</label>
            <input
              type="password"
              name="password"
              className="form-input"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Monthly Income (₹)</label>
              <input
                type="number"
                name="monthly_income"
                className="form-input num-mono"
                placeholder="65000"
                value={formData.monthly_income}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Monthly Budget (₹)</label>
              <input
                type="number"
                name="monthly_budget"
                className="form-input num-mono"
                placeholder="35000"
                value={formData.monthly_budget}
                onChange={handleChange}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Language</label>
              <select
                name="language"
                className="form-select"
                value={formData.language}
                onChange={handleChange}
              >
                <option value="en">English</option>
                <option value="ta">தமிழ் (Tamil)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Recovery PIN (4 Digits)</label>
              <input
                type="text"
                name="recovery_pin"
                maxLength="4"
                className="form-input num-mono"
                placeholder="1234"
                value={formData.recovery_pin}
                onChange={handleChange}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating Account...' : 'Register Account'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.75rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
