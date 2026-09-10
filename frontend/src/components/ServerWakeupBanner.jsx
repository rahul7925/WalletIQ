import React, { useState, useEffect } from 'react';
import { Loader2, X } from 'lucide-react';

export default function ServerWakeupBanner() {
  const [isWaking, setIsWaking] = useState(false);
  const [elapsed, setElapsed] = useState(5);

  useEffect(() => {
    let timer = null;

    function handleWaking() {
      setIsWaking(true);
      setElapsed(5);
      if (!timer) {
        timer = setInterval(() => {
          setElapsed((prev) => prev + 1);
        }, 1000);
      }
    }

    function handleReady() {
      setIsWaking(false);
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    window.addEventListener('walletiq:server-waking', handleWaking);
    window.addEventListener('walletiq:server-ready', handleReady);

    return () => {
      window.removeEventListener('walletiq:server-waking', handleWaking);
      window.removeEventListener('walletiq:server-ready', handleReady);
      if (timer) clearInterval(timer);
    };
  }, []);

  if (!isWaking) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: '1rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        background: 'rgba(18, 18, 26, 0.96)',
        border: '1px solid rgba(200, 169, 110, 0.4)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px rgba(200, 169, 110, 0.15)',
        backdropFilter: 'blur(12px)',
        padding: '0.65rem 1.25rem',
        borderRadius: '9999px',
        color: '#F8FAFC',
        fontSize: '0.875rem',
        animation: 'fadeIn 0.2s ease-in-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', color: '#C8A96E' }}>
        <Loader2 className="animate-spin" size={18} />
      </div>
      <div>
        <span style={{ fontWeight: 600, color: '#C8A96E' }}>Waking up Cloud Server</span>
        <span style={{ color: '#94A3B8', marginLeft: '0.5rem' }}>
          Render free tier is spinning up (~{elapsed}s)...
        </span>
      </div>
      <button
        onClick={() => setIsWaking(false)}
        style={{
          background: 'none',
          border: 'none',
          color: '#94A3B8',
          cursor: 'pointer',
          padding: '2px',
          marginLeft: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#F8FAFC')}
        onMouseLeave={(e) => (e.currentTarget.style.color = '#94A3B8')}
        title="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
}
