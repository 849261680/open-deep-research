import React from 'react';
import { Menu, Search } from 'lucide-react';

/**
 * Header - 极简顶部导航栏
 *
 * 固定在页面顶部，显示应用名称和移动端菜单按钮
 */
const Header = ({ onMenuClick }) => {
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

        {/* 右侧 - 预留位置（可添加设置、用户头像等） */}
        <div className="flex items-center gap-2">
          {/* 未来可以添加：设置图标、用户头像等 */}
        </div>
      </div>
    </header>
  );
};

export default Header;