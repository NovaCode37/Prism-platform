import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        bg: 'rgb(var(--background) / <alpha-value>)',
        surface: {
          1: 'rgb(var(--surface-1) / <alpha-value>)',
          2: 'rgb(var(--surface-2) / <alpha-value>)',
          3: '#1c2330',
        },
        border: {
          1: 'rgb(var(--border-1) / <alpha-value>)',
          2: 'rgb(var(--border-2) / <alpha-value>)',
          3: 'rgb(var(--border-3) / <alpha-value>)',
        },
        text: {
          1: 'rgb(var(--text-1) / <alpha-value>)',
          2: 'rgb(var(--text-2) / <alpha-value>)',
          3: 'rgb(var(--text-3) / <alpha-value>)',
        },
        blue: 'rgb(var(--blue) / <alpha-value>)',
        purple: 'rgb(var(--purple) / <alpha-value>)',
        green: 'rgb(var(--green) / <alpha-value>)',
        red: 'rgb(var(--red) / <alpha-value>)',
        yellow: 'rgb(var(--yellow) / <alpha-value>)',
        orange: '#e3812b',
      },
      backgroundImage: {
        grad: 'linear-gradient(135deg, #4f8ef7, #7c5cfc)',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,.4), 0 0 0 1px rgba(255,255,255,.06)',
        glow: '0 0 20px rgba(79,142,247,.25)',
        'glow-sm': '0 0 10px rgba(79,142,247,.15)',
      },
      borderRadius: {
        card: '10px',
        sm: '6px',
      },
      animation: {
        spin: 'spin 0.8s linear infinite',
        'fade-in': 'fadeIn 0.2s ease',
        'slide-up': 'slideUp 0.25s ease',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
};

export default config;
