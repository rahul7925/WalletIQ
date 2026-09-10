import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  DollarSign,
  TrendingDown,
  PiggyBank,
  AlertTriangle,
  Receipt,
  Plus,
  ArrowUpRight,
  Bot,
  FileSpreadsheet,
  CheckCircle,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import ProgressBar from '../components/ProgressBar';
import { api } from '../services/api';

export default function DashboardPage({ onOpenAddExpense }) {
  const [data, setData] = useState(null);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadDashboard() {
      setIsLoading(false);
      try {
        const [summaryRes, statsRes] = await Promise.all([
          api.getDashboardSummary(),
          api.getDashboardStats().catch(() => null),
        ]);
        if (isMounted) {
          setData(summaryRes);
          setStats(statsRes);
        }
      } catch (err) {
        if (isMounted) setError(err.message || 'Failed to load dashboard data');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadDashboard();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading && !data) {
    return (
      <div className="page-wrapper" style={{ textAlign: 'center', padding: '5rem 0' }}>
        <div style={{ color: 'var(--accent-gold)' }}>Loading your financial overview...</div>
      </div>
    );
  }

  const totalSpent = data?.total_spent ?? data?.stats?.month_total ?? stats?.month_total ?? 0;
  const monthlyBudget = data?.monthly_budget ?? data?.user?.monthly_budget ?? stats?.monthly_budget ?? 0;
  const monthlyIncome = data?.monthly_income ?? data?.user?.monthly_income ?? stats?.monthly_income ?? 0;
  const budgetProgress = data?.budget_progress ?? (monthlyBudget > 0 ? Math.min(100, Math.round((totalSpent / monthlyBudget) * 100)) : 0);
  const savingsRate = monthlyIncome > 0 ? Math.max(0, Math.round(((monthlyIncome - totalSpent) / monthlyIncome) * 100)) : 0;
  const overdueBills = data?.overdue_bills_count ?? data?.stats?.overdue_bills ?? stats?.overdue_bills ?? 0;
  const categorySpending = data?.category_spending || data?.stats?.cat_totals || stats?.cat_totals || {};

  return (
    <div className="page-wrapper animate-fade">
      {/* Top Banner / Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Financial Overview
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Real-time portfolio intelligence, expenses, and budget utilization
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="button" className="btn btn-primary" onClick={onOpenAddExpense}>
            <Plus size={16} />
            <span>Record Expense</span>
          </button>
          <Link to="/ai-advisor" className="btn btn-secondary">
            <Bot size={16} />
            <span>AI Advisor</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <StatCard
          title="Spent This Month"
          value={`₹${totalSpent.toLocaleString()}`}
          subtitle={`${budgetProgress}% of budget used`}
          icon={TrendingDown}
          color={budgetProgress >= 100 ? 'red' : 'gold'}
        />
        <StatCard
          title="Monthly Budget"
          value={`₹${monthlyBudget.toLocaleString()}`}
          subtitle={`Remaining: ₹${Math.max(0, monthlyBudget - totalSpent).toLocaleString()}`}
          icon={PiggyBank}
          color="blue"
        />
        <StatCard
          title="Savings Rate"
          value={`${savingsRate}%`}
          subtitle={`Net Income: ₹${monthlyIncome.toLocaleString()}`}
          icon={DollarSign}
          trend={savingsRate > 20 ? 'up' : 'down'}
          trendLabel={savingsRate > 20 ? 'Healthy' : 'Below Target'}
          color="green"
        />
        <StatCard
          title="Unpaid / Overdue Bills"
          value={overdueBills}
          subtitle="Requires attention"
          icon={AlertTriangle}
          color={overdueBills > 0 ? 'red' : 'purple'}
        />
      </div>

      {/* Main Content Grid: Budget Progress & Category Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Budget Utilization Card */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1.25rem' }}>
            Overall Budget Utilization
          </h3>
          <ProgressBar
            value={totalSpent}
            max={monthlyBudget}
            label={`Spent ₹${totalSpent.toLocaleString()} of ₹${monthlyBudget.toLocaleString()}`}
          />
          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Monthly Allowance</span>
              <strong className="num-mono" style={{ color: 'var(--text-primary)' }}>₹{monthlyBudget.toLocaleString()}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Available Capacity</span>
              <strong className="num-mono" style={{ color: 'var(--accent-green)' }}>
                ₹{Math.max(0, monthlyBudget - totalSpent).toLocaleString()}
              </strong>
            </div>
          </div>
        </div>

        {/* Top Spending Categories */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Top Spending Categories</h3>
            <Link to="/expenses" style={{ fontSize: '0.8125rem', color: 'var(--accent-gold)' }}>
              View all
            </Link>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
            {categorySpending && Object.keys(categorySpending).length > 0 ? (
              Object.entries(categorySpending)
                .slice(0, 5)
                .map(([cat, amt], idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{cat}</span>
                      <strong className="num-mono">₹{Number(amt).toLocaleString()}</strong>
                    </div>
                    <ProgressBar value={amt} max={totalSpent || 1} showPercent={false} />
                  </div>
                ))
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                No category spending data for this month.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Recent Transactions</h3>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Latest expenses recorded</span>
          </div>
          <Link to="/expenses" className="btn btn-secondary btn-sm">
            <span>Manage All</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Category</th>
                <th>Description / Notes</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {(data?.recent_expenses || data?.transactions) && (data?.recent_expenses || data?.transactions).length > 0 ? (
                (data?.recent_expenses || data?.transactions).slice(0, 6).map((exp) => (
                  <tr key={exp.id}>
                    <td className="num-mono" style={{ color: 'var(--text-secondary)' }}>
                      {exp.date}
                    </td>
                    <td>
                      <span className="badge badge-gold">{exp.category}</span>
                    </td>
                    <td style={{ color: 'var(--text-primary)' }}>
                      {exp.description || exp.title || '—'}
                    </td>
                    <td className="num-mono" style={{ textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                      ₹{Number(exp.amount).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No expenses recorded yet. Click "Record Expense" to begin.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
