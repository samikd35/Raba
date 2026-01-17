'use client'

import { motion } from 'framer-motion'
import { Check, Loader2, Circle, Lock, Eye } from 'lucide-react'
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
    activeStepId?: string | null
    onStepClick?: (stepId: string) => void
}

export function PipelineStepper({ steps, activeStepId, onStepClick }: PipelineStepperProps) {
    return (
        <div className="relative flex flex-col gap-6 md:flex-row md:items-start md:justify-between w-full max-w-4xl mx-auto py-6">
            {/* Progress Line Background */}
            <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-muted md:left-4 md:right-4 md:top-[15px] md:h-0.5 md:w-auto md:bottom-auto -z-10" />

            {steps.map((step, index) => {
                const isActive = step.status === 'running' || step.status === 'waiting'
                const isCompleted = step.status === 'completed'
                const isSelected = activeStepId === step.id
                const isClickable = isCompleted && !!onStepClick

                const handleClick = () => {
                    if (isClickable) {
                        onStepClick?.(step.id)
                    }
                }

                return (
                    <div 
                        key={step.id} 
                        className={cn(
                            "group relative flex items-center gap-4 md:flex-col md:gap-3 md:items-center md:text-center md:flex-1 transition-all",
                            isClickable && "cursor-pointer",
                            !isClickable && "cursor-default"
                        )}
                        onClick={handleClick}
                    >
                        {/* Step Icon */}
                        <motion.div
                            initial={false}
                            animate={{
                                scale: isActive ? 1.1 : isSelected ? 1.05 : 1,
                                backgroundColor: isCompleted ? 'var(--color-primary)' : isActive ? 'var(--color-background)' : 'var(--color-muted)',
                                borderColor: isActive ? 'var(--color-primary)' : isSelected ? 'var(--color-primary)' : isCompleted ? 'transparent' : 'transparent',
                            }}
                            className={cn(
                                "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 shadow-sm transition-all",
                                isActive && "border-primary shadow-[0_0_10px_rgba(99,102,241,0.5)]",
                                !isActive && !isCompleted && "bg-muted text-muted-foreground",
                                isCompleted && "bg-primary text-primary-foreground border-transparent",
                                isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                                isClickable && "hover:scale-110 hover:shadow-lg"
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
                            <div className="flex items-center gap-1.5">
                                <span className={cn(
                                    "text-sm font-semibold tracking-tight",
                                    isActive ? "text-primary" : isSelected ? "text-primary" : isCompleted ? "text-foreground" : "text-muted-foreground"
                                )}>
                                    {step.label}
                                </span>
                                {isClickable && (
                                    <Eye className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                )}
                            </div>
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
