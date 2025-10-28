import React from 'react';

/**
 * Button - 统一的按钮组件
 *
 * 提供三种变体：
 * - primary: 主要按钮（深蓝灰背景）
 * - secondary: 次要按钮（透明背景 + 边框）
 * - ghost: 幽灵按钮（无边框）
 *
 * 提供三种尺寸：
 * - small: 小尺寸
 * - medium: 中等尺寸（默认）
 * - large: 大尺寸
 */
const Button = ({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
  className = '',
  onClick,
  type = 'button',
  ...props
}) => {
  // 基础样式
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-fast focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  // 变体样式
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-dark active:scale-98',
    secondary: 'bg-transparent border border-border-medium text-text-primary hover:bg-background-tertiary active:scale-98',
    ghost: 'bg-transparent text-text-secondary hover:bg-background-tertiary hover:text-text-primary',
  };

  // 尺寸样式
  const sizes = {
    small: 'px-4 py-2 text-sm rounded',
    medium: 'px-5 py-2.5 text-base rounded-md',
    large: 'px-6 py-3 text-base rounded-md',
  };

  const buttonClasses = `${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`;

  const iconElement = icon && (
    <span className={`inline-flex ${children ? (iconPosition === 'left' ? 'mr-2' : 'ml-2') : ''}`}>
      {icon}
    </span>
  );

  const loadingSpinner = (
    <span className="inline-flex mr-2">
      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </span>
  );

  return (
    <button
      type={type}
      className={buttonClasses}
      onClick={onClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading && loadingSpinner}
      {!loading && icon && iconPosition === 'left' && iconElement}
      {children}
      {!loading && icon && iconPosition === 'right' && iconElement}
    </button>
  );
};

export default Button;
