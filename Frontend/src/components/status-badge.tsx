import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Loader2, CheckCircle2, XCircle, PauseCircle, Clock } from "lucide-react"

interface StatusBadgeProps {
    status: string
    className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
    const getStatusConfig = (status: string) => {
        switch (status) {
            case 'completed':
                return { color: 'bg-green-500/15 text-green-500 border-green-500/20', icon: CheckCircle2, label: 'Completed' }
            case 'failed':
                return { color: 'bg-red-500/15 text-red-500 border-red-500/20', icon: XCircle, label: 'Failed' }
            case 'running':
                return { color: 'bg-blue-500/15 text-blue-500 border-blue-500/20', icon: Loader2, label: 'Running', animate: true }
            case 'pending':
                return { color: 'bg-yellow-500/15 text-yellow-500 border-yellow-500/20', icon: Clock, label: 'Pending' }
            default:
                // Handle awaiting_* statuses
                if (status.startsWith('awaiting_')) {
                    return { color: 'bg-orange-500/15 text-orange-500 border-orange-500/20', icon: PauseCircle, label: 'Awaiting Approval', animate: true }
                }
                return { color: 'bg-muted text-muted-foreground', icon: Clock, label: status }
        }
    }

    const config = getStatusConfig(status)
    const Icon = config.icon

    return (
        <Badge
            variant="outline"
            className={cn("gap-1.5 py-1 px-2.5 capitalize border", config.color, className)}
        >
            <Icon className={cn("h-3.5 w-3.5", config.animate && "animate-spin")} />
            {config.label}
        </Badge>
    )
}
