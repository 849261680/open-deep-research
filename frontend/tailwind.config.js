/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Helvetica', 'Arial', 'sans-serif'],
        display: ['Inter', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        // Wise-inspired palette
        background: {
          primary: '#FFFFFF',
          secondary: '#F5F8F2',   // warm green-tinted surface
          tertiary: '#EBF0E7',    // light surface
        },
        primary: {
          DEFAULT: '#0e0f0c',     // near-black
          light: '#454745',
          dark: '#000000',
        },
        accent: {
          DEFAULT: '#9fe870',     // Wise Green
          light: '#cdffad',       // pastel green
          dark: '#163300',        // dark green (button text)
          mint: '#e2f6d5',        // light mint surface
        },
        success: {
          DEFAULT: '#054d28',
          light: '#9fe870',
          dark: '#163300',
          bg: '#e2f6d5',
        },
        warning: {
          DEFAULT: '#ffd11a',
          light: '#ffe566',
          dark: '#b8960a',
          bg: '#FFF9E0',
        },
        error: {
          DEFAULT: '#d03238',
          light: '#e06060',
          dark: '#a01f24',
          bg: '#FDECEA',
        },
        info: {
          DEFAULT: '#0e0f0c',
          light: '#454745',
          dark: '#000000',
          bg: 'rgba(56,200,255,0.10)',
        },
        // Text
        text: {
          primary: '#0e0f0c',
          secondary: '#454745',
          tertiary: '#868685',
          disabled: '#c0c0bf',
        },
        // Borders — approximation of rgba(14,15,12,0.12) on white
        border: {
          light: '#E2E5DE',
          medium: '#C4C9C1',
          DEFAULT: '#E2E5DE',
        },
        divider: '#EBF0E7',
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
        '3xl': '64px',
      },
      boxShadow: {
        // Wise ring shadow philosophy
        xs: 'rgba(14,15,12,0.08) 0px 0px 0px 1px',
        sm: 'rgba(14,15,12,0.12) 0px 0px 0px 1px',
        DEFAULT: 'rgba(14,15,12,0.12) 0px 0px 0px 1px',
        md: 'rgba(14,15,12,0.12) 0px 0px 0px 1px',
        lg: 'rgba(14,15,12,0.16) 0px 0px 0px 1px, rgba(14,15,12,0.08) 0px 4px 12px',
        xl: 'rgba(14,15,12,0.16) 0px 0px 0px 1px, rgba(14,15,12,0.10) 0px 8px 24px',
        inset: 'rgb(134,134,133) 0px 0px 0px 1px inset',
        none: 'none',
      },
      borderRadius: {
        xs: '2px',
        sm: '4px',
        DEFAULT: '10px',
        md: '16px',      // small card
        lg: '20px',      // medium card
        xl: '30px',      // feature card
        '2xl': '40px',   // large card / table
        '3xl': '1000px',
        full: '9999px',  // pill — all buttons
      },
      fontSize: {
        xs: ['12px', { lineHeight: '1.5', letterSpacing: '-0.084px' }],
        sm: ['14px', { lineHeight: '1.5', letterSpacing: '-0.084px' }],
        base: ['16px', { lineHeight: '1.44', letterSpacing: '0.18px' }],
        lg: ['18px', { lineHeight: '1.44', letterSpacing: '-0.108px' }],
        xl: ['22px', { lineHeight: '1.25', letterSpacing: '-0.396px' }],
        '2xl': ['26px', { lineHeight: '1.23', letterSpacing: '-0.39px' }],
        '3xl': ['40px', { lineHeight: '0.85', letterSpacing: 'normal' }],
        '4xl': ['64px', { lineHeight: '0.85', letterSpacing: 'normal' }],
        '5xl': ['96px', { lineHeight: '0.85', letterSpacing: 'normal' }],
      },
      fontWeight: {
        normal: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
        black: '900',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 300ms ease-out',
        'slide-in': 'slideIn 400ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 150ms ease-out',
        'spin': 'spin 1s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateY(-16px) scale(0.97)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      transitionDuration: {
        fast: '150ms',
        normal: '200ms',
        slow: '300ms',
      },
      maxWidth: {
        reading: '720px',
        container: '1200px',
      },
      scale: {
        '98': '0.98',
        '102': '1.02',
        '105': '1.05',
        '95': '0.95',
      },
    },
  },
  plugins: [],
}
