import React, { useState, useEffect } from 'react';
import { Plus, PiggyBank, AlertTriangle, CheckCircle, Trash2, Edit2 } from 'lucide-react';
import Modal from '../components/Modal';
import ProgressBar from '../components/ProgressBar';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

const CATEGORIES = [
  'Food',
  'Transport',
  'Utilities',
  'Entertainment',
  'Shopping',
  'Health',
  'Education',
  'Savings',
  'EMI',
  'General',
];

export default function BudgetsPage() {
  const cachedData = api.getCached ? api.getCached('/budgets') : null;
  const initialBudgets = cachedData?.budgets || [];
  const [budgetList, setBudgetList] = useState(initialBudgets);
  const [isLoading, setIsLoading] = useState(initialBudgets.length === 0);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ category: 'Food', limit_amount: '' });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadBudgets() {
    if (budgetList.length === 0 && initialBudgets.length === 0) setIsLoading(true);
    try {
      const data = await api.getBudgets();
      setBudgetList(data?.budgets || []);
    } catch (err) {
      console.error('Failed to load budgets', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadBudgets();
  }, []);

  function handleOpenModal(initialCategory = 'Food', initialLimit = '') {
    setFormData({ category: initialCategory, limit_amount: initialLimit });
    setError('');
    setIsModalOpen(true);
  }

  async function handleSaveBudget(e) {
    e.preventDefault();
    if (!formData.limit_amount || isNaN(formData.limit_amount) || parseFloat(formData.limit_amount) <= 0) {
      setError('Please enter a valid limit amount greater than 0.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      await api.saveBudget({
        category: formData.category,
        limit_amount: parseFloat(formData.limit_amount),
      });
      setIsModalOpen(false);
      loadBudgets();
    } catch (err) {
      setError(err.message || 'Failed to save budget');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteBudget(id) {
    if (!window.confirm('Delete this budget limit?')) return;
    try {
      await api.deleteBudget(id);
      loadBudgets();
    } catch (err) {
      alert(err.message || 'Failed to delete budget');
    }
  }

  const totalAllocated = budgetList.reduce((acc, b) => acc + (b.limit_amount || 0), 0);
  const totalSpent = budgetList.reduce((acc, b) => acc + (b.spent || 0), 0);
  const overspentCount = budgetList.filter((b) => b.is_overspent).length;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Category Budgets
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Establish and enforce discipline targets per category
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={() => handleOpenModal()}>
          <Plus size={16} />
          <span>Set Budget Limit</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Total Allocated Budget"
          value={`₹${totalAllocated.toLocaleString()}`}
          subtitle="Sum of active limits"
          icon={PiggyBank}
          color="gold"
        />
        <StatCard
          title="Total Spent Under Budgets"
          value={`₹${totalSpent.toLocaleString()}`}
          subtitle={`${totalAllocated > 0 ? Math.round((totalSpent / totalAllocated) * 100) : 0}% of allocated`}
          icon={PiggyBank}
          color={totalSpent > totalAllocated ? 'red' : 'green'}
        />
        <StatCard
          title="Overspent Categories"
          value={overspentCount}
          subtitle={overspentCount > 0 ? 'Exceeding target' : 'All within limits'}
          icon={AlertTriangle}
          color={overspentCount > 0 ? 'red' : 'green'}
        />
      </div>

      {/* Budgets Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {isLoading ? (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--accent-gold)' }}>
            Loading budgets...
          </div>
        ) : budgetList.length > 0 ? (
          budgetList.map((b) => (
            <div key={b.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span className="badge badge-gold" style={{ fontSize: '0.8125rem' }}>
                    {b.category}
                  </span>
                  {b.is_overspent && (
                    <span className="badge badge-red" style={{ marginLeft: '0.5rem' }}>
                      Overspent
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  <button
                    onClick={() => handleOpenModal(b.category, b.limit_amount)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem' }}
                    title="Edit Limit"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => handleDeleteBudget(b.id)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '0.25rem' }}
                    title="Delete Budget"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Spent</span>
                  <div className="num-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: b.is_overspent ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                    ₹{Number(b.spent || 0).toLocaleString()}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Limit</span>
                  <div className="num-mono" style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    ₹{Number(b.limit_amount).toLocaleString()}
                  </div>
                </div>
              </div>

              <ProgressBar value={b.spent || 0} max={b.limit_amount} />

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Remaining: ₹{Math.max(0, b.remaining || 0).toLocaleString()}</span>
                <span>{b.progress_pct}%</span>
              </div>
            </div>
          ))
        ) : (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
            No category budgets created yet. Click "Set Budget Limit" to allocate spending targets.
          </div>
        )}
      </div>

      {/* Set Budget Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Set Category Budget"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSaveBudget} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Set Limit'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSaveBudget}>
          {error && (
            <div style={{ marginBottom: '1rem', padding: '0.625rem', borderRadius: 'var(--radius-md)', background: 'var(--accent-red-dim)', color: 'var(--accent-red)', fontSize: '0.8125rem' }}>
              {error}
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Category</label>
            <select
              className="form-select"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Monthly Limit Amount (₹)</label>
            <input
              type="number"
              className="form-input num-mono"
              placeholder="e.g. 12000"
              value={formData.limit_amount}
              onChange={(e) => setFormData({ ...formData, limit_amount: e.target.value })}
              required
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
