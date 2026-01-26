'use client'

import { useParams, useRouter } from 'next/navigation'
import { useState, useEffect, useMemo } from 'react'
import { useWorkflow } from '@/hooks/use-workflow'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { PipelineStepper } from '@/components/pipeline-stepper'
import { StatusBadge } from '@/components/status-badge'
import { ChevronLeft, RefreshCw, Trash2, Download, ExternalLink, Zap, FileText, Image as ImageIcon, Video, Search, Recycle, Users, Play } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { BorderBeam } from '@/components/ui/border-beam'

const categoryDisplayNames: Record<string, string> = {
    realistic: 'Realistic',
    anime: 'Anime',
    animation: 'Animation',
    surreal_realism: 'Realistic',
    high_octane_anime: 'Anime',
    stylized_3d: 'Animation',
    auto: 'Auto',
}

const formatCategory = (category: string | undefined): string => {
    if (!category) return 'Auto'
    return categoryDisplayNames[category] || category.replace('_', ' ')
}

// Helper function to extract image URLs from different data structures
const getImageUrls = (generatedImages: any): string[] => {
    if (!generatedImages) return []
    
    // Direct array of URLs
    if (Array.isArray(generatedImages)) {
        return generatedImages.map((img: any) => {
            if (typeof img === 'string') return img
            if (typeof img === 'object' && img.url) return img.url
            if (typeof img === 'object' && img.image_url) return img.image_url
            return ''
        }).filter(Boolean)
    }
    
    // Object with image_urls array
    if (typeof generatedImages === 'object' && generatedImages.image_urls) {
        return Array.isArray(generatedImages.image_urls) ? generatedImages.image_urls : []
    }
    
    // Object with all_image_urls array
    if (typeof generatedImages === 'object' && generatedImages.all_image_urls) {
        return Array.isArray(generatedImages.all_image_urls) ? generatedImages.all_image_urls : []
    }
    
    // Object with images array (each item may be object with url property)
    if (typeof generatedImages === 'object' && generatedImages.images) {
        const images = generatedImages.images
        if (Array.isArray(images)) {
            return images.map((img: any) => {
                if (typeof img === 'string') return img
                if (typeof img === 'object' && img.url) return img.url
                if (typeof img === 'object' && img.image_url) return img.image_url
                return ''
            }).filter(Boolean)
        }
    }
    
    return []
}

