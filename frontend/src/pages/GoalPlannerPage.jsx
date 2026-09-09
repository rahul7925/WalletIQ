import React, { useState, useEffect } from 'react';
import { Target, Plus, CheckCircle, Sparkles, Trash2, Edit3 } from 'lucide-react';
import Modal from '../components/Modal';
import ProgressBar from '../components/ProgressBar';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function GoalPlannerPage() {
  const [goals, setGoals] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSavingsModalOpen, setIsSavingsModalOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState(null);

  const [formData, setFormData] = useState({
    title: '',
    target_amount: '',
    current_amount: '0',
    target_date: '',
  });
  const [savingsInput, setSavingsInput] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadGoals() {
    setIsLoading(true);
    try {
      const [goalRes, recRes] = await Promise.all([
        api.getGoals(),
        api.getGoalRecommendations().catch(() => null),
      ]);
      setGoals(goalRes.goals || []);
      setRecommendations(recRes?.recommendations || []);
    } catch (err) {
      console.error('Failed to load goals', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadGoals();
  }, []);

  async function handleCreateGoal(e) {
    e.preventDefault();
    if (!formData.title.trim() || !formData.target_amount || isNaN(formData.target_amount)) {
      setError('Please provide a valid goal title and target amount.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      await api.createGoal({
        title: formData.title.trim(),
        target_amount: parseFloat(formData.target_amount),
        current_amount: parseFloat(formData.current_amount || 0),
        target_date: formData.target_date || null,
      });
      setIsAddModalOpen(false);
      loadGoals();
    } catch (err) {
      setError(err.message || 'Failed to create goal');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleUpdateSavings(e) {
    e.preventDefault();
    if (!savingsInput || isNaN(savingsInput)) return;

    setIsSubmitting(true);
    try {
      await api.updateGoalSavings(selectedGoal.id, {
        current_amount: parseFloat(savingsInput),
      });
      setIsSavingsModalOpen(false);
      loadGoals();
    } catch (err) {
      alert(err.message || 'Failed to update goal progress');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteGoal(id) {
    if (!window.confirm('Delete this financial goal?')) return;
    try {
      await api.deleteGoal(id);
      loadGoals();
    } catch (err) {
      alert(err.message || 'Failed to delete goal');
    }
  }

  const totalTarget = goals.reduce((acc, g) => acc + (g.target_amount || 0), 0);
  const totalSaved = goals.reduce((acc, g) => acc + (g.current_amount || 0), 0);

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Target size={24} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Strategic Goal Planner
            </h1>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Set capital milestones, compute monthly roadmaps, and automate trajectory tracking
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={() => setIsAddModalOpen(true)}>
          <Plus size={16} />
          <span>Define New Goal</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Total Goals Target"
          value={`₹${totalTarget.toLocaleString()}`}
          subtitle={`${goals.length} Active targets`}
          icon={Target}
          color="gold"
        />
        <StatCard
          title="Total Capital Accumulated"
          value={`₹${totalSaved.toLocaleString()}`}
          subtitle={`${totalTarget > 0 ? Math.round((totalSaved / totalTarget) * 100) : 0}% achieved`}
          icon={CheckCircle}
          color="green"
        />
      </div>

      {/* Goals Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {isLoading ? (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--accent-gold)' }}>
            Loading goals...
          </div>
        ) : goals.length > 0 ? (
          goals.map((g) => {
            const pct = Math.min(Math.round(((g.current_amount || 0) / (g.target_amount || 1)) * 100), 100);
            return (
              <div key={g.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>{g.title}</h3>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button
                      onClick={() => {
                        setSelectedGoal(g);
                        setSavingsInput(g.current_amount || 0);
                        setIsSavingsModalOpen(true);
                      }}
                      style={{ background: 'transparent', border: 'none', color: 'var(--accent-gold)', cursor: 'pointer', padding: '0.25rem' }}
                      title="Update Savings"
                    >
                      <Edit3 size={15} />
                    </button>
                    <button
                      onClick={() => handleDeleteGoal(g.id)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '0.25rem' }}
                      title="Delete Goal"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Saved</span>
                    <div className="num-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-green)' }}>
                      ₹{Number(g.current_amount || 0).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target</span>
                    <div className="num-mono" style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      ₹{Number(g.target_amount).toLocaleString()}
                    </div>
                  </div>
                </div>

                <ProgressBar value={g.current_amount || 0} max={g.target_amount} />

                {g.target_date && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Target Date: {g.target_date}
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
            No goals created yet. Click "Define New Goal" to start planning milestones.
          </div>
        )}
      </div>

      {/* Add Goal Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Define Financial Goal"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleCreateGoal} disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Goal'}
            </button>
          </>
        }
      >
        <form onSubmit={handleCreateGoal}>
          {error && (
            <div style={{ marginBottom: '1rem', padding: '0.625rem', borderRadius: 'var(--radius-md)', background: 'var(--accent-red-dim)', color: 'var(--accent-red)', fontSize: '0.8125rem' }}>
              {error}
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Goal Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Down Payment for Home, Emergency Fund"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Target Amount (₹) *</label>
              <input
                type="number"
                step="0.01"
                className="form-input num-mono"
                placeholder="200000"
                value={formData.target_amount}
                onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Current Saved (₹)</label>
              <input
                type="number"
                step="0.01"
                className="form-input num-mono"
                placeholder="25000"
                value={formData.current_amount}
                onChange={(e) => setFormData({ ...formData, current_amount: e.target.value })}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Target Date</label>
            <input
              type="date"
              className="form-input"
              value={formData.target_date}
              onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
            />
          </div>
        </form>
      </Modal>

      {/* Update Savings Modal */}
      <Modal
        isOpen={isSavingsModalOpen}
        onClose={() => setIsSavingsModalOpen(false)}
        title={`Update Saved Amount: ${selectedGoal?.title}`}
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsSavingsModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleUpdateSavings} disabled={isSubmitting}>
              Update Progress
            </button>
          </>
        }
      >
        <form onSubmit={handleUpdateSavings}>
          <div className="form-group">
            <label className="form-label">New Total Saved Amount (₹)</label>
            <input
              type="number"
              step="0.01"
              className="form-input num-mono"
              value={savingsInput}
              onChange={(e) => setSavingsInput(e.target.value)}
              required
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
