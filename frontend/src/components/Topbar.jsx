import React, { useState, useEffect, useRef } from 'react';
import { Menu, Bell, Plus, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Topbar({ onToggleSidebar, onOpenAddExpense }) {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    async function loadNotifications() {
      try {
        const data = await api.getNotifications();
        if (isMounted && data) {
          setNotifications(data.notifications || []);
          setUnreadCount(data.unread_count || 0);
        }
      } catch {
        // Soft fail
      }
    }
    loadNotifications();
    const interval = setInterval(loadNotifications, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Click outside to close notification panel
  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  async function handleMarkRead(id) {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  }

  async function handleMarkAllRead() {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  }

  function getGreeting() {
    const hour = new Date().getHours();
    if (user?.language === 'ta') {
      if (hour < 12) return 'காலை வணக்கம்';
      if (hour < 17) return 'மதிய வணக்கம்';
      return 'மாலை வணக்கம்';
    }
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  return (
    <header
      style={{
        height: '70px',
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-color)',
        padding: '0 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button
          onClick={onToggleSidebar}
          style={{
            display: window.innerWidth <= 992 ? 'flex' : 'none',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '0.5rem',
            borderRadius: 'var(--radius-sm)',
          }}
        >
          <Menu size={20} />
        </button>

        <div>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {getGreeting()}, <span className="gold-text">{user?.full_name?.split(' ')[0] || user?.username || 'Trader'}</span>
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            {new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {onOpenAddExpense && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onOpenAddExpense}>
            <Plus size={16} />
            <span>Add Expense</span>
          </button>
        )}

        {/* Notification bell */}
        <div style={{ position: 'relative' }} ref={notifRef}>
          <button
            onClick={() => setShowNotifications((prev) => !prev)}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              padding: '0.5rem',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  background: 'var(--accent-red)',
                  color: '#fff',
                  borderRadius: '50%',
                  fontSize: '0.625rem',
                  fontWeight: 700,
                  width: '16px',
                  height: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notification dropdown */}
          {showNotifications && (
            <div
              className="glass-card animate-fade"
              style={{
                position: 'absolute',
                top: '115%',
                right: 0,
                width: '320px',
                padding: '1rem',
                zIndex: 200,
                maxHeight: '400px',
                overflowY: 'auto',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                  Notifications
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--accent-gold)',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              {notifications.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.5rem 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                  No notifications yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {notifications.slice(0, 10).map((n) => (
                    <div
                      key={n.id}
                      onClick={() => !n.is_read && handleMarkRead(n.id)}
                      style={{
                        padding: '0.625rem',
                        borderRadius: 'var(--radius-md)',
                        background: n.is_read ? 'transparent' : 'rgba(200, 169, 110, 0.08)',
                        borderLeft: n.is_read ? '2px solid transparent' : '2px solid var(--accent-gold)',
                        cursor: 'pointer',
                        fontSize: '0.8125rem',
                      }}
                    >
                      <div style={{ color: 'var(--text-primary)', fontWeight: n.is_read ? 400 : 600 }}>
                        {n.title || n.message}
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {n.created_at ? new Date(n.created_at).toLocaleDateString() : 'Recent'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
