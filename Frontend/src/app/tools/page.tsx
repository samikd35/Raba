'use client'

import { useMemo, useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Zap, Star, Plus, Filter, Loader2, Trash2, FileText, Settings, Play, Sparkles, Video } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'

// Tool list summary shape
interface Tool {
  tool_id: string
  tool_name: string
  category: string
  description: string
  version: number
  usage_count: number
  success_rate: number
  is_active: boolean
  priority?: number
}

// Tool detail shape (subset from docs)
interface ToolDetail extends Tool {
  capabilities?: Record<string, any>
  script_prompt_template?: string
  image_prompt_template?: string
  video_prompt_template?: string
  parameters_schema?: any
  original_idea?: string
  source_video_url?: string
  improvement_history?: Array<{ timestamp: string; previous_version: number; suggestion: string; changes_made?: string }>
}

interface ToolsListResponse { tools: Tool[]; total: number; limit?: number; offset?: number }

interface ToolVideoAnalysis {
  script_style: string
  visual_style: string
  camera_grammar: string
  editing_pacing: string
  audio_profile: string
  text_overlay_style: string
  key_motifs: string[]
  negative_constraints: string[]
  tool_idea: string
  suggested_tool_name?: string
}

interface ToolVideoPreviewResponse {
  draft_id: string
  source_video_url: string
  analysis: ToolVideoAnalysis
  preview: {
    tool_id: string
    tool_name: string
    category: string
    description: string
    reasoning?: string
  }
}