export default function WorkflowDetailPage() {
    const params = useParams()
    const router = useRouter()
    const workflowId = params.id as string
    const { data: workflow, isLoading, error, refetch } = useWorkflow(workflowId)
    const [activeStep, setActiveStep] = useState<string | null>(null)
    const [isContinuing, setIsContinuing] = useState(false)

    // All hooks must be called before any conditional returns
    const imageUrls = useMemo(() => getImageUrls(workflow?.generated_images), [workflow?.generated_images])

    // Calculate pipeline steps
    const steps = useMemo(() => {
        const toolName = workflow?.tool_selection?.selected_tool?.tool_name || workflow?.tool_selection?.tool_name
        
        // Calculate research sources count from various possible structures
        const researchSourcesCount = (() => {
            if (!workflow?.research_output) return 0
            const ro = workflow.research_output
            
            // Check total_sources field first
            if (ro.total_sources) return ro.total_sources
            
            // Extract from research_findings citations
            if (ro.research_findings && Array.isArray(ro.research_findings)) {
                const citationUrls = new Set<string>()
                ro.research_findings.forEach((finding: any) => {
                    if (finding.citations && Array.isArray(finding.citations)) {
                        finding.citations.forEach((citation: any) => {
                            if (citation.url) citationUrls.add(citation.url)
                        })
                    }
                })
                if (citationUrls.size > 0) return citationUrls.size
            }
            
            // Check direct sources array
            if (ro.sources && Array.isArray(ro.sources)) {
                return ro.sources.length
            }
            
            return 0
        })()
        
        return [
        {
            id: 'tool',
            label: 'Strategy',
            status: workflow?.tool_selection ? 'completed' : workflow?.current_hitl_gate === 'tool_selection' ? 'waiting' : workflow?.status === 'running' ? 'running' : 'pending',
            meta: toolName
        },
        {
            id: 'research',
            label: 'Research',
            status: workflow?.research_output ? 'completed' : (workflow?.tool_selection && workflow?.current_hitl_gate === 'research') ? 'waiting' : (workflow?.tool_selection && workflow?.status === 'running') ? 'running' : 'pending',
            meta: workflow?.research_output ? `${researchSourcesCount} sources` : undefined
        },
        {
            id: 'script',
            label: 'Script',
            status: workflow?.script_output ? 'completed' : (workflow?.research_output && workflow?.current_hitl_gate === 'script') ? 'waiting' : (workflow?.research_output && workflow?.status === 'running') ? 'running' : 'pending',
            meta: workflow?.script_output ? `Viral Score: ${workflow.script_output.viral_score}` : undefined
        },
        {
            id: 'character',
            label: 'Character',
            status: workflow?.character_reference_sheet ? 'completed' : (workflow?.script_output && workflow?.current_hitl_gate === 'character_reference') ? 'waiting' : (workflow?.script_output && workflow?.status === 'running') ? 'running' : 'pending',
            meta: workflow?.character_reference_sheet ? `${workflow.character_reference_sheet.reference_images?.length || 0} views` : undefined
        },
        {
            id: 'image',
            label: 'Images',
            status: imageUrls.length > 0 ? 'completed' : (workflow?.character_reference_sheet && workflow?.current_hitl_gate === 'images') ? 'waiting' : ((workflow?.character_reference_sheet || workflow?.script_output) && workflow?.status === 'running') ? 'running' : 'pending',
            meta: imageUrls.length > 0 ? `${imageUrls.length} generated` : undefined
        },
        {
            id: 'video',
            label: 'Video',
            status: workflow?.video_url ? 'completed' : (imageUrls.length > 0 && workflow?.current_hitl_gate === 'video') ? 'waiting' : (imageUrls.length > 0 && workflow?.status === 'running') ? 'running' : 'pending'
        }
    ] as const
    }, [workflow, imageUrls])

    // Determine initial active step - show most recent completed step, or first available
    useEffect(() => {
        if (!workflow || activeStep !== null) return
        
        // Find the last completed step
        const completedSteps = steps.filter(s => s.status === 'completed')
        if (completedSteps.length > 0) {
            setActiveStep(completedSteps[completedSteps.length - 1].id)
        } else {
            // If no completed steps, show the first step that has content or is running
            const firstAvailable = steps.find(s => 
                s.status === 'running' || 
                s.status === 'waiting' ||
                (s.id === 'tool' && workflow.tool_selection) ||
                (s.id === 'research' && workflow.research_output) ||
                (s.id === 'script' && workflow.script_output) ||
                (s.id === 'character' && workflow.character_reference_sheet) ||
                (s.id === 'image' && imageUrls.length > 0) ||
                (s.id === 'video' && workflow.video_url)
            )
            if (firstAvailable) {
                setActiveStep(firstAvailable.id)
            }
        }
    }, [workflow, steps, activeStep, imageUrls])

    const handleDelete = async (purgeMedia: boolean) => {
        const verb = purgeMedia ? 'delete and purge media' : 'delete (keep media)'
        if (!confirm(`Are you sure you want to ${verb}?`)) return
        try {
            await api.delete(`/workflows/${workflowId}?purge_media=${purgeMedia ? 'true' : 'false'}`)
            toast.success(purgeMedia ? 'Workflow deleted and media purged' : 'Workflow deleted (media kept)')
            router.push('/workflows')
        } catch (e: any) {
            toast.error(e?.message || 'Failed to delete workflow')
        }
    }

    const handlePurgeMedia = async () => {
        if (!confirm('Purge all stored media for this workflow?')) return
        try {
            const res = await api.post(`/workflows/${workflowId}/purge-media`, {})
            toast.success('Media purged successfully')
            // Optionally refetch to update any derived state
            refetch()
        } catch (e: any) {
            toast.error(e?.message || 'Failed to purge media')
        }
    }

    const handleContinue = async () => {
        try {
            setIsContinuing(true)
            await api.post(`/workflows/${workflowId}/continue`, {})
            toast.success('Continue started — workflow will resume from the last completed step')
            refetch()
        } catch (e: any) {
            toast.error(e?.message || 'Failed to continue workflow')
        } finally {
            setIsContinuing(false)
        }
    }

    const handleStepClick = (stepId: string) => {
        // Only allow clicking if step has content
        const step = steps.find(s => s.id === stepId)
        if (step && step.status === 'completed') {
            setActiveStep(stepId)
        }
    }

    // Early returns after all hooks
    if (isLoading) {
        return (
            <div className="container py-10 space-y-8">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-md" />
                    <div className="space-y-2">
                        <Skeleton className="h-8 w-64" />
                        <Skeleton className="h-4 w-32" />
                    </div>
                </div>
                <Skeleton className="h-24 w-full" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Skeleton className="h-96 md:col-span-2" />
                    <Skeleton className="h-96" />
                </div>
            </div>
        )
    }

    if (error || !workflow) {
        return (
            <div className="container py-20 text-center">
                <h2 className="text-2xl font-bold text-destructive mb-4">Workflow Not Found</h2>
                <p className="text-muted-foreground mb-8">Could not load workflow {workflowId}</p>
                <Button variant="outline" asChild>
                    <Link href="/workflows">Back to Workflows</Link>
                </Button>
            </div>
        )
    }

    return (
        <div className="container py-8 max-w-6xl space-y-8 mx-auto">
            {/* Header */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-start gap-4">
                    <Button variant="ghost" size="icon" asChild className="mt-1">
                        <Link href="/workflows"><ChevronLeft className="h-5 w-5" /></Link>
                    </Button>
                    <div className="space-y-1">
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold tracking-tight line-clamp-1">{workflow.topic}</h1>
                            <StatusBadge status={workflow.status} />
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{new Date(workflow.created_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <span>{formatCategory(workflow.category)}</span>
                            <span>•</span>
                            <span>{workflow.resolution}</span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {workflow.status === 'failed' && (
                        <Button size="sm" onClick={handleContinue} disabled={isContinuing}>
                            <Play className="h-4 w-4 mr-2" />
                            {isContinuing ? 'Starting…' : 'Continue'}
                        </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Refresh
                    </Button>
                    <Button variant="outline" size="sm" onClick={handlePurgeMedia}>
                        <Recycle className="h-4 w-4 mr-2" />
                        Purge Media
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => handleDelete(false)}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete (keep media)
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(true)}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                    </Button>
                </div>
            </div>

            {/* Pipeline Stepper */}
            <Card>
                <CardContent className="pt-6">
                    <PipelineStepper 
                        steps={steps as any} 
                        activeStepId={activeStep}
                        onStepClick={handleStepClick}
                    />
                </CardContent>
            </Card>

            {/* Step-Based Content View */}
            <div className="space-y-6">
                {activeStep === 'tool' && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Zap className="h-5 w-5 text-primary" />
                                Strategy - Tool Selection
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {workflow.tool_selection ? (
                            <div className="p-4 bg-muted/30 rounded-lg border-l-4 border-primary space-y-4">
                                {/* Selected Tool */}
                                {(workflow.tool_selection.selected_tool || workflow.tool_selection.tool_name) && (
                                    <div>
                                        <span className="text-sm font-semibold text-muted-foreground">Selected Tool:</span>
                                        <p className="text-lg font-bold">
                                            {workflow.tool_selection.selected_tool?.tool_name || workflow.tool_selection.tool_name}
                                        </p>
                                        {workflow.tool_selection.selected_tool?.description && (
                                            <p className="text-sm text-muted-foreground mt-1">
                                                {workflow.tool_selection.selected_tool.description}
                                            </p>
                                        )}
                                    </div>
                                )}
                                
                                {/* Intent Metadata */}
                                {workflow.tool_selection.intent_metadata && (
                                    <div className="pt-2 border-t">
                                        <h4 className="text-sm font-semibold mb-2">Intent Analysis</h4>
                                        <div className="grid grid-cols-2 gap-3 text-sm">
                                            {workflow.tool_selection.intent_metadata.intent_type && (
                                                <div>
                                                    <span className="text-muted-foreground">Type:</span>
                                                    <p className="font-medium capitalize">{workflow.tool_selection.intent_metadata.intent_type}</p>
                                                </div>
                                            )}
                                            {workflow.tool_selection.intent_metadata.tone && (
                                                <div>
                                                    <span className="text-muted-foreground">Tone:</span>
                                                    <p className="font-medium capitalize">{workflow.tool_selection.intent_metadata.tone}</p>
                                                </div>
                                            )}
                                            {workflow.tool_selection.intent_metadata.target_audience && (
                                                <div>
                                                    <span className="text-muted-foreground">Audience:</span>
                                                    <p className="font-medium capitalize">{workflow.tool_selection.intent_metadata.target_audience}</p>
                                                </div>
                                            )}
                                            {workflow.tool_selection.intent_metadata.complexity_score !== undefined && (
                                                <div>
                                                    <span className="text-muted-foreground">Complexity:</span>
                                                    <p className="font-medium">{(workflow.tool_selection.intent_metadata.complexity_score * 100).toFixed(0)}%</p>
                                                </div>
                                            )}
                                        </div>
                                        {workflow.tool_selection.intent_metadata.keywords && workflow.tool_selection.intent_metadata.keywords.length > 0 && (
                                            <div className="mt-2">
                                                <span className="text-muted-foreground text-sm">Keywords: </span>
                                                <span className="text-sm">
                                                    {workflow.tool_selection.intent_metadata.keywords.join(', ')}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                )}
                                
                                {/* Validated Parameters */}
                                {workflow.tool_selection.validated_params && (
                                    <div className="pt-2 border-t">
                                        <h4 className="text-sm font-semibold mb-2">Parameters</h4>
                                        <div className="grid grid-cols-3 gap-3 text-sm">
                                            <div>
                                                <span className="text-muted-foreground">Duration:</span>
                                                <p className="font-medium">{workflow.tool_selection.validated_params.duration_seconds}s</p>
                                            </div>
                                            <div>
                                                <span className="text-muted-foreground">Aspect Ratio:</span>
                                                <p className="font-medium">{workflow.tool_selection.validated_params.aspect_ratio}</p>
                                            </div>
                                            <div>
                                                <span className="text-muted-foreground">Resolution:</span>
                                                <p className="font-medium">{workflow.tool_selection.validated_params.resolution}</p>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                
                                {/* Confidence and Reasoning */}
                                <div className="pt-2 border-t space-y-2">
                                    {workflow.tool_selection.confidence !== undefined && (
                                        <div>
                                            <span className="text-sm font-semibold text-muted-foreground">Confidence:</span>
                                            <p className="text-base">{(workflow.tool_selection.confidence * 100).toFixed(1)}%</p>
                                        </div>
                                    )}
                                    {workflow.tool_selection.selection_reasoning && (
                                        <div>
                                            <span className="text-sm font-semibold text-muted-foreground">Reasoning:</span>
                                            <p className="text-sm text-muted-foreground mt-1">{workflow.tool_selection.selection_reasoning}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                            ) : (
                                <div className="p-8 text-center text-muted-foreground">
                                    <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>Tool selection data is not yet available.</p>
                                    <p className="text-sm mt-2">This step may still be in progress or the workflow may be in auto mode.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {activeStep === 'research' && workflow.research_output && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Search className="h-5 w-5 text-primary" />
                                Research
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="p-4 bg-muted/30 rounded-lg space-y-4">
                                {/* Executive Summary */}
                                {workflow.research_output.executive_summary && (
                                    <div className="pb-4 border-b">
                                        <h4 className="text-sm font-semibold mb-2">Executive Summary</h4>
                                        <p className="text-sm text-foreground">{workflow.research_output.executive_summary}</p>
                                    </div>
                                )}
                                
                                {/* Extract sources from research_findings citations or direct sources array */}
                                {(() => {
                                    const sources: any[] = []
                                    
                                    // Extract from research_findings citations
                                    if (workflow.research_output.research_findings && Array.isArray(workflow.research_output.research_findings)) {
                                        workflow.research_output.research_findings.forEach((finding: any) => {
                                            if (finding.citations && Array.isArray(finding.citations)) {
                                                finding.citations.forEach((citation: any) => {
                                                    if (citation.url && !sources.find(s => s.url === citation.url)) {
                                                        sources.push({
                                                            source: citation.source || 'Unknown',
                                                            url: citation.url,
                                                            quote: citation.quote
                                                        })
                                                    }
                                                })
                                            }
                                        })
                                    }
                                    
                                    // Also check direct sources array if available
                                    if (workflow.research_output.sources && Array.isArray(workflow.research_output.sources)) {
                                        workflow.research_output.sources.forEach((s: any) => {
                                            if (typeof s === 'string') {
                                                if (!sources.find(src => src.url === s)) {
                                                    sources.push({ source: s, url: s })
                                                }
                                            } else if (s.url && !sources.find(src => src.url === s.url)) {
                                                sources.push(s)
                                            }
                                        })
                                    }
                                    
                                    // Also check total_sources count
                                    const totalSources = workflow.research_output.total_sources || sources.length
                                    
                                    return (
                                        <div className="pb-4 border-b">
                                            <div className="mb-3">
                                                <span className="text-sm font-semibold">
                                                    {totalSources} Source{totalSources !== 1 ? 's' : ''} Used
                                                </span>
                                            </div>
                                            {sources.length > 0 && (
                                                <div className="space-y-2 max-h-60 overflow-y-auto">
                                                    {sources.map((s: any, i: number) => {
                                                        const sourceTitle = s.source || s.title || s.url || `Source ${i + 1}`
                                                        const sourceUrl = s.url
                                                        return (
                                                            <div key={i} className="p-2 bg-background rounded border text-sm">
                                                                <div className="flex items-start gap-2">
                                                                    <span className="text-xs text-muted-foreground font-mono">{i + 1}.</span>
                                                                    <div className="flex-1">
                                                                        {sourceUrl ? (
                                                                            <a 
                                                                                href={sourceUrl} 
                                                                                target="_blank" 
                                                                                rel="noopener noreferrer"
                                                                                className="font-medium hover:text-primary transition-colors flex items-center gap-1"
                                                                            >
                                                                                {sourceTitle}
                                                                                <ExternalLink className="h-3 w-3" />
                                                                            </a>
                                                                        ) : (
                                                                            <p className="font-medium">{sourceTitle}</p>
                                                                        )}
                                                                        {s.quote && (
                                                                            <p className="text-xs text-muted-foreground mt-1 italic">"{s.quote}"</p>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    )
                                })()}
                                
                                {/* Research Findings */}
                                {workflow.research_output.research_findings && workflow.research_output.research_findings.length > 0 && (
                                    <div className="pb-4 border-b">
                                        <h4 className="text-sm font-semibold mb-3">Key Findings</h4>
                                        <div className="space-y-4">
                                            {workflow.research_output.research_findings.map((finding: any, i: number) => {
                                                if (typeof finding === 'string') {
                                                    return (
                                                        <div key={i} className="text-sm text-foreground">
                                                            {finding}
                                                        </div>
                                                    )
                                                }
                                                return (
                                                    <div key={i} className="p-3 bg-background rounded border">
                                                        {finding.topic_segment && (
                                                            <h5 className="text-sm font-semibold mb-2">{finding.topic_segment}</h5>
                                                        )}
                                                        {finding.key_facts && finding.key_facts.length > 0 && (
                                                            <ul className="list-disc list-inside space-y-1 text-sm text-foreground ml-2">
                                                                {finding.key_facts.map((fact: string, factIdx: number) => (
                                                                    <li key={factIdx}>{fact}</li>
                                                                ))}
                                                            </ul>
                                                        )}
                                                        {finding.confidence !== undefined && (
                                                            <p className="text-xs text-muted-foreground mt-2">
                                                                Confidence: {(finding.confidence * 100).toFixed(0)}%
                                                            </p>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                                
                                {/* Visual Elements */}
                                {workflow.research_output.visual_elements && workflow.research_output.visual_elements.length > 0 && (
                                    <div className="pb-4 border-b">
                                        <h4 className="text-sm font-semibold mb-2">Visual Elements</h4>
                                        <div className="flex flex-wrap gap-2">
                                            {workflow.research_output.visual_elements.map((element: string, i: number) => (
                                                <span key={i} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                                    {element}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {/* Interesting Angles */}
                                {workflow.research_output.interesting_angles && workflow.research_output.interesting_angles.length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-semibold mb-2">Interesting Angles</h4>
                                        <ul className="list-disc list-inside space-y-1 text-sm text-foreground ml-2">
                                            {workflow.research_output.interesting_angles.map((angle: string, i: number) => (
                                                <li key={i}>{angle}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {activeStep === 'script' && workflow.script_output && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <FileText className="h-5 w-5 text-primary" />
                                Script
                                <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                    Viral Score: {workflow.script_output.viral_score?.toFixed(4) || 'N/A'}
                                </span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4 max-h-[600px] overflow-y-auto font-mono text-sm leading-relaxed">
                            {/* Hook Section */}
                            {workflow.script_output.hook && (
                                <div className="p-4 bg-muted/30 rounded-lg border-l-4 border-primary">
                                    <p className="font-semibold text-primary mb-2">Hook</p>
                                    <p className="mb-2">{workflow.script_output.hook.script || workflow.script_output.hook}</p>
                                    {workflow.script_output.hook.visual_direction && (
                                        <p className="text-xs text-muted-foreground italic mt-2">
                                            Visual: {workflow.script_output.hook.visual_direction}
                                        </p>
                                    )}
                                    {workflow.script_output.hook.duration_seconds && (
                                        <p className="text-xs text-muted-foreground mt-1">
                                            Duration: {workflow.script_output.hook.duration_seconds}s
                                        </p>
                                    )}
                                </div>
                            )}
                            
                            {/* Scenes */}
                            {workflow.script_output.scenes && workflow.script_output.scenes.length > 0 && (
                                <div className="space-y-4">
                                    <h4 className="text-sm font-semibold text-foreground">Scenes</h4>
                                    {workflow.script_output.scenes.map((scene: any, i: number) => (
                                        <div key={i} className="pl-4 border-l-2 border-border">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                                                    Scene {scene.scene_number || i + 1}
                                                </span>
                                                {scene.timestamp_start !== undefined && scene.timestamp_end !== undefined && (
                                                    <span className="text-xs text-muted-foreground">
                                                        ({scene.timestamp_start.toFixed(1)}s - {scene.timestamp_end.toFixed(1)}s)
                                                    </span>
                                                )}
                                            </div>
                                            <p className="mb-2">{scene.description}</p>
                                            {scene.dialogue && (
                                                <p className="text-xs text-muted-foreground italic mb-1">
                                                    Dialogue: "{scene.dialogue}"
                                                </p>
                                            )}
                                            {scene.camera_direction && (
                                                <p className="text-xs text-muted-foreground">
                                                    Camera: {scene.camera_direction}
                                                </p>
                                            )}
                                            {scene.visual_keywords && scene.visual_keywords.length > 0 && (
                                                <div className="flex flex-wrap gap-1 mt-2">
                                                    {scene.visual_keywords.map((keyword: string, kwIdx: number) => (
                                                        <span key={kwIdx} className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                                                            {keyword}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            {/* Call to Action */}
                            {workflow.script_output.call_to_action && (
                                <div className="p-4 bg-muted/30 rounded-lg border-l-4 border-primary mt-4">
                                    <p className="font-semibold text-primary mb-2">Call to Action</p>
                                    {workflow.script_output.call_to_action.script && (
                                        <p className="mb-2">{workflow.script_output.call_to_action.script}</p>
                                    )}
                                    {workflow.script_output.call_to_action.visual_direction && (
                                        <p className="text-xs text-muted-foreground italic mt-2">
                                            Visual: {workflow.script_output.call_to_action.visual_direction}
                                        </p>
                                    )}
                                    {workflow.script_output.call_to_action.type && (
                                        <p className="text-xs text-muted-foreground mt-1 capitalize">
                                            Type: {workflow.script_output.call_to_action.type}
                                        </p>
                                    )}
                                    {workflow.script_output.call_to_action.placement_seconds !== undefined && (
                                        <p className="text-xs text-muted-foreground mt-1">
                                            Placement: {workflow.script_output.call_to_action.placement_seconds}s
                                        </p>
                                    )}
                                </div>
                            )}
                            
                            {/* Viral Metrics */}
                            {workflow.script_output.viral_metrics && (
                                <div className="pt-4 border-t">
                                    <h4 className="text-sm font-semibold mb-2">Viral Metrics Breakdown</h4>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        {workflow.script_output.viral_metrics.hook_strength !== undefined && (
                                            <div>
                                                <span className="text-muted-foreground">Hook Strength:</span>
                                                <span className="ml-2 font-medium">{(workflow.script_output.viral_metrics.hook_strength * 100).toFixed(0)}%</span>
                                            </div>
                                        )}
                                        {workflow.script_output.viral_metrics.pattern_interrupt_density !== undefined && (
                                            <div>
                                                <span className="text-muted-foreground">Pattern Interrupts:</span>
                                                <span className="ml-2 font-medium">{(workflow.script_output.viral_metrics.pattern_interrupt_density * 100).toFixed(0)}%</span>
                                            </div>
                                        )}
                                        {workflow.script_output.viral_metrics.emotional_arc !== undefined && (
                                            <div>
                                                <span className="text-muted-foreground">Emotional Arc:</span>
                                                <span className="ml-2 font-medium">{(workflow.script_output.viral_metrics.emotional_arc * 100).toFixed(0)}%</span>
                                            </div>
                                        )}
                                        {workflow.script_output.viral_metrics.call_to_action_clarity !== undefined && (
                                            <div>
                                                <span className="text-muted-foreground">CTA Clarity:</span>
                                                <span className="ml-2 font-medium">{(workflow.script_output.viral_metrics.call_to_action_clarity * 100).toFixed(0)}%</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                            
                            {/* Total Duration */}
                            {workflow.script_output.total_duration_seconds && (
                                <div className="pt-2 border-t text-xs text-muted-foreground">
                                    Total Duration: {workflow.script_output.total_duration_seconds.toFixed(1)}s
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {activeStep === 'character' && workflow.character_reference_sheet && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Users className="h-5 w-5 text-primary" />
                                Character Reference Sheet
                                {workflow.character_reference_sheet.character_name && (
                                    <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                        {workflow.character_reference_sheet.character_name}
                                    </span>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {workflow.character_reference_sheet.reference_images && workflow.character_reference_sheet.reference_images.length > 0 ? (
                                <div className="space-y-4">
                                    {workflow.character_reference_sheet.character_description && (
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            <p className="text-sm text-foreground">
                                                {workflow.character_reference_sheet.character_description}
                                            </p>
                                        </div>
                                    )}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                        {workflow.character_reference_sheet.reference_images.map((ref: any, i: number) => (
                                            <div key={i} className="space-y-2">
                                                <div className="aspect-square relative rounded-lg overflow-hidden border bg-muted group">
                                                    <img 
                                                        src={ref.url} 
                                                        alt={`${ref.view} view`} 
                                                        className="object-cover w-full h-full transition-transform group-hover:scale-105"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23ccc" width="400" height="400"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="18" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EImage not available%3C/text%3E%3C/svg%3E'
                                                        }}
                                                    />
                                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                                        <a href={ref.url} target="_blank" rel="noopener noreferrer" className="p-2 bg-background/80 rounded-full hover:bg-background">
                                                            <ExternalLink className="h-4 w-4" />
                                                        </a>
                                                    </div>
                                                </div>
                                                <p className="text-xs text-center text-muted-foreground capitalize font-medium">
                                                    {ref.view} view
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="p-8 text-center text-muted-foreground">
                                    <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No character reference images available.</p>
                                    <p className="text-sm mt-2">Character reference images will appear here once generated.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {activeStep === 'image' && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <ImageIcon className="h-5 w-5 text-primary" />
                                Generated Images
                                {imageUrls.length > 0 && (
                                    <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                        {imageUrls.length} images
                                    </span>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {imageUrls.length > 0 ? (
                                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                                    {imageUrls.map((url, i) => (
                                        <div key={i} className="aspect-square relative rounded-lg overflow-hidden border bg-muted group">
                                            <img 
                                                src={url} 
                                                alt={`Scene ${i + 1}`} 
                                                className="object-cover w-full h-full transition-transform group-hover:scale-105"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23ccc" width="400" height="400"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="18" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EImage not available%3C/text%3E%3C/svg%3E'
                                                }}
                                            />
                                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                                <a href={url} target="_blank" rel="noopener noreferrer" className="p-2 bg-background/80 rounded-full hover:bg-background">
                                                    <ExternalLink className="h-4 w-4" />
                                                </a>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-8 text-center text-muted-foreground">
                                    <ImageIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No images have been generated yet.</p>
                                    <p className="text-sm mt-2">Images will appear here once the image generation step completes.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {activeStep === 'video' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <Card className="overflow-hidden relative bg-black/5 border-muted-foreground/10">
                                {workflow.video_url ? (
                                    <div className="relative bg-black flex items-center justify-center">
                                        <div className="w-full max-w-md mx-auto aspect-[9/16] relative">
                                            <BorderBeam size={200} duration={8} borderWidth={2} colorFrom="#BEF264" colorTo="#6366F1" />
                                            <video
                                                src={workflow.video_url}
                                                controls
                                                className="w-full h-full object-contain"
                                                poster={imageUrls[0]}
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="aspect-[9/16] max-w-md mx-auto flex flex-col items-center justify-center text-center p-6 bg-muted/10 border-2 border-dashed border-muted-foreground/20 m-4 rounded-xl">
                                        {workflow.status === 'failed' ? (
                                            <div className="text-destructive space-y-2">
                                                <Trash2 className="h-8 w-8 mx-auto" />
                                                <p className="font-semibold">Generation Failed</p>
                                            </div>
                                        ) : (
                                            <div className="text-muted-foreground space-y-4 animate-pulse">
                                                <div className="h-12 w-12 rounded-full bg-muted mx-auto" />
                                                <p className="text-sm">Video generating...</p>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {workflow.video_url && (
                                    <div className="p-4 flex gap-2">
                                        <Button className="w-full" asChild>
                                            <a href={workflow.video_url} download>
                                                <Download className="h-4 w-4 mr-2" /> Download
                                            </a>
                                        </Button>
                                    </div>
                                )}
                            </Card>
                        </div>
                        <div className="space-y-6">
                            {workflow.video_url && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <Video className="h-4 w-4 text-primary" />
                                            Video Details
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="text-sm space-y-2">
                                        <div>
                                            <span className="font-semibold">Resolution:</span> {workflow.resolution}
                                        </div>
                                        <div>
                                            <span className="font-semibold">Duration:</span> {workflow.duration_seconds}s
                                        </div>
                                        <div>
                                            <span className="font-semibold">Aspect Ratio:</span> {workflow.aspect_ratio}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </div>
                )}

                {/* Default view when no step is selected or step has no content */}
                {(!activeStep || 
                  (activeStep === 'tool' && !workflow.tool_selection) ||
                  (activeStep === 'research' && !workflow.research_output) ||
                  (activeStep === 'script' && !workflow.script_output) ||
                  (activeStep === 'character' && !workflow.character_reference_sheet) ||
                  (activeStep === 'image' && imageUrls.length === 0) ||
                  (activeStep === 'video' && !workflow.video_url)) && (
                    <Card>
                        <CardContent className="py-12 text-center">
                            <p className="text-muted-foreground">
                                {!activeStep 
                                    ? 'Select a step to view its content'
                                    : 'Content for this step is not yet available'}
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
