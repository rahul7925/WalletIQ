import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, trend, trendLabel, color = 'gold' }) {
  const colorMap = {
    gold: { text: 'var(--accent-gold)', bg: 'var(--accent-gold-dim)' },
    green: { text: 'var(--accent-green)', bg: 'var(--accent-green-dim)' },
    red: { text: 'var(--accent-red)', bg: 'var(--accent-red-dim)' },
    blue: { text: 'var(--accent-blue)', bg: 'var(--accent-blue-dim)' },
    purple: { text: 'var(--accent-purple)', bg: 'var(--accent-purple-dim)' },
  };

  const currentTheme = colorMap[color] || colorMap.gold;

  return (
    <div className="glass-card animate-fade">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          {title}
        </span>
        {Icon && (
          <div
            style={{
              padding: '0.5rem',
              borderRadius: 'var(--radius-md)',
              background: currentTheme.bg,
              color: currentTheme.text,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>

      <div className="num-mono" style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
        {value}
      </div>

      {(subtitle || trend) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
          {trend && (
            <span
              style={{
                color: trend === 'up' ? 'var(--accent-green)' : trend === 'down' ? 'var(--accent-red)' : 'var(--text-secondary)',
                fontWeight: 600,
              }}
            >
              {trendLabel}
            </span>
          )}
          {subtitle && <span style={{ color: 'var(--text-muted)' }}>{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
