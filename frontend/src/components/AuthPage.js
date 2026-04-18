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
    padding: '16px 18px',
    background: '#F8FBF5',
    border: '1px solid #E2E5DE',
    borderRadius: '16px',
    fontSize: '17px',
    fontWeight: 500,
    color: '#0e0f0c',
    outline: 'none',
    transition: 'border-color 150ms ease',
    fontFeatureSettings: '"calt"',
  };

  const isRegister = mode === 'register';
  const heading = isRegister ? '注册后开始使用' : '登录解锁更多功能';
  const submitLabel = loading ? '请稍候...' : isRegister ? '创建账户' : '登录';
  const switchPrompt = isRegister ? '已经有账号了？' : '还没有账号？';
  const switchLabel = isRegister ? '返回登录' : '立即注册';

  const content = (
    <div
      className="w-full"
      style={{ maxWidth: isModal ? '560px' : '620px', width: isModal ? 'calc(100vw - 24px)' : '100%' }}
    >
      <div
        className="bg-white w-full"
        style={{
          borderRadius: '32px',
          boxShadow: 'rgba(14,15,12,0.10) 0px 0px 0px 1px, 0 20px 60px rgba(14,15,12,0.10)',
          padding: isModal ? '24px' : '28px',
        }}
      >
        <section className="relative">
          <div
            style={{
              width: '92%',
              margin: '0 auto',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: '16px',
            }}
          >
            <h1 style={{ fontSize: '34px', fontWeight: 900, lineHeight: 0.95, color: '#0e0f0c', letterSpacing: 'normal' }}>
              {heading}
            </h1>
            {isModal && (
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-full hover:bg-background-secondary transition-colors duration-fast btn-scale flex-shrink-0"
                aria-label="关闭"
                style={{ marginTop: '-2px', marginRight: '-8px' }}
              >
                <X className="w-5 h-5 text-text-secondary" />
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-5 mt-7">
            <div style={{ width: '92%', margin: '0 auto' }}>
              <label
                className="block text-sm font-semibold text-text-secondary mb-2"
                style={{ transform: 'translateY(3px)' }}
              >
                邮箱
              </label>
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

            <div style={{ width: '92%', margin: '0 auto' }}>
              <div className="flex items-center justify-between mb-2">
                <label
                  className="block text-sm font-semibold text-text-secondary"
                  style={{ transform: 'translateY(3px)' }}
                >
                  密码
                </label>
                {isRegister && (
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#868685' }}>至少 6 位</span>
                )}
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={isRegister ? '请输入至少 6 位密码' : '请输入密码'}
                minLength={isRegister ? 6 : undefined}
                style={inputStyle}
                onFocus={(e) => { e.target.style.borderColor = '#9fe870'; }}
                onBlur={(e) => { e.target.style.borderColor = '#E2E5DE'; }}
              />
            </div>

            {error && (
              <p className="text-sm font-medium" style={{ color: '#d03238' }}>{error}</p>
            )}

            <div className="flex justify-center pt-1">
              <button
                type="submit"
                disabled={loading}
                className="rounded-full font-semibold btn-scale transition-transform duration-fast disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none"
                style={{ background: '#9fe870', color: '#163300', fontSize: '18px', padding: '16px 20px', width: '72%', minWidth: '220px' }}
              >
                {submitLabel}
              </button>
            </div>
          </form>

          <div
            className="mt-8 pt-5 flex items-center justify-center gap-2"
            style={{ borderTop: '1px solid #E8ECE3' }}
          >
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#6b6f68' }}>
              {switchPrompt}
            </span>
            <button
              type="button"
              onClick={() => {
                setMode(isRegister ? 'login' : 'register');
                setError('');
                setPassword('');
              }}
              className="font-semibold transition-colors duration-fast"
              style={{ fontSize: '14px', color: '#163300' }}
            >
              {switchLabel}
            </button>
          </div>
        </section>
      </div>
    </div>
  );

  if (isModal) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center px-2"
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
