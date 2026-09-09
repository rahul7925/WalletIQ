import React, { useState } from 'react';
import { BadgePercent, ShieldCheck, AlertTriangle, CheckCircle, ArrowRight, Loader2 } from 'lucide-react';
import ProgressBar from '../components/ProgressBar';
import { api } from '../services/api';

export default function LoanEligibilityPage() {
  const [formData, setFormData] = useState({
    loan_amount: '500000',
    loan_term_months: '36',
    monthly_income: '75000',
    credit_score: '750',
    existing_emi: '12000',
    employment_status: 'employed',
  });
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const payload = {
        loan_amount: parseFloat(formData.loan_amount),
        loan_term_months: parseInt(formData.loan_term_months),
        monthly_income: parseFloat(formData.monthly_income),
        credit_score: parseInt(formData.credit_score),
        existing_emi: parseFloat(formData.existing_emi || 0),
        employment_status: formData.employment_status,
      };
      const data = await api.getLoanEligibility(payload);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to evaluate loan eligibility');
    } finally {
      setIsLoading(false);
    }
  }

  const prob = result?.probability !== undefined ? result.probability : result?.approval_probability || 0;
  const isApproved = result?.approved || prob >= 65;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <BadgePercent size={24} color="var(--accent-gold)" />
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            AI Loan Underwriting Assessment
          </h1>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Assess debt capacity, credit risk, and bank underwriting probability prior to applying
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        {/* Form Card */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem' }}>
            Application Parameters
          </h3>

          <form onSubmit={handleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Loan Amount (₹) *</label>
                <input
                  type="number"
                  name="loan_amount"
                  className="form-input num-mono"
                  value={formData.loan_amount}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Tenure (Months) *</label>
                <input
                  type="number"
                  name="loan_term_months"
                  className="form-input num-mono"
                  value={formData.loan_term_months}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Monthly Income (₹) *</label>
                <input
                  type="number"
                  name="monthly_income"
                  className="form-input num-mono"
                  value={formData.monthly_income}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Credit Score (CIBIL) *</label>
                <input
                  type="number"
                  name="credit_score"
                  min="300"
                  max="900"
                  className="form-input num-mono"
                  value={formData.credit_score}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Current Monthly EMIs (₹)</label>
                <input
                  type="number"
                  name="existing_emi"
                  className="form-input num-mono"
                  value={formData.existing_emi}
                  onChange={handleChange}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Employment Status</label>
                <select
                  name="employment_status"
                  className="form-select"
                  value={formData.employment_status}
                  onChange={handleChange}
                >
                  <option value="employed">Salaried (Full-Time)</option>
                  <option value="self_employed">Self-Employed / Business</option>
                  <option value="freelance">Freelance / Contract</option>
                  <option value="unemployed">Unemployed</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Running Credit Risk Model...
                </>
              ) : (
                <>
                  <ShieldCheck size={16} />
                  Evaluate Approval Probability
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results Deck */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem' }}>
              Underwriting Outcome
            </h3>

            {result ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className={`badge ${isApproved ? 'badge-green' : 'badge-red'}`} style={{ fontSize: '0.875rem', padding: '0.35rem 0.8rem' }}>
                    {isApproved ? 'High Approval Likelihood' : 'Elevated Rejection Risk'}
                  </span>
                  <div className="num-mono" style={{ fontSize: '2.25rem', fontWeight: 800, color: isApproved ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {Math.round(prob)}%
                  </div>
                </div>

                <ProgressBar
                  value={prob}
                  max={100}
                  label="Model Confidence Score"
                  colorOverride={isApproved ? 'var(--accent-green)' : 'var(--accent-red)'}
                />

                <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.8125rem', lineHeight: '1.6' }}>
                  {result.recommendations ||
                    (isApproved
                      ? 'Your debt-to-income ratio and credit score are well within prime borrowing tiers.'
                      : 'High debt burden relative to income. Consider lowering loan amount or paying off existing credit cards first.')}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Configure parameters and submit to run our ML underwriting score model.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
