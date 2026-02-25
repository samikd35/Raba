'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Video, Zap, Activity } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'

export function Navigation() {
    const pathname = usePathname()

    const navItems = [
        { name: 'Create', href: '/', icon: Video },
        { name: 'Workflows', href: '/workflows', icon: Activity },
        { name: 'Tools', href: '/tools', icon: Zap },
    ]

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-14 items-center">
                <div className="mr-4 hidden md:flex">
                    <Link href="/" className="mr-6 flex items-center space-x-2">
                        <span className="hidden font-bold sm:inline-block bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent text-xl">
                            RABA
                        </span>
                    </Link>
                    <nav className="flex items-center space-x-6 text-sm font-medium">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "transition-colors hover:text-foreground/80 flex items-center gap-2",
                                    pathname === item.href ? "text-foreground" : "text-foreground/60"
                                )}
                            >
                                <item.icon className="h-4 w-4" />
                                {item.name}
                            </Link>
                        ))}
                    </nav>
                </div>
                <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
                    <div className="w-full flex-1 md:w-auto md:flex-none">
                        {/* Search placeholder could go here */}
                    </div>
                    <ThemeToggle />
                </div>
            </div>
        </header>
    )
}
