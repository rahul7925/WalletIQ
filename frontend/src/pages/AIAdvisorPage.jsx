import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, User, Sparkles, Trash2, ShieldCheck, Loader2 } from 'lucide-react';
import { api } from '../services/api';

const QUICK_PROMPTS = [
  'Analyze my spending trends and top expenses this month.',
  'Can I afford a vacation trip worth ₹45,000 next month?',
  'How can I optimize my monthly budget to save 25%?',
  'Review my upcoming bills and flag any risks.',
];

export default function AIAdvisorPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hello! I am WalletIQ AI Advisor, powered by Google Gemini. I have real-time visibility into your expenses, budgets, bills, and portfolios. How can I assist your wealth strategy today?',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  async function handleSend(textToSend) {
    const userMsg = (textToSend || input).trim();
    if (!userMsg || isThinking) return;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { role: 'user', content: userMsg, time }]);
    setInput('');
    setIsThinking(true);

    try {
      const res = await api.sendChatMessage(userMsg);
      const aiReply = res?.response || res?.message || 'I analyzed your request. Everything looks in order.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: aiReply,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '⚠️ ' + (err.message || 'Apologies, I encountered a temporary connection issue. Please try again.'),
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  }

  async function handleClearHistory() {
    try {
      await api.clearChatHistory();
    } catch {
      // soft fail
    }
    setMessages([
      {
        role: 'assistant',
        content: 'Chat context cleared. How can I help you analyze your finances?',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  }

  return (
    <div className="page-wrapper animate-fade" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bot size={22} color="var(--accent-gold)" />
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>AI Financial Advisor</h1>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Context-aware intelligence grounded in your personal transactions
          </p>
        </div>

        <button type="button" className="btn btn-secondary btn-sm" onClick={handleClearHistory} title="Clear conversation">
          <Trash2 size={14} />
          <span>Clear Context</span>
        </button>
      </div>

      {/* Chat messages viewport */}
      <div
        className="glass-card"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
          padding: '1.5rem',
          gap: '1.25rem',
          marginBottom: '1rem',
        }}
      >
        {messages.map((m, idx) => {
          const isAi = m.role === 'assistant';
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                gap: '0.875rem',
                alignSelf: isAi ? 'flex-start' : 'flex-end',
                maxWidth: '85%',
                flexDirection: isAi ? 'row' : 'row-reverse',
              }}
            >
              <div
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  background: isAi ? 'var(--accent-gold-dim)' : 'var(--accent-purple-dim)',
                  color: isAi ? 'var(--accent-gold)' : 'var(--accent-purple)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {isAi ? <Bot size={18} /> : <User size={18} />}
              </div>

              <div>
                <div
                  style={{
                    padding: '0.875rem 1.125rem',
                    borderRadius: 'var(--radius-lg)',
                    background: isAi ? 'var(--bg-elevated)' : 'linear-gradient(135deg, #c8a96e 0%, #a4813f 100%)',
                    color: isAi ? 'var(--text-primary)' : '#0a0a0f',
                    border: isAi ? '1px solid var(--border-color)' : 'none',
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                    boxShadow: isAi ? 'none' : '0 2px 10px rgba(200, 169, 110, 0.25)',
                  }}
                >
                  {m.content}
                </div>
                <div
                  style={{
                    fontSize: '0.6875rem',
                    color: 'var(--text-muted)',
                    marginTop: '0.25rem',
                    textAlign: isAi ? 'left' : 'right',
                  }}
                >
                  {m.time}
                </div>
              </div>
            </div>
          );
        })}

        {isThinking && (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', color: 'var(--accent-gold)', fontSize: '0.8125rem' }}>
            <Loader2 size={16} className="animate-spin" />
            <span>WalletIQ AI is reasoning through your financial context...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips */}
      <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.75rem', scrollbarWidth: 'none' }}>
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem', whiteSpace: 'nowrap', flexShrink: 0 }}
            onClick={() => handleSend(prompt)}
            disabled={isThinking}
          >
            <Sparkles size={12} color="var(--accent-gold)" />
            <span>{prompt}</span>
          </button>
        ))}
      </div>

      {/* Input box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        style={{ display: 'flex', gap: '0.75rem' }}
      >
        <input
          type="text"
          className="form-input"
          placeholder="Ask anything about your money, budgets, or investments..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isThinking}
        />
        <button type="submit" className="btn btn-primary" disabled={isThinking || !input.trim()}>
          <Send size={16} />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
