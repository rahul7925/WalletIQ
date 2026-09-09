import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShieldCheck, FileSpreadsheet, Download, AlertCircle, Calendar } from 'lucide-react';
import { api } from '../services/api';

export default function SharedReportPage() {
  const { token } = useParams();
  const [reportData, setReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadShared() {
      setIsLoading(true);
      try {
        const data = await api.getSharedReport(token);
        setReportData(data);
      } catch (err) {
        setError(err.message || 'Shared report not found or link has expired.');
      } finally {
        setIsLoading(false);
      }
    }
    if (token) loadShared();
  }, [token]);

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
        <div style={{ color: 'var(--accent-gold)' }}>Loading verified financial statement...</div>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', padding: '2rem' }}>
        <div className="glass-card" style={{ maxWidth: '460px', textAlign: 'center', padding: '3rem 2rem' }}>
          <AlertCircle size={40} color="var(--accent-red)" style={{ margin: '0 auto 1rem' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>Report Unavailable</h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            {error || 'This link may have expired or been revoked by the owner.'}
          </p>
          <Link to="/login" className="btn btn-primary">
            Go to WalletIQ
          </Link>
        </div>
      </div>
    );
  }

  const r = reportData.report || reportData;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', padding: '3rem 1.5rem' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Branding header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(135deg, var(--accent-gold) 0%, #a4813f 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldCheck size={20} color="#0a0a0f" strokeWidth={2.5} />
            </div>
            <div style={{ fontWeight: 700, fontSize: '1.25rem' }}>
              Wallet<span className="gold-text">IQ</span>
            </div>
          </div>

          <span className="badge badge-green">Verified Statement</span>
        </div>

        {/* Statement Box */}
        <div className="glass-card" style={{ padding: '2.5rem' }}>
          <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem', marginBottom: '1.5rem' }}>
            <span className="badge badge-gold" style={{ marginBottom: '0.5rem' }}>
              {(r.format || 'pdf').toUpperCase()} STATEMENT
            </span>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
              {r.title || 'Financial Operations Summary'}
            </h1>
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              <span>Period: {r.month}/{r.year}</span>
              <span>Generated: {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Recent'}</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Total Inflows</span>
              <strong className="num-mono" style={{ fontSize: '1.25rem', color: 'var(--accent-green)' }}>
                ₹{Number(r.total_income || 0).toLocaleString()}
              </strong>
            </div>
            <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Total Outflows</span>
              <strong className="num-mono" style={{ fontSize: '1.25rem', color: 'var(--accent-gold)' }}>
                ₹{Number(r.total_expenses || 0).toLocaleString()}
              </strong>
            </div>
            <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Net Savings</span>
              <strong className="num-mono" style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>
                ₹{Number(r.net_savings || 0).toLocaleString()}
              </strong>
            </div>
          </div>

          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '2rem' }}>
            This cryptographic token grants read access to this specific compiled statement. All proprietary credentials and database mutations remain isolated.
          </p>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <a
              href={api.getDownloadUrl(r.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
            >
              <Download size={16} />
              <span>Download Official Copy</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
