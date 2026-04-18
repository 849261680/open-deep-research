import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { useHistory } from '../contexts/HistoryContext';
import HistoryItem from './HistoryItem';

const HistoryList = ({ onResume }) => {
  const { history, currentResearch, searchHistory, groupedHistory } = useHistory();
  const [searchTerm, setSearchTerm] = useState('');

  const displayHistory = searchTerm ? searchHistory(searchTerm) : history;
  const grouped = groupedHistory();

  const groupTitles = {
    pinned: '已固定',
    today: '今天',
    yesterday: '昨天',
    lastWeek: '最近 7 天',
    older: '更早',
  };

  const renderGroup = (groupName, items) => {
    if (!items || items.length === 0) return null;
    return (
      <div key={groupName} className="mb-5">
        <p
          className="px-4 mb-2 uppercase tracking-widest text-text-tertiary"
          style={{ fontSize: '10px', fontWeight: 600 }}
        >
          {groupTitles[groupName]}
        </p>
        <div className="space-y-0.5">
          {items.map((research) => (
            <HistoryItem
              key={research.id}
              research={research}
              isActive={currentResearch && currentResearch.id === research.id}
              onResume={onResume}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="px-4 mb-4">
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-full bg-background-tertiary border border-border-light"
        >
          <Search className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" />
          <input
            type="text"
            placeholder="搜索历史..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none font-medium"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-1">
        {displayHistory.length === 0 ? (
          <div className="text-center py-10 px-4">
            <p className="text-sm text-text-tertiary font-medium">
              {searchTerm ? '没有找到匹配的记录' : '还没有研究历史'}
            </p>
          </div>
        ) : searchTerm ? (
          <div className="space-y-0.5 mb-4">
            {displayHistory.map((research) => (
              <HistoryItem
                key={research.id}
                research={research}
                isActive={currentResearch && currentResearch.id === research.id}
                onResume={onResume}
              />
            ))}
          </div>
        ) : (
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
