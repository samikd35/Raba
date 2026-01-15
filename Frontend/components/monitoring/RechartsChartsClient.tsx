"use client"
import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type ByType = Record<string, { cost_usd: number; tokens?: number; count?: number }>
type ByModel = Record<string, { cost_usd: number; tokens?: number; calls?: number }>

export function RechartsChartsClient({ byType, byModel }: { byType: ByType; byModel: ByModel }) {
  const typeData = useMemo(() => Object.entries(byType || {}).map(([k, v]) => ({ name: k, Cost: +(v.cost_usd ?? 0) })), [byType])
  const modelData = useMemo(() => Object.entries(byModel || {}).map(([k, v]) => ({ name: k, Cost: +(v.cost_usd ?? 0) })), [byModel])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="card-surface p-3 rounded-xl">
        <h3 className="font-semibold mb-2">Cost by Type</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={typeData} margin={{ top: 10, right: 16, left: 0, bottom: 16 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'Cost']} />
              <Bar dataKey="Cost" fill="#6366F1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card-surface p-3 rounded-xl">
        <h3 className="font-semibold mb-2">Cost by Model</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={modelData} margin={{ top: 10, right: 16, left: 0, bottom: 16 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} height={60} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'Cost']} />
              <Bar dataKey="Cost" fill="#06B6D4" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

