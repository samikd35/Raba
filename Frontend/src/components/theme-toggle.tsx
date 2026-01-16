'use client'

import * as React from 'react'
import { Moon, Sun, Monitor } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
    const { setTheme, theme } = useTheme()
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return (
            <div className="flex items-center gap-1 border border-border rounded-lg p-1 bg-background/50 backdrop-blur-sm opacity-0">
                {/* Prevent layout shift by rendering invisible buttons of same size */}
                <Button variant="ghost" size="icon" className="h-7 w-7"><Sun className="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" className="h-7 w-7"><Moon className="h-4 w-4" /></Button>
            </div>
        )
    }

    return (
        <div className="flex items-center gap-1 border border-border rounded-lg p-1 bg-background/50 backdrop-blur-sm">
            <Button
                variant="ghost"
                size="icon"
                className={`h-7 w-7 rounded-md ${theme === 'light' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                onClick={() => setTheme('light')}
                aria-label="Light mode"
            >
                <Sun className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                className={`h-7 w-7 rounded-md ${theme === 'dark' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                onClick={() => setTheme('dark')}
                aria-label="Dark mode"
            >
                <Moon className="h-4 w-4" />
            </Button>
        </div>
    )
}
