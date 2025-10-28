import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { useHistory } from '../contexts/HistoryContext';
import HistoryItem from './HistoryItem';

/**
 * HistoryList - 历史记录列表组件
 *
 * 显示分组的历史记录
 * 支持搜索过滤
 */
const HistoryList = () => {
  const { history, currentResearch, searchHistory, groupedHistory } = useHistory();
  const [searchTerm, setSearchTerm] = useState('');

  // 获取要显示的历史记录
  const displayHistory = searchTerm ? searchHistory(searchTerm) : history;
  const grouped = groupedHistory();

  // 组标题映射
  const groupTitles = {
    pinned: '已固定',
    today: '今天',
    yesterday: '昨天',
    lastWeek: '最近 7 天',
    older: '更早',
  };

  // 渲染单个分组
  const renderGroup = (groupName, items) => {
    if (!items || items.length === 0) return null;

    return (
      <div key={groupName} className="mb-lg">
        <h3 className="text-xs font-medium text-text-tertiary px-md mb-sm uppercase tracking-wide">
          {groupTitles[groupName]}
        </h3>
        <div className="space-y-1">
          {items.map((research) => (
            <HistoryItem
              key={research.id}
              research={research}
              isActive={currentResearch && currentResearch.id === research.id}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* 搜索框 */}
      <div className="px-md mb-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input
            type="text"
            placeholder="搜索历史..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3 py-2 text-sm bg-background-tertiary border border-border-light rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-all duration-fast"
          />
        </div>
      </div>

      {/* 历史记录列表 */}
      <div className="flex-1 overflow-y-auto px-sm">
        {displayHistory.length === 0 ? (
          <div className="text-center py-xl px-md">
            <p className="text-sm text-text-tertiary">
              {searchTerm ? '没有找到匹配的记录' : '还没有研究历史'}
            </p>
          </div>
        ) : searchTerm ? (
          // 搜索结果显示为单个列表
          <div className="space-y-1 mb-md">
            {displayHistory.map((research) => (
              <HistoryItem
                key={research.id}
                research={research}
                isActive={currentResearch && currentResearch.id === research.id}
              />
            ))}
          </div>
        ) : (
          // 正常显示分组列表
          <>
            {renderGroup('pinned', grouped.pinned)}
            {renderGroup('today', grouped.today)}
            {renderGroup('yesterday', grouped.yesterday)}
            {renderGroup('lastWeek', grouped.lastWeek)}
            {renderGroup('older', grouped.older)}
          </>
        )}
      </div>
    </div>
  );
};

export default HistoryList;
