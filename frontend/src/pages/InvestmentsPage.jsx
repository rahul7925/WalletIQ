import React, { useState, useEffect } from 'react';
import { Plus, TrendingUp, TrendingDown, DollarSign, PieChart, Trash2, Edit2, AlertCircle } from 'lucide-react';
import Modal from '../components/Modal';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

const ASSET_TYPES = ['Stocks', 'Mutual Funds', 'Gold', 'Real Estate', 'Crypto', 'Fixed Deposit', 'Other'];

export default function InvestmentsPage() {
  const [investments, setInvestments] = useState([]);
  const [metrics, setMetrics] = useState({ total_invested: 0, current_value: 0, total_gain_loss: 0, gain_loss_pct: 0 });
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedInv, setSelectedInv] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'Stocks',
    amount: '',
    current_value: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadInvestments() {
    setIsLoading(true);
    try {
      const data = await api.getInvestments();
      setInvestments(data?.investments || data?.items || []);
      setMetrics({
        total_invested: data?.total_invested || 0,
        current_value: data?.current_value || data?.total_current || 0,
        total_gain_loss: data?.total_gain_loss ?? data?.total_gain ?? 0,
        gain_loss_pct: data?.gain_loss_pct ?? data?.gain_pct ?? 0,
      });
    } catch (err) {
      console.error('Failed to load investments', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadInvestments();
  }, []);

  function handleOpenAdd() {
    setSelectedInv(null);
    setFormData({ name: '', type: 'Stocks', amount: '', current_value: '' });
    setError('');
    setIsModalOpen(true);
  }

  function handleOpenEdit(inv) {
    setSelectedInv(inv);
    setFormData({
      name: inv.name,
      type: inv.type,
      amount: inv.amount,
      current_value: inv.current_value !== null ? inv.current_value : inv.amount,
    });
    setError('');
    setIsModalOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!formData.name.trim() || !formData.amount || isNaN(formData.amount)) {
      setError('Please provide a valid asset name and invested amount.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      const payload = {
        name: formData.name.trim(),
        type: formData.type,
        amount: parseFloat(formData.amount),
        current_value: formData.current_value ? parseFloat(formData.current_value) : parseFloat(formData.amount),
      };

      if (selectedInv) {
        await api.updateInvestment(selectedInv.id, payload);
      } else {
        await api.createInvestment(payload);
      }
      setIsModalOpen(false);
      loadInvestments();
    } catch (err) {
      setError(err.message || 'Failed to save asset position');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this investment position?')) return;
    try {
      await api.deleteInvestment(id);
      loadInvestments();
    } catch (err) {
      alert(err.message || 'Failed to delete investment');
    }
  }

  const isProfitable = metrics.total_gain_loss >= 0;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Portfolio & Investments
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Track capital allocation, market value, and unrealized returns
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={handleOpenAdd}>
          <Plus size={16} />
          <span>Add Asset Position</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Total Capital Invested"
          value={`₹${metrics.total_invested.toLocaleString()}`}
          subtitle="Cost basis"
          icon={DollarSign}
          color="gold"
        />
        <StatCard
          title="Current Portfolio Value"
          value={`₹${metrics.current_value.toLocaleString()}`}
          subtitle="Mark to market"
          icon={TrendingUp}
          color="blue"
        />
        <StatCard
          title="Total Unrealized P&L"
          value={`${isProfitable ? '+' : ''}₹${metrics.total_gain_loss.toLocaleString()}`}
          subtitle={`${isProfitable ? '+' : ''}${metrics.gain_loss_pct}% overall return`}
          icon={isProfitable ? TrendingUp : TrendingDown}
          color={isProfitable ? 'green' : 'red'}
        />
      </div>

      {/* Investments Table */}
      <div className="glass-card" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset Name</th>
                <th>Asset Class</th>
                <th style={{ textAlign: 'right' }}>Invested Amount</th>
                <th style={{ textAlign: 'right' }}>Current Value</th>
                <th style={{ textAlign: 'right' }}>P&L Return</th>
                <th style={{ textAlign: 'center', width: '100px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--accent-gold)' }}>
                    Loading investments...
                  </td>
                </tr>
              ) : investments.length > 0 ? (
                investments.map((inv) => {
                  const gain = (inv.current_value || inv.amount) - inv.amount;
                  const gainPct = inv.amount > 0 ? Math.round((gain / inv.amount) * 1000) / 10 : 0;
                  const positive = gain >= 0;

                  return (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{inv.name}</td>
                      <td>
                        <span className="badge badge-purple">{inv.type}</span>
                      </td>
                      <td className="num-mono" style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
                        ₹{Number(inv.amount).toLocaleString()}
                      </td>
                      <td className="num-mono" style={{ textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                        ₹{Number(inv.current_value || inv.amount).toLocaleString()}
                      </td>
                      <td className="num-mono" style={{ textAlign: 'right', fontWeight: 600, color: positive ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {positive ? '+' : ''}₹{gain.toLocaleString()} ({positive ? '+' : ''}{gainPct}%)
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                          <button
                            onClick={() => handleOpenEdit(inv)}
                            style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.25rem' }}
                            title="Edit"
                          >
                            <Edit2 size={15} />
                          </button>
                          <button
                            onClick={() => handleDelete(inv.id)}
                            style={{ background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '0.25rem' }}
                            title="Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No investments logged. Click "Add Asset Position" to record stocks, funds, or assets.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedInv ? 'Edit Asset Position' : 'Add Asset Position'}
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Position'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSave}>
          {error && (
            <div style={{ marginBottom: '1rem', padding: '0.625rem', borderRadius: 'var(--radius-md)', background: 'var(--accent-red-dim)', color: 'var(--accent-red)', fontSize: '0.8125rem' }}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Asset Name *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Nifty 50 Index Fund, Apple Inc"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Asset Class *</label>
            <select
              className="form-select"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            >
              {ASSET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Invested Amount (₹) *</label>
              <input
                type="number"
                step="0.01"
                className="form-input num-mono"
                placeholder="50000"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Current Market Value (₹)</label>
              <input
                type="number"
                step="0.01"
                className="form-input num-mono"
                placeholder="58000"
                value={formData.current_value}
                onChange={(e) => setFormData({ ...formData, current_value: e.target.value })}
              />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}
