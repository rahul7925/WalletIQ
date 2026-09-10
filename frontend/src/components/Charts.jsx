import React, { useEffect, useRef, useState } from 'react';

export const CAT_COLORS = {
  Food: '#FFD75A',
  Bills: '#5B8CFF',
  Travel: '#5CD46B',
  Entertainment: '#B57CFF',
  Shopping: '#FF6B6B',
  Health: '#83C5C0',
  Investment: '#2ECC71',
  Education: '#FFAA54',
  Transport: '#4FA2E6',
  Utilities: '#6C5CE7',
  Savings: '#00B894',
  EMI: '#E17055',
  General: '#C8A96E',
  Others: '#7EE7F5',
};

const DEFAULT_PALETTE = ['#FFD75A', '#5CD46B', '#4FA2E6', '#B57CFF', '#FF6B6B', '#83C5C0', '#FFAA54', '#7EE7F5'];

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
            hoverBackgroundColor: colors.map((c) => c + 'DD'),
            borderRadius: { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 },
            borderSkipped: false,
            maxBarThickness: 36,
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
            borderColor: '#12121A',
            borderWidth: 2,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        animation: { duration: 600, easing: 'easeOutQuart' },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              borderRadius: 3,
              useBorderRadius: true,
              padding: 12,
              color: '#94A3B8',
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