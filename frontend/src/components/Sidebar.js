import React from 'react';
import { PlusCircle, Activity } from 'lucide-react';
import HistoryList from './HistoryList';

const Sidebar = ({ backendStatus, onNewResearch, onResumeResearch, isMobile, isOpen, onClose }) => {
  const handleOverlayClick = () => {
    if (isMobile && onClose) onClose();
  };

  const handleSidebarClick = (e) => {
    if (isMobile) e.stopPropagation();
  };

  const statusColor = {
    online: '#9fe870',
    offline: '#d03238',
    checking: '#ffd11a',
  }[backendStatus] || '#ffd11a';

  const statusLabel = {
    online: '在线',
    offline: '离线',
    checking: '检查中',
  }[backendStatus] || '检查中';

  const sidebarContent = (
    <div className="flex flex-col h-full bg-background-secondary border-r border-border-light">
      {/* New research button */}
      <div className="p-md pt-5 border-b border-border-light flex-shrink-0">
        <button
          onClick={onNewResearch}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-accent text-accent-dark text-sm font-semibold rounded-full btn-scale transition-transform duration-fast"
        >
          <PlusCircle className="w-4 h-4" />
          新建研究
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-hidden py-md">
        <HistoryList onResume={onResumeResearch} />
      </div>

      {/* Status bar */}
      <div className="p-md border-t border-border-light flex-shrink-0">
        <div className="flex items-center gap-2 text-xs">
          <Activity className="w-3.5 h-3.5 text-text-tertiary" />
          <span className="text-text-tertiary font-medium">服务状态</span>
          <div className="flex items-center gap-1.5 ml-1">
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{
                backgroundColor: statusColor,
                boxShadow: backendStatus === 'checking' ? `0 0 0 2px ${statusColor}40` : 'none',
              }}
            />
            <span className="font-semibold" style={{ color: statusColor }}>
              {statusLabel}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  if (isMobile) {
    return (
      <>
        {isOpen && (
          <div
            className="fixed inset-0 bg-black/40 z-40 md:hidden"
            onClick={handleOverlayClick}
          />
        )}
        <div
          className={`fixed left-0 top-0 bottom-0 w-72 z-50 transform transition-transform duration-slow md:hidden ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          onClick={handleSidebarClick}
        >
          {sidebarContent}
        </div>
      </>
    );
  }

  return (
    <div className="hidden md:block w-72 flex-shrink-0 h-full">
      {sidebarContent}
    </div>
  );
};

export default Sidebar;
