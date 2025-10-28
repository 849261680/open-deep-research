import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * LoadingSpinner - 极简加载动画
 *
 * 只显示旋转图标和当前步骤文字
 */
const LoadingSpinner = ({ message = '处理中...' }) => {
  return (
    <div className="flex flex-col items-center justify-center py-2xl">
      {/* 旋转图标 */}
      <div className="mb-lg">
        <Loader2 className="w-12 h-12 text-accent animate-spin" />
      </div>

      {/* 当前步骤文字 */}
      <p className="text-base text-text-secondary text-center">
        {message}
      </p>

      {/* 预计时间提示 */}
      <p className="mt-sm text-xs text-text-tertiary text-center">
        通常需要 30-60 秒
      </p>
    </div>
  );
};

export default LoadingSpinner;
