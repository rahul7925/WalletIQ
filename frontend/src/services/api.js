/**
 * api.js — Centralized WalletIQ REST API Client
 * Seamlessly talks to Railway Flask REST API with Bearer Token + Cookie fallback.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_PREFIX = `${BASE_URL}/api/v1`;

function getStoredToken() {
  try {
    return localStorage.getItem('walletiq_token');
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem('walletiq_token', token);
    } else {
      localStorage.removeItem('walletiq_token');
    }
  } catch (e) {
    console.error('Failed to update stored token', e);
  }
}

let wakingTimer = null;
let activeRequests = 0;

function onRequestStart() {
  activeRequests++;
  if (activeRequests === 1) {
    wakingTimer = setTimeout(() => {
      try {
        window.dispatchEvent(new CustomEvent('walletiq:server-waking'));
      } catch {}
    }, 3000);
  }
}

function onRequestEnd() {
  activeRequests = Math.max(0, activeRequests - 1);
  if (activeRequests === 0) {
    if (wakingTimer) {
      clearTimeout(wakingTimer);
      wakingTimer = null;
    }
    try {
      window.dispatchEvent(new CustomEvent('walletiq:server-ready'));
    } catch {}
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_PREFIX}${endpoint}`;
  const token = getStoredToken();

  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If payload is not FormData, default to JSON
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  onRequestStart();
  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });

    // Handle file downloads
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/pdf') || contentType.includes('application/vnd.openxmlformats') || contentType.includes('text/csv')) {
      if (!response.ok) {
        throw new Error(`File download failed with status ${response.status}`);
      }
      return response.blob();
    }

    let json;
    try {
      json = await response.json();
    } catch (err) {
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      throw new Error('Invalid JSON response from server');
    }

    if (!response.ok || json.success === false) {
      const errorMsg = json.error?.message || json.message || `Request failed (${response.status})`;
      const error = new Error(errorMsg);
      error.status = response.status;
      error.code = json.error?.code || 'ERROR';
      error.details = json.error?.details || null;
      throw error;
    }

    return json.data;
  } finally {
    onRequestEnd();
  }
}


export const api = {
  // ── 1. Authentication ──────────────────────────────────────────────────────
  register: (payload) => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  getMe: () => request('/auth/me', { method: 'GET' }),
  forgotPassword: (payload) => request('/auth/forgot-password', { method: 'POST', body: JSON.stringify(payload) }),
  updateProfile: (payload) => request('/auth/update-profile', { method: 'POST', body: JSON.stringify(payload) }),

  // ── 2. Dashboard ───────────────────────────────────────────────────────────
  getDashboardSummary: () => request('/dashboard/summary', { method: 'GET' }),
  getDashboardStats: () => request('/dashboard/stats', { method: 'GET' }),

  // ── 3. Expenses ────────────────────────────────────────────────────────────
  getExpenses: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/expenses${query ? `?${query}` : ''}`, { method: 'GET' });
  },
  createExpense: (payload) => request('/expenses', { method: 'POST', body: JSON.stringify(payload) }),
  updateExpense: (id, payload) => request(`/expenses/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteExpense: (id) => request(`/expenses/${id}`, { method: 'DELETE' }),
  exportCsv: () => request('/export/csv', { method: 'GET' }),

  // ── 4. OCR Receipt ─────────────────────────────────────────────────────────
  scanReceipt: (file) => {
    const formData = new FormData();
    formData.append('receipt', file);
    return request('/ocr/receipt', { method: 'POST', body: formData });
  },

  // ── 5. Budgets ─────────────────────────────────────────────────────────────
  getBudgets: () => request('/budgets', { method: 'GET' }),
  saveBudget: (payload) => request('/budgets', { method: 'POST', body: JSON.stringify(payload) }),
  deleteBudget: (id) => request(`/budgets/${id}`, { method: 'DELETE' }),

  // ── 6. Investments ─────────────────────────────────────────────────────────
  getInvestments: () => request('/investments', { method: 'GET' }),
  createInvestment: (payload) => request('/investments', { method: 'POST', body: JSON.stringify(payload) }),
  updateInvestment: (id, payload) => request(`/investments/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteInvestment: (id) => request(`/investments/${id}`, { method: 'DELETE' }),

  // ── 7. Bills ───────────────────────────────────────────────────────────────
  getBills: () => request('/bills', { method: 'GET' }),
  createBill: (payload) => request('/bills', { method: 'POST', body: JSON.stringify(payload) }),
  updateBill: (id, payload) => request(`/bills/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteBill: (id) => request(`/bills/${id}`, { method: 'DELETE' }),
  payBill: (id) => request(`/bills/pay/${id}`, { method: 'POST' }),
  getBillCalendar: (month, year) => request(`/bills/calendar?month=${month || ''}&year=${year || ''}`, { method: 'GET' }),
  getBillReminders: () => request('/bills/reminders', { method: 'GET' }),

  // ── 8. AI Financial Advisor ────────────────────────────────────────────────
  sendChatMessage: (message) => request('/ai/chat', { method: 'POST', body: JSON.stringify({ message, question: message, prompt: message }) }),
  getChatContext: () => request('/ai/context', { method: 'GET' }),
  clearChatHistory: () => request('/ai/clear', { method: 'POST' }),
  getAiRecommendations: () => request('/ai/recommendations', { method: 'GET' }),

  // ── 9. Financial Health & Predictions ──────────────────────────────────────
  getFinancialHealth: () => request('/financial-health', { method: 'GET' }),
  updateIncome: (monthly_income) => request('/financial-health/income', { method: 'POST', body: JSON.stringify({ monthly_income }) }),
  getSavingsPrediction: (months = 6, extraDeposit = 0, returnRate = 0) =>
    request(`/predictions/savings?months=${months}&extra_deposit=${extraDeposit}&return_rate=${returnRate}`, { method: 'GET' }),
  saveSavingsPrediction: (payload) => request('/predictions/savings/save', { method: 'POST', body: JSON.stringify(payload) }),
  getLoanEligibility: (payload) => request('/predictions/loan', { method: 'POST', body: JSON.stringify(payload) }),

  // ── 10. Goals ──────────────────────────────────────────────────────────────
  getGoals: () => request('/goals', { method: 'GET' }),
  createGoal: (payload) => request('/goals', { method: 'POST', body: JSON.stringify(payload) }),
  updateGoalSavings: (id, payload) => request(`/goals/${id}/savings`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGoal: (id) => request(`/goals/${id}`, { method: 'DELETE' }),
  getGoalRecommendations: () => request('/goals/recommendations', { method: 'GET' }),

  // ── 11. Spending Insights ──────────────────────────────────────────────────
  getSpendingInsights: () => request('/insights/spending', { method: 'GET' }),

  // ── 12. Reports ────────────────────────────────────────────────────────────
  getReports: () => request('/reports', { method: 'GET' }),
  generateReport: (payload) => request('/reports/generate', { method: 'POST', body: JSON.stringify(payload) }),
  deleteReport: (id) => request(`/reports/${id}`, { method: 'DELETE' }),
  compareReports: (reportId1, reportId2) =>
    request('/reports/compare', { method: 'POST', body: JSON.stringify({ report_id_1: reportId1, report_id_2: reportId2 }) }),
  shareReport: (id) => request(`/reports/share/${id}`, { method: 'POST' }),
  getSharedReport: (token) => request(`/reports/shared/${token}`, { method: 'GET' }),
  getDownloadUrl: (id) => `${API_PREFIX}/reports/download/${id}`,

  // ── 13. Notifications ──────────────────────────────────────────────────────
  getNotifications: () => request('/notifications', { method: 'GET' }),
  markNotificationRead: (id) => request(`/notifications/read/${id}`, { method: 'POST' }),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'POST' }),
};

export default api;
