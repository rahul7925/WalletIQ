import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Camera,
  Download,
  Trash2,
  Edit2,
  Filter,
  Search,
  CheckCircle,
  AlertCircle,
  Calendar,
} from 'lucide-react';
import Modal from '../components/Modal';
import ReceiptScannerModal from '../components/ReceiptScannerModal';
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

export default function ExpensesPage() {
  const cachedData = api.getCached ? (api.getCached('/expenses?page=1&per_page=15') || api.getCached('/expenses')) : null;
  const initialExpenses = cachedData?.expenses || cachedData?.items || [];
  const [expenses, setExpenses] = useState(initialExpenses);
  const [pagination, setPagination] = useState({
    page: cachedData?.page || 1,
    per_page: cachedData?.per_page || cachedData?.limit || 15,
    total: cachedData?.total || initialExpenses.length,
    total_pages: cachedData?.total_pages || cachedData?.pages || 1,
  });
  const [categoryFilter, setCategoryFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(initialExpenses.length === 0);

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isOcrModalOpen, setIsOcrModalOpen] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);

  // Form states
  const [formData, setFormData] = useState({
    amount: '',
    category: 'Food',
    description: '',
    date: new Date().toISOString().split('T')[0],
  });
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchExpenses = useCallback(async (page = 1) => {
    if (expenses.length === 0 && initialExpenses.length === 0) setIsLoading(true);
    try {
      const params = { page, per_page: 15 };
      if (categoryFilter) params.category = categoryFilter;
      const data = await api.getExpenses(params);
      const list = data?.expenses || data?.items || [];
      setExpenses(list);
      setPagination({
        page: data?.page || page,
        per_page: data?.per_page || data?.limit || 15,
        total: data?.total ?? list.length,
        total_pages: data?.total_pages || data?.pages || 1,
      });
    } catch (err) {
      console.error('Failed to load expenses', err);
    } finally {
      setIsLoading(false);
    }
  }, [categoryFilter, expenses.length, initialExpenses.length]);

  useEffect(() => {
    fetchExpenses(1);
  }, [fetchExpenses]);

  function handleOpenAdd() {
    setFormData({
      amount: '',
      category: 'Food',
      description: '',
      date: new Date().toISOString().split('T')[0],
    });
    setFormError('');
    setIsAddModalOpen(true);
  }

  function handleOpenEdit(exp) {
    setSelectedExpense(exp);
    setFormData({
      amount: exp.amount,
      category: exp.category,
      description: exp.description || '',
      date: exp.date,
    });
    setFormError('');
    setIsEditModalOpen(true);
  }

  async function handleSaveExpense(e) {
    e.preventDefault();
    if (!formData.amount || isNaN(formData.amount) || parseFloat(formData.amount) <= 0) {
      setFormError('Please enter a valid amount greater than 0.');
      return;
    }

    setIsSubmitting(true);
    setFormError('');
    try {
      if (selectedExpense) {
        await api.updateExpense(selectedExpense.id, {
          title: (formData.description || '').trim() || `${formData.category} Expense`,
          description: (formData.description || '').trim(),
          amount: parseFloat(formData.amount),
          category: formData.category,
          date: formData.date,
        });
        setIsEditModalOpen(false);
      } else {
        await api.createExpense({
          title: (formData.description || '').trim() || `${formData.category} Expense`,
          description: (formData.description || '').trim(),
          amount: parseFloat(formData.amount),
          category: formData.category,
          date: formData.date,
        });
        setIsAddModalOpen(false);
      }
      fetchExpenses(pagination.page);
    } catch (err) {
      setFormError(err.message || 'Failed to save expense');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteExpense(id) {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;
    try {
      await api.deleteExpense(id);
      fetchExpenses(pagination.page);
    } catch (err) {
      alert(err.message || 'Failed to delete expense');
    }
  }

  function handleOcrApply(scanned) {
    setFormData({
      amount: scanned.amount,
      category: scanned.category || 'General',
      description: scanned.notes || scanned.merchant || 'Scanned Receipt',
      date: scanned.date || new Date().toISOString().split('T')[0],
    });
    setIsAddModalOpen(true);
  }

  async function handleExportCsv() {
    try {
      const blob = await api.exportCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `walletiq_expenses_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to export CSV: ' + err.message);
    }
  }

  const filteredExpenses = expenses.filter((e) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (e.description && e.description.toLowerCase().includes(term)) ||
      (e.title && e.title.toLowerCase().includes(term)) ||
      (e.category && e.category.toLowerCase().includes(term))
    );
  });

  return (
    <div className="page-wrapper animate-fade">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Expense Tracking
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Log, categorize, and analyze your individual cash flows
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={() => setIsOcrModalOpen(true)}>
            <Camera size={16} />
            <span>Scan Receipt (AI)</span>
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleExportCsv}>
            <Download size={16} />
            <span>Export CSV</span>
          </button>
          <button type="button" className="btn btn-primary" onClick={handleOpenAdd}>
            <Plus size={16} />
            <span>Add Expense</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="glass-card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ position: 'relative', flex: '1', minWidth: '200px' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="form-input"
            style={{ paddingLeft: '2.25rem' }}
            placeholder="Search descriptions or categories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div style={{ width: '180px' }}>
          <select
            className="form-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Expenses Table */}
      <div className="glass-card" style={{ padding: '0' }}>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Category</th>
                <th>Description</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th style={{ textAlign: 'center', width: '100px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--accent-gold)' }}>
                    Loading expenses...
                  </td>
                </tr>
              ) : filteredExpenses.length > 0 ? (
                filteredExpenses.map((exp) => (
                  <tr key={exp.id}>
                    <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                      {exp.date}
                    </td>
                    <td>
                      <span className="badge badge-gold">{exp.category}</span>
                    </td>
                    <td style={{ color: 'var(--text-primary)' }}>{exp.description || exp.title || '—'}</td>
                    <td className="num-mono" style={{ textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                      ₹{Number(exp.amount).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                        <button
                          onClick={() => handleOpenEdit(exp)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '0.25rem',
                          }}
                          title="Edit"
                        >
                          <Edit2 size={15} />
                        </button>
                        <button
                          onClick={() => handleDeleteExpense(exp.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--accent-red)',
                            cursor: 'pointer',
                            padding: '0.25rem',
                          }}
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
                    No expenses found matching the current filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {pagination.total_pages > 1 && (
          <div
            style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.8125rem',
            }}
          >
            <span style={{ color: 'var(--text-muted)' }}>
              Showing Page {pagination.page} of {pagination.total_pages} ({pagination.total} total)
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagination.page <= 1}
                onClick={() => fetchExpenses(pagination.page - 1)}
              >
                Previous
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={pagination.page >= pagination.total_pages}
                onClick={() => fetchExpenses(pagination.page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add / Edit Expense Modal */}
      <Modal
        isOpen={isAddModalOpen || isEditModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setIsEditModalOpen(false);
        }}
        title={selectedExpense ? 'Edit Expense' : 'Add New Expense'}
        footer={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setIsAddModalOpen(false);
                setIsEditModalOpen(false);
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSaveExpense}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Save Expense'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSaveExpense}>
          {formError && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.625rem 0.875rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--accent-red-dim)',
                border: '1px solid rgba(255, 100, 100, 0.3)',
                color: 'var(--accent-red)',
                fontSize: '0.8125rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <AlertCircle size={15} />
              <span>{formError}</span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Amount (₹) *</label>
            <input
              type="number"
              step="0.01"
              className="form-input num-mono"
              placeholder="e.g. 450.00"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Category *</label>
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
              <label className="form-label">Date *</label>
              <input
                type="date"
                className="form-input"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Description / Notes</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Dinner with team, groceries"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>
        </form>
      </Modal>

      {/* OCR Scanner Modal */}
      <ReceiptScannerModal
        isOpen={isOcrModalOpen}
        onClose={() => setIsOcrModalOpen(false)}
        onApplyData={handleOcrApply}
      />
    </div>
  );
}
