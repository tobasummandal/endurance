import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        'bg-1': 'var(--bg-1)',
        fg: 'var(--fg)',
        dim: 'var(--dim)',
        line: 'var(--line)',
        sun: 'var(--sun)',
        'sun-warm': 'var(--sun-warm)',
        wrong: 'var(--wrong)',
        right: 'var(--right)',
      },
      fontFamily: {
        mono: ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
    },
  },
  plugins: [],
};

export default config;
