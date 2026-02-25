'use client'

import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts"
import { DollarSign, Activity, Clock, Database } from 'lucide-react'

// Types based on API docs
interface MonitoringSummary {
    period: {
        start: string
        end: string
        days: number
    }
    totals: {
        total_tokens: number
        total_cost_usd: number
        total_videos: number
        completed_videos: number
        failed_videos: number
    }
    by_generation_type: Record<string, {
        tokens: number
        cost_usd: number
        count: number
    }>
    by_model: Record<string, {
        tokens: number
        cost_usd: number
        calls: number
    }>
    metrics: {
        success_rate: number
        cache_hit_rate: number
        avg_generation_time_seconds: number
        avg_cost_per_video_usd: number
    }
}

export default function MonitoringPage() {
    const [days, setDays] = useState("7")

    const { data, isLoading } = useQuery({
        queryKey: ['monitoring', days],
        queryFn: () => api.get<MonitoringSummary>(`/monitoring/summary?days=${days}`),
    })
    
    // Normalize backend response for UI compatibility
    const totals = {
        total_tokens: data?.totals?.total_tokens ?? (data as any)?.total_tokens ?? 0,
        total_cost_usd: data?.totals?.total_cost_usd ?? (data as any)?.total_cost_usd ?? 0,
        total_videos: data?.totals?.total_videos ?? 0,
        completed_videos: data?.totals?.completed_videos ?? 0,
        failed_videos: data?.totals?.failed_videos ?? 0,
    }
    const successFractionRaw = data?.metrics?.success_rate ?? (data as any)?.success_rate ?? 0
    const successFraction = successFractionRaw > 1 ? successFractionRaw / 100 : successFractionRaw
    const cacheFractionRaw = data?.metrics?.cache_hit_rate ?? (data as any)?.cache_hit_rate ?? 0
    const cacheFraction = cacheFractionRaw > 1 ? cacheFractionRaw / 100 : cacheFractionRaw
    const avgGenTime = data?.metrics?.avg_generation_time_seconds ?? 0
    const avgCostPerVideo = data?.metrics?.avg_cost_per_video_usd ?? 0

    // Transform for charts (support legacy keys)
    const byType = data?.by_generation_type ?? (data as any)?.by_type
    const typeData = byType ? Object.entries(byType).map(([key, val]: any) => ({
        name: key.toUpperCase(),
        cost: Number(val.cost_usd || 0),
    })) : []
    const byModel = data?.by_model ?? (data as any)?.by_model
    const modelData = byModel ? Object.entries(byModel).map(([key, val]: any) => ({
        name: key,
        cost: Number(val.cost_usd || 0),
        calls: Number(val.calls || val.count || 0),
    })) : []

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold tracking-tight">System Monitoring</h1>
                    <p className="text-muted-foreground">Real-time usage metrics, costs, and system performance.</p>
                </div>
                <div className="w-[180px]">
                    <Select value={days} onValueChange={setDays}>
                        <SelectTrigger>
                            <SelectValue placeholder="Period" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7">Last 7 Days</SelectItem>
                            <SelectItem value="14">Last 14 Days</SelectItem>
                            <SelectItem value="30">Last 30 Days</SelectItem>
                            <SelectItem value="90">Last 90 Days</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-20" /> : (
                            <div className="text-2xl font-bold">${(totals.total_cost_usd ?? 0).toFixed(2)}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            For {totals.total_videos} videos
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-20" /> : (
                            <div className="text-2xl font-bold">{(successFraction * 100).toFixed(1)}%</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            {totals.completed_videos} completed / {totals.failed_videos} failed
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Cost / Video</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-20" /> : (
                            <div className="text-2xl font-bold">${avgCostPerVideo.toFixed(2)}</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            Est. margins +25%
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Gen Time</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-8 w-20" /> : (
                            <div className="text-2xl font-bold">{Math.round(avgGenTime)}s</div>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                            ~{(Number(avgGenTime) / 60).toFixed(1)} mins
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Charts */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">

                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Cost Breakdown</CardTitle>
                        <CardDescription>Spending by generation type (Video, Image, LLM, Research)</CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        {isLoading ? <Skeleton className="h-[350px] w-full" /> : (
                            <ResponsiveContainer width="100%" height={350}>
                                <BarChart data={typeData}>
                                    <XAxis
                                        dataKey="name"
                                        stroke="#888888"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        stroke="#888888"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => `$${value}`}
                                    />
                                    <Tooltip
                                        cursor={{ fill: 'transparent' }}
                                        contentStyle={{ borderRadius: '8px', border: 'none', background: '#18181b', color: '#fff' }}
                                    />
                                    <Bar dataKey="cost" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>

                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Model Usage</CardTitle>
                        <CardDescription>Cost distribution by AI model</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <Skeleton className="h-[350px] w-full" /> : (
                            <div className="space-y-8">
                                {modelData.sort((a, b) => b.cost - a.cost).map((model) => (
                                    <div key={model.name} className="flex items-center">
                                        <div className="space-y-1 flex-1">
                                            <div className="text-sm font-medium leading-none">{model.name}</div>
                                            <div className="text-xs text-muted-foreground">{model.calls} calls</div>
                                        </div>
                                        <div className="text-sm font-bold">${model.cost.toFixed(2)}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

            </div>
        </div>
    )
}
