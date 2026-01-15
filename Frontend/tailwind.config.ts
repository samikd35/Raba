import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Brand per color_guide.md
        indigo: {
          500: '#6366F1'
        },
        cyan: {
          500: '#06B6D4'
        },
        lime: {
          300: '#BEF264'
        },
        // Surfaces
        background: {
          light: '#F2F4F7',
          dark: '#09090B'
        },
        surface: {
          light: '#FFFFFF',
          dark: '#121217'
        },
        border: {
          light: '#E2E8F0',
          dark: 'rgba(255,255,255,0.08)'
        }
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(99,102,241,0.35), 0 8px 40px rgba(99,102,241,0.15)'
      },
      keyframes: {
        borderBeam: {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '200% 0%' }
        }
      },
      animation: {
        borderBeam: 'borderBeam 2.4s linear infinite'
      }
    }
  },
  plugins: [],
} satisfies Config

