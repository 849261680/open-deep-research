import React from 'react';
import { LogOut, Menu, Search } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

/**
 * Header - 极简顶部导航栏
 *
 * 固定在页面顶部，显示应用名称和移动端菜单按钮
 */
const Header = ({ onMenuClick, onLoginClick }) => {
  const { user, logout } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-30 bg-background-primary border-b border-border-light h-12">
      <div className="h-full px-md flex items-center justify-between">
        {/* 左侧 - 菜单按钮（移动端）和 Logo */}
        <div className="flex items-center gap-3">
          {/* 移动端汉堡菜单 */}
          <button
            onClick={onMenuClick}
            className="md:hidden p-2 -ml-2 text-text-secondary hover:text-text-primary hover:bg-background-tertiary rounded transition-colors duration-fast"
            aria-label="打开菜单"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Logo 和应用名称 */}
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center">
              <Search className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-semibold text-text-primary">
              Research GPT
            </h1>
          </div>
        </div>

        {/* 右侧 - 用户信息和退出 */}
        {user ? (
          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-xs text-text-secondary truncate max-w-[160px]">
              {user.email}
            </span>
            <button
              onClick={logout}
              title="退出登录"
              className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-background-tertiary rounded transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onLoginClick}
            className="px-3 py-1.5 text-sm font-medium text-text-primary border border-border-light rounded-md hover:bg-background-tertiary transition-colors"
          >
            登录
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
