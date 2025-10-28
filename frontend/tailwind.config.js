/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 主色系 - 优雅的中性灰和深蓝灰
        background: {
          primary: '#FFFFFF',
          secondary: '#F8F9FA',
          tertiary: '#F1F3F4',
        },
        primary: {
          DEFAULT: '#2C3E50',
          light: '#5D6D7E',
          dark: '#1A252F',
        },
        accent: {
          DEFAULT: '#3498DB',
          light: '#5DADE2',
          dark: '#2874A6',
        },
        // 语义色
        success: {
          DEFAULT: '#27AE60',
          light: '#58D68D',
          dark: '#1E8449',
          bg: '#E8F8F5',
        },
        warning: {
          DEFAULT: '#F39C12',
          light: '#F8C471',
          dark: '#D68910',
          bg: '#FEF5E7',
        },
        error: {
          DEFAULT: '#E74C3C',
          light: '#EC7063',
          dark: '#C0392B',
          bg: '#FADBD8',
        },
        info: {
          DEFAULT: '#3498DB',
          light: '#5DADE2',
          dark: '#2874A6',
          bg: '#EBF5FB',
        },
        // 文字颜色
        text: {
          primary: '#1A1A1A',
          secondary: '#6B7280',
          tertiary: '#9CA3AF',
          disabled: '#D1D5DB',
        },
        // 边框和分割线
        border: {
          light: '#E5E7EB',
          medium: '#D1D5DB',
          DEFAULT: '#E5E7EB',
        },
        divider: '#F3F4F6',
      },
      // 间距系统（8px 基准）
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
        '3xl': '64px',
      },
      // 阴影系统（极简柔和）
      boxShadow: {
        xs: '0 1px 2px rgba(0, 0, 0, 0.04)',
        sm: '0 1px 3px rgba(0, 0, 0, 0.06)',
        DEFAULT: '0 1px 3px rgba(0, 0, 0, 0.06)',
        md: '0 4px 6px rgba(0, 0, 0, 0.05)',
        lg: '0 10px 15px rgba(0, 0, 0, 0.05)',
        xl: '0 20px 25px rgba(0, 0, 0, 0.05)',
      },
      // 圆角系统
      borderRadius: {
        xs: '2px',
        sm: '4px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
        '2xl': '16px',
      },
      // 字体系统
      fontSize: {
        xs: ['12px', { lineHeight: '16px' }],
        sm: ['14px', { lineHeight: '20px' }],
        base: ['16px', { lineHeight: '24px' }],
        lg: ['18px', { lineHeight: '28px' }],
        xl: ['20px', { lineHeight: '28px' }],
        '2xl': ['24px', { lineHeight: '32px' }],
        '3xl': ['30px', { lineHeight: '36px' }],
      },
      // 动画
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 300ms ease-out',
        'slide-in': 'slideIn 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 150ms ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': {
            opacity: '0',
            transform: 'translateY(-20px) scale(0.95)'
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0) scale(1)'
          },
        },
        slideUp: {
          '0%': { transform: 'translateY(2px)' },
          '100%': { transform: 'translateY(0)' },
        },
      },
      // 过渡
      transitionDuration: {
        fast: '150ms',
        normal: '200ms',
        slow: '300ms',
      },
      // 最大宽度（阅读宽度）
      maxWidth: {
        reading: '720px',
        container: '1200px',
      },
    },
  },
  plugins: [],
}