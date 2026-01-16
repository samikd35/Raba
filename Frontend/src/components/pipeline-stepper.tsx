'use client'

import { motion } from 'framer-motion'
import { Check, Loader2, Circle, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Step {
    id: string
    label: string
    status: 'pending' | 'running' | 'completed' | 'waiting'
    meta?: string
}

interface PipelineStepperProps {
    steps: Step[]
    currentStepId?: string
}

export function PipelineStepper({ steps }: PipelineStepperProps) {
    return (
        <div className="relative flex flex-col gap-6 md:flex-row md:items-start md:justify-between w-full max-w-4xl mx-auto py-6">
            {/* Progress Line Background */}
            <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-muted md:left-4 md:right-4 md:top-[15px] md:h-0.5 md:w-auto md:bottom-auto -z-10" />

            {steps.map((step, index) => {
                const isActive = step.status === 'running' || step.status === 'waiting'
                const isCompleted = step.status === 'completed'

                return (
                    <div key={step.id} className="group relative flex items-center gap-4 md:flex-col md:gap-3 md:items-center md:text-center md:flex-1">

                        {/* Step Icon */}
                        <motion.div
                            initial={false}
                            animate={{
                                scale: isActive ? 1.1 : 1,
                                backgroundColor: isCompleted ? 'var(--color-primary)' : isActive ? 'var(--color-background)' : 'var(--color-muted)',
                                borderColor: isActive ? 'var(--color-primary)' : isCompleted ? 'transparent' : 'transparent',
                            }}
                            className={cn(
                                "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 shadow-sm transition-colors",
                                isActive && "border-primary shadow-[0_0_10px_rgba(99,102,241,0.5)]",
                                !isActive && !isCompleted && "bg-muted text-muted-foreground",
                                isCompleted && "bg-primary text-primary-foreground border-transparent"
                            )}
                        >
                            {step.status === 'running' ? (
                                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                            ) : step.status === 'waiting' ? (
                                <Lock className="h-4 w-4 text-orange-500" />
                            ) : isCompleted ? (
                                <Check className="h-4 w-4" />
                            ) : (
                                <span className="text-xs font-medium">{index + 1}</span>
                            )}
                        </motion.div>

                        {/* Step Text */}
                        <div className="flex flex-col md:items-center">
                            <span className={cn(
                                "text-sm font-semibold tracking-tight",
                                isActive ? "text-primary" : isCompleted ? "text-foreground" : "text-muted-foreground"
                            )}>
                                {step.label}
                            </span>
                            {step.meta && (
                                <span className="text-xs text-muted-foreground hidden md:inline-block mt-1">
                                    {step.meta}
                                </span>
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
