import React from 'react';

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
  const baseStyles = [
    'inline-flex items-center justify-center',
    'font-semibold rounded-full',
    'transition-transform duration-fast',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-accent',
    'disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none',
    'btn-scale',
  ].join(' ');

  const variants = {
    primary: [
      'bg-accent text-accent-dark',
      'hover:bg-accent-light',
    ].join(' '),
    secondary: [
      'bg-transparent border text-text-primary',
      'border-border-medium hover:bg-background-secondary',
    ].join(' '),
    ghost: [
      'bg-transparent text-text-secondary',
      'hover:bg-background-secondary hover:text-text-primary',
    ].join(' '),
    danger: [
      'bg-error text-white',
      'hover:bg-error-dark',
    ].join(' '),
  };

  const sizes = {
    small: 'px-4 py-1.5 text-sm gap-1.5',
    medium: 'px-5 py-2.5 text-base gap-2',
    large: 'px-6 py-3 text-lg gap-2',
  };

  const buttonClasses = `${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`;

  const loadingSpinner = (
    <span className="inline-flex">
      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
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
      {!loading && icon && iconPosition === 'left' && icon}
      {children}
      {!loading && icon && iconPosition === 'right' && icon}
    </button>
  );
};

export default Button;
