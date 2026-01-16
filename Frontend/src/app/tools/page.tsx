'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Zap, Star } from 'lucide-react'

// Defined based on backend registry
interface Tool {
    tool_id: string
    tool_name: string
    category: string
    description: string
    version: number
    usage_count: number
    success_rate: number
    is_active: boolean
}

export default function ToolsPage() {
    const { data, isLoading } = useQuery({
        queryKey: ['tools'],
        queryFn: () => api.get<{ tools: Tool[] }>('/tools'),
    })

    return (
        <div className="container py-8 max-w-5xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight mb-2">Creative Tools</h1>
                <p className="text-muted-foreground">
                    The AI agents available in the RABA tool repository. These define the visual style and narrative strategy.
                </p>
            </div>

            {isLoading ? (
                <div className="grid gap-6 md:grid-cols-2">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-40" />)}
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {data?.tools.map((tool) => (
                        <Card key={tool.tool_id} className="relative overflow-hidden hover:border-primary/50 transition-colors">
                            <CardHeader>
                                <div className="flex justify-between items-start mb-2">
                                    <Badge variant="secondary" className="capitalize">
                                        {tool.category.replace('_', ' ')}
                                    </Badge>
                                    {tool.success_rate > 0.8 && (
                                        <Badge variant="outline" className="border-yellow-500/50 text-yellow-500 bg-yellow-500/10 gap-1">
                                            <Star className="h-3 w-3 fill-yellow-500" /> Top Rated
                                        </Badge>
                                    )}
                                </div>
                                <CardTitle className="flex items-center gap-2">
                                    <Zap className="h-5 w-5 text-primary" />
                                    {tool.tool_name}
                                </CardTitle>
                                <CardDescription className="line-clamp-2">
                                    {tool.description}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center justify-between text-sm text-muted-foreground">
                                    <span>v{tool.version}.0</span>
                                    <span>{tool.usage_count} Generations</span>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
