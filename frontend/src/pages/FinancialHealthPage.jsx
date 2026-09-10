import React, { useState, useEffect } from 'react';
import { HeartPulse, ShieldCheck, DollarSign, AlertTriangle, Sparkles, CheckCircle, Edit2 } from 'lucide-react';
import StatCard from '../components/StatCard';
import ProgressBar from '../components/ProgressBar';
import Modal from '../components/Modal';
import { api } from '../services/api';

export default function FinancialHealthPage() {
  const cachedHealth = api.getCached ? api.getCached('/financial-health') : null;
  const [healthData, setHealthData] = useState(cachedHealth);
  const [isLoading, setIsLoading] = useState(!cachedHealth);
  const [isIncomeModalOpen, setIsIncomeModalOpen] = useState(false);
  const [incomeInput, setIncomeInput] = useState(cachedHealth?.monthly_income || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadHealth() {
    if (!healthData && !cachedHealth) setIsLoading(true);
    try {
      const data = await api.getFinancialHealth();
      setHealthData(data);
      if (data?.monthly_income) {
        setIncomeInput(data.monthly_income);
      }
    } catch (err) {
      console.error('Failed to load financial health', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadHealth();
  }, []);

  async function handleUpdateIncome(e) {
    e.preventDefault();
    if (!incomeInput || isNaN(incomeInput) || parseFloat(incomeInput) <= 0) return;
    setIsSubmitting(true);
    try {
      await api.updateIncome(parseFloat(incomeInput));
      setIsIncomeModalOpen(false);
      loadHealth();
    } catch (err) {
      alert(err.message || 'Failed to update income');
    } finally {
      setIsSubmitting(false);
    }
  }

  const score = healthData?.health_score || healthData?.score || 72;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <HeartPulse size={24} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Financial Health Diagnostics
            </h1>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Holistic assessment of your liquidity resilience, expense leverage, and savings efficiency
          </p>
        </div>

        <button type="button" className="btn btn-secondary" onClick={() => setIsIncomeModalOpen(true)}>
          <Edit2 size={16} />
          <span>Update Income Base</span>
        </button>
      </div>

      {/* Main Score Hero Card */}
      <div
        className="glass-card"
        style={{
          padding: '2.5rem 2rem',
          marginBottom: '2rem',
          background: 'radial-gradient(ellipse at top right, rgba(200, 169, 110, 0.15) 0%, var(--bg-surface) 70%)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '2rem',
        }}
      >
        <div style={{ maxWidth: '600px' }}>
          <span className="badge badge-gold" style={{ marginBottom: '0.75rem' }}>
            Health Assessment Grade
          </span>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {score >= 80 ? 'Excellent Financial Standing' : score >= 60 ? 'Moderate Resilience' : 'High Expense Vulnerability'}
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            {healthData?.summary ||
              'Your financial ratios indicate consistent cash preservation. Continue diversifying your capital into long-term compounding assets.'}
          </p>
        </div>

        <div style={{ textAlign: 'center', minWidth: '180px' }}>
          <div className="num-mono gold-text" style={{ fontSize: '4rem', fontWeight: 800, lineHeight: 1 }}>
            {score}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '0.25rem' }}>
            Score Out of 100
          </div>
        </div>
      </div>

      {/* Metric Breakdown Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="glass-card">
          <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '1rem' }}>Savings Capacity</h4>
          <ProgressBar
            value={healthData?.savings_ratio || 25}
            max={50}
            label={`Savings Ratio: ${healthData?.savings_ratio || 25}% (Target: 20%+)`}
          />
        </div>

        <div className="glass-card">
          <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '1rem' }}>Expense Pressure</h4>
          <ProgressBar
            value={healthData?.expense_ratio || 65}
            max={100}
            label={`Expense-to-Income: ${healthData?.expense_ratio || 65}%`}
            colorOverride="var(--accent-gold)"
          />
        </div>

        <div className="glass-card">
          <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '1rem' }}>Debt & Obligations</h4>
          <ProgressBar
            value={healthData?.debt_ratio || 15}
            max={50}
            label={`Debt-to-Income: ${healthData?.debt_ratio || 15}% (Safe < 30%)`}
            colorOverride="var(--accent-blue)"
          />
        </div>
      </div>

      {/* AI Recommendations */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={18} color="var(--accent-gold)" />
          <span>Strategic Wealth Recommendations</span>
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {healthData?.recommendations && healthData.recommendations.length > 0 ? (
            healthData.recommendations.map((rec, idx) => (
              <div
                key={idx}
                style={{
                  padding: '1rem 1.25rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  fontSize: '0.875rem',
                }}
              >
                <CheckCircle size={18} color="var(--accent-green)" style={{ marginTop: '2px', flexShrink: 0 }} />
                <span style={{ color: 'var(--text-primary)', lineHeight: '1.5' }}>{rec}</span>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No custom recommendations generated yet. Log more expenses to build a precise behavioral baseline.
            </div>
          )}
        </div>
      </div>

      {/* Income Modal */}
      <Modal
        isOpen={isIncomeModalOpen}
        onClose={() => setIsIncomeModalOpen(false)}
        title="Update Monthly Income"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsIncomeModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleUpdateIncome} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Update Base'}
            </button>
          </>
        }
      >
        <form onSubmit={handleUpdateIncome}>
          <div className="form-group">
            <label className="form-label">Monthly Net Income (₹)</label>
            <input
              type="number"
              className="form-input num-mono"
              placeholder="65000"
              value={incomeInput}
              onChange={(e) => setIncomeInput(e.target.value)}
              required
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
