import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Plus,
  Download,
  Share2,
  Trash2,
  GitCompare,
  Sparkles,
  CheckCircle,
  FileText,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import Modal from '../components/Modal';
import { api } from '../services/api';

export default function ReportStudioPage() {
  const cachedReports = api.getCached ? api.getCached('/reports') : null;
  const initialReports = cachedReports?.reports || [];
  const [reports, setReports] = useState(initialReports);
  const [isLoading, setIsLoading] = useState(initialReports.length === 0);

  // Modals & Action States
  const [isGenModalOpen, setIsGenModalOpen] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);
  const [genData, setGenData] = useState({
    format: 'pdf',
    month: new Date().getMonth() + 1,
    year: new Date().getFullYear(),
  });
  const [compareIds, setCompareIds] = useState({ id1: '', id2: '' });
  const [comparisonResult, setComparisonResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  function showToast(msg) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3500);
  }

  async function loadReports() {
    if (reports.length === 0 && initialReports.length === 0) setIsLoading(true);
    try {
      const data = await api.getReports();
      setReports(data?.reports || []);
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
    if (e) e.preventDefault();
    setIsProcessing(true);
    try {
      await api.generateReport(genData);
      setIsGenModalOpen(false);
      showToast('Document compiled successfully!');
      loadReports();
    } catch (err) {
      alert(err.message || 'Failed to generate report');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleQuickGenerate(format = 'pdf') {
    setIsProcessing(true);
    try {
      const now = new Date();
      await api.generateReport({
        format,
        month: now.getMonth() + 1,
        year: now.getFullYear(),
      });
      showToast(`${format.toUpperCase()} report generated!`);
      loadReports();
    } catch (err) {
      alert(err.message || 'Failed to generate statement');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDownload(id, fallbackName, format) {
    setDownloadingId(id);
    try {
      const downloadUrl = api.getDownloadUrl(id);
      const token = localStorage.getItem('walletiq_token');
      const res = await fetch(downloadUrl, {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        throw new Error(`Download failed with status ${res.status}`);
      }

      let filename = fallbackName;
      const disposition = res.headers.get('content-disposition');
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '');
        }
      }
      if (!filename) {
        const ext = format === 'excel' ? 'xlsx' : 'pdf';
        filename = `WalletIQ_Report_${id}.${ext}`;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast(`Downloaded: ${filename}`);
    } catch (err) {
      alert(err.message || 'Failed to download report');
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleShare(id) {
    try {
      const res = await api.shareReport(id);
      const token = res?.share_key || res?.share_token || res?.token;
      const origin = window.location.origin;
      const link = `${origin}/shared/${token}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(link);
        showToast('Share link copied to clipboard!');
      } else {
        alert(`Report share link:\n${link}`);
      }
    } catch (err) {
      alert(err.message || 'Failed to generate share link');
    }
  }

  function openCompareModal() {
    if (reports.length >= 2) {
      setCompareIds({
        id1: String(reports[1].id),
        id2: String(reports[0].id),
      });
    } else if (reports.length === 1) {
      setCompareIds({ id1: String(reports[0].id), id2: '' });
    }
    setComparisonResult(null);
    setIsCompareModalOpen(true);
  }

  async function handleCompare(e) {
    if (e) e.preventDefault();
    if (!compareIds.id1 || !compareIds.id2) {
      alert('Please select both statements to compare.');
      return;
    }
    if (compareIds.id1 === compareIds.id2) {
      alert('Please select two different statements for comparative analysis.');
      return;
    }
    setIsProcessing(true);
    try {
      const data = await api.compareReports(parseInt(compareIds.id1, 10), parseInt(compareIds.id2, 10));
      setComparisonResult(data);
    } catch (err) {
      alert(err.message || 'Failed to perform AI comparative review');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Are you sure you want to permanently delete this report archive?')) return;
    setDeletingId(id);
    try {
      await api.deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      showToast('Report archive deleted.');
      loadReports();
    } catch (err) {
      alert(err.message || 'Failed to delete report');
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="page-wrapper animate-fade">
      {/* Toast feedback banner */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: '1.5rem',
            right: '1.5rem',
            zIndex: 9999,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--accent-gold)',
            color: 'var(--text-primary)',
            padding: '0.75rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: 500,
          }}
        >
          <CheckCircle size={16} color="var(--accent-gold)" />
          <span>{toastMessage}</span>
        </div>
      )}

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

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={openCompareModal}
            disabled={reports.length < 2}
            title={reports.length < 2 ? 'Generate at least 2 reports to enable AI comparison' : 'Compare two reports side-by-side'}
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
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report Title / Period</th>
                <th>Format</th>
                <th>File Size</th>
                <th>Generated On</th>
                <th style={{ textAlign: 'center', width: '170px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--accent-gold)' }}>
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Loading report archive...</span>
                    </div>
                  </td>
                </tr>
              ) : reports.length > 0 ? (
                reports.map((r) => {
                  const isPdf = (r.format || '').toLowerCase() === 'pdf';
                  const title = r.title || r.report_name || r.name || 'Financial Statement';
                  const isThisDownloading = downloadingId === r.id;
                  const isThisDeleting = deletingId === r.id;

                  return (
                    <tr key={r.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {isPdf ? <FileText size={16} color="var(--accent-gold)" /> : <FileSpreadsheet size={16} color="#10B981" />}
                          <span>{title}</span>
                          {r.version > 1 && (
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', border: '1px solid var(--border-color)', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                              v{r.version}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                          Period: {r.month}/{r.year} {r.download_count > 0 && `• ${r.download_count} download${r.download_count > 1 ? 's' : ''}`}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${isPdf ? 'badge-gold' : 'badge-green'}`}>
                          {isPdf ? 'PDF' : 'EXCEL (.XLSX)'}
                        </span>
                      </td>
                      <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                        {r.file_size ? `${Math.round(r.file_size / 1024)} KB` : '—'}
                      </td>
                      <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                        {r.generated_date || r.created_at
                          ? new Date(r.generated_date || r.created_at).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })
                          : 'Recent'}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center' }}>
                          {/* 1-Click Download Button */}
                          <button
                            onClick={() => handleDownload(r.id, r.file_name || `${title}.${isPdf ? 'pdf' : 'xlsx'}`, r.format)}
                            className="btn btn-sm btn-secondary"
                            style={{
                              padding: '0.35rem 0.65rem',
                              borderColor: 'var(--accent-gold)',
                              color: 'var(--accent-gold)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                            }}
                            title="1-Click Download to Device"
                            disabled={isThisDownloading}
                          >
                            {isThisDownloading ? (
                              <Loader2 size={13} className="animate-spin" />
                            ) : (
                              <Download size={13} />
                            )}
                            <span style={{ fontSize: '0.75rem' }}>Download</span>
                          </button>

                          {/* Share Link Button */}
                          <button
                            onClick={() => handleShare(r.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                              padding: '0.35rem',
                              display: 'inline-flex',
                              alignItems: 'center',
                            }}
                            title="Share Link"
                          >
                            <Share2 size={15} />
                          </button>

                          {/* Delete / Archive Button */}
                          <button
                            onClick={() => handleDelete(r.id)}
                            disabled={isThisDeleting}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--accent-red)',
                              cursor: 'pointer',
                              padding: '0.35rem',
                              display: 'inline-flex',
                              alignItems: 'center',
                              opacity: isThisDeleting ? 0.4 : 1,
                            }}
                            title="Delete / Clean Archive"
                          >
                            {isThisDeleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
                    <FileSpreadsheet size={40} color="var(--accent-gold)" style={{ margin: '0 auto 1rem', opacity: 0.7 }} />
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>No Reports in Archive</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem', maxWidth: '420px', margin: '0 auto 1.5rem' }}>
                      Generate audit-grade PDF financial statements or downloadable Excel workbooks for any month.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => handleQuickGenerate('pdf')}
                        disabled={isProcessing}
                      >
                        <Plus size={14} />
                        <span>Generate Current Month PDF</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleQuickGenerate('excel')}
                        disabled={isProcessing}
                      >
                        <FileSpreadsheet size={14} />
                        <span>Generate Excel (.xlsx)</span>
                      </button>
                    </div>
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
        maxWidth="720px"
        footer={
          <button type="button" className="btn btn-secondary" onClick={() => setIsCompareModalOpen(false)}>
            Close
          </button>
        }
      >
        <form onSubmit={handleCompare} style={{ marginBottom: '1.25rem' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Select any two monthly reports to run a side-by-side AI comparative analysis highlighting spending drift, cash leakages, and savings trends.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Base Period (Period A)</label>
              <select
                className="form-select"
                value={compareIds.id1}
                onChange={(e) => setCompareIds({ ...compareIds, id1: e.target.value })}
                required
              >
                <option value="">Select statement...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title || r.report_name} ({r.month}/{r.year})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Target Period (Period B)</label>
              <select
                className="form-select"
                value={compareIds.id2}
                onChange={(e) => setCompareIds({ ...compareIds, id2: e.target.value })}
                required
              >
                <option value="">Select statement...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title || r.report_name} ({r.month}/{r.year})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Running Comparative Variance Engine...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Run AI Comparative Review</span>
              </>
            )}
          </button>
        </form>

        {comparisonResult && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* 4 Side-by-Side KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
              {/* Income */}
              <div style={{ background: 'var(--bg-elevated)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Income</div>
                <div style={{ fontSize: '1rem', fontWeight: 700 }} className="num-mono">
                  ₹{(comparisonResult.income?.b || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: '0.75rem', color: (comparisonResult.income?.diff || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '0.2rem' }}>
                  {comparisonResult.income?.diff >= 0 ? '+' : ''}{comparisonResult.income?.pct}% vs A
                </div>
              </div>

              {/* Total Expenses / Spending Drift */}
              <div style={{ background: 'var(--bg-elevated)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Expenses (Drift)</div>
                <div style={{ fontSize: '1rem', fontWeight: 700 }} className="num-mono">
                  ₹{(comparisonResult.expenses?.b || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: '0.75rem', color: (comparisonResult.expenses?.diff || 0) <= 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '0.2rem' }}>
                  {comparisonResult.expenses?.diff > 0 ? '+' : ''}{comparisonResult.expenses?.pct}% drift
                </div>
              </div>

              {/* Net Savings */}
              <div style={{ background: 'var(--bg-elevated)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Net Savings</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-green)' }} className="num-mono">
                  ₹{(comparisonResult.savings?.b || 0).toLocaleString()}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', marginTop: '0.2rem' }}>
                  Rate: {comparisonResult.rate_b || 0}%
                </div>
              </div>

              {/* Financial Health */}
              <div style={{ background: 'var(--bg-elevated)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Health Score</div>
                <div style={{ fontSize: '1rem', fontWeight: 700 }} className="num-mono">
                  {comparisonResult.health_score?.b || 0}/100
                </div>
                <div style={{ fontSize: '0.75rem', color: (comparisonResult.health_score?.diff || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '0.2rem' }}>
                  {comparisonResult.health_score?.diff >= 0 ? '+' : ''}{comparisonResult.health_score?.diff || 0} pts
                </div>
              </div>
            </div>

            {/* Cash Leakages alert banner if any */}
            {comparisonResult.leakages && comparisonResult.leakages.length > 0 ? (
              <div
                style={{
                  padding: '0.75rem 1rem',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.65rem',
                }}
              >
                <AlertTriangle size={18} color="var(--accent-red)" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--accent-red)', marginBottom: '0.2rem' }}>
                    Cash Leakage Spikes Flagged ({comparisonResult.leakages.length})
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                    {comparisonResult.leakages.map((l, idx) => (
                      <span key={l.category}>
                        <strong>{l.category}</strong>: +₹{l.diff.toLocaleString()} (+{l.pct}%)
                        {idx < comparisonResult.leakages.length - 1 ? ' • ' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div
                style={{
                  padding: '0.6rem 0.85rem',
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.8rem',
                  color: 'var(--accent-green)',
                }}
              >
                <CheckCircle size={15} />
                <span>No critical cash leakage spikes detected between these two periods.</span>
              </div>
            )}

            {/* AI Narrative Breakdown */}
            <div
              style={{
                padding: '1.25rem',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
              }}
            >
              <h4
                style={{
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  color: 'var(--accent-gold)',
                  marginBottom: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <Sparkles size={16} />
                <span>Comparative AI Findings & Action Directives</span>
              </h4>
              <div
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--text-primary)',
                  lineHeight: '1.65',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {comparisonResult.narrative || comparisonResult.analysis || comparisonResult.comparison}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
