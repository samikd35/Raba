'use client'

import React from 'react'
import { ThemeToggle } from "@/components/theme-toggle"

export function Header() {
    return (
        <div className="flex h-14 items-center justify-between border-b px-4 bg-background z-50">
            <div className="flex items-center gap-2">
                {/* We can envision a logo here if needed, or just the text RABA */}
                <span className="font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent text-xl truncate">
                    RABA
                </span>
            </div>
            <div className="flex items-center gap-2">
                <ThemeToggle />
            </div>
        </div>
    )
}
