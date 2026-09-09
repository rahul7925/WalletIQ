import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Modal from './components/Modal';
import { api } from './services/api';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import DashboardPage from './pages/DashboardPage';
import ExpensesPage from './pages/ExpensesPage';
import BudgetsPage from './pages/BudgetsPage';
import InvestmentsPage from './pages/InvestmentsPage';
import BillsPage from './pages/BillsPage';
import CommandCenterPage from './pages/CommandCenterPage';
import AIAdvisorPage from './pages/AIAdvisorPage';
import FinancialHealthPage from './pages/FinancialHealthPage';
import SavingsPredictionPage from './pages/SavingsPredictionPage';
import LoanEligibilityPage from './pages/LoanEligibilityPage';
import GoalPlannerPage from './pages/GoalPlannerPage';
import SpendingInsightsPage from './pages/SpendingInsightsPage';
import ReportStudioPage from './pages/ReportStudioPage';
import SharedReportPage from './pages/SharedReportPage';
import SettingsPage from './pages/SettingsPage';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
        <div className="num-mono gold-text" style={{ fontSize: '1.25rem' }}>
          Initializing WalletIQ Secure Session...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export default function App() {
  const { isAuthenticated } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Global Quick Add Expense Modal
  const [isQuickExpenseOpen, setIsQuickExpenseOpen] = useState(false);
  const [quickAmount, setQuickAmount] = useState('');
  const [quickCategory, setQuickCategory] = useState('Food');
  const [quickDesc, setQuickDesc] = useState('');
  const [quickDate, setQuickDate] = useState(new Date().toISOString().split('T')[0]);
  const [isSavingQuick, setIsSavingQuick] = useState(false);

  async function handleSaveQuickExpense(e) {
    e.preventDefault();
    if (!quickAmount || isNaN(quickAmount) || parseFloat(quickAmount) <= 0) return;

    setIsSavingQuick(true);
    try {
      await api.createExpense({
        amount: parseFloat(quickAmount),
        category: quickCategory,
        description: quickDesc,
        date: quickDate,
      });
      setIsQuickExpenseOpen(false);
      setQuickAmount('');
      setQuickDesc('');
      window.location.reload(); // Refresh views
    } catch (err) {
      alert(err.message || 'Failed to record expense');
    } finally {
      setIsSavingQuick(false);
    }
  }

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} />
        <Route path="/register" element={!isAuthenticated ? <RegisterPage /> : <Navigate to="/dashboard" replace />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/shared/:token" element={<SharedReportPage />} />

        {/* Protected Dashboard Layout */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="app-container">
                <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
                <div className="main-content">
                  <Topbar
                    onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
                    onOpenAddExpense={() => setIsQuickExpenseOpen(true)}
                  />
                  <Routes>
                    <Route path="/dashboard" element={<DashboardPage onOpenAddExpense={() => setIsQuickExpenseOpen(true)} />} />
                    <Route path="/expenses" element={<ExpensesPage />} />
                    <Route path="/budgets" element={<BudgetsPage />} />
                    <Route path="/investments" element={<InvestmentsPage />} />
                    <Route path="/bills" element={<BillsPage />} />
                    <Route path="/command-center" element={<CommandCenterPage />} />
                    <Route path="/ai-advisor" element={<AIAdvisorPage />} />
                    <Route path="/financial-health" element={<FinancialHealthPage />} />
                    <Route path="/savings-prediction" element={<SavingsPredictionPage />} />
                    <Route path="/loan-eligibility" element={<LoanEligibilityPage />} />
                    <Route path="/goals" element={<GoalPlannerPage />} />
                    <Route path="/spending-insights" element={<SpendingInsightsPage />} />
                    <Route path="/reports" element={<ReportStudioPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </div>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>

      {/* Global Quick Add Expense Modal */}
      <Modal
        isOpen={isQuickExpenseOpen}
        onClose={() => setIsQuickExpenseOpen(false)}
        title="Quick Record Expense"
        footer={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => setIsQuickExpenseOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSaveQuickExpense} disabled={isSavingQuick}>
              {isSavingQuick ? 'Recording...' : 'Record Transaction'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSaveQuickExpense}>
          <div className="form-group">
            <label className="form-label">Amount (₹) *</label>
            <input
              type="number"
              step="0.01"
              className="form-input num-mono"
              placeholder="e.g. 500"
              value={quickAmount}
              onChange={(e) => setQuickAmount(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={quickCategory}
                onChange={(e) => setQuickCategory(e.target.value)}
              >
                {['Food', 'Transport', 'Utilities', 'Entertainment', 'Shopping', 'Health', 'Education', 'Savings', 'EMI', 'General'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input
                type="date"
                className="form-input"
                value={quickDate}
                onChange={(e) => setQuickDate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Coffee, Lunch"
              value={quickDesc}
              onChange={(e) => setQuickDesc(e.target.value)}
            />
          </div>
        </form>
      </Modal>
    </>
  );
}
