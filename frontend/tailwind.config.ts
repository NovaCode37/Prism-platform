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
        bg: '#0d1117',
        surface: {
          1: '#0f1318',
          2: '#161b22',
          3: '#1c2330',
        },
        border: {
          1: 'rgba(255,255,255,0.05)',
          2: 'rgba(255,255,255,0.10)',
          3: 'rgba(255,255,255,0.18)',
        },
        text: {
          1: '#e6edf3',
          2: '#8b949e',
          3: '#484f58',
        },
        blue: '#4f8ef7',
        purple: '#7c5cfc',
        green: '#3fb950',
        red: '#f85149',
        yellow: '#d29922',
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
