import React, { useState, useEffect } from 'react';
import { LineChart, Sparkles, TrendingUp, Save, CheckCircle, AlertCircle } from 'lucide-react';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function SavingsPredictionPage() {
  const [horizon, setHorizon] = useState(6);
  const [extraDeposit, setExtraDeposit] = useState(5000);
  const [returnRate, setReturnRate] = useState(8);
  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  async function calculatePrediction() {
    setIsLoading(true);
    try {
      const data = await api.getSavingsPrediction(horizon, extraDeposit, returnRate);
      setPrediction(data);
    } catch (err) {
      console.error('Failed to compute forecast', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    calculatePrediction();
  }, [horizon, extraDeposit, returnRate]);

  async function handleSaveScenario() {
    try {
      await api.saveSavingsPrediction({
        horizon_months: horizon,
        extra_deposit: extraDeposit,
        return_rate: returnRate,
        projected_savings: prediction?.projected_savings || 0,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert(err.message || 'Failed to save prediction scenario');
    }
  }

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <LineChart size={24} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              ML Savings Forecaster
            </h1>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Simulate future wealth accumulation with machine-learning velocity curves and compounding yield
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={handleSaveScenario} disabled={!prediction}>
          <Save size={16} />
          <span>Save Simulation</span>
        </button>
      </div>

      {saveSuccess && (
        <div
          style={{
            marginBottom: '1.5rem',
            padding: '0.75rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            background: 'var(--accent-green-dim)',
            border: '1px solid rgba(0, 214, 143, 0.3)',
            color: 'var(--accent-green)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle size={16} />
          <span>Simulation scenario saved to your portfolio history!</span>
        </div>
      )}

      {/* Control Sliders & Result Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Controls Card */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.5rem' }}>
            Simulation Parameters
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Horizon */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Forecast Horizon</span>
                <strong className="num-mono" style={{ color: 'var(--accent-gold)' }}>{horizon} Months</strong>
              </div>
              <input
                type="range"
                min="3"
                max="36"
                step="3"
                value={horizon}
                onChange={(e) => setHorizon(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-gold)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                <span>3 mo</span>
                <span>12 mo</span>
                <span>24 mo</span>
                <span>36 mo</span>
              </div>
            </div>

            {/* Extra Monthly Contribution */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Additional Monthly Deposit</span>
                <strong className="num-mono" style={{ color: 'var(--accent-gold)' }}>₹{extraDeposit.toLocaleString()}</strong>
              </div>
              <input
                type="range"
                min="0"
                max="50000"
                step="1000"
                value={extraDeposit}
                onChange={(e) => setExtraDeposit(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-gold)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                <span>₹0</span>
                <span>₹25,000</span>
                <span>₹50,000</span>
              </div>
            </div>

            {/* Return Rate */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Estimated Annual Yield (CAGR)</span>
                <strong className="num-mono" style={{ color: 'var(--accent-gold)' }}>{returnRate}%</strong>
              </div>
              <input
                type="range"
                min="0"
                max="18"
                step="1"
                value={returnRate}
                onChange={(e) => setReturnRate(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-gold)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                <span>0% (Cash)</span>
                <span>8% (Index)</span>
                <span>18% (Equities)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Prediction Results Card */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <span className="badge badge-gold" style={{ marginBottom: '0.75rem' }}>
              Projected Capital Velocity
            </span>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Estimated total capital accumulated at the end of {horizon} months:
            </div>

            <div className="num-mono gold-text" style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '1rem', lineHeight: 1 }}>
              ₹{Number(prediction?.projected_savings || 0).toLocaleString()}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Baseline Savings</span>
                <div className="num-mono" style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  ₹{Number(prediction?.baseline_savings || 0).toLocaleString()}
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Compounding Interest</span>
                <div className="num-mono" style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--accent-green)' }}>
                  +₹{Number(prediction?.interest_earned || 0).toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          <div
            style={{
              padding: '1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-color)',
              fontSize: '0.8125rem',
              color: 'var(--text-secondary)',
              marginTop: '1.5rem',
            }}
          >
            💡 By dedicating an extra ₹{extraDeposit.toLocaleString()}/month into an {returnRate}% asset, you generate{' '}
            <strong style={{ color: 'var(--accent-gold)' }}>
              ₹{Number((prediction?.projected_savings || 0) - (prediction?.baseline_savings || 0)).toLocaleString()}
            </strong>{' '}
            in excess wealth.
          </div>
        </div>
      </div>
    </div>
  );
}
