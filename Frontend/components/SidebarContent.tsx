"use client"
import { useSidebar } from './Sidebar'
import type { ReactNode } from 'react'
import { clsx } from 'clsx'

export function LayoutContent({ children }: { children: ReactNode }) {
  const { isCollapsed } = useSidebar()
  
  return (
    <div
      className={clsx(
        'transition-all duration-300 ease-in-out min-h-screen',
        'md:ml-64', // Default expanded width on md+
      )}
      style={{ 
        marginLeft: isCollapsed ? '4rem' : '16rem'
      }}
    >
      {children}
    </div>
  )
}
