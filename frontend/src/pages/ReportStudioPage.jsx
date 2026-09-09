import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, Plus, Download, Share2, Trash2, GitCompare, Sparkles, CheckCircle, FileText, Loader2 } from 'lucide-react';
import Modal from '../components/Modal';
import { api } from '../services/api';

export default function ReportStudioPage() {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isGenModalOpen, setIsGenModalOpen] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);
  const [genData, setGenData] = useState({ format: 'pdf', month: new Date().getMonth() + 1, year: new Date().getFullYear() });
  const [compareIds, setCompareIds] = useState({ id1: '', id2: '' });
  const [comparisonResult, setComparisonResult] = useState(null);
  const [sharedLink, setSharedLink] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  async function loadReports() {
    setIsLoading(true);
    try {
      const data = await api.getReports();
      setReports(data.reports || []);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  async function handleGenerate(e) {
    e.preventDefault();
    setIsProcessing(true);
    try {
      await api.generateReport(genData);
      setIsGenModalOpen(false);
      loadReports();
    } catch (err) {
      alert(err.message || 'Failed to generate report');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDownload(id, filename) {
    try {
      const downloadUrl = api.getDownloadUrl(id);
      const token = localStorage.getItem('walletiq_token');
      const res = await fetch(downloadUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `walletiq_report_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || 'Failed to download report');
    }
  }

  async function handleShare(id) {
    try {
      const res = await api.shareReport(id);
      const token = res?.share_token || res?.token;
      const origin = window.location.origin;
      const link = `${origin}/shared/${token}`;
      setSharedLink(link);
      navigator.clipboard?.writeText(link);
      alert(`Report shared! Link copied to clipboard:\n${link}`);
    } catch (err) {
      alert(err.message || 'Failed to generate share link');
    }
  }

  async function handleCompare(e) {
    e.preventDefault();
    if (!compareIds.id1 || !compareIds.id2) return;
    setIsProcessing(true);
    try {
      const data = await api.compareReports(parseInt(compareIds.id1), parseInt(compareIds.id2));
      setComparisonResult(data);
    } catch (err) {
      alert(err.message || 'Failed to compare reports');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this report archive?')) return;
    try {
      await api.deleteReport(id);
      loadReports();
    } catch (err) {
      alert(err.message || 'Failed to delete report');
    }
  }

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <FileSpreadsheet size={24} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Report Studio & Export Engine
            </h1>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Compile audit-grade PDF financial statements, Excel workbooks, and comparative AI reviews
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setComparisonResult(null);
              setIsCompareModalOpen(true);
            }}
            disabled={reports.length < 2}
          >
            <GitCompare size={16} />
            <span>AI Comparative Review</span>
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setIsGenModalOpen(true)}>
            <Plus size={16} />
            <span>Generate Statement</span>
          </button>
        </div>
      </div>

      {/* Reports Table */}
      <div className="glass-card" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report Title / Period</th>
                <th>Format</th>
                <th>File Size</th>
                <th>Generated On</th>
                <th style={{ textAlign: 'center', width: '160px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--accent-gold)' }}>
                    Loading report archive...
                  </td>
                </tr>
              ) : reports.length > 0 ? (
                reports.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.title || r.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Month: {r.month}/{r.year}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${r.format === 'pdf' ? 'badge-gold' : 'badge-green'}`}>
                        {(r.format || 'pdf').toUpperCase()}
                      </span>
                    </td>
                    <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                      {r.file_size ? `${Math.round(r.file_size / 1024)} KB` : 'N/A'}
                    </td>
                    <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center' }}>
                        <button
                          onClick={() => handleDownload(r.id, `${r.title || 'report'}.${r.format || 'pdf'}`)}
                          className="btn btn-sm btn-secondary"
                          style={{ padding: '0.25rem 0.5rem' }}
                          title="Download"
                        >
                          <Download size={14} />
                        </button>
                        <button
                          onClick={() => handleShare(r.id)}
                          style={{ background: 'transparent', border: 'none', color: 'var(--accent-gold)', cursor: 'pointer', padding: '0.25rem' }}
                          title="Share Link"
                        >
                          <Share2 size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(r.id)}
                          style={{ background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '0.25rem' }}
                          title="Delete"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No reports generated yet. Click "Generate Statement" to create your first PDF/Excel report.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generate Modal */}
      <Modal
        isOpen={isGenModalOpen}
        onClose={() => setIsGenModalOpen(false)}
        title="Generate Financial Statement"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsGenModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleGenerate} disabled={isProcessing}>
              {isProcessing ? 'Generating Document...' : 'Compile Document'}
            </button>
          </>
        }
      >
        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label className="form-label">Format</label>
            <select
              className="form-select"
              value={genData.format}
              onChange={(e) => setGenData({ ...genData, format: e.target.value })}
            >
              <option value="pdf">PDF Statement (With Visuals & Charts)</option>
              <option value="excel">Excel Workbook (.xlsx)</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Month</label>
              <select
                className="form-select"
                value={genData.month}
                onChange={(e) => setGenData({ ...genData, month: parseInt(e.target.value) })}
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    {new Date(2026, m - 1, 1).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Year</label>
              <input
                type="number"
                className="form-input num-mono"
                value={genData.year}
                onChange={(e) => setGenData({ ...genData, year: parseInt(e.target.value) })}
              />
            </div>
          </div>
        </form>
      </Modal>

      {/* Compare Modal */}
      <Modal
        isOpen={isCompareModalOpen}
        onClose={() => setIsCompareModalOpen(false)}
        title="AI Comparative Statement Review"
        maxWidth="650px"
        footer={
          <button type="button" className="btn btn-secondary" onClick={() => setIsCompareModalOpen(false)}>
            Close
          </button>
        }
      >
        <form onSubmit={handleCompare} style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Period A Report</label>
              <select
                className="form-select"
                value={compareIds.id1}
                onChange={(e) => setCompareIds({ ...compareIds, id1: e.target.value })}
                required
              >
                <option value="">Select statement...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title || `Statement #${r.id} (${r.month}/${r.year})`}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Period B Report</label>
              <select
                className="form-select"
                value={compareIds.id2}
                onChange={(e) => setCompareIds({ ...compareIds, id2: e.target.value })}
                required
              >
                <option value="">Select statement...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title || `Statement #${r.id} (${r.month}/${r.year})`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={isProcessing}>
            {isProcessing ? 'Analyzing Velocity...' : 'Generate AI Variance Analysis'}
          </button>
        </form>

        {comparisonResult && (
          <div style={{ padding: '1.25rem', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-gold)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={16} />
              <span>Comparative AI Findings</span>
            </h4>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
              {comparisonResult.analysis || comparisonResult.comparison || 'Variance calculated successfully between periods.'}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
