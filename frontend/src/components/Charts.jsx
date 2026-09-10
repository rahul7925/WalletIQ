import React, { useEffect, useRef, useState } from 'react';

export const CAT_COLORS = {
  Food: '#D946EF',          // Electric Magenta
  Bills: '#2563EB',         // Royal Blue
  Travel: '#06B6D4',        // Bright Cyan
  Entertainment: '#9333EA',  // Vivid Purple
  Shopping: '#EC4899',      // Hot Pink
  Health: '#EF4444',        // Bright Red
  Investment: '#16A34A',    // Vibrant Green
  Transport: '#38BDF8',     // Sky Blue
  Utilities: '#6366F1',     // Bright Indigo
  Savings: '#22C55E',       // Fresh Lime Green
  Education: '#0EA5E9',     // Deep Sky Blue
  EMI: '#DC2626',           // Deep Red
  General: '#C8A96E',       // Metallic Gold
  Others: '#8B5CF6',        // Bright Violet
};

const DEFAULT_PALETTE = [
  '#D946EF', // Electric Magenta
  '#2563EB', // Blue
  '#16A34A', // Green
  '#EF4444', // Red
  '#9333EA', // Purple
  '#38BDF8', // Sky Blue
  '#06B6D4', // Cyan
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#6366F1', // Indigo
];

function getColor(label, idx = 0) {
  return CAT_COLORS[label] || DEFAULT_PALETTE[idx % DEFAULT_PALETTE.length];
}

const TOOLTIP_OPTIONS = {
  backgroundColor: 'rgba(18, 18, 26, 0.95)',
  borderColor: 'rgba(200, 169, 110, 0.3)',
  borderWidth: 1,
  titleColor: '#F8FAFC',
  bodyColor: '#C8A96E',
  padding: 12,
  cornerRadius: 8,
  displayColors: true,
  callbacks: {
    label: (context) => {
      const val = context.raw || 0;
      return ` ₹${Number(val).toLocaleString('en-IN')}`;
    },
  },
};

// Helper hook to ensure Chart.js is ready
function useChartJs() {
  const [ready, setReady] = useState(typeof window !== 'undefined' && !!window.Chart);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.Chart) {
      setReady(true);
      return;
    }

    let script = document.getElementById('chartjs-cdn-script');
    if (!script) {
      script = document.createElement('script');
      script.id = 'chartjs-cdn-script';
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
      script.async = true;
      document.head.appendChild(script);
    }

    const onLoad = () => setReady(true);
    script.addEventListener('load', onLoad);
    return () => {
      script.removeEventListener('load', onLoad);
    };
  }, []);

  return ready;
}

// ── 1. Category Bar Chart ─────────────────────────────────────────────────────
export function CategoryBarChart({ categorySpending = {}, height = 240 }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);
  const isChartReady = useChartJs();

  const entries = Object.entries(categorySpending || {}).filter(([_, v]) => Number(v) > 0);
  const labels = entries.map(([k]) => k);
  const dataVals = entries.map(([_, v]) => Number(v));

  useEffect(() => {
    if (!isChartReady || !canvasRef.current || labels.length === 0) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');
    const colors = labels.map((l, i) => getColor(l, i));

    chartInstance.current = new window.Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Spending',
            data: dataVals,
            backgroundColor: colors,
            hoverBackgroundColor: colors.map((c) => c + 'EE'),
            borderColor: colors,
            borderWidth: 1.5,
            borderRadius: { topLeft: 8, topRight: 8, bottomLeft: 0, bottomRight: 0 },
            borderSkipped: false,
            maxBarThickness: 38,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: TOOLTIP_OPTIONS,
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#94A3B8', font: { size: 11 } },
            border: { display: false },
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              color: '#94A3B8',
              font: { size: 11 },
              callback: (v) => '₹' + Number(v).toLocaleString('en-IN'),
            },
            border: { display: false },
          },
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
    };
  }, [isChartReady, JSON.stringify(categorySpending)]);

  if (labels.length === 0) {
    return (
      <div style={{ height, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        <span style={{ fontSize: '1.75rem', marginBottom: '0.5rem', opacity: 0.4 }}>📊</span>
        <span>No category expenses recorded this month</span>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      <canvas ref={canvasRef} />
    </div>
  );
}

// ── 2. Category Doughnut / Pie Chart ──────────────────────────────────────────
export function CategoryDoughnutChart({ categorySpending = {}, height = 240 }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);
  const isChartReady = useChartJs();

  const entries = Object.entries(categorySpending || {}).filter(([_, v]) => Number(v) > 0);
  const labels = entries.map(([k]) => k);
  const dataVals = entries.map(([_, v]) => Number(v));

  useEffect(() => {
    if (!isChartReady || !canvasRef.current || labels.length === 0) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');
    const colors = labels.map((l, i) => getColor(l, i));

    chartInstance.current = new window.Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [
          {
            data: dataVals,
            backgroundColor: colors,
            hoverBackgroundColor: colors.map((c) => c + 'EE'),
            borderColor: '#12121A',
            borderWidth: 3,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '64%',
        animation: { duration: 600, easing: 'easeOutQuart' },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              borderRadius: 4,
              useBorderRadius: true,
              padding: 14,
              color: '#CBD5E1',
              font: { size: 11, weight: '500' },
            },
          },
          tooltip: TOOLTIP_OPTIONS,
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
    };
  }, [isChartReady, JSON.stringify(categorySpending)]);

  if (labels.length === 0) {
    return (
      <div style={{ height, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        <span style={{ fontSize: '1.75rem', marginBottom: '0.5rem', opacity: 0.4 }}>🍩</span>
        <span>No expense breakdown available</span>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      <canvas ref={canvasRef} />
    </div>
  );
}

// ── 3. Monthly Trend Line Chart ───────────────────────────────────────────────
export function MonthlyTrendLineChart({ monthlyKeys = [], monthlyVals = [], height = 240 }) {
  const canvasRef = useRef(null);
  const chartInstance = useRef(null);
  const isChartReady = useChartJs();

  const labels = monthlyKeys && monthlyKeys.length > 0 ? monthlyKeys : ['Current Month'];
  const dataVals = monthlyVals && monthlyVals.length > 0 ? monthlyVals : [0];

  useEffect(() => {
    if (!isChartReady || !canvasRef.current) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');

    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(200, 169, 110, 0.35)');
    gradient.addColorStop(1, 'rgba(200, 169, 110, 0.00)');

    chartInstance.current = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Total Expenses',
            data: dataVals,
            borderColor: '#C8A96E',
            borderWidth: 2.5,
            backgroundColor: gradient,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#C8A96E',
            pointBorderColor: '#12121A',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          tooltip: TOOLTIP_OPTIONS,
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#94A3B8', font: { size: 11 } },
            border: { display: false },
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: {
              color: '#94A3B8',
              font: { size: 11 },
              callback: (v) => '₹' + Number(v).toLocaleString('en-IN'),
            },
            border: { display: false },
          },
        },
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
    };
  }, [isChartReady, JSON.stringify(monthlyKeys), JSON.stringify(monthlyVals)]);

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      <canvas ref={canvasRef} />
    </div>
  );
}

export default {
  CategoryBarChart,
  CategoryDoughnutChart,
  MonthlyTrendLineChart,
};