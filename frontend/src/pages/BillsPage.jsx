import React, { useState, useEffect } from 'react';
import { Plus, Calendar, CheckCircle, AlertTriangle, Clock, Trash2, Edit2, Check, AlertCircle } from 'lucide-react';
import Modal from '../components/Modal';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function BillsPage() {
  const cachedBills = api.getCached ? api.getCached('/bills') : null;
  const initialBills = cachedBills?.bills || [];
  const [bills, setBills] = useState(initialBills);
  const [reminders, setReminders] = useState(() => (api.getCached ? api.getCached('/bills/reminders') : null));
  const [isLoading, setIsLoading] = useState(initialBills.length === 0);

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedBill, setSelectedBill] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    amount: '',
    due_date: new Date().toISOString().split('T')[0],
    category: 'Utilities',
    is_recurring: false,
    recurring_frequency: 'monthly',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadBills() {
    if (bills.length === 0 && initialBills.length === 0) setIsLoading(true);
    try {
      const [billsData, remData] = await Promise.all([
        api.getBills(),
        api.getBillReminders().catch(() => null),
      ]);
      setBills(billsData?.bills || []);
      setReminders(remData);
    } catch (err) {
      console.error('Failed to load bills', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadBills();
  }, []);

  function handleOpenAdd() {
    setSelectedBill(null);
    setFormData({
      title: '',
      amount: '',
      due_date: new Date().toISOString().split('T')[0],
      category: 'Utilities',
      is_recurring: false,
      recurring_frequency: 'monthly',
    });
    setError('');
    setIsModalOpen(true);
  }

  function handleOpenEdit(b) {
    setSelectedBill(b);
    setFormData({
      title: b.title,
      amount: b.amount,
      due_date: b.due_date,
      category: b.category || 'Utilities',
      is_recurring: !!b.is_recurring,
      recurring_frequency: b.recurring_frequency || 'monthly',
    });
    setError('');
    setIsModalOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!formData.title.trim() || !formData.amount || isNaN(formData.amount)) {
      setError('Please provide a valid bill title and amount.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      const payload = {
        title: formData.title.trim(),
        amount: parseFloat(formData.amount),
        due_date: formData.due_date,
        category: formData.category,
        is_recurring: formData.is_recurring,
        recurring_frequency: formData.recurring_frequency,
      };

      if (selectedBill) {
        await api.updateBill(selectedBill.id, payload);
      } else {
        await api.createBill(payload);
      }
      setIsModalOpen(false);
      loadBills();
    } catch (err) {
      setError(err.message || 'Failed to save bill');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePay(id) {
    try {
      await api.payBill(id);
      loadBills();
    } catch (err) {
      alert(err.message || 'Failed to process bill payment');
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this bill?')) return;
    try {
      await api.deleteBill(id);
      loadBills();
    } catch (err) {
      alert(err.message || 'Failed to delete bill');
    }
  }

  const unpaidBills = bills.filter((b) => !b.is_paid);
  const overdueCount = reminders?.overdue_bills?.length || 0;
  const upcomingCount = reminders?.upcoming_bills?.length || 0;

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Bills & Reminders
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Track recurring utility bills, EMIs, and avoid late payment penalties
          </p>
        </div>

        <button type="button" className="btn btn-primary" onClick={handleOpenAdd}>
          <Plus size={16} />
          <span>Add Recurring Bill</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Active Unpaid Bills"
          value={unpaidBills.length}
          subtitle={`Total due: ₹${unpaidBills.reduce((acc, b) => acc + b.amount, 0).toLocaleString()}`}
          icon={Clock}
          color="gold"
        />
        <StatCard
          title="Overdue Bills"
          value={overdueCount}
          subtitle="Past due date"
          icon={AlertTriangle}
          color={overdueCount > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="Due In Next 7 Days"
          value={upcomingCount}
          subtitle="Upcoming obligations"
          icon={Calendar}
          color="blue"
        />
      </div>

      {/* Bills Table */}
      <div className="glass-card" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title / Category</th>
                <th>Due Date</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Status</th>
                <th style={{ textAlign: 'center', width: '140px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--accent-gold)' }}>
                    Loading bills...
                  </td>
                </tr>
              ) : bills.length > 0 ? (
                bills.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{b.title}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{b.category || 'Utilities'}</div>
                    </td>
                    <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                      {b.due_date}
                    </td>
                    <td className="num-mono" style={{ textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                      ₹{Number(b.amount).toLocaleString()}
                    </td>
                    <td>
                      {b.is_paid ? (
                        <span className="badge badge-green">Paid</span>
                      ) : b.is_overdue ? (
                        <span className="badge badge-red">Overdue</span>
                      ) : (
                        <span className="badge badge-gold">Pending</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', alignItems: 'center' }}>
                        {!b.is_paid && (
                          <button
                            onClick={() => handlePay(b.id)}
                            className="btn btn-sm btn-primary"
                            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
                            title="Mark as Paid"
                          >
                            <Check size={14} />
                            <span>Pay</span>
                          </button>
                        )}
                        <button
                          onClick={() => handleOpenEdit(b)}
                          style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.25rem' }}
                          title="Edit"
                        >
                          <Edit2 size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(b.id)}
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
                    No bills recorded yet. Click "Add Recurring Bill" to track utility payments.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Bill Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedBill ? 'Edit Bill' : 'Add Recurring Bill'}
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Bill'}
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
            <label className="form-label">Bill Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Electricity, Netflix, Home Rent"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Amount (₹) *</label>
              <input
                type="number"
                step="0.01"
                className="form-input num-mono"
                placeholder="2500"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Due Date *</label>
              <input
                type="date"
                className="form-input"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Category</label>
            <input
              type="text"
              className="form-input"
              placeholder="Utilities, Subscription, EMI"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
