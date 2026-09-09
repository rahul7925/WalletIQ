import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Receipt,
  PiggyBank,
  TrendingUp,
  CalendarCheck,
  ShieldCheck,
  Bot,
  HeartPulse,
  LineChart,
  BadgePercent,
  Target,
  Sparkles,
  FileSpreadsheet,
  Settings,
  LogOut,
  X,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_GROUPS = [
  {
    title: 'Overview',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/command-center', label: 'Command Center', icon: Zap },
    ],
  },
  {
    title: 'Finances',
    items: [
      { to: '/expenses', label: 'Expenses', icon: Receipt },
      { to: '/budgets', label: 'Budgets', icon: PiggyBank },
      { to: '/investments', label: 'Investments', icon: TrendingUp },
      { to: '/bills', label: 'Bills & Calendar', icon: CalendarCheck },
      { to: '/goals', label: 'Goal Planner', icon: Target },
    ],
  },
  {
    title: 'AI & Intelligence',
    items: [
      { to: '/ai-advisor', label: 'AI Advisor', icon: Bot },
      { to: '/financial-health', label: 'Financial Health', icon: HeartPulse },
      { to: '/savings-prediction', label: 'Savings Forecast', icon: LineChart },
      { to: '/loan-eligibility', label: 'Loan Eligibility', icon: BadgePercent },
      { to: '/spending-insights', label: 'Spending Insights', icon: Sparkles },
    ],
  },
  {
    title: 'Reports & Admin',
    items: [
      { to: '/reports', label: 'Report Studio', icon: FileSpreadsheet },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            zIndex: 140,
            backdropFilter: 'blur(4px)',
          }}
        />
      )}

      <aside
        style={{
          width: '260px',
          height: '100vh',
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          position: 'fixed',
          top: 0,
          left: 0,
          bottom: 0,
          zIndex: 150,
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          transform: isOpen || window.innerWidth > 992 ? 'translateX(0)' : 'translateX(-100%)',
        }}
      >
        {/* Logo Branding */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-color)',
          }}
        >
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
                boxShadow: '0 2px 10px rgba(200, 169, 110, 0.3)',
              }}
            >
              <ShieldCheck size={20} color="#0a0a0f" strokeWidth={2.5} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.125rem', letterSpacing: '-0.02em' }}>
                Wallet<span className="gold-text">IQ</span>
              </div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Financial OS
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              display: window.innerWidth <= 992 ? 'flex' : 'none',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation List */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1rem 0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
          }}
        >
          {NAV_GROUPS.map((group, gIdx) => (
            <div key={gIdx}>
              <div
                style={{
                  fontSize: '0.6875rem',
                  textTransform: 'uppercase',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  color: 'var(--text-muted)',
                  padding: '0 0.75rem 0.5rem',
                }}
              >
                {group.title}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {group.items.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={idx}
                      to={item.to}
                      onClick={() => {
                        if (window.innerWidth <= 992) onClose();
                      }}
                      style={({ isActive }) => ({
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '0.625rem 0.75rem',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '0.875rem',
                        fontWeight: isActive ? 600 : 500,
                        color: isActive ? 'var(--accent-gold-light)' : 'var(--text-secondary)',
                        background: isActive ? 'var(--accent-gold-dim)' : 'transparent',
                        borderLeft: isActive ? '3px solid var(--accent-gold)' : '3px solid transparent',
                        transition: 'all 0.15s ease',
                      })}
                    >
                      <Icon size={18} />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Snippet & Logout */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderTop: '1px solid var(--border-color)',
            background: 'var(--bg-elevated)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                background: 'var(--accent-purple-dim)',
                color: 'var(--accent-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '0.875rem',
                flexShrink: 0,
              }}
            >
              {(user?.username || 'U')[0].toUpperCase()}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {user?.full_name || user?.username || 'User'}
              </div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {user?.email || 'authenticated'}
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            title="Log Out"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.375rem',
              display: 'flex',
              alignItems: 'center',
              borderRadius: 'var(--radius-sm)',
              transition: 'color 0.2s',
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
    </>
  );
}
