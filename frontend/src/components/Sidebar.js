import React from 'react';
import { PlusCircle, Activity } from 'lucide-react';
import Button from './Button';
import HistoryList from './HistoryList';

/**
 * Sidebar - 侧边栏组件
 *
 * 包含新建按钮、历史记录列表、底部状态
 */
const Sidebar = ({ backendStatus, onNewResearch, isMobile, isOpen, onClose }) => {
  // 移动端关闭侧边栏
  const handleOverlayClick = () => {
    if (isMobile && onClose) {
      onClose();
    }
  };

  // 移动端阻止点击事件冒泡
  const handleSidebarClick = (e) => {
    if (isMobile) {
      e.stopPropagation();
    }
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-background-secondary border-r border-border-light">
      {/* 头部 - 新建研究按钮 */}
      <div className="p-md border-b border-border-light flex-shrink-0">
        <Button
          variant="primary"
          size="large"
          icon={<PlusCircle className="w-4 h-4" />}
          onClick={onNewResearch}
          className="w-full"
        >
          新建研究
        </Button>
      </div>

      {/* 历史记录列表 */}
      <div className="flex-1 overflow-hidden py-md">
        <HistoryList />
      </div>

      {/* 底部 - 服务器状态 */}
      <div className="p-md border-t border-border-light flex-shrink-0">
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-text-tertiary" />
            <span className="text-text-secondary">服务状态:</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${
                backendStatus === 'online'
                  ? 'bg-success'
                  : backendStatus === 'offline'
                  ? 'bg-error'
                  : 'bg-warning animate-pulse'
              }`}
            />
            <span
              className={`font-medium ${
                backendStatus === 'online'
                  ? 'text-success'
                  : backendStatus === 'offline'
                  ? 'text-error'
                  : 'text-warning'
              }`}
            >
              {backendStatus === 'online'
                ? '在线'
                : backendStatus === 'offline'
                ? '离线'
                : '检查中'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  // 移动端：抽屉式侧边栏
  if (isMobile) {
    return (
      <>
        {/* 遮罩层 */}
        {isOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={handleOverlayClick}
          />
        )}

        {/* 侧边栏 */}
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

  // 桌面端：固定侧边栏
  return (
    <div className="hidden md:block w-72 flex-shrink-0 h-full">
      {sidebarContent}
    </div>
  );
};

export default Sidebar;
