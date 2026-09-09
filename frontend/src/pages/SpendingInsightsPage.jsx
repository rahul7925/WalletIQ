import React, { useState, useEffect } from 'react';
import { Sparkles, AlertTriangle, Repeat, TrendingUp, ShieldCheck, CheckCircle } from 'lucide-react';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function SpendingInsightsPage() {
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadInsights() {
      setIsLoading(true);
      try {
        const data = await api.getSpendingInsights();
        if (isMounted) setInsights(data);
      } catch (err) {
        console.error('Failed to load insights', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadInsights();
    return () => {
      isMounted = false;
    };
  }, []);

  const anomalies = insights?.anomalies || [];
  const subscriptions = insights?.subscriptions || [];
  const fastestGrowing = insights?.fastest_growing_category || 'None';
  const recommendations = insights?.recommendations || [];

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <Sparkles size={24} color="var(--accent-gold)" />
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Behavioral Spending Insights
          </h1>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Automated pattern recognition identifying cash leaks, subscriptions, and rapid expenditure drift
        </p>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Detected Anomalies"
          value={anomalies.length}
          subtitle={anomalies.length > 0 ? 'Unusual deviations' : 'Baseline normal'}
          icon={AlertTriangle}
          color={anomalies.length > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="Active Subscriptions"
          value={subscriptions.length}
          subtitle="Recurring monthly debit"
          icon={Repeat}
          color="purple"
        />
        <StatCard
          title="Fastest Escalating Area"
          value={fastestGrowing}
          subtitle="Highest month-over-month growth"
          icon={TrendingUp}
          color="gold"
        />
      </div>

      {/* Grid: Anomalies & Subscriptions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Outliers */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={18} color="var(--accent-red)" />
            <span>Unusual Spending Spikes</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {anomalies.length > 0 ? (
              anomalies.map((anom, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.875rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-red-dim)',
                    border: '1px solid rgba(255, 100, 100, 0.3)',
                    fontSize: '0.8125rem',
                    color: 'var(--text-primary)',
                    lineHeight: '1.5',
                  }}
                >
                  {typeof anom === 'string' ? anom : JSON.stringify(anom)}
                </div>
              ))
            ) : (
              <div style={{ padding: '1.5rem 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                No spending spikes detected. All purchases align with historic baselines.
              </div>
            )}
          </div>
        </div>

        {/* Subscriptions */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Repeat size={18} color="var(--accent-purple)" />
            <span>Recurring Digital Subscriptions</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {subscriptions.length > 0 ? (
              subscriptions.map((sub, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.875rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{sub.name || sub.title || 'Subscription'}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sub.frequency || 'Monthly'}</div>
                  </div>
                  <div className="num-mono" style={{ fontWeight: 600, color: 'var(--accent-gold)' }}>
                    ₹{Number(sub.amount || 0).toLocaleString()}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '1.5rem 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                No active subscription duplicates detected.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle size={18} color="var(--accent-green)" />
          <span>Optimization Recommendations</span>
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {recommendations.length > 0 ? (
            recommendations.map((rec, idx) => (
              <div
                key={idx}
                style={{
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.875rem',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                }}
              >
                <span className="badge badge-gold" style={{ marginTop: '2px' }}>Insight</span>
                <span>{rec}</span>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Add more monthly transactions to unlock deep behavioral optimization prompts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
