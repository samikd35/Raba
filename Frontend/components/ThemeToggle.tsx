"use client"
import { useTheme } from 'next-themes'
import { Moon, Sun } from 'lucide-react'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const isDark = theme === 'dark'
  return (
    <button
      aria-label="Toggle dark mode"
      aria-pressed={isDark}
      className="p-2 rounded-md border border-[var(--border)] hover:shadow-glow transition focus-ring"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
    >
      <span className="sr-only">Toggle theme</span>
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

