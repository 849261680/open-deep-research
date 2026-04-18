import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const CollapsibleSection = ({
  title,
  headerMeta,
  children,
  defaultOpen = false,
  icon,
  badge,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={`overflow-hidden ${className}`}
      style={{
        borderRadius: '20px',
        boxShadow: 'rgba(14,15,12,0.12) 0px 0px 0px 1px',
        background: '#FFFFFF',
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 bg-background-secondary hover:bg-accent-mint transition-colors duration-fast text-left"
        aria-expanded={isOpen}
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="text-text-tertiary transition-transform duration-fast flex-shrink-0">
            {isOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>

          {icon && (
            <span className="text-accent-dark">{icon}</span>
          )}

          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-2">
              <span
                className="truncate text-text-primary"
                style={{ fontSize: '15px', fontWeight: 600, lineHeight: 1.4 }}
              >
                {title}
              </span>
              {badge && (
                <span
                  className="shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{ background: '#e2f6d5', color: '#163300' }}
                >
                  {badge}
                </span>
              )}
            </div>
            {headerMeta && (
              <div className="mt-1 min-w-0 text-xs text-text-tertiary font-normal">
                {headerMeta}
              </div>
            )}
          </div>
        </div>
      </button>

      <div
        className={`transition-all duration-slow ease-in-out overflow-hidden ${
          isOpen ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-5 py-5 border-t border-border-light">
          {children}
        </div>
      </div>
    </div>
  );
};

export default CollapsibleSection;
