'use client'

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
    Video,
    Activity,
    Zap,
    BarChart3,
    ChevronLeft,
    ChevronRight,
    Settings2
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/theme-toggle"

const startItems = [
    { name: 'Create', href: '/', icon: Video },
    { name: 'Workflows', href: '/workflows', icon: Activity },
    { name: 'Tools', href: '/tools', icon: Zap },
    { name: 'Monitoring', href: '/monitoring', icon: BarChart3 },
]

export function Sidebar() {
    const pathname = usePathname()
    const [collapsed, setCollapsed] = React.useState(false)

    return (
        <div
            className={cn(
                "relative flex flex-col border-r bg-background transition-all duration-300",
                collapsed ? "w-16" : "w-64"
            )}
        >

            {/* Header section removed */}

            {/* Toggle Button for Sidebar - Optional, or we can keep it inside the sidebar at the top or bottom. 
                For now, let's keep a simple collapse trigger if needed, or rely on the user dragging/clicking?
                The original design had it in the header. Let's put a collapse button at the top of the sidebar 
                or just keep the list. The requirement said "extend the header... only in the sidebar to the full screen".
                So the sidebar itself will just be the nav items.
            */}
            <div className="flex justify-end p-2">
                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground" onClick={() => setCollapsed(!collapsed)}>
                    {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                </Button>
            </div>


            {/* Navigation */}
            <div className="flex-1 overflow-auto pt-0 px-2 pb-4">
                <nav className="grid gap-1">

                    {startItems.map((item, index) => {
                        const isActive = pathname === item.href
                        return (
                            <Link
                                key={index}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted transition-colors",
                                    isActive ? "bg-muted text-primary" : "text-muted-foreground",
                                    collapsed && "justify-center px-2"
                                )}
                                title={collapsed ? item.name : undefined}
                            >
                                <item.icon className="h-4 w-4 shrink-0" />
                                {!collapsed && <span>{item.name}</span>}
                            </Link>
                        )
                    })}
                </nav>
            </div>

            {/* Footer */}
            <div className="border-t p-2">
                {/* Footer content if any */}
            </div>
        </div>
    )
}