export default function ToolsPage() {
  const qc = useQueryClient()

  // Filters and search
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [activeOnly, setActiveOnly] = useState<boolean>(true)
  const [search, setSearch] = useState<string>('')

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['tools', { categoryFilter, activeOnly }],
    queryFn: () => api.get<ToolsListResponse>(`/tools?is_active=${activeOnly}&limit=50&offset=0${categoryFilter !== 'all' ? `&category=${categoryFilter}` : ''}`),
  })

  const filtered = useMemo(() => {
    const list = data?.tools || []
    if (!search) return list
    const q = search.toLowerCase()
    return list.filter(t => t.tool_name.toLowerCase().includes(q) || t.tool_id.toLowerCase().includes(q))
  }, [data, search])

  // Create tool dialog state
  const [openCreate, setOpenCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newIdea, setNewIdea] = useState('')
  const [newCategory, setNewCategory] = useState<string>('auto_detect')
  const [preview, setPreview] = useState<any | null>(null)
  const [creating, setCreating] = useState(false)
  const [previewing, setPreviewing] = useState(false)

  // Video-based tool creation state
  const [openVideoCreate, setOpenVideoCreate] = useState(false)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoToolName, setVideoToolName] = useState('')
  const [videoCategory, setVideoCategory] = useState<string>('auto')
  const [videoNotes, setVideoNotes] = useState('')
  const [videoPreview, setVideoPreview] = useState<ToolVideoPreviewResponse | null>(null)
  const [videoPreviewing, setVideoPreviewing] = useState(false)
  const [videoCreating, setVideoCreating] = useState(false)

  const resetVideoState = () => {
    setVideoFile(null)
    setVideoToolName('')
    setVideoCategory('auto')
    setVideoNotes('')
    setVideoPreview(null)
    setVideoPreviewing(false)
    setVideoCreating(false)
  }

  const handlePreview = async () => {
    if (!newName || !newIdea) {
      toast.error('Please provide tool name and idea')
      return
    }
    setPreviewing(true)
    try {
      const body: any = { tool_name: newName, idea: newIdea }
      if (newCategory !== 'auto_detect') body.category = newCategory
      const res = await api.post<any>('/tools/preview', body)
      setPreview(res)
      toast.success('Preview generated')
    } catch (e: any) {
      toast.error('Preview failed', { description: e.message })
    } finally {
      setPreviewing(false)
    }
  }

  const handleCreate = async () => {
    if (!newName || !newIdea) {
      toast.error('Please provide tool name and idea')
      return
    }
    setCreating(true)
    try {
      const body: any = { tool_name: newName, idea: newIdea }
      if (newCategory !== 'auto_detect') body.category = newCategory
      const res = await api.post<ToolDetail>('/tools', body)
      toast.success('Tool created', { description: res.tool_name })
      setOpenCreate(false)
      setNewName(''); setNewIdea(''); setNewCategory(''); setPreview(null)
      await qc.invalidateQueries({ queryKey: ['tools'] })
    } catch (e: any) {
      toast.error('Create failed', { description: e.message })
    } finally {
      setCreating(false)
    }
  }

  const handleVideoPreview = async () => {
    if (!videoFile) {
      toast.error('Please select a reference video')
      return
    }
    setVideoPreviewing(true)
    try {
      const form = new FormData()
      form.append('reference_video', videoFile)
      if (videoToolName) form.append('tool_name', videoToolName)
      if (videoCategory !== 'auto') form.append('category', videoCategory)
      if (videoNotes) form.append('notes', videoNotes)
      const res = await api.postMultipart<ToolVideoPreviewResponse>('/tools/from-video/preview', form)
      setVideoPreview(res)
      toast.success('Video analysis complete')
    } catch (e: any) {
      toast.error('Video preview failed', { description: e.message })
    } finally {
      setVideoPreviewing(false)
    }
  }

  const handleVideoCreate = async () => {
    if (!videoPreview) {
      toast.error('Preview the video first')
      return
    }
    setVideoCreating(true)
    try {
      const body: any = { draft_id: videoPreview.draft_id }
      if (videoToolName) body.tool_name = videoToolName
      if (videoCategory !== 'auto') body.category = videoCategory
      if (videoNotes) body.notes = videoNotes
      const res = await api.post<ToolDetail>('/tools/from-video', body)
      toast.success('Tool created', { description: res.tool_name })
      setOpenVideoCreate(false)
      resetVideoState()
      await qc.invalidateQueries({ queryKey: ['tools'] })
      setSelectedId(res.tool_id)
    } catch (e: any) {
      toast.error('Create failed', { description: e.message })
    } finally {
      setVideoCreating(false)
    }
  }

  // Selected tool detail dialog
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: detail, isFetching: fetchingDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['tool-detail', selectedId],
    queryFn: () => api.get<ToolDetail>(`/tools/${selectedId}`),
    enabled: !!selectedId,
  })
  const [editState, setEditState] = useState<ToolDetail | null>(null)

  const onOpenDetail = (id: string) => { setSelectedId(id) }
  const onCloseDetail = () => { setSelectedId(null); setEditState(null) }

  // Initialize from query params (?tool=tool_id&category=realistic)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const cat = params.get('category')
    const tool = params.get('tool')
    if (cat) setCategoryFilter(cat)
    if (tool) setSelectedId(tool)
  }, [])

  // Load detail into edit state once fetched
  useEffect(() => {
    if (!fetchingDetail && detail && !editState) {
      setEditState({ ...detail })
    }
  }, [fetchingDetail, detail, editState])

  const saveEdits = async () => {
    if (!editState) return
    try {
      // Prepare payload (send editable fields only)
      const payload: any = {
        tool_name: editState.tool_name,
        description: editState.description,
        is_active: editState.is_active,
        priority: editState.priority ?? 0,
        script_prompt_template: editState.script_prompt_template,
        image_prompt_template: editState.image_prompt_template,
        video_prompt_template: editState.video_prompt_template,
      }
      // Optional capabilities/idea
      if (typeof (editState as any).idea === 'string' && (editState as any).idea.length > 0) {
        payload.idea = (editState as any).idea
      }
      if (editState.capabilities) payload.capabilities = editState.capabilities

      await api.put<ToolDetail>(`/tools/${editState.tool_id}`, payload)
      toast.success('Tool updated')
      await Promise.all([
        refetchDetail(),
        qc.invalidateQueries({ queryKey: ['tools'] }),
      ])
    } catch (e: any) {
      toast.error('Update failed', { description: e.message })
    }
  }

  const [improveText, setImproveText] = useState('')
  const [preserveTemplates, setPreserveTemplates] = useState(false)
  const improveTool = async () => {
    if (!selectedId) return
    if (!improveText || improveText.length < 10) {
      toast.error('Please enter an improvement suggestion (min 10 chars)')
      return
    }
    try {
      const res = await api.post<ToolDetail>(`/tools/${selectedId}/improve`, {
        improvement_suggestion: improveText,
        preserve_templates: preserveTemplates,
      })
      toast.success('Tool improved', { description: `v${res.version}` })
      setImproveText('')
      await Promise.all([
        refetchDetail(),
        qc.invalidateQueries({ queryKey: ['tools'] }),
      ])
    } catch (e: any) {
      toast.error('Improve failed', { description: e.message })
    }
  }

  const [execTopic, setExecTopic] = useState('')
  const [execParams, setExecParams] = useState<string>('')
  const [execResult, setExecResult] = useState<any | null>(null)
  const executeTool = async () => {
    if (!selectedId) return
    if (!execTopic || execTopic.length < 3) {
      toast.error('Please enter a topic (min 3 chars)')
      return
    }
    let params: any | undefined
    if (execParams.trim()) {
      try { params = JSON.parse(execParams) } catch {
        toast.error('Parameters must be valid JSON')
        return
      }
    }
    try {
      const res = await api.post<any>(`/tools/${selectedId}/execute`, { topic: execTopic, parameters: params })
      setExecResult(res)
      toast.success('Execution complete')
    } catch (e: any) {
      toast.error('Execute failed', { description: e.message })
    }
  }

  const deleteTool = async () => {
    if (!selectedId) return
    if (!confirm('Disable this tool? This is a soft delete.')) return
    try {
      await api.delete<any>(`/tools/${selectedId}`)
      toast.success('Tool disabled')
      onCloseDetail()
      await qc.invalidateQueries({ queryKey: ['tools'] })
    } catch (e: any) {
      toast.error('Delete failed', { description: e.message })
    }
  }

  return (
    <div className="container py-8 max-w-6xl mx-auto">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">Creative Tools</h1>
          <p className="text-muted-foreground">Manage, improve, and test video generation tools.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setOpenVideoCreate(true)}>
            <Video className="h-4 w-4 mr-2" /> From Video
          </Button>
          <Button onClick={() => setOpenCreate(true)}>
            <Plus className="h-4 w-4 mr-2" /> New Tool
          </Button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              <SelectItem value="realistic">Realistic</SelectItem>
              <SelectItem value="anime">Anime</SelectItem>
              <SelectItem value="animation">Animation</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-3">
          <Switch checked={activeOnly} onCheckedChange={setActiveOnly} />
          <span className="text-sm">Show active only</span>
        </div>
        <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or id" />
      </div>

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-40" />)}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tool) => (
            <Card key={tool.tool_id} className="relative overflow-hidden hover:border-primary/50 transition-colors cursor-pointer" onClick={() => onOpenDetail(tool.tool_id)}>
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

      {/* Create Tool Dialog */}
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">Create New Tool</DialogTitle>
            <DialogDescription className="text-base">Describe your idea; preview AI enhancement, then create.</DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Tool Name</Label>
                <Input 
                  value={newName} 
                  onChange={e => setNewName(e.target.value)} 
                  placeholder="e.g., Neon Cyberpunk Streets" 
                  className="h-11"
                />
                <p className="text-xs text-muted-foreground">Choose a descriptive name for your tool</p>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Category (optional)</Label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger className="h-11">
                    <SelectValue placeholder="Auto-detect" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto_detect">Auto-detect</SelectItem>
                    <SelectItem value="realistic">Realistic</SelectItem>
                    <SelectItem value="anime">Anime</SelectItem>
                    <SelectItem value="animation">Animation</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">Let AI detect or choose manually</p>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-semibold">Idea</Label>
              <Textarea 
                value={newIdea} 
                onChange={e => setNewIdea(e.target.value)} 
                rows={8} 
                placeholder="Describe what this tool should do, its style, visual direction, and any specific requirements..." 
                className="resize-none"
              />
              <p className="text-xs text-muted-foreground">Be as detailed as possible for better AI enhancement</p>
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button 
                variant="outline" 
                onClick={handlePreview} 
                disabled={previewing || !newName || !newIdea}
                className="min-w-[160px]"
              >
                {previewing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Previewing...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Preview Enhancement
                  </>
                )}
              </Button>
              <Button 
                onClick={handleCreate} 
                disabled={creating || !newName || !newIdea}
                className="min-w-[140px]"
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Tool
                  </>
                )}
              </Button>
            </div>
            {preview && (
              <div className="rounded-lg border-2 border-primary/20 bg-muted/50 p-5 space-y-3 mt-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary" className="capitalize text-sm px-3 py-1">
                      {preview.category?.replace('_', ' ') || 'Uncategorized'}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">{preview.tool_id}</span>
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-lg mb-1">{preview.tool_name}</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{preview.description}</p>
                </div>
                {preview.reasoning && (
                  <div className="rounded-md bg-background/50 p-3 border">
                    <div className="text-xs font-medium mb-1 text-muted-foreground">AI Reasoning:</div>
                    <div className="text-sm text-foreground">{preview.reasoning}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Tool From Video Dialog */}
      <Dialog open={openVideoCreate} onOpenChange={(open) => { setOpenVideoCreate(open); if (!open) resetVideoState() }}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">Create Tool From Video</DialogTitle>
            <DialogDescription className="text-base">Upload a short video, preview analysis, then create a tool.</DialogDescription>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label className="text-sm font-semibold">Reference Video</Label>
              <Input
                type="file"
                accept="video/mp4,video/quicktime,video/webm"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null
                  setVideoFile(file)
                  setVideoPreview(null)
                }}
              />
              <p className="text-xs text-muted-foreground">Accepted: mp4, mov, webm. Max 50MB.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Tool Name (optional)</Label>
                <Input
                  value={videoToolName}
                  onChange={e => { setVideoToolName(e.target.value); setVideoPreview(null) }}
                  placeholder="e.g., Cinematic Macro Explainers"
                  className="h-11"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Category (optional)</Label>
                <Select value={videoCategory} onValueChange={(value) => { setVideoCategory(value); setVideoPreview(null) }}>
                  <SelectTrigger className="h-11">
                    <SelectValue placeholder="Auto-detect" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto-detect</SelectItem>
                    <SelectItem value="realistic">Realistic</SelectItem>
                    <SelectItem value="anime">Anime</SelectItem>
                    <SelectItem value="animation">Animation</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-semibold">Notes (optional)</Label>
              <Textarea
                value={videoNotes}
                onChange={e => { setVideoNotes(e.target.value); setVideoPreview(null) }}
                rows={4}
                placeholder="Constraints or adjustments (e.g., no on-screen text, faster pacing)"
                className="resize-none"
              />
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="outline"
                onClick={handleVideoPreview}
                disabled={videoPreviewing || !videoFile}
                className="min-w-[180px]"
              >
                {videoPreviewing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Preview Analysis
                  </>
                )}
              </Button>
              <Button
                onClick={handleVideoCreate}
                disabled={videoCreating || !videoPreview}
                className="min-w-[160px]"
              >
                {videoCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Tool
                  </>
                )}
              </Button>
            </div>

            {videoPreview && (
              <div className="space-y-6 border-t pt-6">
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Reference Video</Label>
                  <video src={videoPreview.source_video_url} controls className="w-full rounded border" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Script Style</div>
                    <div className="text-sm">{videoPreview.analysis.script_style}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Visual Style</div>
                    <div className="text-sm">{videoPreview.analysis.visual_style}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Camera Grammar</div>
                    <div className="text-sm">{videoPreview.analysis.camera_grammar}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Editing & Pacing</div>
                    <div className="text-sm">{videoPreview.analysis.editing_pacing}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Audio Profile</div>
                    <div className="text-sm">{videoPreview.analysis.audio_profile}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Text Overlay</div>
                    <div className="text-sm">{videoPreview.analysis.text_overlay_style}</div>
                  </div>
                </div>
                {(videoPreview.analysis.key_motifs?.length ?? 0) > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">Key Motifs</div>
                    <div className="flex flex-wrap gap-2">
                      {videoPreview.analysis.key_motifs.map((m, i) => (
                        <Badge key={i} variant="secondary">{m}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                {(videoPreview.analysis.negative_constraints?.length ?? 0) > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">Negative Constraints</div>
                    <div className="text-sm text-muted-foreground">
                      {videoPreview.analysis.negative_constraints.join(', ')}
                    </div>
                  </div>
                )}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Derived Tool Idea</Label>
                  <div className="p-4 bg-muted/30 rounded-lg border text-sm text-muted-foreground">
                    {videoPreview.analysis.tool_idea}
                  </div>
                </div>
                <div className="rounded-lg border-2 border-primary/20 bg-muted/50 p-5 space-y-3">
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary" className="capitalize text-sm px-3 py-1">
                      {videoPreview.preview.category?.replace('_', ' ') || 'Uncategorized'}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">{videoPreview.preview.tool_id}</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-lg mb-1">{videoPreview.preview.tool_name}</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">{videoPreview.preview.description}</p>
                  </div>
                  {videoPreview.preview.reasoning && (
                    <div className="rounded-md bg-background/50 p-3 border">
                      <div className="text-xs font-medium mb-1 text-muted-foreground">AI Reasoning:</div>
                      <div className="text-sm text-foreground">{videoPreview.preview.reasoning}</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Tool Detail Dialog */}
      <Dialog open={!!selectedId} onOpenChange={(open) => open ? null : onCloseDetail()}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col" onOpenAutoFocus={(e) => e.preventDefault()}>
          <DialogHeader className="pb-4">
            <DialogTitle className="text-2xl">Tool Details</DialogTitle>
            <DialogDescription className="text-base">View, edit, improve, execute, or disable this tool.</DialogDescription>
          </DialogHeader>

          {fetchingDetail && (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 mr-3 animate-spin" />
              <span>Loading tool details…</span>
            </div>
          )}

          {!fetchingDetail && detail && editState && (
            <div className="flex-1 overflow-y-auto">
              <Tabs defaultValue="overview" className="w-full">
                <TabsList className="grid w-full grid-cols-4 mb-6">
                  <TabsTrigger value="overview" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Overview
                  </TabsTrigger>
                  <TabsTrigger value="templates" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Templates
                  </TabsTrigger>
                  <TabsTrigger value="capabilities" className="flex items-center gap-2">
                    <Zap className="h-4 w-4" />
                    Capabilities
                  </TabsTrigger>
                  <TabsTrigger value="actions" className="flex items-center gap-2">
                    <Play className="h-4 w-4" />
                    Actions
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-6 mt-0">
                  {/* Header summary */}
                  <div className="flex items-start justify-between gap-4 pb-4 border-b">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <Badge variant="secondary" className="capitalize text-sm px-3 py-1">
                          {editState.category.replace('_', ' ')}
                        </Badge>
                        <span className="text-xs text-muted-foreground font-mono">{editState.tool_id}</span>
                        <div className="flex items-center gap-2 ml-auto">
                          <Switch 
                            checked={editState.is_active} 
                            onCheckedChange={(v) => setEditState({ ...editState, is_active: v })} 
                          />
                          <span className="text-sm text-muted-foreground">Active</span>
                        </div>
                      </div>
                      <Input 
                        className="text-2xl font-bold mb-2 h-auto py-2" 
                        value={editState.tool_name} 
                        onChange={e => setEditState({ ...editState, tool_name: e.target.value })} 
                      />
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>v{editState.version}.0</span>
                        <span>•</span>
                        <span>{editState.usage_count} generations</span>
                        {editState.success_rate > 0 && (
                          <>
                            <span>•</span>
                            <span>{(editState.success_rate * 100).toFixed(0)}% success rate</span>
                          </>
                        )}
                      </div>
                    </div>
                    <Button variant="destructive" onClick={deleteTool} className="shrink-0">
                      <Trash2 className="h-4 w-4 mr-2" /> 
                      Disable
                    </Button>
                  </div>

                  {/* Description */}
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">Description</Label>
                    <Textarea 
                      value={editState.description || ''} 
                      onChange={e => setEditState({ ...editState, description: e.target.value })} 
                      rows={4}
                      className="resize-none"
                    />
                  </div>

                  {/* Priority and Save */}
                  <div className="flex items-center justify-between p-4 bg-muted/30 rounded-lg border">
                    <div className="flex items-center gap-4">
                      <Label className="text-sm font-semibold min-w-20">Priority</Label>
                      <Input 
                        type="number" 
                        value={String(editState.priority ?? 0)} 
                        onChange={e => setEditState({ ...editState, priority: Number(e.target.value) })} 
                        className="max-w-[120px]"
                      />
                    </div>
                    <Button onClick={saveEdits} className="min-w-[140px]">
                      Save Changes
                    </Button>
                  </div>

                  {/* Original Idea */}
                  {editState.original_idea && (
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold">Original Idea</Label>
                      <div className="p-4 bg-muted/30 rounded-lg border text-sm text-muted-foreground">
                        {editState.original_idea}
                      </div>
                    </div>
                  )}

                  {editState.source_video_url && (
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold">Source Video</Label>
                      <video src={editState.source_video_url} controls className="w-full rounded border" />
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="templates" className="space-y-6 mt-0">
                  <div className="grid grid-cols-1 gap-6">
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Script Prompt Template
                      </Label>
                      <Textarea 
                        value={editState.script_prompt_template || ''} 
                        onChange={e => setEditState({ ...editState, script_prompt_template: e.target.value })} 
                        rows={10}
                        className="resize-none font-mono text-sm"
                        placeholder="Enter script prompt template..."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Image Prompt Template
                      </Label>
                      <Textarea 
                        value={editState.image_prompt_template || ''} 
                        onChange={e => setEditState({ ...editState, image_prompt_template: e.target.value })} 
                        rows={10}
                        className="resize-none font-mono text-sm"
                        placeholder="Enter image prompt template..."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Video Prompt Template
                      </Label>
                      <Textarea 
                        value={editState.video_prompt_template || ''} 
                        onChange={e => setEditState({ ...editState, video_prompt_template: e.target.value })} 
                        rows={10}
                        className="resize-none font-mono text-sm"
                        placeholder="Enter video prompt template..."
                      />
                    </div>
                  </div>
                  <div className="flex justify-end pt-4 border-t">
                    <Button onClick={saveEdits} className="min-w-[140px]">
                      Save Changes
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="capabilities" className="space-y-6 mt-0">
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">Capabilities (JSON)</Label>
                    <Textarea
                      value={JSON.stringify(editState.capabilities ?? {}, null, 2)}
                      onChange={e => {
                        try { 
                          setEditState({ ...editState, capabilities: JSON.parse(e.target.value || '{}') }) 
                        } catch { /* ignore update if invalid */ }
                      }}
                      rows={16}
                      className="resize-none font-mono text-sm"
                      placeholder="{}"
                    />
                    <p className="text-xs text-muted-foreground">
                      Edit the JSON object to modify tool capabilities. Invalid JSON will be ignored.
                    </p>
                  </div>
                  <div className="flex justify-end pt-4 border-t">
                    <Button onClick={saveEdits} className="min-w-[140px]">
                      Save Changes
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="actions" className="space-y-6 mt-0">
                  {/* Improve Tool */}
                  <div className="rounded-lg border-2 p-5 space-y-4 bg-muted/20">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      <h3 className="font-semibold text-lg">Improve Tool</h3>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Use AI to enhance this tool based on your suggestions. The tool version will be incremented.
                    </p>
                    <Textarea 
                      value={improveText} 
                      onChange={e => setImproveText(e.target.value)} 
                      placeholder="How should this tool improve? Be specific about what you want to change or enhance..." 
                      rows={4}
                      className="resize-none"
                    />
                    <div className="flex items-center gap-2">
                      <Switch checked={preserveTemplates} onCheckedChange={setPreserveTemplates} />
                      <Label className="text-sm cursor-pointer">Preserve existing templates</Label>
                    </div>
                    <Button variant="secondary" onClick={improveTool} disabled={!improveText || improveText.length < 10}>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Apply Improvement
                    </Button>
                    {detail.improvement_history && detail.improvement_history.length > 0 && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="font-medium mb-3 text-sm">Improvement History</div>
                        <div className="space-y-2">
                          {detail.improvement_history.map((h, i) => (
                            <div key={i} className="text-sm p-3 bg-background/50 rounded border">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium">v{h.previous_version} → v{h.previous_version + 1}</span>
                                <span className="text-xs text-muted-foreground">{h.timestamp}</span>
                              </div>
                              <p className="text-muted-foreground">{h.suggestion}</p>
                              {h.changes_made && (
                                <p className="text-xs text-muted-foreground mt-2 italic">Changes: {h.changes_made}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Execute Tool */}
                  <div className="rounded-lg border-2 p-5 space-y-4 bg-muted/20">
                    <div className="flex items-center gap-2">
                      <Play className="h-5 w-5 text-primary" />
                      <h3 className="font-semibold text-lg">Execute Tool</h3>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Test this tool by generating prompts for a specific topic.
                    </p>
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Topic</Label>
                        <Input 
                          value={execTopic} 
                          onChange={e => setExecTopic(e.target.value)} 
                          placeholder="Enter a topic to generate prompts for..." 
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Optional Parameters (JSON)</Label>
                        <Textarea 
                          value={execParams} 
                          onChange={e => setExecParams(e.target.value)} 
                          placeholder='{"neon_intensity": 0.8, "style": "cyberpunk"}' 
                          rows={4}
                          className="resize-none font-mono text-sm"
                        />
                      </div>
                      <Button onClick={executeTool} disabled={!execTopic || execTopic.length < 3} className="w-full">
                        <Play className="h-4 w-4 mr-2" />
                        Run Execution
                      </Button>
                    </div>
                    {execResult && (
                      <div className="rounded-lg border p-4 bg-background/50 mt-4">
                        <div className="text-sm font-semibold mb-3">Generated Prompts</div>
                        <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/50 p-3 rounded border overflow-x-auto">
                          {JSON.stringify(execResult.generated_prompts ?? execResult, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}

        </DialogContent>
      </Dialog>
    </div>
  )
}
