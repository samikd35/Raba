import type { ReactNode } from 'react'
import './globals.css'
import { Providers } from './providers'
import { Header } from '@/components/Header'
import { Sidebar, SidebarProvider } from '@/components/Sidebar'
import { LayoutContent } from '@/components/SidebarContent'

export const metadata = {
  title: 'RABA — AI Shorts Generator',
  description: 'AI-Powered Multi-Agent YouTube Shorts Generator',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <Providers>
          <SidebarProvider>
            <Sidebar />
            <LayoutContent>
              <Header />
              <main className="container mx-auto px-4 py-6">{children}</main>
            </LayoutContent>
          </SidebarProvider>
        </Providers>
      </body>
    </html>
  )
}

