import React from 'react';
import { LogOut, Menu } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Header = ({ onMenuClick, onLoginClick }) => {
  const { user, logout } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-30 bg-white border-b border-border-light h-14">
      <div className="h-full px-md flex items-center justify-between">
        {/* Left — menu + wordmark */}
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="md:hidden p-2 -ml-1 text-text-secondary hover:bg-background-secondary rounded-full transition-colors duration-fast"
            aria-label="打开菜单"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5">
            {/* Wise-style pill logo mark */}
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="5" stroke="#163300" strokeWidth="2" />
                <path d="M5.5 8.5L7 10L10.5 6" stroke="#163300" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="text-lg font-black text-text-primary tracking-tight" style={{ lineHeight: 1 }}>
              DeepResearch
            </span>
          </div>
        </div>

        {/* Right — user / login */}
        {user ? (
          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-sm text-text-secondary truncate max-w-[180px] font-medium">
              {user.email}
            </span>
            <button
              onClick={logout}
              title="退出登录"
              className="p-2 text-text-secondary hover:text-text-primary hover:bg-background-secondary rounded-full transition-colors duration-fast btn-scale"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onLoginClick}
            className="px-5 py-2 text-sm font-semibold text-accent-dark bg-accent rounded-full hover:bg-accent-light transition-transform duration-fast btn-scale"
          >
            登录
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
