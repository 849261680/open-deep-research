import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function AuthPage({ onClose = null }) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const isModal = typeof onClose === 'function';

  useEffect(() => {
    if (!isModal) {
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModal, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password);
      }
      if (isModal) {
        onClose();
      }
    } catch (err) {
      const detail = err?.details?.detail || err?.message;
      setError(detail || (mode === 'login' ? '登录失败，请检查邮箱和密码' : '注册失败，请重试'));
    } finally {
      setLoading(false);
    }
  };

  const content = (
    <div className="w-full max-w-sm">
      {isModal && (
        <div className="flex justify-end mb-3">
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-background-primary rounded-md transition-colors"
            aria-label="关闭登录窗口"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

        {/* Logo / 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-text-primary">Research GPT</h1>
          <p className="text-text-secondary text-sm mt-1">智能深度研究助手</p>
        </div>

        {/* 卡片 */}
        <div className="bg-background-secondary border border-border-primary rounded-xl p-6 shadow-lg">
          {/* Tab 切换 */}
          <div className="flex mb-6 bg-background-primary rounded-lg p-1">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); }}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
                mode === 'login'
                  ? 'bg-background-secondary text-text-primary shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              登录
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setError(''); }}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
                mode === 'register'
                  ? 'bg-background-secondary text-text-primary shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              注册
            </button>
          </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-text-secondary mb-1">邮箱</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full px-3 py-2 bg-background-primary border border-border-primary rounded-lg text-text-primary text-sm placeholder-text-tertiary focus:outline-none focus:border-accent-primary transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm text-text-secondary mb-1">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={mode === 'register' ? '至少 6 位' : ''}
                minLength={mode === 'register' ? 6 : undefined}
                className="w-full px-3 py-2 bg-background-primary border border-border-primary rounded-lg text-text-primary text-sm placeholder-text-tertiary focus:outline-none focus:border-accent-primary transition-colors"
              />
            </div>

            {error && (
              <p className="text-error text-sm">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 bg-accent-primary hover:bg-accent-hover text-white font-medium rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
        onClick={onClose}
      >
        <div onClick={(e) => e.stopPropagation()}>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-primary px-4">
      {content}
    </div>
  );
}
