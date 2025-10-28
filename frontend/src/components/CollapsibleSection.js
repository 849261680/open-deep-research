import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

/**
 * CollapsibleSection - 可折叠区块组件
 *
 * 用于展示可展开/折叠的内容区域
 */
const CollapsibleSection = ({
  title,
  children,
  defaultOpen = false,
  icon,
  badge,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`border border-border-light rounded-lg overflow-hidden ${className}`}>
      {/* 头部 - 可点击展开/折叠 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-md py-sm bg-background-secondary hover:bg-background-tertiary transition-colors duration-fast text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          {/* 展开/折叠图标 */}
          <span className="text-text-secondary transition-transform duration-slow">
            {isOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>

          {/* 自定义图标 */}
          {icon && <span className="text-text-secondary">{icon}</span>}

          {/* 标题 */}
          <span className="font-medium text-text-primary">{title}</span>

          {/* 徽章 */}
          {badge && (
            <span className="ml-2 px-2 py-0.5 bg-background-tertiary text-text-secondary text-xs rounded-full">
              {badge}
            </span>
          )}
        </div>
      </button>

      {/* 内容区域 - 带动画的展开/折叠 */}
      <div
        className={`transition-all duration-slow ease-in-out overflow-hidden ${
          isOpen ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-md py-md border-t border-border-light">
          {children}
        </div>
      </div>
    </div>
  );
};

export default CollapsibleSection;
