import React from 'react';

export default function ProgressBar({ value = 0, max = 100, label, showPercent = true, colorOverride }) {
  const percentage = Math.min(Math.max((value / (max || 1)) * 100, 0), 100);

  let barColor = 'var(--accent-green)';
  if (percentage >= 100) {
    barColor = 'var(--accent-red)';
  } else if (percentage >= 80) {
    barColor = 'var(--accent-orange)';
  }

  if (colorOverride) {
    barColor = colorOverride;
  }

  return (
    <div style={{ width: '100%' }}>
      {(label || showPercent) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem', fontSize: '0.8125rem' }}>
          {label && <span style={{ color: 'var(--text-secondary)' }}>{label}</span>}
          {showPercent && (
            <span className="num-mono" style={{ color: barColor, fontWeight: 600 }}>
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      )}
      <div
        style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: 'var(--radius-full)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            background: barColor,
            borderRadius: 'var(--radius-full)',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  );
}
