import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Zap,
  ShieldCheck,
  AlertTriangle,
  Calendar,
  TrendingUp,
  Receipt,
  Bot,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import ProgressBar from '../components/ProgressBar';
import { api } from '../services/api';

export default function CommandCenterPage() {
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadAll() {
      setIsLoading(true);
      try {
        const [dashRes, healthRes, insightsRes] = await Promise.all([
          api.getDashboardSummary().catch(() => null),
          api.getFinancialHealth().catch(() => null),
          api.getSpendingInsights().catch(() => null),
        ]);
        if (isMounted) {
          setData(dashRes);
          setHealth(healthRes);
          setInsights(insightsRes);
        }
      } catch (err) {
        console.error('Command center loading error', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadAll();
    return () => {
      isMounted = false;
    };
  }, []);

  const healthScore = health?.health_score || health?.score || 72;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Zap size={22} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Financial Command Center
            </h1>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Unified real-time telemetry across liquidity, health score, obligations, and AI alerts
          </p>
        </div>

        <Link to="/ai-advisor" className="btn btn-primary">
          <Bot size={16} />
          <span>Launch AI Copilot</span>
        </Link>
      </div>

      {/* Primary KPI Deck */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Financial Health Score"
          value={`${healthScore} / 100`}
          subtitle={healthScore >= 75 ? 'Strong Posture' : healthScore >= 50 ? 'Moderate Risk' : 'Action Required'}
          icon={ShieldCheck}
          color={healthScore >= 75 ? 'green' : healthScore >= 50 ? 'gold' : 'red'}
        />
        <StatCard
          title="Monthly Outflow"
          value={`₹${(data?.total_spent || 0).toLocaleString()}`}
          subtitle={`${data?.budget_progress || 0}% budget used`}
          icon={Receipt}
          color="gold"
        />
        <StatCard
          title="Pending Obligations"
          value={data?.overdue_bills_count || 0}
          subtitle="Unpaid recurring bills"
          icon={Calendar}
          color={data?.overdue_bills_count > 0 ? 'red' : 'blue'}
        />
      </div>

      {/* Grid: Health Telemetry & High Priority Insights */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Health Score Gauge Box */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Liquidity & Stability Audit</h3>
            <Link to="/financial-health" style={{ fontSize: '0.8125rem', color: 'var(--accent-gold)' }}>
              Deep Dive
            </Link>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <ProgressBar
                value={healthScore}
                max={100}
                label="Aggregate Stability Index"
                showPercent={true}
              />
            </div>

            <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.8125rem' }}>
              <div style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                {health?.summary || 'Your cash reserves and spending velocity are actively monitored. Maintain a savings rate above 20% to optimize score.'}
              </div>
              {health?.recommendations && health.recommendations.length > 0 && (
                <div style={{ color: 'var(--accent-gold)', fontWeight: 500 }}>
                  Top recommendation: {health.recommendations[0]}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* AI Anomaly & Spending Alerts */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Active Intelligence Alerts</h3>
            <Link to="/spending-insights" style={{ fontSize: '0.8125rem', color: 'var(--accent-gold)' }}>
              All Insights
            </Link>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {insights?.anomalies && insights.anomalies.length > 0 ? (
              insights.anomalies.slice(0, 3).map((anom, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.875rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-red-dim)',
                    border: '1px solid rgba(255, 100, 100, 0.3)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.75rem',
                  }}
                >
                  <AlertTriangle size={16} color="var(--accent-red)" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>{anom}</div>
                </div>
              ))
            ) : (
              <div
                style={{
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--accent-green-dim)',
                  border: '1px solid rgba(0, 214, 143, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  fontSize: '0.8125rem',
                  color: 'var(--accent-green)',
                }}
              >
                <ShieldCheck size={18} />
                <span>No severe anomalies detected. Cash flows are operating normally.</span>
              </div>
            )}

            {insights?.recommendations && insights.recommendations.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                {insights.recommendations.slice(0, 2).map((rec, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                    <Sparkles size={14} color="var(--accent-gold)" style={{ marginTop: '3px', flexShrink: 0 }} />
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
