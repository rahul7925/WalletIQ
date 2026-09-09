import React, { useState } from 'react';
import { Settings, User, Lock, Globe, DollarSign, ShieldCheck, CheckCircle, AlertCircle, Save } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function SettingsPage() {
  const { user, updateUser } = useAuth();
  const [profileData, setProfileData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    language: user?.language || 'en',
    monthly_budget: user?.monthly_budget || 0,
    monthly_income: user?.monthly_income || 0,
    recovery_pin: '',
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [profileMsg, setProfileMsg] = useState({ text: '', isError: false });
  const [passwordMsg, setPasswordMsg] = useState({ text: '', isError: false });
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);

  function handleProfileChange(e) {
    const { name, value } = e.target;
    setProfileData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSaveProfile(e) {
    e.preventDefault();
    setIsProfileSaving(true);
    setProfileMsg({ text: '', isError: false });
    try {
      const payload = {
        full_name: profileData.full_name,
        email: profileData.email,
        language: profileData.language,
        monthly_budget: parseFloat(profileData.monthly_budget || 0),
        monthly_income: parseFloat(profileData.monthly_income || 0),
      };
      if (profileData.recovery_pin) {
        payload.recovery_pin = profileData.recovery_pin;
      }
      const updated = await api.updateProfile(payload);
      updateUser(updated.user || payload);
      setProfileMsg({ text: 'Profile configuration updated successfully.', isError: false });
    } catch (err) {
      setProfileMsg({ text: err.message || 'Failed to update profile', isError: true });
    } finally {
      setIsProfileSaving(false);
    }
  }

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <Settings size={24} color="var(--accent-gold)" />
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            System & Account Settings
          </h1>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Manage your personal identity, localization preferences, and security credentials
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        {/* Profile Settings */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <User size={18} color="var(--accent-gold)" />
            <span>Profile & Financial Baselines</span>
          </h3>

          {profileMsg.text && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                background: profileMsg.isError ? 'var(--accent-red-dim)' : 'var(--accent-green-dim)',
                color: profileMsg.isError ? 'var(--accent-red)' : 'var(--accent-green)',
                fontSize: '0.8125rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              {profileMsg.isError ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
              <span>{profileMsg.text}</span>
            </div>
          )}

          <form onSubmit={handleSaveProfile}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                name="full_name"
                className="form-input"
                value={profileData.full_name}
                onChange={handleProfileChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                name="email"
                className="form-input"
                value={profileData.email}
                onChange={handleProfileChange}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Monthly Income (₹)</label>
                <input
                  type="number"
                  name="monthly_income"
                  className="form-input num-mono"
                  value={profileData.monthly_income}
                  onChange={handleProfileChange}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Monthly Budget (₹)</label>
                <input
                  type="number"
                  name="monthly_budget"
                  className="form-input num-mono"
                  value={profileData.monthly_budget}
                  onChange={handleProfileChange}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Language</label>
                <select
                  name="language"
                  className="form-select"
                  value={profileData.language}
                  onChange={handleProfileChange}
                >
                  <option value="en">English</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Recovery PIN (4 Digits)</label>
                <input
                  type="password"
                  name="recovery_pin"
                  maxLength="4"
                  className="form-input num-mono"
                  placeholder="••••"
                  value={profileData.recovery_pin}
                  onChange={handleProfileChange}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }}
              disabled={isProfileSaving}
            >
              <Save size={16} />
              <span>{isProfileSaving ? 'Updating...' : 'Save Changes'}</span>
            </button>
          </form>
        </div>

        {/* Security & System Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-card">
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={18} color="var(--accent-gold)" />
              <span>Security & Infrastructure</span>
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Backend Architecture</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Railway Python/Flask</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Database Engine</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Railway MySQL (PyMySQL)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Frontend Host</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Vercel Edge SPA</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Authentication Protocol</span>
                <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>Cryptographic URLSafe Bearer</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
