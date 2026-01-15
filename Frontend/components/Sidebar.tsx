"use client"
import { useState, createContext, useContext } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Workflow, 
  Wrench, 
  BarChart3, 
  Menu, 
  X,
  Sparkles
} from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'
import { ConnectionStatus } from './ConnectionStatus'
import { clsx } from 'clsx'

const navItems = [
  { href: '/', label: 'Create', icon: Sparkles },
  { href: '/workflows', label: 'Workflows', icon: Workflow },
  { href: '/tools', label: 'Tools', icon: Wrench },
  { href: '/monitoring', label: 'Monitoring', icon: BarChart3 },
]

const SidebarContext = createContext<{ isCollapsed: boolean; setIsCollapsed: (collapsed: boolean) => void } | null>(null)

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within SidebarProvider')
  }
  return context
}

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  return (
    <SidebarContext.Provider value={{ isCollapsed, setIsCollapsed }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function Sidebar() {
  const { isCollapsed, setIsCollapsed } = useSidebar()
  const pathname = usePathname()

  return (
    <aside
        className={clsx(
          'fixed left-0 top-0 h-full z-40 transition-all duration-300 ease-in-out',
          'bg-[var(--surface)] border-r border-[var(--border)]',
          'flex flex-col',
          'hidden md:flex', // Hide on mobile, show on tablet+
          isCollapsed ? 'w-16' : 'w-64'
        )}
        style={{ '--sidebar-width': isCollapsed ? '4rem' : '16rem' } as React.CSSProperties}
      >
      {/* Header */}
      <div className={clsx('flex items-center p-4 border-b border-[var(--border)]', isCollapsed ? 'justify-center' : 'justify-between')}>
        {!isCollapsed && (
          <Link href="/" className="font-semibold text-lg text-[var(--text)] focus-ring flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[var(--brand)]" />
            <span>RABA</span>
          </Link>
        )}
        {isCollapsed && (
          <Link href="/" className="focus-ring flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-[var(--brand)]" />
          </Link>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={clsx('p-1.5 rounded-md hover:bg-[var(--border)] transition-colors focus-ring', !isCollapsed && 'ml-auto')}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <Menu className="w-5 h-5" />
          ) : (
            <X className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2" aria-label="Main Navigation">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href))
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all',
                'focus-ring',
                isActive
                  ? 'bg-[var(--brand)]/10 text-[var(--brand)] border border-[var(--brand)]/20'
                  : 'text-[var(--text)] opacity-80 hover:opacity-100 hover:bg-[var(--border)]'
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className={clsx('flex-shrink-0', isCollapsed ? 'w-5 h-5 mx-auto' : 'w-5 h-5')} />
              {!isCollapsed && (
                <span className="text-sm font-medium">{item.label}</span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[var(--border)] space-y-2">
        {!isCollapsed && (
          <div className="flex items-center gap-3">
            <ConnectionStatus />
          </div>
        )}
        {isCollapsed && (
          <div className="flex items-center justify-center">
            <ConnectionStatus />
          </div>
        )}
        <div className={clsx('flex items-center', isCollapsed && 'justify-center')}>
          <ThemeToggle />
        </div>
      </div>
    </aside>
  )
}
