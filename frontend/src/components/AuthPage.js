import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function AuthPage({ onClose = null }) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const isModal = typeof onClose === 'function';

  useEffect(() => {
    if (!isModal) return undefined;
    const handleKeyDown = (event) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModal, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') await login(email, password);
      else await register(email, password);
      if (isModal) onClose();
    } catch (err) {
      const detail = err?.details?.detail || err?.message;
      setError(detail || (mode === 'login' ? '登录失败，请检查邮箱和密码' : '注册失败，请重试'));
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '12px 16px',
    background: '#F5F8F2',
    border: '1px solid #E2E5DE',
    borderRadius: '12px',
    fontSize: '15px',
    fontWeight: 500,
    color: '#0e0f0c',
    outline: 'none',
    transition: 'border-color 150ms ease',
    fontFeatureSettings: '"calt"',
  };

  const content = (
    <div className="w-full" style={{ maxWidth: '380px' }}>
      {isModal && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-background-secondary transition-colors duration-fast btn-scale"
            aria-label="关闭"
          >
            <X className="w-4 h-4 text-text-secondary" />
          </button>
        </div>
      )}

      {/* Brand */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full mb-4" style={{ background: '#9fe870' }}>
          <svg width="24" height="24" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="5" stroke="#163300" strokeWidth="2" />
            <path d="M5.5 8.5L7 10L10.5 6" stroke="#163300" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 style={{ fontSize: '28px', fontWeight: 900, lineHeight: 0.9, color: '#0e0f0c', letterSpacing: 'normal' }}>
          DeepResearch
        </h1>
        <p className="text-text-tertiary mt-2" style={{ fontSize: '14px', fontWeight: 400 }}>
          智能深度研究助手
        </p>
      </div>

      {/* Card */}
      <div
        className="bg-white p-6"
        style={{ borderRadius: '30px', boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px' }}
      >
        {/* Tab switcher */}
        <div className="flex mb-6 p-1 rounded-full" style={{ background: '#F5F8F2' }}>
          {['login', 'register'].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setError(''); }}
              className="flex-1 py-2 rounded-full transition-all duration-fast btn-scale"
              style={{
                fontSize: '14px',
                fontWeight: 600,
                background: mode === m ? '#FFFFFF' : 'transparent',
                color: mode === m ? '#0e0f0c' : '#868685',
                boxShadow: mode === m ? 'rgba(14,15,12,0.12) 0px 0px 0px 1px' : 'none',
              }}
            >
              {m === 'login' ? '登录' : '注册'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-text-secondary mb-1.5">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              style={inputStyle}
              onFocus={(e) => { e.target.style.borderColor = '#9fe870'; }}
              onBlur={(e) => { e.target.style.borderColor = '#E2E5DE'; }}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-text-secondary mb-1.5">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder={mode === 'register' ? '至少 6 位' : ''}
              minLength={mode === 'register' ? 6 : undefined}
              style={inputStyle}
              onFocus={(e) => { e.target.style.borderColor = '#9fe870'; }}
              onBlur={(e) => { e.target.style.borderColor = '#E2E5DE'; }}
            />
          </div>

          {error && (
            <p className="text-sm font-medium" style={{ color: '#d03238' }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-full font-semibold text-sm btn-scale transition-transform duration-fast disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none"
            style={{ background: '#9fe870', color: '#163300', fontSize: '15px' }}
          >
            {loading ? '请稍候...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>
      </div>
    </div>
  );

  if (isModal) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center px-4"
        style={{ background: 'rgba(14,15,12,0.5)' }}
        onClick={onClose}
      >
        <div onClick={(e) => e.stopPropagation()}>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4">
      {content}
    </div>
  );
}
